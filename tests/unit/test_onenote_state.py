"""The OneNote page's session state.

The load-bearing property here is the one that breaks the pattern the other
state modules follow: the upload log survives `reset_results`. Everything
else in this app drops derived keys on an input change, because a stale
figure under a new sample's name is a lie — but the log records what
*happened*, which stays true whatever the operator picks next.
"""

import pytest
import streamlit as st

from modules.onenote.ui import onenote_state
from modules.onenote.ui.onenote_state import (
    failed_uploads,
    get_onenote_state,
    initialize_onenote_state,
    record_upload,
    reset_results,
)


@pytest.fixture(autouse=True)
def clean_session_state():
    st.session_state.clear()
    yield
    st.session_state.clear()


def test_initialize_is_idempotent():
    initialize_onenote_state()
    state = get_onenote_state()
    state["wafer_id"] = "HADH51"

    initialize_onenote_state()

    assert get_onenote_state()["wafer_id"] == "HADH51"


def test_reset_drops_the_verdict():
    state = get_onenote_state()
    state["material_check"] = object()
    state["page_preview"] = object()

    reset_results(state)

    assert state["material_check"] is None
    assert state["page_preview"] is None


def test_reset_keeps_the_upload_log():
    """A failure must not vanish when the operator moves to the next wafer.

    This is the whole point of a non-blocking upload: the record of what did
    not make it has to outlive the selection that produced it, or the upload
    is silently lost.
    """
    state = get_onenote_state()
    record_upload(state, "QC Report", "HADH51", "failed", "429 Too Many Requests")

    reset_results(state)

    assert len(state["log"]) == 1
    assert failed_uploads(state)[0]["wafer_id"] == "HADH51"


def test_the_log_is_a_selection_not_an_artifact():
    """Guard the tuple itself, not just the behaviour.

    The repo's convention is that a derived key missing from an artifact
    tuple outlives the run that produced it. The log is deliberately on the
    other side of that line, so the tuples must say so.
    """
    assert "log" in onenote_state._SELECTIONS
    assert "log" not in onenote_state._CHECK_ARTIFACTS


def test_every_derived_key_is_in_an_artifact_tuple():
    """The invariant each state module in this repo states in its docstring."""
    state = get_onenote_state()
    derived = set(state) - set(onenote_state._SELECTIONS)

    assert derived == set(onenote_state._CHECK_ARTIFACTS)


def test_failed_uploads_filters_to_failures():
    state = get_onenote_state()
    record_upload(state, "QC Report", "HADH51", "ok")
    record_upload(state, "Runcard", "HADH51", "failed", "timeout")
    record_upload(state, "Datalog", "HADG38", "ok")

    failures = failed_uploads(state)

    assert [entry["artifact"] for entry in failures] == ["Runcard"]


def test_failures_keep_their_order():
    state = get_onenote_state()
    record_upload(state, "QC Report", "HADH51", "failed", "first")
    record_upload(state, "Runcard", "HADH51", "failed", "second")

    assert [entry["detail"] for entry in failed_uploads(state)] == ["first", "second"]
