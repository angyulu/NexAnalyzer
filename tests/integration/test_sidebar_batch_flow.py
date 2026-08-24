"""Integration test for the sidebar's "Run All Files" batch path.

Two defects motivated it, both in modules/spectra/ui/sidebar.py:

  - the progress bar advanced BEFORE each file's work, so it read 100% for the
    whole of the final (usually slowest) fit and was then torn down;
  - `st.rerun()` immediately after the loop discarded the summary and the list
    of failed files, leaving a multi-file batch with no record of what happened.

The second is why this runs through AppTest rather than a unit test: whether
the report survives to the user is a Streamlit lifecycle question.
"""

import numpy as np
from streamlit.testing.v1 import AppTest


def _write_silicon_raman_file(path, seed, peak_center=520.0):
    """A single peak matching data/materials.json's Silicon (Raman) preset."""
    x = np.linspace(0, 1000, 2000)
    sigma = 8.0 / 2.355
    rng = np.random.default_rng(seed)
    y = 500.0 + 1000.0 * np.exp(-0.5 * ((x - peak_center) / sigma) ** 2) + rng.normal(0, 5, size=x.size)
    with open(path, "w") as f:
        for xi, yi in zip(x, y):
            f.write(f"{xi:.4f}\t{yi:.4f}\n")


def _app_with_files(tmp_path, count=3):
    """The Spectra page with `count` files loaded through the app's own loader.

    `pending_files_to_load` is the seam the Browse button writes and the sidebar
    pops, so the fixture exercises the real parse-and-register path.
    """
    paths = []
    for i in range(1, count + 1):
        path = tmp_path / f"RM_sample{i}.txt"
        _write_silicon_raman_file(path, seed=i)
        paths.append(str(path))

    at = AppTest.from_file("pages/1_Spectra.py", default_timeout=180)
    at.session_state["pending_files_to_load"] = paths
    at.run()
    return at


def _select_silicon(at):
    """Pick the Silicon (Raman) preset.

    The selectbox's options are ("Material", "Mode") tuples rendered through a
    format_func, so set_value needs the tuple; passing the formatted label makes
    format_func index into the string ('S (i)').
    """
    material = next(s for s in at.sidebar.selectbox if "aterial" in (s.label or ""))
    material.set_value(("Silicon", "Raman")).run()
    return at


class TestRunAllFilesBatch:
    def test_the_batch_report_survives_the_run(self, tmp_path):
        """The whole point of dropping st.rerun(): after a batch the user must
        still be able to read how many files succeeded."""
        at = _select_silicon(_app_with_files(tmp_path, count=3))

        next(b for b in at.sidebar.button if "Run All Files" in b.label).click().run()

        assert not at.exception
        messages = [m.value for m in at.sidebar.success] + [m.value for m in at.sidebar.warning]
        assert any("3" in m for m in messages), f"no batch summary survived: {messages}"

    def test_the_status_resolves_instead_of_spinning(self, tmp_path):
        at = _select_silicon(_app_with_files(tmp_path, count=3))

        next(b for b in at.sidebar.button if "Run All Files" in b.label).click().run()

        statuses = at.sidebar.status
        assert statuses, "no status was rendered for the batch"
        assert statuses[0].state == "complete"
        assert "3" in statuses[0].label

    def test_every_file_actually_got_fitted(self, tmp_path):
        """Guards against the progress change quietly skipping an item -- an
        off-by-one in the loop would show here."""
        at = _select_silicon(_app_with_files(tmp_path, count=3))

        next(b for b in at.sidebar.button if "Run All Files" in b.label).click().run()

        files = at.session_state["files"]
        assert len(files) == 3
        assert all(f.fit_done for f in files.values()), \
            {name: f.fit_done for name, f in files.items()}

    def test_the_page_settles_without_a_second_run(self, tmp_path):
        """Dropping the rerun means the run that starts the batch is also the
        run that renders the results, including the export block below it."""
        at = _select_silicon(_app_with_files(tmp_path, count=3))

        next(b for b in at.sidebar.button if "Run All Files" in b.label).click().run()

        assert not at.exception
        # show_fit / show_components are written during the batch and read by
        # checkboxes further down the same function; without a rerun they must
        # still take effect in this very run.
        assert at.session_state["show_fit"] is True
        assert at.session_state["show_components"] is True
