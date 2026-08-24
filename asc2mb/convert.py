"""Turn parsed aSc data into ManageBac import rows.

The central idea: an aSc lesson links one subject and one or more teachers to
parallel lists of classes and divisions ("groups"). Each class/division pair
becomes a ManageBac class ID, and each of the lesson's cards (placements on
the timetable grid) becomes one timetable row per day it occupies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from rich.console import Console

from asc2mb.model import UNKNOWN_TEACHER, Division, SchoolClass, Subject
from asc2mb.parser import TimetableData
from asc2mb.patterns import (
    CLASS_ID_PATTERNS,
    DEFAULT_EMAIL_TEMPLATE,
    SECTION_PATTERNS,
    teacher_email,
)

console = Console()

ClassRow = Tuple[str, str, str, str, str, str, str]
TimetableRow = Tuple[str, int, str, str]
EnrollmentRow = Tuple[str, str]


@dataclass
class Options:
    class_id_pattern: str = "default"
    class_id_prefix: str = ""
    class_id_suffix: str = ""
    section_pattern: str = "default"
    teacher_email_template: str = DEFAULT_EMAIL_TEMPLATE
    smart_combine: bool = True
    combine_uniq_post: bool = False


@dataclass
class ConversionResult:
    class_rows: List[ClassRow] = field(default_factory=list)
    timetable_rows: List[TimetableRow] = field(default_factory=list)
    num_lessons: int = 0
    num_cards: int = 0


def combine_class_ids(ids: List[str]) -> str:
    """Merge the IDs of divisions taught together into one ID, column by
    column: where all IDs agree keep the character, where they differ keep
    each distinct character once, sorted.

    G6_Science_A + G6_Science_B -> G6_Science_AB
    G6_Math_A1 + G6_Math_A2 + G6_Math_B1 -> G6_Math_AB12
    """
    width = max(len(id_) for id_ in ids)
    combined = []
    for col in range(width):
        chars = {id_[col] if col < len(id_) else "" for id_ in ids}
        combined.append("".join(sorted(chars)))
    return "".join(combined)


def _combine_uniq_post(class_id: str) -> str:
    """Special-request reduction of a combined "<grade+digits> <digits><subject>"
    ID down to its lowest division number, e.g. "6AB12 12Sci" -> "6AB 1Sci"."""
    grade_part, subject_part = class_id.split(" ")
    grade = re.match(r"(\d+\w+?)(\d+)", grade_part)
    subject = re.match(r"(\d+)(.*)", subject_part)
    lowest_division = min(subject.groups()[0])
    return f"{grade.groups()[0]} {lowest_division}{subject.groups()[1]}"


def _class_year(class_: SchoolClass) -> str:
    """ManageBac wants a grade year, which aSc keeps as the digits of the
    class's short name (G12 -> 12)."""
    year = "".join(filter(str.isdigit, class_.short))
    if not year:
        year = class_.short or "<>"
        console.print(
            f"[yellow]Warning[/yellow]: expected digits in the class short name "
            f"to use as the grade; using {year!r}",
            f"{class_=}",
        )
    return year


def _padded(items: List[str], index: int) -> Optional[str]:
    return items[index] if index < len(items) else None


def _affixed(class_id: str, options: Options) -> str:
    return options.class_id_prefix + class_id + options.class_id_suffix


def convert(data: TimetableData, options: Options) -> ConversionResult:
    build_class_id = CLASS_ID_PATTERNS[options.class_id_pattern]
    build_section = SECTION_PATTERNS[options.section_pattern]
    result = ConversionResult(num_lessons=len(data.lessons))

    for lesson in data.lessons.values():
        subject = data.subjects.get(lesson.subject_id) or Subject()
        teachers = [
            data.teachers.get(teacher_id) or UNKNOWN_TEACHER
            for teacher_id in lesson.teacher_ids
        ] or [UNKNOWN_TEACHER]
        teacher_emails = "|".join(
            teacher_email(teacher, options.teacher_email_template)
            for teacher in teachers
        )

        cards = data.cards_by_lesson.get(lesson.id, [])
        num_divisions = max(len(lesson.group_ids), len(lesson.class_ids), 1)
        # One teacher covering several divisions at once means aSc "joined"
        # the classes: output them as a single combined class.
        combine = (
            options.smart_combine
            and len(lesson.teacher_ids) <= 1
            and num_divisions > 1
        )

        class_ids: List[str] = []
        last_division_emittable = False
        section = ""
        year = ""

        for index in range(num_divisions):
            group_id = _padded(lesson.group_ids, index)
            class_ref = _padded(lesson.class_ids, index)
            if not class_ref and len(lesson.class_ids) == 1:
                console.print(
                    r"[yellow]Warning:[/] Lesson has multiple divisions but "
                    "only one class; using that class for every division.",
                    f"{lesson=}",
                )
                class_ref = lesson.class_ids[0]

            division = data.divisions.get(group_id or "") or Division()
            class_ = data.school_classes.get(class_ref or "") or SchoolClass()
            if not class_:
                console.print(
                    f"[yellow]Warning:[/] No class corresponds to this division. "
                    f"Divisions: {len(lesson.group_ids)}, classes: {len(lesson.class_ids)}.",
                    f"{lesson=}",
                )

            class_id = build_class_id(class_, division, subject)
            class_ids.append(class_id)
            section = build_section(class_, division)
            last_division_emittable = False

            if not class_ or not cards:
                continue
            year = _class_year(class_)
            result.num_cards += len(cards)
            last_division_emittable = True

            if not combine:
                _emit_rows(
                    result,
                    data,
                    cards,
                    _affixed(class_id, options),
                    year,
                    subject,
                    section,
                    teacher_emails,
                )

        if combine and last_division_emittable:
            # Combine the bare IDs first: merging column by column would
            # garble a shared prefix/suffix when the IDs differ in length.
            combined_id = combine_class_ids(class_ids)
            if options.combine_uniq_post:
                combined_id = _combine_uniq_post(combined_id)
                section = ""
            _emit_rows(
                result,
                data,
                cards,
                _affixed(combined_id, options),
                year,
                subject,
                section,
                teacher_emails,
            )

    return result


def _emit_rows(result, data, cards, class_id, year, subject, section, teacher_emails):
    for card in cards:
        classroom_names = " ".join(
            (data.classrooms.get(classroom_id).short if data.classrooms.get(classroom_id) else "")
            for classroom_id in card.classroom_ids
        )
        for day in card.days:
            result.timetable_rows.append((class_id, day, card.period, classroom_names))
            result.class_rows.append(
                (
                    class_id,
                    f"Grade {year}",
                    subject.name,
                    subject.short,
                    "",
                    section,
                    teacher_emails,
                )
            )


def enrollment_rows(data: TimetableData, options: Options) -> List[EnrollmentRow]:
    """One row per distinct (subject, student) pair. Only subject-based class
    ID patterns make sense here: aSc does not tie student enrollments to
    divisions, so there is no class or division to format with."""
    build_class_id = CLASS_ID_PATTERNS[options.class_id_pattern]
    rows: List[EnrollmentRow] = []
    seen = set()
    for enrollment in data.enrollments:
        key = (enrollment.subject_id, enrollment.student_id)
        if key in seen:
            continue
        seen.add(key)
        subject = data.subjects.get(enrollment.subject_id) or Subject()
        student = data.students.get(enrollment.student_id)
        class_id = _affixed(build_class_id(SchoolClass(), Division(), subject), options)
        rows.append((class_id, student.name if student else ""))
    return rows
