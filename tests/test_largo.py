"""Long-form (tipo_video "largo", 16:9) on motor v2: F1 of docs/LONGFORM-PLAN.md."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]

import construir as c

REF = RAIZ / "video-v2" / "read-janitor"


def _sb_words(**extra):
    sb = json.loads((REF / "storyboard.json").read_text(encoding="utf-8"))
    sb.update(extra)
    return sb, json.loads((REF / "assets" / "words.json").read_text(encoding="utf-8"))


class Layout169(unittest.TestCase):
    def test_largo_plan_and_page_are_1920x1080(self):
        p = c.plan(*_sb_words(tipo_video="largo"))
        self.assertEqual((p["tipo_video"], p["W"], p["H"]), ("largo", 1920, 1080))
        h = c._html(p)
        self.assertIn('data-width="1920" data-height="1080"', h)
        self.assertIn("width: 1920px; height: 1080px", h)
        self.assertIn("#root.ancho .scene", h)
        self.assertRegex(h, r'id="root" class="[^"]*\bancho\b')

    def test_short_plan_has_no_largo_keys(self):
        p = c.plan(*_sb_words())
        self.assertNotIn("tipo_video", p)
        self.assertNotIn(
            "ancho", c._html(p).split('id="root" class="')[1].split('"')[0]
        )

    def test_transition_push_scaled_to_frame_width(self):
        tr = {"sale": {"x": -700}, "entra": {"x": 700, "y": 1240}, "reposo": {"x": 0}}
        e = c._escalar_tr(tr, 1920 / 1080, 1080 / 1920)
        self.assertAlmostEqual(e["entra"]["x"], 700 * 1920 / 1080)
        self.assertAlmostEqual(e["entra"]["y"], 1240 * 1080 / 1920)
        self.assertEqual(tr["sale"]["x"], -700)  # input untouched

    def test_prueba_covers_16x9_frame(self):
        x = {
            "en": "1:Ronald",
            "img": "d",
            "_caja_n": [0.1, 0.45, 0.9, 0.52],
            "_aspecto": 1.3,
        }
        w = _sb_words()[1]
        fr = c.anclas.frases(w)
        d = c.prueba(x, 0, w, fr, 30.0, 1920, 1080)["doc"]
        self.assertGreaterEqual(d[2], 1920)
        self.assertLessEqual(d[0], 0)
        self.assertGreaterEqual(d[0] + d[2], 1920)


class UmbralesPorTipo(unittest.TestCase):
    def test_largo_drops_shorts_ui_zone(self):
        import critico

        rub = critico.cargar_rubrica(REF)
        corto = critico.umbrales(rub, {})
        largo = critico.umbrales(rub, {"tipo_video": "largo"})
        self.assertEqual(corto["zona_derecha"], 0.86)
        self.assertGreater(largo["zona_derecha"], 1.0)
        self.assertGreater(largo["zona_inferior"], corto["zona_inferior"])


if __name__ == "__main__":
    unittest.main()
