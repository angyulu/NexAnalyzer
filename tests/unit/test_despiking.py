"""Unit tests for modules.spectra.processing.despiking (cosmic-ray spike removal)."""

import numpy as np
import pytest

from modules.spectra.processing.despiking import (
    remove_spikes,
    count_spikes,
    spike_fraction,
    suggest_threshold,
)


class TestRemoveSpikes:
    def test_detects_and_replaces_spike(self):
        y = np.array([100., 102., 101., 99., 500., 98., 101., 100., 102., 99.])
        y_clean, mask = remove_spikes(y, threshold=6.0)

        assert mask.tolist() == [False, False, False, False, True, False, False, False, False, False]
        assert y_clean[4] == pytest.approx(100.0)
        # Non-spike points are untouched.
        np.testing.assert_array_equal(np.delete(y_clean, 4), np.delete(y, 4))

    def test_short_array_is_a_noop(self):
        """Arrays under 10 points skip detection entirely (despiking.py:83-85)."""
        y = np.array([100., 102., 500., 98., 101.])
        y_clean, mask = remove_spikes(y, threshold=6.0)

        assert not mask.any()
        np.testing.assert_array_equal(y_clean, y)

    def test_constant_signal_has_no_spikes(self):
        y = np.full(20, 100.0)
        y_clean, mask = remove_spikes(y, threshold=6.0)

        assert not mask.any()
        np.testing.assert_array_equal(y_clean, y)

    def test_threshold_out_of_range_raises(self):
        y = np.arange(20, dtype=float)
        with pytest.raises(ValueError):
            remove_spikes(y, threshold=2.0)
        with pytest.raises(ValueError):
            remove_spikes(y, threshold=31.0)

    def test_even_window_size_raises(self):
        y = np.arange(20, dtype=float)
        with pytest.raises(ValueError):
            remove_spikes(y, threshold=6.0, window_size=4)


class TestCountSpikes:
    def test_counts_true_values(self):
        mask = np.array([False, True, False, True, True])
        assert count_spikes(mask) == 3

    def test_no_spikes(self):
        mask = np.zeros(10, dtype=bool)
        assert count_spikes(mask) == 0


class TestSpikeFraction:
    def test_fraction_of_flagged_points(self):
        mask = np.array([True, False, False, False])
        assert spike_fraction(mask) == pytest.approx(0.25)

    def test_empty_mask_returns_zero(self):
        assert spike_fraction(np.array([], dtype=bool)) == 0.0


class TestSuggestThreshold:
    def test_returns_value_within_clamp_range(self):
        rng = np.random.default_rng(0)
        y = rng.normal(100, 5, size=200)
        suggested = suggest_threshold(y, target_fraction=0.01)
        assert 3.0 <= suggested <= 15.0

    def test_constant_signal_returns_default(self):
        y = np.full(50, 42.0)
        assert suggest_threshold(y) == 6.0
