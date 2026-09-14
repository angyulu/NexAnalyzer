"""
The QC Panel's CSV exports: the OM frame tables and the Raman fit tables.

What these guard is agreement. Each technique writes two files -- a `_stats`
summary and the `_points` rows behind it -- and the whole point of shipping
both is that a reader can average the second and land on the first. A change
that quietly filtered one table and not the other would leave both files valid,
both plausible, and disagreeing; the round-trip tests below are what catch it.

Intensity, never area: `test_intensity_is_the_curve_maximum_not_the_area`
holds the line CLAUDE.md draws.
"""

import io

import numpy as np
import pandas as pd
import pytest

from core.report.models import PeakStat
from modules.optical.io.frame_csv import export_frame_points_csv, export_frame_stats_csv
from modules.optical.processing.contrast import FrameResult, class_labels
from modules.spectra.io.results_csv import export_peak_stats_csv, export_point_fits_csv
from modules.spectra.models.peak import FittedPeak, FitResult
from modules.spectra.processing.peak_metrics import aggregate_fit_results, peak_intensity


def _read(csv_text):
    return pd.read_csv(io.StringIO(csv_text))


# ------------------------------------------------------------------ fixtures
def _frame(point, percentages, contrast_below=-3.2, contrast_above=4.1,
           ref_label="2L"):
    """A FrameResult carrying only the fields the CSVs read.

    The image arrays are one pixel each: these exports never look at them, and
    a realistic frame would make the fixture about segmentation instead.
    """
    return FrameResult(
        name=f"50x-{point}",
        point=point,
        frame_type="circular",
        ref_label=ref_label,
        labels=class_labels(ref_label),
        percentages=percentages,
        contrast_below=contrast_below,
        contrast_above=contrast_above,
        components_below=14,
        components_above=9,
        original=np.zeros((1, 1, 3)),
        overlay=np.zeros((1, 1, 3)),
        valid=np.ones((1, 1), dtype=bool),
        hist_centers=np.array([0.0, 1.0]),
        hist_counts=np.array([1, 2]),
        mode=190.0,
        sigma_l=2.0,
        sigma_r=2.5,
        sigma_noise=1.8,
        threshold_low=182.0,
        threshold_high=197.0,
        shoulder=False,
    )


def _peak(label="E2g+A1g", center=250.0, area=1000.0, fwhm=7.0):
    return FittedPeak(
        label=label,
        center=center,
        center_stderr=0.03,
        area=area,
        area_stderr=5.0,
        width_fwhm=fwhm,
        width_stderr=0.1,
        shape=0.5,
        component_curve=np.zeros(3),
    )


def _fit(peaks, r_squared=0.99):
    return FitResult(
        success=True,
        fitted_peaks=peaks,
        total_fit_curve=np.zeros(3),
        residuals=np.zeros(3),
        chi_squared=1.5,
        r_squared=r_squared,
        convergence_time=0.2,
    )


# ------------------------------------------------------------------- OM CSVs
class TestFrameStatsCsv:
    def test_one_row_per_class_in_label_order(self):
        frames = [_frame(p, (10.0, 70.0, 20.0)) for p in (1, 2, 3)]

        df = _read(export_frame_stats_csv(frames))

        assert list(df["Class"]) == ["Below 2L", "Bilayer", "Above 2L"]
        assert list(df["Position"]) == ["Below", "Reference", "Above"]
        assert list(df["N_Frames"]) == [3, 3, 3]

    def test_position_is_stable_across_reference_layers(self):
        """`Class` follows the layer, `Position` does not -- which is what lets
        a 1L sample's table be stacked on a 2L sample's."""
        monolayer = [_frame(1, (10.0, 70.0, 20.0), ref_label="1L")]

        df = _read(export_frame_stats_csv(monolayer))

        assert list(df["Class"]) == ["Below 1L", "Monolayer", "Above 1L"]
        assert list(df["Position"]) == ["Below", "Reference", "Above"]

    def test_coverage_mean_and_std_match_the_frames(self):
        frames = [
            _frame(1, (10.0, 70.0, 20.0)),
            _frame(2, (14.0, 66.0, 20.0)),
        ]

        df = _read(export_frame_stats_csv(frames)).set_index("Position")

        assert df.loc["Below", "Coverage_Mean_pct"] == pytest.approx(12.0)
        # ddof=1: two frames, one degree of freedom.
        assert df.loc["Below", "Coverage_Std_pct"] == pytest.approx(
            np.std([10.0, 14.0], ddof=1)
        )

    def test_a_single_frame_reports_zero_spread_not_nan(self):
        df = _read(export_frame_stats_csv([_frame(1, (10.0, 70.0, 20.0))]))

        assert list(df["Coverage_Std_pct"]) == [0.0, 0.0, 0.0]

    def test_the_reference_class_has_no_contrast_of_its_own(self):
        """Contrast is measured relative to the reference film, so the
        reference row's cell is blank rather than a 0.0 that reads as flat."""
        df = _read(export_frame_stats_csv([_frame(1, (10.0, 70.0, 20.0))]))
        reference = df[df["Position"] == "Reference"].iloc[0]

        assert pd.isna(reference["Contrast_Mean_pct"])
        assert pd.isna(reference["Contrast_Std_pct"])
        below = df[df["Position"] == "Below"].iloc[0]
        assert below["Contrast_Mean_pct"] == pytest.approx(-3.2)

    def test_no_frames_yields_a_comment_not_an_empty_file(self):
        assert export_frame_stats_csv([]).startswith("# No optical frames")


class TestFramePointsCsv:
    def test_one_row_per_frame_sorted_by_point(self):
        frames = [_frame(p, (10.0, 70.0, 20.0)) for p in (3, 1, 2)]

        df = _read(export_frame_points_csv(frames))

        assert list(df["Point"]) == [1, 2, 3]
        assert list(df["Frame"]) == ["50x-1", "50x-2", "50x-3"]

    def test_coverages_are_a_partition(self):
        df = _read(export_frame_points_csv([_frame(1, (11.5, 69.3, 19.2))]))
        row = df.iloc[0]

        total = (row["Below_Coverage_pct"] + row["Reference_Coverage_pct"]
                 + row["Above_Coverage_pct"])
        assert total == pytest.approx(100.0)

    def test_the_threshold_landmarks_travel_with_the_row(self):
        """The diagnostic PNG's histogram marks, as numbers: a frame that
        segmented badly is legible here without opening the image."""
        df = _read(export_frame_points_csv([_frame(1, (10.0, 70.0, 20.0))]))
        row = df.iloc[0]

        assert row["Green_Mode"] == pytest.approx(190.0)
        assert row["Threshold_Low"] == pytest.approx(182.0)
        assert row["Threshold_High"] == pytest.approx(197.0)
        assert row["Sigma_Noise"] == pytest.approx(1.8)

    def test_the_points_table_averages_to_the_stats_table(self):
        """The reason both files ship. If one ever starts filtering rows the
        other keeps, this is what fails."""
        frames = [
            _frame(1, (10.0, 70.0, 20.0)),
            _frame(2, (14.0, 66.0, 20.0)),
            _frame(3, (12.0, 68.0, 20.0)),
        ]

        points = _read(export_frame_points_csv(frames))
        stats = _read(export_frame_stats_csv(frames)).set_index("Position")

        for position, column in (
            ("Below", "Below_Coverage_pct"),
            ("Reference", "Reference_Coverage_pct"),
            ("Above", "Above_Coverage_pct"),
        ):
            assert stats.loc[position, "Coverage_Mean_pct"] == pytest.approx(
                points[column].mean()
            )
            assert stats.loc[position, "Coverage_Std_pct"] == pytest.approx(
                points[column].std(ddof=1)
            )

    def test_no_frames_yields_a_comment_not_an_empty_file(self):
        assert export_frame_points_csv([]).startswith("# No optical frames")


# ---------------------------------------------------------------- Raman CSVs
class TestPointFitsCsv:
    def test_one_row_per_peak_per_fit(self):
        pairs = [
            (1, _fit([_peak("E2g+A1g"), _peak("2LA", center=260.0)])),
            (2, _fit([_peak("E2g+A1g"), _peak("2LA", center=260.0)])),
        ]

        df = _read(export_point_fits_csv(pairs))

        assert len(df) == 4
        assert sorted(df["Peak_Label"].unique()) == ["2LA", "E2g+A1g"]

    def test_sub_spectra_at_one_point_are_numbered_not_collapsed(self):
        """A map file holds 25 spectra at one position. `Point` repeats;
        `Spectrum` is what tells the rows apart."""
        pairs = [(1, _fit([_peak()])) for _ in range(3)] + [(2, _fit([_peak()]))]

        df = _read(export_point_fits_csv(pairs))

        assert list(df["Point"]) == [1, 1, 1, 2]
        assert list(df["Spectrum"]) == [1, 2, 3, 1]

    def test_intensity_is_the_curve_maximum_not_the_area(self):
        """CLAUDE.md's line. The two differ by ~FWHM x 1.064, and shipping the
        area under an "Intensity" heading is what made v3.3.0's .pptx disagree
        with its own CSV."""
        peak = _peak(area=1000.0, fwhm=7.0)

        df = _read(export_point_fits_csv([(1, _fit([peak]))]))

        assert df.iloc[0]["Intensity"] == pytest.approx(peak_intensity(peak))
        assert df.iloc[0]["Intensity"] != pytest.approx(peak.area)
        assert "Area" not in df.columns

    def test_the_fits_r_squared_lands_on_every_one_of_its_rows(self):
        fit = _fit([_peak(), _peak("2LA")], r_squared=0.87)

        df = _read(export_point_fits_csv([(1, fit)]))

        assert list(df["R_Squared"]) == [pytest.approx(0.87)] * 2

    def test_no_fits_yields_a_comment_not_an_empty_file(self):
        assert export_point_fits_csv([]).startswith("# No fit results")


class TestPeakStatsCsv:
    def test_one_row_per_peak_label_with_n(self):
        stats = [
            PeakStat("E2g+A1g", 9, 250.0, 0.4, 1200.0, 30.0, 7.0, 0.2),
            PeakStat("2LA", 9, 260.0, 0.5, 300.0, 12.0, 9.0, 0.3),
        ]

        df = _read(export_peak_stats_csv(stats))

        assert list(df["Peak_Label"]) == ["E2g+A1g", "2LA"]
        assert list(df["N"]) == [9, 9]
        assert df.iloc[0]["Center_Mean"] == pytest.approx(250.0)
        assert df.iloc[0]["FWHM_Std"] == pytest.approx(0.2)

    def test_an_unmeasurable_width_is_blank_not_zero(self):
        """The empirical "Raw" row on a spectrum with no half-maximum crossing.
        A 0.0 there would read as a measurement of nothing."""
        df = _read(export_peak_stats_csv([
            PeakStat("Raw", 9, 750.0, 3.0, 5000.0, 200.0, None, None),
        ]))

        assert pd.isna(df.iloc[0]["FWHM_Mean"])
        assert pd.isna(df.iloc[0]["FWHM_Std"])

    def test_the_superseded_gaussian_width_stays_out(self):
        """FWHM_v1 under-reports every width by 59-108%. It is an opt-in
        on-screen comparison, not something a saved file carries unlabelled."""
        df = _read(export_peak_stats_csv([
            PeakStat("E2g+A1g", 9, 250.0, 0.4, 1200.0, 30.0, 7.0, 0.2,
                     fwhm_v1_mean=3.0, fwhm_v1_std=0.1),
        ]))

        assert not [c for c in df.columns if "v1" in c.lower()]

    def test_the_points_table_aggregates_to_the_stats_table(self):
        """Same round-trip as the OM pair, through the real aggregation: the
        stats CSV must be the points CSV summarised, not a parallel
        computation that can drift from it."""
        pairs = [
            (1, _fit([_peak(center=250.0, fwhm=7.0)])),
            (2, _fit([_peak(center=250.6, fwhm=7.2)])),
            (3, _fit([_peak(center=250.2, fwhm=6.9)])),
        ]

        points = _read(export_point_fits_csv(pairs))
        stats = _read(export_peak_stats_csv(aggregate_fit_results(pairs)))

        assert stats.iloc[0]["N"] == len(points)
        assert stats.iloc[0]["Center_Mean"] == pytest.approx(points["Center"].mean())
        assert stats.iloc[0]["FWHM_Mean"] == pytest.approx(points["FWHM"].mean())
        assert stats.iloc[0]["Intensity_Mean"] == pytest.approx(
            points["Intensity"].mean()
        )

    def test_no_stats_yields_a_comment_not_an_empty_file(self):
        assert export_peak_stats_csv([]).startswith("# No peak statistics")
