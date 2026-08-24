"""Named formatting rules for class IDs, sections, and teacher emails.

Each rule is a plain function; the registries map the names accepted on the
command line to those functions. To add a school-specific rule, write a
function here and register it.
"""

from __future__ import annotations

from typing import Callable, Dict

from asc2mb.model import Division, SchoolClass, Subject, Teacher

ClassIdPattern = Callable[[SchoolClass, Division, Subject], str]
SectionPattern = Callable[[SchoolClass, Division], str]


def _class_short_division_name(class_: SchoolClass, division: Division, subject: Subject) -> str:
    return f"{class_.short}_{division.name}"


def _dar_al_marefa_class_id(class_: SchoolClass, division: Division, subject: Subject) -> str:
    tag = division.divisiontag if division.divisiontag != "0" else ""
    return f"{class_.short} {tag}{subject.short}"


def _class_name(class_: SchoolClass, division: Division, subject: Subject) -> str:
    return class_.name


def _subject_short(class_: SchoolClass, division: Division, subject: Subject) -> str:
    return subject.short


def _subject_name(class_: SchoolClass, division: Division, subject: Subject) -> str:
    return subject.name


def _subject_short_division(class_: SchoolClass, division: Division, subject: Subject) -> str:
    return f"{subject.short}_{division.divisiontag or 0}"


CLASS_ID_PATTERNS: Dict[str, ClassIdPattern] = {
    "default": _class_short_division_name,
    "dar_al_marefa": _dar_al_marefa_class_id,
    "name_only": _class_name,
    "subject_short": _subject_short,
    "subject_name": _subject_name,
    "subject_short_division": _subject_short_division,
}


def _division_number(class_: SchoolClass, division: Division) -> str:
    return str(int(division.divisiontag or 0) + 1)


def _dar_al_marefa_section(class_: SchoolClass, division: Division) -> str:
    if division.divisiontag == "0":
        return class_.short
    return f"{class_.short}({division.divisiontag or 1})"


SECTION_PATTERNS: Dict[str, SectionPattern] = {
    "default": _division_number,
    "dar_al_marefa": _dar_al_marefa_section,
}

DEFAULT_EMAIL_TEMPLATE = "{name_dotted}@example.com"


def teacher_email(teacher: Teacher, template: str = DEFAULT_EMAIL_TEMPLATE) -> str:
    """The email from the XML wins; otherwise build one from the template.

    Available template fields: {name} {first} {last} {initials} {name_dotted}.
    The built address is lowercased.
    """
    if teacher.email:
        return teacher.email

    name_parts = teacher.name.split(" ")
    fields = {
        "name": teacher.name,
        "first": teacher.firstname or (name_parts[0] if name_parts else ""),
        "last": teacher.lastname or (name_parts[-1] if len(name_parts) > 1 else ""),
        "initials": "".join(part[0] for part in name_parts if part),
        "name_dotted": ".".join(name_parts),
    }
    return template.format(**fields).lower()
