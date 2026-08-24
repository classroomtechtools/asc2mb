"""Command-line interface: asc2mb XML_FILE TIMETABLE_CSV CLASSES_CSV [options]."""

from __future__ import annotations

import sys

import rich_click as click
from rich.console import Console

from asc2mb.convert import Options, convert, enrollment_rows
from asc2mb.output import write_classes, write_enrollments, write_timetable
from asc2mb.parser import UnsupportedExportError, parse_file
from asc2mb.patterns import CLASS_ID_PATTERNS, DEFAULT_EMAIL_TEMPLATE, SECTION_PATTERNS

console = Console()


@click.command()
@click.argument("xml_file", type=click.Path(exists=True))
@click.argument("timetable_csv", type=click.Path(writable=True))
@click.argument("classes_csv", type=click.Path(writable=True))
@click.option(
    "--smart_combine/--dont_combine",
    default=True,
    show_default=True,
    help="When aSc 'Join classes' puts several divisions under one teacher, "
    "output them as a single class whose ID merges the division IDs. "
    "Example: G6_Science_A + G6_Science_B becomes G6_Science_AB.",
)
@click.option("--combine_uniq_post/--keep_uniq_post", hidden=True, default=False)
@click.option(
    "--class_id_pattern",
    type=click.Choice(sorted(CLASS_ID_PATTERNS)),
    default="default",
    show_default=True,
    help="Named rule for building each Class ID. The default combines the "
    "class short name and the division name, e.g. G6_Science_A.",
)
@click.option(
    "--class_id_prefix",
    default="",
    help="Text prepended to every Class ID.",
)
@click.option(
    "--class_id_suffix",
    default="",
    help="Text appended to every Class ID (for example the academic year).",
)
@click.option(
    "--section_pattern",
    type=click.Choice(sorted(SECTION_PATTERNS)),
    default="default",
    show_default=True,
    help="Named rule for each class's Section. The default numbers the "
    "divisions starting at 1.",
)
@click.option(
    "--teacher_email_pattern",
    default=DEFAULT_EMAIL_TEMPLATE,
    show_default=True,
    help="Template for teacher emails when the XML has none. "
    "Fields: {name} {first} {last} {initials} {name_dotted}. "
    "The result is lowercased.",
)
@click.option(
    "--student_enrollments",
    type=click.Path(writable=True),
    help="Also write a student-enrollments CSV to this path. Requires a "
    "subject-based --class_id_pattern, because aSc does not tie student "
    "enrollments to divisions.",
)
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
    """Convert an aSc Timetables XML export into CSV files for bulk upload
    into ManageBac.

    XML_FILE is the path to the aSc XML export, e.g. ./sample.xml

    TIMETABLE_CSV is where to write the timetable import, e.g. ./timetable.csv

    CLASSES_CSV is where to write the classes import, e.g. ./classes.csv

    The defaults are usually good enough to get started; the options let you
    control how Class IDs, Sections, and teacher emails are derived. The
    classes CSV usually needs light editing before import — at minimum,
    filtering by programme.
    """
    if student_enrollments and not class_id_pattern.startswith("subject"):
        console.print(
            "[red]Error:[/] --student_enrollments requires --class_id_pattern "
            "subject_short or subject_name, because aSc does not associate "
            "student enrollments with divisions."
        )
        sys.exit(1)

    options = Options(
        class_id_pattern=class_id_pattern,
        class_id_prefix=class_id_prefix,
        class_id_suffix=class_id_suffix,
        section_pattern=section_pattern,
        teacher_email_template=teacher_email_pattern,
        smart_combine=smart_combine,
        combine_uniq_post=combine_uniq_post,
    )

    try:
        data = parse_file(xml_file)
    except UnsupportedExportError as error:
        console.print(f"[red bold]Critical error[/]: {error}")
        sys.exit(1)

    result = convert(data, options)
    write_timetable(timetable_csv, result.timetable_rows)
    write_classes(classes_csv, result.class_rows)

    console.print("\n[green]Process completed.")
    console.print(f"Lessons processed: {result.num_lessons}")
    console.print(f"Cards processed: {result.num_cards}")

    if student_enrollments:
        rows = enrollment_rows(data, options)
        write_enrollments(student_enrollments, rows)
        console.print(f"Enrollments processed: {len(rows)}")


if __name__ == "__main__":
    main()
