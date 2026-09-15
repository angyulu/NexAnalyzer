"""
Unit tests for the adaptive per-wafer threshold pair.

All synthetic: pools are drawn from known mixtures so every expectation is a
statement about what the placement rules must do, not about any wafer. The
202609 wafer-level behaviour (HADH51 moving to +2.46, HADG38 and HADH26
keeping the preset pair, HADH48 flagged) was validated against the archive on
2026-09-15 and is recorded in adaptive.py's module docstring; re-running it
needs the archive, so it is not a unit test.
"""

import numpy as np
import pytest

from modules.optical.processing.adaptive import (
    GATE_RATIO,
    AdaptivePair,
    derive_pair_from_pool,
)
from modules.spectra.models.preset import OpticalParams
from modules.spectra.utils.preset_staleness import optical_fingerprint

BASE = (6.0, 4.25)
RNG = np.random.default_rng(7)


def _pool(*components):
    """Concatenate (mean, sigma, n) gaussian draws into one contrast pool."""
    return np.concatenate([RNG.normal(m, s, n) for m, s, n in components])


# --------------------------------------------------------------- placement
def test_unimodal_film_keeps_the_base_pair():
    """No population, no evidence, no movement: a clean film must come out
    with the preset pair byte-for-byte, both sides sourced 'default'."""
    result = derive_pair_from_pool(_pool((0, 1.0, 200_000)), 0.9, BASE)
    assert result.pair == BASE
    assert result.below_source == "default"
    assert result.above_source == "default"
    assert result.moved is False
    assert result.below_measurable and result.above_measurable


def test_separated_population_moves_the_cut_to_the_valley():
    """A resolvable population one layer step down, with a real valley in
    between, must pull the below cut off the base pair and inside the gap."""
    pool = _pool((0, 0.9, 180_000), (-8.0, 1.1, 20_000))
    result = derive_pair_from_pool(pool, 0.8, BASE)
    assert result.below_source in ("valley", "crossing")
    assert 2.0 < result.pair[0] < 8.0
    assert result.pair[1] == BASE[1]            # nothing above: base kept
    assert result.moved is True
    assert result.below_measurable


def test_moved_cut_never_sits_inside_the_noise():
    """Whatever the fit says, a cut may not come closer to the mode than
    GATE_RATIO robust sigmas -- the QC summary's own usability rule."""
    pool = _pool((0, 1.0, 180_000), (-8.0, 1.2, 20_000))
    result = derive_pair_from_pool(pool, 1.6, BASE)
    assert result.pair[0] / 1.6 >= GATE_RATIO - 1e-9


def test_tiny_population_without_a_valley_is_not_enough_evidence():
    """Half a percent of pixels smeared against the film's flank -- no dip in
    the pooled density -- may not move the cut: the crossing path demands
    substantial weight, and there is no valley to outrank it. (A tiny
    population WITH a real valley does move the cut, by design: an empirical
    dip is direct evidence, however small the population behind it.)"""
    pool = _pool((0, 1.0, 200_000), (3.0, 1.5, 1_000))
    result = derive_pair_from_pool(pool, 0.9, BASE)
    assert result.pair == BASE
    assert result.moved is False


def test_unresolvable_population_keeps_base_and_says_why():
    """A population buried in the film's own width cannot be thresholded at
    any value. The side must keep the base cut and name the reason, so the
    operator sees there is real mass the number does not resolve."""
    pool = _pool((0, 3.2, 160_000), (4.0, 3.0, 40_000))
    result = derive_pair_from_pool(pool, 1.5, BASE)
    assert result.pair[1] == BASE[1]
    assert result.above_source.startswith("default (")


def test_noise_swallowing_the_base_pair_is_not_measurable():
    """When even the preset cut sits under GATE_RATIO sigmas of frame noise,
    every percentage is segmentation noise: the side must be flagged, not
    silently reported. Mirrors HADG37/HADH48 in the 202609 archive."""
    result = derive_pair_from_pool(_pool((0, 4.5, 200_000)), 4.5, BASE)
    assert result.below_measurable is False
    assert result.above_measurable is False
    assert result.below_source == "NOT MEASURABLE"
    assert set(result.flags) == {"below NOT MEASURABLE", "above NOT MEASURABLE"}


def test_describe_carries_the_pair_and_the_flags():
    result = derive_pair_from_pool(_pool((0, 4.5, 100_000)), 4.5, BASE)
    text = result.describe()
    assert "-6.00/+4.25" in text
    assert "NOT MEASURABLE" in text


def test_derivation_is_deterministic():
    pool = _pool((0, 1.0, 150_000), (-8.0, 1.1, 15_000))
    first = derive_pair_from_pool(pool, 0.8, BASE)
    second = derive_pair_from_pool(pool, 0.8, BASE)
    assert first == second == AdaptivePair(**vars(first))


# ------------------------------------------------------------------ preset
def test_adaptive_is_the_default_when_the_pair_is_set():
    """Since v4.6.0 the flag is an opt-out: a preset that sets the abs pair
    runs adaptive unless it says `adaptive_threshold: false`."""
    pair = dict(abs_threshold_below=6.0, abs_threshold_above=4.25)
    assert OpticalParams(**pair).adaptive_enabled is True
    assert OpticalParams(**pair, adaptive_threshold=True).adaptive_enabled is True
    assert OpticalParams(**pair, adaptive_threshold=False).adaptive_enabled is False


def test_no_pair_means_no_adaptive_whatever_the_flag_says():
    """There is no base to derive from without the pair, so `adaptive_enabled`
    is False for the nsigma path -- unset, tuned, or even (invalidly) True."""
    assert OpticalParams().adaptive_enabled is False
    assert OpticalParams(nsigma=4.0).adaptive_enabled is False
    assert OpticalParams(adaptive_threshold=True).adaptive_enabled is False


def test_the_opt_out_survives_the_store_roundtrip():
    """False is a stored value, not an absence: it is the one state that must
    persist, because absent now means on."""
    params = OpticalParams(adaptive_threshold=False,
                           abs_threshold_below=6.0, abs_threshold_above=4.25)
    restored = OpticalParams.from_dict(params.to_dict())
    assert restored == params
    assert restored.adaptive_enabled is False


def test_adaptive_needs_the_base_pair():
    """The flag without the pair describes nothing: validate must say so."""
    params = OpticalParams(adaptive_threshold=True)
    assert any("adaptive_threshold" in e for e in params.validate())
    params = OpticalParams(adaptive_threshold=True,
                           abs_threshold_below=6.0, abs_threshold_above=4.25)
    assert params.validate() == []


def test_adaptive_is_not_passed_to_analyse_frame():
    """as_kwargs feeds analyse_frame, which has no adaptive argument: the QC
    Panel resolves the flag into a concrete pair before segmentation."""
    params = OpticalParams(adaptive_threshold=True,
                           abs_threshold_below=6.0, abs_threshold_above=4.25)
    kwargs = params.as_kwargs()
    assert "adaptive_threshold" not in kwargs
    assert kwargs["abs_threshold"] == (6.0, 4.25)


def test_adaptive_survives_the_store_roundtrip():
    params = OpticalParams(adaptive_threshold=True,
                           abs_threshold_below=6.0, abs_threshold_above=4.25)
    assert OpticalParams.from_dict(params.to_dict()) == params
    # Unset stays absent, so untouched preset files stay untouched.
    assert "adaptive_threshold" not in OpticalParams(nsigma=4.0).to_dict()


def test_toggling_adaptive_changes_the_optical_fingerprint():
    """The fingerprint is what tells the QC Panel a figure is stale; a method
    change that did not change it would leave a wrong figure on screen."""

    class _Preset:
        def __init__(self, params):
            self._params = params

        def optical_for(self, layer):
            return self._params

    adaptive = OpticalParams(abs_threshold_below=6.0, abs_threshold_above=4.25)
    pinned = OpticalParams(abs_threshold_below=6.0, abs_threshold_above=4.25,
                           adaptive_threshold=False)
    assert optical_fingerprint(_Preset(adaptive), "2L") != \
        optical_fingerprint(_Preset(pinned), "2L")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
