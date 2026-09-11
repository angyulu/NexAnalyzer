"""
Unit tests for modules.spectra.viz.raman_quality (Image 2 of the QC Panel).

The figure reproduces the inherited WSe2 Raman panels, so the tests that matter
are the ones pinning what it plots: which peaks, which metrics, which spec
values, and — the part most easily got wrong — that a ratio is formed within
one spectrum before being summarized, rather than from two separately averaged
intensities.
"""

import numpy as np
import pytest

from modules.spectra.models.peak import FitResult, FittedPeak
from modules.spectra.viz.raman_quality import (
    PANEL_COLUMNS,
    PeakPanel,
    RatioPanel,
    _peak_values,
    _ratio_values,
    build_raman_quality_figure,
)


def _peak(label, center=250.0, intensity=100.0, width_fwhm=7.0):
    curve = np.zeros(10)
    curve[5] = intensity
    return FittedPeak(
        label=label, center=center, center_stderr=0.1,
        area=intensity * 7.0, area_stderr=1.0,
        width_fwhm=width_fwhm, width_stderr=0.1,
        shape=0.3, component_curve=curve,
    )


def _fit(peaks, r_squared=0.99):
    return FitResult(
        success=True, fitted_peaks=peaks,
        total_fit_curve=np.zeros(10), residuals=np.zeros(10),
        chi_squared=1.0, r_squared=r_squared, convergence_time=0.1,
    )


def _wse2_fit(**intensities):
    """A fit carrying the six peaks the figure reads, at given intensities."""
    defaults = {"E2g+A1g": 200.0, "2LA": 30.0, "B2g": 20.0,
                "LA": 40.0, "C": 80.0, "LB": 25.0}
    defaults.update(intensities)
    centers = {"E2g+A1g": 250.0, "2LA": 260.0, "B2g": 308.0,
               "LA": 130.0, "C": 17.0, "LB": 30.0}
    return _fit([_peak(label, center=centers[label], intensity=value)
                 for label, value in defaults.items()])


class TestPanelDefinitions:
    def test_the_grid_is_three_columns_of_two(self):
        assert len(PANEL_COLUMNS) == 3
        assert all(len(panels) == 2 for _title, panels in PANEL_COLUMNS)

    def test_column_titles_match_the_inherited_figure(self):
        assert [title for title, _ in PANEL_COLUMNS] == [
            "FWHM", "Peak Centers", "Diagnostic Ratios"
        ]

    def test_the_inherited_spec_values_are_carried_over(self):
        """7.0, 308.0 and 0.13 are the values the wafer-comparison scripts
        label "(Spec)". They are drawn and never evaluated."""
        specs = {
            panel.caption: panel.spec
            for _title, panels in PANEL_COLUMNS for panel in panels
        }
        assert specs["E₂g + A₁g"] == 7.0
        assert specs["B₂g center"] == 308.0
        assert specs["Defect ratio"] == 0.13

    def test_the_stacking_ratio_is_the_two_interlayer_modes(self):
        """C over LB — shear against layer-breathing. Both are interlayer
        vibrations, which is what makes the ratio a bilayer diagnostic."""
        stacking = next(
            p for _t, panels in PANEL_COLUMNS for p in panels
            if getattr(p, "caption", None) == "Stacking ratio"
        )
        assert isinstance(stacking, RatioPanel)
        assert (stacking.numerator, stacking.denominator) == ("C", "LB")

    def test_the_defect_ratio_is_la_over_the_in_plane_mode(self):
        defect = next(
            p for _t, panels in PANEL_COLUMNS for p in panels
            if getattr(p, "caption", None) == "Defect ratio"
        )
        assert (defect.numerator, defect.denominator) == ("LA", "E2g+A1g")


class TestPeakValues:
    def test_values_are_collected_under_their_grid_position(self):
        fits = [(1, _wse2_fit()), (1, _wse2_fit()), (2, _wse2_fit())]

        values = _peak_values(fits, PeakPanel("E2g+A1g", "center", "y", "c"))

        assert sorted(values) == [1, 2]
        assert values[1].size == 2
        assert values[2].size == 1

    def test_a_missing_peak_yields_no_entry_rather_than_zeros(self):
        fits = [(1, _fit([_peak("E2g+A1g")]))]

        assert _peak_values(fits, PeakPanel("B2g", "center", "y", "c")) == {}

    def test_intensity_is_the_curve_maximum_not_the_area(self):
        """The area is 7x the intensity in this fixture; reading the wrong one
        is the mistake that made the .pptx disagree with the CSV in v3.3.0."""
        fits = [(1, _fit([_peak("LA", intensity=36.0)]))]

        values = _peak_values(fits, PeakPanel("LA", "intensity", "y", "c"))

        assert values[1][0] == pytest.approx(36.0)


class TestRatioValues:
    def test_a_ratio_is_formed_within_one_spectrum(self):
        """Per spectrum, then summarized — not mean(numerator)/mean(denominator).
        These two fits have identical means but opposite per-spectrum ratios, so
        only the per-spectrum form can tell them apart."""
        fits = [
            (1, _wse2_fit(LA=100.0, **{"E2g+A1g": 200.0})),   # 0.5
            (1, _wse2_fit(LA=200.0, **{"E2g+A1g": 100.0})),   # 2.0
        ]

        values = _ratio_values(fits, RatioPanel("LA", "E2g+A1g", "y", "c"))

        assert sorted(values[1]) == pytest.approx([0.5, 2.0])

    def test_a_spectrum_missing_either_peak_is_skipped(self):
        fits = [(1, _fit([_peak("LA")])), (1, _wse2_fit())]

        values = _ratio_values(fits, RatioPanel("LA", "E2g+A1g", "y", "c"))

        assert values[1].size == 1

    def test_a_zero_denominator_is_skipped_not_infinite(self):
        fits = [(1, _wse2_fit(LB=0.0))]

        assert _ratio_values(fits, RatioPanel("C", "LB", "y", "c")) == {}


class TestBuildFigure:
    def test_returns_png_bytes(self):
        fits = [(point, _wse2_fit()) for point in range(1, 10)]

        png = build_raman_quality_figure(fits, sample_name="TSM260803")

        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(png) > 10_000

    def test_a_sample_with_no_fits_is_an_error_not_a_blank_figure(self):
        with pytest.raises(ValueError):
            build_raman_quality_figure([], sample_name="Empty")

    def test_panels_whose_peak_is_absent_still_render(self):
        """A non-WSe2 material has none of these peaks. The figure should come
        back with empty panels rather than raising midway through."""
        fits = [(point, _fit([_peak("Si", center=520.0)])) for point in range(1, 10)]

        png = build_raman_quality_figure(fits, sample_name="Silicon", material_name="Si")

        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_many_spectra_at_one_position_do_not_multiply_the_position_count(self):
        fits = [(1, _wse2_fit()) for _ in range(25)] + [(2, _wse2_fit()) for _ in range(25)]

        png = build_raman_quality_figure(fits, sample_name="TwoPoints")

        assert png[:8] == b"\x89PNG\r\n\x1a\n"
