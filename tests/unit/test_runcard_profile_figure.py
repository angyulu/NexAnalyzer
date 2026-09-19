"""Unit tests for modules.runcard.viz.profile (the reconstructed-recipe chart)."""

import plotly.graph_objects as go
import pytest

from modules.runcard.io.parser import parse_runcard
from modules.runcard.processing.growth_window import build_profile
from modules.runcard.processing.stats import profile_stats
from modules.runcard.viz import profile as profile_module
from modules.runcard.viz.profile import (
    FALLBACK_GAS_COLORS,
    GAS_COLORS,
    P1_COLOR,
    P2_COLOR,
    PC1_COLOR,
    _MIN_BAR_SPAN_FRACTION,
    build_profile_figure,
    summary_lines,
)
from tests.datalog_fixtures import RUNCARD_FULL, RUNCARD_SHORT

#: The final ramp completes after the heater went off, so there is no window.
_NO_WINDOW = "MFC/PC,PC-1,400\nWait,Sec,10\nHeater Ramp,900,10\nHeater Soak,0,--\nWait,Sec,60\n"

#: An instantaneous setpoint poke: two commands on one channel with no Wait
#: between them share a timestamp, so the first segment starts and ends at t=0
#: and the second runs 0 -> 60 s. `{}` takes the trailing Wait, because the
#: drawn minimum is a fraction of the recipe's own length.
_POKE = "MFC/PC,MFC-8 H2Se,3\nMFC/PC,MFC-8 H2Se,5\nWait,Sec,{}\n"


def _profile(tmp_path, text, name="recipe.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8", newline="")
    return build_profile(parse_runcard(str(path)))


def _bars(fig):
    return [trace for trace in fig.data if trace.type == "bar"]


def _bar(fig, label):
    return next(trace for trace in _bars(fig) if trace.y[0] == label)


def _markers(fig):
    return [t for t in fig.data if t.type == "scatter" and t.mode == "markers+text"]


def _brightness(color):
    """Sum of the three channels, so a lighter shade scores higher."""
    value = color.lstrip("#")
    return sum(int(value[i:i + 2], 16) for i in (0, 2, 4))


class TestBuildProfileFigure:
    def test_one_trace_per_heater_per_marker_run_and_per_gantt_row(self, tmp_path):
        # Three temperature lines, one marker trace carrying every marker, and
        # one bar trace per row -- not one per segment: a 40-command recipe is
        # ~45 segments, and 45 traces is 45 hover templates for no gain.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert isinstance(fig, go.Figure)
        assert [trace.type for trace in fig.data] == ["scatter"] * 4 + ["bar"] * 7
        assert fig.data[0].name == "Heater"
        assert [trace.y[0] for trace in _bars(fig)] == [
            "MFC-1 Ar", "MFC-3 O2", "MFC-8 H2Se", "RTV P", "PC-1", "PC-2", "Spin",
        ]

    def test_the_preheaters_carry_their_final_temperature_in_the_legend(self, tmp_path):
        # The ancestor drew these as end-of-line labels in the right margin and
        # had to offset P2's by 10 px whenever P1 was present, to stop the two
        # overlapping. A legend has no such collision.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert fig.data[1].name.startswith("P1 (40")
        assert fig.data[2].name.startswith("P2 (50")

    def test_a_recipe_with_no_preheaters_draws_no_preheater_lines(self, tmp_path):
        profile = _profile(tmp_path, RUNCARD_SHORT)

        fig = build_profile_figure("AAA00", profile)

        assert [trace.name for trace in fig.data if trace.type == "scatter"] == ["Heater"]

    def test_the_growth_band_is_drawn_where_the_window_is(self, tmp_path):
        # The shaded rect plus its two dashed edges, in minutes, and below
        # everything else so a 0.18-alpha wash never lightens a bar on top.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert [shape.type for shape in fig.layout.shapes] == ["rect", "line", "line"]
        band = fig.layout.shapes[0]
        assert (band.x0, band.x1) == pytest.approx((190 / 60, 310 / 60))
        assert band.layer == "below"

    def test_no_growth_band_is_drawn_when_there_is_no_window(self, tmp_path):
        # Guarded on `start_s is not None`, not on truthiness -- and the band,
        # the caption and the summary block have to agree about that.
        profile = _profile(tmp_path, _NO_WINDOW)

        fig = build_profile_figure("NOWIN", profile)

        assert fig.layout.shapes == ()
        assert [a.text for a in fig.layout.annotations] == []

    def test_the_band_is_captioned_with_its_duration_and_plateau(self, tmp_path):
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert "Growth (2 min @ 850" in fig.layout.annotations[0].text

    def test_markers_inside_the_growth_window_are_suppressed(self, tmp_path):
        # That stretch is already shaded and captioned, and the labels land on
        # top of the caption. RUNCARD_FULL opens H2Se at the window start and
        # closes it at the window end, so only the O2 marker survives.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        marker = _markers(fig)[0]
        assert marker.x == pytest.approx((10 / 60,))
        assert marker.text == ("O2 on",)

    def test_a_recipe_with_no_markers_draws_no_marker_trace(self, tmp_path):
        profile = _profile(tmp_path, RUNCARD_SHORT)

        fig = build_profile_figure("AAA00", profile)

        assert _markers(fig) == []

    def test_the_time_axis_is_in_minutes(self, tmp_path):
        # Seconds meant a hand-built tick list; minutes make the half-hour
        # ticks a plain dtick and match every number an operator quotes.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert fig.layout.xaxis.range == pytest.approx((0.0, 490 / 60))
        assert fig.layout.xaxis.dtick == 30
        assert fig.layout.xaxis.title.text == "Time (min)"

    def test_the_temperature_axis_is_gridded_at_zero_at_three_hundred_and_at_this_peak(self, tmp_path):
        # Three lines, one of which moves per recipe, is what makes the peak
        # readable off the axis without a ruler.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert fig.layout.yaxis.tickvals == (0, 300, 850)

    def test_the_scale_never_drops_below_the_comparison_floor(self, tmp_path):
        # An 850 and a 900 degree run are drawn on the same scale, so two
        # recipes can be read side by side.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert fig.layout.yaxis.range == (0.0, 900.0)

    def test_the_figure_grows_with_the_gantt(self, tmp_path):
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert fig.layout.height == profile_stats(profile)["canvas_h"]

    def test_a_rowless_figure_is_as_tall_as_the_height_the_page_exports_it_at(self, tmp_path):
        # The rowless figure reserves a row for its "no commands" note and came
        # out 530 px tall while canvas_h said 500. The page feeds canvas_h to
        # the layout and to export_figure_png, so the PNG was cropped by a row.
        profile = _profile(tmp_path, "Heater Ramp,900,10\nWait,Sec,60\n")

        fig = build_profile_figure("BARE", profile)

        assert fig.layout.height == profile_stats(profile)["canvas_h"]

    def test_an_instantaneous_setpoint_change_still_draws_a_visible_tick(self, tmp_path):
        # A zero-width Plotly bar draws nothing at all, so the operator read a
        # gap at exactly the moment the recipe did something. The ancestor
        # clamped every bar to one pixel; the minimum here is in data units and
        # scales with the recipe, because a Plotly bar has no pixel width and
        # the figure is drawn at whatever width the browser gives it.
        profile = _profile(tmp_path, _POKE.format(60))

        fig = build_profile_figure("POKE", profile)

        bar = _bar(fig, "MFC-8 H2Se")
        assert bar.base[0] == 0.0
        # The recipe is one minute long, so the floor is that fraction of 1.0.
        assert bar.x[0] == pytest.approx(_MIN_BAR_SPAN_FRACTION)

    def test_the_widened_tick_still_hovers_its_true_start_and_end(self, tmp_path):
        # The whole point of widening in the drawing and not in the data: the
        # hover box is where an operator finds out the event was an instant,
        # and it must not report the width the tick was padded to.
        profile = _profile(tmp_path, _POKE.format(60))

        fig = build_profile_figure("POKE", profile)

        bar = _bar(fig, "MFC-8 H2Se")
        start_min, end_min, value = bar.customdata[0]
        assert (start_min, end_min, value) == (0.0, 0.0, 3.0)
        # The two really are different numbers: the tick is drawn wider than
        # the span the hover reports, which is the whole arrangement.
        assert bar.x[0] > end_min - start_min

    def test_a_segment_wider_than_the_minimum_keeps_its_true_width(self, tmp_path):
        # Only segments already too narrow to read are widened; the second
        # segment of this recipe runs the whole minute and is drawn as one.
        profile = _profile(tmp_path, _POKE.format(60))

        fig = build_profile_figure("POKE", profile)

        assert _bar(fig, "MFC-8 H2Se").x[1] == pytest.approx(1.0)

    def test_the_minimum_span_scales_with_the_recipes_own_length(self, tmp_path):
        # A fixed number of seconds is invisible on a 130-minute card and a fat
        # block on a five-minute one. Ten times the recipe, ten times the tick,
        # so the tick is the same size on the screen either way.
        short = _profile(tmp_path, _POKE.format(60), "short.csv")
        long_run = _profile(tmp_path, _POKE.format(600), "long.csv")

        short_tick = _bar(build_profile_figure("SHORT", short), "MFC-8 H2Se").x[0]
        long_tick = _bar(build_profile_figure("LONG", long_run), "MFC-8 H2Se").x[0]

        assert short_tick > 0
        assert long_tick == pytest.approx(short_tick * 10)

    def test_a_recipe_with_no_rows_still_gets_a_panel_to_say_so(self, tmp_path):
        profile = _profile(tmp_path, "Heater Ramp,900,10\nWait,Sec,60\n")

        fig = build_profile_figure("BARE", profile)

        assert _bars(fig) == []
        assert any("No gas, pressure or stage commands" in a.text for a in fig.layout.annotations)

    def test_a_row_the_recipe_left_shut_keeps_its_place(self, tmp_path):
        # An empty row needs an invisible zero-width bar or the Plotly category
        # disappears, and "commanded closed" becomes "never mentioned".
        profile = _profile(tmp_path, "MFC/PC,MFC-2 Ar,0\nWait,Sec,60\n")

        fig = build_profile_figure("SHUT", profile)

        assert [trace.y[0] for trace in _bars(fig)] == ["MFC-2 Ar"]
        assert fig.layout.yaxis2.categoryarray == ("MFC-2 Ar",)

    def test_the_row_labels_are_stacked_bottom_up(self, tmp_path):
        # Paper coordinates run bottom-up, so the axis array is the row order
        # reversed; the first row has to come out at the top.
        profile = _profile(tmp_path, RUNCARD_SHORT)

        fig = build_profile_figure("AAA00", profile)

        assert fig.layout.yaxis2.categoryarray == ("Spin", "PC-1", "MFC-1 Ar")

    def test_within_a_row_the_darker_bar_is_the_higher_setpoint(self, tmp_path):
        # Shaded per row rather than across the figure: a gas line running
        # 0-5 sccm and a controller running 0-400 Torr each use their own
        # range, or every gas row comes out white.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        fills = _bar(fig, "PC-1").marker.color
        assert fills[0] == PC1_COLOR  # 400 Torr, this row's own maximum
        assert _brightness(fills[1]) > _brightness(fills[0])

    def test_a_known_species_keeps_the_colour_it_has_always_had(self, tmp_path):
        # Growers read these plots beside years of old ones, and H2Se has been
        # pink on all of them.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert _bar(fig, "MFC-8 H2Se").marker.color == (GAS_COLORS["H2Se"][0],)

    def test_an_unknown_species_gets_the_same_fallback_colour_every_time(self, tmp_path):
        # It was FALLBACK[hash(name) % 2], and Python salts string hashes per
        # process, so the same recipe came out violet one morning and teal the
        # next. crc32 is stable across runs and machines.
        profile = _profile(tmp_path, "MFC/PC,MFC-9 Kr,5\nWait,Sec,60\n")

        first = build_profile_figure("KR", profile)
        second = build_profile_figure("KR", profile)

        assert _bar(first, "MFC-9 Kr").marker.color[0] in [fill for fill, _stroke in FALLBACK_GAS_COLORS]
        assert _bar(first, "MFC-9 Kr").marker.color == _bar(second, "MFC-9 Kr").marker.color

    def test_a_value_the_recipe_wrote_whole_is_printed_whole(self, tmp_path):
        # "20.0 sccm" inside a 40-pixel bar spends a third of its width on a
        # zero nobody typed.
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert _bar(fig, "MFC-1 Ar").text == ("20",)
        assert _bar(fig, "MFC-3 O2").text == ("0.1",)

    def test_a_run_id_from_a_filename_is_escaped(self, tmp_path):
        # Plotly renders a subset of HTML in titles, hover text and
        # annotations, and both of these came from disk.
        profile = _profile(tmp_path, "MFC/PC,MFC-1 <x> Ar,5\nWait,Sec,60\n")

        fig = build_profile_figure("<b>evil</b>", profile)

        assert "&lt;b&gt;evil&lt;/b&gt;" in fig.layout.title.text
        assert "<b>evil</b>" not in fig.layout.title.text
        assert fig.layout.yaxis2.categoryarray == ("MFC-1 &lt;x&gt; Ar",)

    def test_an_empty_recipe_does_not_collapse_the_time_axis(self, tmp_path):
        # A zero-wide x-axis is a Plotly error rather than an empty chart. The
        # page never asks for one -- list_runcards rejects it -- but this is a
        # public builder.
        fig = build_profile_figure("EMPTY", build_profile([]))

        assert fig.layout.xaxis.range == (0.0, 1.0)


class TestDeliberateDivergences:
    """The port's departures from the SVG renderer it replaces are written down.

    Nobody can tell a deliberate divergence from a porting slip by looking at
    the output, so the module docstring is where they are recorded and these
    tests are what keep the record from being deleted with the reasoning.
    """

    def test_the_rtv_row_is_labelled_rtv_p(self, tmp_path):
        # params[1] of RTV Pressure Ctrl is the commanded chamber-pressure
        # setpoint and params[0] the gauge range, so the row is a pressure row
        # and is named like one. This app briefly drew it as bare "RTV".
        profile = _profile(tmp_path, RUNCARD_FULL)

        fig = build_profile_figure("VBBE00", profile)

        assert "RTV P" in [trace.y[0] for trace in _bars(fig)]

    def test_the_rtv_reading_is_recorded_and_not_silent(self):
        # The app held the opposite reading for a while -- that the number was
        # neither the gauge range nor the achieved pressure, so calling it Torr
        # was a guess. Whichever way it is decided, the reasoning has to be
        # findable from the file rather than from a diff.
        doc = profile_module.__doc__

        assert "RTV P" in doc
        assert "gauge range" in doc

    def test_the_dropped_torr_unit_is_recorded_beside_it(self):
        # The older half of the same note, asserted so that a rewrite of the
        # paragraph cannot quietly take one of the two decisions with it.
        assert "Torr" in profile_module.__doc__


class TestSummaryLines:
    def test_the_recipes_own_summary_at_the_growth_midpoint(self, tmp_path):
        profile = _profile(tmp_path, RUNCARD_FULL)

        lines = summary_lines(profile)

        bodies = [body for body, _color, _bold in lines]
        assert bodies[0].startswith("Growth window")
        assert "850" in bodies[0]
        assert lines[0][2] is True
        assert "Gas chemistry: MFC-1 Ar 20 sccm" in bodies[1]
        assert "MFC-8 H2Se 3.5 sccm" in bodies[1]
        assert bodies[2].startswith("Pressure: PC-1 = 300 Torr")
        assert "Spin 10 rpm" in bodies[2]

    def test_the_rtv_number_is_printed_without_the_unit_it_never_had(self, tmp_path):
        # The ancestor printed it as Torr. It is params[1] of RTV Pressure
        # Ctrl, which ranges over {10, 60, 70, 90} while the measured tube
        # pressure during the controlled segment is ~7.9 Torr. The number is
        # reproduced exactly; the unit that misdescribed it is not.
        profile = _profile(tmp_path, RUNCARD_FULL)

        pressure_line = summary_lines(profile)[2][0]

        assert "RTV 60" in pressure_line
        assert "RTV 60 Torr" not in pressure_line

    def test_the_preheater_lines_carry_their_own_colours(self, tmp_path):
        profile = _profile(tmp_path, RUNCARD_FULL)

        lines = summary_lines(profile)

        assert lines[3][1] == P1_COLOR
        assert lines[4][1] == P2_COLOR

    def test_there_is_no_summary_without_a_growth_window(self, tmp_path):
        # Every line in it is a value read at the midpoint, and there is no
        # midpoint without a window.
        profile = _profile(tmp_path, _NO_WINDOW)

        assert summary_lines(profile) == []

    def test_a_long_gas_line_hangs_onto_a_continuation_line(self, tmp_path):
        # Eight channels overrun the figure's width, and the annotation has no
        # wrapping of its own -- an overrun is clipped by the figure edge.
        recipe = "".join(f"MFC/PC,MFC-{i} Xe{i},{i + 1}\n" for i in range(1, 9))
        profile = _profile(
            tmp_path,
            recipe + "Wait,Sec,10\nHeater Ramp,900,5\nWait,Sec,10\nHeater Soak,0,--\nWait,Sec,60\n",
        )

        lines = summary_lines(profile)

        assert lines[1][0].startswith("Gas chemistry: MFC-1 Xe1 2 sccm")
        assert lines[2][0].startswith("MFC-5 Xe5 6 sccm")
        assert lines[3][0].startswith("Pressure:")


class TestThePreheatersCombineWhenTheyTrackTogether:
    """Both preheaters held at one temperature is the ordinary case here.

    Two dashed traces at identical y render as a single line of uncertain
    identity with two legend entries both claiming it, so the reference draws
    one line labelled for the pair.
    """

    def test_identical_preheaters_draw_one_trace(self, tmp_path):
        profile = _profile(
            tmp_path,
            "P1_Heater Ramp,40,60\nP2_Heater Ramp,40,60\n"
            "Wait,Sec,10\nHeater Ramp,900,10\nWait,Sec,10\n"
            "Heater Soak,0,--\nWait,Sec,60\n",
        )

        fig = build_profile_figure("PAIR", profile)
        names = [t.name for t in fig.data if t.name]

        assert any(n.startswith("P1/P2") for n in names)
        assert not any(n.startswith("P1 ") or n.startswith("P2 ") for n in names)

    def test_preheaters_that_differ_keep_their_own_traces(self, tmp_path):
        profile = _profile(
            tmp_path,
            "P1_Heater Ramp,40,60\nP2_Heater Ramp,90,60\n"
            "Wait,Sec,10\nHeater Ramp,900,10\nWait,Sec,10\n"
            "Heater Soak,0,--\nWait,Sec,60\n",
        )

        fig = build_profile_figure("SPLIT", profile)
        names = [t.name for t in fig.data if t.name]

        assert not any(n.startswith("P1/P2") for n in names)
        assert any(n.startswith("P1 ") for n in names)
        assert any(n.startswith("P2 ") for n in names)

    def test_only_one_preheater_is_not_reported_as_a_pair(self, tmp_path):
        # `_tracks_identically` is False whenever either trace is empty, so a
        # recipe addressing only P1 keeps P1's own colour and label.
        profile = _profile(
            tmp_path,
            "P1_Heater Ramp,40,60\nWait,Sec,10\nHeater Ramp,900,10\n"
            "Wait,Sec,10\nHeater Soak,0,--\nWait,Sec,60\n",
        )

        fig = build_profile_figure("ONE", profile)
        names = [t.name for t in fig.data if t.name]

        assert any(n.startswith("P1 ") for n in names)
        assert not any(n.startswith("P1/P2") for n in names)
