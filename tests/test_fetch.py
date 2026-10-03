"""Tests for reading the ecolle CSV export (fetch.py)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers import HEADER, ROWS, AppTestCase

import config
import fetch


class TestReadCsv(AppTestCase):
    """The CSV export is parsed into the normalised agenda."""

    def test_parses_the_expected_export(self):
        self.write_csv(HEADER + ROWS)
        rows = fetch.read_colles_csv(self.csv)

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            rows[0],
            {
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
            },
        )

    def test_rows_are_sorted_by_date(self):
        self.write_csv(
            HEADER
            + "2026-10-06,Mathématiques,M Jouve,mardi,L005,16:00,17:00\n"
            + "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00\n"
        )
        rows = fetch.read_colles_csv(self.csv)
        self.assertEqual([row["date"] for row in rows], ["2026-09-24", "2026-10-06"])

    def test_tolerates_bom_accents_case_and_extra_columns(self):
        self.write_csv(
            "\ufeffDate, Matiere ,COLLEUR,jour,Salle,Début,Fin,Note\n"
            "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00,rien\n"
        )
        rows = fetch.read_colles_csv(self.csv)
        self.assertEqual(rows[0]["matiere"], "Anglais")
        self.assertEqual(rows[0]["colleur"], "Mme Hatri")

    def test_tolerates_underscores_and_dashes_in_headers(self):
        self.write_csv(
            "Date,Matie_re,Col-leur,Jour,Salle,Début,Fin\n"
            "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00\n"
        )
        self.assertEqual(fetch.read_colles_csv(self.csv)[0]["matiere"], "Anglais")

    def test_tolerates_extra_spaces_around_values(self):
        self.write_csv(
            HEADER + "2026-09-24 , Anglais , Mme Hatri , jeudi , L037 , 17:00 , 18:00 \n"
        )
        row = fetch.read_colles_csv(self.csv)[0]
        self.assertEqual(row["matiere"], "Anglais")
        self.assertEqual(row["salle"], "L037")
        self.assertEqual(row["date_time"], "2026-09-24 17:00")

    def test_tolerates_other_date_and_time_layouts(self):
        self.write_csv(
            HEADER + "24/09/2026,Anglais,Mme Hatri,jeudi,L037,17h00,18:00\n"
        )
        row = fetch.read_colles_csv(self.csv)[0]
        self.assertEqual(row["date"], "2026-09-24")
        self.assertEqual(row["heure"], "17:00")

    def test_duplicate_columns_are_rejected(self):
        # The last duplicate would silently win, scheduling the wrong day.
        self.write_csv(
            "Date,Matière,Colleur,Jour,Salle,Début,Fin,Date\n"
            "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00,2027-01-01\n"
        )
        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.read_colles_csv(self.csv)
        self.assertIn("appears twice", str(caught.exception))

    def test_tolerates_crlf_line_endings(self):
        self.write_csv((HEADER + ROWS).replace("\n", "\r\n"))
        self.assertEqual(len(fetch.read_colles_csv(self.csv)), 3)

    def test_tolerates_quoted_fields_containing_commas(self):
        self.write_csv(
            HEADER + '2026-09-24,Anglais,"Mme Hatri, agrégée",jeudi,L037,17:00,18:00\n'
        )
        self.assertEqual(
            fetch.read_colles_csv(self.csv)[0]["colleur"], "Mme Hatri, agrégée"
        )

    def test_missing_optional_columns_are_fine(self):
        self.write_csv(
            "Date,Matière,Colleur,Salle,Début\n"
            "2026-09-24,Anglais,Mme Hatri,L037,17:00\n"
        )
        row = fetch.read_colles_csv(self.csv)[0]
        self.assertEqual(row["jour"], "")
        self.assertEqual(row["fin"], "")

    def test_skips_blank_lines_and_bad_rows(self):
        self.write_csv(
            HEADER
            + "\n"
            + "pas-une-date,Anglais,X,jeudi,L037,17:00,18:00\n"
            + "2026-10-07,Anglais,X,jeudi,L037,25:99,18:00\n"
            + "2026-10-08,Anglais,X,jeudi,L037,18:00,19:00\n"
        )
        rows = fetch.read_colles_csv(self.csv)
        self.assertEqual([row["date"] for row in rows], ["2026-10-08"])

    def test_keeps_every_row_of_a_large_file(self):
        body = "".join(
            f"2026-{month:02d}-{day:02d},Anglais,Mme Hatri,jeudi,L037,17:00,18:00\n"
            for month in range(1, 13)
            for day in range(1, 29)
        )
        self.write_csv(HEADER + body)
        self.assertEqual(len(fetch.read_colles_csv(self.csv)), 12 * 28)

    def test_duplicate_rows_are_kept(self):
        self.write_csv(
            HEADER
            + "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00\n"
            + "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00\n"
        )
        self.assertEqual(len(fetch.read_colles_csv(self.csv)), 2)


class TestReadCsvErrors(AppTestCase):
    """Malformed exports are reported clearly."""

    def assert_agenda_error(self, expected):
        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.read_colles_csv(self.csv)
        self.assertIn(expected, str(caught.exception))
        return str(caught.exception)

    def test_missing_required_column_is_reported(self):
        self.write_csv("Date,Matière,Colleur,Jour,Salle\n")
        message = self.assert_agenda_error("debut")
        self.assertIn("Date", message)  # reminds the expected headers

    def test_empty_file_is_reported(self):
        self.write_csv("")
        self.assert_agenda_error("is empty")

    def test_header_only_is_reported(self):
        self.write_csv(HEADER)
        self.assert_agenda_error("no usable row")

    def test_semicolon_separator_is_reported(self):
        self.write_csv(
            "Date;Matière;Colleur;Jour;Salle;Début;Fin\n"
            "2026-09-24;Anglais;Mme Hatri;jeudi;L037;17:00;18:00\n"
        )
        message = self.assert_agenda_error("missing column")
        self.assertIn("comma-separated", message)

    def test_tab_separator_is_reported(self):
        self.write_csv((HEADER + ROWS).replace(",", "\t"))
        self.assert_agenda_error("missing column")

    def test_directory_instead_of_file_is_reported(self):
        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.read_colles_csv(self.tmp.name)
        self.assertIn("is a directory", str(caught.exception))

    def test_unreadable_file_is_reported(self):
        self.write_csv(HEADER + ROWS)
        os.chmod(self.csv, 0o000)
        self.addCleanup(os.chmod, self.csv, 0o644)

        if os.access(self.csv, os.R_OK):  # running as root: chmod proves nothing
            self.skipTest("cannot make a file unreadable as root")

        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.read_colles_csv(self.csv)
        self.assertIn("cannot be read", str(caught.exception))

    def test_non_utf8_file_is_reported(self):
        with open(self.csv, "wb") as handle:
            handle.write(b"Date,Colleur\n2026-09-24,caf\xe9\n")
        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.read_colles_csv(self.csv)
        self.assertIn("UTF-8", str(caught.exception))

    def test_unwritable_output_is_reported(self):
        self.write_csv(HEADER + ROWS)
        self.set_env(AGENDA_CSV_PATH=os.path.join(self.tmp.name, "nope", "x", "a.csv"))
        os.makedirs(os.path.join(self.tmp.name, "nope"), exist_ok=True)
        os.chmod(os.path.join(self.tmp.name, "nope"), 0o500)
        self.addCleanup(os.chmod, os.path.join(self.tmp.name, "nope"), 0o755)

        if os.access(os.path.join(self.tmp.name, "nope"), os.W_OK):
            self.skipTest("cannot make a directory unwritable as root")

        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.save_agenda(fetch.read_colles_csv(self.csv))
        self.assertIn("could not be written", str(caught.exception))


class TestCsvConfiguration(AppTestCase):
    """Path settings are read when used, and blank means unset."""

    def test_blank_settings_fall_back_to_the_defaults(self):
        self.set_env(
            COLLES_CSV_PATH="", AGENDA_CSV_PATH="", NUMBER_OF_COLLES_TO_SHOW=""
        )
        self.assertEqual(config.csv_path(), config.DEFAULT_CSV_PATH)
        self.assertEqual(config.output_path(), config.DEFAULT_OUTPUT_PATH)
        self.assertEqual(config.number_of_colles_to_show(), 1)

    def test_values_are_stripped(self):
        self.set_env(COLLES_CSV_PATH="  /tmp/a.csv  ")
        self.assertEqual(config.csv_path(), "/tmp/a.csv")


class TestFetchAndSave(AppTestCase):
    """Choosing between the CSV export and the scraper fallback."""

    def test_csv_is_used_and_written_for_parse(self):
        self.write_csv(HEADER + ROWS)
        rows = fetch.fetch_and_save()

        self.assertEqual(len(rows), 3)
        self.assertTrue(os.path.isfile(self.out))
        self.assertEqual(len(self.read_agenda()), 3)

    def test_missing_csv_falls_back_to_the_scraper(self):
        with self.patched(fetch, "scrape_and_save", lambda: []) as _:
            self.assertEqual(fetch.fetch_and_save(), [])

    def test_disabled_scraping_never_calls_the_scraper(self):
        self.set_env(DISABLE_ECOLLE_FETCH="true")
        calls = []
        with self.patched(fetch, "scrape_and_save", lambda: calls.append(1) or []):
            with self.assertRaises(fetch.AgendaError) as caught:
                fetch.fetch_and_save()
        self.assertEqual(calls, [])
        self.assertIn("Scraping ecolle is disabled", str(caught.exception))

    def test_disabled_scraping_error_mentions_the_path(self):
        self.set_env(DISABLE_ECOLLE_FETCH="true")
        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.fetch_and_save()
        self.assertIn(self.csv, str(caught.exception))

    def test_csv_is_still_used_when_scraping_is_disabled(self):
        self.set_env(DISABLE_ECOLLE_FETCH="true")
        self.write_csv(HEADER + ROWS)
        self.assertEqual(len(fetch.fetch_and_save()), 3)


class TestMissingCsvMessages(AppTestCase):
    """The "file not found" message is actionable."""

    def test_message_lists_nearby_csv_files(self):
        self.write_csv(HEADER, path=os.path.join(self.tmp.name, "my-export.csv"))
        message = fetch.describe_missing_csv(self.csv)
        self.assertIn("my-export.csv", message)
        self.assertIn("COLLES_CSV_PATH", message)

    def test_message_mentions_a_missing_directory(self):
        message = fetch.describe_missing_csv(os.path.join(self.tmp.name, "n", "c.csv"))
        self.assertIn("does not exist", message)

    def test_message_says_when_no_csv_is_present(self):
        self.assertIn("no CSV file", fetch.describe_missing_csv(self.csv))

    def test_message_for_a_directory_lists_its_csv_files(self):
        directory = os.path.join(self.tmp.name, "input")
        os.makedirs(directory)
        self.write_csv(HEADER, path=os.path.join(directory, "colles.csv"))

        message = fetch.describe_missing_csv(directory)
        self.assertIn("is a directory, not a file", message)
        self.assertIn("colles.csv", message)

    def test_message_says_when_the_default_path_is_used(self):
        self.set_env(COLLES_CSV_PATH=None)
        self.assertIn("not set", fetch.describe_missing_csv(self.csv))


class TestScraperFallback(AppTestCase):
    """The legacy scraper produces rows shaped like the CSV ones."""

    HTML = """<table class="tableausimple">
    <tr><th>date</th><th>heure</th><th>matiere</th><th>colleur</th><th>prog</th><th>salle</th></tr>
    <tr><td>jeudi 24 septembre</td><td>17h00</td>
        <td style="background-color:#ff0000">Anglais</td><td>Mme Hatri</td>
        <td><a href="/p">prog</a><div class="popup">chap 1</div></td><td>L037</td></tr>
    <tr><td>mercredi 30 septembre</td><td>15h00</td><td>Physique</td><td>M Blain</td>
        <td></td><td>L124</td></tr>
    </table>"""

    def test_rows_match_the_csv_shape(self):
        rows = fetch.parse_agenda_to_rows(self.HTML)
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows[0]), set(fetch.OUTPUT_FIELDS))

    def test_date_time_is_filled_so_parse_can_sort(self):
        import datetime

        rows = fetch.parse_agenda_to_rows(self.HTML)
        when = fetch.dates.parse_row_datetime(rows[0])
        self.assertIsNotNone(when)
        self.assertEqual(when.year, datetime.datetime.now().year)
        self.assertNotEqual(when.year, 1900)

    def test_extracts_the_scraped_extras(self):
        row = fetch.parse_agenda_to_rows(self.HTML)[0]
        self.assertEqual(row["matiere"], "Anglais")
        self.assertEqual(row["salle"], "L037")
        self.assertEqual(row["couleur"], "ff0000")
        self.assertEqual(row["programme_links"], "/p")
        self.assertEqual(row["popup"], "chap 1")

    def test_odd_rows_are_skipped_not_crashing(self):
        rows = fetch.parse_agenda_to_rows(self.HTML + "<tr><td>only one cell</td></tr>")
        self.assertEqual(len(rows), 2)

    def test_table_without_rows_returns_nothing(self):
        self.assertEqual(fetch.parse_agenda_to_rows("<html></html>"), [])

    def test_scraping_without_base_url_is_an_agenda_error(self):
        self.set_env(BASE_URL=None)
        with self.assertRaises(fetch.AgendaError) as caught:
            fetch.scrape_and_save()
        self.assertIn("BASE_URL", str(caught.exception))


class TestFailedScrapeProtection(AppTestCase):
    """Regression: a scrape that finds nothing must not destroy the cache.

    Before v2.4.0 an agenda page without the expected table produced zero rows,
    which was written to the cache as a header-only file and reported as
    success: the previous good agenda was lost and the run exited 0.
    """

    HTML_NO_TABLE = "<html><body>maintenance</body></html>"

    def seed_cache(self):
        self.write_csv(HEADER + ROWS)
        fetch.fetch_and_save()
        with open(self.out, encoding="utf-8") as handle:
            return handle.read()

    def test_empty_scrape_raises_and_keeps_the_cache(self):
        before = self.seed_cache()
        os.remove(self.csv)
        self.set_env(BASE_URL="https://ecolle.example.com")

        with self.patched(fetch, "fetch_agenda", lambda session: self.HTML_NO_TABLE):
            with self.patched(fetch, "login", lambda *args, **kwargs: True):
                with self.assertRaises(fetch.AgendaError) as caught:
                    fetch.scrape_and_save()

        self.assertIn("no usable colle", str(caught.exception))
        with open(self.out, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), before, "the cached agenda was damaged")

    def test_a_table_without_usable_rows_raises(self):
        self.set_env(BASE_URL="https://ecolle.example.com")
        empty_table = '<table class="tableausimple"><tr><th>h</th></tr></table>'

        with self.patched(fetch, "fetch_agenda", lambda session: empty_table):
            with self.patched(fetch, "login", lambda *args, **kwargs: True):
                with self.assertRaises(fetch.AgendaError):
                    fetch.scrape_and_save()

    def test_a_successful_scrape_still_saves(self):
        self.set_env(BASE_URL="https://ecolle.example.com")
        with self.patched(fetch, "fetch_agenda", lambda session: self.HTML):
            with self.patched(fetch, "login", lambda *args, **kwargs: True):
                rows = fetch.scrape_and_save()
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(self.read_agenda()), 2)

    HTML = """<table class="tableausimple">
    <tr><th>d</th><th>h</th><th>m</th><th>c</th><th>p</th><th>s</th></tr>
    <tr><td>jeudi 24 septembre</td><td>17h00</td><td>Anglais</td><td>Mme Hatri</td>
        <td></td><td>L037</td></tr>
    <tr><td>mercredi 30 septembre</td><td>15h00</td><td>Physique</td><td>M Blain</td>
        <td></td><td>L124</td></tr>
    </table>"""


class TestCorruptCache(AppTestCase):
    """Regression: a damaged cache must not crash the run."""

    def test_non_utf8_cache_counts_as_unusable(self):
        with open(self.out, "wb") as handle:
            handle.write(b"date,heure\n2026-09-24,caf\xe9\n")
        self.assertFalse(parse_has_agenda())

    def test_empty_cache_counts_as_unusable(self):
        open(self.out, "w").close()
        self.assertFalse(parse_has_agenda())

    def test_unreadable_cache_counts_as_unusable(self):
        self.write_csv(HEADER + ROWS, path=self.out)
        os.chmod(self.out, 0o000)
        self.addCleanup(os.chmod, self.out, 0o644)
        if os.access(self.out, os.R_OK):
            self.skipTest("cannot make a file unreadable as root")
        self.assertFalse(parse_has_agenda())


def parse_has_agenda():
    import parse

    return parse.has_agenda()


if __name__ == "__main__":
    unittest.main()
