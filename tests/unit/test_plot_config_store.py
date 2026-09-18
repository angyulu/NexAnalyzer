"""
Unit tests for modules/dataviz/io/config_store.py.

Two properties matter more than the round-trip: a malformed or unwritable
settings file must never surface as an error (losing a remembered plot is an
inconvenience; a page that won't open is not), and a config remembered against
a sheet that has since lost a column must come back with that control unset
rather than pointing at a column `build_scatter` will raise on.
"""

import json

import pytest

from modules.dataviz.io import config_store


@pytest.fixture
def store(tmp_path):
    return tmp_path / "plot_explorer.json"


class TestRoundTrip:
    def test_absent_file_reads_as_empty(self, store):
        document = config_store.load_document(store)
        assert document["sheets"] == {}
        assert document["last_path"] is None

    def test_sheet_state_survives_a_write(self, store):
        config_store.save_sheet_state("HA_SplitTable", {"config": {"x": "T"}}, store)
        assert config_store.load_sheet_state("HA_SplitTable", store) == {"config": {"x": "T"}}

    def test_sheets_do_not_overwrite_each_other(self, store):
        """The whole point of keying by sheet: one tool per plot, and the six
        sheets of a process workbook share almost no column names."""
        config_store.save_sheet_state("HA_SplitTable", {"config": {"x": "T"}}, store)
        config_store.save_sheet_state("QUAD_SplitTable", {"config": {"x": "Stage T"}}, store)

        assert config_store.load_sheet_state("HA_SplitTable", store)["config"]["x"] == "T"
        assert config_store.load_sheet_state("QUAD_SplitTable", store)["config"]["x"] == "Stage T"

    def test_unknown_sheet_reads_as_none(self, store):
        assert config_store.load_sheet_state("never-saved", store) is None

    def test_last_location_round_trips(self, store):
        config_store.save_last_location("C:/book.xlsx", "HA_SplitTable", store)
        assert config_store.load_last_location(store) == {
            "path": "C:/book.xlsx",
            "sheet": "HA_SplitTable",
        }

    def test_saving_a_location_keeps_sheet_states(self, store):
        config_store.save_sheet_state("HA_SplitTable", {"config": {"x": "T"}}, store)
        config_store.save_last_location("C:/book.xlsx", "HA_SplitTable", store)
        assert config_store.load_sheet_state("HA_SplitTable", store) is not None


class TestNeverRaises:
    def test_malformed_json_reads_as_empty(self, store):
        store.write_text("{not json at all", encoding="utf-8")
        assert config_store.load_document(store)["sheets"] == {}

    def test_unknown_schema_version_is_discarded(self, store):
        store.write_text(json.dumps({"schema_version": 99, "sheets": {"a": {}}}), encoding="utf-8")
        assert config_store.load_document(store)["sheets"] == {}

    def test_non_dict_document_is_discarded(self, store):
        store.write_text(json.dumps(["not", "a", "document"]), encoding="utf-8")
        assert config_store.load_document(store)["sheets"] == {}

    def test_corrupt_sheets_key_is_replaced(self, store):
        store.write_text(
            json.dumps({"schema_version": config_store.SCHEMA_VERSION, "sheets": "nope"}),
            encoding="utf-8",
        )
        assert config_store.load_document(store)["sheets"] == {}

    def test_unwritable_path_is_silent(self, tmp_path):
        """A read-only data/ costs the user their settings, not their session."""
        unwritable = tmp_path / "no-such-dir" / "nested" / "x.json"
        # Point at a path whose parent cannot be created because a file sits
        # where a directory would go.
        (tmp_path / "no-such-dir").write_text("I am a file", encoding="utf-8")
        config_store.save_sheet_state("HA", {"config": {}}, unwritable)  # must not raise


class TestPruneToColumns:
    def test_absent_column_is_unset(self):
        config = {"x": "T", "y": "FWHM", "color": "Gone"}
        pruned = config_store.prune_to_columns(config, ["T", "FWHM"])
        assert pruned["x"] == "T"
        assert pruned["color"] is None

    def test_hover_data_keeps_survivors(self):
        config = {"hover_data": ["WaferID", "Gone", "Date"]}
        pruned = config_store.prune_to_columns(config, ["WaferID", "Date"])
        assert pruned["hover_data"] == ["WaferID", "Date"]

    def test_non_column_settings_are_untouched(self):
        config = {"x": "T", "log_x": True, "title": "Keep me", "opacity": 0.5}
        pruned = config_store.prune_to_columns(config, ["T"])
        assert pruned["log_x"] is True
        assert pruned["title"] == "Keep me"
        assert pruned["opacity"] == 0.5

    def test_does_not_mutate_the_input(self):
        config = {"x": "Gone"}
        config_store.prune_to_columns(config, ["T"])
        assert config["x"] == "Gone"
