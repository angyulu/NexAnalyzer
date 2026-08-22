"""Unit tests for modules.spectra.processing.peak_metrics (per-peak numbers + aggregation)."""

import numpy as np

from modules.spectra.models.peak import FitResult, FittedPeak
from modules.spectra.processing.peak_metrics import (
    aggregate_fit_results,
    compute_peak_height_ratio,
    peak_height,
    peak_height_and_stderr,
    raw_peak_stats,
)


def _peak(label, center, height, width_fwhm, amplitude=None):
    """A fitted peak whose component curve peaks at `height`.

    `amplitude` is lmfit's integrated intensity, a different quantity. It
    defaults to a value clearly unlike the height so that anything reading the
    wrong one fails loudly rather than looking plausible.
    """
    curve = np.zeros(10)
    curve[5] = height
    return FittedPeak(
        label=label, center=center, center_stderr=0.1,
        amplitude=height * 7.0 if amplitude is None else amplitude,
        amplitude_stderr=1.0,
        width_fwhm=width_fwhm, width_stderr=0.1,
        shape=0.3, component_curve=curve,
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
        assert stat.height_mean == 11000.0
        assert stat.height_std == np.std([10000.0, 12000.0], ddof=1)

    def test_single_fit_has_zero_std(self):
        fits = [_fit_result([_peak("Si", 520.0, 5000.0, 8.0)])]
        stats = aggregate_fit_results(fits)

        assert stats[0].n == 1
        assert stats[0].center_std == 0.0
        assert stats[0].height_std == 0.0
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

    def test_reports_height_not_lmfit_s_integrated_amplitude(self):
        """The two differ by FWHM x 1.064. Reporting area under a heading the
        CSV uses for height is what made the .pptx disagree with every other
        surface in the app."""
        fits = [_fit_result([_peak("LA", 130.0, height=36.0, width_fwhm=22.0, amplitude=1800.0)])]

        assert aggregate_fit_results(fits)[0].height_mean == 36.0


class TestComputePeakHeightRatio:
    def _pair(self, la_height, e2g_height, **kwargs):
        return _fit_result([
            _peak("LA", 130.0, la_height, 20.0, **kwargs),
            _peak("E2g+A1g", 250.0, e2g_height, 4.0),
        ])

    def test_uses_heights_not_lmfit_s_integrated_amplitudes(self):
        """LA is ~6x broader than E2g+A1g here, so the area ratio and the
        height ratio are nothing like each other."""
        fits = [_fit_result([
            _peak("LA", 130.0, height=10.0, width_fwhm=20.0, amplitude=900.0),
            _peak("E2g+A1g", 250.0, height=100.0, width_fwhm=4.0, amplitude=300.0),
        ])]
        median, _mad, _n = compute_peak_height_ratio(fits, "LA", "E2g+A1g")

        assert median == 0.1  # heights, 10/100
        assert median != 900.0 / 300.0  # not the integrated-intensity ratio

    def test_ratio_formed_per_point_not_from_the_two_means(self):
        fits = [self._pair(100.0, 200.0), self._pair(300.0, 100.0)]  # ratios 0.5 and 3.0
        median, _mad, n = compute_peak_height_ratio(fits, "LA", "E2g+A1g")

        assert n == 2
        assert median == np.median([0.5, 3.0])
        # mean(LA)/mean(E2g) would be 200/150 = 1.333
        assert median != (200.0 / 150.0)

    def test_median_resists_one_badly_fitted_point(self):
        """A ratio of two fitted quantities is exactly where one bad point
        drags a mean somewhere no measurement supports."""
        fits = [self._pair(50.0, 100.0), self._pair(50.0, 100.0),
                self._pair(50.0, 100.0), self._pair(500.0, 100.0)]
        median, _mad, n = compute_peak_height_ratio(fits, "LA", "E2g+A1g")

        assert n == 4
        assert median == 0.5           # the three consistent points
        assert np.mean([0.5, 0.5, 0.5, 5.0]) == 1.625  # what the mean would have said

    def test_spread_is_the_median_absolute_deviation(self):
        fits = [self._pair(40.0, 100.0), self._pair(50.0, 100.0), self._pair(70.0, 100.0)]
        _median, mad, _n = compute_peak_height_ratio(fits, "LA", "E2g+A1g")

        assert mad == np.median(np.abs(np.array([0.4, 0.5, 0.7]) - 0.5))

    def test_single_point_has_zero_spread(self):
        median, mad, n = compute_peak_height_ratio([self._pair(100.0, 200.0)], "LA", "E2g+A1g")

        assert (median, mad, n) == (0.5, 0.0, 1)

    def test_points_missing_either_peak_are_skipped(self):
        fits = [self._pair(100.0, 200.0), _fit_result([_peak("LA", 130.0, 300.0, 20.0)])]
        median, _mad, n = compute_peak_height_ratio(fits, "LA", "E2g+A1g")

        assert n == 1
        assert median == 0.5

    def test_a_zero_denominator_is_skipped_rather_than_dividing_by_zero(self):
        fits = [self._pair(100.0, 200.0), self._pair(100.0, 0.0)]
        median, _mad, n = compute_peak_height_ratio(fits, "LA", "E2g+A1g")

        assert n == 1
        assert median == 0.5

    def test_no_point_has_both_labels_returns_none(self):
        fits = [_fit_result([_peak("Exciton", 766.0, 10000.0, 25.0)])]

        assert compute_peak_height_ratio(fits, "LA", "E2g+A1g") is None

    def test_empty_input_returns_none(self):
        assert compute_peak_height_ratio([], "LA", "E2g+A1g") is None


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
