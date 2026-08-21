"""Unit tests for core.io.export (figure rasterization and output filenames).

prompt_save_path() is excluded: it spawns a real tkinter subprocess dialog
and is not practically unit-testable. Fit-results CSVs are covered by
test_results_csv.py.
"""

import plotly.graph_objects as go

from core.io.export import export_figure_html, create_filename


class TestExportFigureHtml:
    def test_produces_standalone_html(self):
        fig = go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[1, 4, 9])])
        html = export_figure_html(fig)
        assert html.strip().lower().startswith("<!doctype html>") or "<html" in html.lower()
        assert "plotly" in html.lower()


class TestCreateFilename:
    def test_strips_txt_extension(self):
        assert create_filename("sample_raman.txt", "fit", "csv") == "sample_raman_fit.csv"

    def test_no_extension_to_strip(self):
        assert create_filename("sample", "preview", "png") == "sample_preview.png"
