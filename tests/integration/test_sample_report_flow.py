"""
Integration test for the Sample Report page (pages/2_Sample_Report.py).

Unlike the unit tests for its building blocks (sample_scanner, sample_batch,
peak_metrics, report.pptx), this exercises the actual Streamlit page via
streamlit.testing.v1.AppTest, closing the gap those unit tests can't cover:
execute_auto_workflow()'s st.session_state coupling and the page's own
button/dropdown wiring. Uses the repo's real Silicon (Raman-only) preset
from data/materials.json rather than the untracked Example/ folders,
so this test is self-contained and doesn't depend on external sample data.
"""

import numpy as np
from streamlit.testing.v1 import AppTest

from modules.spectra.processing.sample_scanner import scan_sample_folder


def _write_silicon_raman_file(path, seed):
    # Single peak near 520 cm-1, matching materials.json's Silicon (Raman)
    # preset (center=520, width_fwhm=8), over enough points that
    # width_min's spectral-resolution term doesn't exceed the peak's FWHM.
    x = np.linspace(0, 1000, 2000)
    sigma = 8.0 / 2.355
    rng = np.random.default_rng(seed)
    y = 500.0 + 1000.0 * np.exp(-0.5 * ((x - 520.0) / sigma) ** 2) + rng.normal(0, 5, size=x.size)
    with open(path, "w") as f:
        for xi, yi in zip(x, y):
            f.write(f"{xi:.4f}\t{yi:.4f}\n")


def _write_tiny_image(path):
    from PIL import Image
    Image.new("RGB", (60, 40), (180, 180, 180)).save(path, format="PNG")


class TestSampleReportPageFlow:
    def test_generate_report_end_to_end(self, tmp_path):
        for point in range(1, 10):
            _write_silicon_raman_file(tmp_path / f"RM_{point}.txt", seed=point)
            _write_tiny_image(tmp_path / f"100x_{point}.png")

        scan = scan_sample_folder(str(tmp_path))
        assert len(scan.raman_files) == 9  # sanity: fixture matches the naming convention

        at = AppTest.from_file("pages/2_Sample_Report.py", default_timeout=60)
        at.session_state["sample_report"] = {
            "folder": str(tmp_path),
            "scan": scan,
            "magnification": "100x",
            "material": "Silicon",
            "batch_result": None,
            "raman_stats": None,
            "pl_stats": None,
            "pptx_bytes": None,
            "slide_images": None,
        }
        at.run()
        assert not at.exception

        generate_button = next(b for b in at.button if "Generate Report" in b.label)
        generate_button.click().run()

        assert not at.exception
        state = at.session_state["sample_report"]
        assert state["batch_result"] is not None
        assert len(state["batch_result"].raman_spectra) == 9
        assert state["raman_stats"] is not None
        assert state["raman_stats"][0].label == "Si"
        assert state["pptx_bytes"] is not None
        assert state["pptx_bytes"][:2] == b"PK"
        # Slide-image rendering needs PowerPoint COM automation (Windows-only,
        # same category of native dependency as the tkinter file dialogs) —
        # only assert its shape when it actually succeeded in this environment.
        if state["slide_images"] is not None:
            assert len(state["slide_images"]) == 3

    def test_empty_state_renders_without_error(self):
        # No folder selected yet -> most of the page is skipped, but the
        # top section (title, folder-pick button) must still render cleanly.
        at = AppTest.from_file("pages/2_Sample_Report.py", default_timeout=60)
        at.run()

        assert not at.exception
