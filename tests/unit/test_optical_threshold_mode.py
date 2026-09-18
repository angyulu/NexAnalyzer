"""
`OpticalParams.threshold_mode` (v4.6.0): the preset-side switch between the
adaptive, absolute and midpoint rules.

What matters here is the contract with v4.4.0 presets. `WSe2` carries an
`abs_threshold_*` pair and no mode, and must keep running the absolute rule;
a preset that sets the mode explicitly must get that mode even if it also
carries a pair; and "absolute" with no pair is a validation error, because
there is no default contrast to fall back on.
"""

import pytest

from modules.optical.processing.contrast import THRESHOLD_MODES
from modules.spectra.models.preset import OpticalParams


class TestAsKwargs:
    def test_unset_passes_nothing_so_contrast_py_decides(self):
        assert "threshold_mode" not in OpticalParams().as_kwargs()

    def test_a_set_mode_reaches_analyse_frame_by_name(self):
        assert OpticalParams(threshold_mode="midpoint").as_kwargs() == {
            "threshold_mode": "midpoint"
        }

    def test_the_v4_4_0_pair_still_travels_without_a_mode(self):
        kwargs = OpticalParams(abs_threshold_below=6.0,
                               abs_threshold_above=4.25).as_kwargs()
        assert kwargs == {"abs_threshold": (6.0, 4.25)}

    def test_a_pair_and_a_mode_both_travel(self):
        """contrast.resolve_threshold_mode gives the mode precedence; the
        preset's job is only to hand both over."""
        kwargs = OpticalParams(abs_threshold_below=6.0, abs_threshold_above=4.25,
                               threshold_mode="midpoint").as_kwargs()
        assert kwargs["abs_threshold"] == (6.0, 4.25)
        assert kwargs["threshold_mode"] == "midpoint"


class TestValidate:
    @pytest.mark.parametrize("mode", THRESHOLD_MODES)
    def test_every_known_mode_is_accepted(self, mode):
        params = OpticalParams(threshold_mode=mode,
                               abs_threshold_below=6.0, abs_threshold_above=4.25)
        assert params.validate() == []

    def test_an_unknown_mode_is_named_in_the_error(self):
        errors = OpticalParams(threshold_mode="otsu").validate()
        assert len(errors) == 1
        assert "otsu" in errors[0]
        assert "midpoint" in errors[0]

    def test_absolute_without_a_pair_is_rejected(self):
        errors = OpticalParams(threshold_mode="absolute").validate()
        assert len(errors) == 1
        assert "abs_threshold_below" in errors[0]

    def test_midpoint_needs_no_pair(self):
        assert OpticalParams(threshold_mode="midpoint").validate() == []


class TestRoundTrip:
    def test_the_mode_survives_to_dict_and_back(self):
        params = OpticalParams(nsigma=4.0, threshold_mode="midpoint")
        again = OpticalParams.from_dict(params.to_dict())
        assert again == params
        assert again.to_dict() == {"nsigma": 4.0, "threshold_mode": "midpoint"}

    def test_unset_is_absent_from_the_file_not_null(self):
        assert "threshold_mode" not in OpticalParams(nsigma=4.0).to_dict()
