"""
Smoke test: every page renders without raising.

Cheap insurance against the failure mode a refactor actually causes — a stale
import or a renamed module that no unit test touches, which would otherwise
only surface as a red Streamlit traceback in front of a user. Rendering is all
this checks; page behavior is covered by the per-page integration tests.
"""

import pytest
from streamlit.testing.v1 import AppTest

PAGES = [
    "app.py",
    "pages/1_Spectra.py",
    "pages/2_Sample_Report.py",
    "pages/3_Material_Presets.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exception(page):
    at = AppTest.from_file(page, default_timeout=60).run()
    assert not at.exception, f"{page} raised: {[e.value for e in at.exception]}"
