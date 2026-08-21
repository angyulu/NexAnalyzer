"""Unit tests for modules.spectra.io.results_csv (fit-results CSV export)."""

import io

import numpy as np
import pandas as pd
import pytest

from modules.spectra.io.results_csv import export_fit_params_csv, export_master_csv
from modules.spectra.models.spectrum import SpectrumData, SpectrumFile, ProcessingSettings
from modules.spectra.models.peak import FittedPeak, FitResult


def _make_spectrum_file(filename="sample_raman.txt", mode="Raman", with_fit=True):
    x = np.linspace(100, 1000, 150)
    y = np.linspace(10, 20, 150)
    data = SpectrumData(X=x, Y=y)

    fit_result = None
    if with_fit:
        component = np.exp(-0.5 * ((x - 500) / 20) ** 2) * 100
        fit_result = FitResult(
            success=True,
            fitted_peaks=[
                FittedPeak(
                    label="Peak 1", center=500.0, center_stderr=0.5,
                    amplitude=1000.0, amplitude_stderr=10.0,
                    width_fwhm=40.0, width_stderr=1.0, shape=0.5,
                    component_curve=component, color="#1f77b4",
                )
            ],
            total_fit_curve=y + component,
            residuals=np.zeros_like(y),
            chi_squared=1.0,
            r_squared=0.95,
            convergence_time=0.1,
        )

    return SpectrumFile(
        filename=filename,
        mode=mode,
        original_data=data,
        raw_data=data,
        processed_data=data,
        processing_settings=ProcessingSettings(),
        fit_result=fit_result,
    )


class TestExportMasterCsv:
    def test_no_fit_results_returns_placeholder_comment(self):
        spectrum = _make_spectrum_file(with_fit=False)
        csv = export_master_csv({"sample_raman.txt": spectrum})
        assert csv.startswith("#")

    def test_includes_one_row_per_peak(self):
        spectrum = _make_spectrum_file(with_fit=True)
        csv = export_master_csv({"sample_raman.txt": spectrum})

        df = pd.read_csv(io.StringIO(csv))
        assert len(df) == 1
        assert df.iloc[0]["Peak_Label"] == "Peak 1"
        assert df.iloc[0]["Filename"] == "sample_raman.txt"

    def test_pl_mode_prepends_raw_row(self):
        spectrum = _make_spectrum_file(filename="pl_sample.txt", mode="PL", with_fit=True)
        csv = export_master_csv({"pl_sample.txt": spectrum})

        df = pd.read_csv(io.StringIO(csv))
        assert df.iloc[0]["Peak_Label"] == "Raw"
        assert df.iloc[1]["Peak_Label"] == "Peak 1"

    def test_column_order_is_stable_across_raw_and_peak_rows(self):
        # The Raw row and the peak rows build their dicts in different orders;
        # the CSV must still have one canonical column order.
        pl = _make_spectrum_file(filename="pl.txt", mode="PL")
        raman = _make_spectrum_file(filename="rm.txt", mode="Raman")
        csv = export_master_csv({"pl.txt": pl, "rm.txt": raman})

        header = csv.splitlines()[0].split(",")
        assert header[:2] == ["Filename", "Mode"]
        assert header[-1] == "Convergence_Time_s"
        assert "Amplitude_Stderr" in header

    def test_amplitude_is_peak_height_not_integrated_amplitude(self):
        spectrum = _make_spectrum_file(with_fit=True)
        csv = export_master_csv({"sample_raman.txt": spectrum})

        df = pd.read_csv(io.StringIO(csv))
        # Component curve peaks at ~100 (discrete grid); lmfit's integrated
        # amplitude is 1000, so height must not be the one reported.
        assert df.iloc[0]["Amplitude"] == pytest.approx(100.0, rel=1e-2)
        # stderr rescaled by the same height/amplitude ratio (10 * 100/1000).
        assert df.iloc[0]["Amplitude_Stderr"] == pytest.approx(1.0, rel=1e-2)


class TestExportFitParamsCsv:
    def test_one_row_per_peak_for_the_current_spectrum(self):
        spectrum = _make_spectrum_file(with_fit=True)
        df = pd.read_csv(io.StringIO(export_fit_params_csv(spectrum)))

        assert len(df) == 1
        assert df.iloc[0]["Peak_Label"] == "Peak 1"
        assert df.iloc[0]["Amplitude"] == pytest.approx(100.0, rel=1e-2)

    def test_omits_provenance_columns_and_raw_row(self):
        # Quick Export stays a compact table; provenance and the PL Raw row
        # belong to the archival master CSV only.
        spectrum = _make_spectrum_file(filename="pl.txt", mode="PL", with_fit=True)
        df = pd.read_csv(io.StringIO(export_fit_params_csv(spectrum)))

        assert "Convergence_Time_s" not in df.columns
        assert "X_Range_Limited" not in df.columns
        assert "Raw" not in df["Peak_Label"].values

    def test_shares_the_amplitude_convention_with_the_master_csv(self):
        spectrum = _make_spectrum_file(with_fit=True)
        quick = pd.read_csv(io.StringIO(export_fit_params_csv(spectrum)))
        master = pd.read_csv(io.StringIO(export_master_csv({"sample_raman.txt": spectrum})))

        for column in ("Amplitude", "Amplitude_Stderr", "Center", "FWHM"):
            assert quick.iloc[0][column] == master.iloc[0][column]
