"""Tests del pipeline de extractores (capa de dominio) y del store de señales."""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.extractors import load_extractors           # noqa: E402
from omega.reasoning import store, signals             # noqa: E402


class ExtractorsTest(unittest.TestCase):
    def test_registry_auto_discovers_plugins(self):
        names = {e.name for e in load_extractors()}
        self.assertIn("theme", names)
        self.assertIn("language", names)
        self.assertGreaterEqual(len(names), 3)

    def test_extractors_emit_generic_signals(self):
        asset = {"title": "How to learn AI fast", "summary": "a guide for programmers"}
        produced = {}
        for e in load_extractors():
            for s in e.extract(asset):
                produced[s["name"]] = s
        self.assertIn("language", produced)
        self.assertEqual(produced["language"]["value"], "en")
        self.assertIn("title_length", produced)
        self.assertEqual(produced["title_length"]["value_num"], float(len(asset["title"])))

    def test_signal_store_is_idempotent(self):
        con = store.connect(":memory:")
        signals.init(con)
        kw = dict(domain="content", asset_ref="a1", name="theme", value="ai", extractor="theme")
        self.assertEqual(signals.add_signal(con, **kw), 1)   # nueva
        self.assertEqual(signals.add_signal(con, **kw), 0)   # duplicada -> ignorada
        self.assertEqual(signals.count_total(con), 1)
        con.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
