"""Unit tests for modules.datalog.io.config_store (this installation's remembered datalog folder)."""

import json

from modules.datalog.io.config_store import SCHEMA_VERSION, load_last_folder, save_last_folder


class TestLastFolderRoundTrip:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "datalog.json"

        save_last_folder(r"D:\HA_DataRecord", path=path)

        assert load_last_folder(path=path) == r"D:\HA_DataRecord"

    def test_saving_again_replaces_the_remembered_folder(self, tmp_path):
        path = tmp_path / "datalog.json"
        save_last_folder(r"D:\HA_DataRecord", path=path)

        save_last_folder(r"E:\Archive", path=path)

        assert load_last_folder(path=path) == r"E:\Archive"

    def test_a_folder_that_is_not_reachable_is_still_remembered(self, tmp_path):
        # Existence is deliberately not checked: a share that has not
        # reconnected yet is still the folder the operator wants, and the run
        # list already says "no runs found" rather than losing the setting.
        path = tmp_path / "datalog.json"

        save_last_folder(r"\\tool-pc\logs", path=path)

        assert load_last_folder(path=path) == r"\\tool-pc\logs"

    def test_the_parent_directory_is_created_if_it_is_missing(self, tmp_path):
        path = tmp_path / "data" / "datalog.json"

        save_last_folder(r"D:\HA_DataRecord", path=path)

        assert path.exists()


class TestLoadDegradesRatherThanRaising:
    def test_a_missing_file_returns_none(self, tmp_path):
        assert load_last_folder(path=tmp_path / "does_not_exist.json") is None

    def test_malformed_json_returns_none(self, tmp_path):
        path = tmp_path / "datalog.json"
        path.write_text("not valid json {{{")

        assert load_last_folder(path=path) is None

    def test_non_utf8_file_returns_none(self, tmp_path):
        # UnicodeDecodeError is a ValueError, not an OSError, so it used to
        # escape the catch and raise out of a function documented never to
        # raise -- a half-written or sync-mangled sidecar took the page down.
        path = tmp_path / "datalog.json"
        path.write_bytes(b"\xff\xfe\x00half a write")

        assert load_last_folder(path=path) is None

    def test_a_schema_this_build_does_not_read_returns_none(self, tmp_path):
        path = tmp_path / "datalog.json"
        path.write_text(json.dumps({"schema_version": SCHEMA_VERSION + 1, "last_folder": "D:\\x"}))

        assert load_last_folder(path=path) is None

    def test_a_missing_folder_key_returns_none(self, tmp_path):
        path = tmp_path / "datalog.json"
        path.write_text(json.dumps({"schema_version": SCHEMA_VERSION}))

        assert load_last_folder(path=path) is None

    def test_a_folder_stored_as_something_other_than_a_string_returns_none(self, tmp_path):
        path = tmp_path / "datalog.json"
        path.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "last_folder": ["D:\\x"]}))

        assert load_last_folder(path=path) is None

    def test_an_empty_folder_string_returns_none(self, tmp_path):
        path = tmp_path / "datalog.json"
        path.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "last_folder": ""}))

        assert load_last_folder(path=path) is None


class TestDefaultPath:
    def test_with_no_path_argument_it_reads_this_installations_sidecar(self, tmp_path, monkeypatch):
        # The page never passes a path; it uses the one in this repo's data/.
        import modules.datalog.io.config_store as config_store

        monkeypatch.setattr(
            config_store, "get_datalog_config_path", lambda: tmp_path / "datalog.json"
        )

        save_last_folder(r"D:\HA_DataRecord")

        assert load_last_folder() == r"D:\HA_DataRecord"
