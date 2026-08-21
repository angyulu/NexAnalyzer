"""Unit tests for modules.spectra.processing.fitting (Voigt fitting, peak auto-find)."""

import numpy as np
import pytest

from modules.spectra.processing.fitting import fit_voigt_peaks, auto_find_peaks, detect_overlapping_peaks
from modules.spectra.models.peak import PeakDefinition


class TestFitVoigtPeaks:
    def test_single_peak_converges_with_good_fit(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=300, peaks=((1000.0, 1000.0, 50.0),))
        peak_defs = [PeakDefinition(center=990.0, amplitude=1.0, width_fwhm=60.0)]

        result = fit_voigt_peaks(x, y, peak_defs, mode="Raman")

        assert result.success
        assert result.r_squared > 0.9
        assert len(result.fitted_peaks) == 1
        assert result.fitted_peaks[0].center == pytest.approx(1000.0, abs=10.0)

    def test_two_peaks_converges_with_good_fit(self, synthetic_spectrum):
        x, y = synthetic_spectrum(
            n_points=300,
            peaks=((800.0, 500.0, 40.0), (1300.0, 800.0, 60.0)),
        )
        peak_defs = [
            PeakDefinition(center=790.0, amplitude=1.0, width_fwhm=45.0),
            PeakDefinition(center=1310.0, amplitude=1.0, width_fwhm=65.0),
        ]

        result = fit_voigt_peaks(x, y, peak_defs, mode="Raman")

        assert result.success
        assert result.r_squared > 0.9
        assert len(result.fitted_peaks) == 2

    def test_empty_peak_table_raises(self, synthetic_spectrum):
        x, y = synthetic_spectrum()
        with pytest.raises(ValueError):
            fit_voigt_peaks(x, y, [], mode="Raman")

    def test_too_many_peaks_raises(self, synthetic_spectrum):
        x, y = synthetic_spectrum()
        peak_defs = [PeakDefinition(center=float(c), amplitude=1.0, width_fwhm=20.0) for c in range(11)]
        with pytest.raises(ValueError):
            fit_voigt_peaks(x, y, peak_defs, mode="Raman")

    def test_mismatched_lengths_raise(self):
        x = np.linspace(0, 10, 100)
        y = np.ones(50)
        peak_defs = [PeakDefinition(center=5.0, amplitude=1.0, width_fwhm=1.0)]
        with pytest.raises(ValueError):
            fit_voigt_peaks(x, y, peak_defs, mode="Raman")


class TestAutoFindPeaks:
    def test_finds_single_real_peak(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=300, peaks=((1000.0, 1000.0, 50.0),))
        found = auto_find_peaks(x, y, mode="Raman", min_peaks=2, max_peaks=5)

        assert len(found) == 1
        assert found[0].center == pytest.approx(1000.0, abs=15.0)

    def test_fewer_real_peaks_than_min_peaks_does_not_crash(self, synthetic_spectrum):
        """Regression test for the auto_find_peaks clarity fix (fitting.py).

        min_peaks can't manufacture peaks that don't exist; the function
        should simply return however many real peaks it actually found.
        """
        x, y = synthetic_spectrum(n_points=300, peaks=((1000.0, 1000.0, 50.0),))
        found = auto_find_peaks(x, y, mode="Raman", min_peaks=3, max_peaks=5)

        assert len(found) == 1

    def test_caps_at_max_peaks(self, synthetic_spectrum):
        peaks = tuple((200.0 + i * 300.0, 500.0 + i * 50.0, 30.0) for i in range(6))
        x, y = synthetic_spectrum(n_points=600, x_range=(0.0, 2000.0), peaks=peaks, noise_std=0.0)

        found = auto_find_peaks(x, y, mode="Raman", min_peaks=1, max_peaks=3, prominence_threshold=0.01)

        assert len(found) <= 3

    def test_short_array_returns_empty(self):
        x = np.linspace(0, 10, 5)
        y = np.ones(5)
        assert auto_find_peaks(x, y) == []

    def test_no_peaks_returns_empty(self):
        x = np.linspace(0, 10, 200)
        y = np.ones(200)  # perfectly flat, no prominence anywhere
        assert auto_find_peaks(x, y, prominence_threshold=0.5) == []

    def test_result_sorted_by_center(self, synthetic_spectrum):
        x, y = synthetic_spectrum(
            n_points=400, x_range=(0.0, 2000.0),
            peaks=((1500.0, 800.0, 30.0), (500.0, 600.0, 30.0)),
        )
        found = auto_find_peaks(x, y, mode="Raman", min_peaks=1, max_peaks=5, prominence_threshold=0.1)

        centers = [p.center for p in found]
        assert centers == sorted(centers)


class TestDetectOverlappingPeaks:
    def test_no_warnings_for_well_separated_peaks(self):
        peaks = [
            PeakDefinition(center=100.0, amplitude=1.0, width_fwhm=10.0, label="A"),
            PeakDefinition(center=500.0, amplitude=1.0, width_fwhm=10.0, label="B"),
        ]
        assert detect_overlapping_peaks(peaks, merge_threshold=2.0) == []

    def test_warns_for_close_peaks(self):
        peaks = [
            PeakDefinition(center=100.0, amplitude=1.0, width_fwhm=20.0, label="A"),
            PeakDefinition(center=105.0, amplitude=1.0, width_fwhm=20.0, label="B"),
        ]
        warnings = detect_overlapping_peaks(peaks, merge_threshold=2.0)
        assert len(warnings) == 1
        assert "A" in warnings[0] and "B" in warnings[0]
