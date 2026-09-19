"""Unit tests for modules.runcard.io.config_store (the remembered runcard folder)."""

import json

from core.paths import DATA_DIR
from modules.runcard.io.config_store import (
    SCHEMA_VERSION,
    get_runcard_config_path,
    load_runcard_folder,
    save_runcard_folder,
)


class TestRuncardFolderRoundTrip:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "runcard.json"
        save_runcard_folder(r"C:\recipes\archive", path=path)

        assert load_runcard_folder(path=path) == r"C:\recipes\archive"

    def test_overwrite_updates_the_value(self, tmp_path):
        path = tmp_path / "runcard.json"
        save_runcard_folder(r"C:\recipes\archive", path=path)
        save_runcard_folder(r"C:\recipes\2026", path=path)

        assert load_runcard_folder(path=path) == r"C:\recipes\2026"

    def test_the_file_carries_its_schema_version(self, tmp_path):
        # report_settings.json does not, and the cost is that a future reader
        # of it cannot tell an old shape from a new one without guessing.
        path = tmp_path / "runcard.json"
        save_runcard_folder("F", path=path)

        assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION

    def test_saving_creates_the_data_folder(self, tmp_path):
        path = tmp_path / "data" / "runcard.json"

        save_runcard_folder("F", path=path)

        assert load_runcard_folder(path=path) == "F"

    def test_a_folder_that_no_longer_exists_is_still_returned(self, tmp_path):
        # An archive on a disconnected share is still the right answer to
        # "where was I", and the page can say so far more usefully than a None.
        path = tmp_path / "runcard.json"
        save_runcard_folder(str(tmp_path / "went_away"), path=path)

        assert load_runcard_folder(path=path) == str(tmp_path / "went_away")


class TestLoadNeverRaises:
    """A lost preference must never be why a page refuses to open."""

    def test_a_missing_file_is_none(self, tmp_path):
        assert load_runcard_folder(path=tmp_path / "does_not_exist.json") is None

    def test_malformed_json_is_none(self, tmp_path):
        path = tmp_path / "runcard.json"
        path.write_text("not valid json {{{")

        assert load_runcard_folder(path=path) is None

    def test_a_json_document_that_is_not_an_object_is_none(self, tmp_path):
        path = tmp_path / "runcard.json"
        path.write_text('["C:\\\\recipes"]')

        assert load_runcard_folder(path=path) is None

    def test_a_file_whose_bytes_are_not_utf8_is_none(self, tmp_path):
        # UnicodeDecodeError is a ValueError, not an OSError, so it used to
        # escape the catch and raise out of here.
        path = tmp_path / "runcard.json"
        path.write_bytes(b"\xff\xfe\x00half a write")

        assert load_runcard_folder(path=path) is None

    def test_a_schema_this_build_does_not_read_is_none(self, tmp_path):
        path = tmp_path / "runcard.json"
        path.write_text(json.dumps({"schema_version": SCHEMA_VERSION + 1, "folder": "F"}))

        assert load_runcard_folder(path=path) is None

    def test_a_missing_or_empty_folder_key_is_none(self, tmp_path):
        path = tmp_path / "runcard.json"
        path.write_text(json.dumps({"schema_version": SCHEMA_VERSION}))
        assert load_runcard_folder(path=path) is None

        path.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "folder": ""}))
        assert load_runcard_folder(path=path) is None

    def test_a_folder_that_is_not_a_string_is_none(self, tmp_path):
        path = tmp_path / "runcard.json"
        path.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "folder": 7}))

        assert load_runcard_folder(path=path) is None


class TestConfigPath:
    def test_the_sidecar_lives_with_this_installations_data(self):
        # A function rather than a module constant, so a test can redirect it:
        # a constant read into a module global at import time cannot be
        # patched on the module that imported it.
        path = get_runcard_config_path()

        assert path.name == "runcard.json"
        assert path.parent == DATA_DIR
