"""Unit tests for modules.spectra.processing.peak_metrics (per-peak numbers + aggregation)."""

import numpy as np

from modules.spectra.models.peak import FitResult, FittedPeak
from modules.spectra.processing.peak_metrics import (
    aggregate_fit_results,
    aggregate_raw_peak_stats,
    compute_peak_intensity_ratio,
    peak_intensity,
    peak_intensity_and_stderr,
    raw_peak_stats,
)


def _peak(label, center, intensity, width_fwhm, area=None):
    """A fitted peak whose component curve peaks at `intensity`.

    `area` is the area under the peak, a different quantity. It defaults to a
    value clearly unlike the intensity so that anything reading the wrong one
    fails loudly rather than looking plausible.
    """
    curve = np.zeros(10)
    curve[5] = intensity
    return FittedPeak(
        label=label, center=center, center_stderr=0.1,
        area=intensity * 7.0 if area is None else area,
        area_stderr=1.0,
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
        assert stat.intensity_mean == 11000.0
        assert stat.intensity_std == np.std([10000.0, 12000.0], ddof=1)

    def test_single_fit_has_zero_std(self):
        fits = [_fit_result([_peak("Si", 520.0, 5000.0, 8.0)])]
        stats = aggregate_fit_results(fits)

        assert stats[0].n == 1
        assert stats[0].center_std == 0.0
        assert stats[0].intensity_std == 0.0
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

    def test_reports_intensity_not_the_area(self):
        """The two differ by FWHM x 1.064. Reporting area under a heading the
        CSV uses for intensity is what made the .pptx disagree with every other
        surface in the app."""
        fits = [_fit_result([_peak("LA", 130.0, intensity=36.0, width_fwhm=22.0, area=1800.0)])]

        assert aggregate_fit_results(fits)[0].intensity_mean == 36.0


class TestComputePeakIntensityRatio:
    def _pair(self, la_intensity, e2g_intensity, **kwargs):
        return _fit_result([
            _peak("LA", 130.0, la_intensity, 20.0, **kwargs),
            _peak("E2g+A1g", 250.0, e2g_intensity, 4.0),
        ])

    def test_uses_intensities_not_areas(self):
        """LA is ~6x broader than E2g+A1g here, so the area ratio and the
        intensity ratio are nothing like each other."""
        fits = [_fit_result([
            _peak("LA", 130.0, intensity=10.0, width_fwhm=20.0, area=900.0),
            _peak("E2g+A1g", 250.0, intensity=100.0, width_fwhm=4.0, area=300.0),
        ])]
        median, _mad, _n = compute_peak_intensity_ratio(fits, "LA", "E2g+A1g")

        assert median == 0.1  # intensities, 10/100
        assert median != 900.0 / 300.0  # not the area ratio

    def test_ratio_formed_per_point_not_from_the_two_means(self):
        fits = [self._pair(100.0, 200.0), self._pair(300.0, 100.0)]  # ratios 0.5 and 3.0
        median, _mad, n = compute_peak_intensity_ratio(fits, "LA", "E2g+A1g")

        assert n == 2
        assert median == np.median([0.5, 3.0])
        # mean(LA)/mean(E2g) would be 200/150 = 1.333
        assert median != (200.0 / 150.0)

    def test_median_resists_one_badly_fitted_point(self):
        """A ratio of two fitted quantities is exactly where one bad point
        drags a mean somewhere no measurement supports."""
        fits = [self._pair(50.0, 100.0), self._pair(50.0, 100.0),
                self._pair(50.0, 100.0), self._pair(500.0, 100.0)]
        median, _mad, n = compute_peak_intensity_ratio(fits, "LA", "E2g+A1g")

        assert n == 4
        assert median == 0.5           # the three consistent points
        assert np.mean([0.5, 0.5, 0.5, 5.0]) == 1.625  # what the mean would have said

    def test_spread_is_the_median_absolute_deviation(self):
        fits = [self._pair(40.0, 100.0), self._pair(50.0, 100.0), self._pair(70.0, 100.0)]
        _median, mad, _n = compute_peak_intensity_ratio(fits, "LA", "E2g+A1g")

        assert mad == np.median(np.abs(np.array([0.4, 0.5, 0.7]) - 0.5))

    def test_single_point_has_zero_spread(self):
        median, mad, n = compute_peak_intensity_ratio([self._pair(100.0, 200.0)], "LA", "E2g+A1g")

        assert (median, mad, n) == (0.5, 0.0, 1)

    def test_points_missing_either_peak_are_skipped(self):
        fits = [self._pair(100.0, 200.0), _fit_result([_peak("LA", 130.0, 300.0, 20.0)])]
        median, _mad, n = compute_peak_intensity_ratio(fits, "LA", "E2g+A1g")

        assert n == 1
        assert median == 0.5

    def test_a_zero_denominator_is_skipped_rather_than_dividing_by_zero(self):
        fits = [self._pair(100.0, 200.0), self._pair(100.0, 0.0)]
        median, _mad, n = compute_peak_intensity_ratio(fits, "LA", "E2g+A1g")

        assert n == 1
        assert median == 0.5

    def test_no_point_has_both_labels_returns_none(self):
        fits = [_fit_result([_peak("Exciton", 766.0, 10000.0, 25.0)])]

        assert compute_peak_intensity_ratio(fits, "LA", "E2g+A1g") is None

    def test_empty_input_returns_none(self):
        assert compute_peak_intensity_ratio([], "LA", "E2g+A1g") is None


class TestQuantityNamingIsUnambiguous:
    """Two quantities, two names everywhere: the curve's maximum is
    "intensity", the area under it is "area". The .pptx once reported the area
    under a heading the CSV used for the maximum. Neither "amplitude" nor
    "height" names either quantity any more, so the two can't be silently
    swapped again."""

    def test_fitted_peak_names_neither_quantity_amplitude(self):
        peak = _peak("LA", 130.0, intensity=10.0, width_fwhm=20.0)

        assert not hasattr(peak, "amplitude")
        assert not hasattr(peak, "amplitude_stderr")
        assert peak.area == 70.0  # the integrated quantity, named for what it is

    def test_peak_stat_reports_intensity_under_that_name(self):
        fits = [_fit_result([_peak("LA", 130.0, intensity=36.0, width_fwhm=22.0)])]
        stat = aggregate_fit_results(fits)[0]

        assert not hasattr(stat, "amplitude_mean")
        assert not hasattr(stat, "height_mean")
        assert stat.intensity_mean == 36.0

    def test_peak_definition_names_its_ceiling_intensity_max(self):
        from modules.spectra.models.peak import PeakDefinition

        peak_def = PeakDefinition(center=130.0, intensity=1.0, width_fwhm=20.0)

        assert not hasattr(peak_def, "amplitude_max")
        assert not hasattr(peak_def, "height_max")
        assert hasattr(peak_def, "intensity_max")


class TestPeakIntensityAndStderr:
    def test_intensity_comes_from_the_component_curve_not_the_area(self):
        curve = np.array([0.0, 25.0, 100.0, 25.0, 0.0])
        peak = FittedPeak(
            label="LA", center=250.0, center_stderr=0.1,
            area=1000.0, area_stderr=50.0,
            width_fwhm=10.0, width_stderr=0.1, shape=0.3, component_curve=curve,
        )

        intensity, stderr = peak_intensity_and_stderr(peak)
        assert intensity == 100.0
        # 50 rescaled by the same intensity/area ratio = 100/1000
        assert stderr == 5.0
        assert peak_intensity(peak) == 100.0

    def test_falls_back_to_the_area_when_no_component_curve(self):
        peak = FittedPeak(
            label="LA", center=250.0, center_stderr=0.1,
            area=42.0, area_stderr=3.0,
            width_fwhm=10.0, width_stderr=0.1, shape=0.3, component_curve=None,
        )

        assert peak_intensity_and_stderr(peak) == (42.0, 3.0)

    def test_zero_area_gives_zero_stderr_rather_than_dividing_by_zero(self):
        peak = FittedPeak(
            label="Flat", center=250.0, center_stderr=0.1,
            area=0.0, area_stderr=5.0,
            width_fwhm=10.0, width_stderr=0.1, shape=0.3,
            component_curve=np.array([0.0, 1.0, 0.0]),
        )

        intensity, stderr = peak_intensity_and_stderr(peak)
        assert intensity == 1.0
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


class _Spectrum:
    """Just the `processed_data.X/.Y` that aggregate_raw_peak_stats reads."""

    class _Data:
        def __init__(self, x, y):
            self.X, self.Y = x, y

    def __init__(self, x, y):
        self.processed_data = self._Data(x, y)


def _pl_spectrum(peak_intensity_value, center, half_width=1.0):
    """A triangular emission peak of the given height at the given center."""
    x = np.arange(center - 4.0, center + 4.01, 1.0)
    y = np.clip(peak_intensity_value * (1.0 - np.abs(x - center) / (2.0 * half_width)), 0.0, None)
    return _Spectrum(x, y)


class TestAggregateRawPeakStats:
    """The empirical PL row: measured off the processed spectrum, no fit."""

    def test_labelled_raw_so_it_matches_the_other_surfaces(self):
        stat = aggregate_raw_peak_stats([_pl_spectrum(1000.0, 766.0)])

        assert stat.label == "Raw"

    def test_averages_intensity_and_center_across_points(self):
        stats = aggregate_raw_peak_stats([
            _pl_spectrum(1000.0, 766.0),
            _pl_spectrum(2000.0, 768.0),
        ])

        assert stats.n == 2
        assert stats.intensity_mean == 1500.0
        assert stats.center_mean == 767.0
        assert stats.intensity_std == np.std([1000.0, 2000.0], ddof=1)
        assert stats.center_std == np.std([766.0, 768.0], ddof=1)

    def test_single_point_has_no_spread(self):
        stat = aggregate_raw_peak_stats([_pl_spectrum(1000.0, 766.0)])

        assert stat.n == 1
        assert stat.intensity_std == 0.0
        assert stat.center_std == 0.0
        assert stat.fwhm_std == 0.0

    def test_measures_a_width_at_half_maximum(self):
        stat = aggregate_raw_peak_stats([_pl_spectrum(1000.0, 766.0, half_width=1.0)])

        assert stat.fwhm_mean is not None
        assert stat.fwhm_mean > 0.0

    def test_unmeasurable_width_is_none_not_zero(self):
        """A flat spectrum has no half-maximum crossing. Reporting 0.0 would
        print a fake measurement; the renderer dashes a None instead."""
        flat = _Spectrum(np.arange(5.0), np.zeros(5))
        stat = aggregate_raw_peak_stats([flat])

        assert stat is not None          # the tallest point still exists
        assert stat.fwhm_mean is None
        assert stat.fwhm_std is None

    def test_width_is_none_when_only_some_points_could_be_measured(self):
        """Averaging the measurable subset while `n` claims the full count
        would report a width the sample never had."""
        stats = aggregate_raw_peak_stats([
            _pl_spectrum(1000.0, 766.0),
            _Spectrum(np.arange(5.0), np.zeros(5)),
        ])

        assert stats.n == 2
        assert stats.fwhm_mean is None

    def test_reads_processed_data_so_it_is_comparable_to_fitted_intensities(self):
        """The layer the fit sees, not the raw file: a baseline-corrected
        spectrum, so no baseline offset inflates the reported intensity."""
        spectrum = _pl_spectrum(1000.0, 766.0)
        spectrum.processed_data.Y = spectrum.processed_data.Y + 0.0  # already corrected

        assert aggregate_raw_peak_stats([spectrum]).intensity_mean == 1000.0

    def test_no_spectra_returns_none(self):
        assert aggregate_raw_peak_stats([]) is None

    def test_empty_spectra_return_none(self):
        assert aggregate_raw_peak_stats([_Spectrum(np.array([]), np.array([]))]) is None
