# aSc to ManageBac

## Getting started

Requires Python 3.6 or above. For Windows, install Python via the Microsoft Store. For Mac, install Python at [python.org](https://www.python.org). Installing Python also installs a package manager (called `pip`) that can install the command `asc2mb` into your command line environment.

After installing Python, open the terminal or command line or PowerShell, and peform the following:

```sh
pip install asc2mb
```

If for some reason the `pip` command doesn't work, you can manually install it by following [the relevant instructions](https://pip.pypa.io/en/stable/installing/) for your system.

### Upgrade

Should you need to update to the latest version, you can do:

```
pip install --upgrade asc2mb
```

## Use

After `pip install` worked, it is now installed on your path, and the command `asc2mb` should be available:

```
asc2mb ~/path/to/xml.xml ~/path/to/save/timetable.csv ~/path/to/save/classes.csv
```

It takes only a second to run. It reports how many records it processed.

## Algorithm

This script uses input from more than one international school to generate the expected output. The key to success is using aSc Divisions to match the `uniq_id`s found in ManageBac classes.

## Help

For built-in help, and list of options and their functionality:

```
asc2mb --help
```

## Options

The command takes three required arguments — where the xml file is located, and where to save the two csv files — plus options that depend on your school's needs.

The class ID is how ManageBac knows which class you are referring to, so the program derives it from information in the xml file. It's up to you to ensure there are classes with those IDs in ManageBac, but the program does produce a csv so they can be uploaded in bulk.

- `--class_id_pattern` picks a named rule for building class IDs. The default combines the class short name and the division name, e.g. `G6_Science A`. Other rules use the class name or the subject name/short. Adding a school-specific rule is a small pull request: write one function in `asc2mb/patterns.py` and register it.
- `--class_id_prefix` / `--class_id_suffix` add consistent text around every class ID (for example `-2526` for the academic year).
- `--section_pattern` picks a named rule for each class's Section; the default numbers the divisions starting at 1.
- `--teacher_email_pattern` builds teacher emails when the xml doesn't include one. It is a template with the fields `{name}`, `{first}`, `{last}`, `{initials}`, and `{name_dotted}`; the result is lowercased. The default is `{name_dotted}@example.com`, producing e.g. `abbott.alice@example.com`.
- `--smart_combine` (on by default) merges divisions joined under one teacher (aSc "Join classes") into a single class: `G6_Science_A` + `G6_Science_B` becomes `G6_Science_AB`. Turn it off with `--dont_combine`.
- `--student_enrollments <path>` also writes a student-enrollments csv. It requires a subject-based `--class_id_pattern` (`subject_short` or `subject_name`), because aSc does not associate student enrollments with divisions.

## Development

The code lives in the `asc2mb` package: `parser.py` reads the xml into typed records, `patterns.py` holds the named class-ID/section/email rules, `convert.py` turns lessons into rows, `output.py` writes the csvs, and `cli.py` ties it together.

To run the tests:

```sh
pip install -e . pytest
pytest
```







