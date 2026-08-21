"""Unit tests for core.report.pptx (Sample Report .pptx assembly)."""

import io

from PIL import Image
from pptx import Presentation

from core.report.pptx import build_sample_report_pptx
from core.report.models import PeakStat


def _tiny_png(size=(40, 30), color=(200, 200, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _tables(slide):
    """Tables on `slide`, in the order they were added (Raman, then PL)."""
    return [shape.table for shape in slide.shapes if shape.has_table]


def _stat(label="Exciton", n=9):
    return PeakStat(
        label=label, n=n,
        center_mean=766.5, center_std=0.7,
        amplitude_mean=12000.0, amplitude_std=1500.0,
        fwhm_mean=25.0, fwhm_std=1.2,
    )


class TestBuildSampleReportPptx:
    def test_full_report_builds_three_slides(self):
        om_bytes = {p: _tiny_png() for p in range(1, 10)}
        fit_bytes = {p: _tiny_png() for p in range(1, 10)}

        result = build_sample_report_pptx(
            sample_name="VABA52", material_name="WSe2", report_date="2026-08-21",
            magnification_label="100x", om_image_bytes=om_bytes,
            raman_stats=[_stat("E2g+A1g"), _stat("2LA")], raman_fit_images=fit_bytes,
            pl_stats=[_stat("Exciton"), _stat("Trion")], pl_fit_images=fit_bytes,
        )

        assert result[:2] == b"PK"  # pptx is a zip archive
        prs = Presentation(io.BytesIO(result))
        assert len(prs.slides) == 3

    def test_missing_points_use_placeholders_without_error(self):
        result = build_sample_report_pptx(
            sample_name="Partial", material_name="WSe2", report_date="2026-08-21",
            magnification_label="100x", om_image_bytes={1: _tiny_png(), 5: _tiny_png()},
            raman_stats=None, raman_fit_images={1: _tiny_png()},
            pl_stats=None, pl_fit_images={},
        )

        prs = Presentation(io.BytesIO(result))
        assert len(prs.slides) == 3

    def test_technique_entirely_omitted(self):
        fit_bytes = {p: _tiny_png() for p in range(1, 10)}

        result = build_sample_report_pptx(
            sample_name="RamanOnly", material_name="Silicon", report_date="2026-08-21",
            magnification_label=None, om_image_bytes={},
            raman_stats=[_stat("Si", n=9)], raman_fit_images=fit_bytes,
            pl_stats=None, pl_fit_images={},
        )

        prs = Presentation(io.BytesIO(result))
        assert len(prs.slides) == 3
        # PL slide's fit grid should be all placeholders (no PL images given)
        pl_slide = prs.slides[2]
        pictures = [s for s in pl_slide.shapes if s.shape_type == 13]
        assert len(pictures) == 0

    def test_wide_and_tall_images_both_fit_without_error(self):
        fit_bytes = {p: _tiny_png() for p in range(1, 10)}

        result = build_sample_report_pptx(
            sample_name="AspectRatios", material_name="WSe2", report_date="2026-08-21",
            magnification_label="100x",
            om_image_bytes={1: _tiny_png(size=(200, 40)), 2: _tiny_png(size=(40, 200))},
            raman_stats=[_stat()], raman_fit_images=fit_bytes,
            pl_stats=None, pl_fit_images={},
        )

        prs = Presentation(io.BytesIO(result))
        assert len(prs.slides) == 3

    def test_many_peaks_shrinks_table_font_without_error(self):
        stats = [_stat(label=f"Peak{i}") for i in range(11)]

        result = build_sample_report_pptx(
            sample_name="ManyPeaks", material_name="WSe2", report_date="2026-08-21",
            magnification_label=None, om_image_bytes={},
            raman_stats=stats, raman_fit_images={},
            pl_stats=None, pl_fit_images={},
        )

        prs = Presentation(io.BytesIO(result))
        assert len(prs.slides) == 3

    def test_missing_content_placeholders_have_no_text(self):
        result = build_sample_report_pptx(
            sample_name="Empty", material_name="WSe2", report_date="2026-08-21",
            magnification_label=None, om_image_bytes={},
            raman_stats=None, raman_fit_images={},
            pl_stats=None, pl_fit_images={},
        )

        prs = Presentation(io.BytesIO(result))
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.shape_type == 1 and shape.has_text_frame:  # AUTO_SHAPE (placeholder rectangles)
                    assert shape.text_frame.text == ""

    def test_raman_amplitude_ratio_is_a_row_of_the_raman_table(self):
        result = build_sample_report_pptx(
            sample_name="RatioTest", material_name="WSe2", report_date="2026-08-21",
            magnification_label=None, om_image_bytes={},
            raman_stats=[_stat("LA"), _stat("E2g+A1g")], raman_fit_images={},
            pl_stats=None, pl_fit_images={},
            raman_amplitude_ratio=(0.59, 0.08, 9), raman_amplitude_ratio_label="LA / E2g+A1g ratio",
        )

        prs = Presentation(io.BytesIO(result))
        raman_table = _tables(prs.slides[0])[0]

        # header + 2 peaks + ratio row
        assert len(raman_table.rows) == 4
        ratio_row = [c.text for c in raman_table.rows[3].cells]
        assert ratio_row[0] == "LA / E2g+A1g ratio"
        assert ratio_row[2] == "0.59 ± 0.08"  # value sits in the Amplitude column
        assert ratio_row[4] == "9"

        # ...and nowhere outside the table
        overview_texts = [s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame]
        assert not any("ratio" in t for t in overview_texts)

    def test_raman_amplitude_ratio_omitted_when_none(self):
        result = build_sample_report_pptx(
            sample_name="NoRatio", material_name="Silicon", report_date="2026-08-21",
            magnification_label=None, om_image_bytes={},
            raman_stats=[_stat("Si")], raman_fit_images={},
            pl_stats=None, pl_fit_images={},
            raman_amplitude_ratio=None,
        )

        prs = Presentation(io.BytesIO(result))
        raman_table = _tables(prs.slides[0])[0]
        assert len(raman_table.rows) == 2  # header + the single peak, no ratio row

        overview_texts = [s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame]
        assert not any("ratio" in t for t in overview_texts)
