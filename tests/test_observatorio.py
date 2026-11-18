"""Observatorio P0 (docs/OBSERVATORIO.md): full traffic breakdown, hourly snapshots, autopsy.

Fake clients only: no network.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega import analytics_yt as ay
from omega.creative import production_dna
from omega.reasoning import store

T0 = 1_800_000_000  # fixed "now" (epoch s)


class _Exec:
    def __init__(self, v):
        self.v = v

    def execute(self):
        return self.v


class FakeStats:
    """Data API videos.list(part=statistics) over a fixed id -> stats map."""

    def __init__(self, stats):
        self.stats, self.pedidos = stats, []

    def videos(self):
        return self

    def list(self, **kw):
        ids = kw["id"].split(",")
        self.pedidos.append(ids)
        return _Exec(
            {
                "items": [
                    {"id": i, "statistics": self.stats[i]}
                    for i in ids
                    if i in self.stats
                ]
            }
        )


class AutopsiaTest(unittest.TestCase):
    # Real cases measured on 14-nov-2026 (docs/OBSERVATORIO.md section 1).
    def test_casos_reales(self):
        casos = {
            "nvidia-weight": (2, {"YT_SEARCH": 2}, 0.0, "no_probado"),
            "binance-heist": (5, {"YT_SEARCH": 2, "SHORTS": 2}, 0.0, "deslizado"),
            "fed-vs-card": (4, {"SHORTS": 1, "YT_SEARCH": 2}, 0.1108, "deslizado"),
            "holiday-debt": (29, {"SHORTS": 26}, 0.191, "deslizado"),
            "ronald-wayne": (241, {"SHORTS": 237}, 0.6974, "empujado"),
            "midterm-rally": (496, {"SHORTS": 479}, 0.8117, "empujado"),
        }
        for ref, (v, traf, avp, esperado) in casos.items():
            with self.subTest(ref=ref):
                self.assertEqual(ay.autopsia(v, traf, avp), esperado)

    def test_visto_sin_empuje_y_sin_datos(self):
        self.assertEqual(ay.autopsia(7, {"SHORTS": 7}, 0.48), "visto_sin_empuje")
        self.assertEqual(ay.autopsia(None, None, None), "sin_datos")
        self.assertEqual(ay.autopsia(0, {}, None), "sin_datos")

    def test_bucle_mas_de_100_cuenta_como_visto(self):
        self.assertEqual(ay.autopsia(300, {"SHORTS": 290}, 1.12), "empujado")


class DesgloseTest(unittest.TestCase):
    def test_resumen_guarda_desglose_completo(self):
        r = ay.resumen(
            {"views": 5, "averageViewPercentage": 0.0},
            [(0, 1), (1, 0.3)],
            [
                {"insightTrafficSourceType": "YT_SEARCH", "views": 2},
                {"insightTrafficSourceType": "SHORTS", "views": 2},
                {"insightTrafficSourceType": "SUBSCRIBER", "views": 1},
            ],
            None,
            37,
        )
        self.assertEqual(
            r["traffic_breakdown"], {"YT_SEARCH": 2, "SHORTS": 2, "SUBSCRIBER": 1}
        )

    def test_desglose_persiste_y_bd_vieja_migra(self):
        con = store.connect(":memory:")
        con.execute(
            "CREATE TABLE production_analytics (production_ref TEXT PRIMARY KEY, ctr REAL, "
            "avd_pct REAL, retention_avg REAL, traffic_source TEXT, retention_by_block TEXT, "
            "measured_at INTEGER NOT NULL)"
        )
        production_dna.init(con)
        production_dna.record_analytics(
            con, production_ref="v", views=5, traffic_breakdown={"SHORTS": 2}
        )
        fila = con.execute(
            "SELECT traffic_breakdown FROM production_analytics"
        ).fetchone()
        self.assertEqual(json.loads(fila[0]), {"SHORTS": 2})
        con.close()


class FotosTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        production_dna.init(self.con)
        h = 3600
        # published 2 h ago, 5 days ago, 30 days ago (too old), and one only scheduled (no date)
        for ref, vid, edad in (
            ("a", "A", 2 * h),
            ("b", "B", 5 * 24 * h),
            ("c", "C", 30 * 24 * h),
        ):
            production_dna.record_video(
                self.con, ref, vid, publish_at=ay.iso_utc(T0 - edad)
            )
        production_dna.record_video(self.con, "d", "D")

    def tearDown(self):
        self.con.close()

    def test_solo_videos_recientes_y_horas_desde_publicar(self):
        yt = FakeStats(
            {
                "A": {"viewCount": "12", "likeCount": "1", "commentCount": "0"},
                "B": {"viewCount": "300"},  # likes hidden: NULL, not 0
            }
        )
        n = ay.fotos(self.con, yt, now=T0)
        self.assertEqual(n, 2)
        self.assertEqual(
            yt.pedidos, [["A", "B"]]
        )  # one batched call, no old/unpublished ids
        filas = self.con.execute(
            "SELECT production_ref, t_horas, views, likes, comments FROM production_snapshot "
            "ORDER BY production_ref"
        ).fetchall()
        self.assertEqual(
            [tuple(f) for f in filas],
            [("a", 2.0, 12, 1, 0), ("b", 120.0, 300, None, None)],
        )

    def test_repetir_en_la_misma_hora_no_duplica(self):
        yt = FakeStats({"A": {"viewCount": "12"}, "B": {"viewCount": "300"}})
        ay.fotos(self.con, yt, now=T0)
        ay.fotos(self.con, yt, now=T0 + 60)
        n = self.con.execute("SELECT COUNT(*) FROM production_snapshot").fetchone()[0]
        self.assertEqual(n, 2)


if __name__ == "__main__":
    unittest.main()
