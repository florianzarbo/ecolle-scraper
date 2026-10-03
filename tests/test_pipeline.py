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

    def test_csv_is_used_even_when_scraping_is_disabled(self):
        os.environ["DISABLE_ECOLLE_FETCH"] = "true"
        self.write_csv(HEADER + ROWS)
        self.assertEqual(len(fetch.fetch_and_save()), 3)

    def test_disabled_scraping_never_calls_the_scraper(self):
        os.environ["DISABLE_ECOLLE_FETCH"] = "true"
        called = []
        original = fetch.scrape_and_save
        fetch.scrape_and_save = lambda: called.append(True) or []
        self.addCleanup(setattr, fetch, "scrape_and_save", original)

        with self.assertRaises(fetch.AgendaError):
            fetch.fetch_and_save()
        self.assertEqual(called, [])

    def test_disabled_scraping_error_mentions_the_path(self):
        os.environ["DISABLE_ECOLLE_FETCH"] = "true"
        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.fetch_and_save()
        message = str(caught.exception)
        self.assertIn(self.csv, message)
        self.assertIn("Scraping ecolle is disabled", message)

    def test_deprecated_misspelling_still_works(self):
        os.environ["DISABLE_ECALLE_FETCH"] = "true"
        self.assertTrue(fetch.scraping_disabled())

    def test_canonical_name_is_the_ecolle_spelling(self):
        self.assertEqual(fetch.DISABLE_FETCH_NAMES[0], "DISABLE_ECOLLE_FETCH")

    def test_scraping_enabled_by_default(self):
        for name in fetch.DISABLE_FETCH_NAMES:
            os.environ.pop(name, None)
        self.assertFalse(fetch.scraping_disabled())

    def test_disable_names_and_truthy_values(self):
        for name in fetch.DISABLE_FETCH_NAMES:
            for value in ("true", "TRUE", "1", "yes", "on"):
                os.environ[name] = value
                self.assertTrue(fetch.scraping_disabled(), (name, value))
                os.environ.pop(name)

        for value in ("false", "0", "no", "", "off"):
            os.environ["DISABLE_ECOLLE_FETCH"] = value
            self.assertFalse(fetch.scraping_disabled(), value)


class TestMissingCsvMessages(TempAgenda):
    def test_message_lists_nearby_csv_files(self):
        with open(os.path.join(self.tmp.name, "my-export.csv"), "w") as handle:
            handle.write(HEADER)

        message = fetch.describe_missing_csv(self.csv)
        self.assertIn("my-export.csv", message)
        self.assertIn("COLLES_CSV_PATH", message)

    def test_message_mentions_a_missing_directory(self):
        missing = os.path.join(self.tmp.name, "nope", "colles.csv")
        message = fetch.describe_missing_csv(missing)
        self.assertIn("does not exist", message)

    def test_message_says_when_no_csv_is_present(self):
        message = fetch.describe_missing_csv(self.csv)
        self.assertIn("no CSV file", message)

    def test_message_for_a_directory_lists_its_csv_files(self):
        directory = os.path.join(self.tmp.name, "input")
        os.makedirs(directory)
        with open(os.path.join(directory, "colles.csv"), "w") as handle:
            handle.write(HEADER)

        message = fetch.describe_missing_csv(directory)
        self.assertIn("is a directory, not a file", message)
        self.assertIn("colles.csv", message)
        self.assertNotIn("does not exist", message)

    def test_unreadable_file_is_reported_clearly(self):
        self.write_csv(HEADER + ROWS)
        os.chmod(self.csv, 0o000)
        self.addCleanup(os.chmod, self.csv, 0o644)

        if os.access(self.csv, os.R_OK):  # running as root, chmod proves nothing
            self.skipTest("cannot make a file unreadable as root")

        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.read_colles_csv(self.csv)
        self.assertIn("cannot be read", str(caught.exception))

    def test_directory_instead_of_file_is_reported(self):
        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.read_colles_csv(self.tmp.name)
        self.assertIn("is a directory", str(caught.exception))


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


COLLE = {
    "date": "2026-09-24",
    "heure": "17:00",
    "date_time": "2026-09-24 17:00",
    "matiere": "Anglais",
    "colleur": "Mme Hatri",
    "salle": "L037",
    "jour": "jeudi",
    "fin": "18:00",
    "couleur": "",
    "programme_links": "",
    "popup": "",
}


class TestMessageFormat(unittest.TestCase):
    """The notification body format and its derived fields."""

    def setUp(self):
        import notif

        self.notif = notif

    def test_default_format_reads_like_a_french_sentence(self):
        message = self.notif.format_message(COLLE)
        self.assertEqual(
            message, "jeudi 24 septembre 17h00 L037 - Anglais (Mme Hatri)"
        )

    def test_default_without_an_end_time(self):
        message = self.notif.format_message(dict(COLLE, fin=""))
        self.assertEqual(message, "jeudi 24 septembre 17h00 L037 - Anglais (Mme Hatri)")

    def test_jour_is_derived_from_the_date_not_the_csv_column(self):
        # A wrong or missing "Jour" column must not change the output.
        for jour in ("jeudi", "", "lundi", "2026"):
            message = self.notif.format_message(
                dict(COLLE, jour=jour), "{jour} {date_courte}"
            )
            self.assertEqual(message, "jeudi 24 septembre")

    def test_french_date_fields(self):
        derived = self.notif.derived_fields(COLLE)
        self.assertEqual(derived["date_courte"], "24 septembre")
        self.assertEqual(derived["date_longue"], "jeudi 24 septembre")
        self.assertEqual(derived["date_annee"], "24 septembre 2026")
        self.assertEqual(derived["date_heure"], "24 septembre 17h00")

    def test_french_time_fields(self):
        derived = self.notif.derived_fields(COLLE)
        self.assertEqual(derived["heure_debut"], "17h00")
        self.assertEqual(derived["heure_fin"], "17h00 - 18h00")
        self.assertEqual(derived["heure_fin"], "17h00 - 18h00")

    def test_every_month_has_a_french_name(self):
        expected = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre",
        ]
        for month, name in enumerate(expected, start=1):
            message = self.notif.format_message(
                {**COLLE, "date": f"2027-{month:02d}-16",
                 "date_time": f"2027-{month:02d}-16 17:00"},
                "{date_annee}",
            )
            self.assertEqual(message, f"16 {name} 2027")

    def test_the_day_name_matches_the_real_weekday(self):
        # 2027-01-16 is a Saturday, whatever the CSV says.
        message = self.notif.format_message(
            {**COLLE, "date": "2027-01-16", "date_time": "2027-01-16 15:00"},
            "{jour} {date_longue}",
        )
        self.assertEqual(message, "samedi samedi 16 janvier")

    def test_no_date_degrades_gracefully(self):
        message = self.notif.format_message(
            {"matiere": "Maths"}, "{jour} {date_courte} {heure_debut} {matiere}"
        )
        self.assertEqual(message, "Maths")

    def test_fallback_syntax_is_used_when_a_field_is_empty(self):
        template = "{matiere} {fin|fin inconnue} {date_courte}"
        self.assertEqual(
            self.notif.format_message(COLLE, template),
            "Anglais 18:00 24 septembre",
        )
        self.assertEqual(
            self.notif.format_message(dict(COLLE, fin=""), template),
            "Anglais fin inconnue 24 septembre",
        )

    def test_fallback_syntax_reports_unknown_fields(self):
        with self.assertRaises(ValueError) as caught:
            self.notif.format_message(COLLE, "{nope|x}")
        self.assertIn("nope", str(caught.exception))

    def test_technical_fields_still_available(self):
        message = self.notif.format_message(
            COLLE, "{matiere} {date} {heure} {salle} {colleur}"
        )
        self.assertEqual(message, "Anglais 2026-09-24 17:00 L037 Mme Hatri")

    def test_previous_default_template_still_works(self):
        message = self.notif.format_message(
            COLLE, "{jour} {date} {heure_fin} - {matiere} en {salle} ({colleur})"
        )
        self.assertEqual(
            message, "jeudi 2026-09-24 17h00 - 18h00 - Anglais en L037 (Mme Hatri)"
        )

    def test_whitespace_is_collapsed(self):
        message = self.notif.format_message(COLLE, "  {matiere}   {salle}  ")
        self.assertEqual(message, "Anglais L037")

    def test_unbalanced_braces_are_reported(self):
        with self.assertRaises(ValueError):
            self.notif.format_message(COLLE, "{matiere")


if __name__ == "__main__":
    unittest.main()
