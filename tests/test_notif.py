"""Tests for the notification body (notif.py)."""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers import COLLE, AppTestCase

import config
import notif


class TestDefaultFormat(AppTestCase):
    def test_reads_like_a_sentence(self):
        self.assertEqual(
            notif.format_message(COLLE),
            "jeudi 24 septembre 17h00 L037 - Anglais (Mme Hatri)",
        )

    def test_without_an_end_time(self):
        self.assertEqual(
            notif.format_message(dict(COLLE, fin="")),
            "jeudi 24 septembre 17h00 L037 - Anglais (Mme Hatri)",
        )

    def test_the_configured_format_wins(self):
        self.set_env(NTFY_FORMAT="{matiere} {salle}")
        self.assertEqual(notif.format_message(COLLE), "Anglais L037")

    def test_a_blank_format_falls_back_to_the_default(self):
        self.set_env(NTFY_FORMAT="")
        self.assertEqual(notif.ntfy_format(), notif.DEFAULT_NTFY_FORMAT)


class TestDerivedFields(AppTestCase):
    def test_french_date_fields(self):
        values = notif.derived_fields(COLLE)
        self.assertEqual(values["date_courte"], "24 septembre")
        self.assertEqual(values["date_longue"], "jeudi 24 septembre")
        self.assertEqual(values["date_annee"], "24 septembre 2026")
        self.assertEqual(values["date_heure"], "24 septembre 17h00")

    def test_french_time_fields(self):
        values = notif.derived_fields(COLLE)
        self.assertEqual(values["heure_debut"], "17h00")
        self.assertEqual(values["heure_fin"], "17h00 - 18h00")

    def test_heure_fin_without_an_end_time(self):
        self.assertEqual(notif.derived_fields(dict(COLLE, fin=""))["heure_fin"], "17h00")

    def test_jour_comes_from_the_date_not_the_column(self):
        for jour in ("jeudi", "", "lundi", "DIMANCHE", "2026"):
            message = notif.format_message(
                dict(COLLE, jour=jour), "{jour} {date_courte}"
            )
            self.assertEqual(message, "jeudi 24 septembre", jour)

    def test_a_wrong_weekday_in_the_export_cannot_leak(self):
        # 2026-12-07 is a Monday, whatever the CSV claims.
        row = dict(COLLE, date="2026-12-07", date_time="2026-12-07 16:00",
                   jour="dimanche", heure="16:00")
        self.assertEqual(notif.format_message(row, "{jour}"), "lundi")

    def test_the_source_row_is_not_modified(self):
        original = dict(COLLE)
        notif.derived_fields(COLLE)
        self.assertEqual(COLLE, original)

    def test_missing_date_leaves_the_extras_empty(self):
        values = notif.derived_fields({"matiere": "Maths"})
        self.assertEqual(values["date_courte"], "")
        self.assertEqual(values["date_longue"], "")
        self.assertEqual(values["date_annee"], "")
        self.assertEqual(values["date_heure"], "")

    def test_legacy_french_row_gets_a_real_year(self):
        row = {
            "date": "jeudi 24 septembre",
            "heure": "17h00",
            "date_time": "",
            "matiere": "Anglais",
            "colleur": "Mme Hatri",
            "salle": "L037",
            "jour": "jeudi",
            "fin": "",
        }
        values = notif.derived_fields(row)
        self.assertNotIn("1900", values["date_annee"])
        self.assertIn(str(datetime.datetime.now().year), values["date_annee"])


class TestTemplates(AppTestCase):
    def test_every_derived_field_is_usable(self):
        message = notif.format_message(
            COLLE,
            "{jour}|{date_courte}|{date_longue}|{date_annee}|{date_heure}"
            "|{heure_debut}|{heure_fin}|{matiere}|{colleur}|{salle}",
        )
        self.assertEqual(
            message,
            "jeudi|24 septembre|jeudi 24 septembre|24 septembre 2026"
            "|24 septembre 17h00|17h00|17h00 - 18h00|Anglais|Mme Hatri|L037",
        )

    def test_raw_fields_are_still_available(self):
        self.assertEqual(
            notif.format_message(COLLE, "{date} {heure} {fin} {date_time}"),
            "2026-09-24 17:00 18:00 2026-09-24 17:00",
        )

    def test_fallback_syntax_when_a_field_is_empty(self):
        self.assertEqual(
            notif.format_message(COLLE, "{matiere} {fin|fin inconnue}"),
            "Anglais 18:00",
        )
        self.assertEqual(
            notif.format_message(dict(COLLE, fin=""), "{matiere} {fin|fin inconnue}"),
            "Anglais fin inconnue",
        )

    def test_fallback_syntax_reports_unknown_fields(self):
        with self.assertRaises(ValueError) as caught:
            notif.format_message(COLLE, "{nope|x}")
        self.assertIn("nope", str(caught.exception))

    def test_unknown_field_lists_the_available_ones(self):
        with self.assertRaises(ValueError) as caught:
            notif.format_message(COLLE, "{nope}")
        message = str(caught.exception)
        self.assertIn("nope", message)
        self.assertIn("date_courte", message)

    def test_unbalanced_braces_are_reported(self):
        with self.assertRaises(ValueError) as caught:
            notif.format_message(COLLE, "{matiere")
        self.assertIn("NTFY_FORMAT", str(caught.exception))

    def test_literal_text_and_braces_are_kept(self):
        self.assertEqual(
            notif.format_message(COLLE, "Colle de {matiere} !"), "Colle de Anglais !"
        )

    def test_whitespace_and_punctuation_are_tidied(self):
        self.assertEqual(notif.format_message(COLLE, "  {matiere}   {salle}  "),
                         "Anglais L037")
        self.assertEqual(notif.format_message(COLLE, "{matiere} , {salle}"),
                         "Anglais, L037")
        self.assertEqual(notif.format_message(COLLE, "({matiere} )"), "(Anglais)")

    def test_empty_field_does_not_leave_a_dangling_separator(self):
        row = dict(COLLE, colleur="")
        message = notif.format_message(row, "{matiere} - {colleur} - {salle}")
        self.assertNotIn("- -", message)


class TestSendColle(AppTestCase):
    def test_sends_the_formatted_message_with_the_title(self):
        sent = []
        self.set_env(NTFY_TOPIC="topic", NTFY_TITLE="Mes colles")
        with self.patched(
            notif,
            "send_ntfy_message",
            lambda message, **headers: sent.append((message, headers)),
        ):
            notif.send_colle(COLLE)
        self.assertEqual(
            sent, [("jeudi 24 septembre 17h00 L037 - Anglais (Mme Hatri)",
                    {"Title": "Mes colles"})]
        )

    def test_missing_topic_is_reported(self):
        self.set_env(NTFY_TOPIC=None)
        with self.assertRaises(ValueError) as caught:
            notif.send_colle(COLLE)
        self.assertIn("NTFY_TOPIC", str(caught.exception))

    def test_blank_topic_is_reported(self):
        self.set_env(NTFY_TOPIC="   ")
        with self.assertRaises(ValueError):
            notif.send_colle(COLLE)


class TestVerifySetting(AppTestCase):
    def test_default_verifies_certificates(self):
        self.set_env(SELF_SIGNED_CERTIFICATE=None, ROOT_CA_PATH=None)
        self.assertIs(config.verify_setting(), True)

    def test_self_signed_disables_verification(self):
        self.set_env(SELF_SIGNED_CERTIFICATE="true", ROOT_CA_PATH=None)
        self.assertIs(config.verify_setting(), False)

    def test_truthy_spellings_are_accepted(self):
        for value in ("true", "TRUE", "1", "yes", "on"):
            self.set_env(SELF_SIGNED_CERTIFICATE=value, ROOT_CA_PATH=None)
            self.assertIs(config.verify_setting(), False, value)

    def test_falsy_spellings_keep_verification(self):
        for value in ("false", "0", "no", "off", "", "nope"):
            self.set_env(SELF_SIGNED_CERTIFICATE=value, ROOT_CA_PATH=None)
            self.assertIs(config.verify_setting(), True, value)

    def test_root_ca_takes_precedence(self):
        self.set_env(ROOT_CA_PATH="/tmp/ca.pem", SELF_SIGNED_CERTIFICATE=None)
        self.assertEqual(config.verify_setting(), "/tmp/ca.pem")


class TestNtfyServer(AppTestCase):
    def test_default_server(self):
        self.set_env(NTFY_SERVER=None)
        self.assertEqual(config.ntfy_server(), "https://ntfy.sh")

    def test_trailing_slash_is_removed(self):
        self.set_env(NTFY_SERVER="https://ntfy.example.org/")
        self.assertEqual(config.ntfy_server(), "https://ntfy.example.org")

    def test_topic_is_stripped(self):
        self.set_env(NTFY_TOPIC="  my topic  ")
        self.assertEqual(config.ntfy_topic(), "my topic")


if __name__ == "__main__":
    unittest.main()
