import requests
from dotenv import load_dotenv
import os

load_dotenv()

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")
NTFY_TITLE = os.getenv("NTFY_TITLE", "")

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
    send_ntfy_message(f"{colle["matiere"]} {colle["date"]} {colle["heure"]} {colle["salle"]} {colle["colleur"]}", Title=NTFY_TITLE)