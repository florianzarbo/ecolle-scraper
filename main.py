"""Send ntfy notifications for the next colles."""

import requests

import fetch
import notif
import parse


def main() -> int:
    """Refresh the agenda from the CSV (or scrape it) and notify.

    Returns:
        ``0`` when the run succeeded (including "nothing to send"), ``1`` when
        the agenda could not be built or a notification could not be sent.
    """
    try:
        fetch.fetch_and_save()
    except fetch.AgendaError as error:
        print(f"[!] Could not build the agenda: {error}")
        if not parse.has_agenda():
            return 1
        print("[!] Falling back to the agenda cached by a previous run")

    try:
        colles = parse.get_next_colles()
    except ValueError as error:
        print(f"[!] {error}")
        return 1

    if not colles:
        print("[*] No upcoming colle to notify about")
        return 0

    # Oldest first, so the soonest colle is the last notification sent.
    for colle in colles[::-1]:
        try:
            notif.send_colle(colle)
        except ValueError as error:
            print(f"[!] {error}")
            return 1
        except requests.RequestException as error:
            print(f"[!] Could not send the notification: {error}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
