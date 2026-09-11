"""Unit tests for modules.optical.ui.qc_panel_state (QC Panel session state)."""

from modules.optical.ui import qc_panel_state
from modules.optical.ui.qc_panel_state import (
    _OPTICAL_ARTIFACTS,
    _RAMAN_ARTIFACTS,
    _SELECTIONS,
    reset_optical_results,
    reset_raman_results,
    reset_results,
)


def _fresh_state(monkeypatch):
    """The initial dict, without needing a Streamlit session."""
    store: dict = {}
    monkeypatch.setattr(qc_panel_state, "st", type("_St", (), {"session_state": store})())
    qc_panel_state.initialize_qc_panel_state()
    return store["qc_panel"]


class TestEveryDerivedKeyIsResettable:
    """A derived key left out of the artifact tuples outlives its run.

    The QC Panel's results are rendered from persisted state, so a key that
    `reset_results` does not clear keeps showing last run's answer under this
    run's heading -- the failure the module docstring describes, and the one
    the gate verdict ("check that MoS2 is what this sample is") would repeat
    against the newly chosen material.
    """

    def test_no_key_is_unaccounted_for(self, monkeypatch):
        state = _fresh_state(monkeypatch)
        accounted = set(_SELECTIONS) | set(_OPTICAL_ARTIFACTS) | set(_RAMAN_ARTIFACTS)

        assert set(state) - accounted == set()

    def test_no_tuple_names_a_key_that_does_not_exist(self, monkeypatch):
        state = _fresh_state(monkeypatch)
        named = set(_SELECTIONS) | set(_OPTICAL_ARTIFACTS) | set(_RAMAN_ARTIFACTS)

        assert named - set(state) == set()

    def test_reset_results_clears_every_derived_key(self, monkeypatch):
        state = _fresh_state(monkeypatch)
        for key in state:
            state[key] = "set"

        reset_results(state)

        assert [k for k in _OPTICAL_ARTIFACTS + _RAMAN_ARTIFACTS if state[k] is not None] == []
        assert all(state[k] == "set" for k in _SELECTIONS)


class TestPerTechniqueResets:
    """A Raman peak edit must not discard a 30-second OM segmentation."""

    def test_raman_reset_leaves_the_optical_artifacts(self, monkeypatch):
        state = _fresh_state(monkeypatch)
        for key in state:
            state[key] = "set"

        reset_raman_results(state)

        assert all(state[k] is None for k in _RAMAN_ARTIFACTS)
        assert all(state[k] == "set" for k in _OPTICAL_ARTIFACTS)

    def test_optical_reset_leaves_the_raman_artifacts(self, monkeypatch):
        state = _fresh_state(monkeypatch)
        for key in state:
            state[key] = "set"

        reset_optical_results(state)

        assert all(state[k] is None for k in _OPTICAL_ARTIFACTS)
        assert all(state[k] == "set" for k in _RAMAN_ARTIFACTS)
