#! .venv/bin/python
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()

BASE_URL = "https://colles.janson-de-sailly.fr"
LOGIN_URL = urljoin(BASE_URL, "/eleve/")
AGENDA_URL = urljoin(BASE_URL, "/eleve/action/agenda")

USERNAME = os.getenv("COLLES_USERNAME", "")
PASSWORD = os.getenv("COLLES_PASSWORD", "")


def get_csrf_token(session: requests.Session) -> str:
    """
    Fetch the login page and extract the CSRF token

    Args:
        session: requests.Session object

    Returns:
        str: CSRF token
    """
    print(f"[*] Fetching login page: {LOGIN_URL}")
    response = session.get(LOGIN_URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})

    if not csrf_input:
        raise ValueError("Could not find CSRF token in login page")

    csrf_token = csrf_input.get("value")
    print(f"[+] CSRF token extracted: {csrf_token[:20]}...")

    return csrf_token


def login(session: requests.Session, username: str, password: str) -> bool:
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
    try:
        response = session.post(
            LOGIN_URL,
            data=login_data,
            headers=headers,
            allow_redirects=True,
            timeout=10,
        )
        response.raise_for_status()

        if "Déconlnexion" in response.text:
            print("[+] Login successful!")
            return True
        else:
            print("[-] Login may have failed. Continuing anyway...")
            return True

    except requests.exceptions.HTTPError as e:
        print(f"[!] HTTP Error during login: {e}")
        raise


def fetch_agenda(session: requests.Session) -> str:
    """Fetch the colloscope (agenda) page"""
    print(f"[*] Fetching agenda: {AGENDA_URL}")
    response = session.get(AGENDA_URL, timeout=10)
    response.raise_for_status()

    print(f"[+] agenda fetched successfully ({len(response.content)} bytes)")
    return response.text


def main():
    ses = requests.Session()
    login(ses, USERNAME, PASSWORD)


if __name__ == "__main__":
    main()
