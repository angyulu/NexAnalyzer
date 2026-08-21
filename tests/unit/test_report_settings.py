"""Unit tests for core.io.report_settings (persisted default-material sidecar)."""

from core.io.report_settings import load_default_material, save_default_material


class TestDefaultMaterialRoundTrip:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "report_settings.json"
        save_default_material("WSe2", path=path)

        assert load_default_material(path=path) == "WSe2"

    def test_overwrite_updates_value(self, tmp_path):
        path = tmp_path / "report_settings.json"
        save_default_material("WSe2", path=path)
        save_default_material("MoS2", path=path)

        assert load_default_material(path=path) == "MoS2"

    def test_missing_file_returns_none(self, tmp_path):
        assert load_default_material(path=tmp_path / "does_not_exist.json") is None

    def test_malformed_json_returns_none(self, tmp_path):
        path = tmp_path / "report_settings.json"
        path.write_text("not valid json {{{")

        assert load_default_material(path=path) is None

    def test_missing_key_returns_none(self, tmp_path):
        path = tmp_path / "report_settings.json"
        path.write_text("{}")

        assert load_default_material(path=path) is None
