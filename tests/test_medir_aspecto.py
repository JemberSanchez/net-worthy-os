"""tools/medir_aspecto.py against synthetic known cases, and the aspect/selection gates in construir.py."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

RAIZ = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]

import broll
import construir as c
import medir_aspecto as ma


def lleno(rgb, n=4, h=96, w=54):
    return np.full((n, h, w, 3), rgb, np.uint8)


class TestPixeles(unittest.TestCase):
    def test_green_black_vs_neutral(self):
        verde = ma.medir_pixeles(lleno((20, 90, 40)))
        self.assertEqual(verde["verde_amarillo_pct"], 100.0)
        gris = ma.medir_pixeles(lleno((128, 128, 128)))
        self.assertEqual(gris["verde_amarillo_pct"], 0.0)
        self.assertEqual(gris["saturacion"], 0.0)

    def test_very_dark_and_luma(self):
        self.assertEqual(
            ma.medir_pixeles(lleno((10, 10, 10)))["muy_oscuros_pct"], 100.0
        )
        self.assertEqual(
            ma.medir_pixeles(lleno((200, 200, 200)))["muy_oscuros_pct"], 0.0
        )
        self.assertEqual(ma.medir_pixeles(lleno((200, 200, 200)))["luma"], 200.0)

    def test_vignette_lowers_corners_over_centre(self):
        f = lleno((200, 200, 200))
        self.assertEqual(ma.medir_pixeles(f)["esquinas_centro"], 1.0)
        f = f.copy()
        f[:, :20, :] = 40
        f[:, -20:, :] = 40
        self.assertLess(ma.medir_pixeles(f)["esquinas_centro"], 0.5)

    def test_entropy_grows_with_colour_variety(self):
        rng = np.random.default_rng(1)
        ruido = rng.integers(0, 255, (4, 96, 54, 3), np.uint8)
        self.assertGreater(
            ma.medir_pixeles(ruido)["entropia_color"],
            ma.medir_pixeles(lleno((20, 90, 40)))["entropia_color"] + 3,
        )

    def test_compositions_count_cuts_not_stills(self):
        rng = np.random.default_rng(3)
        a = np.kron(rng.integers(0, 255, (8, 9, 3), np.uint8), np.ones((12, 6, 1), np.uint8))
        b = np.kron(rng.integers(0, 255, (8, 9, 3), np.uint8), np.ones((12, 6, 1), np.uint8))
        quieto = np.stack([a] * 8)
        self.assertEqual(ma.composiciones(quieto)["cambios_composicion_10s"], 0.0)
        self.assertEqual(ma.composiciones(quieto)["composiciones"], 1)
        cortado = np.stack([a] * 4 + [b] * 4)
        self.assertEqual(ma.composiciones(cortado)["composiciones"], 2)
        self.assertGreater(ma.composiciones(cortado)["cambios_composicion_10s"], 0)


def plan_base():
    return {
        "D": 10.0,
        "aviso": {"ventanas": [[1.0, 8.0]], "final": 9.0},
        "pruebas": [{"t0": 2.0, "t1": 3.0, "img": "doc"}],
        "fotos": [{"img": "a"}, {"clip": "b"}, {"clip": "b"}],
        "escenas": [
            {
                "tipo": "foto",
                "t0": 0.0,
                "t1": 4.0,
                "rotulos": [{"en": 0.0, "hasta": 1.0}],
                "pos": "ter",
            },
            {"tipo": "foto", "t0": 4.0, "t1": 6.0, "limpio": True},
            {
                "tipo": "grafica",
                "t0": 6.0,
                "t1": 10.0,
                "rotulos": [{"en": 6.0}],
                "pos": "sup",
            },
        ],
    }


class TestPlan(unittest.TestCase):
    def test_known_plan(self):
        m = ma.medir_plan(plan_base())
        # foto 0: 1-4 s minus the 2-3 s proof = 2 s; clean foto: 2 s
        self.assertEqual(m["imagen_sin_texto_grande_pct"], 40.0)
        self.assertEqual(m["imagen_limpia_pct"], 20.0)
        self.assertEqual(m["posiciones"], 2)
        self.assertEqual(m["fuentes"], 3)  # a, b, doc
        self.assertEqual(m["fuente_mas_repetida"], 2)
        self.assertEqual(m["pruebas"], 1)
        self.assertEqual(m["tipos_escena"], 3)  # foto, grafica, prueba
        self.assertEqual(m["aviso_pct"], 80.0)

    def test_targets(self):
        fallos = ma.objetivos({"verde_amarillo_pct": 80.0, "muy_oscuros_pct": 10.0})
        self.assertEqual(len(fallos), 1)
        self.assertIn("verde_amarillo_pct", fallos[0])


class TestAvisos(unittest.TestCase):
    def _p(self, escenas, D=10.0):
        return {"D": D, "fin_voz": D, "escenas": escenas, "golpes": [], "impactos": []}

    def test_big_text_share(self):
        p = self._p(
            [
                {
                    "tipo": "foto",
                    "clip": "a",
                    "t0": 0.0,
                    "t1": 10.0,
                    "rotulos": [{"en": 0.0}],
                }
            ]
        )
        self.assertEqual(c.pct_texto_grande(p), 100.0)
        self.assertTrue(any("texto grande" in a for a in c.avisos_retencion(p)))
        p = self._p(
            [
                {
                    "tipo": "foto",
                    "clip": "a",
                    "t0": 0.0,
                    "t1": 10.0,
                    "rotulos": [{"en": 0.0, "hasta": 2.0}],
                }
            ]
        )
        self.assertEqual(c.pct_texto_grande(p), 20.0)
        self.assertFalse(any("texto grande" in a for a in c.avisos_retencion(p)))

    def test_same_position_run(self):
        esc = [
            {
                "tipo": "foto",
                "t0": float(k),
                "t1": k + 1.0,
                "rotulos": [{"en": k + 0.9}],
                "pos": "sup",
            }
            for k in range(5)
        ]
        self.assertTrue(
            any("misma posición" in a for a in c.avisos_retencion(self._p(esc, 5.0)))
        )
        esc[2]["pos"] = "ter"
        self.assertFalse(
            any("misma posición" in a for a in c.avisos_retencion(self._p(esc, 5.0)))
        )


class TestSeleccion(unittest.TestCase):
    def _sb(self, **k):
        return {"imagenes": {}, "clips": {}, "escenas": [], **k}

    def test_cliche_veto(self):
        with tempfile.TemporaryDirectory() as d:
            for nombre in (
                "File:Hooded hacker.webm",
                "File:Hands typing on keyboard.webm",
            ):
                sb = self._sb(clips={"x": {"commons": nombre}})
                self.assertTrue(c.errores_seleccion(sb, Path(d)), nombre)
            sb = self._sb(clips={"x": {"commons": "File:USS Abraham Lincoln.webm"}})
            self.assertEqual(c.errores_seleccion(sb, Path(d)), [])

    def test_veto_ignores_words_ending_in_hood(self):
        with tempfile.TemporaryDirectory() as d:
            sb = self._sb(clips={"x": {"commons": "File:Aerial neighborhood.webm"}})
            self.assertEqual(c.errores_seleccion(sb, Path(d)), [])
            sb = self._sb(clips={"x": {"commons": "File:man_hooded.webm"}})
            self.assertTrue(c.errores_seleccion(sb, Path(d)))

    def test_veto_reads_pexels_slug_in_credits(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "assets" / "clips").mkdir(parents=True)
            (Path(d) / "assets" / "clips" / "creditos.json").write_text(
                '[{"archivo": "x.src", "titulo": "pexels:1", "fuente": "https://www.pexels.com/video/a-hacker-in-a-hoodie-1/"}]',
                encoding="utf-8",
            )
            self.assertTrue(
                c.errores_seleccion(self._sb(clips={"x": {"pexels": 1}}), Path(d))
            )

    def test_source_uses_and_mandatory_proof(self):
        with tempfile.TemporaryDirectory() as d:
            esc = [{"tipo": "foto", "img": "a"}] * 3
            self.assertTrue(
                any(
                    "usada 3" in e
                    for e in c.errores_seleccion(self._sb(escenas=esc), Path(d))
                )
            )
            self.assertEqual(
                c.errores_seleccion(self._sb(escenas=esc[:2]), Path(d)), []
            )
            self.assertTrue(
                any(
                    "pruebas" in e
                    for e in c.errores_seleccion(self._sb(cifras=[{}]), Path(d))
                )
            )

    def test_aspect_rules(self):
        sb = {"aspecto": "cine", "imagenes": {"x": {}}, "escenas": []}
        self.assertTrue(any("archivo real" in e for e in c._validar_aspecto(sb)))
        sb["imagenes"]["x"] = {"archivo": True}
        self.assertEqual(c._validar_aspecto(sb), [])
        sb = {"escenas": [{"tipo": "foto", "limpio": True, "rotulos": [{}]}]}
        self.assertTrue(any("limpio" in e for e in c._validar_aspecto(sb)))
        sb = {"escenas": [{"tipo": "foto", "pos": "centro"}]}
        self.assertTrue(any("pos" in e for e in c._validar_aspecto(sb)))
        self.assertEqual(c._validar_aspecto({"escenas": []}), [])

    def test_light_grade_has_no_tint_or_vignette(self):
        f = broll.filtro("ligero", False)
        self.assertNotIn("vignette", f)
        self.assertNotIn("colorbalance", f)
        self.assertIn("vignette", broll.filtro("color", False))


class TestMarkup(unittest.TestCase):
    def test_scrim_and_position_only_when_asked(self):
        s = {"rotulos": [{"texto": "A", "estilo": "mid"}]}
        self.assertNotIn(
            "tscrim", c.m_foto(s, "s0")
        )  # published storyboards: unchanged markup
        self.assertNotIn(" p-", c.m_foto(s, "s0"))
        s["pos"] = "ter"
        html = c.m_foto(s, "s0")
        self.assertIn('class="tscrim ter" id="s0-ts"', html)
        self.assertIn("p-ter", html)


if __name__ == "__main__":
    unittest.main()
