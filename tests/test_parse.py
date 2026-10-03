"""Tests for selecting the next colles (parse.py)."""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers import HEADER, ROWS, AppTestCase

import config
import fetch
import parse


class TestAgendaFile(AppTestCase):
    def test_missing_agenda_is_reported(self):
        with self.assertRaises(FileNotFoundError) as caught:
            parse.load_rows()
        self.assertIn(self.out, str(caught.exception))

    def test_has_agenda_is_false_without_a_file(self):
        self.assertFalse(parse.has_agenda())

    def test_has_agenda_is_true_after_a_fetch(self):
        self.write_csv(HEADER + ROWS)
        fetch.fetch_and_save()
        self.assertTrue(parse.has_agenda())

    def test_has_agenda_is_false_for_an_empty_file(self):
        open(self.out, "w").close()
        self.assertFalse(parse.has_agenda())

    def test_agenda_path_follows_the_setting(self):
        self.set_env(AGENDA_CSV_PATH="/tmp/custom.csv")
        self.assertEqual(parse.agenda_csv_path(), "/tmp/custom.csv")


class TestGetNextColles(AppTestCase):
    def setUp(self):
        super().setUp()
        self.write_csv(HEADER + ROWS)
        fetch.fetch_and_save()

    def test_returns_the_next_colle(self):
        rows = parse.get_next_colles(datetime.datetime(2026, 9, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], "2026-09-24")

    def test_returns_them_soonest_first(self):
        self.set_env(NUMBER_OF_COLLES_TO_SHOW="3")
        rows = parse.get_next_colles(datetime.datetime(2026, 9, 1))
        self.assertEqual(
            [row["date"] for row in rows],
            ["2026-09-24", "2026-09-30", "2026-10-06"],
        )

    def test_the_last_row_is_not_dropped(self):
        self.set_env(NUMBER_OF_COLLES_TO_SHOW="3")
        rows = parse.get_next_colles(datetime.datetime(2026, 9, 1))
        self.assertEqual(rows[-1]["date"], "2026-10-06")

    def test_ignores_past_colles(self):
        rows = parse.get_next_colles(datetime.datetime(2026, 10, 1))
        self.assertEqual([row["date"] for row in rows], ["2026-10-06"])

    def test_returns_nothing_after_the_last_colle(self):
        self.assertEqual(parse.get_next_colles(datetime.datetime(2027, 1, 1)), [])

    def test_a_colle_starting_right_now_is_not_announced(self):
        # 2026-09-24 17:00 exactly: it has started, so it is skipped.
        rows = parse.get_next_colles(datetime.datetime(2026, 9, 24, 17, 0))
        self.assertEqual([row["date"] for row in rows], ["2026-09-30"])

    def test_a_colle_later_today_is_announced(self):
        rows = parse.get_next_colles(datetime.datetime(2026, 9, 24, 16, 59))
        self.assertEqual([row["date"] for row in rows], ["2026-09-24"])

    def test_ask_for_more_than_there_are(self):
        self.set_env(NUMBER_OF_COLLES_TO_SHOW="100")
        rows = parse.get_next_colles(datetime.datetime(2026, 9, 1))
        self.assertEqual(len(rows), 3)

    def test_bad_number_of_colles_is_reported(self):
        self.set_env(NUMBER_OF_COLLES_TO_SHOW="abc")
        with self.assertRaises(ValueError) as caught:
            parse.get_next_colles(datetime.datetime(2026, 9, 1))
        self.assertIn("NUMBER_OF_COLLES_TO_SHOW", str(caught.exception))

    def test_zero_colles_is_reported_rather_than_sending_nothing(self):
        self.set_env(NUMBER_OF_COLLES_TO_SHOW="0")
        with self.assertRaises(ValueError) as caught:
            parse.get_next_colles(datetime.datetime(2026, 9, 1))
        self.assertIn("at least 1", str(caught.exception))

    def test_a_row_sorting_before_the_current_year_still_works(self):
        rows = parse.get_next_colles(datetime.datetime(2025, 1, 1))
        self.assertEqual(rows[0]["date"], "2026-09-24")


class TestMixedSources(AppTestCase):
    """A cached agenda and a scraper agenda are both readable."""

    def load_agenda(self, text):
        """Write an agenda file directly and return the selected rows."""
        with open(self.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        return parse.get_next_colles(datetime.datetime(2026, 9, 1))

    def test_legacy_rows_without_date_time_are_understood(self):
        rows = self.load_agenda(
            "date,heure,matiere,colleur,salle,jour,fin,couleur,programme_links,popup\n"
            "jeudi 24 septembre,17h00,Anglais,Mme Hatri,L037,jeudi,,,,\n"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["matiere"], "Anglais")

    def test_unreadable_rows_are_skipped(self):
        rows = self.load_agenda(
            "date,heure,matiere,colleur,salle,jour,fin,couleur,programme_links,popup\n"
            "nope,,Anglais,Mme Hatri,L037,,,,\n"
            "2026-10-06,16:00,Maths,M Jouve,L005,,,,\n"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["matiere"], "Maths")


if __name__ == "__main__":
    unittest.main()
