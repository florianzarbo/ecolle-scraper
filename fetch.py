#! .venv/bin/python
"""Build ``output/agenda.csv`` from a CSV export of the ecolle agenda.

Since v2.0.0 the colles are read from a CSV file instead of being scraped from
the ecolle website. The expected file looks like this::

    Date,Matière,Colleur,Jour,Salle,Début,Fin
    2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00
    2026-09-30,Physique,M Blain,mercredi,L124,15:00,16:00

Only the header names and the ``YYYY-MM-DD`` dates matter: accents, casing,
extra whitespace, extra columns and a BOM are all tolerated. The rows are
normalised into ``output/agenda.csv``, which is the file :mod:`parse` reads.

If the CSV file cannot be found, the legacy HTML scraper is used as a fallback,
so an existing ecolle instance still works. Set ``DISABLE_ECALLE_FETCH=true`` to
turn that fallback off and use the CSV file as the only source.
"""

import csv
import datetime
import os
from typing import Optional
from urllib.parse import urljoin

try:  # pragma: no cover - trivial import shim
    import requests
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional, scraper fallback only
    requests = None
    BeautifulSoup = None

try:  # pragma: no cover - trivial import shim
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

# Load credentials from .env file
if load_dotenv is not None:
    load_dotenv()

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

#: File to read the colles from. Overridable with ``COLLES_CSV_PATH``.
DEFAULT_CSV_PATH = os.path.join("input", "colles.csv")
DEFAULT_OUTPUT_PATH = os.path.join("output", "agenda.csv")

#: Same columns as the scraper, plus the fields of the CSV export, so the rest
#: of the pipeline (parse.py, notif.py) keeps working unchanged.
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

#: Accepted header spellings, mapped to the internal (output) column name.
COLUMN_ALIASES = {
    "date": "date",
    "matiere": "matiere",
    "colleur": "colleur",
    "jour": "jour",
    "salle": "salle",
    "debut": "debut",
    "fin": "fin",
}

#: Header names expected in the CSV export, in their usual spelling.
INPUT_FIELDS = ["Date", "Matière", "Colleur", "Jour", "Salle", "Début", "Fin"]

#: Columns without which the file is unusable.
REQUIRED_COLUMNS = ["date", "matiere", "colleur", "salle", "debut"]

#: Accepted date/time layouts, tried in order.
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")
TIME_FORMATS = ("%H:%M", "%H:%M:%S", "%Hh%M", "%Hh")

BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
LOGIN_URL = urljoin(BASE_URL + "/", "eleve/")
AGENDA_URL = urljoin(BASE_URL + "/", "eleve/action/agenda")

USERNAME = os.getenv("COLLES_USERNAME", "")
PASSWORD = os.getenv("COLLES_PASSWORD", "")


class AgendaError(Exception):
    """Raised when the CSV export is present but cannot be used."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def setting(name: str, default: str = "") -> str:
    """Return an environment variable, treating blank values as unset."""
    value = os.getenv(name)
    return value if value not in (None, "") else default


def setting_any(names, default: str = "") -> str:
    """Return the first of ``names`` that is set."""
    for name in names:
        value = setting(name)
        if value:
            return value
    return default


def is_true(value: str) -> bool:
    """Interpret a human-written boolean."""
    return value.strip().lower() in ("1", "true", "yes", "on")


#: Names accepted for "never scrape ecolle, the CSV is the only source".
DISABLE_FETCH_NAMES = (
    "DISABLE_ECALLE_FETCH",
    "DISABLE_SCRAPER_FALLBACK",
    "NO_SCRAPE",
)


def scraping_disabled() -> bool:
    """Whether the ecolle website must never be contacted."""
    return is_true(setting_any(DISABLE_FETCH_NAMES, "false"))


def csv_path() -> str:
    """Path of the CSV export to read."""
    return setting("COLLES_CSV_PATH", DEFAULT_CSV_PATH)


def output_path() -> str:
    """Path of the normalised agenda written for :mod:`parse`."""
    return setting("AGENDA_CSV_PATH", DEFAULT_OUTPUT_PATH)


def normalize_header(name: Optional[str]) -> str:
    """Lowercase a header and strip accents, spaces, underscores and dashes."""
    if name is None:
        return ""
    cleaned = name.strip().lower().replace("\ufeff", "")
    for source, target in (
        ("é", "e"),
        ("è", "e"),
        ("ê", "e"),
        ("à", "a"),
        ("û", "u"),
        ("ô", "o"),
    ):
        cleaned = cleaned.replace(source, target)
    return cleaned.replace(" ", "").replace("_", "").replace("-", "")


def parse_date(raw: str) -> datetime.date:
    """Parse a date, trying every supported layout."""
    raw = (raw or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {raw!r} (expected YYYY-MM-DD)")


def parse_time(raw: str) -> datetime.time:
    """Parse a time, trying every supported layout."""
    raw = (raw or "").strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"unrecognised time {raw!r} (expected HH:MM)")


# --------------------------------------------------------------------------- #
# CSV source
# --------------------------------------------------------------------------- #


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

    if os.environ.get("COLLES_CSV_PATH"):
        message.append(
            "COLLES_CSV_PATH is the path *inside* the container: with the "
            "provided docker-compose.yml, ./input on the host is /app/input."
        )
    else:
        message.append("COLLES_CSV_PATH is not set, using the default path.")

    return " ".join(message)


def read_colles_csv(path: str) -> list[dict]:
    """Read the ecolle CSV export and return normalised agenda rows.

    Args:
        path: Path of the CSV file exported from ecolle.

    Returns:
        Rows shaped like the historical scraper output, sorted by date.

    Raises:
        AgendaError: If the file is empty, malformed or has no usable row.
    """
    print(f"[*] Reading CSV: {path}")
    try:
        csvfile = open(path, newline="", encoding="utf-8-sig")
    except PermissionError as error:
        raise AgendaError(
            f"{path} exists but cannot be read ({error}). The file is mounted "
            "read-only, make sure it is world-readable (chmod a+r)."
        ) from error
    except IsADirectoryError as error:
        raise AgendaError(
            f"{path} is a directory, COLLES_CSV_PATH must point at the CSV file"
        ) from error
    except UnicodeDecodeError as error:
        raise AgendaError(
            f"{path} is not valid UTF-8 text ({error}). Export the CSV again as "
            "UTF-8 or comma-separated values."
        ) from error
    except OSError as error:
        raise AgendaError(f"{path} could not be opened ({error})") from error

    with csvfile:
        reader = csv.DictReader(csvfile)
        if reader.fieldnames is None:
            raise AgendaError(f"{path} is empty")

        columns = {}
        for field in reader.fieldnames:
            target = COLUMN_ALIASES.get(normalize_header(field))
            if target:
                columns[target] = field

        missing = [name for name in REQUIRED_COLUMNS if name not in columns]
        if missing:
            raise AgendaError(
                f"{path}: missing column(s) {', '.join(missing)} "
                f"(found: {', '.join(reader.fieldnames)}). "
                "The file must be a comma-separated export with the headers "
                + ", ".join(INPUT_FIELDS)
            )

        rows = []
        for lineno, raw in enumerate(reader, start=2):
            if not any((value or "").strip() for value in raw.values()):
                continue  # skip blank lines
            try:
                date = parse_date(raw.get(columns["date"], ""))
                start = parse_time(raw.get(columns["debut"], ""))
            except ValueError as error:
                print(f"[!] {path}:{lineno}: skipped row ({error})")
                continue

            rows.append(
                {
                    "date": date.isoformat(),
                    "heure": start.strftime("%H:%M"),
                    "date_time": datetime.datetime.combine(
                        date, start
                    ).isoformat(sep=" ", timespec="minutes"),
                    "matiere": (raw.get(columns["matiere"]) or "").strip(),
                    "colleur": (raw.get(columns["colleur"]) or "").strip(),
                    "salle": (raw.get(columns["salle"]) or "").strip(),
                    "jour": (raw.get(columns.get("jour", "")) or "").strip(),
                    "fin": (raw.get(columns.get("fin", "")) or "").strip(),
                    # Kept for backward compatibility with the scraper output.
                    "couleur": "",
                    "programme_links": "",
                    "popup": "",
                }
            )

    if not rows:
        raise AgendaError(
            f"{path}: no usable row found, check that the dates look like 2026-09-24 "
            "and the times like 17:00"
        )

    rows.sort(key=lambda row: row["date_time"])
    print(f"[+] Parsed {len(rows)} colles from CSV")
    return rows


def save_agenda(rows: list[dict]) -> list[dict]:
    """Write rows to the normalised agenda file read by :mod:`parse`."""
    path = output_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] Saved {len(rows)} rows to {path}")
    return rows


# --------------------------------------------------------------------------- #
# Legacy HTML scraper (fallback when no CSV is available)
# --------------------------------------------------------------------------- #


def get_csrf_token(session) -> str:
    """
    Fetch the login page and extract the CSRF token

    Args:
        session: requests.Session object

    Returns:
        str: CSRF token
    """
    print(f"[*] Fetching login page: {LOGIN_URL}")
    response = session.get(LOGIN_URL, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})

    if not csrf_input:
        raise ValueError("Could not find CSRF token in login page")

    csrf_token = csrf_input.get("value")
    print(f"[+] CSRF token extracted: {csrf_token[:20]}...")

    return csrf_token


def login(session, username: str, password: str) -> bool:
    """
    Login to the e-colle system with proper CSRF handling
    """
    print("[*] Extracting CSRF token...")
    csrf_token = get_csrf_token(session)

    login_data = {
        "csrfmiddlewaretoken": csrf_token,
        "username": username,
        "password": password,
    }

    headers = {
        "Referer": LOGIN_URL,
        "Origin": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    print(f"[*] Logging in as user: {username}")
    response = session.post(
        LOGIN_URL,
        data=login_data,
        headers=headers,
        allow_redirects=True,
        timeout=10,
    )
    response.raise_for_status()

    if "Déconnexion" in response.text:
        print("[+] Login successful!")
    else:
        print("[-] Login may have failed. Continuing anyway...")
    return True


def fetch_agenda(session) -> str:
    """Fetch the colloscope (agenda) page"""
    print(f"[*] Fetching agenda: {AGENDA_URL}")
    response = session.get(AGENDA_URL, timeout=10)
    response.raise_for_status()

    print(f"[+] agenda fetched successfully ({len(response.content)} bytes)")
    return response.text


def parse_agenda_to_rows(html_text: str) -> list[dict]:
    """Parse the ecolle agenda HTML into normalised agenda rows."""
    soup = BeautifulSoup(html_text, "html.parser")
    table = soup.find("table", class_="tableausimple")
    rows = []

    if not table:
        print("[-] No agenda table found.")
        return rows

    for tr in table.find_all("tr")[1:]:  # Skip header
        tds = tr.find_all("td")
        if len(tds) != 6:
            continue

        date_str = tds[0].get_text(strip=True)
        time_str = tds[1].get_text(strip=True)
        matiere_td = tds[2]
        couleur_style = matiere_td.get("style", "")
        couleur = (
            couleur_style.replace("background-color:", "").replace("#", "").strip("; ")
        )
        programme_td = tds[4]
        programme_links = [a["href"] for a in programme_td.find_all("a", href=True)]
        popup = programme_td.find("div", class_="popup")

        rows.append(
            {
                "date": date_str,
                "heure": time_str,
                "date_time": "",
                "matiere": matiere_td.get_text(strip=True),
                "colleur": tds[3].get_text(strip=True),
                "salle": tds[5].get_text(strip=True),
                "jour": date_str.split()[0] if date_str.split() else "",
                "fin": "",
                "couleur": couleur,
                "programme_links": "|".join(programme_links),  # CSV-safe
                "popup": popup.get_text(strip=True) if popup else "",
            }
        )

    return rows


def scrape_and_save() -> list[dict]:
    """Scrape the ecolle website (legacy behaviour) and save the agenda."""
    if requests is None or BeautifulSoup is None:
        raise RuntimeError(
            "requests and beautifulsoup4 are required for the scraper fallback"
        )
    if not BASE_URL:
        raise RuntimeError("no CSV available and BASE_URL is not set, nothing to fetch")

    session = requests.Session()
    session.verify = setting("ROOT_CA_PATH") or (
        setting("SELF_SIGNED_CERTIFICATE", "False").lower() != "true"
    )
    login(session, USERNAME, PASSWORD)
    return save_agenda(parse_agenda_to_rows(fetch_agenda(session)))


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #


def fetch_and_save() -> list[dict]:
    """Populate the agenda from the CSV export, or scrape it as a fallback.

    The scraper fallback is skipped entirely when scraping is disabled, see
    :data:`DISABLE_FETCH_NAMES`.

    Returns:
        The normalised agenda rows written to ``output/agenda.csv``.

    Raises:
        AgendaError: If no agenda could be built.
    """
    path = csv_path()

    if os.path.isfile(path):
        return save_agenda(read_colles_csv(path))

    if scraping_disabled():
        raise AgendaError(
            describe_missing_csv(path)
            + " Scraping ecolle is disabled, so nothing was fetched."
        )

    print(f"[!] No CSV found at {path}, falling back to the ecolle website")
    try:
        return scrape_and_save()
    except AgendaError:
        raise
    except Exception as error:
        raise AgendaError(
            f"no CSV at {path} and scraping the ecolle website failed ({error})"
        ) from error


if __name__ == "__main__":
    fetch_and_save()
