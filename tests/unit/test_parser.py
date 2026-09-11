"""Unit tests for modules.spectra.processing.parser (spectrum .txt file parsing)."""

import numpy as np
import pytest

from modules.spectra.processing.parser import (
    parse_spectrum,
    count_spectra,
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
        # VABD38's naming. Until v4.0.0 the scanner read this as Raman while
        # the detector, which knew only "RM", returned None for it.
        ("Raman_1.txt", "Raman"),
        ("RAMAN-3.txt", "Raman"),
        ("raman_map.txt", "Raman"),
    ])
    def test_detects_mode_from_prefix(self, filename, expected):
        assert detect_mode_from_filename(filename) == expected


class TestTheTwoFilenameRulesShareOneVocabulary:
    """`sample_scanner` matches whole prefixes and `detect_mode_from_filename`
    matches leading substrings -- two questions, one vocabulary. They disagreed
    until v4.0.0, and a file the scanner collected could be one the detector
    could not label."""

    def test_every_prefix_the_scanner_accepts_the_detector_also_reads(self, tmp_path):
        from modules.spectra.processing.parser import PL_PREFIXES, RAMAN_PREFIXES
        from modules.spectra.processing.sample_scanner import scan_sample_folder

        # A distinct point per prefix: the scanner keys by point within a
        # technique, so RM_1 and RAMAN_1 would be the same slot.
        prefixes = sorted(RAMAN_PREFIXES | PL_PREFIXES)
        for point, prefix in enumerate(prefixes, start=1):
            (tmp_path / f"{prefix}_{point}.txt").write_text("1 2" + chr(10))

        scan = scan_sample_folder(str(tmp_path))
        collected = list(scan.raman_files.values()) + list(scan.pl_files.values())

        assert len(collected) == len(prefixes)
        for path in collected:
            assert detect_mode_from_filename(path) is not None, path

    def test_the_scanner_no_longer_keeps_its_own_copy(self):
        """A second copy of the list is how they drifted apart the first time."""
        import modules.spectra.processing.sample_scanner as scanner

        assert not hasattr(scanner, "_RAMAN_PREFIXES")


class TestCountSpectra:
    """Sizing the work without paying to parse it.

    The report's progress weighting needs to know how many spectra a folder
    holds before fitting starts. Re-parsing every 2.6 MB file to find out would
    cost more than the weighting is worth.
    """

    def _write(self, path, columns, rows=200):
        import numpy as np
        x = np.linspace(0, 1000, rows)
        data = [x] + [np.full(rows, 100.0 + i) for i in range(columns)]
        with open(path, "w") as f:
            for row in zip(*data):
                f.write("\t".join(f"{v:.4f}" for v in row) + "\n")

    def test_counts_y_columns_not_all_columns(self, tmp_path):
        path = tmp_path / "rm-1.txt"
        self._write(path, columns=25)

        assert count_spectra(str(path)) == 25

    def test_a_two_column_file_holds_one_spectrum(self, tmp_path):
        path = tmp_path / "single.txt"
        self._write(path, columns=1)

        assert count_spectra(str(path)) == 1

    def test_it_agrees_with_the_real_parse(self, tmp_path):
        """If these ever disagree the progress bar sizes work that never
        happens, or misses work that does."""
        path = tmp_path / "rm-2.txt"
        self._write(path, columns=7)

        assert count_spectra(str(path)) == len(parse_spectrum_multi(str(path)))

    def test_an_unreadable_file_counts_zero_rather_than_raising(self, tmp_path):
        """A caller sizing work shouldn't handle an exception for a file the
        fit loop will report as an error moments later anyway."""
        assert count_spectra(str(tmp_path / "does_not_exist.txt")) == 0
