"""Golden-file tests: run the CLI on a real aSc export and compare the CSVs
against known-good output (captured from version 0.7.2)."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from asc2mb.cli import main

DATA = Path(__file__).parent / "data"
XML = str(DATA / "test22.xml")
GOLDEN = DATA / "golden"


def run_cli(tmp_path, extra_args=()):
    timetable = tmp_path / "timetable.csv"
    classes = tmp_path / "classes.csv"
    result = CliRunner().invoke(main, [XML, str(timetable), str(classes), *extra_args])
    assert result.exit_code == 0, result.output
    return timetable, classes


def test_default_options(tmp_path):
    timetable, classes = run_cli(tmp_path)
    assert timetable.read_text() == (GOLDEN / "timetable.csv").read_text()
    assert classes.read_text() == (GOLDEN / "classes.csv").read_text()


def test_dont_combine(tmp_path):
    timetable, classes = run_cli(tmp_path, ["--dont_combine"])
    assert timetable.read_text() == (GOLDEN / "timetable_nocombine.csv").read_text()
    assert classes.read_text() == (GOLDEN / "classes_nocombine.csv").read_text()


def test_subject_pattern_with_enrollments(tmp_path):
    enrollments = tmp_path / "enrollments.csv"
    timetable, classes = run_cli(
        tmp_path,
        ["--class_id_pattern", "subject_short", "--student_enrollments", str(enrollments)],
    )
    assert timetable.read_text() == (GOLDEN / "timetable_subj.csv").read_text()
    assert classes.read_text() == (GOLDEN / "classes_subj.csv").read_text()
    assert enrollments.read_text() == (GOLDEN / "enrollments.csv").read_text()


def test_prefix_and_suffix(tmp_path):
    # Prefix/suffix must survive intact on every ID, including smart-combined
    # ones, where they are applied after the column-wise merge.
    _, classes = run_cli(
        tmp_path, ["--class_id_prefix", "X-", "--class_id_suffix", "-2526"]
    )
    body = classes.read_text().splitlines()[1:]
    assert body
    assert all(line.startswith("X-") for line in body)
    assert all(line.split(",")[0].endswith("-2526") for line in body)


def test_enrollments_require_subject_pattern(tmp_path):
    result = CliRunner().invoke(
        main,
        [XML, str(tmp_path / "t.csv"), str(tmp_path / "c.csv"),
         "--student_enrollments", str(tmp_path / "e.csv")],
    )
    assert result.exit_code == 1
    assert "subject" in result.output
