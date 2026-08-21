"""
Technique-agnostic export plumbing: a native Save-As dialog, figure
rasterization, and output filename construction.

Fit-results CSVs live in results_csv.py — this module knows nothing about
peaks or spectra.
"""

from typing import Optional


def prompt_save_path(default_dir: Optional[str],
                     default_filename: str,
                     title: str = "Save File",
                     filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
                     default_extension: str = ".csv") -> Optional[str]:
    """
    Open a native OS "Save As" dialog and return the chosen path.

    Runs tkinter.filedialog.asksaveasfilename in a subprocess (the same pattern
    used by the "Browse Spectrum Files" button), so the user can choose the
    folder AND type the filename. The dialog opens pre-pointed at ``default_dir``
    with ``default_filename`` pre-filled.

    Parameters
    ----------
    default_dir : Optional[str]
        Folder to open the dialog in. If None/empty/nonexistent, the OS default
        is used.
    default_filename : str
        Pre-filled filename in the dialog (user can edit).
    title : str
        Dialog window title.
    filetypes : tuple
        (label, pattern) pairs for the file-type filter.
    default_extension : str
        Extension appended if the user types a name without one.

    Returns
    -------
    Optional[str]
        Absolute path chosen by the user, or None if the dialog was cancelled.
    """
    import subprocess
    import sys
    import os
    import tempfile
    import json

    # NOTE: asksaveasfilename returns a single path; serialize via json.dumps so
    # paths with spaces/commas/unicode round-trip safely across the subprocess.
    dialog_script = """
import tkinter as tk
from tkinter import filedialog
import sys
import json

root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)

initial_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ""
initial_file = sys.argv[2] if len(sys.argv) > 2 else ""
default_ext = sys.argv[3] if len(sys.argv) > 3 else ""

path = filedialog.asksaveasfilename(
    title="__TITLE__",
    initialdir=initial_dir,
    initialfile=initial_file,
    defaultextension=default_ext,
    filetypes=__FILETYPES__
)

root.destroy()
print(json.dumps(path))
"""
    # Inject title and filetypes (kept simple: title has no quotes/newlines).
    dialog_script = dialog_script.replace("__TITLE__", title)
    dialog_script = dialog_script.replace("__FILETYPES__", repr([list(ft) for ft in filetypes]))

    safe_dir = default_dir if (default_dir and os.path.isdir(default_dir)) else ""

    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(dialog_script)
            script_path = f.name

        result = subprocess.run(
            [sys.executable, script_path, safe_dir, default_filename, default_extension],
            capture_output=True,
            text=True,
            timeout=300
        )
    finally:
        if script_path and os.path.exists(script_path):
            os.unlink(script_path)

    raw = result.stdout.strip()
    if not raw:
        return None
    path = json.loads(raw)
    # Empty string => user cancelled the dialog.
    return path if path else None
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
