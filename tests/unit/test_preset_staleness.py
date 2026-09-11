"""Unit tests for per-block preset fingerprinting.

The property that matters is *independence*: a Raman edit must change the Raman
fingerprint and leave the optical one alone, because the QC Panel throws away
whichever figures the changed fingerprint produced, and an OM segmentation
costs thirty seconds.
"""

from modules.spectra.models.preset import MaterialPreset, OpticalParams, TechniquePreset
from modules.spectra.models.preset import PeakTemplate
from modules.spectra.utils.preset_staleness import (
    optical_fingerprint,
    technique_fingerprint,
)


def _peak(label="E2g", center=250.0, color="#1f77b4"):
    return PeakTemplate(peak_label=label, center=center, center_tolerance=7.0,
                        width_fwhm=4.0, shape=0.3, color=color)


def _preset(**overrides):
    defaults = dict(
        material_name="WSe2",
        raman=TechniquePreset(despike_threshold=8.0, peak_templates=[_peak()]),
        optical={"2L": OpticalParams(nsigma=4.0, minpx=3)},
    )
    defaults.update(overrides)
    return MaterialPreset(**defaults)


class TestFingerprintsAreStable:
    def test_the_same_preset_fingerprints_the_same_way_twice(self):
        preset = _preset()

        assert technique_fingerprint(preset, "Raman") == technique_fingerprint(preset, "Raman")
        assert optical_fingerprint(preset, "2L") == optical_fingerprint(preset, "2L")

    def test_two_equal_presets_agree(self):
        assert technique_fingerprint(_preset(), "Raman") == technique_fingerprint(_preset(), "Raman")

    def test_a_missing_block_fingerprints_as_none(self):
        preset = _preset()

        assert technique_fingerprint(preset, "PL") is None
        assert technique_fingerprint(None, "Raman") is None
        assert optical_fingerprint(None, "2L") is None


class TestBlocksAreIndependent:
    """Editing one block must not invalidate the other's figures."""

    def test_a_raman_edit_leaves_the_optical_fingerprint_alone(self):
        before = _preset()
        after = _preset(
            raman=TechniquePreset(despike_threshold=8.0,
                                  peak_templates=[_peak(color="#ff0000")])
        )

        assert technique_fingerprint(before, "Raman") != technique_fingerprint(after, "Raman")
        assert optical_fingerprint(before, "2L") == optical_fingerprint(after, "2L")

    def test_an_optical_edit_leaves_the_raman_fingerprint_alone(self):
        before = _preset()
        after = _preset(optical={"2L": OpticalParams(nsigma=5.0, minpx=3)})

        assert optical_fingerprint(before, "2L") != optical_fingerprint(after, "2L")
        assert technique_fingerprint(before, "Raman") == technique_fingerprint(after, "Raman")

    def test_editing_one_layer_leaves_the_other_alone(self):
        before = _preset(optical={"1L": OpticalParams(nsigma=3.0),
                                  "2L": OpticalParams(nsigma=4.0)})
        after = _preset(optical={"1L": OpticalParams(nsigma=3.5),
                                 "2L": OpticalParams(nsigma=4.0)})

        assert optical_fingerprint(before, "1L") != optical_fingerprint(after, "1L")
        assert optical_fingerprint(before, "2L") == optical_fingerprint(after, "2L")


class TestFingerprintsTrackWhatActuallyChangesTheFigure:
    def test_the_layer_is_part_of_the_optical_fingerprint(self):
        """Switching 1L to 2L changes the class labels even when both blocks
        hold identical numbers, so it must invalidate the figure."""
        preset = _preset(optical={"1L": OpticalParams(nsigma=4.0, minpx=3),
                                  "2L": OpticalParams(nsigma=4.0, minpx=3)})

        assert optical_fingerprint(preset, "1L") != optical_fingerprint(preset, "2L")

    def test_an_untuned_layer_fingerprints_as_the_defaults(self):
        """And so agrees with any other untuned layer of the same name."""
        tuned = _preset()
        untuned = _preset(optical={})

        assert optical_fingerprint(untuned, "2L") == optical_fingerprint(
            MaterialPreset(material_name="Other"), "2L"
        )
        assert optical_fingerprint(tuned, "2L") != optical_fingerprint(untuned, "2L")

    def test_every_persisted_field_is_covered(self):
        """The fingerprint is taken over to_dict(), so a field added to the
        model cannot drift out of it."""
        base = _preset()
        for field, value in (("despike_threshold", 9.0),
                             ("baseline_algorithm", "ALS"),
                             ("x_range_enabled", True),
                             ("exclusion_ranges", "100-200")):
            block = TechniquePreset(despike_threshold=8.0, peak_templates=[_peak()])
            setattr(block, field, value)
            changed = _preset(raman=block)
            assert technique_fingerprint(base, "Raman") != technique_fingerprint(
                changed, "Raman"
            ), field
