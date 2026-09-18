"""
Unit tests for modules/dataviz/viz/scatter.py.

The distinction under test is the module's central one: a choice that would
*crash* Plotly is raised with a message naming the control, while a choice that
merely renders badly is reported as a warning and still drawn.
"""

import pandas as pd
import pytest

from modules.dataviz.viz import scatter


@pytest.fixture
def frame():
    return pd.DataFrame(
        {
            "t": [700, 890, 950, 890],
            "fwhm": [3.1, 3.4, 3.9, 3.5],
            "err": [0.1, 0.2, 0.1, 0.2],
            "tool": ["HA", "HA", "QUAD", "QUAD"],
            "wafer": ["A", "B", "C", "D"],
            "signed": [-1.0, 2.0, 3.0, 4.0],
        }
    )


class TestNumericColumns:
    def test_offers_only_numeric(self, frame):
        assert scatter.numeric_columns(frame) == ["t", "fwhm", "err", "signed"]


class TestBuildScatter:
    def test_minimal_config_draws(self, frame):
        fig = scatter.build_scatter(frame, {"x": "t", "y": "fwhm"})
        assert len(fig.data) == 1
        assert fig.layout.xaxis.title.text == "t"

    def test_colour_splits_into_traces(self, frame):
        fig = scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "color": "tool"})
        assert len(fig.data) == 2

    def test_error_bars_are_attached(self, frame):
        fig = scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "error_y": "err"})
        assert tuple(fig.data[0].error_y.array) == (0.1, 0.2, 0.1, 0.2)

    def test_log_and_range_are_applied(self, frame):
        fig = scatter.build_scatter(
            frame,
            {"x": "t", "y": "fwhm", "log_x": True, "range_y_min": 3.0, "range_y_max": 4.0},
        )
        assert fig.layout.xaxis.type == "log"
        assert tuple(fig.layout.yaxis.range) == (3.0, 4.0)

    def test_half_open_range_is_ignored(self, frame):
        """Plotly needs both ends; inventing the other would silently override
        the autoscaling the user still had."""
        fig = scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "range_y_min": 3.0})
        assert fig.layout.yaxis.range is None

    def test_title_is_set(self, frame):
        fig = scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "title": "FWHM vs T"})
        assert fig.layout.title.text == "FWHM vs T"

    def test_facets_produce_subplots(self, frame):
        fig = scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "facet_col": "tool"})
        assert fig.layout.xaxis2 is not None


class TestGuardedFailures:
    def test_missing_axes(self, frame):
        with pytest.raises(ValueError, match="Choose an X and a Y"):
            scatter.build_scatter(frame, {"x": "t"})

    def test_unknown_column_names_the_control(self, frame):
        with pytest.raises(ValueError, match="color = 'nope' is not a column"):
            scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "color": "nope"})

    def test_size_on_text_is_refused_with_a_useful_message(self, frame):
        with pytest.raises(ValueError, match="holds text"):
            scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "size": "wafer"})

    def test_size_on_negative_values_is_refused(self, frame):
        """Plotly raises here too, but says nothing about which control did it."""
        with pytest.raises(ValueError, match="negative"):
            scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "size": "signed"})

    def test_trendline_without_statsmodels_explains_the_fix(self, frame, monkeypatch):
        monkeypatch.setattr(scatter, "statsmodels_available", lambda: False)
        with pytest.raises(ValueError, match="statsmodels"):
            scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "trendline": "ols"})

    def test_trendline_choices_all_work_without_options(self, frame):
        """Every offered trendline must run on library defaults.

        "rolling", "expanding" and "ewm" are excluded from TRENDLINE_CHOICES
        precisely because they need a trendline_options window this panel does
        not expose -- a control that raises when used is worse than no control.
        """
        if not scatter.statsmodels_available():
            pytest.skip("statsmodels not installed")
        for choice in scatter.TRENDLINE_CHOICES:
            if not choice:
                continue
            scatter.build_scatter(frame, {"x": "t", "y": "fwhm", "trendline": choice})


class TestCardinalityWarnings:
    def test_quiet_for_reasonable_choices(self, frame):
        assert scatter.cardinality_warnings(frame, {"x": "t", "y": "fwhm", "color": "tool"}) == []

    def test_warns_about_a_high_cardinality_facet(self):
        df = pd.DataFrame({"x": range(50), "y": range(50), "id": [f"W{i}" for i in range(50)]})
        warnings = scatter.cardinality_warnings(df, {"x": "x", "y": "y", "facet_col": "id"})
        assert len(warnings) == 1
        assert "50 subplots" in warnings[0]

    def test_warns_about_a_long_discrete_legend(self):
        df = pd.DataFrame({"x": range(40), "y": range(40), "id": [f"W{i}" for i in range(40)]})
        warnings = scatter.cardinality_warnings(df, {"x": "x", "y": "y", "color": "id"})
        assert "40 entries" in warnings[0]

    def test_numeric_colour_is_continuous_and_never_warns(self):
        """A numeric colour is a colourbar, not a legend, so cardinality is
        irrelevant however many distinct values it has."""
        df = pd.DataFrame({"x": range(40), "y": range(40), "v": range(40)})
        assert scatter.cardinality_warnings(df, {"x": "x", "y": "y", "color": "v"}) == []

    def test_warnings_do_not_prevent_a_figure(self):
        df = pd.DataFrame({"x": range(40), "y": range(40), "id": [f"W{i}" for i in range(40)]})
        config = {"x": "x", "y": "y", "color": "id"}
        assert scatter.cardinality_warnings(df, config)
        assert scatter.build_scatter(df, config) is not None
