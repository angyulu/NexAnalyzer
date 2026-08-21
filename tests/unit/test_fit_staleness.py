"""Unit tests for modules.spectra.utils.fit_staleness (preprocessing-hash stale-fit detection).

Moved out of src.ui.control_panel during the Phase 4 refactor specifically
because it has no Streamlit dependency and is now directly testable.
"""

import numpy as np

from modules.spectra.utils.fit_staleness import compute_preprocessing_hash, mark_fit_stale_if_needed
from modules.spectra.models.spectrum import SpectrumData, SpectrumFile, ProcessingSettings


def _make_spectrum(**settings_overrides):
    x = np.linspace(100, 1000, 150)
    y = np.linspace(10, 20, 150)
    data = SpectrumData(X=x, Y=y)
    settings = ProcessingSettings(**settings_overrides)
    return SpectrumFile(
        filename="sample.txt", mode="Raman",
        original_data=data, raw_data=data, processed_data=data,
        processing_settings=settings,
    )


class TestComputePreprocessingHash:
    def test_same_settings_give_same_hash(self):
        s1 = _make_spectrum(despike_threshold=6.0)
        s2 = _make_spectrum(despike_threshold=6.0)
        assert compute_preprocessing_hash(s1) == compute_preprocessing_hash(s2)

    def test_different_settings_give_different_hash(self):
        s1 = _make_spectrum(despike_threshold=6.0)
        s2 = _make_spectrum(despike_threshold=8.0)
        assert compute_preprocessing_hash(s1) != compute_preprocessing_hash(s2)

    def test_returns_64_char_hex_string(self):
        s = _make_spectrum()
        h = compute_preprocessing_hash(s)
        assert len(h) == 64
        int(h, 16)  # raises if not valid hex


class TestMarkFitStaleIfNeeded:
    def test_no_fit_done_stays_not_stale(self):
        spectrum = _make_spectrum()
        spectrum.fit_done = False
        mark_fit_stale_if_needed(spectrum)
        assert spectrum.fit_stale is False

    def test_hash_unchanged_stays_not_stale(self):
        spectrum = _make_spectrum(despike_threshold=6.0)
        spectrum.fit_done = True
        spectrum.last_preprocessing_hash = compute_preprocessing_hash(spectrum)

        mark_fit_stale_if_needed(spectrum)

        assert spectrum.fit_stale is False

    def test_hash_changed_marks_stale(self):
        spectrum = _make_spectrum(despike_threshold=6.0)
        spectrum.fit_done = True
        spectrum.last_preprocessing_hash = compute_preprocessing_hash(spectrum)

        # Simulate the user re-running despike with a different threshold.
        spectrum.processing_settings.despike_threshold = 10.0
        mark_fit_stale_if_needed(spectrum)

        assert spectrum.fit_stale is True

    def test_no_saved_hash_stays_not_stale(self):
        # last_preprocessing_hash is None until a fit has actually saved one.
        spectrum = _make_spectrum()
        spectrum.fit_done = True
        spectrum.last_preprocessing_hash = None

        mark_fit_stale_if_needed(spectrum)

        assert spectrum.fit_stale is False
