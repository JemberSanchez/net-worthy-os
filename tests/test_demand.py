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

    def test_channel_name_terms_filtered_per_video(self):
        # ANTI-AUTOBOMBO: "CryptoNews Net" pone su marca en sus títulos -> min_videos no protege
        # (el mismo canal aporta los 2 videos). El término derivado del propio canal se descarta.
        spam = [dict(_video("a", "CryptoNews Net: Bitcoin update", 900), channel="CryptoNews Net"),
                dict(_video("b", "CryptoNews Net daily market recap", 800), channel="CryptoNews Net"),
                _video("c", "Bitcoin halving explained", 100)]
        by_term = {r["term"]: r for r in demand.theme_demand(spam, min_videos=2)}
        self.assertNotIn("cryptonews net", by_term)   # marca del canal: fuera
        self.assertNotIn("cryptonews", by_term)
        self.assertIn("bitcoin", by_term)             # tema real: sobrevive (videos a + c)
        self.assertEqual(by_term["bitcoin"]["videos"], 2)

    def test_channel_phrase_survives_if_other_channels_use_it(self):
        # si OTROS canales usan la frase como tema real, no se pierde: solo se filtra
        # en los videos del canal homónimo.
        videos = [dict(_video("a", "Housing Market crash?", 500), channel="Housing Market TV"),
                  dict(_video("b", "Housing market forecast 2027", 700), channel="Alice"),
                  dict(_video("c", "The housing market is frozen", 300), channel="Bob")]
        by_term = {r["term"]: r for r in demand.theme_demand(videos, min_videos=2)}
        self.assertIn("housing market", by_term)
        self.assertEqual(by_term["housing market"]["videos"], 2)      # b + c (a filtrado)
        self.assertEqual(by_term["housing market"]["total_views"], 1000)

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
            rows, videos = demand.scan_nicho(["q1", "q2"], days=30, max_results=25)
        finally:
            yt.fetch_recent = saved
        self.assertEqual(len(videos), 2)  # x (dedupe) + y
        by_term = {r["term"]: r for r in rows}
        # 'ethereum' aparece en x e y -> 2 videos, 500+200 vistas (x no se dobla)
        self.assertEqual(by_term["ethereum"]["videos"], 2)
        self.assertEqual(by_term["ethereum"]["total_views"], 700)

    def test_related_finds_adjacent_topics_by_co_occurrence(self):
        # audiencia de 'bitcoin': dos videos lo emparejan con 'ethereum', uno con 'gold'
        videos = [
            _video("a", "Bitcoin and Ethereum both pumping", 1000),
            _video("b", "Why Bitcoin beats Ethereum long term", 2000),
            _video("c", "Bitcoin vs gold as a hedge", 500),
        ]
        rows = demand.related("bitcoin", videos, min_together=2)
        terms = [r["term"] for r in rows]
        self.assertIn("ethereum", terms)      # co-ocurre en 2 videos -> adyacente
        self.assertNotIn("gold", terms)       # solo 1 video -> bajo el umbral
        self.assertNotIn("bitcoin", terms)    # el propio root no se lista
        eth = next(r for r in rows if r["term"] == "ethereum")
        self.assertEqual(eth["views"], 3000)  # 1000 + 2000 (vistas de los videos donde co-ocurre)

    def test_related_matches_words_not_substrings(self):
        # root 'car' NO debe excluir 'cards' (contiene 'car' como subcadena, no como palabra)
        videos = [
            _video("a", "car loans and credit cards explained", 1000),
            _video("b", "best car deals and credit cards", 2000),
        ]
        terms = [r["term"] for r in demand.related("car", videos, min_together=2)]
        self.assertIn("cards", terms)   # antes se excluía por 'car' in 'cards' (bug de subcadena)
        self.assertNotIn("car", terms)  # el root sí se excluye


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


class EvergreenTest(unittest.TestCase):
    """Visión evergreen: el punto ciego que solo dejaba a `decide` proponer noticia.

    VIRALIDAD.md §3.1: los 39 despegues tienen 133-352 días y siguen acumulando, pero
    `youtube-scan` pide publishedAfter=30d. El catálogo que SÍ funciona era invisible.
    """
    AHORA = 1784950000.0        # referencia fija: los tests no pueden depender de la fecha real

    def _v(self, vid, title, views, dias_atras, channel="c"):
        import datetime as dt
        pub = dt.datetime.fromtimestamp(self.AHORA - dias_atras*86400, dt.UTC)
        return {"video_id": vid, "title": title, "views": views, "channel": channel,
                "published_at": pub.strftime("%Y-%m-%dT%H:%M:%SZ"), "likes": 0, "comments": 0,
                "url": f"https://youtu.be/{vid}"}

    def test_views_per_day_separa_catalogo_vivo_de_solo_viejo(self):
        vivo  = self._v("a", "x", 300_000, 300)    # 1.000/día
        viejo = self._v("b", "x", 300_000, 1095)   # las mismas vistas en 3 años: ~274/día
        self.assertAlmostEqual(demand.views_per_day(vivo,  now=self.AHORA), 1000, delta=5)
        self.assertGreater(demand.views_per_day(vivo, now=self.AHORA),
                           demand.views_per_day(viejo, now=self.AHORA))

    def test_video_de_hoy_no_infla_la_velocidad(self):
        # sin el suelo de 1 día, un video de hace 1 hora daría 24x su cifra real
        hoy = self._v("a", "x", 5_000, 0)
        self.assertEqual(demand.views_per_day(hoy, now=self.AHORA), 5_000)

    def test_sin_fecha_de_publicacion_no_revienta(self):
        self.assertEqual(demand.views_per_day({"views": 100, "published_at": ""}), 0.0)
        self.assertEqual(demand.views_per_day({"views": 100, "published_at": "no-es-fecha"}), 0.0)

    def test_ranking_evergreen_pondera_velocidad_no_total(self):
        # 'compounding' acumula MENOS vistas totales pero mucha más velocidad que 'lottery'.
        # OJO: cada par comparte UNA sola palabra a propósito. Si dos términos empatan en vistas,
        # el desempate depende del hash de strings (aleatorio por proceso) y el test se vuelve
        # flaky — pasa aislado y falla en la suite.
        videos = [
            self._v("a", "compounding explained", 200_000, 200),   # 1.000/día
            self._v("b", "compounding basics",    200_000, 200),   # 1.000/día
            self._v("c", "lottery jackpot story", 900_000, 3000),  # 300/día
            self._v("d", "lottery ticket rich",   900_000, 3000),  # 300/día
        ]
        por_total = [r["term"] for r in demand.theme_demand(videos)]
        por_velocidad = [r["term"] for r in demand.theme_evergreen(videos, now=self.AHORA)]
        self.assertEqual(por_total[0], "lottery")        # por vistas totales gana lo viejo
        self.assertEqual(por_velocidad[0], "compounding")  # por velocidad gana lo vivo

    def _scan(self, capturados, subs_por_canal, **kw):
        """Corre scan_evergreen con la red monkeypatcheada. Devuelve (rows, videos)."""
        import omega.sources.youtube as yt
        orig_fetch, orig_subs = yt.fetch_recent, yt.channel_subs
        self.llamadas = {}
        def fake_fetch(q, days=30, max_results=25, order="viewCount", **k):
            self.llamadas['days'] = days; self.llamadas['order'] = order
            return list(capturados)
        yt.fetch_recent = fake_fetch
        yt.channel_subs = lambda ids: dict(subs_por_canal)
        try:
            return demand.scan_evergreen(["compound interest"], now=self.AHORA, **kw)
        finally:
            yt.fetch_recent, yt.channel_subs = orig_fetch, orig_subs

    def _vc(self, vid, title, views, dias, canal_id, likes=None):
        v = self._v(vid, title, views, dias)
        v["channel_id"] = canal_id
        v["likes"] = views // 50 if likes is None else likes   # 2% like rate por defecto
        return v

    def test_scan_evergreen_descarta_lo_reciente(self):
        capturados = [
            self._vc("viejo",    "compound interest explained", 500_000, 300, "ch1"),
            self._vc("viejo2",   "compound interest basics",    400_000, 250, "ch1"),
            self._vc("reciente", "compound interest news",      900_000, 10,  "ch1"),  # <90d
        ]
        rows, videos = self._scan(capturados, {"ch1": 20_000})
        self.assertEqual(self.llamadas['days'], 0)      # sin publishedAfter: ahí está el catálogo
        self.assertEqual(self.llamadas['order'], 'viewCount')
        self.assertEqual(sorted(v["video_id"] for v in videos), ["viejo", "viejo2"])
        self.assertTrue(all("views_per_day" in v for v in videos))
        self.assertTrue(any(r["term"] == "compound interest" for r in rows))

    def test_canales_gigantes_quedan_fuera(self):
        """El confounder que invalidó el Intento 2 de VIRALIDAD.md: sin banda de suscriptores el
        barrido devuelve lo que hacen canales de cientos de miles de subs, irreplicable aquí."""
        capturados = [
            self._vc("gigante", "compound interest explained", 300_000_000, 900, "mega"),
            self._vc("mi_liga", "compound interest basics",        400_000, 250, "chico"),
            self._vc("mi_liga2","compound interest simple",        300_000, 250, "chico"),
        ]
        _, videos = self._scan(capturados, {"mega": 12_000_000, "chico": 20_000})
        self.assertEqual(sorted(v["video_id"] for v in videos), ["mi_liga", "mi_liga2"])

    def test_canales_fantasma_tambien_quedan_fuera(self):
        # con 20 subs, 230 vistas ya parecen "x10": el multiplicador miente (VIRALIDAD.md §2)
        capturados = [
            self._vc("fantasma", "compound interest explained", 5_000, 200, "ghost"),
            self._vc("real",     "compound interest basics",  400_000, 250, "chico"),
        ]
        _, videos = self._scan(capturados, {"ghost": 20, "chico": 20_000})
        self.assertEqual([v["video_id"] for v in videos], ["real"])

    def test_engagement_de_humo_queda_fuera(self):
        # §3.3: todos los despegues reales tienen likes/vista entre 1% y 3,7%
        capturados = [
            self._vc("humo",  "compound interest explained", 900_000, 300, "chico", likes=200),
            self._vc("bueno", "compound interest basics",    400_000, 250, "chico"),
        ]
        _, videos = self._scan(capturados, {"chico": 20_000})
        self.assertEqual([v["video_id"] for v in videos], ["bueno"])


class TargetMarketFilterTest(unittest.TestCase):
    """Guard de MERCADO: inglés correcto pero dirigido a otro mercado (RPM ~10x menor).

    Es un filtro DISTINTO al de idioma: estos videos pasan `_is_english` legítimamente.
    Casos reales del scan del 2026-07-24 que hicieron ganar a 'build wealth' con un 70% de
    demanda inflada.
    """

    def test_real_case_indiabulls_sip_is_dropped(self):
        import omega.sources.youtube as yt
        v = {"title": "Build Wealth by Investing in the Brands You Believe In with Stock SIP",
             "channel": "Indiabulls Securities", "language": "en"}
        self.assertTrue(yt._is_english(v))          # el idioma es correcto...
        self.assertFalse(yt._is_target_market(v))   # ...pero el mercado no es el nuestro

    def test_real_case_rupee_symbol_and_lakh_are_dropped(self):
        import omega.sources.youtube as yt
        v = {"title": "Warren Buffett's ₹2 Lakh Investment Strategy: Build Wealth",
             "channel": "Finance Guru", "language": "en"}
        self.assertTrue(yt._is_english(v))
        self.assertFalse(yt._is_target_market(v))

    def test_market_acronyms_are_case_sensitive(self):
        import omega.sources.youtube as yt
        # 'SIP' (Systematic Investment Plan) fuera; 'Sip' (beber) es inglés corriente y pasa.
        self.assertFalse(yt._is_target_market({"title": "Best SIP Plans for 2026", "channel": "x"}))
        self.assertTrue(yt._is_target_market({"title": "Sip Coffee, Save Money", "channel": "x"}))

    def test_ambiguous_english_words_are_not_false_positives(self):
        import omega.sources.youtube as yt
        # 'nifty' solo se rechaza como índice ('Nifty 50'), no como adjetivo inglés.
        self.assertTrue(yt._is_target_market(
            {"title": "A Nifty Little Trick to Save $500 a Month", "channel": "x"}))
        self.assertFalse(yt._is_target_market(
            {"title": "Nifty 50 Outlook for Next Week", "channel": "x"}))

    def test_country_in_title_is_a_topic_not_a_market(self):
        import omega.sources.youtube as yt
        # Un canal US hablando DE India es un tema legítimo: el país solo delata en el CANAL.
        self.assertTrue(yt._is_target_market(
            {"title": "Why India's Economy Matters for US Investors", "channel": "Bloomberg"}))
        self.assertFalse(yt._is_target_market(
            {"title": "Why the Economy Matters", "channel": "India Today Business"}))

    def test_clean_us_content_passes(self):
        import omega.sources.youtube as yt
        self.assertTrue(yt._is_target_market(
            {"title": "How to Build Wealth on a Low Income", "channel": "Money Guy"}))
        self.assertTrue(yt._is_target_market(
            {"title": "7 Powerful Money Habits", "channel": "Financial Tips"}))

    def test_fetch_recent_applies_the_guard_at_capture(self):
        import omega.sources.youtube as yt
        captured = [
            {"video_id": "a", "title": "Build Wealth with Stock SIP", "channel": "Indiabulls",
             "language": "en", "views": 1_000_000},
            {"video_id": "b", "title": "How to Build Wealth on a Low Income", "channel": "Money Guy",
             "language": "en", "views": 90_000},
        ]
        orig_search, orig_stats = yt.search_video_ids, yt.video_stats
        yt.search_video_ids = lambda *a, **k: ["a", "b"]
        yt.video_stats = lambda ids: list(captured)
        try:
            out = yt.fetch_recent("build wealth", days=0)
            self.assertEqual([v["video_id"] for v in out], ["b"])  # el indio no entra al dataset
        finally:
            yt.search_video_ids, yt.video_stats = orig_search, orig_stats


class MonetizationTest(unittest.TestCase):
    """Valor por nicho (RPM): no todas las vistas valen igual en dinero."""

    def test_high_rpm_subniches_beat_crypto(self):
        from omega.analyze import monetization as mon
        self.assertGreater(mon.rpm_prior("best tax software for retirement"),
                           mon.rpm_prior("bitcoin price prediction"))
        self.assertEqual(mon.rpm_prior("cheap car insurance quotes"), 70)   # ultra
        self.assertEqual(mon.rpm_prior("dogecoin to the moon"), 8)          # crypto/volátil

    def test_unknown_topic_gets_niche_baseline(self):
        from omega.analyze import monetization as mon
        self.assertEqual(mon.rpm_prior("some random title"), 12)  # baseline

    def test_score_is_normalized_0_1(self):
        from omega.analyze import monetization as mon
        self.assertAlmostEqual(mon.monetization_score("mortgage refinance"), 1.0, places=2)
        self.assertLess(mon.monetization_score("crypto news"), 0.2)


class AbstainIsReachableTest(unittest.TestCase):
    """REGRESIÓN (2026-07-16): la abstención tiene que ser ALCANZABLE.

    El umbral era 0.50 = exactamente la confianza base de un candidato de la vía demanda. Como
    score = confianza + Σ peso·feature y las features de demanda son >= 0, todo candidato pasaba
    SIEMPRE: el sistema no podía decir 'hoy no hay nada bueno' aunque no lo hubiera.
    """

    def test_threshold_is_above_demand_path_base_confidence(self):
        from omega import config
        # confianza base vía demanda: 0.50 + 0.08*momentum - 0.20*contradiction, con momentum 0
        base_conf = 0.50
        self.assertGreater(
            config.ABSTAIN_THRESHOLD, base_conf,
            "el umbral debe exigir features REALES por encima de la confianza base, "
            "o la abstención es inalcanzable por construcción")


class DemandMomentumNeedsBaselineTest(unittest.TestCase):
    """REGRESIÓN (2026-07-16): sin baseline no hay momentum — no un momentum inventado.

    Un término ausente del escaneo previo daba old=0 -> log2(v+1) -> capado a 2.0 -> +0.40 al
    score, IDÉNTICO para 1.000 vistas que para 700.000. Casi el máximo de `demand` (+0.45): un
    término nuevo por variación del basket ganaba `decide` por goleada. Y 'nuevo' no es 'emergente'.
    """

    def setUp(self):
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

    def _scan(self, rows, at):
        # el momentum se lee de theme_demand_history (no del cache de upsert_theme_demand)
        self.db.append_theme_demand_history(
            [{"term": t, "total_views": v, "videos": 3} for t, v in rows], scanned_at=at)

    def test_term_without_baseline_scores_zero_momentum(self):
        self._scan([("old topic", 100_000)], at=1000)
        self._scan([("old topic", 100_000), ("brand new topic", 1_000)], at=2000)
        dmom = self.db.fetch_demand_momentum()
        self.assertNotIn("brand new topic", dmom,
                         "un término sin baseline no puede puntuar momentum: no es medible")
        self.assertEqual(dmom.get("brand new topic", 0.0), 0.0)

    def test_real_growth_still_measured(self):
        # el arreglo NO puede matar la señal legítima: con baseline, el crecimiento se mide
        self._scan([("real topic", 100_000)], at=1000)
        self._scan([("real topic", 200_000)], at=2000)
        self.assertAlmostEqual(self.db.fetch_demand_momentum()["real topic"], 1.0, places=2)  # 2x

    def test_a_new_term_cannot_outscore_a_term_with_real_demand(self):
        from omega import config
        w = config.DECISION_WEIGHTS
        self._scan([("real topic", 700_000)], at=1000)
        self._scan([("real topic", 770_000), ("noise", 1_000)], at=2000)
        dmom = self.db.fetch_demand_momentum()
        aporte_ruido = w["demand_momentum"] * dmom.get("noise", 0.0)
        aporte_real = w["demand_momentum"] * dmom.get("real topic", 0.0)
        self.assertEqual(aporte_ruido, 0.0)
        self.assertGreater(aporte_real, aporte_ruido)


class MonetizationNotContaminatedByExampleTest(unittest.TestCase):
    """REGRESIÓN (2026-07-16): el RPM se mide sobre el TÉRMINO, nunca sobre el título ajeno.

    Bug real, cazado en producción: 'housing market' (baseline $12) heredaba $70 porque el
    `example` — un título de OTRO canal traído por el scan — decía "Mortgage Rates". Ese +0.3
    de score le hacía GANAR `decide`, y con él se eligió el tema de un video real. El ejemplo
    es incidental (se elige arbitrariamente entre los del scan): dejar que decida el RPM hace
    que la elección de tema dependa de qué título haya pescado YouTube ese día.
    Misma clase que el bug de 'justin verlander' vía "OR retirement": texto ajeno contamina.
    """

    def setUp(self):
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

    def _monetization_of(self, term, example):
        import json
        from omega.analyze import hypothesis_engine
        from omega.reasoning import hypotheses, signals
        self.db.upsert_theme_demand(
            [{"term": term, "total_views": 700_000, "videos": 8, "avg_views": 87_500,
              "examples": [example]}], scanned_at=1000)
        with self.db.connect() as con:
            signals.init(con)          # el engine lee `signal` (prevalencia) y escribe `hypothesis`
            hypotheses.init(con)
            hypothesis_engine.generate(con)
            for row in hypotheses.list_candidates(con, domain="content"):
                ev = json.loads(row["evidence"])
                if ev["signals"][0]["value"] == term:
                    return ev["features"]["monetization"]
        self.fail(f"no se generó hipótesis para {term!r}")

    def test_example_title_does_not_inflate_rpm(self):
        # el término es baseline ($12 -> 0.171); el título ajeno menciona "Mortgage" ($70 -> 1.0)
        monet = self._monetization_of(
            "housing market", "Housing Market Update: Home Prices, Mortgage Rates & Outlook")
        self.assertAlmostEqual(monet, 0.171, places=3)

    def test_rpm_is_independent_of_which_example_was_scraped(self):
        # el MISMO término no puede puntuar distinto según el título que pescara el scan
        a = self._monetization_of("housing market", "Housing Market Update: Mortgage Rates")
        self.tearDown(); self.setUp()
        b = self._monetization_of("housing market", "Housing Market: what nobody tells you")
        self.assertEqual(a, b)


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


class DemandMomentumTest(unittest.TestCase):
    """#2: momentum de demanda entre escaneos (necesita >=2; con 1, no hay señal)."""

    def setUp(self):
        import tempfile
        from omega import config, db
        self.config, self.db = config, db
        self._saved = config.DB_PATH
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        config.DB_PATH = self._tmp.name
        db.init()

    def tearDown(self):
        self.config.DB_PATH = self._saved
        os.unlink(self._tmp.name)

    def test_single_scan_has_no_momentum(self):
        self.db.append_theme_demand_history(
            [{"term": "build wealth", "total_views": 1_000_000, "videos": 5}], scanned_at=1000)
        self.assertEqual(self.db.fetch_demand_momentum(), {})  # sin baseline, sin señal

    def test_rising_demand_is_positive_new_term_has_no_momentum(self):
        # CAMBIADO 2026-07-16. Este test exigía que un término NUEVO puntuara momentum alto
        # (>5, capado luego a 2.0 = +0.40 al score). La intención era "detectar demanda
        # emergente antes que el resto"; el efecto medido fue otro: un término nuevo de 1.000
        # vistas puntuaba IGUAL que uno de 700.000 y ganaba `decide` por encima de términos con
        # demanda real (Warren Buffett aporta +0.112 en total). Y un término "nuevo" no es
        # demanda emergente: casi siempre es que el basket de queries pescó algo distinto.
        # Sin baseline el momentum no es medible -> 0. La demanda emergente real se ve en el
        # escaneo siguiente, ya con baseline.
        self.db.append_theme_demand_history([
            {"term": "build wealth", "total_views": 1_000_000, "videos": 5},
        ], scanned_at=1000)
        # escaneo 2: 'build wealth' duplica; 'ai stocks' aparece por primera vez
        self.db.append_theme_demand_history([
            {"term": "build wealth", "total_views": 2_000_000, "videos": 6},
            {"term": "ai stocks", "total_views": 3_000_000, "videos": 4},
        ], scanned_at=2000)
        mom = self.db.fetch_demand_momentum()
        self.assertAlmostEqual(mom["build wealth"], 1.0, places=1)  # log2(2M/1M) ~ 1.0 (duplicó)
        self.assertNotIn("ai stocks", mom)                          # sin baseline -> no medible


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
