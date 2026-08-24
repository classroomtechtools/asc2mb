"""CSV writers for the ManageBac bulk-import formats."""

from __future__ import annotations

import csv
from typing import Iterable, List, Sequence

from asc2mb.convert import ClassRow, EnrollmentRow, TimetableRow

TIMETABLE_HEADER = ["Class ID", "Day", "Period", "Classroom"]
CLASSES_HEADER = ["Class ID", "Year", "Group", "Subject", "Name", "Section", "Teacher Email"]
ENROLLMENTS_HEADER = ["Class ID", "Student Name"]


def _write(path: str, header: Sequence[str], rows: Iterable[Sequence]) -> None:
    with open(path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(rows)


def write_timetable(path: str, rows: List[TimetableRow]) -> None:
    _write(path, TIMETABLE_HEADER, sorted(rows))


def write_classes(path: str, rows: List[ClassRow]) -> None:
    """A class appears once per timetable placement; the import wants it once."""
    deduped = dict.fromkeys(rows)
    _write(path, CLASSES_HEADER, sorted(deduped))


def write_enrollments(path: str, rows: List[EnrollmentRow]) -> None:
    _write(path, ENROLLMENTS_HEADER, rows)
