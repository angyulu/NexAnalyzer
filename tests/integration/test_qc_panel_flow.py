"""
Integration test for the QC Panel page (pages/4_QC_Panel.py).

Drives the real Streamlit page through streamlit.testing.v1.AppTest, which is
the only way to cover execute_auto_workflow()'s st.session_state coupling and
the page's own button wiring.

Uses the repo's real Silicon (Raman-only) preset from data/materials.json
rather than external sample data, following the Sample Report flow test. The
WSe2-specific panel contents are covered by tests/unit/test_raman_quality.py;
what this test covers is that a folder goes in and two images come out.

The Raman fixtures deliberately carry three spectra per file. That is the
multi-spectrum shape real sample folders use — TSM260803's files hold 25 each —
and until v3.10.0 the report path parsed only the first two columns and
silently excluded every such file, so the Raman half produced nothing at all.
"""

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from core.paths import PROJECT_ROOT

from modules.spectra.processing.sample_scanner import scan_sample_folder

SUB_SPECTRA = 3


def _write_multi_spectrum_raman(path, seed):
    """One X column plus SUB_SPECTRA intensity columns, tab separated.

    A single peak near 520 cm-1, matching materials.json's Silicon (Raman)
    preset, over enough points that width_min's spectral-resolution term stays
    below the peak's FWHM.
    """
    x = np.linspace(0, 1000, 2000)
    sigma = 8.0 / 2.355
    rng = np.random.default_rng(seed)
    columns = [x]
    for offset in range(SUB_SPECTRA):
        peak = 1000.0 + 40.0 * offset
        columns.append(
            500.0
            + peak * np.exp(-0.5 * ((x - 520.0) / sigma) ** 2)
            + rng.normal(0, 5, size=x.size)
        )
    with open(path, "w") as f:
        for row in zip(*columns):
            f.write("\t".join(f"{v:.4f}" for v in row) + "\n")


def _write_om_frame(path, seed):
    """A frame with gentle vignetting, noise, and one brighter patch, so the
    segmentation has something to find rather than an empty class."""
    from PIL import Image

    H, W = 150, 200
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(yy - H / 2, xx - W / 2) / np.hypot(H / 2, W / 2)
    green = 190.0 - 8.0 * r**2 + rng.normal(0, 1.2, size=(H, W))
    green[40:60, 60:110] += 9.0
    green[100:112, 130:170] -= 9.0
    rgb = np.stack([green * 0.95, green, green * 1.02], axis=-1)
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(path)


def _seeded_app(tmp_path, points=range(1, 10)):
    for point in points:
        _write_multi_spectrum_raman(tmp_path / f"RM_{point}.txt", seed=point)
        _write_om_frame(tmp_path / f"50x_{point}.png", seed=100 + point)

    scan = scan_sample_folder(str(tmp_path))
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/4_QC_Panel.py"), default_timeout=180)
    at.session_state["qc_panel"] = {
        "folder": str(tmp_path),
        "scan": scan,
        "magnification": "50x",
        "material": "Silicon",
        "reference_layer": "2L",
        "frames": None,
        "om_png": None,
        "raman_png": None,
        "raman_stats": None,
        "errors": None,
    }
    return at, scan


class TestQcPanelPageFlow:
    def test_empty_state_renders_without_error(self):
        at = AppTest.from_file(str(PROJECT_ROOT / "pages/4_QC_Panel.py"),
                               default_timeout=60).run()

        assert not at.exception

    def test_run_produces_both_images(self, tmp_path):
        at, scan = _seeded_app(tmp_path)
        at.run()

        next(b for b in at.button if "Run Analysis" in b.label).click().run()

        assert not at.exception, [e.value for e in at.exception]
        state = at.session_state["qc_panel"]
        assert state["om_png"][:8] == b"\x89PNG\r\n\x1a\n"
        assert state["raman_png"][:8] == b"\x89PNG\r\n\x1a\n"

    def test_every_sub_spectrum_is_fitted_not_just_the_first(self, tmp_path):
        """The defect this guards: parse_spectrum() read a multi-column file as
        two columns and the rest were dropped on the floor."""
        at, scan = _seeded_app(tmp_path)
        at.run()
        next(b for b in at.button if "Run Analysis" in b.label).click().run()

        stats = at.session_state["qc_panel"]["raman_stats"]

        assert stats, "no Raman peaks were aggregated"
        assert stats[0].n == 9 * SUB_SPECTRA

    def test_one_frame_per_grid_position_is_segmented(self, tmp_path):
        at, scan = _seeded_app(tmp_path)
        at.run()
        next(b for b in at.button if "Run Analysis" in b.label).click().run()

        frames = at.session_state["qc_panel"]["frames"]

        assert [f.point for f in frames] == list(range(1, 10))
        assert all(f.labels == ("Below 2L", "Bilayer", "Above 2L") for f in frames)

    def test_coverage_percentages_are_a_partition(self, tmp_path):
        at, scan = _seeded_app(tmp_path)
        at.run()
        next(b for b in at.button if "Run Analysis" in b.label).click().run()

        for frame in at.session_state["qc_panel"]["frames"]:
            assert sum(frame.percentages) == pytest.approx(100.0, abs=0.01)

    def test_a_sample_with_no_optical_images_still_produces_the_raman_image(self, tmp_path):
        for point in range(1, 10):
            _write_multi_spectrum_raman(tmp_path / f"RM_{point}.txt", seed=point)
        scan = scan_sample_folder(str(tmp_path))

        at = AppTest.from_file(str(PROJECT_ROOT / "pages/4_QC_Panel.py"), default_timeout=180)
        at.session_state["qc_panel"] = {
            "folder": str(tmp_path), "scan": scan, "magnification": None,
            "material": "Silicon", "reference_layer": "2L", "frames": None,
            "om_png": None, "raman_png": None, "raman_stats": None, "errors": None,
        }
        at.run()
        next(b for b in at.button if "Run Analysis" in b.label).click().run()

        assert not at.exception, [e.value for e in at.exception]
        state = at.session_state["qc_panel"]
        assert state["om_png"] is None, "no images means no OM figure, not an empty one"
        assert state["raman_png"] is not None

    def test_changing_the_reference_layer_drops_stale_results(self, tmp_path):
        """A figure labelled 'Bilayer' must not survive a switch to 1L."""
        at, scan = _seeded_app(tmp_path)
        at.run()
        next(b for b in at.button if "Run Analysis" in b.label).click().run()
        assert at.session_state["qc_panel"]["om_png"] is not None

        selectbox = next(s for s in at.selectbox if "film being measured" in s.label)
        selectbox.select("1L").run()

        state = at.session_state["qc_panel"]
        assert state["reference_layer"] == "1L"
        assert state["om_png"] is None
        assert state["raman_png"] is None


class TestSaveImages:
    """The save path, with the native dialog stubbed out.

    Worth testing despite the dialog itself being untestable: the bug this
    guards is a wrong call into `prompt_save_path` (its first argument is
    `default_dir`, and the filename keyword is `default_filename`), which the
    page catches and reports as a toast. Nothing else in the suite touches this
    code, so it shipped broken once already.
    """

    def _run_and_save(self, tmp_path, monkeypatch, target):
        import core.io.export as export_module

        calls = {}

        def _fake_dialog(default_dir, default_filename, **kwargs):
            calls["default_dir"] = default_dir
            calls["default_filename"] = default_filename
            calls.update(kwargs)
            return target

        monkeypatch.setattr(export_module, "prompt_save_path", _fake_dialog)

        at, _scan = _seeded_app(tmp_path)
        at.run()
        next(b for b in at.button if "Run Analysis" in b.label).click().run()
        next(b for b in at.button if "Save Images" in b.label).click().run()
        return at, calls

    def test_all_three_images_are_written_with_distinct_suffixes(self, tmp_path, monkeypatch):
        """One dialog, three files: the clean OM grid a report carries, the
        diagnostic copy carrying the histograms, and the Raman panels."""
        out = tmp_path / "out"
        out.mkdir()
        at, _calls = self._run_and_save(tmp_path, monkeypatch, str(out / "TSM_QC.png"))

        assert not at.exception, [e.value for e in at.exception]
        written = sorted(p.name for p in out.glob("*.png"))
        assert written == [
            "TSM_QC_OM.png",
            "TSM_QC_OM_diagnostic.png",
            "TSM_QC_Raman.png",
        ]
        for path in out.glob("*.png"):
            assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_the_dialog_opens_in_the_sample_folder(self, tmp_path, monkeypatch):
        out = tmp_path / "out"
        out.mkdir()
        _at, calls = self._run_and_save(tmp_path, monkeypatch, str(out / "x.png"))

        assert calls["default_dir"] == str(tmp_path)
        assert calls["default_filename"].endswith("_QC.png")
        assert calls["default_extension"] == ".png"

    def test_cancelling_the_dialog_writes_nothing(self, tmp_path, monkeypatch):
        out = tmp_path / "out"
        out.mkdir()
        at, _calls = self._run_and_save(tmp_path, monkeypatch, None)

        assert not at.exception
        assert list(out.glob("*.png")) == []

    def test_the_clean_copy_and_the_diagnostic_copy_are_different_images(
        self, tmp_path, monkeypatch
    ):
        """Guards the whole point of Change B. If `show_histograms` stopped
        being honoured, both files would still be written and both would still
        be valid PNGs, so only comparing them catches it."""
        out = tmp_path / "out"
        out.mkdir()
        self._run_and_save(tmp_path, monkeypatch, str(out / "TSM_QC.png"))

        clean = (out / "TSM_QC_OM.png").read_bytes()
        diagnostic = (out / "TSM_QC_OM_diagnostic.png").read_bytes()

        assert clean != diagnostic
        # The diagnostics row is extra content, so it is the larger figure.
        assert len(diagnostic) > len(clean)
