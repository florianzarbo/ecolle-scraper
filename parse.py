import csv
import datetime
import locale
from dotenv import load_dotenv
import os

load_dotenv()
NUMBER_OF_COLLES_TO_SHOW = int(os.getenv("NUMBER_OF_COLLES_TO_SHOW", "1"))


locale.setlocale(locale.LC_ALL, "fr_FR.utf8")


def parse_date_string(datestring):
    now = datetime.datetime.now()
    year = now.year
    temp = datetime.datetime.strptime(
        datestring.split()[2], "%B"
    )  # to get only the month data
    if temp.month < now.month:
        year += 1
    return datetime.datetime.strptime(datestring + " " + str(year), "%A %d %B %Hh%M %Y")


def get_next_colles():
    out = []

    with open("output/agenda.csv", newline="") as csvfile:
        sreader = csv.DictReader(csvfile)
        m = 0
        n = 0
        sreader = list(sreader)
        parsed = parse_date_string(sreader[n]["date"] + " " + sreader[n]["heure"])
        while n < len(sreader)-1 and m < NUMBER_OF_COLLES_TO_SHOW:
            if parsed.timestamp() > datetime.datetime.now().timestamp():
                m += 1
                print("next colle: ", parsed)
                out.append(sreader[n])
            n += 1
            parsed = parse_date_string(sreader[n]["date"] + " " + sreader[n]["heure"])

    return out


