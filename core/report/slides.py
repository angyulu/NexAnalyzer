"""
Renders a .pptx's slides to PNG images via PowerPoint COM automation, so
the Sample Report page can show an on-screen preview of the actual
generated report (not a second, independently-built approximation of it)
and save page images alongside the .pptx.

Runs in an isolated subprocess — the same pattern used for the tkinter
file/folder dialogs elsewhere in this app (src/io/export.py,
src/io/folder_picker.py) — rather than calling win32com in-process.
This isn't just style consistency: Streamlit executes page scripts on a
worker thread (never the main thread), and COM apartments are
thread-local — calling win32com.client.Dispatch() directly from that
thread was observed to raise an unrecoverable "Windows fatal exception:
code 0x80010108" (RPC_E_DISCONNECTED) that bypasses ordinary Python
exception handling entirely. A subprocess gets a clean, COM-initialized
main thread of its own, sidestepping the problem completely.

Requires Microsoft PowerPoint installed on this (Windows) machine. Not
unit-tested for the same reason the dialog functions aren't: it drives a
real desktop application, which is slow and environment-dependent.
"""

import os
import subprocess
import sys
import tempfile
from typing import List

_EXPORT_SCRIPT = """
import sys
import os

pptx_path = sys.argv[1]
out_dir = sys.argv[2]
width_px = int(sys.argv[3])
height_px = int(sys.argv[4])

import pythoncom
pythoncom.CoInitialize()
try:
    import win32com.client
    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    try:
        presentation = powerpoint.Presentations.Open(pptx_path, WithWindow=False)
        try:
            for index, slide in enumerate(presentation.Slides, start=1):
                out_path = os.path.join(out_dir, "slide_{}.png".format(index))
                slide.Export(out_path, "PNG", width_px, height_px)
        finally:
            presentation.Close()
    finally:
        powerpoint.Quit()
finally:
    pythoncom.CoUninitialize()
"""


def render_slides_to_png(pptx_bytes: bytes, width_px: int = 1920, height_px: int = 1080) -> List[bytes]:
    """
    Render each slide of `pptx_bytes` to a PNG image via PowerPoint COM
    automation (run in a subprocess), in slide order.

    Raises
    ------
    RuntimeError
        If PowerPoint COM automation is unavailable or fails (PowerPoint
        not installed, pywin32 missing, export timeout, etc). Callers
        should treat this as "no preview/export images available" rather
        than a fatal error — the .pptx itself is unaffected.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        pptx_path = os.path.join(tmp_dir, "report.pptx")
        with open(pptx_path, "wb") as f:
            f.write(pptx_bytes)

        out_dir = os.path.join(tmp_dir, "slides")
        os.makedirs(out_dir, exist_ok=True)

        script_path = os.path.join(tmp_dir, "export_slides.py")
        with open(script_path, "w") as f:
            f.write(_EXPORT_SCRIPT)

        try:
            result = subprocess.run(
                [sys.executable, script_path, pptx_path, out_dir, str(width_px), str(height_px)],
                capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"PowerPoint slide export timed out: {e}")

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
            raise RuntimeError(f"PowerPoint slide export failed: {detail}")

        png_bytes_list = []
        index = 1
        while True:
            slide_path = os.path.join(out_dir, f"slide_{index}.png")
            if not os.path.exists(slide_path):
                break
            with open(slide_path, "rb") as f:
                png_bytes_list.append(f.read())
            index += 1

        if not png_bytes_list:
            raise RuntimeError("PowerPoint slide export produced no images")

        return png_bytes_list
