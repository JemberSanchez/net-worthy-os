"""meta-sync: Facebook and Instagram reel metrics, read through the Graph API shapes and stored."""

import sqlite3
import unittest
from unittest import mock

from omega import publish_meta
from omega.creative import production_dna


def _insights(**valores):
    return {"data": [{"name": k, "values": [{"value": v}]} for k, v in valores.items()]}


class Metricas(unittest.TestCase):
    def _con_respuestas(self, *respuestas):
        p = mock.patch.object(publish_meta, "_request", side_effect=list(respuestas))
        peticion = p.start()
        self.addCleanup(p.stop)
        return peticion

    def test_facebook_convierte_ms_y_lee_likes_y_repeticiones(self):
        self._con_respuestas(
            {
                "views": 302,
                "likes": {"summary": {"total_count": 2}},
                "comments": {"summary": {"total_count": 1}},
            },
            _insights(post_video_avg_time_watched=12753, fb_reels_replay_count=52),
        )
        m = publish_meta.metricas_reel("facebook", "v1", "tok")
        self.assertEqual((m["views"], m["likes"], m["comments"], m["replays"]), (302, 2, 1, 52))
        self.assertAlmostEqual(m["avg_watch_s"], 12.753)
        self.assertNotIn("reach", m)

    def test_instagram_lee_alcance_guardados_y_compartidos(self):
        self._con_respuestas(
            {"like_count": 1, "comments_count": 0},
            _insights(views=118, reach=106, saved=3, shares=4, ig_reels_avg_watch_time=12973),
        )
        m = publish_meta.metricas_reel("instagram", "m1", "tok")
        self.assertEqual(
            (m["views"], m["reach"], m["likes"], m["comments"], m["saved"], m["shares"]),
            (118, 106, 1, 0, 3, 4),
        )
        self.assertAlmostEqual(m["avg_watch_s"], 12.973)
        self.assertNotIn("replays", m)


class Guardado(unittest.TestCase):
    def test_una_fila_por_plataforma_y_la_ultima_medicion_reemplaza(self):
        con = sqlite3.connect(":memory:")
        production_dna.init(con)
        production_dna.record_social(con, "r", "facebook", {"views": 1, "avg_watch_s": 2.0}, now=10)
        production_dna.record_social(con, "r", "instagram", {"views": 5}, now=10)
        production_dna.record_social(con, "r", "facebook", {"views": 9, "likes": 3}, now=20)
        filas = con.execute(
            "SELECT platform, views, likes, avg_watch_s, measured_at FROM production_social"
            " ORDER BY platform"
        ).fetchall()
        self.assertEqual(filas, [("facebook", 9, 3, None, 20), ("instagram", 5, None, None, 10)])


if __name__ == "__main__":
    unittest.main()
