"""Unit tests for modules.runcard.io.parser (runcard CSV reading and folder listing)."""

import os

import pytest

from modules.runcard.io import parser
from modules.runcard.io.parser import (
    RuncardCommand,
    derive_run_id,
    file_mtime,
    list_runcards,
    load_runcard,
    parse_runcard,
)
from tests.datalog_fixtures import DATALOG_SHORT, RUNCARD_FULL, RUNCARD_SHORT

_NO_CLOCK = "Heater Ramp,850,120\nStage Rot,10,--\nEnd,--,--\n"
_MALFORMED = "Heater Ramp,abc,--\nWait,Sec,10\nEnd,--,--\n"


def _write_runcard(folder, text=RUNCARD_FULL, name="VBBE00.csv", encoding="utf-8"):
    """Write `text` into `folder` and return its absolute path, as a str.

    `newline=""` because the real cards are CRLF and `csv` is what has to see
    the line endings, not Python's text layer. A str rather than a Path,
    because that is what the page stores and what the parse cache keys on.
    """
    path = folder / name
    path.write_text(text, encoding=encoding, newline="")
    return str(path)


def _explode(*args, **kwargs):
    raise AssertionError("the file was read again")


class TestParseRuncard:
    def test_the_padding_rows_after_end_are_dropped(self, tmp_path):
        # RUNCARD_FULL carries three `--,--,--` rows past its End; a real VBBE
        # card carries 981 and a HAD card 975, so no count here may be assumed
        # from the file's length.
        path = _write_runcard(tmp_path)

        commands = parse_runcard(path)

        assert len(commands) == 23

    def test_end_is_kept_and_is_the_last_command(self, tmp_path):
        # The CLI this was ported from dropped End and scanned to EOF, so every
        # index here is one different from that reference.
        path = _write_runcard(tmp_path)

        commands = parse_runcard(path)

        assert commands[-1] == RuncardCommand(index=22, name="End", params=("--", "--"))

    def test_index_counts_surviving_commands_not_csv_lines(self, tmp_path):
        path = _write_runcard(
            tmp_path, "--,--,--\nWait,Sec,10\n--,--,--\nWait,Sec,20\nEnd,--,--\n", "padded.csv"
        )

        commands = parse_runcard(path)

        assert [cmd.index for cmd in commands] == [0, 1, 2]

    def test_rows_with_fewer_than_three_cells_are_skipped(self, tmp_path):
        # The blank line is what `csv` yields as `[]`; the two-cell row is a
        # truncated write.
        path = _write_runcard(tmp_path, "Wait,Sec\n\nWait,Sec,10\nEnd,--,--\n", "short_rows.csv")

        commands = parse_runcard(path)

        assert [cmd.name for cmd in commands] == ["Wait", "End"]

    def test_cells_are_stripped_before_the_padding_test(self, tmp_path):
        path = _write_runcard(tmp_path, " -- , -- , -- \n Wait , Sec , 10 \nEnd,--,--\n", "spaced.csv")

        commands = parse_runcard(path)

        assert commands[0] == RuncardCommand(index=0, name="Wait", params=("Sec", "10"))

    def test_a_row_with_an_empty_first_cell_is_skipped(self, tmp_path):
        path = _write_runcard(tmp_path, ",Sec,10\nWait,Sec,10\nEnd,--,--\n", "headless.csv")

        commands = parse_runcard(path)

        assert [cmd.name for cmd in commands] == ["Wait", "End"]

    def test_a_datalog_parses_loudly_rather_than_raising(self, tmp_path):
        # This is what makes `total_time <= 0` the validity gate rather than the
        # row shape: a datalog export in the same folder parses happily, into
        # one command named after the header and one per timestamp.
        path = _write_runcard(tmp_path, DATALOG_SHORT, "2026-08-06_173312~VBBE00.csv")

        commands = parse_runcard(path)

        assert len(commands) == 37
        assert commands[0].name == "Time"
        assert len(commands[0].params) == 11
        assert commands[1].name == "2026/08/06 17:33:12"

    def test_a_bom_does_not_corrupt_the_first_command(self, tmp_path):
        # utf-8, not utf-8-sig, would make this `﻿Stage Rot` -- a name no
        # dispatch branch matches, so the command is dropped with no error at
        # all. It is the one corruption this format cannot report.
        path = _write_runcard(tmp_path, RUNCARD_SHORT, "bom.csv", encoding="utf-8-sig")

        commands = parse_runcard(path)

        assert commands[0] == RuncardCommand(index=0, name="Stage Rot", params=("10", "--"))

    def test_a_file_with_no_end_parses_to_the_last_row(self, tmp_path):
        path = _write_runcard(tmp_path, "Wait,Sec,10\nWait,Sec,20\n", "unterminated.csv")

        commands = parse_runcard(path)

        assert [cmd.name for cmd in commands] == ["Wait", "Wait"]

    def test_params_hold_every_column_after_the_first(self, tmp_path):
        path = _write_runcard(tmp_path, "Wait,Sec,10,extra,more\nEnd,--,--\n", "ragged.csv")

        commands = parse_runcard(path)

        assert commands[0].params == ("Sec", "10", "extra", "more")

    def test_a_missing_file_raises(self, tmp_path):
        with pytest.raises(OSError):
            parse_runcard(str(tmp_path / "does_not_exist.csv"))


class TestLoadRuncard:
    """The memoized door, keyed on the path **and** its mtime.

    A path-only key serves the pre-edit program for the life of the process,
    and editing a recipe in place is the normal way these files change.
    """

    def test_it_returns_what_parse_runcard_returns(self, tmp_path):
        path = _write_runcard(tmp_path)

        assert load_runcard(path) == parse_runcard(path)

    def test_a_repeat_call_does_not_read_the_file_again(self, tmp_path, monkeypatch):
        path = _write_runcard(tmp_path, RUNCARD_SHORT, "AAA00.csv")
        os.utime(path, (1_700_000_000, 1_700_000_000))  # pin the cache key
        first = load_runcard(path)

        monkeypatch.setattr(parser, "parse_runcard", _explode)

        assert load_runcard(path) == first

    def test_a_recipe_edited_in_place_is_read_again(self, tmp_path):
        path = _write_runcard(tmp_path, RUNCARD_FULL, "AAA00.csv")
        assert len(load_runcard(path)) == 23

        _write_runcard(tmp_path, RUNCARD_SHORT, "AAA00.csv")
        os.utime(path, (1_700_000_000, 1_700_000_000))

        assert len(load_runcard(path)) == 12

    def test_a_missing_file_raises_rather_than_caching_an_empty_program(self, tmp_path):
        # The unstat-able file gets mtime -1.0 and still reaches the open(),
        # which is what says what is actually wrong with it.
        with pytest.raises(OSError):
            load_runcard(str(tmp_path / "does_not_exist.csv"))


class TestListRuncards:
    def test_recipes_are_found_recursively(self, tmp_path):
        _write_runcard(tmp_path, RUNCARD_FULL, "VBBE00.csv")
        (tmp_path / "sub").mkdir()
        _write_runcard(tmp_path / "sub", RUNCARD_SHORT, "AAA00.csv")

        found = list_runcards(str(tmp_path))

        assert {os.path.relpath(p, str(tmp_path)) for p in found} == {
            "VBBE00.csv",
            os.path.join("sub", "AAA00.csv"),
        }

    def test_a_datalog_in_the_same_folder_is_not_a_recipe(self, tmp_path):
        # Recipes and the tool's own datalog exports live in one folder. The
        # datalog parses to 37 commands, none of which advances the clock.
        _write_runcard(tmp_path, RUNCARD_FULL, "VBBE00.csv")
        _write_runcard(tmp_path, DATALOG_SHORT, "2026-08-06_173312~VBBE00.csv")

        found = list_runcards(str(tmp_path))

        assert [os.path.basename(p) for p in found] == ["VBBE00.csv"]

    def test_one_malformed_recipe_costs_only_its_own_row(self, tmp_path):
        # `Heater Ramp,abc,--` raises ValueError out of the validity gate. The
        # ported version caught only OSError and UnicodeDecodeError there, so
        # one bad file anywhere in the tree cost the operator the whole listing.
        _write_runcard(tmp_path, _MALFORMED, "broken.csv")
        _write_runcard(tmp_path, RUNCARD_FULL, "VBBE00.csv")

        found = list_runcards(str(tmp_path))

        assert [os.path.basename(p) for p in found] == ["VBBE00.csv"]

    def test_a_truncated_recipe_costs_only_its_own_row(self, tmp_path):
        # Two-cell rows never reach the timeline -- the parser drops them for
        # their shape -- so this file survives as a lone `End` and is rejected
        # by the clock gate instead.
        _write_runcard(tmp_path, "Wait,Sec\nHeater Ramp,850\nEnd,--,--\n", "truncated.csv")
        _write_runcard(tmp_path, RUNCARD_FULL, "VBBE00.csv")

        found = list_runcards(str(tmp_path))

        assert [os.path.basename(p) for p in found] == ["VBBE00.csv"]

    def test_a_file_that_never_advances_the_clock_is_not_a_recipe(self, tmp_path):
        _write_runcard(tmp_path, _NO_CLOCK, "no_wait.csv")

        assert list_runcards(str(tmp_path)) == []

    def test_a_file_with_no_commands_at_all_is_not_a_recipe(self, tmp_path):
        _write_runcard(tmp_path, "", "empty.csv")
        _write_runcard(tmp_path, "--,--,--\n--,--,--\n", "padding_only.csv")

        assert list_runcards(str(tmp_path)) == []

    def test_results_come_back_in_path_order_as_strings(self, tmp_path):
        for name in ("ccc.csv", "aaa.csv", "bbb.csv"):
            _write_runcard(tmp_path, RUNCARD_SHORT, name)

        found = list_runcards(str(tmp_path))

        assert [os.path.basename(p) for p in found] == ["aaa.csv", "bbb.csv", "ccc.csv"]
        assert all(isinstance(p, str) for p in found)

    def test_a_missing_folder_is_not_an_error(self, tmp_path):
        # An archive on a share that went away must not stop the page opening.
        assert list_runcards(str(tmp_path / "not_there")) == []

    def test_a_file_where_a_folder_was_expected_is_not_an_error(self, tmp_path):
        path = _write_runcard(tmp_path)

        assert list_runcards(path) == []


class TestDeriveRunId:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("VBBE00.csv", "VBBE00"),
            ("0810_VBBE00.csv", "VBBE00"),               # operators prefix the export date
            ("VBBE00_runcard.csv", "VBBE00"),            # and suffix the word runcard
            ("VBBE00_RUNCARD.CSV", "VBBE00"),            # in whichever case they typed it
            ("0810_VBBE00_runcard.csv", "VBBE00"),
            ("20240810_a_b.csv", "A_B"),                 # only the leading segment goes
            ("runcard.csv", "RUNCARD"),                  # no underscore, nothing to strip
            ("HADG37_runcard_v2.csv", "HADG37_RUNCARD_V2"),  # _runcard is end-anchored
        ],
    )
    def test_the_display_name_a_filename_is_carrying(self, filename, expected):
        assert derive_run_id(filename) == expected

    def test_the_folder_a_recipe_sits_in_is_not_part_of_its_name(self, tmp_path):
        path = _write_runcard(tmp_path, RUNCARD_FULL, "0810_VBBE00_runcard.csv")

        assert derive_run_id(path) == "VBBE00"


class TestFileMtime:
    """The only date a recipe carries.

    A runcard's own clock starts at zero and the CSV records nothing about when
    it was written, so "which of these is the latest" can only be asked of the
    filesystem. The same number is `load_runcard`'s cache key, which is why it
    is one public function rather than two private ones that could drift.
    """

    def test_it_reports_the_files_modification_time(self, tmp_path):
        path = tmp_path / "VBBE00.csv"
        path.write_text(RUNCARD_FULL, encoding="utf-8", newline="")
        os.utime(path, (1_000_000_000, 1_000_000_000))

        assert file_mtime(str(path)) == pytest.approx(1_000_000_000)

    def test_a_file_that_cannot_be_statted_is_minus_one(self, tmp_path):
        # Not an exception and not 0: the Runcard table renders this as an
        # empty cell and sorts it last, where a 0 would read as 1970 and sort
        # among real dates.
        assert file_mtime(str(tmp_path / "does-not-exist.csv")) == -1.0
