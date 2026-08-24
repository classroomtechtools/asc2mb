"""Typed records for the parts of an aSc XML export that asc2mb uses.

Every string field defaults to "" so that records built from XML elements
with missing attributes are safe to format into class IDs, sections, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Subject:
    id: str = ""
    name: str = ""
    short: str = ""


@dataclass(frozen=True)
class Teacher:
    id: str = ""
    name: str = ""
    firstname: str = ""
    lastname: str = ""
    email: str = ""


UNKNOWN_TEACHER = Teacher(name="Unknown Teacher")


@dataclass(frozen=True)
class SchoolClass:
    """An aSc "class" (a homeroom/grade grouping such as G12)."""

    id: str = ""
    name: str = ""
    short: str = ""

    def __bool__(self) -> bool:
        return bool(self.id or self.name or self.short)


@dataclass(frozen=True)
class Division:
    """An aSc "group": a division of a class, such as "Entire class" or "A"."""

    id: str = ""
    name: str = ""
    divisiontag: str = ""


@dataclass(frozen=True)
class Classroom:
    id: str = ""
    name: str = ""
    short: str = ""


@dataclass(frozen=True)
class Student:
    id: str = ""
    name: str = ""


@dataclass(frozen=True)
class Card:
    """One placement of a lesson on the timetable grid."""

    lesson_id: str = ""
    period: str = ""
    classroom_ids: List[str] = field(default_factory=list)
    days: List[int] = field(default_factory=list)


@dataclass(frozen=True)
class Lesson:
    id: str = ""
    subject_id: str = ""
    teacher_ids: List[str] = field(default_factory=list)
    group_ids: List[str] = field(default_factory=list)
    class_ids: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Enrollment:
    """A studentsubjects record: one student taking one subject."""

    subject_id: str = ""
    student_id: str = ""
