"""
Native folder-picker dialog for the Sample Report page.

No askdirectory pattern existed elsewhere in the app — this is modeled on
export.prompt_save_path()'s tkinter-subprocess/JSON round-trip pattern
(also used by the "Browse Spectrum Files" button in src/ui/sidebar.py).
"""

import json
import os
import subprocess
import sys
import tempfile
from typing import Optional


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

    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write(dialog_script)
            script_path = f.name

        result = subprocess.run(
            [sys.executable, script_path, safe_dir],
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
