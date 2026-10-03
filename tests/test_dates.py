"""Tests for the French date and time handling (dates.py)."""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dates

SEPTEMBER_2026 = datetime.datetime(2026, 9, 1)


class TestParseDate(unittest.TestCase):
    def test_iso_date(self):
        self.assertEqual(dates.parse_date("2026-09-24"), datetime.date(2026, 9, 24))

    def test_tolerated_layouts(self):
        for value in ("24/09/2026", "24-09-2026", "24.09.2026"):
            self.assertEqual(
                dates.parse_date(value), datetime.date(2026, 9, 24), value
            )

    def test_surrounding_spaces_are_ignored(self):
        self.assertEqual(dates.parse_date("  2026-09-24 "), datetime.date(2026, 9, 24))

    def test_junk_is_rejected(self):
        for value in ("", "nope", "2026-13-45", "2026-02-30", None):
            with self.assertRaises(ValueError, msg=value):
                dates.parse_date(value)


class TestParseTime(unittest.TestCase):
    def test_iso_time(self):
        self.assertEqual(dates.parse_time("17:00"), datetime.time(17, 0))

    def test_tolerated_layouts(self):
        for value in ("17:00:00", "17h00", "17h"):
            self.assertEqual(dates.parse_time(value), datetime.time(17, 0), value)

    def test_junk_is_rejected(self):
        for value in ("", "25:99", "nope", None):
            with self.assertRaises(ValueError, msg=value):
                dates.parse_time(value)


class TestInferYear(unittest.TestCase):
    """School years run from September to July."""

    def test_autumn_seen_in_autumn_is_the_same_year(self):
        self.assertEqual(dates.infer_year(9, SEPTEMBER_2026), 2026)

    def test_spring_seen_in_autumn_is_the_next_year(self):
        self.assertEqual(dates.infer_year(1, SEPTEMBER_2026), 2027)
        self.assertEqual(dates.infer_year(7, SEPTEMBER_2026), 2027)

    def test_spring_seen_in_spring_is_the_same_year(self):
        march = datetime.datetime(2026, 3, 1)
        self.assertEqual(dates.infer_year(1, march), 2026)
        self.assertEqual(dates.infer_year(6, march), 2026)


class TestParseFrenchDatetime(unittest.TestCase):
    """The legacy scraped format has no year: it must not become 1900."""

    def test_with_day_name(self):
        self.assertEqual(
            dates.parse_datetime("jeudi 24 septembre 17h00", SEPTEMBER_2026),
            datetime.datetime(2026, 9, 24, 17, 0),
        )

    def test_without_day_name(self):
        self.assertEqual(
            dates.parse_datetime("24 septembre 17h00", SEPTEMBER_2026),
            datetime.datetime(2026, 9, 24, 17, 0),
        )

    def test_with_a_colon_time(self):
        self.assertEqual(
            dates.parse_datetime("jeudi 24 septembre 17:00", SEPTEMBER_2026),
            datetime.datetime(2026, 9, 24, 17, 0),
        )

    def test_january_seen_in_october_gets_the_next_year(self):
        october = datetime.datetime(2026, 10, 1)
        self.assertEqual(
            dates.parse_datetime("lundi 5 janvier 15h00", october),
            datetime.datetime(2027, 1, 5, 15, 0),
        )

    def test_accented_and_unaccented_months(self):
        for name in ("février", "fevrier"):
            self.assertEqual(
                dates.parse_datetime(f"lundi 2 {name} 15h00", SEPTEMBER_2026),
                datetime.datetime(2027, 2, 2, 15, 0),
                name,
            )

    def test_junk_is_rejected(self):
        for value in ("nope", "jeudi 24 blabla 17h00", "jeudi septembre 17h00", ""):
            with self.assertRaises(ValueError, msg=value):
                dates.parse_datetime(value, SEPTEMBER_2026)


class TestParseDatetime(unittest.TestCase):
    def test_normalised_form(self):
        self.assertEqual(
            dates.parse_datetime("2026-09-24 17:00"),
            datetime.datetime(2026, 9, 24, 17, 0),
        )

    def test_iso_t_separator_and_trailing_z(self):
        self.assertEqual(
            dates.parse_datetime("2026-09-24T17:00"),
            datetime.datetime(2026, 9, 24, 17, 0),
        )
        self.assertEqual(
            dates.parse_datetime("2026-09-24T17:00Z"),
            datetime.datetime(2026, 9, 24, 17, 0),
        )

    def test_date_without_time(self):
        self.assertEqual(
            dates.parse_datetime("2026-09-24"), datetime.datetime(2026, 9, 24, 0, 0)
        )

    def test_french_layout_with_time(self):
        self.assertEqual(
            dates.parse_datetime("24/09/2026 17:00"),
            datetime.datetime(2026, 9, 24, 17, 0),
        )

    def test_falls_back_to_the_french_text_format(self):
        self.assertEqual(
            dates.parse_datetime("jeudi 24 septembre 17h00", SEPTEMBER_2026),
            datetime.datetime(2026, 9, 24, 17, 0),
        )

    def test_empty_is_rejected(self):
        with self.assertRaises(ValueError):
            dates.parse_datetime("")


class TestParseRowDatetime(unittest.TestCase):
    def test_prefers_date_time(self):
        row = {"date_time": "2026-09-24 17:00", "date": "1999-01-01", "heure": "00:00"}
        self.assertEqual(
            dates.parse_row_datetime(row), datetime.datetime(2026, 9, 24, 17, 0)
        )

    def test_falls_back_to_date_and_heure(self):
        row = {"date_time": "", "date": "jeudi 24 septembre", "heure": "17h00"}
        self.assertEqual(
            dates.parse_row_datetime(row, SEPTEMBER_2026),
            datetime.datetime(2026, 9, 24, 17, 0),
        )

    def test_date_without_time_is_midnight(self):
        row = {"date_time": "", "date": "2026-09-24", "heure": ""}
        self.assertEqual(
            dates.parse_row_datetime(row), datetime.datetime(2026, 9, 24, 0, 0)
        )

    def test_unusable_rows_return_none(self):
        for row in ({}, {"date_time": "", "date": "", "heure": ""},
                    {"date_time": "nope"}, {"date": "nope"}):
            self.assertIsNone(dates.parse_row_datetime(row), row)


class TestFormatting(unittest.TestCase):
    def test_french_date(self):
        day = datetime.date(2027, 1, 16)
        self.assertEqual(dates.french_date(day), "16 janvier")
        self.assertEqual(dates.french_date(day, with_year=True), "16 janvier 2027")

    def test_every_month_has_a_name(self):
        expected = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre",
        ]
        for month, name in enumerate(expected, start=1):
            self.assertEqual(dates.french_date(datetime.date(2027, month, 16)),
                             f"16 {name}")

    def test_french_weekday(self):
        self.assertEqual(dates.french_weekday(datetime.date(2027, 1, 16)), "samedi")

    def test_every_weekday_has_a_name(self):
        expected = [
            "lundi", "mardi", "mercredi", "jeudi",
            "vendredi", "samedi", "dimanche",
        ]
        start = datetime.date(2027, 1, 11)  # a Monday
        for offset, name in enumerate(expected):
            self.assertEqual(
                dates.french_weekday(start + datetime.timedelta(days=offset)), name
            )

    def test_french_time(self):
        self.assertEqual(dates.french_time("15:00"), "15h00")
        self.assertEqual(dates.french_time(datetime.time(9, 5)), "9h05")
        self.assertEqual(dates.french_time(""), "")
        self.assertEqual(dates.french_time(None), "")

    def test_day_names_match_the_real_weekday(self):
        # Spot-check against dates whose weekday is well known.
        self.assertEqual(dates.french_weekday(datetime.date(2026, 9, 24)), "jeudi")
        self.assertEqual(dates.french_weekday(datetime.date(2026, 10, 6)), "mardi")
        self.assertEqual(dates.french_weekday(datetime.date(2027, 3, 24)), "mercredi")


class TestLocaleIndependence(unittest.TestCase):
    """French output must not depend on the host locale."""

    def test_output_does_not_use_the_locale(self):
        import locale

        for name in ("C", "POSIX", "en_US.UTF-8"):
            try:
                locale.setlocale(locale.LC_ALL, name)
            except locale.Error:
                continue
            self.assertEqual(
                dates.french_date(datetime.date(2027, 1, 16)), "16 janvier", name
            )
        locale.setlocale(locale.LC_ALL, "")


if __name__ == "__main__":
    unittest.main()
