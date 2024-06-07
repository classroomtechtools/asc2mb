"""
A simple script that converts the exported xml from ASC into two files
that is in the format expected to be imported into ManageBac.

USAGE:
asc2mb --help

Copyright 2021 Adam Morris Adam Morris adam.morris@classroomtechtools.com

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
ˇ
"""

import re
from rich.console import Console

console = Console()
import rich_click as click
import csv
from lxml import etree

from collections import UserDict, defaultdict


class Json(UserDict):
    """
    Create instances of json-like objects
    Intention here is just to make it easy to write pattern strings
    such as {group.name} instead of {group.get('name', ''))}
    If group.name is None then it should be an empty string
    """

    def __init__(self, data={}, default=""):
        UserDict.__init__(self, data)  # UserDict is a built-in class, data is dict
        self.default = default

    def __getattr__(self, key):
        """
        All attribute requests will end up here for this
        If key not ot in here, return the default
        """
        if not key in self.__dict__["data"]:
            return ""
        if key in self.__dict__["data"].keys():
            return self.__dict__["data"][key]
        return self.default


class Teacher(Json):
    """
    Special behavior for a teacher, where there is an email that might be in the xml file
    or it might not be. Some functionality is needed here to allow the end user define the pattern used to make the email
    for example by initials or firstname.lastname@example.com
    """

    def __init__(self, data={}, default=None):
        if not data:
            data = {"name": "Unknown Teacher"}
        if default is None:
            default = '{".".join(teacher.name.split(' ')) + "@example.com"}'
        self.default = default
        Json.__init__(self, data, default)

    @property
    def email(self):
        """
        Conveniently override the email property to use an evaluated string
        """
        if "email" in self.data and self.data.get("email"):
            return self.data.email
        teacher = self
        pattern = "f'" + (self.default or "") + "'"
        return eval(pattern).lower()


# eval used
class_id_patterns = [
    {"p": "{class_.short}_{division.name}", "n": "default"},
    {
        "p": "{class_.short} {division.divisiontag if division.divisiontag!='0' else ''}{subject.short}",
        "n": "dar_al_marefa",
    },
    {"p": "{class_.name}", "n": "name_only"},
    {"p": "{subject.short}", "n": "subject_short"},
    {"p": "{subject.name}", "n": "subject_name"},
    {"p": "{subject.short}_{division.divisiontag or 0}", "n": "subject_short_division"},
]
pattern_choices = [pattern.get("n") for pattern in class_id_patterns]

section_patterns = [
    {"p": "{int(division.divisiontag or 0)+1}", "n": "default"},
    #    {"p": "{teacher.name.split(' ')[0][0] + teacher.name.split(' ')[1][0] if len(teacher.name.split(' '))>1 else ''}", "n": 'teacher_intiails'},
    {
        "p": "{class_.short if division.divisiontag == '0' else f'{class_.short}({division.divisiontag or 1})'}",
        "n": "dar_al_marefa",
    },
]
section_pattern_choices = list(map(lambda x: x["n"], section_patterns))

# Combine classes by seeing multiple teachers with one subject group
combine_choices = [
    "concat",  # dumb concat
    "dar_al_marefa",  # a foo,b foo => ab foo
]


def get_pattern(patterns, target):
    return (
        'f"' + [ptn for ptn in patterns if ptn.get("n") == target].pop().get("p") + '"'
    )


class NullList(list):
    def __getitem__(self, index):
        if index > len(self) - 1:
            return None
        return list.__getitem__(self, index)


smart_combine_help = """
ON by default. When using 'Join classes' aSc functionality to combine classes with only one teacher, 
one single uniq ID is generated for all divisions and output as one class. Combining classes with more than one teacher will output multiple classes. See above for algorithm and examples
"""


@click.command()
@click.argument("xml_file", type=click.Path(exists=True))
@click.argument("timetable_csv", type=click.Path(writable=True))
@click.argument("classes_csv", type=click.Path(writable=True))
@click.option(
    "--smart_combine/--dont_combine",
    show_default=True,
    help=smart_combine_help,
    default=True,
)
@click.option(
    "--combine_uniq_post/--keep_uniq_post", hidden=True, help="", default=False
)
@click.option(
    "--class_id_pattern",
    show_default=True,
    help="Defines the template used to build uniq_ids. Default is `{class_.short}_{division.name}`",
    type=click.Choice(pattern_choices),
    default="default",
)
@click.option(
    "--class_id_prefix",
    show_default=False,
    help="Add a prefix to every uniq ID",
    default="",
)
@click.option(
    "--class_id_suffix",
    show_default=False,
    help="Add a suffix to every uniq ID (for example the academic year)",
    default="",
)
@click.option(
    "--section_pattern",
    show_default=True,
    help="Defines the template used to output section for each class, default is `{int(division.divisiontag)+1}`",
    type=click.Choice(section_pattern_choices),
    default="default",
)
@click.option(
    "--teacher_email_pattern",
    show_default=False,
    help="""Defines the template used to output the teacher email. Default is `{".".join(teacher.name.split(' ')) + "@example.com"}`""",
)
@click.option("--student_enrollments", 'student_enrollments', type=click.Path(writable=True))
def main(
    xml_file,
    timetable_csv,
    classes_csv,
    smart_combine,
    combine_uniq_post,
    class_id_pattern,
    class_id_prefix,
    class_id_suffix,
    section_pattern,
    teacher_email_pattern,
    student_enrollments,
):
    """
    Convert the data in an asc xml output into two csv files that can be bulk uploaded to ManageBac.

    XML_FILE is the path to where the xml output is located on your drive. Example: ~/sample.xml or ./sample.xml

    TIMETABLE_CSV is the path to where you want the timetable data to be output to. Example: ~/timetables.csv

    CLASSES_CSV is the path to where you want the classes csv to be output to. Example: ~/classes.csv

    The resulting files are suitably formatted to (mostly) match the expected output of bulk classes import, and the timetable bulk import.
    Some modification is likely required, especially for the classes csv, as you will minimally need to filter by programme for individual import.

    OPTIONS:

    Default behavior is probably good enough to get started, but these parameters are available. See below for legal values.

    --class_id_pattern: If you want more control over how the program dervies the Class Id field, this option can be sent. Note however, that options are limited; further improvements need to hard coded

    --class_id_prefix: If every class Id is supposed to have a consistent prefix, indicate so with this option.

    --class_id_suffix: If every class Id is supposed to have a consistent suffix, for example -2122 to indicate the academic year, indicate so with this option

    ---section_pattern: Every class should have a section indicated somehow. By default, it uses the xml divisiontag. This can be changed in the code.

    --teacher_email_pattern: Teacher email addresses may be included in the xml, in which case this is used. You can also derive it from the teacher's name itself

    NEW in version 0.5:

    --smart_combine: Default is true. If two aSc classes are joined together with one individual teacher, the following transpformation is applied to the `uniq_id`:

      * The new uniq ID combines all the characters of the divisions into one new uniq ID
      * Ex) G6_Science_A + G6_Science_B => G6_Science_AB
      * Ex) G6_Math_A1 + G6_Math_A2 + G6_Math_B1 => G6_Math_AB12

    """
    # mytree = ET.parse(xml_file)
    parser = etree.XMLParser()
    mytree = etree.parse(xml_file, parser)

    myroot = mytree.getroot()

    # find the group type, assume grouptype = 1 if not present
    grouptype = (
        1
        if "groupstype1" in (myroot.attrib.get("options") or ["groupstype1"]).split(",")
        else 2
    )
    lookup = {}

    process_info = {"num_lessons": 0, "num_cards": 0}

    # populate the lookup tables
    for child in myroot:
        name = child.tag
        lookup[name] = {}
        for grandkid in child:
            values = grandkid.attrib
            id_ = values.get("id")

            if not id_ is None:
                lookup[name][id_] = values
            elif name == "cards":
                id_ = values.get("lessonid")
                if not id_ in lookup[name]:
                    lookup[name][id_] = []
                lookup[name][id_].append(values)
            elif name == 'studentsubjects':
                id_ = f"{values.get('subjectid')}_{values.get('studentid')}"
                if not id_ in lookup[name]:
                    lookup[name][id_] = []
                lookup[name][id_].append(values)

    lessons = lookup.get("lessons")
    subjects = lookup.get("subjects")
    student_subjects = lookup.get('studentsubjects')
    students = lookup.get('students')
    classes_file = []
    timetable_output = []
    staging = {}

    process_info["num_lessons"] += len(lessons)

    if grouptype == 1:
        # grouptype=1 means that lessons can have multiple groups and classes
        for lesson_id, lesson in lessons.items():
            subject_id = lesson.get("subjectid")
            subject = Json(subjects.get(subject_id))
            teachers = NullList(lesson.get("teacherids").split(","))
            groups = NullList(lesson.get("groupids").split(","))
            classes = NullList(lesson.get("classids").split(","))
            # if len(groups) == 1 and groups[0] == '':
            #     # not associated to groups
            #     if not class_id_patterns.startswith('subject'):
            #         console.print(r"[red]Error:[/] No")
            largest = max(map(lambda x: len(x), [groups, classes]))

            teacher_emails_list = []
            for teacher_id in teachers:
                teacher = lookup.get("teachers").get(teacher_id)
                teacher_obj = Teacher(teacher, teacher_email_pattern)
                teacher_emails_list.append(teacher_obj)
            teacher_emails = "|".join(
                [
                    teacher.email if hasattr(teacher, "email") else ""
                    for teacher in teacher_emails_list
                ]
            )

            combine = False
            if smart_combine and len(teachers) == 1 and largest > 1:
                combine = True

            uniqs = []
            for index in range(largest):
                group_id = groups[index]
                class_id = classes[index]
                if not classes[index] and len(classes) == 1:
                    console.print(
                        r"[yellow]Warning:[/] Lesson definition with multiple divisions but only one class. Using the first class as the default",
                        f"{lesson=}",
                    )
                    class_id = classes[0]

                division = (
                    Json(lookup.get("groups").get(group_id))
                    if group_id is not None
                    else Json()
                )
                class_ = (
                    Json(lookup.get("classes").get(class_id))
                    if class_id is not None
                    else Json()
                )

                if not class_:
                    console.print(
                        f"[yellow]Warning: [/] No class information available that cooresponds to division. Number of divisions: {len(groups)}, number of classes: {len(classes)}",
                        f"{lesson=}",
                    )

                pattern = get_pattern(class_id_patterns, class_id_pattern)
                uniq = eval(pattern)
                if class_id_prefix:
                    uniq = f"{class_id_prefix}{uniq}"
                if class_id_suffix:
                    uniq = f"{uniq}{class_id_suffix}"
                uniqs.append(uniq)

                # all of the card placements
                cards = lookup.get("cards").get(lesson_id)
                staging[uniq] = cards

                section = eval(get_pattern(section_patterns, section_pattern))

                ## Get the year which we'll put in the classes output
                year = "".join(filter(str.isdigit, class_.short))
                if not year:
                    console.print(
                        f"[yellow]Warning[/yellow]: Expecting digits in 'short' as the Grade `class_.sort`. Using itself instead, or '<>' if none provided",
                        f"{class_=}",
                    )
                    year = class_.short or "<>"

                if cards is None:
                    continue
                process_info["num_cards"] += len(cards)
                for card in cards:
                    classrooms = map(
                        lambda x: lookup.get("classrooms").get(x),
                        card.get("classroomids").split(","),
                    )
                    if card.get("day"):
                        days = [card.get("day")]
                    elif card.get("days"):
                        days = [
                            i + 1 for i, c in enumerate(card.get("days")) if c == "1"
                        ]
                    period = card.get("period")
                    classroom_output = " ".join(
                        [
                            (classroom or {"short": ""}).get("short", "")
                            for classroom in classrooms
                        ]
                    )
                    for day in days:
                        if combine:
                            # the same teacher teaches across "classes" in the timetable
                            if len(uniqs) == largest:
                                # when we're at the end of the uniqs, we convert to one uniq
                                matrix = []
                                for row in range(len(uniqs)):
                                    matrix.append([s for s in uniqs[row]])
                                combined_uniq = []
                                for col in range(max([len(m) for m in matrix])):
                                    cells = []
                                    for row in range(len(matrix)):
                                        try:
                                            cells.append(matrix[row][col])
                                        except IndexError:
                                            cells.append("")
                                    if len(set([c for c in cells])) == 1:
                                        # they are all the same
                                        combined_uniq.append(matrix[0][col])
                                    else:
                                        combined_uniq.append(
                                            "".join(sorted(set(cells)))
                                        )

                                # get the uniq:
                                uniq = "".join(combined_uniq)
                                if combine_uniq_post:
                                    # special request
                                    f, s = uniq.split(" ")
                                    g = re.match(r"(\d+\w+?)(\d+)", f)
                                    h = re.match(r"(\d+)(.*)", s)
                                    i = min(h.groups()[0])
                                    uniq = g.groups()[0] + " " + i + h.groups()[1]
                                    section = ""
                                timetable_output.append(
                                    [uniq, day, period, classroom_output]
                                )
                                classes_file.append(
                                    [
                                        uniq,
                                        f"Grade {year}",
                                        division.name,
                                        subject.short,
                                        "",
                                        teacher_emails,
                                        section,
                                    ]
                                )

                        else:
                            timetable_output.append(
                                [uniq, day, period, classroom_output]
                            )
                            classes_file.append(
                                [
                                    uniq,
                                    f"Grade {year}",
                                    division.name,
                                    subject.short,
                                    "",
                                    teacher_emails,
                                    section,
                                ]
                            )

    elif grouptype == 2:
        console.print("[red bold]Critical error[/]: grouptype == 2 not implemented yet")
        exit(0)

    else:
        console.print("[red bold]Critical error[/] uknown group type")
        exit(0)

    # remove dups
    classes_file = sorted(list(dict.fromkeys([tuple(i) for i in classes_file])))
    timetable_output = sorted(timetable_output)
    with open(timetable_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Class ID", "Day", "Period", "Classroom"])
        for row in timetable_output:
            writer.writerow(row)

    with open(classes_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            ["Class ID", "Year", "Group", "Subject", "Name", "Teacher Email", "Section"]
        )
        for row in classes_file:
            writer.writerow(row)

    if student_enrollments:
        if not class_id_pattern.startswith('subject'):
            click.echo(r'[red]Error: [/] Student enrollments selected but the class_id_pattern does not match. ASC does not associate student enrollments to divisions, so class_id_pattern must be subject_short or subject_name')
        else: 
            with open(student_enrollments, 'w', newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    ["Class ID", "Student Name"]
                )
                process_info['num_enrollments'] = 0
                for id_, student_subject in student_subjects.items():
                    subject_id, student_id = id_.split('_')
                    subject = Json(subjects.get(subject_id))
                    student = Json(students.get(student_id))

                    unique = get_pattern(class_id_patterns, class_id_pattern)
                    class_id = eval(unique)
                    writer.writerow([class_id, student.name])
                    process_info['num_enrollments'] += 1


    console.print("\n[green]Process completed.")
    console.print(
        f"Lessons processed: {process_info['num_lessons']}\nCards processed: {process_info['num_cards']}"
    )
    if student_enrollments:
        console.print(f"Enrollments processed: {process_info['num_enrollments']}")
