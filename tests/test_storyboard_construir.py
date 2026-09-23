"""Tests del constructor del motor v2 (storyboard.json -> plan con tiempos).

`validar` es la puerta que un storyboard escrito por un LLM tiene que pasar ANTES del render:
cada regla aquí es un error que costaría 6 minutos de render (o un vídeo publicado mal).
"""
from __future__ import annotations
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video-v2", "motor"))

import construir as c  # noqa: E402

W = [{"text": x, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, x in enumerate(
    "He died with eight million dollars. No big salary. Team skill, or team time?".split())]

BASE = {
    "imagenes": {"foto1": {"commons": "File:X.jpg"}},
    "aviso": {"lineas": ["Not financial advice"]},
    "cifras": [{"dato": "$8M", "fuente": "https://example.org"}],
    "subtitulos": ["1", "1"],
    "escenas": [
        {"tipo": "foto", "en": "0", "img": "foto1", "kicker": {"texto": "Eight million", "en": "0:eight"}},
        {"tipo": "lista", "en": "1", "icono": "x", "items": [{"texto": "No big salary", "en": "1"}]},
        {"tipo": "cta", "en": "2", "a": {"texto": "Skill", "en": "2:skill"}, "b": {"texto": "Time", "en": "2:time"},
         "botones": [{"texto": "Team skill", "en": "2:team"}, {"texto": "Team time", "en": "2:team#2"}]},
    ],
}


def sb(**cambios):
    d = copy.deepcopy(BASE)
    d.update(cambios)
    return d


class ValidarTest(unittest.TestCase):
    def test_storyboard_bueno_no_da_errores(self):
        self.assertEqual(c.validar(sb(), W), [])

    def test_tipo_desconocido(self):
        d = sb(); d["escenas"][1]["tipo"] = "carrusel"
        self.assertTrue(any("no existe" in e for e in c.validar(d, W)))

    def test_imagen_no_declarada(self):
        d = sb(); d["escenas"][0]["img"] = "otra"
        self.assertTrue(any("'otra' no declarada" in e for e in c.validar(d, W)))

    def test_escenas_fuera_de_orden(self):
        d = sb(); d["escenas"][1]["en"] = "0"          # empata con la escena 0
        self.assertTrue(any("antes o a la vez" in e for e in c.validar(d, W)))

    def test_cifra_sin_fuente_y_sin_aviso(self):
        d = sb(cifras=[{"dato": "$8M"}], aviso={})
        errs = c.validar(d, W)
        self.assertTrue(any("sin `fuente`" in e for e in errs))
        self.assertTrue(any("aviso YMYL" in e for e in errs))

    def test_un_solo_contador3d(self):
        d = sb()
        d["escenas"][1:1] = [{"tipo": "contador3d", "en": "0:million", "valor": 1, "llega": "0:dollars"},
                             {"tipo": "contador3d", "en": "0:dollars", "valor": 1, "llega": "0:dollars$"}]
        self.assertTrue(any("más de un `contador3d`" in e for e in c.validar(d, W)))

    def test_anclas_sueltas_tambien_se_validan(self):
        d = sb(); d["aviso"]["ventanas"] = [["0", "9"]]
        self.assertTrue(any("solo tiene 3 frases" in e for e in c.validar(d, W)))


class PlanTest(unittest.TestCase):
    def test_ventanas_contiguas_y_final(self):
        p = c.plan(sb(), W)
        e = p["escenas"]
        self.assertEqual(e[0]["t0"], 0.0)
        self.assertAlmostEqual(e[1]["t0"], 3.0 - c.PRE)                 # "No" arranca en 3.0
        for a, b in zip(e, e[1:]):
            self.assertAlmostEqual(a["t1"], b["t0"] + 0.02)             # solape mínimo, sin huecos
        self.assertEqual(e[-1]["t1"], p["D"])
        self.assertEqual(p["D"], round(W[-1]["end"] + 3.0, 2))          # cola por defecto 3 s

    def test_fotos_subtitulos_y_texto_visible(self):
        p = c.plan(sb(), W)
        self.assertEqual([f["img"] for f in p["fotos"]], ["foto1"])
        self.assertEqual(p["fotos"][0]["opacidad"], 1)
        self.assertEqual(p["subtitulos"], [6, 8])                       # palabras de la frase 1
        self.assertIn("salary", p["escenas"][1]["texto_visible"])       # para no duplicar subtítulo

    def test_enfasis_y_escape(self):
        self.assertEqual(c.txt("*3* <b>"), '<span class="gold">3</span> &lt;b&gt;')


if __name__ == "__main__":
    unittest.main(verbosity=2)
