"""Select the next colles from the normalised ``output/agenda.csv``."""

import csv
import datetime
import locale
import os

try:  # pragma: no cover - trivial import shim
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

DEFAULT_AGENDA_CSV_PATH = os.path.join("output", "agenda.csv")

try:  # the legacy date format needs the French locale
    locale.setlocale(locale.LC_ALL, "fr_FR.utf8")
except locale.Error:  # pragma: no cover - depends on the host
    print("[!] fr_FR.utf8 locale unavailable, only ISO dates will be parsed")


def agenda_csv_path() -> str:
    """Path of the normalised agenda, read when needed."""
    return os.getenv("AGENDA_CSV_PATH") or DEFAULT_AGENDA_CSV_PATH


def number_of_colles_to_show() -> int:
    """How many upcoming colles to return, read when needed."""
    return int(os.getenv("NUMBER_OF_COLLES_TO_SHOW", "1"))


def parse_date_string(datestring: str) -> datetime.datetime:
    """Parse a colle date, either ISO (``2026-09-24 17:00``) or legacy French.

    The legacy scraped format looked like ``jeudi 24 septembre 17h00``.
    """
    datestring = datestring.strip()
    try:
        return datetime.datetime.fromisoformat(datestring)
    except ValueError:
        pass

    # Legacy format from the HTML scraper: infer the year, rolling over in July.
    now = datetime.datetime.now()
    year = now.year
    month = datetime.datetime.strptime(datestring.split()[2], "%B")
    if now.month > 7 and month.month < 7:
        year += 1
    return datetime.datetime.strptime(datestring + " " + str(year), "%A %d %B %Hh%M %Y")


def load_rows() -> list[dict]:
    """Read every row of the normalised agenda file."""
    path = agenda_csv_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{path} not found, run fetch.py (or main.py) first")

    with open(path, newline="", encoding="utf-8") as csvfile:
        return list(csv.DictReader(csvfile))


def has_agenda() -> bool:
    """Whether a usable agenda from an earlier run is available."""
    try:
        return bool(load_rows())
    except (OSError, csv.Error):
        return False


def get_next_colles(now: datetime.datetime = None) -> list[dict]:
    """Return the ``NUMBER_OF_COLLES_TO_SHOW`` next upcoming colles.

    Rows are sorted chronologically and only future colles are considered.
    """
    now = now or datetime.datetime.now()
    upcoming = []

    for row in load_rows():
        raw = row.get("date_time") or " ".join(
            part for part in (row.get("date"), row.get("heure")) if part
        )
        if not raw:
            continue
        try:
            when = parse_date_string(raw)
        except (ValueError, IndexError, KeyError) as error:
            print(f"[!] skipping unparsable row {row!r} ({error})")
            continue
        if when > now:
            upcoming.append((when, row))

    upcoming.sort(key=lambda item: item[0])

    out = []
    for when, row in upcoming[: number_of_colles_to_show()]:
        print("next colle: ", when)
        out.append(row)
    return out


if __name__ == "__main__":
    print(get_next_colles())
