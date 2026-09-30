"""The wafer-prefix table, its local overlay, and the material check.

The committed table is asserted here so that a hand-edit which drops a tool
line or renames a material fails a test rather than silently downgrading every
wafer on that line to "not verified".
"""

import json

import pytest

from modules.onenote.io import prefix_store as ps


# --- the committed table -------------------------------------------------

def test_committed_table_covers_every_tool_line():
    """All six tool lines resolve, from the file that ships with the repo.

    A missing line is not a crash — it reports as an unknown prefix — which is
    exactly why it needs a test: every wafer on that line would quietly stop
    being checked.
    """
    shared, _ = ps.load_prefixes()

    assert shared == {
        "HA": "WSe2",
        "VA": "WSe2",
        "VB": "WSe2",
        "DU": "WSe2",
        "DD": "WSe2",
        "QU": "MoS2",
    }


def test_committed_table_is_schema_v1():
    with open(ps.get_prefix_table_path(), encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema_version"] == 1


# --- prefix extraction ---------------------------------------------------

@pytest.mark.parametrize(
    "wafer_id,expected",
    [
        ("HADH51", "HA"),
        ("hadh51", "HA"),
        ("  HADG38  ", "HA"),
        ("QUAB07", "QU"),
        ("VBBE12", "VB"),
    ],
)
def test_wafer_prefix_takes_the_tool_line(wafer_id, expected):
    assert ps.wafer_prefix(wafer_id) == expected


def test_wafer_prefix_tolerates_a_non_wafer_folder_name():
    """A folder that is not a wafer ID yields something that misses the table.

    Reporting "unknown prefix" is the right outcome for a folder named `X`;
    raising would take the page down over a name the operator can see.
    """
    assert ps.wafer_prefix("X") == "X"
    assert ps.wafer_prefix("") == ""
    assert ps.resolve("X", shared={"HA": "WSe2"}, local={}).material is None


# --- the overlay ---------------------------------------------------------

def test_local_overlay_wins_and_says_so():
    resolution = ps.resolve("QUAB07", shared={"QU": "MoS2"}, local={"QU": "WS2"})

    assert resolution.material == "WS2"
    assert resolution.source == ps.SOURCE_LOCAL
    assert resolution.is_local


def test_shared_answers_when_the_overlay_is_silent():
    resolution = ps.resolve("HADH51", shared={"HA": "WSe2"}, local={})

    assert resolution.material == "WSe2"
    assert resolution.source == ps.SOURCE_SHARED
    assert not resolution.is_local


def test_add_local_prefix_writes_only_the_local_file(tmp_path):
    """The one-click add must never touch the committed table.

    If it did, one operator's guess would land uncommitted on their machine
    and diverge from everyone else's while both showed a verified result.
    """
    local = tmp_path / "material_prefixes.local.json"
    ps.add_local_prefix("hm", "MoS2", path=local)

    assert json.loads(local.read_text(encoding="utf-8"))["prefixes"] == {"HM": "MoS2"}
    # The committed table on disk is untouched.
    shared, _ = ps.load_prefixes()
    assert "HM" not in shared


def test_add_local_prefix_accumulates(tmp_path):
    local = tmp_path / "material_prefixes.local.json"
    ps.add_local_prefix("HM", "MoS2", path=local)
    ps.add_local_prefix("ZZ", "WS2", path=local)

    assert ps._read_prefixes(local) == {"HM": "MoS2", "ZZ": "WS2"}


def test_a_malformed_table_reads_as_empty_rather_than_raising(tmp_path):
    """A trailing comma must degrade to "unknown", not break the page."""
    broken = tmp_path / "material_prefixes.local.json"
    broken.write_text('{"prefixes": {"HA": "WSe2",}}', encoding="utf-8")

    assert ps._read_prefixes(broken) == {}


def test_a_missing_file_reads_as_empty(tmp_path):
    assert ps._read_prefixes(tmp_path / "nope.json") == {}


# --- the check -----------------------------------------------------------

def test_match():
    check = ps.check_material("HADH51", "WSe2", shared={"HA": "WSe2"}, local={})

    assert check.verdict == ps.MATCH
    assert "matches" in check.summary()


def test_match_is_case_insensitive():
    """`WSe2` and `wse2` are the same material, not a mismatch."""
    check = ps.check_material("HADH51", "wse2", shared={"HA": "WSe2"}, local={})

    assert check.verdict == ps.MATCH


def test_mismatch_names_both_materials():
    """The verdict the check exists for: a QU wafer left on WSe2."""
    check = ps.check_material("QUAB07", "WSe2", shared={"QU": "MoS2"}, local={})

    assert check.verdict == ps.MISMATCH
    assert check.expected == "MoS2"
    assert check.selected == "WSe2"
    assert "WSe2" in check.summary() and "MoS2" in check.summary()


def test_unknown_prefix_is_not_a_mismatch():
    """"We did not check" and "we checked and it disagrees" must differ.

    Rendering them alike would teach the team to read every warning as the
    same thing, which is how a real mismatch gets dismissed.
    """
    check = ps.check_material("HMAA01", "MoS2", shared={"HA": "WSe2"}, local={})

    assert check.verdict == ps.UNKNOWN_PREFIX
    assert check.expected is None
    assert "not verified" in check.summary()
    assert "mismatch" not in check.summary().lower()


def test_no_selection_is_its_own_verdict():
    check = ps.check_material("HADH51", None, shared={"HA": "WSe2"}, local={})

    assert check.verdict == ps.NO_SELECTION


def test_a_locally_resolved_match_is_marked_unshared():
    """A local guess must never present itself as the team's agreed answer."""
    check = ps.check_material("HMAA01", "MoS2", shared={}, local={"HM": "MoS2"})

    assert check.verdict == ps.MATCH
    assert check.is_local
    assert "not yet shared" in check.summary()


def test_a_shared_match_carries_no_local_caveat():
    check = ps.check_material("HADH51", "WSe2", shared={"HA": "WSe2"}, local={})

    assert not check.is_local
    assert "not yet shared" not in check.summary()


def test_the_check_never_raises_on_junk():
    """Every outcome is a verdict the page renders and then uploads anyway."""
    for wafer_id in ("", "   ", "X", "123456"):
        assert ps.check_material(wafer_id, "WSe2", shared={"HA": "WSe2"}, local={})


# --- wafer ID shape ------------------------------------------------------

@pytest.mark.parametrize("wafer_id", ["HADH51", "hadh51", " VBBE12 ", "QUAB07"])
def test_a_real_wafer_id_looks_like_one(wafer_id):
    assert ps.looks_like_wafer_id(wafer_id)


@pytest.mark.parametrize("name", ["HA", "HADH", "HADH5", "HADH511", "", "HAD-51"])
def test_a_partial_or_malformed_name_does_not(name):
    """`HA` is a tool prefix, not a wafer.

    It resolves against the table perfectly well, so without this check a page
    named after a whole tool line would report a confident green match.
    """
    assert not ps.looks_like_wafer_id(name)


def test_the_shape_check_does_not_gate_the_material_check():
    """A malformed name still gets a verdict — the shape check only warns.

    This app does not own the naming convention, and refusing a folder the
    operator can see would be the app overruling the share.
    """
    check = ps.check_material("HA", "WSe2", shared={"HA": "WSe2"}, local={})

    assert check.verdict == ps.MATCH
