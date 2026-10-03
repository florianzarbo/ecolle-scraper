"""Regression tests for the CSV pipeline.

Run with::

    uv run python -m unittest discover -s tests

Only the standard library is needed.
"""

import datetime
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fetch  # noqa: E402
import parse  # noqa: E402

HEADER = "Date,Matière,Colleur,Jour,Salle,Début,Fin\n"
ROWS = (
    "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00\n"
    "2026-09-30,Physique,M Blain,mercredi,L124,15:00,16:00\n"
    "2026-10-06,Mathématiques,M Jouve,mardi,L005,16:00,17:00\n"
)


class TempAgenda(unittest.TestCase):
    """Base class giving each test its own CSV files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.csv = os.path.join(self.tmp.name, "colles.csv")
        self.out = os.path.join(self.tmp.name, "agenda.csv")
        self._env = dict(os.environ)
        self.addCleanup(self._restore_env)
        os.environ["COLLES_CSV_PATH"] = self.csv
        os.environ["AGENDA_CSV_PATH"] = self.out

    def _restore_env(self):
        os.environ.clear()
        os.environ.update(self._env)

    def write_csv(self, text):
        with open(self.csv, "w", encoding="utf-8") as handle:
            handle.write(text)


class TestReadCsv(TempAgenda):
    def test_parses_the_expected_export(self):
        self.write_csv(HEADER + ROWS)
        rows = fetch.read_colles_csv(self.csv)

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["date"], "2026-09-24")
        self.assertEqual(rows[0]["heure"], "17:00")
        self.assertEqual(rows[0]["date_time"], "2026-09-24 17:00")
        self.assertEqual(rows[0]["matiere"], "Anglais")
        self.assertEqual(rows[0]["colleur"], "Mme Hatri")
        self.assertEqual(rows[0]["salle"], "L037")
        self.assertEqual(rows[0]["jour"], "jeudi")
        self.assertEqual(rows[0]["fin"], "18:00")

    def test_rows_are_sorted_by_date(self):
        self.write_csv(
            HEADER
            + "2026-10-06,Mathématiques,M Jouve,mardi,L005,16:00,17:00\n"
            + "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00\n"
        )
        rows = fetch.read_colles_csv(self.csv)
        self.assertEqual([row["date"] for row in rows], ["2026-09-24", "2026-10-06"])

    def test_tolerates_bom_accents_and_extra_columns(self):
        self.write_csv(
            "\ufeffDate, Matiere ,Colleur,Jour,Salle,Début,Fin,Note\n"
            "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00,rien\n"
        )
        rows = fetch.read_colles_csv(self.csv)
        self.assertEqual(rows[0]["matiere"], "Anglais")

    def test_skips_bad_and_blank_rows(self):
        self.write_csv(
            HEADER
            + "pas-une-date,Anglais,X,jeudi,L037,17:00,18:00\n"
            + "2026-10-07,Anglais,X,jeudi,L037,25:99,18:00\n"
            + "\n"
            + "2026-10-08,Anglais,X,jeudi,L037,18:00,19:00\n"
        )
        rows = fetch.read_colles_csv(self.csv)
        self.assertEqual([row["date"] for row in rows], ["2026-10-08"])

    def test_missing_column_is_reported(self):
        self.write_csv("Date,Matière,Colleur,Jour,Salle\n")
        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.read_colles_csv(self.csv)
        self.assertIn("debut", str(caught.exception))

    def test_empty_file_is_reported(self):
        self.write_csv("")
        with self.assertRaises(fetch.AgendaError):
            fetch.read_colles_csv(self.csv)

    def test_header_only_is_reported(self):
        self.write_csv(HEADER)
        with self.assertRaises(fetch.AgendaError):
            fetch.read_colles_csv(self.csv)

    def test_semicolon_separator_is_reported(self):
        self.write_csv(HEADER.replace(",", ";") + ROWS.replace(",", ";"))
        with self.assertRaises(fetch.AgendaError):
            fetch.read_colles_csv(self.csv)


class TestFetchAndSave(TempAgenda):
    def test_csv_wins_and_is_written_for_parse(self):
        self.write_csv(HEADER + ROWS)
        rows = fetch.fetch_and_save()

        self.assertEqual(len(rows), 3)
        self.assertTrue(os.path.isfile(self.out))
        with open(self.out, encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 4)  # header + 3 rows

    def test_missing_csv_falls_back_to_the_scraper(self):
        called = []
        original = fetch.scrape_and_save
        fetch.scrape_and_save = lambda: called.append(True) or []
        self.addCleanup(setattr, fetch, "scrape_and_save", original)

        fetch.fetch_and_save()
        self.assertEqual(called, [True])

    def test_missing_csv_and_broken_scraper_raises_agenda_error(self):
        original = fetch.scrape_and_save

        def boom():
            raise RuntimeError("network is down")

        fetch.scrape_and_save = boom
        self.addCleanup(setattr, fetch, "scrape_and_save", original)

        with self.assertRaises(fetch.AgendaError):
            fetch.fetch_and_save()


class TestParse(TempAgenda):
    def setUp(self):
        super().setUp()
        # Keep the test output quiet, the individual tests set what they need.
        os.environ["NUMBER_OF_COLLES_TO_SHOW"] = "0"
        self.write_csv(HEADER + ROWS)
        fetch.fetch_and_save()

    def test_returns_the_next_colles_in_order(self):
        os.environ["NUMBER_OF_COLLES_TO_SHOW"] = "1"
        rows = parse.get_next_colles(datetime.datetime(2026, 9, 1))
        self.assertEqual(rows[0]["date"], "2026-09-24")
        self.assertEqual(len(rows), 1)

    def test_ignores_past_colles(self):
        os.environ["NUMBER_OF_COLLES_TO_SHOW"] = "1"
        rows = parse.get_next_colles(datetime.datetime(2026, 10, 1))
        self.assertEqual([row["date"] for row in rows], ["2026-10-06"])

    def test_returns_nothing_after_the_last_colle(self):
        os.environ["NUMBER_OF_COLLES_TO_SHOW"] = "1"
        self.assertEqual(parse.get_next_colles(datetime.datetime(2027, 1, 1)), [])

    def test_last_row_is_not_dropped(self):
        os.environ["NUMBER_OF_COLLES_TO_SHOW"] = "3"
        rows = parse.get_next_colles(datetime.datetime(2026, 9, 1))
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]["date"], "2026-10-06")

    def test_has_agenda(self):
        self.assertTrue(parse.has_agenda())

    def test_has_agenda_without_cache(self):
        os.remove(self.out)
        self.assertFalse(parse.has_agenda())

    def test_iso_and_legacy_dates_are_both_parsed(self):
        self.assertEqual(
            parse.parse_date_string("2026-09-24 17:00"),
            datetime.datetime(2026, 9, 24, 17, 0),
        )


class TestNotif(TempAgenda):
    def test_format_uses_the_configured_template(self):
        sent = []
        import notif

        original_format = notif.NTFY_FORMAT
        original_send = notif.send_ntfy_message
        notif.NTFY_FORMAT = "{matiere} {jour} {heure}-{fin} {salle}"
        notif.send_ntfy_message = lambda message, **headers: sent.append(message)
        self.addCleanup(setattr, notif, "NTFY_FORMAT", original_format)
        self.addCleanup(setattr, notif, "send_ntfy_message", original_send)

        notif.send_colle(
            {
                "matiere": "Anglais",
                "jour": "jeudi",
                "heure": "17:00",
                "fin": "18:00",
                "salle": "L037",
                "date": "2026-09-24",
                "colleur": "Mme Hatri",
            }
        )
        self.assertEqual(sent, ["Anglais jeudi 17:00-18:00 L037"])

    def test_unknown_field_is_reported(self):
        import notif

        original_format = notif.NTFY_FORMAT
        notif.NTFY_FORMAT = "{nope}"
        self.addCleanup(setattr, notif, "NTFY_FORMAT", original_format)

        with self.assertRaises(ValueError) as caught:
            notif.send_colle({"matiere": "Anglais"})
        self.assertIn("nope", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
