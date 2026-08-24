"""Parse an aSc Timetables XML export into typed records (see model.py)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from lxml import etree

from asc2mb.model import (
    Card,
    Classroom,
    Division,
    Enrollment,
    Lesson,
    SchoolClass,
    Student,
    Subject,
    Teacher,
)


class UnsupportedExportError(Exception):
    """The XML export uses a structure this tool does not handle."""


@dataclass
class TimetableData:
    """Everything asc2mb needs from one aSc export."""

    subjects: Dict[str, Subject] = field(default_factory=dict)
    teachers: Dict[str, Teacher] = field(default_factory=dict)
    school_classes: Dict[str, SchoolClass] = field(default_factory=dict)
    divisions: Dict[str, Division] = field(default_factory=dict)
    classrooms: Dict[str, Classroom] = field(default_factory=dict)
    students: Dict[str, Student] = field(default_factory=dict)
    lessons: Dict[str, Lesson] = field(default_factory=dict)
    cards_by_lesson: Dict[str, List[Card]] = field(default_factory=dict)
    enrollments: List[Enrollment] = field(default_factory=list)


def split_ids(value: str) -> List[str]:
    """Split an aSc comma-separated id list, dropping empty entries."""
    return [part for part in value.split(",") if part]


def _card_days(attrib) -> List[int]:
    """A card stores its placement either as a single day number or as a
    seven-character bitmap like "0010000" (day 3)."""
    day = attrib.get("day")
    if day:
        return [int(day)]
    bitmap = attrib.get("days")
    if bitmap:
        return [i + 1 for i, flag in enumerate(bitmap) if flag == "1"]
    return []


def _check_grouptype(root) -> None:
    """asc2mb only understands "groupstype1" exports, where each lesson lists
    parallel classids/groupids. Absence of the options attribute means type 1."""
    options = root.attrib.get("options")
    if options and "groupstype1" not in options.split(","):
        raise UnsupportedExportError(
            "This export uses aSc group type 2, which is not supported yet."
        )


def parse_file(xml_path: str) -> TimetableData:
    root = etree.parse(xml_path, etree.XMLParser(encoding="UTF-8")).getroot()
    _check_grouptype(root)

    data = TimetableData()
    for section in root:
        for element in section:
            attrib = element.attrib
            get = lambda key: attrib.get(key, "")  # noqa: E731

            if section.tag == "subjects":
                data.subjects[get("id")] = Subject(
                    id=get("id"), name=get("name"), short=get("short")
                )
            elif section.tag == "teachers":
                data.teachers[get("id")] = Teacher(
                    id=get("id"),
                    name=get("name"),
                    firstname=get("firstname"),
                    lastname=get("lastname"),
                    email=get("email"),
                )
            elif section.tag == "classes":
                data.school_classes[get("id")] = SchoolClass(
                    id=get("id"), name=get("name"), short=get("short")
                )
            elif section.tag == "groups":
                data.divisions[get("id")] = Division(
                    id=get("id"), name=get("name"), divisiontag=get("divisiontag")
                )
            elif section.tag == "classrooms":
                data.classrooms[get("id")] = Classroom(
                    id=get("id"), name=get("name"), short=get("short")
                )
            elif section.tag == "students":
                data.students[get("id")] = Student(id=get("id"), name=get("name"))
            elif section.tag == "lessons":
                data.lessons[get("id")] = Lesson(
                    id=get("id"),
                    subject_id=get("subjectid"),
                    teacher_ids=split_ids(get("teacherids")),
                    group_ids=split_ids(get("groupids")),
                    class_ids=split_ids(get("classids")),
                )
            elif section.tag == "cards":
                card = Card(
                    lesson_id=get("lessonid"),
                    period=get("period"),
                    classroom_ids=get("classroomids").split(","),
                    days=_card_days(attrib),
                )
                data.cards_by_lesson.setdefault(card.lesson_id, []).append(card)
            elif section.tag == "studentsubjects":
                data.enrollments.append(
                    Enrollment(subject_id=get("subjectid"), student_id=get("studentid"))
                )

    return data
