"""Send ntfy notifications for the next colles."""

import notif
import fetch
import parse


def main() -> int:
    """Refresh the agenda from the CSV (or scrape it) and notify."""
    try:
        fetch.fetch_and_save()
    except Exception as error:
        # No agenda could be built: keep the notifications going with the
        # cached agenda if there is one, otherwise say why and give up.
        print(f"[!] Could not build the agenda: {error}")
        if not parse.has_agenda():
            return 1
        print("[!] Falling back to the cached agenda from a previous run")

    colles = parse.get_next_colles()
    if not colles:
        print("[*] No upcoming colle to notify about")
        return 0

    # Oldest first, so the soonest colle is the last notification sent.
    for colle in colles[::-1]:
        notif.send_colle(colle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
