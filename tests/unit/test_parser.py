"""Unit tests for modules.spectra.processing.parser (spectrum .txt file parsing)."""

import numpy as np
import pytest

from modules.spectra.processing.parser import (
    parse_spectrum,
    parse_spectrum_multi,
    validate_spectrum_file,
    estimate_spectral_resolution,
    detect_mode_from_filename,
)


def _write_spectrum_file(tmp_path, x, y, sep="\t", name="spectrum.txt"):
    path = tmp_path / name
    lines = [f"{xi}{sep}{yi}" for xi, yi in zip(x, y)]
    path.write_text("\n".join(lines))
    return str(path)


class TestParseSpectrum:
    def test_parses_tab_delimited_file(self, tmp_path):
        x = np.linspace(100, 1000, 150)
        y = np.linspace(10, 20, 150)
        path = _write_spectrum_file(tmp_path, x, y, sep="\t")

        data = parse_spectrum(path)

        assert data.X.shape == (150,)
        assert data.Y.shape == (150,)
        np.testing.assert_allclose(data.X, x)
        np.testing.assert_allclose(data.Y, y)

    def test_parses_comma_delimited_file(self, tmp_path):
        x = np.linspace(0, 100, 120)
        y = np.linspace(0, 50, 120)
        path = _write_spectrum_file(tmp_path, x, y, sep=",")

        data = parse_spectrum(path)
        np.testing.assert_allclose(data.X, x)

    def test_parses_whitespace_delimited_file(self, tmp_path):
        x = np.linspace(0, 100, 120)
        y = np.linspace(0, 50, 120)
        path = _write_spectrum_file(tmp_path, x, y, sep="   ")

        data = parse_spectrum(path)
        np.testing.assert_allclose(data.X, x)

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_spectrum("does_not_exist.txt")

    def test_multi_column_file_requires_parse_spectrum_multi(self, tmp_path):
        x = np.linspace(0, 100, 120)
        y1 = np.linspace(0, 50, 120)
        y2 = np.linspace(50, 100, 120)
        path = tmp_path / "multi.txt"
        lines = [f"{xi}\t{a}\t{b}" for xi, a, b in zip(x, y1, y2)]
        path.write_text("\n".join(lines))

        with pytest.raises(ValueError):
            parse_spectrum(str(path))

        spectra = parse_spectrum_multi(str(path))
        assert len(spectra) == 2


class TestValidateSpectrumFile:
    def test_valid_file(self, tmp_path):
        x = np.linspace(0, 100, 120)
        y = np.linspace(0, 50, 120)
        path = _write_spectrum_file(tmp_path, x, y)

        is_valid, msg = validate_spectrum_file(path)
        assert is_valid
        assert msg == ""

    def test_missing_file_is_invalid(self):
        is_valid, msg = validate_spectrum_file("does_not_exist.txt")
        assert not is_valid
        assert msg != ""
class TestEstimateSpectralResolution:
    def test_matches_expected_median_step(self):
        X = np.linspace(100, 1000, 1000)
        resolution = estimate_spectral_resolution(X)
        assert resolution == pytest.approx(0.901, abs=0.001)

    def test_single_point_returns_fallback(self):
        assert estimate_spectral_resolution(np.array([5.0])) == 1.0


class TestDetectModeFromFilename:
    @pytest.mark.parametrize("filename,expected", [
        ("RM_carbon_sample.txt", "Raman"),
        ("pl_emission_test.txt", "PL"),
        ("sample_001.txt", None),
        ("/path/to/RM_data.txt", "Raman"),
    ])
    def test_detects_mode_from_prefix(self, filename, expected):
        assert detect_mode_from_filename(filename) == expected
