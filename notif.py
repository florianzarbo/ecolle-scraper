"""Send the notifications through ntfy.

The body of a notification is built from :data:`config.NTFY_FORMAT`, a format
string whose fields come from the agenda row plus a few derived ones (see
:func:`derived_fields`).
"""

import re

import requests

import config
import dates

#: Default notification body. Renders as
#: ``vendredi 16 janvier 15h00 P103 - Mathématiques (M Jouve)``.
DEFAULT_NTFY_FORMAT = (
    "{jour} {date_courte} {heure_debut} {salle} - {matiere} ({colleur})"
)

#: ``{field|text}`` renders ``text`` when ``field`` is empty.
FALLBACK_SYNTAX = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\|([^{}]*)\}")


def ntfy_format() -> str:
    """Body format to use, read when needed."""
    return config.setting("NTFY_FORMAT") or DEFAULT_NTFY_FORMAT


def parse_row_date(colle: dict):
    """Return the ``datetime`` of a row, or ``None`` when it is unusable."""
    return dates.parse_row_datetime(colle)


def french_date(when, with_year: bool = False) -> str:
    """Format a date in French: ``16 janvier``, or ``16 janvier 2027``."""
    return dates.french_date(when, with_year)


def french_time(value) -> str:
    """Write a time the French way: ``15:00`` becomes ``15h00``."""
    return dates.french_time(value)


def derived_fields(colle: dict) -> dict:
    """Add the convenience fields that notification templates can use."""
    values = dict(colle)
    heure = (colle.get("heure") or "").strip()
    fin = (colle.get("fin") or "").strip()
    values["heure_debut"] = dates.french_time(heure)
    values["heure_fin"] = (
        f"{dates.french_time(heure)} - {dates.french_time(fin)}"
        if heure and fin
        else dates.french_time(heure) or dates.french_time(fin)
    )

    when = parse_row_date(colle)
    if when is None:
        # Nothing to compute from: leave the date fields empty rather than
        # stopping the whole run because of one odd row.
        values.setdefault("jour", (colle.get("jour") or "").strip())
        values["date_courte"] = ""
        values["date_longue"] = ""
        values["date_annee"] = ""
        values["date_heure"] = ""
        return values

    # The day name comes from the date, so the optional "Jour" column of the
    # export can never make the notification state the wrong day.
    values["jour"] = dates.french_weekday(when)
    values["date_courte"] = dates.french_date(when)
    values["date_longue"] = f"{dates.french_weekday(when)} {dates.french_date(when)}"
    values["date_annee"] = dates.french_date(when, with_year=True)
    values["date_heure"] = (
        f"{dates.french_date(when)} {dates.french_time(heure)}".strip()
    )
    return values


def _tidy(message: str) -> str:
    """Clean up what empty fields leave behind.

    Two artefacts are handled:

    * a separator with nothing between it and the next one, as produced by
      ``{matiere} - {colleur} - {salle}`` when ``colleur`` is empty;
    * empty brackets, as produced by ``{matiere} ({colleur})``.

    Only separators that are surrounded by spaces are touched, so a hyphen
    inside a value is preserved: ``2026-09-24`` must survive intact.
    """
    # A separator with nothing between it and the next one carries no
    # information: "A - - B" is really "A - B". Requiring whitespace between the
    # separators is what keeps the hyphens of an ISO date such as "2026-09-24"
    # out of the match.
    message = re.sub(r"[-–—](?:\s+[-–—])+", " - ", message)
    message = re.sub(r"\s+", " ", message)
    # Only commas lose their leading space: French typography keeps one before
    # "!", "?" and ":".
    message = re.sub(r"\s+,", ",", message)

    # "A ()" and "( )" lose the empty brackets; repeat for nested pairs. The
    # lookbehind keeps the opening bracket of "()" out of the match.
    while True:
        stripped = re.sub(r"(?<!\()\(\s*\)", "", message)
        if stripped == message:
            break
        message = stripped

    message = re.sub(r"\(\s+", "(", message)
    message = re.sub(r"\s+\)", ")", message)
    return re.sub(r" +", " ", message).strip()


def format_message(colle: dict, template: str = None) -> str:
    """Render ``template`` (``NTFY_FORMAT`` by default) for one colle.

    Any column of the row can be used, plus the derived fields. Unknown field
    names are reported with the list of available ones.

    Raises:
        ValueError: If the format string is invalid or names unknown fields.
    """
    template = ntfy_format() if template is None else template
    values = derived_fields(colle)

    def replace_fallback(match: re.Match) -> str:
        name, fallback = match.group(1), match.group(2)
        if name not in values:
            raise ValueError(unknown_field_message(name, values))
        return str(values[name]) if values.get(name) else fallback

    template = FALLBACK_SYNTAX.sub(replace_fallback, template)

    try:
        return _tidy(template.format(**values))
    except KeyError as error:
        raise ValueError(
            unknown_field_message(str(error).strip("'"), values)
        ) from error
    except (IndexError, ValueError) as error:
        raise ValueError(f"NTFY_FORMAT could not be applied ({error})") from error


def unknown_field_message(name: str, values: dict) -> str:
    """Explain an unknown field name and list the usable ones."""
    return (
        f"NTFY_FORMAT references the unknown field '{name}'; available fields: "
        + ", ".join(f"{{{field}}}" for field in sorted(values))
    )


def send_ntfy_message(message: str, **headers):
    """Post one message to the configured topic.

    Raises:
        ValueError: If no topic is configured.
        requests.HTTPError: If the server refuses the message.
    """
    topic = config.ntfy_topic()
    url = f"{config.ntfy_server()}/{topic}"

    response = requests.post(
        url,
        data=message.encode(),
        headers=headers,
        verify=config.verify_setting(),
        timeout=15,
    )
    response.raise_for_status()


def send_colle(colle: dict):
    """Notify about a single colle, formatted with ``NTFY_FORMAT``."""
    if not config.ntfy_topic():
        raise ValueError(
            "NTFY_TOPIC is not set, there is nowhere to send the notification"
        )
    send_ntfy_message(format_message(colle), Title=config.ntfy_title())
