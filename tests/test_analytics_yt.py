"""Tests del Analytics automático (omega/analytics_yt.py) con clientes FALSOS: sin red.

Lo importante: que los bucles de Shorts (>100 %) no rompan el contrato [0,1] del dataset, que la
retención por bloque use el ADN real, y que el video_id viva en la BASE (viaja al repo de estado).
"""
from __future__ import annotations
import json
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega import analytics_yt as ay  # noqa: E402
from omega.reasoning import store  # noqa: E402
from omega.creative import production_dna, decisions, scoring  # noqa: E402


def _resp(cols, rows):
    return {"columnHeaders": [{"name": c} for c in cols], "rows": rows}


class _Exec:
    def __init__(self, v):
        self.v = v

    def execute(self):
        return self.v


class FakeYT:
    def __init__(self, privacy="public"):
        self.privacy = privacy

    def videos(self):
        return self

    def list(self, **kw):
        return _Exec({"items": [{"status": {"privacyStatus": self.privacy},
                                 "snippet": {"publishedAt": "2026-09-20T16:00:00Z"},
                                 "contentDetails": {"duration": "PT40S"}}]})


class FakeYTA:
    def __init__(self, sin_engaged=False):
        self.sin_engaged, self.llamadas = sin_engaged, []

    def reports(self):
        return self

    def query(self, **kw):
        self.llamadas.append(kw)
        dims = kw.get("dimensions")
        if dims is None:
            if "engagedViews" in kw["metrics"]:
                if self.sin_engaged:
                    raise RuntimeError("Unknown metric engagedViews")
                return _Exec(_resp(["views", "engagedViews", "averageViewPercentage", "averageViewDuration"],
                                   [[500, 210, 112.0, 44.8]]))
            return _Exec(_resp(["views", "averageViewPercentage", "averageViewDuration"], [[500, 112.0, 44.8]]))
        if dims == "elapsedVideoTimeRatio":        # 1.2 al inicio (bucle) -> 0.3 al final
            return _Exec(_resp(["elapsedVideoTimeRatio", "audienceWatchRatio", "relativeRetentionPerformance"],
                               [[i / 100, 1.2 - 0.9 * i / 100, 0.5] for i in range(1, 101)]))
        if dims == "insightTrafficSourceType":
            return _Exec(_resp(["insightTrafficSourceType", "views"], [["SHORTS", 420], ["YT_SEARCH", 80]]))
        return _Exec(_resp(["insightTrafficSourceDetail", "views"], [["ronald read janitor", 50], ["janitor millionaire", 30]]))


class PurasTest(unittest.TestCase):
    def test_duracion_iso(self):
        self.assertEqual(ay.duracion_iso("PT40S"), 40)
        self.assertEqual(ay.duracion_iso("PT1M5S"), 65)
        with self.assertRaises(ay.AnalyticsError):
            ay.duracion_iso("40s")

    def test_interpolacion_y_bordes(self):
        c = [(0.1, 1.0), (0.2, 0.5)]
        self.assertAlmostEqual(ay.retencion_en(c, 0.15), 0.75)
        self.assertEqual(ay.retencion_en(c, 0.0), 1.0)
        self.assertEqual(ay.retencion_en(c, 1.0), 0.5)
        self.assertIsNone(ay.retencion_en([], 0.5))

    def test_por_bloques_usa_el_adn_y_recorta(self):
        curva = [(0.0, 1.3), (0.5, 0.4), (1.0, 0.2)]
        r = ay.por_bloques(curva, [{"block": "hook", "length_s": 10}, {"block": "datos", "length_s": 10},
                                   {"block": "hook", "length_s": 20}], 40)
        self.assertEqual(r, {"hook": 1.0, "datos": 0.85, "hook#3": 0.4})     # 1.3 -> 1.0 (bucle)
        sin_adn = ay.por_bloques(curva, None, 40)
        self.assertEqual(set(sin_adn), {"3s", "10s", "20s", "fin"})

    def test_resumen_shorts_mas_de_100(self):
        r = ay.resumen({"views": 500, "averageViewPercentage": 112.0}, [(0, 1), (1, .3)],
                       [{"insightTrafficSourceType": "SHORTS", "views": 9}], None, 40)
        self.assertEqual((r["retention_avg"], r["avg_view_pct_raw"], r["traffic_source"]), (1.0, 1.12, "shorts"))
        self.assertIsNone(r["engaged_views"])


class ConsultarGuardarTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        for mod in (production_dna, decisions):
            mod.init(self.con)

    def tearDown(self):
        self.con.close()

    def test_privado_no_consulta_analytics(self):
        yta = FakeYTA()
        self.assertEqual(ay.consultar("x", FakeYT("private"), yta)["estado"], "privado")
        self.assertEqual(yta.llamadas, [])

    def test_flujo_completo_y_rescore(self):
        production_dna.record_dna(self.con, production_ref="r7", blocks=[
            {"block": "hook", "technique": "t", "length_s": 4}, {"block": "cuerpo", "technique": "t", "length_s": 36}])
        datos = ay.consultar("vid", FakeYT(), FakeYTA(), hoy=date(2026, 9, 25))
        self.assertEqual(datos["estado"], "ok")
        r = ay.guardar(self.con, "r7", datos, now=1)
        row = self.con.execute("SELECT * FROM production_analytics WHERE production_ref='r7'").fetchone()
        self.assertEqual((row["views"], row["engaged_views"], row["retention_avg"]), (500, 210, 1.0))
        self.assertEqual(set(json.loads(row["retention_by_block"])), {"hook", "cuerpo"})
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM production_retention").fetchone()[0], 100)
        self.assertEqual(r["busquedas"][0], ("ronald read janitor", 50))
        self.assertGreater(r["puntos_control"]["3s"], 1.0)                 # bruto: se ve el bucle
        score, partes = scoring.desde_analytics(self.con, "r7")
        self.assertFalse(partes["parcial"])
        # re-sincronizar reemplaza, no duplica
        ay.guardar(self.con, "r7", datos, now=2)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM production_search_terms").fetchone()[0], 2)

    def test_sin_engaged_views_sigue(self):
        datos = ay.consultar("vid", FakeYT(), FakeYTA(sin_engaged=True))
        self.assertNotIn("engagedViews", datos["basicas"])
        self.assertEqual(datos["estado"], "ok")

    def test_video_en_la_base_conserva_publish_at(self):
        production_dna.record_video(self.con, "r8", "abc", publish_at="2026-09-26T16:00:00Z")
        production_dna.record_video(self.con, "r8", "abc")
        self.assertEqual(production_dna.video_de(self.con, "r8"), "abc")
        self.assertEqual(self.con.execute("SELECT publish_at FROM production_video").fetchone()[0],
                         "2026-09-26T16:00:00Z")
        self.assertIsNone(production_dna.video_de(self.con, "nada"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
