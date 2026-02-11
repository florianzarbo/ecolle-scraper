#! .venv/bin/python
import requests
from bs4 import BeautifulSoup
import pandas as pd
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


def parse_agenda_to_csv(html_text):
    """
    Parse e-colle agenda HTML and save to agenda.csv.

    Args:
        html_text (str): Raw HTML from requests.get(url).text

    Returns:
        pd.DataFrame: Parsed agenda data
    """
    soup = BeautifulSoup(html_text, "html.parser")
    table = soup.find("table", class_="tableausimple")
    rows = []

    if not table:
        print("No agenda table found.")
        return pd.DataFrame()

    for tr in table.find_all("tr")[1:]:  # Skip header
        tds = tr.find_all("td")
        if len(tds) == 6:
            date_str = tds[0].get_text(strip=True)
            time_str = tds[1].get_text(strip=True)
            matiere_td = tds[2]
            matiere = matiere_td.get_text(strip=True)
            couleur_style = matiere_td.get("style", "")
            couleur = (
                couleur_style.replace("background-color:", "")
                .replace("#", "")
                .strip("; ")
            )
            colleur = tds[3].get_text(strip=True)
            programme_td = tds[4]
            programme_links = [a["href"] for a in programme_td.find_all("a", href=True)]
            popup = programme_td.find("div", class_="popup")
            popup_text = popup.get_text(strip=True) if popup else ""
            salle = tds[5].get_text(strip=True)

            rows.append(
                {
                    "date": date_str,
                    "heure": time_str,
                    "matiere": matiere,
                    "couleur": couleur,
                    "colleur": colleur,
                    "programme_links": "|".join(programme_links),  # CSV-safe
                    "popup": popup_text,
                    "salle": salle,
                }
            )

    df = pd.DataFrame(rows)
    df.to_csv("agenda.csv", index=False)
    print(f"Saved {len(df)} rows to agenda.csv")
    return df


def main():
    ses = requests.Session()
    login(ses, USERNAME, PASSWORD)
    parse_agenda_to_csv(fetch_agenda(ses))


if __name__ == "__main__":
    main()
