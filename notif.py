"""ntfy notification helpers."""

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
#: ``{heure_fin}`` is the start time, followed by the end time when known.
DEFAULT_NTFY_FORMAT = (
    "{jour} {date} {heure_fin} - {matiere} en {salle} ({colleur})"
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


def derived_fields(colle: dict) -> dict:
    """Add the convenience fields that templates can use."""
    values = dict(colle)
    heure = (colle.get("heure") or "").strip()
    fin = (colle.get("fin") or "").strip()
    if heure and fin:
        values["heure_fin"] = f"{heure} - {fin}"
    else:
        values["heure_fin"] = heure or fin
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
