"""
Native folder- and file-picker dialogs.

No askdirectory pattern existed elsewhere in the app — this is modeled on
export.prompt_save_path()'s tkinter-subprocess/JSON round-trip pattern
(also used by the "Browse Spectrum Files" button in modules/spectra/ui/sidebar.py).
"""

import json
import os
import subprocess
import sys
import tempfile
from typing import Optional, Sequence, Tuple


def _run_dialog(script: str, *args: str) -> Optional[str]:
    """Run a tkinter dialog script in a subprocess and return its JSON result.

    Isolated in a subprocess because tkinter cannot share a process with
    Streamlit's script runner, and serialized through JSON because a bare
    print() mangles paths containing spaces, commas or unicode.
    """
    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(script)
            script_path = f.name

        result = subprocess.run(
            [sys.executable, script_path, *args],
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
    return path if path else None


def prompt_folder_path(default_dir: Optional[str] = None, title: str = "Select Sample Folder") -> Optional[str]:
    """
    Open a native OS folder-picker dialog and return the chosen path.

    Runs tkinter.filedialog.askdirectory in a subprocess so paths with
    spaces/unicode round-trip safely via JSON.

    Returns
    -------
    Optional[str]
        Absolute folder path chosen by the user, or None if cancelled.
    """
    dialog_script = """
import tkinter as tk
from tkinter import filedialog
import sys
import json

root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)

initial_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ""

path = filedialog.askdirectory(
    title="__TITLE__",
    initialdir=initial_dir
)

root.destroy()
print(json.dumps(path))
"""
    dialog_script = dialog_script.replace("__TITLE__", title)

    safe_dir = default_dir if (default_dir and os.path.isdir(default_dir)) else ""
    return _run_dialog(dialog_script, safe_dir)


def prompt_open_path(
    default_dir: Optional[str] = None,
    title: str = "Select File",
    filetypes: Sequence[Tuple[str, str]] = (("Excel workbooks", "*.xlsx"), ("All files", "*.*")),
) -> Optional[str]:
    """
    Open a native OS file-open dialog and return the chosen path.

    The single-file counterpart to the sidebar's multi-select "Browse Spectrum
    Files" button, which inlines its own copy of this pattern. Lives here
    rather than in a module because a native dialog knows nothing about peaks
    or spectra — it is exactly what core/io is for.

    Parameters
    ----------
    default_dir : Optional[str]
        Folder to open the dialog in. Ignored if it doesn't exist, so a
        remembered path pointing at an unplugged drive doesn't fail the dialog.
    title : str
        Dialog window title.
    filetypes : Sequence[Tuple[str, str]]
        (label, pattern) pairs for the file-type filter.

    Returns
    -------
    Optional[str]
        Absolute path chosen by the user, or None if cancelled.
    """
    dialog_script = """
import tkinter as tk
from tkinter import filedialog
import sys
import json

root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)

initial_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ""
filetypes = [tuple(pair) for pair in json.loads(sys.argv[2])]

path = filedialog.askopenfilename(
    title="__TITLE__",
    initialdir=initial_dir,
    filetypes=filetypes
)

root.destroy()
print(json.dumps(path))
"""
    dialog_script = dialog_script.replace("__TITLE__", title)

    safe_dir = default_dir if (default_dir and os.path.isdir(default_dir)) else ""
    return _run_dialog(dialog_script, safe_dir, json.dumps([list(pair) for pair in filetypes]))
