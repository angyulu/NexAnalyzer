"""
Export functions for CSV, PNG, and HTML formats.

This module provides functions to:
- Export fitted peak parameters to CSV (master table)
- Export composite plots to PNG and HTML
- Generate publication-quality figures
"""

import pandas as pd
import numpy as np
from typing import Dict
import io


def export_master_csv(files: Dict) -> str:
    """
    Export all fitted peaks from all files to a master CSV.

    Parameters
    ----------
    files : Dict[str, SpectrumFile]
        Dictionary of filename -> SpectrumFile.

    Returns
    -------
    csv_string : str
        CSV content as string.

    Notes
    -----
    CSV format (FR-045 to FR-047):
    - One row per peak per file
    - Columns: Filename, Peak_Label, Center, Center_Stderr, Amplitude,
      Amplitude_Stderr, FWHM, FWHM_Stderr, Shape, R_Squared, Chi_Squared

    Examples
    --------
    >>> csv = export_master_csv(st.session_state['files'])
    >>> with open('results.csv', 'w') as f:
    ...     f.write(csv)
    """
    rows = []

    for filename, spectrum in files.items():
        if spectrum.fit_result is None or not spectrum.fit_result.success:
            continue

        # PL mode only: prepend a Raw row holding raw spectrum stats
        # (max Y, its x, and FWHM at half-max) before the peak rows.
        if spectrum.mode == "PL":
            y_data = spectrum.processed_data.Y
            x_data = spectrum.processed_data.X
            if len(y_data) > 0:
                imax = int(np.argmax(y_data))
                raw_intensity = float(y_data[imax])
                raw_center = float(x_data[imax])
                if raw_intensity > 0:
                    above = y_data >= raw_intensity / 2.0
                    if above.any():
                        idxs = np.where(above)[0]
                        raw_fwhm: object = float(x_data[idxs[-1]] - x_data[idxs[0]])
                    else:
                        raw_fwhm = ""
                else:
                    raw_fwhm = ""

                rows.append({
                    "Filename": filename,
                    "Mode": spectrum.mode,
                    "Auto_Detected": spectrum.auto_detected,
                    "X_Range_Limited": spectrum.x_range_enabled,
                    "X_Min": spectrum.x_min if spectrum.x_range_enabled else "",
                    "X_Max": spectrum.x_max if spectrum.x_range_enabled else "",
                    "Peak_Label": "Raw",
                    "Center": raw_center,
                    "Center_Stderr": "",
                    "Amplitude": raw_intensity,
                    "Amplitude_Stderr": "",
                    "FWHM": raw_fwhm,
                    "FWHM_Stderr": "",
                    "Shape": "",
                    "R_Squared": "",
                    "Chi_Squared": "",
                    "Convergence_Time_s": ""
                })

        for peak in spectrum.fit_result.fitted_peaks:
            # Peak height (Amplitude in this CSV) = max of the fitted component curve.
            # peak.amplitude from lmfit is integrated intensity (height × FWHM × 1.064);
            # users want height, so we sample the component curve directly.
            if peak.component_curve is not None and len(peak.component_curve) > 0:
                height = float(np.max(peak.component_curve))
                # Scale stderr by the same height/integrated ratio (linear approximation).
                if peak.amplitude > 0:
                    height_stderr = float(peak.amplitude_stderr) * (height / peak.amplitude)
                else:
                    height_stderr = 0.0
            else:
                height = float(peak.amplitude)
                height_stderr = float(peak.amplitude_stderr)

            rows.append({
                "Filename": filename,
                "Mode": spectrum.mode,
                # v2.1 new columns
                "Auto_Detected": spectrum.auto_detected,
                "X_Range_Limited": spectrum.x_range_enabled,
                "X_Min": spectrum.x_min if spectrum.x_range_enabled else "",
                "X_Max": spectrum.x_max if spectrum.x_range_enabled else "",
                # Existing columns
                "Peak_Label": peak.label,
                "Center": peak.center,
                "Center_Stderr": peak.center_stderr,
                "Amplitude": height,
                "Amplitude_Stderr": height_stderr,
                "FWHM": peak.width_fwhm,
                "FWHM_Stderr": peak.width_stderr,
                "Shape": peak.shape,
                "R_Squared": spectrum.fit_result.r_squared,
                "Chi_Squared": spectrum.fit_result.chi_squared,
                "Convergence_Time_s": spectrum.fit_result.convergence_time
            })

    if len(rows) == 0:
        return "# No fit results to export\n"

    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def export_single_spectrum_csv(spectrum, include_fit: bool = True) -> str:
    """
    Export a single spectrum's data and fit to CSV.

    Parameters
    ----------
    spectrum : SpectrumFile
        Spectrum to export.
    include_fit : bool, default=True
        Whether to include fit curve and residuals (requires fit_result).

    Returns
    -------
    csv_string : str
        CSV content as string.

    Notes
    -----
    CSV columns:
    - X: Wavenumber or wavelength
    - Y_Raw: Original intensity
    - Y_Processed: After despike/baseline
    - Y_Fit: Total fit curve (if include_fit and fit exists)
    - Residual: Y_Processed - Y_Fit (if include_fit and fit exists)
    - Peak1, Peak2, ...: Individual component curves (if include_fit)
    """
    data = {
        "X": spectrum.raw_data.X,
        "Y_Raw": spectrum.raw_data.Y,
        "Y_Processed": spectrum.processed_data.Y
    }

    if include_fit and spectrum.fit_result and spectrum.fit_result.success:
        data["Y_Fit"] = spectrum.fit_result.total_fit_curve
        data["Residual"] = spectrum.fit_result.residuals

        # Add individual peak components
        for i, peak in enumerate(spectrum.fit_result.fitted_peaks):
            col_name = f"{peak.label or f'Peak_{i+1}'}"
            data[col_name] = peak.component_curve

    df = pd.DataFrame(data)
    return df.to_csv(index=False)


def export_figure_png(fig, width: int = 1200, height: int = 600, scale: float = 2.0) -> bytes:
    """
    Export Plotly figure to PNG bytes.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        Figure to export.
    width : int, default=1200
        Image width in pixels.
    height : int, default=600
        Image height in pixels.
    scale : float, default=2.0
        Scale factor for high-DPI displays (2.0 = retina quality).

    Returns
    -------
    png_bytes : bytes
        PNG image as bytes.

    Notes
    -----
    Requires kaleido package: pip install kaleido

    Examples
    --------
    >>> png = export_figure_png(fig)
    >>> with open('plot.png', 'wb') as f:
    ...     f.write(png)
    """
    try:
        png_bytes = fig.to_image(
            format='png',
            width=width,
            height=height,
            scale=scale,
            engine='kaleido'
        )
        return png_bytes
    except Exception as e:
        raise RuntimeError(
            f"PNG export failed: {e}. "
            f"Make sure kaleido is installed: pip install kaleido"
        )


def export_figure_html(fig) -> str:
    """
    Export Plotly figure to interactive HTML.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        Figure to export.

    Returns
    -------
    html_string : str
        Standalone HTML file content.

    Notes
    -----
    The HTML file is fully self-contained (includes Plotly.js library).
    Can be opened in any web browser with full interactivity.

    Examples
    --------
    >>> html = export_figure_html(fig)
    >>> with open('plot.html', 'w') as f:
    ...     f.write(html)
    """
    html_string = fig.to_html(
        include_plotlyjs='cdn',  # Use CDN for smaller file size
        full_html=True,
        config={'displayModeBar': True, 'displaylogo': False}
    )
    return html_string


def create_filename(base_name: str, suffix: str, extension: str) -> str:
    """
    Create safe filename for export.

    Parameters
    ----------
    base_name : str
        Base filename (e.g., spectrum filename without .txt).
    suffix : str
        Suffix to add (e.g., "fit", "preview").
    extension : str
        File extension (e.g., "csv", "png", "html").

    Returns
    -------
    filename : str
        Safe filename.

    Examples
    --------
    >>> create_filename("sample_raman.txt", "fit", "csv")
    'sample_raman_fit.csv'
    """
    # Remove original extension if present
    if base_name.endswith('.txt'):
        base_name = base_name[:-4]

    # Create new filename
    return f"{base_name}_{suffix}.{extension}"
