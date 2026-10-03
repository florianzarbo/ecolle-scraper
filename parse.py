"""Select the next colles from the normalised agenda.

:mod:`fetch` writes ``output/agenda.csv``; this module reads it back, keeps the
colles that are still to come and returns the closest ones.
"""

import csv
import datetime
import os

import config
import dates

#: Columns that must be present for the agenda to be usable.
REQUIRED_COLUMNS = ("date", "heure", "matiere", "salle", "colleur")


def agenda_csv_path() -> str:
    """Path of the normalised agenda, read when needed."""
    return config.output_path()


def load_rows() -> list[dict]:
    """Read every row of the normalised agenda file.

    Raises:
        FileNotFoundError: If no agenda has been produced yet.
    """
    path = agenda_csv_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"{path} not found, run fetch.py (or main.py) first"
        )

    with open(path, newline="", encoding="utf-8") as csvfile:
        return list(csv.DictReader(csvfile))


def has_agenda() -> bool:
    """Whether a usable agenda from an earlier run is available.

    Never raises: a corrupt or unreadable cache simply counts as unusable.
    """
    try:
        rows = load_rows()
    except (OSError, csv.Error, UnicodeDecodeError, ValueError):
        return False
    return bool(rows)


def next_datetime(row: dict, now: datetime.datetime = None):
    """Return when a colle happens, or ``None`` if that cannot be read."""
    return dates.parse_row_datetime(row, now)


def get_next_colles(now: datetime.datetime = None) -> list[dict]:
    """Return the next upcoming colles, soonest first.

    Only colles that have not started yet are returned, and their number is
    limited by ``NUMBER_OF_COLLES_TO_SHOW``.

    Raises:
        ValueError: If ``NUMBER_OF_COLLES_TO_SHOW`` is not a positive integer.
    """
    now = now or datetime.datetime.now()
    limit = config.number_of_colles_to_show()
    upcoming = []

    for row in load_rows():
        when = next_datetime(row, now)
        if when is None:
            print(f"[!] skipping unreadable row: {row!r}")
            continue
        if when > now:
            upcoming.append((when, row))

    upcoming.sort(key=lambda item: item[0])

    out = []
    for when, row in upcoming[:limit]:
        print(f"[*] next colle: {when:%Y-%m-%d %H:%M}")
        out.append(row)
    return out


if __name__ == "__main__":
    for _row in get_next_colles():
        print(_row)
