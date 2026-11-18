"""Long-form (tipo_video "largo", 16:9) on motor v2: F1 of docs/LONGFORM-PLAN.md."""

from __future__ import annotations

import json
import sys
import unittest
from typing import ClassVar
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


def _guion_largo(palabras=1400, tu_en=20, capitulos=4):
    """`palabras` words in 20-word sentences; the viewer ("you") at word `tu_en`."""
    relleno = ["the", "company", "sold", "chips", "to", "data", "centers", "while", "the", "stock", "kept", "climbing", "past", "every", "forecast", "made"]
    ws = [relleno[i % len(relleno)] for i in range(palabras)]
    ws[tu_en - 1] = "you"
    for i in range(50, palabras, 97):
        ws[i] = str(1000 + i)  # many distinct figures: no cap in long-form
    frases = [
        {"id": f"f{k}", "texto": " ".join(ws[i : i + 20]) + "."}
        for k, i in enumerate(range(0, palabras, 20))
    ]
    paso = len(frases) // max(1, capitulos)
    caps = [{"titulo": f"Part {k + 1}", "desde": k * paso} for k in range(capitulos)]
    return frases, caps


class GuionLargo(unittest.TestCase):
    def ids_malos(self, frases, caps):
        import guionista as g

        return sorted(
            p["id"]
            for p in g.puertas(frases, tipo_video="largo", capitulos=caps)
            if not p["ok"]
        )

    def test_good_long_script_passes(self):
        self.assertEqual(self.ids_malos(*_guion_largo()), [])

    def test_length_window(self):
        self.assertIn("G-LARGO", self.ids_malos(*_guion_largo(palabras=900)))
        self.assertIn("G-LARGO", self.ids_malos(*_guion_largo(palabras=1700)))

    def test_promise_within_30_s(self):
        self.assertIn("G-TU", self.ids_malos(*_guion_largo(tu_en=120)))

    def test_needs_three_chapters_from_zero_ascending(self):
        f, caps = _guion_largo(capitulos=2)
        self.assertIn("G-CAPITULOS", self.ids_malos(f, caps))
        f, caps = _guion_largo()
        self.assertIn("G-CAPITULOS", self.ids_malos(f, caps[1:] + caps[:1]))
        self.assertIn(
            "G-CAPITULOS", self.ids_malos(f, [{**caps[0], "desde": 99}, *caps[1:]])
        )

    def test_short_keeps_its_figure_cap(self):
        import guionista as g

        f, _ = _guion_largo()
        self.assertFalse(next(p for p in g.puertas(f) if p["id"] == "G-CIFRAS")["ok"])


class VozCapitulos(unittest.TestCase):
    def test_chapter_boundary_gets_0_9_s_silence(self):
        import voz

        sb = {
            "guion": [{"id": f"f{k}", "texto": f"Sentence {k}."} for k in range(4)],
            "capitulos": [{"titulo": "A", "desde": 0}, {"titulo": "B", "desde": 2}],
        }
        silencios = [t for t in voz.tomas(sb) if isinstance(t, float)]
        self.assertEqual(silencios, [0.3, 0.9, 0.3])

    def test_short_without_chapters_unchanged(self):
        import voz

        sb = {"guion": [{"id": "a", "texto": "One."}, {"id": "b", "texto": "Two."}]}
        self.assertEqual(voz.tomas(sb), [("One.", 1.0), 0.3, ("Two.", 1.0)])


class ListaCapitulos(unittest.TestCase):
    SB: ClassVar[dict] = {
        "guion": [
            {"texto": "One two."},
            {"texto": "Three four."},
            {"texto": "Five six."},
        ],
        "capitulos": [
            {"titulo": "Intro", "desde": 0},
            {"titulo": "The sale", "desde": 1},
            {"titulo": "What now", "desde": 2},
        ],
    }

    def words(self, *inicios):
        return [
            {"text": "w", "start": t, "end": t + 0.3}
            for a in inicios
            for t in (a, a + 0.5)
        ]

    def test_list_from_first_word_of_each_chapter(self):
        import producir

        t = producir.lista_capitulos(self.SB, self.words(0.4, 75.2, 610.0, 700.0))
        self.assertEqual(t, "0:00 Intro\n1:15 The sale\n10:10 What now")

    def test_chapter_shorter_than_10_s_is_refused(self):
        import producir

        with self.assertRaises(ValueError):
            producir.lista_capitulos(self.SB, self.words(0.4, 5.0, 610.0))

    def test_no_chapters_no_list(self):
        import producir

        self.assertEqual(producir.lista_capitulos({"guion": []}, []), "")


class Miniatura(unittest.TestCase):
    def test_four_words_max_and_background_required(self):
        import social

        self.assertEqual(social.validar_miniatura({"texto": "Huang *sold* again", "fondo": "img:x"}), [])
        self.assertEqual(len(social.validar_miniatura({"texto": "one two three four five", "fondo": "img:x"})), 1)
        self.assertEqual(len(social.validar_miniatura({"texto": "ok", "fondo": ""})), 1)

    def test_page_is_1280x720(self):
        import social

        h = social._html_miniatura("Huang sold")
        self.assertIn('data-width="1280" data-height="720"', h)
        self.assertIn("width: 1280px; height: 720px", h)


if __name__ == "__main__":
    unittest.main()
