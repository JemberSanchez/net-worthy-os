"""Tests de la integración de DEMANDA (YouTube) en el flujo de decisión.

No llaman a la red: monkeypatch de la fuente YouTube. Validan: agregación por vistas, dedupe
entre queries, round-trip del cache en SQLite, tolerancia a cache vacío, y que la feature
'demand' entra en el score del kernel (una demanda alta gana a una baja, todo lo demás igual).
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.analyze import demand  # noqa: E402
from omega.reasoning import decision_engine, hypotheses, store  # noqa: E402


def _video(vid, title, views):
    return {"video_id": vid, "title": title, "views": views, "channel": "c",
            "published_at": "", "likes": 0, "comments": 0, "url": f"https://youtu.be/{vid}"}


class ThemeDemandTest(unittest.TestCase):
    def test_aggregates_views_per_term_and_filters_singletons(self):
        videos = [
            _video("a", "Bitcoin crash explained", 100),
            _video("b", "Bitcoin rally incoming", 300),   # 'bitcoin' en 2 videos -> cuenta
            _video("c", "Gold is boring", 50),            # 'gold' en 1 -> se filtra (min_videos=2)
        ]
        rows = demand.theme_demand(videos, min_videos=2)
        by_term = {r["term"]: r for r in rows}
        self.assertIn("bitcoin", by_term)
        self.assertEqual(by_term["bitcoin"]["total_views"], 400)
        self.assertEqual(by_term["bitcoin"]["videos"], 2)
        self.assertNotIn("gold", by_term)  # aparece en un solo video -> ruido descartado

    def test_scan_nicho_dedupes_videos_across_queries(self):
        # el mismo video "x" sale en dos búsquedas -> debe contarse UNA vez
        calls = {"q1": [_video("x", "Ethereum staking guide", 500)],
                 "q2": [_video("x", "Ethereum staking guide", 500),
                        _video("y", "Ethereum merge recap", 200)]}
        orig = demand.__dict__.get("youtube")
        import omega.sources.youtube as yt
        saved = yt.fetch_recent
        yt.fetch_recent = lambda q, **kw: calls[q]
        try:
            rows, n = demand.scan_nicho(["q1", "q2"], days=30, max_results=25)
        finally:
            yt.fetch_recent = saved
        self.assertEqual(n, 2)  # x (dedupe) + y
        by_term = {r["term"]: r for r in rows}
        # 'ethereum' aparece en x e y -> 2 videos, 500+200 vistas (x no se dobla)
        self.assertEqual(by_term["ethereum"]["videos"], 2)
        self.assertEqual(by_term["ethereum"]["total_views"], 700)


class EnglishFilterTest(unittest.TestCase):
    """Filtro de idioma: solo contenido EN (protege RPM y limpia la señal)."""

    def test_declared_non_english_audio_is_dropped_even_with_latin_title(self):
        import omega.sources.youtube as yt
        # título en alfabeto latino pero audio declarado tamil -> fuera (el caso 'tamil motivation')
        v = {"title": "5 Smart Money Habits That Build Wealth | Tamil motivation", "language": "ta"}
        self.assertFalse(yt._is_english(v))

    def test_non_latin_title_without_declared_lang_is_dropped(self):
        import omega.sources.youtube as yt
        self.assertFalse(yt._is_english({"title": "स्टॉक मार्केट क्रैश", "language": ""}))  # hindi
        self.assertFalse(yt._is_english({"title": "股票市场分析", "language": ""}))          # chino

    def test_self_declared_language_name_in_latin_title_is_dropped(self):
        import omega.sources.youtube as yt
        # el patrón que se colaba: título latino, sin idioma declarado, pero dice "Tamil Motivation"
        v = {"title": "Money Never Stays? 5 Habits to Build Wealth | Tamil Motivation #shorts",
             "language": ""}
        self.assertFalse(yt._is_english(v))

    def test_title_betrayal_beats_mislabeled_english_audio(self):
        import omega.sources.youtube as yt
        # canal que MISLABELA su audio como 'en' pero el título dice Tamil -> el título manda
        v = {"title": "5 Habits to Build Wealth | Tamil Motivation #tamilshorts", "language": "en"}
        self.assertFalse(yt._is_english(v))

    def test_english_passes(self):
        import omega.sources.youtube as yt
        self.assertTrue(yt._is_english({"title": "How to Build Wealth in 2026", "language": "en-US"}))
        self.assertTrue(yt._is_english({"title": "Stock Market Crash Explained", "language": ""}))


class DemandCacheTest(unittest.TestCase):
    def setUp(self):
        # DB temporal aislada: repuntamos config.DB_PATH a un archivo en memoria por proceso
        import tempfile
        from omega import config, db
        self.config, self.db = config, db
        self._saved_path = config.DB_PATH
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        config.DB_PATH = self._tmp.name
        db.init()

    def tearDown(self):
        self.config.DB_PATH = self._saved_path
        os.unlink(self._tmp.name)

    def test_empty_cache_is_tolerant(self):
        # antes de escanear, fetch devuelve {} y no rompe (decide sigue funcionando)
        self.assertEqual(self.db.fetch_theme_demand(), {})

    def test_upsert_and_fetch_round_trip_and_replace(self):
        rows = [{"term": "bitcoin", "total_views": 400, "videos": 2, "avg_views": 200,
                 "examples": ["Bitcoin crash"]}]
        self.db.upsert_theme_demand(rows, scanned_at=1000)
        self.assertEqual(self.db.fetch_theme_demand(), {"bitcoin": 400})
        # re-escanear reemplaza (no acumula) el mismo término
        self.db.upsert_theme_demand(
            [{"term": "bitcoin", "total_views": 999, "videos": 3, "avg_views": 333,
              "examples": []}], scanned_at=2000)
        self.assertEqual(self.db.fetch_theme_demand(), {"bitcoin": 999})
        self.assertEqual(self.db.theme_demand_scanned_at(), 2000)

    def test_clear_removes_stale_terms_from_old_query_basket(self):
        # snapshot 1: basket viejo deja 'share market' (ruido de streams)
        self.db.upsert_theme_demand(
            [{"term": "share market", "total_views": 6_000_000, "videos": 16, "avg_views": 375_000,
              "examples": ["Zee Business Live"]}], scanned_at=1000)
        # snapshot 2: basket nuevo -> se limpia primero, luego se escribe lo fresco
        self.db.clear_theme_demand()
        self.db.upsert_theme_demand(
            [{"term": "build wealth", "total_views": 4_000_000, "videos": 8, "avg_views": 500_000,
              "examples": ["How to build wealth"]}], scanned_at=2000)
        cache = self.db.fetch_theme_demand()
        self.assertIn("build wealth", cache)
        self.assertNotIn("share market", cache)  # el término stale NO sobrevive al re-escaneo


class DemandFeatureInScoreTest(unittest.TestCase):
    """La feature 'demand' es genérica para el kernel: con peso >0, más demanda -> más score."""

    def setUp(self):
        self.con = store.connect(":memory:")
        for mod in (store, hypotheses):
            mod.init(self.con)

    def tearDown(self):
        self.con.close()

    def _cand(self, term, demand_norm):
        return hypotheses.create_hypothesis(
            self.con, domain="content", statement=f"Demanda creciente en torno a '{term}'",
            confidence=0.45, evidence={"features": {"momentum": 0.0, "prevalence": 5,
                                                     "contradiction": 0.0, "demand": demand_norm}})

    def test_higher_demand_wins_all_else_equal(self):
        weights = {"momentum": 0.05, "prevalence": 0.0, "contradiction": -0.30, "demand": 0.40}
        low = self.con.execute("SELECT * FROM hypothesis WHERE id=?",
                               (self._cand("low", 0.1),)).fetchone()
        high = self.con.execute("SELECT * FROM hypothesis WHERE id=?",
                                (self._cand("high", 1.0),)).fetchone()
        s_low, _ = decision_engine.score(low, weights)
        s_high, _ = decision_engine.score(high, weights)
        self.assertGreater(s_high, s_low)
        # la diferencia debe ser exactamente el peso · (1.0 - 0.1) = 0.36
        self.assertAlmostEqual(s_high - s_low, 0.40 * 0.9, places=4)


class DemandOriginatesHypothesisTest(unittest.TestCase):
    """B: la demanda de YouTube ORIGINA hipótesis (frases), no solo pondera las de RSS.

    Sin RSS (observed_content vacío), una frase de alta demanda debe volverse hipótesis; un
    token suelto genérico de más demanda NO (solo se originan frases: los tokens los cubre RSS)."""

    def setUp(self):
        import tempfile
        from omega import config, db
        from omega.reasoning import signals as sigstore
        self.config, self.db = config, db
        self._saved = config.DB_PATH
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        config.DB_PATH = self._tmp.name
        db.init()  # observed_content (vacío -> sin momentum RSS) + theme_demand
        self.con = store.connect(":memory:")
        for mod in (store, hypotheses, sigstore):
            mod.init(self.con)

    def tearDown(self):
        self.con.close()
        self.config.DB_PATH = self._saved
        os.unlink(self._tmp.name)

    def test_high_demand_phrase_originates_but_generic_token_does_not(self):
        from omega.analyze import hypothesis_engine
        self.db.upsert_theme_demand([
            {"term": "michael saylor", "total_views": 2_000_000, "videos": 5,
             "avg_views": 400_000, "examples": ["Saylor speaks at BTC Prague"]},
            {"term": "news", "total_views": 3_000_000, "videos": 10,  # más demanda, pero suelto
             "avg_views": 300_000, "examples": ["market news today"]},
        ], scanned_at=1000)

        hypothesis_engine.generate(self.con, domain="content")
        statements = [c["statement"] for c in hypotheses.list_candidates(self.con, "content")]

        self.assertTrue(any("michael saylor" in s for s in statements))  # frase -> se origina
        self.assertFalse(any("'news'" in s for s in statements))         # token suelto -> no

    def test_weak_demand_phrase_below_floor_is_skipped(self):
        from omega.analyze import hypothesis_engine
        self.db.upsert_theme_demand([
            {"term": "big topic", "total_views": 1_000_000, "videos": 4,
             "avg_views": 250_000, "examples": ["big topic"]},
            {"term": "tiny phrase", "total_views": 50_000, "videos": 2,  # <15% del máximo
             "avg_views": 25_000, "examples": ["tiny phrase"]},
        ], scanned_at=1000)

        hypothesis_engine.generate(self.con, domain="content")
        statements = [c["statement"] for c in hypotheses.list_candidates(self.con, "content")]

        self.assertTrue(any("big topic" in s for s in statements))
        self.assertFalse(any("tiny phrase" in s for s in statements))  # cola débil descartada


if __name__ == "__main__":
    unittest.main(verbosity=2)
