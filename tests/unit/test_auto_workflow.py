"""Unit tests for the pure-logic parts of modules.spectra.processing.auto_workflow.

execute_auto_workflow() itself is tightly coupled to st.session_state and is
out of scope here (would require streamlit.testing.v1.AppTest). Only
format_workflow_summary() and get_workflow_suggestions() have no Streamlit
dependency and are unit-tested directly.
"""

from modules.spectra.processing.auto_workflow import format_workflow_summary, get_workflow_suggestions
from modules.spectra.models.preset import MaterialPreset, PeakTemplate
from modules.spectra.models.peak import FittedPeak, FitResult


def _make_preset(x_range_enabled=False):
    return MaterialPreset(
        material_name="Silicon",
        mode="Raman",
        enabled=True,
        x_range_enabled=x_range_enabled,
        x_min=100.0 if x_range_enabled else None,
        x_max=900.0 if x_range_enabled else None,
        despike_threshold=6.0,
        baseline_algorithm="Polynomial",
        baseline_degree=5,
        baseline_lambda=None,
        baseline_p=None,
        peak_templates=[
            PeakTemplate(peak_label="Si", center=520.0, center_tolerance=3.0,
                         width_fwhm=8.0, shape=0.2, color="#2ca02c")
        ],
    )


def _make_fit_result():
    return FitResult(
        success=True,
        fitted_peaks=[
            FittedPeak(label="Si", center=520.0, center_stderr=0.1, amplitude=1000.0,
                       amplitude_stderr=5.0, width_fwhm=8.0, width_stderr=0.2, shape=0.2,
                       component_curve=None, color="#2ca02c")
        ],
        total_fit_curve=None,
        residuals=None,
        chi_squared=1.23,
        r_squared=0.987,
        convergence_time=0.05,
    )


class TestFormatWorkflowSummary:
    def test_success_summary_includes_key_facts(self):
        preset = _make_preset(x_range_enabled=True)
        result = {"success": True, "fit_result": _make_fit_result()}

        summary = format_workflow_summary(result, preset)

        assert "Silicon" in summary
        assert "Raman" in summary
        assert "0.9870" in summary
        assert "100.0 - 900.0" in summary

    def test_failure_summary_includes_stage_and_error(self):
        preset = _make_preset()
        result = {"success": False, "stage_completed": "baseline", "error_message": "boom"}

        summary = format_workflow_summary(result, preset)

        assert "baseline" in summary
        assert "boom" in summary


class TestGetWorkflowSuggestions:
    def test_known_stage_returns_specific_suggestions(self):
        suggestion = get_workflow_suggestions("despike", "some error")
        assert "despike_threshold" in suggestion

    def test_unknown_stage_returns_generic_suggestion(self):
        suggestion = get_workflow_suggestions("unknown_stage", "some error")
        assert suggestion == "Try manual workflow to diagnose the issue."
