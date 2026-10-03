"""Shared helpers for the test suite.

Each test gets its own temporary directory and a clean environment, so the test
order cannot influence the results: every setting is read through
:mod:`config`, which reads the environment when a value is needed.
"""

import contextlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402

HEADER = "Date,Matière,Colleur,Jour,Salle,Début,Fin\n"

ROWS = (
    "2026-09-24,Anglais,Mme Hatri,jeudi,L037,17:00,18:00\n"
    "2026-09-30,Physique,M Blain,mercredi,L124,15:00,16:00\n"
    "2026-10-06,Mathématiques,M Jouve,mardi,L005,16:00,17:00\n"
)

#: A complete agenda row, as produced by fetch.py.
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

#: Environment variables the application reads. Cleared before each test.
ALL_SETTINGS = (
    "COLLES_CSV_PATH",
    "AGENDA_CSV_PATH",
    "COLLES_USERNAME",
    "COLLES_PASSWORD",
    "NUMBER_OF_COLLES_TO_SHOW",
    "NTFY_TOPIC",
    "NTFY_TITLE",
    "NTFY_SERVER",
    "NTFY_FORMAT",
    "BASE_URL",
    "SELF_SIGNED_CERTIFICATE",
    "ROOT_CA_PATH",
) + config.DISABLE_FETCH_NAMES


class AppTestCase(unittest.TestCase):
    """Base class with a temporary directory and an isolated environment."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.csv = os.path.join(self.tmp.name, "colles.csv")
        self.out = os.path.join(self.tmp.name, "agenda.csv")
        self.set_env(COLLES_CSV_PATH=self.csv, AGENDA_CSV_PATH=self.out)

    def set_env(self, **values):
        """Set environment values, restoring the previous state afterwards."""
        for name, value in values.items():
            self._remember(name)
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def _remember(self, name):
        key = f"_saved_env_{name}"
        if not hasattr(self, key):
            setattr(self, key, os.environ.get(name))
            self.addCleanup(self._restore, name)

    def _restore(self, name):
        saved = getattr(self, f"_saved_env_{name}")
        if saved is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = saved

    @contextlib.contextmanager
    def patched(self, module, attribute, value):
        """Temporarily replace an attribute on a module."""
        original = getattr(module, attribute)
        setattr(module, attribute, value)
        try:
            yield
        finally:
            setattr(module, attribute, original)

    def write_csv(self, text, path=None):
        """Write a CSV file and return its path."""
        path = path or self.csv
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def read_agenda(self):
        """Return the normalised agenda as a list of rows."""
        import csv

        with open(self.out, newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
