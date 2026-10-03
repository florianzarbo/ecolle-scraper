"""Reading of the environment variables, in one place.

Every other module goes through :func:`setting` so that a variable set to an
empty string is treated as unset, consistently. Reading happens when the value
is used rather than at import time, so tests can change the environment and a
``.env`` file loaded later still takes effect.
"""

import os

try:  # pragma: no cover - trivial import shim
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

#: Default locations, relative to the working directory (``/app`` in Docker).
DEFAULT_CSV_PATH = os.path.join("input", "colles.csv")
DEFAULT_OUTPUT_PATH = os.path.join("output", "agenda.csv")

#: Truthy spellings accepted for the boolean settings.
TRUE_VALUES = ("1", "true", "yes", "on")

#: Names accepted for "never scrape ecolle, the CSV is the only source".
DISABLE_FETCH_NAMES = (
    "DISABLE_ECOLLE_FETCH",
    "DISABLE_ECALLE_FETCH",  # misspelling shipped in v2.1.0, kept as an alias
    "DISABLE_SCRAPER_FALLBACK",
    "NO_SCRAPE",
)


def setting(name: str, default: str = "") -> str:
    """Return an environment variable, treating blank values as unset."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def setting_any(names, default: str = "") -> str:
    """Return the first of ``names`` that is set."""
    for name in names:
        value = setting(name)
        if value:
            return value
    return default


def is_true(value: str) -> bool:
    """Interpret a human-written boolean."""
    return (value or "").strip().lower() in TRUE_VALUES


def scraping_disabled() -> bool:
    """Whether the ecolle website must never be contacted."""
    return is_true(setting_any(DISABLE_FETCH_NAMES, "false"))


def csv_path() -> str:
    """Path of the CSV export to read."""
    return setting("COLLES_CSV_PATH", DEFAULT_CSV_PATH)


def output_path() -> str:
    """Path of the normalised agenda written for :mod:`parse`."""
    return setting("AGENDA_CSV_PATH", DEFAULT_OUTPUT_PATH)


def number_of_colles_to_show() -> int:
    """How many upcoming colles to send.

    Raises:
        ValueError: If the value is not a positive integer.
    """
    raw = setting("NUMBER_OF_COLLES_TO_SHOW", "1")
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"NUMBER_OF_COLLES_TO_SHOW must be a whole number, got {raw!r}"
        ) from None
    if value < 1:
        raise ValueError(
            f"NUMBER_OF_COLLES_TO_SHOW must be at least 1, got {value}"
        )
    return value


def ntfy_server() -> str:
    """Base URL of the ntfy server, without a trailing slash."""
    return setting("NTFY_SERVER", "https://ntfy.sh").rstrip("/")


def ntfy_topic() -> str:
    """ntfy topic to publish to."""
    return setting("NTFY_TOPIC")


def ntfy_title() -> str:
    """Title of the notifications."""
    return setting("NTFY_TITLE")


def verify_setting():
    """Value for ``requests``'s ``verify`` argument."""
    root_ca = setting("ROOT_CA_PATH")
    if root_ca:
        return root_ca
    return not is_true(setting("SELF_SIGNED_CERTIFICATE", "False"))
