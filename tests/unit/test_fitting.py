"""Unit tests for modules.spectra.processing.fitting (Voigt fitting, peak auto-find)."""

import numpy as np
import pytest

from modules.spectra.processing.fitting import (
    auto_find_peaks,
    detect_overlapping_peaks,
    fit_voigt_peaks,
    voigt_fwhm,
    voigt_fwhm_stderr,
)
from modules.spectra.models.peak import PeakDefinition


class TestFitVoigtPeaks:
    def test_single_peak_converges_with_good_fit(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=300, peaks=((1000.0, 1000.0, 50.0),))
        peak_defs = [PeakDefinition(center=990.0, intensity=1.0, width_fwhm=60.0)]

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
            PeakDefinition(center=790.0, intensity=1.0, width_fwhm=45.0),
            PeakDefinition(center=1310.0, intensity=1.0, width_fwhm=65.0),
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
        peak_defs = [PeakDefinition(center=float(c), intensity=1.0, width_fwhm=20.0) for c in range(11)]
        with pytest.raises(ValueError):
            fit_voigt_peaks(x, y, peak_defs, mode="Raman")

    def test_mismatched_lengths_raise(self):
        x = np.linspace(0, 10, 100)
        y = np.ones(50)
        peak_defs = [PeakDefinition(center=5.0, intensity=1.0, width_fwhm=1.0)]
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
            PeakDefinition(center=100.0, intensity=1.0, width_fwhm=10.0, label="A"),
            PeakDefinition(center=500.0, intensity=1.0, width_fwhm=10.0, label="B"),
        ]
        assert detect_overlapping_peaks(peaks, merge_threshold=2.0) == []

    def test_warns_for_close_peaks(self):
        peaks = [
            PeakDefinition(center=100.0, intensity=1.0, width_fwhm=20.0, label="A"),
            PeakDefinition(center=105.0, intensity=1.0, width_fwhm=20.0, label="B"),
        ]
        warnings = detect_overlapping_peaks(peaks, merge_threshold=2.0)
        assert len(warnings) == 1
        assert "A" in warnings[0] and "B" in warnings[0]


class TestVoigtFwhm:
    """A Voigt's width comes from both of its components. Reporting
    2.355*sigma described only the Gaussian half and understated every width
    in the app by 60-110%."""

    def _measured_fwhm(self, sigma, gamma):
        """Half-maximum width read off an actual Voigt curve, on a grid fine
        enough that the reading is the reference and not the approximation."""
        from lmfit.models import VoigtModel

        x = np.linspace(-400.0, 400.0, 400001)
        curve = VoigtModel().eval(x=x, center=0.0, amplitude=1.0, sigma=sigma, gamma=gamma)
        above = np.where(curve >= curve.max() / 2.0)[0]
        return float(x[above[-1]] - x[above[0]])

    def test_pure_gaussian_reduces_to_the_gaussian_width(self):
        assert voigt_fwhm(10.0, 0.0) == pytest.approx(2.3548 * 10.0, rel=1e-3)

    def test_pure_lorentzian_reduces_to_twice_gamma(self):
        assert voigt_fwhm(0.0, 7.0) == pytest.approx(14.0, rel=1e-3)

    @pytest.mark.parametrize("sigma,gamma", [(2.0, 3.0), (9.0, 11.0), (1.9, 3.0), (0.5, 5.0), (5.0, 0.5)])
    def test_matches_the_measured_width_of_a_real_voigt_curve(self, sigma, gamma):
        assert voigt_fwhm(sigma, gamma) == pytest.approx(self._measured_fwhm(sigma, gamma), rel=0.005)

    def test_always_at_least_the_gaussian_only_value(self):
        """The old formula was a lower bound, never an estimate."""
        for sigma, gamma in ((2.0, 3.0), (9.0, 11.0), (0.7, 1.5)):
            assert voigt_fwhm(sigma, gamma) > 2.355 * sigma

    def test_a_fitted_peak_reports_the_width_of_the_curve_it_drew(self):
        """End to end: fit a synthetic peak, then check the reported FWHM
        against its own component curve."""
        x = np.linspace(900.0, 1100.0, 2000)
        from lmfit.models import VoigtModel
        y = VoigtModel().eval(x=x, center=1000.0, amplitude=5000.0, sigma=4.0, gamma=3.0)

        result = fit_voigt_peaks(x, y, [PeakDefinition(center=1000.0, intensity=1.0, width_fwhm=15.0)], mode="Raman")
        peak = result.fitted_peaks[0]

        curve = peak.component_curve
        above = np.where(curve >= curve.max() / 2.0)[0]
        measured = float(x[above[-1]] - x[above[0]])

        assert peak.width_fwhm == pytest.approx(measured, rel=0.02)


class TestVoigtFwhmStderr:
    def test_zero_uncertainty_in_gives_zero_out(self):
        assert voigt_fwhm_stderr(2.0, 3.0, 0.0, 0.0) == 0.0

    def test_anticorrelation_shrinks_the_uncertainty(self):
        """sigma and gamma trade off against each other, so each is poorly
        determined alone while their sum is not. Ignoring that is what quoted
        a width of 2.07 +/- 133.29."""
        quadrature = voigt_fwhm_stderr(2.0, 3.0, 1.0, 1.5, correlation=None)
        with_correl = voigt_fwhm_stderr(2.0, 3.0, 1.0, 1.5, correlation=-0.92)

        assert with_correl < quadrature

    def test_degenerate_widths_do_not_divide_by_zero(self):
        assert voigt_fwhm_stderr(0.0, 0.0, 1.0, 1.0) == 0.0

    def test_grows_with_the_input_uncertainty(self):
        small = voigt_fwhm_stderr(2.0, 3.0, 0.1, 0.1)
        large = voigt_fwhm_stderr(2.0, 3.0, 1.0, 1.0)

        assert large > small > 0


class TestIntensityMaxIsAnIntensity:
    """The ceiling on a peak is expressed in intensity -- the curve's
    maximum -- and only becomes an area on the way into lmfit. It was called
    amplitude_max, which read as lmfit's amplitude, an area, and was neither."""

    def test_auto_bound_is_five_times_the_data_maximum(self):
        peak = PeakDefinition(center=250.0, intensity=1.0, width_fwhm=4.0)
        peak.calculate_auto_bounds("Raman", x_range=(0.0, 400.0), y_max=120.0, spectral_resolution=0.5)

        assert peak.intensity_max == 5.0 * 120.0

    def test_the_old_names_are_gone(self):
        peak = PeakDefinition(center=250.0, intensity=1.0, width_fwhm=4.0)

        assert not hasattr(peak, "amplitude_max")
        assert not hasattr(peak, "height_max")

    def test_a_peak_may_reach_that_intensity_but_not_exceed_it(self):
        """End to end: a peak taller than the ceiling gets clipped to it."""
        x = np.linspace(200.0, 300.0, 800)
        from lmfit.models import VoigtModel
        y = VoigtModel().eval(x=x, center=250.0, amplitude=1000.0, sigma=2.0, gamma=1.0)

        result = fit_voigt_peaks(x, y, [PeakDefinition(center=250.0, intensity=1.0, width_fwhm=5.0)], mode="Raman")
        intensity = float(np.max(result.fitted_peaks[0].component_curve))

        assert intensity <= 5.0 * float(np.max(y)) * 1.001
