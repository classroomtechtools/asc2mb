from asc2mb.model import Division, SchoolClass, Subject, Teacher
from asc2mb.patterns import (
    CLASS_ID_PATTERNS,
    SECTION_PATTERNS,
    teacher_email,
)

CLASS_ = SchoolClass(id="c1", name="Grade 6", short="G6")
DIVISION = Division(id="d1", name="Science A", divisiontag="1")
ENTIRE_CLASS = Division(id="d0", name="Entire class", divisiontag="0")
SUBJECT = Subject(id="s1", name="PYP Science", short="Sci")


def test_class_id_patterns():
    cases = {
        "default": "G6_Science A",
        "dar_al_marefa": "G6 1Sci",
        "name_only": "Grade 6",
        "subject_short": "Sci",
        "subject_name": "PYP Science",
        "subject_short_division": "Sci_1",
    }
    for name, expected in cases.items():
        assert CLASS_ID_PATTERNS[name](CLASS_, DIVISION, SUBJECT) == expected


def test_dar_al_marefa_class_id_omits_zero_tag():
    assert CLASS_ID_PATTERNS["dar_al_marefa"](CLASS_, ENTIRE_CLASS, SUBJECT) == "G6 Sci"


def test_section_default_numbers_from_one():
    assert SECTION_PATTERNS["default"](CLASS_, ENTIRE_CLASS) == "1"
    assert SECTION_PATTERNS["default"](CLASS_, DIVISION) == "2"
    assert SECTION_PATTERNS["default"](CLASS_, Division()) == "1"


def test_section_dar_al_marefa():
    assert SECTION_PATTERNS["dar_al_marefa"](CLASS_, ENTIRE_CLASS) == "G6"
    assert SECTION_PATTERNS["dar_al_marefa"](CLASS_, DIVISION) == "G6(1)"


def test_email_from_xml_wins():
    teacher = Teacher(name="Abbott Alice", email="aa@school.org")
    assert teacher_email(teacher) == "aa@school.org"


def test_email_default_template():
    teacher = Teacher(name="Abbott Alice")
    assert teacher_email(teacher) == "abbott.alice@example.com"


def test_email_custom_template():
    teacher = Teacher(name="Abbott Alice", firstname="Alice", lastname="Abbott")
    assert (
        teacher_email(teacher, "{first}.{last}@school.org") == "alice.abbott@school.org"
    )
    assert teacher_email(teacher, "{initials}@school.org") == "aa@school.org"
