"""
Unit tests for modules.spectra.processing.sample_batch.

Only the `preset is None` short-circuit path is testable without Streamlit
(execute_auto_workflow() is tightly coupled to st.session_state — see the
same carve-out documented in tests/unit/test_auto_workflow.py). Actually
fitting is covered by manual/integration testing, not here.
"""

from core.report.models import SampleScan
from modules.spectra.processing.sample_batch import run_sample_batch


def _scan(raman_points=(), pl_points=()):
    return SampleScan(
        folder="/fake/folder",
        sample_name="Fake",
        raman_files={p: f"/fake/folder/Raman_{p}.txt" for p in raman_points},
        pl_files={p: f"/fake/folder/PL_{p}.txt" for p in pl_points},
    )


class TestRunSampleBatchWithNoPresets:
    def test_both_presets_none_returns_empty_result(self):
        scan = _scan(raman_points=(1, 2, 3), pl_points=(1, 2, 3))

        result = run_sample_batch(scan, raman_preset=None, pl_preset=None)

        assert result.raman_spectra == []
        assert result.pl_spectra == []
        assert result.raman_errors == []
        assert result.pl_errors == []

    def test_progress_callback_never_called_when_both_presets_none(self):
        scan = _scan(raman_points=(1, 2), pl_points=(1, 2))
        calls = []

        run_sample_batch(scan, raman_preset=None, pl_preset=None,
                          progress_callback=lambda *args: calls.append(args))

        assert calls == []

    def test_technique_with_files_but_no_preset_is_skipped(self):
        # Raman has files but no preset -> skipped; PL has neither -> also skipped.
        scan = _scan(raman_points=(1, 2, 3))

        result = run_sample_batch(scan, raman_preset=None, pl_preset=None)

        assert result.raman_spectra == []
        assert result.raman_errors == []

    def test_no_files_at_all_is_a_no_op(self):
        scan = _scan()

        result = run_sample_batch(scan, raman_preset=None, pl_preset=None)

        assert result.raman_spectra == []
        assert result.pl_spectra == []
