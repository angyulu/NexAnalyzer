"""Unit tests for modules.spectra.processing.baseline (baseline correction algorithms)."""

import numpy as np
import pytest

from modules.spectra.processing.baseline import (
    apply_auto_shift,
    baseline_polynomial,
    baseline_polynomial_with_autoshift,
    baseline_polynomial_with_mask,
    baseline_als,
    baseline_als_with_autoshift,
    baseline_als_with_mask,
    baseline_rolling_ball,
    baseline_spline,
    baseline_airpls,
    calculate_baseline_quality_metrics,
)


class TestApplyAutoShift:
    def test_negative_values_are_shifted_positive(self):
        y = np.array([-50., -10., 100., 200.])
        y_shifted, shift = apply_auto_shift(y, epsilon=1.0)

        assert shift == pytest.approx(51.0)
        assert y_shifted.min() == pytest.approx(1.0)

    def test_already_positive_values_are_unshifted(self):
        y = np.array([1., 2., 3.])
        y_shifted, shift = apply_auto_shift(y)

        assert shift == 0.0
        np.testing.assert_array_equal(y_shifted, y)


class TestBaselinePolynomial:
    def test_flat_signal_gives_near_zero_corrected(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=200, peaks=(), baseline_offset=50.0)
        y_corr, baseline = baseline_polynomial(x, y, degree=1)

        assert baseline.shape == x.shape
        assert np.abs(y_corr).max() < 1.0

    def test_invalid_degree_raises(self):
        x = np.linspace(0, 10, 200)
        y = np.ones(200)
        with pytest.raises(ValueError):
            baseline_polynomial(x, y, degree=0)
        with pytest.raises(ValueError):
            baseline_polynomial(x, y, degree=11)

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            baseline_polynomial(np.arange(10.0), np.arange(5.0), degree=2)

    def test_with_autoshift_matches_unshifted_for_positive_data(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=200, peaks=(), baseline_slope=0.05, baseline_offset=50.0)
        y_corr_direct, baseline_direct = baseline_polynomial(x, y, degree=2)
        y_corr_shifted, baseline_shifted, shift = baseline_polynomial_with_autoshift(x, y, degree=2)

        assert shift == 0.0  # already positive, no shift needed
        np.testing.assert_allclose(y_corr_direct, y_corr_shifted, atol=1e-8)
        np.testing.assert_allclose(baseline_direct, baseline_shifted, atol=1e-8)

    def test_with_mask_excludes_peak_region(self, synthetic_spectrum):
        x, y = synthetic_spectrum(
            n_points=300, x_range=(0.0, 300.0), peaks=((150.0, 500.0, 20.0),),
            baseline_offset=10.0,
        )
        y_corr, baseline = baseline_polynomial_with_mask(x, y, degree=1, exclusions=[(120.0, 180.0)])
        assert baseline.shape == x.shape
        # Outside the excluded/peak region the corrected signal should be near flat.
        far_from_peak = (x < 100.0) | (x > 200.0)
        assert np.abs(y_corr[far_from_peak]).max() < 5.0

    def test_with_mask_too_few_points_raises(self):
        x = np.linspace(0, 10, 100)
        y = np.ones(100)
        # Excluding almost everything leaves too few points for a degree-5 fit.
        with pytest.raises(ValueError):
            baseline_polynomial_with_mask(x, y, degree=5, exclusions=[(0.0, 9.9)])


class TestBaselineAls:
    def test_returns_correct_shapes(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=150, peaks=(), baseline_offset=20.0)
        y_corr, baseline = baseline_als(x, y, lambda_=1e4, p=0.01, max_iter=10)
        assert y_corr.shape == x.shape
        assert baseline.shape == x.shape

    def test_invalid_lambda_raises(self):
        x = np.linspace(0, 10, 100)
        y = np.ones(100)
        with pytest.raises(ValueError):
            baseline_als(x, y, lambda_=1.0)

    def test_invalid_p_raises(self):
        x = np.linspace(0, 10, 100)
        y = np.ones(100)
        with pytest.raises(ValueError):
            baseline_als(x, y, p=0.5)

    def test_too_few_points_raises(self):
        x = np.linspace(0, 10, 5)
        y = np.ones(5)
        with pytest.raises(ValueError):
            baseline_als(x, y)

    def test_with_autoshift_handles_negative_data(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=150, peaks=(), baseline_offset=-30.0)
        y_corr, baseline, shift = baseline_als_with_autoshift(x, y, lambda_=1e4, p=0.01)
        assert shift > 0.0
        assert y_corr.shape == x.shape

    def test_with_mask_runs_with_exclusions(self, synthetic_spectrum):
        x, y = synthetic_spectrum(
            n_points=150, x_range=(0.0, 150.0), peaks=((75.0, 300.0, 15.0),), baseline_offset=10.0
        )
        y_corr, baseline = baseline_als_with_mask(x, y, lambda_=1e4, p=0.01, exclusions=[(60.0, 90.0)])
        assert baseline.shape == x.shape
class TestBaselineRollingBall:
    def test_returns_correct_shapes(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=200, x_range=(0.0, 1000.0), peaks=(), baseline_offset=10.0)
        y_corr, baseline = baseline_rolling_ball(x, y, radius=50.0)
        assert y_corr.shape == x.shape
        assert baseline.shape == x.shape

    def test_invalid_radius_raises(self):
        x = np.linspace(0, 10, 100)
        y = np.ones(100)
        with pytest.raises(ValueError):
            baseline_rolling_ball(x, y, radius=0)

    def test_radius_too_large_raises(self):
        x = np.linspace(0, 10, 100)
        y = np.ones(100)
        with pytest.raises(ValueError):
            baseline_rolling_ball(x, y, radius=1000)


class TestBaselineSpline:
    def test_returns_correct_shapes(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=200, peaks=(), baseline_offset=10.0)
        y_corr, baseline = baseline_spline(x, y)
        assert y_corr.shape == x.shape
        assert baseline.shape == x.shape

    def test_negative_smoothness_raises(self):
        x = np.linspace(0, 10, 100)
        y = np.ones(100)
        with pytest.raises(ValueError):
            baseline_spline(x, y, smoothness=-1.0)


class TestBaselineAirpls:
    def test_returns_correct_shapes(self, synthetic_spectrum):
        x, y = synthetic_spectrum(n_points=200, peaks=(), baseline_offset=10.0)
        y_corr, baseline = baseline_airpls(x, y, lambda_=1e5)
        assert y_corr.shape == x.shape
        assert baseline.shape == x.shape

    def test_invalid_lambda_raises(self):
        x = np.linspace(0, 10, 100)
        y = np.ones(100)
        with pytest.raises(ValueError):
            baseline_airpls(x, y, lambda_=1.0)


class TestBaselineQualityMetrics:
    def test_returns_expected_keys(self):
        y = np.array([10., 12., 11., 13., 10.])
        baseline = np.array([10., 10., 10., 10., 10.])
        metrics = calculate_baseline_quality_metrics(y, baseline)

        assert set(metrics.keys()) == {
            "residual_std", "residual_mean", "roughness", "peak_count", "baseline_range"
        }
        assert metrics["baseline_range"] == (10.0, 10.0)

    def test_perfect_baseline_has_zero_residual(self):
        y = np.array([1., 2., 3., 4., 5.])
        metrics = calculate_baseline_quality_metrics(y, y.copy())
        assert metrics["residual_std"] == pytest.approx(0.0)
        assert metrics["residual_mean"] == pytest.approx(0.0)
