"""Literal runcard and datalog CSV text for the Datalog and Runcard pages' tests.

The files these mimic live in a datalog_monitor sample folder outside this
repo, which no other machine has. Carrying the text here instead keeps the
suite self-contained, and matches how every other test in this suite builds
its input: nothing under tests/ is read from disk, it is written into tmp_path
first. (``tests/fixtures/*.txt`` is gitignored precisely because it holds real
customer data; a committed CSV there would mean the opposite of what the
directory says.)

Every number below is load-bearing -- the comment on each block says which
assertion it feeds. Editing one of them breaks a test somewhere that is not
obviously about that number.
"""

#: A full recipe, for the Runcard page's timeline. Never paired with a datalog:
#: its multi-minute Waits would need a 490-row one. ``Wait,Min,2`` is the only
#: unit conversion; ``Accumulation PC1`` and ``Stage Rot`` are the commands that
#: map to no column; ``MFC-3 O2,0.1`` sits just above the MFC "on" floor;
#: ``Heater Soak`` starts the cooldown; the two ``Heater Ramp``s make the growth
#: window a plateau rather than a point; the trailing ``--`` rows are the
#: padding a real runcard carries past ``End``.
RUNCARD_FULL = """\
Stage Rot,10,--
Pumping Forward,0.001,--
Wait,Sec,10
MFC/PC,MFC-1 Ar,20
MFC/PC,MFC-3 O2,0.1
MFC/PC,PC-1,400
MFC/PC,PC-2,140
RTV Pressure Ctrl,100 Torr,60
P1_Heater Ramp,40,60
P2_Heater Ramp,50,60
Heater Ramp,300,60
Wait,Sec,60
Heater Ramp,850,120
Accumulation PC1,300,20
Wait,Min,2
MFC/PC,MFC-8 H2Se,3.5
Wait,Sec,120
MFC/PC,MFC-8 H2Se,0
Heater Soak,0,--
Wait,Sec,120
Pumping Forward,0.05,--
Wait,Sec,60
End,--,--
--,--,--
--,--,--
--,--,--
"""

#: The recipe DATALOG_SHORT was written against: 36 seconds of it, so the two
#: can be checked against each other without a 490-row datalog.
RUNCARD_SHORT = """\
Stage Rot,10,--
Pumping Forward,0.001,--
Wait,Sec,5
MFC/PC,MFC-1 Ar,20
MFC/PC,PC-1,400
Wait,Sec,10
Heater Ramp,850,10
Wait,Sec,10
MFC/PC,MFC-1 Ar,0
Heater Soak,0,--
Wait,Sec,5
End,--,--
--,--,--
--,--,--
"""

#: 36 rows at 1 Hz and 12 of the real file's 39 columns -- one of every kind:
#: the timestamp, three categoricals (``Auto Action``, ``Program``,
#: ``651C Gauge``), two unpaired numerics (``Tube Pressure``, ``Stage Rot``) and
#: three PV/SV pairs. ``Tube Pressure`` is in engineering notation, as the
#: controller writes it.
#:
#: The ``Heater SV = 910`` block at the top is the single most important number
#: here. It is the stale leftover from the previous run that
#: `analysis.find_final_plateau_start`'s docstring describes, and it is higher
#: than this run's real 850 plateau -- so a naive "last rising edge into the
#: global max" returns row 0's timestamp instead of 17:33:40. The fixture tells
#: the two implementations apart.
#:
#: ``MFC-1`` walks 5 -> 10 -> 15 -> 20 against a setpoint of 20, which is one
#: three-sample violation with clean rows on both sides, and sits at SV 0 at
#: both ends of the run, which is the epsilon guard's case.
DATALOG_SHORT = """\
Time,Auto Action,Program,Tube Pressure,651C Gauge,Stage Rot,Heater PV,Heater SV,MFC-1 PV,MFC-1 SV,P1 PV,P1 SV
2026/08/06 17:33:12,LYH,Stage Rot,19.45E-3,1000 Torr,1.0,88,910,0.000,0.000,140.000,140.000
2026/08/06 17:33:13,LYH,Pumping Forward,18.28E-3,1000 Torr,1.0,88,910,0.000,0.000,140.000,140.000
2026/08/06 17:33:14,LYH,Wait,16.93E-3,1000 Torr,10.0,89,910,0.000,0.000,140.000,140.000
2026/08/06 17:33:15,LYH,Wait,16.39E-3,1000 Torr,10.0,89,910,0.000,0.000,140.000,140.000
2026/08/06 17:33:16,LYH,Wait,15.58E-3,1000 Torr,10.0,90,910,0.000,0.000,140.000,140.000
2026/08/06 17:33:17,LYH,Wait,14.77E-3,1000 Torr,10.0,90,910,0.000,0.000,140.000,140.000
2026/08/06 17:33:18,LYH,Wait,14.32E-3,1000 Torr,10.0,91,910,0.000,0.000,140.000,140.000
2026/08/06 17:33:19,LYH,MFC/PC,1.51E-3,1000 Torr,10.0,91,910,0.000,0.000,140.000,140.000
2026/08/06 17:33:20,LYH,Wait,1.46E+0,1000 Torr,10.0,92,910,5.000,20.000,398.500,400.000
2026/08/06 17:33:21,LYH,Wait,2.59E-3,1000 Torr,10.0,92,910,10.000,20.000,398.500,400.000
2026/08/06 17:33:22,LYH,Wait,7.85E+0,1000 Torr,10.0,93,910,15.000,20.000,398.500,400.000
2026/08/06 17:33:23,LYH,Wait,7.89E+0,1000 Torr,10.0,93,910,20.000,20.000,398.500,400.000
2026/08/06 17:33:24,LYH,Wait,7.92E+0,1000 Torr,10.0,94,910,20.000,20.000,398.500,400.000
2026/08/06 17:33:25,LYH,Wait,7.91E+0,1000 Torr,10.0,94,910,20.000,20.000,398.500,400.000
2026/08/06 17:33:26,LYH,Wait,7.89E+0,1000 Torr,10.0,95,910,20.000,20.000,398.500,400.000
2026/08/06 17:33:27,LYH,Wait,7.91E+0,1000 Torr,10.0,95,910,20.000,20.000,398.500,400.000
2026/08/06 17:33:28,LYH,Wait,7.97E+0,1000 Torr,10.0,96,910,20.000,20.000,398.500,400.000
2026/08/06 17:33:29,LYH,Wait,8.64E+0,1000 Torr,10.0,96,910,20.000,20.000,398.500,400.000
2026/08/06 17:33:30,LYH,Heater Ramp,8.99E+0,100 Torr,10.0,97,910,20.000,20.000,398.500,400.000
2026/08/06 17:33:31,LYH,Wait,9.13E+0,100 Torr,10.0,98,100,20.000,20.000,398.500,400.000
2026/08/06 17:33:32,LYH,Wait,8.60E+0,100 Torr,10.0,180,183,20.000,20.000,398.500,400.000
2026/08/06 17:33:33,LYH,Wait,8.25E+0,100 Torr,10.0,263,267,20.000,20.000,398.500,400.000
2026/08/06 17:33:34,LYH,Wait,8.27E+0,100 Torr,10.0,345,350,20.000,20.000,398.500,400.000
2026/08/06 17:33:35,LYH,Wait,8.27E+0,100 Torr,10.0,428,433,20.000,20.000,398.500,400.000
2026/08/06 17:33:36,LYH,Wait,53.74E-3,100 Torr,10.0,512,517,20.000,20.000,398.500,400.000
2026/08/06 17:33:37,LYH,Wait,2.23E-3,100 Torr,10.0,595,600,20.000,20.000,398.500,400.000
2026/08/06 17:33:38,LYH,Wait,8.05E+0,100 Torr,10.0,678,683,20.000,20.000,398.500,400.000
2026/08/06 17:33:39,LYH,Wait,7.59E+0,100 Torr,10.0,762,767,20.000,20.000,398.500,400.000
2026/08/06 17:33:40,LYH,Wait,5.86E+0,100 Torr,10.0,845,850,20.000,20.000,398.500,400.000
2026/08/06 17:33:41,LYH,MFC/PC,12.07E-3,100 Torr,10.0,848,850,0.000,0.000,398.500,400.000
2026/08/06 17:33:42,LYH,Wait,11.50E-3,100 Torr,10.0,849,850,0.000,0.000,398.500,400.000
2026/08/06 17:33:43,LYH,Wait,10.90E-3,100 Torr,10.0,850,850,0.000,0.000,398.500,400.000
2026/08/06 17:33:44,LYH,Wait,10.20E-3,100 Torr,10.0,850,850,0.000,0.000,398.500,400.000
2026/08/06 17:33:45,LYH,Wait,9.80E-3,100 Torr,10.0,850,850,0.000,0.000,398.500,400.000
2026/08/06 17:33:46,LYH,Wait,9.10E-3,100 Torr,10.0,850,850,0.000,0.000,398.500,400.000
2026/08/06 17:33:47,Stop,End,8.70E-3,100 Torr,10.0,850,850,0.000,0.000,398.500,400.000
"""


def rewrite_cell(text, time, column, value):
    """Return `text` with one datalog cell replaced, addressed by timestamp + column.

    Deriving a variant beats carrying a second fixture: the diff between the
    two files is then the one thing the test is about, and it is visible in the
    test rather than two hundred lines away.
    """
    lines = text.splitlines()
    idx = lines[0].split(",").index(column)
    for i, line in enumerate(lines[1:], start=1):
        fields = line.split(",")
        if fields[0] == time:
            fields[idx] = value
            lines[i] = ",".join(fields)
            return "\n".join(lines) + "\n"
    raise AssertionError(f"no row at {time}")


def drop_rows(text, start_time, count):
    """Return `text` with `count` rows removed, starting at the row stamped `start_time`."""
    lines = text.splitlines()
    i = next(k for k, line in enumerate(lines) if line.startswith(start_time))
    return "\n".join(lines[:i] + lines[i + count:]) + "\n"


def write_datalog(folder, text=DATALOG_SHORT, name="2026-08-06_173312~VBBE00.csv"):
    """Write datalog `text` into `folder` and return its absolute path, as a str.

    `name` is not cosmetic. `scanner.load_run_dataframe` is cached on
    ``(path, mtime)``, and two variants written to one filename inside a single
    test land in the same mtime tick -- the second read then returns the first
    frame. Give every variant its own name. The suite's autouse cache clear
    covers bleed *between* tests, not reuse of one path inside one.

    A str rather than a Path, because that is what `scanner.discover_csv_files`
    hands the rest of the package and what the cache keys on.
    """
    path = folder / name
    path.write_text(text, encoding="utf-8", newline="")
    return str(path)
