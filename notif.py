"""ntfy notification helpers."""

import datetime
import os
import re

import requests

try:  # pragma: no cover - trivial import shim
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

#: Default notification body, see docs/configuration.md.
#: Renders as "vendredi 16 janvier 15h00 P103 - Mathématiques (M Jouve)".
DEFAULT_NTFY_FORMAT = (
    "{jour} {date_courte} {heure_debut} {salle} - {matiere} ({colleur})"
)

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
NTFY_TITLE = os.getenv("NTFY_TITLE", "")
NTFY_FORMAT = os.getenv("NTFY_FORMAT") or DEFAULT_NTFY_FORMAT

SELF_SIGNED_CERTIFICATE = os.getenv("SELF_SIGNED_CERTIFICATE", "False").lower() in [
    "true"
]
ROOT_CA_PATH = os.getenv("ROOT_CA_PATH", "")  # e.g., "/path/to/rootCA.pem"

#: Fields that are computed from a row instead of being columns of the agenda.
#: ``{field|fallback}`` renders the field, or the fallback text when it is empty.
FALLBACK_SYNTAX = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\|([^{}]*)\}")

#: French names, hardcoded so the output does not depend on the host locale.
#: Without fr_FR, ``strftime("%B")`` would silently return "January".
MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
WEEKDAYS = (
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
)


def parse_row_date(colle: dict):
    """Return the ``datetime`` of a row, or ``None`` when it is unusable."""
    raw = (colle.get("date_time") or "").strip()
    if not raw:
        raw = " ".join(
            part for part in (colle.get("date"), colle.get("heure")) if part
        ).strip()
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(raw)
    except ValueError:
        pass
    try:  # legacy scraped format, e.g. "jeudi 24 septembre 17h00"
        return datetime.datetime.strptime(raw, "%A %d %B %Hh%M")
    except ValueError:
        return None


def french_date(when: datetime.datetime, with_year: bool = False) -> str:
    """Format a date in French: ``16 janvier``, or ``16 janvier 2027``."""
    text = f"{when.day} {MONTHS[when.month - 1]}"
    return f"{text} {when.year}" if with_year else text


def french_time(value: str) -> str:
    """Write a time the French way: ``15:00`` becomes ``15h00``."""
    value = (value or "").strip()
    return value.replace(":", "h") if value else ""


def derived_fields(colle: dict) -> dict:
    """Add the convenience fields that templates can use."""
    values = dict(colle)
    heure = (colle.get("heure") or "").strip()
    fin = (colle.get("fin") or "").strip()
    values["heure_debut"] = french_time(heure)
    values["heure_fin"] = (
        f"{french_time(heure)} - {french_time(fin)}"
        if heure and fin
        else french_time(heure) or french_time(fin)
    )

    when = parse_row_date(colle)
    if when is None:
        # Nothing to compute from, leave the extras empty.
        values.setdefault("jour", (colle.get("jour") or "").strip())
        values["date_courte"] = ""
        values["date_longue"] = ""
        values["date_annee"] = ""
        values["date_heure"] = ""
        return values

    # The day name is derived from the date, so it cannot go out of sync with
    # the optional "Jour" column of the export.
    values["jour"] = WEEKDAYS[when.weekday()]
    values["date_courte"] = french_date(when)
    values["date_longue"] = f"{WEEKDAYS[when.weekday()]} {french_date(when)}"
    values["date_annee"] = french_date(when, with_year=True)
    values["date_heure"] = f"{french_date(when)} {french_time(heure)}".strip()
    return values


def _tidy(message: str) -> str:
    """Collapse the spacing and punctuation left behind by empty fields."""
    message = re.sub(r"\s+", " ", message)
    message = re.sub(r"\s+([,;:!?])", r"\1", message)
    message = re.sub(r"\(\s+", "(", message)
    message = re.sub(r"\s+\)", ")", message)
    return message.strip()


def format_message(colle: dict, template: str = None) -> str:
    """Render ``template`` (``NTFY_FORMAT`` by default) for one colle.

    Any column of the row can be used, plus the derived ``{heure_fin}`` field.
    ``{field|fallback}`` renders the fallback when the field is empty, which is
    handy for the optional ``Jour`` and ``Fin`` columns. Unknown field names are
    reported instead of raising a bare ``KeyError``.
    """
    template = NTFY_FORMAT if template is None else template
    values = derived_fields(colle)

    # Resolve {field|fallback} before the real formatting pass.
    def replace_fallback(match: re.Match) -> str:
        name, fallback = match.group(1), match.group(2)
        if name not in values:
            raise ValueError(
                f"NTFY_FORMAT references the unknown field '{name}'; available "
                "fields: " + ", ".join(f"{{{field}}}" for field in values)
            )
        return str(values[name]) if values.get(name) else fallback

    template = FALLBACK_SYNTAX.sub(replace_fallback, template)

    try:
        return _tidy(template.format(**values))
    except KeyError as error:
        raise ValueError(
            f"NTFY_FORMAT references the unknown field {error}; available fields: "
            + ", ".join(f"{{{field}}}" for field in values)
        ) from error
    except (IndexError, ValueError) as error:
        raise ValueError(f"NTFY_FORMAT could not be applied ({error})") from error


def send_ntfy_message(message: str, **headers):
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"

    verify = ROOT_CA_PATH if ROOT_CA_PATH else (not SELF_SIGNED_CERTIFICATE)

    response = requests.post(url, data=message.encode(), headers=headers, verify=verify)
    response.raise_for_status()


def send_colle(colle):
    """Notify about a single colle, formatted with ``NTFY_FORMAT``."""
    send_ntfy_message(format_message(colle), Title=NTFY_TITLE)
