"""Tests del pipeline de extractores (capa de dominio) y del store de señales."""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.extractors import load_extractors           # noqa: E402
from omega.reasoning import store, signals             # noqa: E402
from omega.analyze.momentum import _terms               # noqa: E402


class TokenizerNoiseTest(unittest.TestCase):
    """El ruido observado el 2026-07-09 no debe volver: contracciones y palabras de formato
    NO son temas ('i'm' llegó a #2 de demanda con 9.1M vistas; 'daily' casi gana decide)."""

    def test_contractions_are_not_terms(self):
        terms = _terms("Top Stocks I'm Buying Now — Don't Miss These")
        self.assertNotIn("i'm", terms)
        self.assertNotIn("don't", terms)
        self.assertNotIn("i'm buying", terms)   # el bigrama con contracción tampoco
        self.assertIn("stocks", terms)           # el contenido real sí queda
        self.assertIn("buying", terms)

    def test_typographic_apostrophe_normalized(self):
        # "don’t" (apóstrofe U+2019) no debe producir el token falso "don"
        terms = _terms("Don’t Buy This ETF — I’m Selling")
        self.assertNotIn("don", terms)
        self.assertNotIn("don't", terms)
        self.assertNotIn("i'm", terms)
        self.assertIn("etf", terms)
        self.assertIn("selling", terms)

    def test_entity_possessives_survive(self):
        # los posesivos de entidad son señal real, no ruido
        terms = _terms("Warren Buffett's Warning About the Fed's Rate Cuts")
        self.assertIn("buffett's", terms)
        self.assertIn("fed's", terms)
        self.assertIn("warren buffett's", terms)

    def test_format_words_are_not_terms(self):
        terms = _terms("Daily Live Stock Market News Update")
        for noise in ("daily", "live", "news", "update"):
            self.assertNotIn(noise, terms)
        self.assertIn("stock market", terms)


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
