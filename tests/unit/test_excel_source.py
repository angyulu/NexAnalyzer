"""
Unit tests for modules/dataviz/io/excel_source.py.

The fixture workbook is modelled on the sheet this module was written against
(``Milestone and Schedule.xlsx``, ``HA_SplitTable``): two header rows where the
second is a unit, three columns sharing the name ``H2O``, a spacer column with
no header at all, columns mixing numbers with prose, ``/`` used to mean "not
applicable", and blank filler rows. Every one of those is a real property of
the file, not an invented edge case.
"""

import pandas as pd
import pytest
from openpyxl import Workbook

from modules.dataviz.io import excel_source as source


@pytest.fixture
def workbook(tmp_path):
    """A two-header-row sheet with the real file's awkward shapes."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Runs"

    ws.append(["WaferID", "P", "T", "H2O", "H2O", "H2O", "H2Se", None, "FWHM"])
    ws.append([None, "torr", "degC", "sccm", "sccm", "torr", "sccm", None, "E2g"])
    ws.append(["HAAA01", 65, 890, 50, 10, 175, 2, None, 35.5])
    ws.append(["HAAA02", 65, "950", "/", 30, "175/150", "1->4(0.2sccm)", None, None])
    ws.append([None, None, None, None, None, None, None, None, None])  # blank filler
    ws.append(["HAAA03", 90, 700, "/", "/", "/", "12min30s", None, "35.5-37.5"])

    second = wb.create_sheet("Empty")
    second.append(["A", "B"])
    second.append(["unit", "unit"])

    path = tmp_path / "runs.xlsx"
    wb.save(path)
    return str(path)


class TestListSheets:
    def test_counts_rows_below_the_headers(self, workbook):
        infos = {s.name: s for s in source.list_sheets(workbook, header_rows=2)}
        # Three wafers; the blank filler row is still counted here because the
        # picker's job is "does this sheet have content", and the loader's
        # blank-row drop is what reconciles the two.
        assert infos["Runs"].populated_rows == 3
        assert infos["Empty"].populated_rows == 0

    def test_header_rows_shifts_the_count(self, workbook):
        one = {s.name: s for s in source.list_sheets(workbook, header_rows=1)}
        # With one header row the unit row counts as data, which is exactly the
        # off-by-one the header_rows argument exists to prevent.
        assert one["Runs"].populated_rows == 4


class TestBuildLabels:
    def test_single_header_row_passes_through(self):
        assert source.build_labels([["A", "B"]]) == ["A", "B"]

    def test_qualifier_row_is_joined(self):
        labels = source.build_labels([["H2O", "FWHM"], ["torr", "E2g"]])
        assert labels == ["H2O (torr)", "FWHM (E2g)"]

    def test_empty_header_marks_a_column_for_dropping(self):
        assert source.build_labels([["A", None, "B"], [None, None, None]]) == ["A", None, "B"]

    def test_duplicates_are_suffixed_explicitly(self):
        labels = source.build_labels([["H2O", "H2O", "H2O"], ["sccm", "sccm", "torr"]])
        assert labels == ["H2O (sccm)", "H2O (sccm) #2", "H2O (torr)"]

    def test_qualifier_alone_names_the_column(self):
        assert source.build_labels([[None], ["torr"]]) == ["torr"]


class TestReadSheet:
    def test_joins_headers_and_drops_spacer_and_blank_rows(self, workbook):
        df = source.read_sheet(workbook, "Runs", header_rows=2)
        assert list(df.columns) == [
            "WaferID", "P (torr)", "T (degC)", "H2O (sccm)", "H2O (sccm) #2", "H2O (torr)",
            "H2Se (sccm)", "FWHM (E2g)",
        ]
        # Three wafers: the blank filler row is gone, the spacer column with it.
        assert len(df) == 3
        assert list(df["WaferID"]) == ["HAAA01", "HAAA02", "HAAA03"]

    def test_one_header_row_leaves_the_units_as_data(self, workbook):
        df = source.read_sheet(workbook, "Runs", header_rows=1)
        assert list(df["T"])[0] == "degC"

    def test_header_rows_beyond_the_sheet_is_an_error(self, workbook):
        with pytest.raises(ValueError, match="header row"):
            source.read_sheet(workbook, "Empty", header_rows=9)

    def test_header_rows_must_be_positive(self, workbook):
        with pytest.raises(ValueError, match="at least 1"):
            source.read_sheet(workbook, "Runs", header_rows=0)

    def test_numeric_column_infers_a_numeric_dtype(self, workbook):
        df = source.read_sheet(workbook, "Runs", header_rows=2)
        # Without infer_objects() a wholly numeric column comes back as object
        # -- because the header rows above it were strings -- and every axis
        # built on it would be categorical.
        assert pd.api.types.is_numeric_dtype(df["P (torr)"])
        # A single "/" is enough to keep a column out of that, which is exactly
        # what the coercion strategies exist to resolve.
        assert not pd.api.types.is_numeric_dtype(df["H2O (sccm) #2"])


class TestDropBlankRows:
    def test_a_row_of_slashes_survives(self):
        df = pd.DataFrame({"id": ["A", None], "flow": ["/", None]})
        kept = source.drop_blank_rows(df)
        # "/" means "not applicable", which is a statement about the run.
        assert len(kept) == 1
        assert kept.iloc[0]["flow"] == "/"

    def test_whitespace_only_row_is_blank(self):
        df = pd.DataFrame({"a": ["x", "   "], "b": ["y", ""]})
        assert len(source.drop_blank_rows(df)) == 1


class TestProfileColumns:
    def test_mixed_is_detected_and_examples_are_text_only(self, workbook):
        df = source.read_sheet(workbook, "Runs", header_rows=2)
        profiles = {p.name: p for p in source.profile_columns(df)}

        h2se = profiles["H2Se (sccm)"]
        assert h2se.kind == "mixed"
        assert h2se.numeric == 1 and h2se.text == 2
        assert "1->4(0.2sccm)" in h2se.examples
        assert all(not e.isdigit() for e in h2se.examples)

    def test_empty_column_is_named_as_such(self):
        profiles = source.profile_columns(pd.DataFrame({"a": [None, None]}))
        assert profiles[0].kind == "empty"
        assert profiles[0].filled == 0

    def test_null_markers_do_not_count_as_text(self):
        profiles = source.profile_columns(pd.DataFrame({"a": [1.0, "/", "NA"]}))
        assert profiles[0].kind == "numeric"
        assert profiles[0].filled == 1


class TestCoercion:
    def test_range_separator_is_not_a_minus_sign(self):
        """The regression this module's regex exists for.

        A naive number pattern reads "35.5-37.5" as 35.5 and -37.5, making the
        midpoint -1.0 instead of 36.5 -- a plausible-looking number that is
        wrong by 37.5.
        """
        series = pd.Series(["35.5-37.5"])
        assert source.coerce_column(series, "midpoint").values.iloc[0] == pytest.approx(36.5)
        assert source.coerce_column(series, "leading").values.iloc[0] == pytest.approx(35.5)

    def test_leading_number_reads_a_ramp_as_its_start(self):
        series = pd.Series(["1->4(0.2sccm)", "12min30s", "90(1000Torr)"])
        values = source.coerce_column(series, "leading").values
        assert list(values) == [1.0, 12.0, 90.0]

    def test_midpoint_averages_the_first_two_numbers(self):
        series = pd.Series(["1->4(0.2sccm)", "175/150"])
        values = source.coerce_column(series, "midpoint").values
        assert list(values) == [2.5, 162.5]

    def test_strict_blanks_anything_that_is_not_a_number(self):
        result = source.coerce_column(pd.Series([890, "950", "12min30s"]), "strict")
        assert list(result.values) == [890.0, 950.0, None] or (
            result.values.iloc[2] != result.values.iloc[2]  # NaN
        )
        assert result.lost == 1

    def test_null_markers_are_not_counted_as_lost(self):
        result = source.coerce_column(pd.Series([1, "/", "NA", None]), "strict")
        # Only the one real value was ever there, and it survived.
        assert result.lost == 0

    def test_none_returns_the_column_untouched(self):
        series = pd.Series(["a", 1])
        result = source.coerce_column(series, "none")
        assert result.lost == 0
        assert result.values is series

    def test_unknown_strategy_is_rejected(self):
        with pytest.raises(ValueError, match="Unknown coercion strategy"):
            source.coerce_column(pd.Series([1]), "guess")

    def test_negative_numbers_still_parse(self):
        assert source.coerce_column(pd.Series(["-5 sccm"]), "leading").values.iloc[0] == -5.0


class TestCoercionPreview:
    def test_shows_only_the_values_that_change(self):
        series = pd.Series([890, "12min30s", 700, "1->4"])
        pairs = source.coercion_preview(series, "leading")
        assert pairs == [("12min30s", "12"), ("1->4", "1")]

    def test_unparseable_value_previews_as_blank(self):
        assert source.coercion_preview(pd.Series(["TBC"]), "strict") == [("TBC", "(blank)")]

    def test_respects_the_limit(self):
        series = pd.Series([f"{i}min" for i in range(20)])
        assert len(source.coercion_preview(series, "leading", limit=3)) == 3


class TestApplyCoercions:
    def test_reports_losses_per_column(self):
        df = pd.DataFrame({"a": [1, "x"], "b": [2, 3]})
        out, losses = source.apply_coercions(df, {"a": "strict", "b": "strict"})
        assert losses == {"a": 1}
        assert list(out["b"]) == [2.0, 3.0]

    def test_a_column_the_sheet_lacks_is_ignored(self):
        """A config remembered against another sheet must not raise."""
        df = pd.DataFrame({"a": [1]})
        out, losses = source.apply_coercions(df, {"missing": "strict"})
        assert losses == {}
        assert list(out.columns) == ["a"]


class TestFilters:
    def test_keep_set_selects_rows(self):
        df = pd.DataFrame({"id": ["A", "B", "Cleaning"], "v": [1, 2, 3]})
        out = source.apply_filters(df, [source.RowFilter(column="id", keep=("A", "B"))])
        assert list(out["id"]) == ["A", "B"]

    def test_numeric_range_is_inclusive(self):
        df = pd.DataFrame({"t": [700, 890, 950]})
        out = source.apply_filters(df, [source.RowFilter(column="t", minimum=700, maximum=890)])
        assert list(out["t"]) == [700, 890]

    def test_blank_in_the_filtered_column_is_excluded(self):
        df = pd.DataFrame({"t": [700, None]})
        out = source.apply_filters(df, [source.RowFilter(column="t", minimum=0, maximum=10000)])
        assert len(out) == 1

    def test_missing_column_is_skipped_not_raised(self):
        df = pd.DataFrame({"a": [1, 2]})
        out = source.apply_filters(df, [source.RowFilter(column="gone", keep=("x",))])
        assert len(out) == 2

    def test_filters_compose(self):
        df = pd.DataFrame({"id": ["A", "B", "C"], "t": [700, 890, 950]})
        out = source.apply_filters(
            df,
            [
                source.RowFilter(column="id", keep=("A", "B")),
                source.RowFilter(column="t", minimum=800, maximum=1000),
            ],
        )
        assert list(out["id"]) == ["B"]


class TestDistinctValues:
    def test_sorted_and_blank_free(self):
        series = pd.Series(["B", "A", None, "  ", "A"])
        assert source.distinct_values(series) == ["A", "B"]

    def test_capped(self):
        series = pd.Series([str(i) for i in range(1000)])
        assert len(source.distinct_values(series, limit=10)) == 10
