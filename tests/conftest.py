"""Shared pytest fixtures for the NexAnalyzer test suite."""

import numpy as np
import pytest


def _pseudo_voigt(x, center, amplitude, fwhm, shape=0.5):
    """Cheap pseudo-Voigt profile for building synthetic test spectra.

    Not the same math as lmfit's VoigtModel (true Voigt is a convolution),
    but close enough in shape to exercise fitting/despiking/baseline code
    against a realistic peak-on-baseline signal.
    """
    sigma = fwhm / 2.355
    gaussian = np.exp(-0.5 * ((x - center) / sigma) ** 2)
    lorentzian = 1.0 / (1.0 + ((x - center) / (fwhm / 2)) ** 2)
    return amplitude * ((1 - shape) * gaussian + shape * lorentzian)


@pytest.fixture
def synthetic_spectrum():
    """Factory fixture: build an (x, y) synthetic spectrum for testing.

    Returns a callable so each test can customize peaks/baseline/noise.
    Defaults satisfy SpectrumData's >=100-point minimum.
    """
    def _make(
        n_points=300,
        x_range=(100.0, 2000.0),
        peaks=((1000.0, 1000.0, 50.0),),  # (center, amplitude, fwhm) tuples
        baseline_slope=0.0,
        baseline_offset=0.0,
        noise_std=0.0,
        seed=0,
    ):
        x = np.linspace(x_range[0], x_range[1], n_points)
        y = baseline_offset + baseline_slope * (x - x_range[0])
        for center, amplitude, fwhm in peaks:
            y = y + _pseudo_voigt(x, center, amplitude, fwhm)
        if noise_std > 0:
            rng = np.random.default_rng(seed)
            y = y + rng.normal(0, noise_std, size=n_points)
        return x, y

    return _make
