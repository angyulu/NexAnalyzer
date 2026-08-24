"""The on-screen plot and the exported figures must style shared traces alike.

A Sample Report that doesn't look like the spectrum it came from is the bug
these tests exist to prevent: the two plotters each used to pick their own
colors, and drifted into a black dashed fit on screen versus a solid orange one
in the .pptx.
"""

import numpy as np

from core.report.pptx import _hex_to_rgb
from modules.spectra.viz import fit_plot, live_plot, palette


class _Peak:
    def __init__(self, label="Exciton", color="#123456", curve=None):
        self.label = label
        self.color = color
        self.component_curve = curve if curve is not None else np.array([0.0, 1.0, 0.0])


class _Fit:
    success = True

    def __init__(self):
        self.fitted_peaks = [_Peak()]
        self.total_fit_curve = np.array([0.0, 1.0, 0.0])
        self.residuals = np.array([0.0, 0.0, 0.0])


def _traces_by_name(fig):
    return {t.name: t for t in fig.data if t.name}


class TestBothPlottersShareOnePalette:
    def test_neither_plotter_hardcodes_a_shared_trace_color(self):
        """The colors live in palette.py; a literal in either plotter is how
        they drifted apart before."""
        for module in (fit_plot, live_plot):
            source = open(module.__file__, encoding="utf-8").read()
            for stray in ('color="blue"', "color='blue'", 'color="#1f77b4"',
                          'color="#ff7f0e"', 'color="#d62728"', 'color="green"',
                          'color="black"'):
                assert stray not in source, f"{module.__name__} hardcodes {stray}"

    def test_the_exported_figure_draws_the_palette_colors(self):
        x = np.array([0.0, 1.0, 2.0])
        fig = fit_plot.plot_composite(
            x, np.array([0.0, 1.0, 0.0]), _Fit(), mode="Raman",
            show_components=True, show_residuals=True,
        )
        traces = _traces_by_name(fig)

        assert traces["Data"].marker.color == palette.DATA_COLOR
        assert traces["Total Fit"].line.color == palette.FIT_TOTAL_COLOR
        assert traces["Total Fit"].line.dash == palette.FIT_TOTAL_DASH
        assert traces["Residuals"].marker.color == palette.RESIDUAL_COLOR

    def test_the_total_fit_is_dashed_and_the_components_are_not(self):
        """The two lines sit on top of each other for most of their length, so
        the dash is what tells them apart."""
        x = np.array([0.0, 1.0, 2.0])
        fig = fit_plot.plot_composite(
            x, np.array([0.0, 1.0, 0.0]), _Fit(), mode="Raman", show_components=True,
        )
        traces = _traces_by_name(fig)

        assert traces["Total Fit"].line.dash == "dash"
        assert traces["Exciton"].line.dash == palette.COMPONENT_DASH
        assert palette.COMPONENT_DASH is None  # i.e. solid
        assert traces["Exciton"].opacity == palette.COMPONENT_OPACITY

    def test_the_legend_swatches_survive_the_pptx_color_parser(self):
        """`_hex_to_rgb` falls back to black for anything it can't read, so a
        CSS name here would plot in color and draw a black swatch beside it."""
        for label, color in fit_plot.fit_legend_entries([_Fit()]):
            assert color.startswith("#") and len(color) == 7, (label, color)
            assert _hex_to_rgb(color) == _hex_to_rgb(color)  # parses without raising

        data_entry = dict(fit_plot.fit_legend_entries([_Fit()]))["Data"]
        assert _hex_to_rgb(data_entry) != _hex_to_rgb("not-a-color"), \
            "Data's swatch fell back to black, so it no longer matches its line"

    def test_the_palette_colors_are_the_css_names_the_screen_used(self):
        """Hex, not names — but the same colors the Spectra page always drew."""
        assert palette.DATA_COLOR == "#0000FF"      # blue
        assert palette.FIT_TOTAL_COLOR == "#000000"  # black
        assert palette.RESIDUAL_COLOR == "#008000"   # green

    def test_a_component_keeps_its_own_preset_color(self):
        """Only the style is shared; the color comes from the Material Preset so
        the same peak is the same color in every point's panel."""
        x = np.array([0.0, 1.0, 2.0])
        fig = fit_plot.plot_composite(
            x, np.array([0.0, 1.0, 0.0]), _Fit(), mode="Raman", show_components=True,
        )

        assert _traces_by_name(fig)["Exciton"].line.color == "#123456"


class TestPaletteIsOnlyForSharedTraces:
    def test_the_screen_only_layers_are_not_in_the_palette(self):
        """De-spiked, baseline-corrected and the live previews belong to the
        Spectra page alone; the report never draws them."""
        for name in ("DESPIKED_COLOR", "BASELINE_COLOR", "CORRECTED_COLOR", "PREVIEW_COLOR"):
            assert not hasattr(palette, name)
