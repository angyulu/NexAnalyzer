"""Unit tests for modules.spectra.processing.peak_metrics (per-peak numbers + aggregation)."""

import numpy as np

from modules.spectra.models.peak import FitResult, FittedPeak
from modules.spectra.processing.peak_metrics import (
    aggregate_fit_results,
    compute_peak_amplitude_ratio,
    peak_height,
    peak_height_and_stderr,
    raw_peak_stats,
)


def _peak(label, center, amplitude, width_fwhm):
    return FittedPeak(
        label=label, center=center, center_stderr=0.1,
        amplitude=amplitude, amplitude_stderr=1.0,
        width_fwhm=width_fwhm, width_stderr=0.1,
        shape=0.3, component_curve=np.zeros(10),
    )


def _fit_result(peaks):
    return FitResult(
        success=True, fitted_peaks=peaks,
        total_fit_curve=np.zeros(10), residuals=np.zeros(10),
        chi_squared=1.0, r_squared=0.99, convergence_time=0.1,
    )


class TestAggregateFitResults:
    def test_mean_and_std_across_multiple_fits(self):
        fits = [
            _fit_result([_peak("Exciton", 766.0, 10000.0, 25.0)]),
            _fit_result([_peak("Exciton", 768.0, 12000.0, 27.0)]),
        ]
        stats = aggregate_fit_results(fits)

        assert len(stats) == 1
        stat = stats[0]
        assert stat.label == "Exciton"
        assert stat.n == 2
        assert stat.center_mean == 767.0
        assert stat.center_std == np.std([766.0, 768.0], ddof=1)

    def test_single_fit_has_zero_std(self):
        fits = [_fit_result([_peak("Si", 520.0, 5000.0, 8.0)])]
        stats = aggregate_fit_results(fits)

        assert stats[0].n == 1
        assert stats[0].center_std == 0.0
        assert stats[0].amplitude_std == 0.0
        assert stats[0].fwhm_std == 0.0

    def test_multiple_labels_preserve_first_seen_order(self):
        fits = [
            _fit_result([_peak("Exciton", 766.0, 10000.0, 25.0), _peak("Trion", 785.0, 3000.0, 45.0)]),
            _fit_result([_peak("Exciton", 767.0, 11000.0, 26.0), _peak("Trion", 786.0, 3100.0, 46.0)]),
        ]
        stats = aggregate_fit_results(fits)

        assert [s.label for s in stats] == ["Exciton", "Trion"]

    def test_asymmetric_peak_presence_gives_correct_n_per_label(self):
        fits = [
            _fit_result([_peak("Exciton", 766.0, 10000.0, 25.0), _peak("Trion", 785.0, 3000.0, 45.0)]),
            _fit_result([_peak("Exciton", 767.0, 11000.0, 26.0)]),  # no Trion this point
        ]
        stats = {s.label: s for s in aggregate_fit_results(fits)}

        assert stats["Exciton"].n == 2
        assert stats["Trion"].n == 1

    def test_empty_input_returns_empty_list(self):
        assert aggregate_fit_results([]) == []


class TestComputePeakAmplitudeRatio:
    def test_ratio_averaged_per_point_not_ratio_of_means(self):
        fits = [
            _fit_result([_peak("LA", 130.0, 100.0, 20.0), _peak("E2g+A1g", 250.0, 200.0, 4.0)]),  # ratio 0.5
            _fit_result([_peak("LA", 130.0, 300.0, 20.0), _peak("E2g+A1g", 250.0, 100.0, 4.0)]),  # ratio 3.0
        ]
        mean, std, n = compute_peak_amplitude_ratio(fits, "LA", "E2g+A1g")

        assert n == 2
        assert mean == (0.5 + 3.0) / 2  # per-point average, not mean(LA)/mean(E2g)
        assert std == np.std([0.5, 3.0], ddof=1)

    def test_single_point_has_zero_std(self):
        fits = [_fit_result([_peak("LA", 130.0, 100.0, 20.0), _peak("E2g+A1g", 250.0, 200.0, 4.0)])]
        mean, std, n = compute_peak_amplitude_ratio(fits, "LA", "E2g+A1g")

        assert n == 1
        assert mean == 0.5
        assert std == 0.0

    def test_points_missing_either_peak_are_skipped(self):
        fits = [
            _fit_result([_peak("LA", 130.0, 100.0, 20.0), _peak("E2g+A1g", 250.0, 200.0, 4.0)]),
            _fit_result([_peak("LA", 130.0, 300.0, 20.0)]),  # no E2g+A1g this point
        ]
        mean, std, n = compute_peak_amplitude_ratio(fits, "LA", "E2g+A1g")

        assert n == 1
        assert mean == 0.5

    def test_no_point_has_both_labels_returns_none(self):
        fits = [_fit_result([_peak("Exciton", 766.0, 10000.0, 25.0)])]

        assert compute_peak_amplitude_ratio(fits, "LA", "E2g+A1g") is None

    def test_empty_input_returns_none(self):
        assert compute_peak_amplitude_ratio([], "LA", "E2g+A1g") is None


class TestPeakHeightAndStderr:
    def test_height_comes_from_the_component_curve_not_the_amplitude(self):
        curve = np.array([0.0, 25.0, 100.0, 25.0, 0.0])
        peak = FittedPeak(
            label="LA", center=250.0, center_stderr=0.1,
            amplitude=1000.0, amplitude_stderr=50.0,
            width_fwhm=10.0, width_stderr=0.1, shape=0.3, component_curve=curve,
        )

        height, stderr = peak_height_and_stderr(peak)
        assert height == 100.0
        # 50 rescaled by height/amplitude = 100/1000
        assert stderr == 5.0
        assert peak_height(peak) == 100.0

    def test_falls_back_to_amplitude_when_no_component_curve(self):
        peak = FittedPeak(
            label="LA", center=250.0, center_stderr=0.1,
            amplitude=42.0, amplitude_stderr=3.0,
            width_fwhm=10.0, width_stderr=0.1, shape=0.3, component_curve=None,
        )

        assert peak_height_and_stderr(peak) == (42.0, 3.0)

    def test_zero_amplitude_gives_zero_stderr_rather_than_dividing_by_zero(self):
        peak = FittedPeak(
            label="Flat", center=250.0, center_stderr=0.1,
            amplitude=0.0, amplitude_stderr=5.0,
            width_fwhm=10.0, width_stderr=0.1, shape=0.3,
            component_curve=np.array([0.0, 1.0, 0.0]),
        )

        height, stderr = peak_height_and_stderr(peak)
        assert height == 1.0
        assert stderr == 0.0


class TestRawPeakStats:
    def test_measures_max_position_and_width_at_half_max(self):
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        y = np.array([0.0, 50.0, 100.0, 50.0, 0.0])

        stats = raw_peak_stats(x, y)
        assert stats.intensity == 100.0
        assert stats.center == 2.0
        assert stats.fwhm == 2.0  # x=1 to x=3 are >= half max

    def test_empty_spectrum_returns_none(self):
        assert raw_peak_stats(np.array([]), np.array([])) is None

    def test_non_positive_signal_has_no_measurable_width(self):
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 0.0, 0.0])

        stats = raw_peak_stats(x, y)
        assert stats.intensity == 0.0
        assert stats.fwhm is None
