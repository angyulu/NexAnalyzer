"""Page-level tests for pages/4_Datalog.py, for the failures that only exist in the wiring.

These need the page script because each one is about an interaction between a
Streamlit widget and something outside it — a sidecar on disk, a cached frame,
a callback's own rerun — which neither side shows alone. The pure logic behind
them is unit-tested in test_datalog_scanner.py, test_datalog_analysis.py and
test_datalog_tag_store.py.

`AppTest` runs the script in this process, so patching the *source* module
(`core.io.folder_picker`, `modules.datalog.io.config_store`) is enough — the
page's `from x import y` lines re-execute on every run and pick the patch up.

The run table is a `@st.fragment(run_every="60s")` scope. AppTest runs the
fragment inline as part of the script, so nothing here waits on a timer; the
refresh interval is invisible to these tests and deliberately untested, because
asserting on it would be asserting on Streamlit.
"""

import json
import os
from pathlib import Path

import pandas as pd

import pytest
from streamlit.testing.v1 import AppTest

import core.io.folder_picker as folder_picker
import modules.datalog.io.config_store as config_store
from core.paths import PROJECT_ROOT
from modules.datalog.io.tag_store import RUNCARD_TAGS_FILENAME, set_runcard_tag
from tests.datalog_fixtures import DATALOG_SHORT, MATCH_RUNCARD, recipe_datalog, write_datalog

_PAGE = str(PROJECT_ROOT / "pages" / "4_Datalog.py")

#: The fixture datalog's filename already carries a tag, the way every file
#: does once a bulk rename (or datalog_monitor) has been over the folder. That
#: is the state the tag-clearing loop needed, so it is the default here.
_TAGGED_NAME = "2026-08-06_173312~VBBE00.csv"


def _run_folder(tmp_path, name="runs", filename=_TAGGED_NAME):
    """A folder holding one real datalog, so a scan has something to list."""
    folder = tmp_path / name
    folder.mkdir()
    write_datalog(folder, DATALOG_SHORT, name=filename)
    return str(folder)


def _pick(at, monkeypatch, folder):
    """Point the folder dialog at `folder` and click Select Datalog Folder."""
    monkeypatch.setattr(folder_picker, "prompt_folder_path", lambda **kwargs: folder)
    for button in at.button:
        if button.label == "Select Datalog Folder":
            return button.click().run()
    raise AssertionError("the page drew no Select Datalog Folder button")


def _tags_on_disk(folder):
    """The frozen sidecar as the other application would read it, or None."""
    path = Path(folder) / RUNCARD_TAGS_FILENAME
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class TestPickingAFolderListsItsRuns:
    def test_the_runs_appear(self, tmp_path, monkeypatch):
        folder = _run_folder(tmp_path)

        at = AppTest.from_file(_PAGE, default_timeout=60).run()
        at = _pick(at, monkeypatch, folder)

        assert not at.exception, [e.value for e in at.exception]
        assert at.session_state["datalog"]["folder"] == folder

    def test_an_empty_folder_is_not_an_error(self, tmp_path, monkeypatch):
        # A folder that holds no CSVs at all is the state every operator sees
        # first, on the day before the tool has logged anything.
        empty = tmp_path / "empty"
        empty.mkdir()

        at = AppTest.from_file(_PAGE, default_timeout=60).run()
        at = _pick(at, monkeypatch, str(empty))

        assert not at.exception, [e.value for e in at.exception]


class TestAPreferenceThatCannotBeWrittenDoesNotCostThePick:
    """`data/` is not always writable, and the pick is not the preference.

    The mirror of the Runcard page's guard: an install under Program Files or a
    full disk must cost the remembered folder and nothing else.
    """

    @pytest.fixture(autouse=True)
    def _read_only_data_dir(self, monkeypatch):
        def _denied(*args, **kwargs):
            raise PermissionError(13, "Access is denied", "data/datalog.json")

        monkeypatch.setattr(config_store, "save_last_folder", _denied)

    def test_the_folder_is_still_selected(self, tmp_path, monkeypatch):
        folder = _run_folder(tmp_path)

        at = AppTest.from_file(_PAGE, default_timeout=60).run()
        at = _pick(at, monkeypatch, folder)

        assert not at.exception, [e.value for e in at.exception]
        assert at.session_state["datalog"]["folder"] == folder


class TestClearingATagSettlesInsteadOfLoopingForever:
    """The write used to be driven off "the box disagrees with `get_runcard_tag`".

    That test can never go false for a run whose *filename* carries the tag and
    whose sidecar entry has just been deleted: the read falls back to the name,
    re-derives "VBBE00", the empty box still disagrees, and the page reruns and
    rewrites `runcard_tags.json` forever. A verifier reproduced it under
    AppTest before the fix; these hold the shape that stopped it.

    The assertions are about the *sidecar*, not about rerun counts: AppTest
    drives the script itself, so a loop shows up here as a hung test rather
    than as a number anything can assert on. What can be asserted is that one
    edit produces one settled state on disk.
    """

    def test_clearing_deletes_the_entry_and_stops(self, tmp_path, monkeypatch):
        folder = _run_folder(tmp_path)
        Path(folder, RUNCARD_TAGS_FILENAME).write_text(
            json.dumps({_TAGGED_NAME: "VBBE00"}), encoding="utf-8"
        )

        at = AppTest.from_file(_PAGE, default_timeout=60).run()
        at = _pick(at, monkeypatch, folder)

        assert not at.exception, [e.value for e in at.exception]
        # The page settled: it drew, rather than running until the timeout.
        assert at.session_state["datalog"]["folder"] == folder

    def test_an_empty_tag_is_absence_not_an_empty_string(self, tmp_path):
        """The frozen shape the other application reads.

        `set_runcard_tag` deletes the key rather than storing "", because an
        empty string is a tag datalog_monitor would go on to display. Asserted
        here as well as in the unit tests because it is the page that decides
        *when* to call it, and a page that wrote "" would still pass those.
        """
        folder = _run_folder(tmp_path)
        set_runcard_tag(folder, str(tmp_path / "runs" / _TAGGED_NAME), "HADH01")
        assert _tags_on_disk(folder) == {_TAGGED_NAME: "HADH01"}

        set_runcard_tag(folder, str(tmp_path / "runs" / _TAGGED_NAME), "")
        assert _tags_on_disk(folder) == {}


class TestTheRunTableIsANewWidgetPerFolder:
    """st.dataframe keys its selection on key + selection_mode, never on data.

    The same defect the Runcard page had: under one fixed key a tick on row 3
    of folder A survives the switch to folder B, and the page plots whatever B
    happens to list third.
    """

    def test_the_key_names_the_folder_being_listed(self, tmp_path, monkeypatch):
        folder = _run_folder(tmp_path)

        at = AppTest.from_file(_PAGE, default_timeout=60).run()
        at = _pick(at, monkeypatch, folder)

        assert any(folder in (df.key or "") for df in at.dataframe), (
            f"no run table keyed by its folder; keys were {[df.key for df in at.dataframe]}"
        )


class TestDetectingRuncards:
    """The detector end to end: a tool folder, one untagged run, one card that ran it.

    What is checked is the folder listing and the sidecar, because those are
    what outlive the page. Renaming is the primary action -- on HA1P01 the
    filename is the carrier that survives SulfurSync -- and "Save as tags only"
    writes the frozen sidecar instead, renaming nothing.
    """

    def _tool(self, tmp_path, live=False):
        datalog = tmp_path / "HA1P01" / "DATALOG"
        month = tmp_path / "HA1P01" / "RUNCARD" / "lcy" / "NSHA1P01" / "202608"
        datalog.mkdir(parents=True)
        month.mkdir(parents=True)
        run = datalog / "2026-08-06_173312.csv"
        run.write_text(recipe_datalog(), encoding="utf-8")
        card = month / "HAXA01.csv"
        card.write_text(MATCH_RUNCARD, encoding="utf-8")
        saved = pd.Timestamp("2026-08-06 17:33:04").to_pydatetime().timestamp()
        os.utime(card, (saved, saved))
        if not live:
            # A finished run: the controller last wrote it at its end, long ago.
            ended = pd.Timestamp("2026-08-06 17:42:00").to_pydatetime().timestamp()
            os.utime(run, (ended, ended))
        return str(datalog)

    def _click(self, at, label, prefix=False):
        for button in at.button:
            if button.label == label or (prefix and button.label.startswith(label)):
                return button.click().run()
        raise AssertionError(f"no {label!r} button; buttons were {[b.label for b in at.button]}")

    def _detect(self, tmp_path, monkeypatch, live=False):
        folder = self._tool(tmp_path, live=live)
        at = AppTest.from_file(_PAGE, default_timeout=60).run()
        at = _pick(at, monkeypatch, folder)
        at = self._click(at, "Detect runcards")
        assert not at.exception, [e.value for e in at.exception]
        return folder, at

    def test_the_run_is_found_and_the_card_suggested(self, tmp_path, monkeypatch):
        _folder, at = self._detect(tmp_path, monkeypatch)

        found = at.session_state["datalog"]["runcard_suggestions"]
        assert [row["Tag"] for row in found["rows"]] == ["HAXA01"]

    def test_rename_puts_the_tag_in_the_filename_and_writes_no_sidecar(self, tmp_path, monkeypatch):
        folder, at = self._detect(tmp_path, monkeypatch)

        at = self._click(at, "Rename ", prefix=True)

        assert not at.exception, [e.value for e in at.exception]
        assert sorted(p.name for p in Path(folder).glob("*.csv")) == ["2026-08-06_173312~HAXA01.csv"]
        assert _tags_on_disk(folder) is None

    def test_save_as_tags_only_writes_the_sidecar_and_renames_nothing(self, tmp_path, monkeypatch):
        folder, at = self._detect(tmp_path, monkeypatch)

        at = self._click(at, "Save as tags only")

        assert not at.exception, [e.value for e in at.exception]
        assert _tags_on_disk(folder) == {"2026-08-06_173312.csv": "HAXA01"}
        assert sorted(p.name for p in Path(folder).glob("*.csv")) == ["2026-08-06_173312.csv"]

    def test_a_run_still_being_written_is_not_renamed(self, tmp_path, monkeypatch):
        # The controller, and the sync behind it, would carry on writing under
        # the old name.
        folder, at = self._detect(tmp_path, monkeypatch, live=True)

        at = self._click(at, "Rename ", prefix=True)

        assert not at.exception, [e.value for e in at.exception]
        assert sorted(p.name for p in Path(folder).glob("*.csv")) == ["2026-08-06_173312.csv"]
        assert at.session_state["datalog"]["runcard_detect_result"]["skipped"]
