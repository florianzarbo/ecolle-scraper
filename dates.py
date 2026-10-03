"""French date and time handling.

Kept in one place because three modules need it: :mod:`fetch` to normalise the
export, :mod:`parse` to sort the colles and :mod:`notif` to write the message.

Month and day names are hardcoded rather than taken from the ``locale`` module:
``strftime("%B")`` returns ``January`` when ``fr_FR`` is not installed, which
would silently produce English notifications.
"""

import datetime
import unicodedata

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

#: Accepted date layouts, tried in order.
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")

#: Accepted time layouts, tried in order.
TIME_FORMATS = ("%H:%M", "%H:%M:%S", "%Hh%M", "%Hh")

#: The school year rolls over in the summer holidays: a month before July seen
#: after July belongs to the next year.
ROLLOVER_MONTH = 7


def ascii_fold(text: str) -> str:
    """Strip accents and lowercase, for tolerant lookups."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


#: Month name (accent-insensitive) to month number.
MONTH_NUMBERS = {ascii_fold(name): number for number, name in enumerate(MONTHS, 1)}
MONTH_NUMBERS.update(
    {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
)


def infer_year(month: int, now: datetime.datetime = None) -> int:
    """Guess the year of a date given only its month.

    School years run from September to July, so a colle in a month before July
    that is announced after July is in the next calendar year.
    """
    now = now or datetime.datetime.now()
    if now.month > ROLLOVER_MONTH and month <= ROLLOVER_MONTH:
        return now.year + 1
    return now.year


def parse_date(value: str) -> datetime.date:
    """Parse a date as ``YYYY-MM-DD``, or the tolerated French layouts.

    Raises:
        ValueError: If no supported layout matches.
    """
    value = (value or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {value!r} (expected YYYY-MM-DD)")


def parse_time(value: str) -> datetime.time:
    """Parse a time as ``HH:MM``, or the tolerated layouts.

    Raises:
        ValueError: If no supported layout matches.
    """
    value = (value or "").strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"unrecognised time {value!r} (expected HH:MM)")


def parse_french_datetime(value: str, now: datetime.datetime = None):
    """Parse the legacy scraped format, e.g. ``jeudi 24 septembre 17h00``.

    The year is not part of that format, so it is inferred with
    :func:`infer_year` and, failing that, the following year is tried. The day
    name is ignored: only the day number, the month and the time are used.

    Raises:
        ValueError: If the text does not look like that format.
    """
    parts = (value or "").split()
    if len(parts) >= 4 and parts[0].isalpha():
        parts = parts[1:]  # drop the day name, e.g. "jeudi"
    if len(parts) < 3 or not parts[0].rstrip("er").isdigit():
        raise ValueError(f"unrecognised date {value!r}")

    day, month_name, time_text = parts[0], parts[1], parts[2]
    month = MONTH_NUMBERS.get(ascii_fold(month_name))
    if month is None:
        raise ValueError(f"unrecognised month {month_name!r} in {value!r}")

    year = infer_year(month, now)
    for candidate_year in (year, year + 1):
        for candidate in (
            f"{day} {month} {time_text} {candidate_year}",
            f"{day} {month} {time_text.replace('h', ':')} {candidate_year}",
        ):
            for fmt in ("%d %m %Hh%M %Y", "%d %m %H:%M %Y"):
                try:
                    return datetime.datetime.strptime(candidate, fmt)
                except ValueError:
                    continue
    raise ValueError(f"unrecognised date {value!r}")


def parse_datetime(value: str, now: datetime.datetime = None):
    """Parse a date, with a time, in any supported form.

    Accepts the normalised ``YYYY-MM-DD HH:MM`` and the legacy French text.

    Raises:
        ValueError: If the text is not a date in a supported form.
    """
    value = (value or "").strip()
    if not value:
        raise ValueError("empty date")

    # Tolerate the ISO "T" separator and a trailing "Z".
    normalised = value.replace("T", " ").rstrip("Z").strip()
    try:
        return datetime.datetime.fromisoformat(normalised)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(normalised, fmt)
        except ValueError:
            continue

    return parse_french_datetime(value, now)


def parse_row_datetime(row: dict, now: datetime.datetime = None):
    """Return the ``datetime`` of an agenda row, or ``None`` if unusable."""
    raw = (row.get("date_time") or "").strip()
    if not raw:
        date = (row.get("date") or "").strip()
        time = (row.get("heure") or "").strip()
        raw = f"{date} {time}".strip()
    if not raw:
        return None
    try:
        return parse_datetime(raw, now)
    except ValueError:
        return None


def french_date(when: datetime.date, with_year: bool = False) -> str:
    """Format a date in French: ``16 janvier``, or ``16 janvier 2027``."""
    text = f"{when.day} {MONTHS[when.month - 1]}"
    return f"{text} {when.year}" if with_year else text


def french_weekday(when: datetime.date) -> str:
    """French day name of a date."""
    return WEEKDAYS[when.weekday()]


def french_time(value) -> str:
    """Write a time the French way: ``15:00`` becomes ``15h00``."""
    if isinstance(value, datetime.time):
        return f"{value.hour}h{value.minute:02d}"
    if isinstance(value, datetime.datetime):
        return f"{value.hour}h{value.minute:02d}"
    text = (value or "").strip()
    return text.replace(":", "h") if text else ""
