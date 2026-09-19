"""Unit tests for modules.datalog.viz.charts (the single-run and comparison figures)."""

import numpy as np
import pandas as pd

from modules.datalog.processing.analysis import (
    compute_deviation_pct,
    find_violation_mask,
)
from modules.datalog.viz.charts import (
    PV_COLOR,
    RUN_COLORS,
    SV_COLOR,
    VIOLATION_COLOR,
    _run_color,
    build_comparison_figure,
    build_single_run_figure,
    plot_item_label,
)

_PAIR_ITEM = {"kind": "pvsv", "pair_name": "X", "pv_col": "X PV", "sv_col": "X SV"}
_PLAIN_ITEM = {"kind": "plain", "channel": "Tube Pressure"}


def _frame(pv, sv):
    timestamps = pd.date_range("2026-08-06 17:33:12", periods=len(pv), freq="1s")
    return pd.DataFrame({
        "Time": timestamps,
        "X PV": pv,
        "X SV": sv,
        "Tube Pressure": np.linspace(0.01, 0.02, len(pv)),
    })


def _masks(df, tolerance_pct=5.0):
    deviation = compute_deviation_pct(df, "X PV", "X SV")
    return {"X": (find_violation_mask(deviation, tolerance_pct), deviation)}


class TestPlotItemLabel:
    def test_a_pair_answers_to_its_pair_name(self):
        assert plot_item_label(_PAIR_ITEM) == "X"

    def test_a_plain_channel_answers_to_its_column(self):
        assert plot_item_label(_PLAIN_ITEM) == "Tube Pressure"


class TestBuildSingleRunFigure:
    def test_one_panel_per_selected_channel(self):
        df = _frame([10.0, 10.0], [10.0, 10.0])

        fig = build_single_run_figure(df, [_PAIR_ITEM, _PLAIN_ITEM], {})

        assert [a.text for a in fig.layout.annotations] == ["X", "Tube Pressure"]
        assert fig.layout.yaxis.title.text == "X"
        assert fig.layout.yaxis2.title.text == "Tube Pressure"

    def test_a_pair_draws_the_process_value_solid_and_its_setpoint_dashed(self):
        # The figure carries no legend at all, so solid-versus-dashed is the
        # only thing telling PV from SV.
        df = _frame([10.0, 10.0], [10.0, 10.0])

        fig = build_single_run_figure(df, [_PAIR_ITEM], {})

        pv_trace, sv_trace = fig.data
        assert pv_trace.line.color == PV_COLOR
        assert pv_trace.line.dash is None
        assert sv_trace.line.color == SV_COLOR
        assert sv_trace.line.dash == "dash"

    def test_no_trace_asks_for_a_legend_entry(self):
        df = _frame([10.0, 20.0], [10.0, 10.0])

        fig = build_single_run_figure(df, [_PAIR_ITEM, _PLAIN_ITEM], _masks(df))

        assert [trace.showlegend for trace in fig.data] == [False, False, False, False]

    def test_out_of_tolerance_samples_are_marked_on_the_pv_trace_itself(self):
        # Full-length x, NaN everywhere in tolerance, so the dots land on the
        # offending part of the line rather than in a strip to be read back
        # against it.
        df = _frame([10.0, 20.0, 10.0], [10.0, 10.0, 10.0])

        fig = build_single_run_figure(df, [_PAIR_ITEM], _masks(df))

        marker_trace = fig.data[2]
        assert marker_trace.mode == "markers"
        assert marker_trace.marker.color == VIOLATION_COLOR
        assert len(marker_trace.x) == 3
        assert [v for v in marker_trace.y if not pd.isna(v)] == [20.0]

    def test_a_clean_pair_draws_no_marker_trace(self):
        df = _frame([10.0, 10.0], [10.0, 10.0])

        fig = build_single_run_figure(df, [_PAIR_ITEM], _masks(df))

        assert len(fig.data) == 2

    def test_a_pair_with_no_mask_at_all_still_draws(self):
        df = _frame([10.0, 20.0], [10.0, 10.0])

        fig = build_single_run_figure(df, [_PAIR_ITEM], {})

        assert len(fig.data) == 2

    def test_only_the_bottom_panel_labels_the_shared_x_axis(self):
        df = _frame([10.0, 10.0], [10.0, 10.0])

        fig = build_single_run_figure(df, [_PAIR_ITEM, _PLAIN_ITEM], {})

        assert fig.layout.xaxis.title.text is None
        assert fig.layout.xaxis2.title.text == "Time"


class TestBuildComparisonFigure:
    def test_x_is_seconds_from_each_runs_own_alignment_point(self):
        # Runs spend different amounts of time in load, pump-down and purge, so
        # overlaying on wall-clock start lines nothing up with anything.
        df = _frame([10.0] * 4, [10.0] * 4)

        fig = build_comparison_figure([("run a", df)], [_PAIR_ITEM], [df["Time"].iloc[2]])

        assert list(fig.data[0].x) == [-2.0, -1.0, 0.0, 1.0]

    def test_only_the_process_value_is_drawn(self):
        # This figure answers "did these runs do the same thing?"; setpoints and
        # violation markers belong to the single-run view.
        df = _frame([10.0, 20.0], [10.0, 10.0])

        fig = build_comparison_figure([("run a", df)], [_PAIR_ITEM], [df["Time"].iloc[0]])

        assert len(fig.data) == 1
        assert list(fig.data[0].y) == [10.0, 20.0]

    def test_one_run_is_one_color_down_the_whole_stack(self):
        df = _frame([10.0, 10.0], [10.0, 10.0])
        align = [df["Time"].iloc[0], df["Time"].iloc[0]]

        fig = build_comparison_figure(
            [("run a", df), ("run b", df)], [_PAIR_ITEM, _PLAIN_ITEM], align
        )

        colors = {trace.name: {t.line.color for t in fig.data if t.name == trace.name}
                  for trace in fig.data}
        assert colors["run a"] == {RUN_COLORS[0]}
        assert colors["run b"] == {RUN_COLORS[1]}

    def test_no_two_runs_share_a_color_past_the_end_of_the_palette(self):
        # Two runs the same color is the one failure a comparison cannot
        # survive, so the generated hues must not restart the list.
        df = _frame([10.0, 10.0], [10.0, 10.0])
        runs = [(f"run {i}", df) for i in range(len(RUN_COLORS) + 3)]

        fig = build_comparison_figure(runs, [_PAIR_ITEM], [df["Time"].iloc[0]] * len(runs))

        assert len({trace.line.color for trace in fig.data}) == len(runs)

    def test_a_run_whose_controller_logged_a_different_channel_set_is_skipped(self):
        # One missing channel costs that panel for that run, not the figure.
        full = _frame([10.0, 10.0], [10.0, 10.0])
        partial = full.drop(columns=["Tube Pressure"])
        align = [full["Time"].iloc[0], partial["Time"].iloc[0]]

        fig = build_comparison_figure(
            [("run a", full), ("run b", partial)], [_PAIR_ITEM, _PLAIN_ITEM], align
        )

        assert len(fig.data) == 3

    def test_the_x_axis_says_what_zero_means(self):
        # "seconds" on its own reads as run time.
        df = _frame([10.0, 10.0], [10.0, 10.0])

        fig = build_comparison_figure([("run a", df)], [_PAIR_ITEM], [df["Time"].iloc[0]])

        assert fig.layout.xaxis.title.text.startswith("Time relative to Heater SV")


class TestEveryLineTraceSaysSoExplicitly:
    """An unset mode means "lines+markers" below 20 points, not "lines".

    A short or aborted run -- the one a process engineer opens this page to look
    at -- therefore came out dotted while a normal run did not, and in the
    single-run figure those stray dots read as violation markers. The reference
    application pins mode="lines" on all four of these traces.
    """

    def test_a_short_run_still_draws_as_lines_not_dots(self):
        # Under 20 points, which is exactly where Plotly's default flips.
        df = _frame([10.0, 20.0, 10.0], [10.0, 10.0, 10.0])

        fig = build_single_run_figure(df, [_PAIR_ITEM, _PLAIN_ITEM], _masks(df))

        modes = {trace.name: trace.mode for trace in fig.data}
        assert modes["X PV"] == "lines"
        assert modes["X SV"] == "lines"
        assert modes["Tube Pressure"] == "lines"

    def test_the_violation_trace_is_still_the_only_one_drawing_markers(self):
        df = _frame([10.0, 20.0, 10.0], [10.0, 10.0, 10.0])

        fig = build_single_run_figure(df, [_PAIR_ITEM], _masks(df))

        assert [trace.mode for trace in fig.data] == ["lines", "lines", "markers"]

    def test_a_short_run_in_a_comparison_draws_as_lines(self):
        df = _frame([10.0, 10.0], [10.0, 10.0])

        fig = build_comparison_figure([("run a", df)], [_PAIR_ITEM], [df["Time"].iloc[0]])

        assert fig.data[0].mode == "lines"


class TestTheGeneratedHuesMatchTheReferenceApplication:
    """The golden-angle walk starts at the first *generated* run, not at run 0.

    Dropping the `index - len(RUN_COLORS)` offset samples the same sequence
    eight steps in, so run 9 comes out pink where datalog_monitor draws it red.
    Both are equally well spread -- the offset is what makes a chart from this
    app comparable with a chart from that one for the same run list.
    """

    def test_the_first_generated_color_starts_the_sequence_at_its_beginning(self):
        # hue 0 at saturation 0.65, value 0.85.
        assert _run_color(len(RUN_COLORS)) == "#d84b4b"

    def test_the_curated_palette_is_still_used_first(self):
        assert [_run_color(i) for i in range(len(RUN_COLORS))] == RUN_COLORS
