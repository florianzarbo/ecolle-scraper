#! /usr/bin/env python3
"""Build the normalised agenda from a CSV export of the ecolle colles.

Since v2.0.0 the colles are read from a CSV file instead of being scraped from
the ecolle website. The expected file looks like this::

    Date,Matière,Colleur,Jour,Salle,Début,Fin
    2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00
    2026-09-30,Physique,M Blain,mercredi,L124,15:00,16:00

Header names are matched without accents, case, spaces, dashes or underscores,
a UTF-8 BOM is stripped, extra columns and blank lines are ignored, and rows
whose date or time cannot be read are skipped with a warning. The result is
written to ``output/agenda.csv``, which :mod:`parse` reads.

When the CSV file is missing, the pre-2.0.0 HTML scraper is used as a fallback.
Set ``DISABLE_ECOLLE_FETCH=true`` to switch that off and make the CSV file the
only source.
"""

import csv
import datetime
import io
import os
from typing import Optional
from urllib.parse import urljoin

import config
import dates

try:  # pragma: no cover - the scraper fallback is optional
    import requests
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    requests = None
    BeautifulSoup = None

#: Columns of the normalised agenda, read by :mod:`parse` and :mod:`notif`.
#: The last three are the historical scraper columns, kept so that an agenda
#: produced by either source has the same shape.
OUTPUT_FIELDS = [
    "date",
    "heure",
    "date_time",
    "matiere",
    "colleur",
    "salle",
    "jour",
    "fin",
    "couleur",
    "programme_links",
    "popup",
]

#: Accepted header spellings, mapped to the internal column name.
COLUMN_ALIASES = {
    "date": "date",
    "matiere": "matiere",
    "colleur": "colleur",
    "jour": "jour",
    "salle": "salle",
    "debut": "debut",
    "fin": "fin",
}

#: Header names expected in the export, in their usual spelling.
INPUT_FIELDS = ["Date", "Matière", "Colleur", "Jour", "Salle", "Début", "Fin"]

#: Columns without which the file is unusable.
REQUIRED_COLUMNS = ["date", "matiere", "colleur", "salle", "debut"]


class AgendaError(Exception):
    """Raised when an agenda cannot be built from the CSV export."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def normalize_header(name: Optional[str]) -> str:
    """Lowercase a header and strip accents, spaces, underscores and dashes."""
    return dates.ascii_fold(name or "").replace(" ", "").replace("_", "").replace("-", "")


def describe_missing_csv(path: str) -> str:
    """Build an actionable message for a CSV file that is not there."""
    message = [
        f"CSV file not found at {path!r} (working directory: {os.getcwd()!r}).",
        f"Put your export at {os.path.join('input', 'colles.csv')} or point "
        "COLLES_CSV_PATH at it.",
    ]

    directory = os.path.dirname(path) or "."
    if os.path.isdir(path):
        message.append(f"{path!r} is a directory, not a file.")
        directory = path
    elif not os.path.isdir(directory):
        message.append(f"The directory {directory!r} does not exist.")

    if os.path.isdir(directory):
        try:
            names = sorted(
                name
                for name in os.listdir(directory)
                if name.lower().endswith((".csv", ".txt"))
            )
        except OSError as error:
            message.append(f"Could not read {directory!r} ({error}).")
        else:
            if names:
                message.append(f"CSV-like files in {directory!r}: " + ", ".join(names))
            else:
                message.append(f"There is no CSV file in {directory!r}.")

    if config.setting("COLLES_CSV_PATH"):
        message.append(
            "COLLES_CSV_PATH is the path *inside* the container: with the "
            "provided docker-compose.yml, ./input on the host is /app/input."
        )
    else:
        message.append("COLLES_CSV_PATH is not set, using the default path.")

    return " ".join(message)


def describe_export(path: str, fieldnames, missing: list) -> str:
    """Explain which columns were found and which were expected."""
    found = ", ".join(repr(name) for name in fieldnames or [])
    expected = ", ".join(INPUT_FIELDS)
    return (
        f"{path}: missing column(s) {', '.join(missing)}; found {found}. "
        f"The file must be a comma-separated export with the headers {expected}"
    )


# --------------------------------------------------------------------------- #
# CSV source
# --------------------------------------------------------------------------- #


def column_map(fieldnames) -> dict:
    """Map internal column names to the header spelling used in the file.

    Raises:
        AgendaError: If the same column appears twice: the last one would
            silently win, which could schedule a colle on the wrong day.
    """
    columns = {}
    for field in fieldnames or []:
        target = COLUMN_ALIASES.get(normalize_header(field))
        if not target:
            continue
        if target in columns:
            raise AgendaError(
                f"column {target!r} appears twice in the header "
                f"({columns[target]!r} and {field!r}); remove the duplicate"
            )
        columns[target] = field
    return columns


def build_row(raw: dict, columns: dict) -> dict:
    """Normalise one CSV record into an agenda row.

    Raises:
        ValueError: If the date or the start time cannot be read.
    """
    date = dates.parse_date(raw.get(columns["date"], ""))
    start = dates.parse_time(raw.get(columns["debut"], ""))

    def text(name: str) -> str:
        column = columns.get(name)
        return (raw.get(column) or "").strip() if column else ""

    return {
        "date": date.isoformat(),
        "heure": start.strftime("%H:%M"),
        "date_time": datetime.datetime.combine(date, start).isoformat(
            sep=" ", timespec="minutes"
        ),
        "matiere": text("matiere"),
        "colleur": text("colleur"),
        "salle": text("salle"),
        "jour": text("jour"),
        "fin": text("fin"),
        # Kept for backward compatibility with the scraper output.
        "couleur": "",
        "programme_links": "",
        "popup": "",
    }


def read_colles_csv(path: str) -> list[dict]:
    """Read the ecolle CSV export and return normalised agenda rows.

    Args:
        path: Path of the CSV file exported from ecolle.

    Returns:
        Rows shaped like the historical scraper output, sorted by date.

    Raises:
        AgendaError: If the file is unreadable, empty, malformed, or has no
            usable row.
    """
    print(f"[*] Reading CSV: {path}")
    try:
        # Read and decode up front: decoding a text-mode file happens lazily, so
        # an encoding error would otherwise surface in the middle of parsing.
        with open(path, "rb") as handle:
            raw_bytes = handle.read()
    except PermissionError as error:
        raise AgendaError(
            f"{path} exists but cannot be read ({error}). The file is mounted "
            "read-only, make sure it is world-readable (chmod a+r)."
        ) from error
    except IsADirectoryError as error:
        raise AgendaError(
            f"{path} is a directory, COLLES_CSV_PATH must point at the CSV file"
        ) from error
    except OSError as error:
        raise AgendaError(f"{path} could not be opened ({error})") from error

    try:
        text = raw_bytes.decode("utf-8-sig")  # also strips a BOM
    except UnicodeDecodeError as error:
        hint = ""
        if raw_bytes[:2] in (b"\xff\xfe", b"\xfe\xff"):
            hint = " The file looks like UTF-16: re-export it as CSV UTF-8."
        raise AgendaError(
            f"{path} is not valid UTF-8 text ({error}). Export the CSV again as "
            f"UTF-8 (comma separated).{hint}"
        ) from error

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise AgendaError(f"{path} is empty")

    columns = column_map(reader.fieldnames)
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    if missing:
        raise AgendaError(describe_export(path, reader.fieldnames, missing))

    rows = []
    try:
        for lineno, raw in enumerate(reader, start=2):
            if not any((value or "").strip() for value in raw.values()):
                continue  # skip blank lines
            try:
                rows.append(build_row(raw, columns))
            except ValueError as error:
                print(f"[!] {path}:{lineno}: skipped row ({error})")
    except csv.Error as error:
        raise AgendaError(f"{path} is not a valid CSV file ({error})") from error

    if not rows:
        raise AgendaError(
            f"{path}: no usable row found, check that the dates look like "
            "2026-09-24 and the times like 17:00"
        )

    rows.sort(key=lambda row: row["date_time"])
    print(f"[+] Parsed {len(rows)} colles from CSV")
    return rows


def save_agenda(rows: list[dict]) -> list[dict]:
    """Write rows to the normalised agenda file read by :mod:`parse`.

    Raises:
        AgendaError: If the file cannot be created.
    """
    path = config.output_path()
    directory = os.path.dirname(path)

    try:
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    except OSError as error:
        raise AgendaError(
            f"{path} could not be written ({error}). Is the directory mounted "
            "writable?"
        ) from error

    print(f"[+] Saved {len(rows)} rows to {path}")
    return rows


# --------------------------------------------------------------------------- #
# Legacy HTML scraper (fallback when no CSV is available)
# --------------------------------------------------------------------------- #


def _url(path: str) -> str:
    """Absolute URL for a path on the ecolle instance."""
    return urljoin(config.setting("BASE_URL").rstrip("/") + "/", path)


def get_csrf_token(session) -> str:
    """Fetch the login page and extract the CSRF token."""
    url = _url("eleve/")
    print(f"[*] Fetching login page: {url}")
    response = session.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
    if not csrf_input:
        raise ValueError("Could not find CSRF token in login page")

    csrf_token = csrf_input.get("value")
    print(f"[+] CSRF token extracted: {csrf_token[:20]}...")
    return csrf_token


def login(session, username: str, password: str) -> bool:
    """Log in to the ecolle system, with CSRF handling."""
    url = _url("eleve/")
    login_data = {
        "csrfmiddlewaretoken": get_csrf_token(session),
        "username": username,
        "password": password,
    }
    headers = {
        "Referer": url,
        "Origin": config.setting("BASE_URL").rstrip("/"),
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    print(f"[*] Logging in as user: {username}")
    response = session.post(
        url, data=login_data, headers=headers, allow_redirects=True, timeout=10
    )
    response.raise_for_status()

    if "Déconnexion" in response.text:
        print("[+] Login successful!")
    else:
        print("[-] Login may have failed, continuing anyway...")
    return True


def fetch_agenda(session) -> str:
    """Fetch the colloscope (agenda) page."""
    url = _url("eleve/action/agenda")
    print(f"[*] Fetching agenda: {url}")
    response = session.get(url, timeout=10)
    response.raise_for_status()
    print(f"[+] agenda fetched successfully ({len(response.content)} bytes)")
    return response.text


def parse_agenda_to_rows(html_text: str) -> list[dict]:
    """Parse the ecolle agenda HTML into normalised agenda rows.

    The scraped format has no year, so it is inferred by
    :func:`dates.parse_french_datetime` and stored in ``date_time``. That keeps
    the scraper output shaped exactly like the CSV output.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    table = soup.find("table", class_="tableausimple")
    rows = []
    skipped = 0

    if not table:
        print("[-] No agenda table found.")
        return rows

    for tr in table.find_all("tr")[1:]:  # Skip the header row
        tds = tr.find_all("td")
        if len(tds) != 6:
            skipped += 1
            continue

        date_str = tds[0].get_text(strip=True)
        time_str = tds[1].get_text(strip=True)
        matiere_td = tds[2]
        style = matiere_td.get("style", "")
        couleur = style.replace("background-color:", "").replace("#", "").strip("; ")
        programme_td = tds[4]
        links = [a["href"] for a in programme_td.find_all("a", href=True)]
        popup = programme_td.find("div", class_="popup")

        try:
            when = dates.parse_datetime(f"{date_str} {time_str}")
        except ValueError as error:
            print(f"[!] skipped unusable agenda row ({error})")
            skipped += 1
            continue

        rows.append(
            {
                "date": date_str,
                "heure": time_str,
                "date_time": when.isoformat(sep=" ", timespec="minutes"),
                "matiere": matiere_td.get_text(strip=True),
                "colleur": tds[3].get_text(strip=True),
                "salle": tds[5].get_text(strip=True),
                "jour": date_str.split()[0] if date_str.split() else "",
                "fin": "",
                "couleur": couleur,
                "programme_links": "|".join(links),  # CSV-safe
                "popup": popup.get_text(strip=True) if popup else "",
            }
        )

    if skipped:
        print(f"[!] Skipped {skipped} unusable agenda row(s)")
    return rows


def scrape_and_save() -> list[dict]:
    """Scrape the ecolle website (legacy behaviour) and save the agenda."""
    if requests is None or BeautifulSoup is None:
        raise AgendaError(
            "the scraper fallback needs requests and beautifulsoup4, which are "
            "not installed"
        )

    base_url = config.setting("BASE_URL")
    if not base_url:
        raise AgendaError(
            "no CSV available and BASE_URL is not set, nothing to fetch"
        )

    session = requests.Session()
    session.verify = config.verify_setting()
    login(session, config.setting("COLLES_USERNAME"), config.setting("COLLES_PASSWORD"))

    rows = parse_agenda_to_rows(fetch_agenda(session))
    if not rows:
        raise AgendaError("the ecolle agenda page contained no usable colle")
    return save_agenda(rows)


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #


def fetch_and_save() -> list[dict]:
    """Populate the agenda from the CSV export, or scrape it as a fallback.

    Returns:
        The normalised agenda rows written to ``output/agenda.csv``.

    Raises:
        AgendaError: If no agenda could be built.
    """
    path = config.csv_path()

    if os.path.isfile(path):
        return save_agenda(read_colles_csv(path))

    if config.scraping_disabled():
        raise AgendaError(
            describe_missing_csv(path)
            + " Scraping ecolle is disabled, so nothing was fetched."
        )

    print(f"[!] No CSV found at {path}, falling back to the ecolle website")
    return scrape_and_save()


if __name__ == "__main__":
    fetch_and_save()
