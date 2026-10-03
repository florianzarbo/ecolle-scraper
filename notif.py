"""ntfy notification helpers."""

import os

import requests

try:  # pragma: no cover - trivial import shim
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
NTFY_TITLE = os.getenv("NTFY_TITLE", "")
NTFY_FORMAT = os.getenv("NTFY_FORMAT", "{matiere} {date} {heure} {salle} {colleur}")

SELF_SIGNED_CERTIFICATE = os.getenv("SELF_SIGNED_CERTIFICATE", "False").lower() in [
    "true"
]
ROOT_CA_PATH = os.getenv("ROOT_CA_PATH", "")  # e.g., "/path/to/rootCA.pem"


def send_ntfy_message(message: str, **headers):
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"

    verify = ROOT_CA_PATH if ROOT_CA_PATH else (not SELF_SIGNED_CERTIFICATE)

    response = requests.post(url, data=message.encode(), headers=headers, verify=verify)
    response.raise_for_status()


def send_colle(colle):
    """Notify about a single colle, formatted with ``NTFY_FORMAT``."""
    try:
        message = NTFY_FORMAT.format(**colle)
    except KeyError as error:
        raise ValueError(
            f"NTFY_FORMAT references the unknown field {error}; available fields: "
            + ", ".join(f"{{{field}}}" for field in colle)
        ) from error
    send_ntfy_message(message, Title=NTFY_TITLE)
