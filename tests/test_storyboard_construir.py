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
        self.assertEqual([f["img"] for f in p["fotos"] if not f["id"].endswith("a")], ["foto1"])
        self.assertEqual(p["fotos"][0]["opacidad"], 1)
        self.assertEqual(p["subtitulos"], [6, 8])                       # palabras de la frase 1
        self.assertIn("salary", p["escenas"][1]["texto_visible"])       # para no duplicar subtítulo

    def test_aviso_de_hueco_estatico(self):
        # CTA con un solo elemento durante una frase larga (el fallo de Grace Groner): aviso
        W2 = [{"text": f"w{i}", "start": i * 1.0, "end": i * 1.0 + 0.5} for i in range(8)]
        W2[3]["text"], W2[7]["text"] = "w3.", "w7?"
        d = {"escenas": [{"tipo": "foto", "en": "0", "img": "f"},
                         {"tipo": "cta", "en": "1", "a": {"texto": "Hold", "en": "1"}, "b": {"texto": "Sell", "en": "1:w7"}}],
             "imagenes": {"f": {}}}
        avisos = c.huecos_estaticos(c.plan(d, W2))
        self.assertEqual(len(avisos), 1)
        self.assertIn("escena 1 (cta)", avisos[0])
        self.assertEqual(c.huecos_estaticos(c.plan(sb(), W)), [])     # el bueno no avisa

    def test_enfasis_y_escape(self):
        self.assertEqual(c.txt("*3* <b>"), '<span class="gold">3</span> &lt;b&gt;')


class RetencionTest(unittest.TestCase):
    def test_gancho_y_regancho(self):
        p = c.plan(sb(), W)
        av = c.avisos_retencion(p)
        self.assertTrue(any("foto fija" in a for a in av))                 # foto sin clip
        self.assertFalse(any("re-gancho" in a for a in av))                # vídeo de 5 s
        p["fin_voz"] = 30.0
        self.assertTrue(any("sin re-gancho" in a for a in c.avisos_retencion(p)))
        p["escenas"][0]["tipo"] = "titulo"
        self.assertTrue(any("gancho sin imagen" in a for a in c.avisos_retencion(p)))


class FondoAutoTest(unittest.TestCase):
    """Ninguna escena de texto sobre verde vacío: fondo automático desenfocado del propio proyecto."""

    def test_escenas_de_texto_reciben_fondo_desenfocado(self):
        d = sb(imagenes={"foto1": {"commons": "File:X.jpg"}, "foto2": {"commons": "File:Y.jpg"}})
        p = c.plan(d, W)
        auto = [f for f in p["fotos"] if f["id"].endswith("a")]
        self.assertEqual([f["id"] for f in auto], ["ph1a", "ph2a"])          # lista y cta; la foto no
        self.assertTrue(all(f["opacidad"] == c.OPACIDAD_AUTO and f["archivo"].endswith("-desenfoque") for f in auto))
        self.assertEqual(auto[0]["img"], "foto2")                         # evita la imagen de la foto vecina
        self.assertIn('src="assets/t/foto2-desenfoque.jpg"', c._capa_html(auto[0], 0))

    def test_se_puede_desactivar(self):
        self.assertFalse(any(f["id"].endswith("a") for f in c.plan(sb(fondos_auto=False), W)["fotos"]))
        d = sb(); d["escenas"][1]["fondo"] = False
        self.assertNotIn("ph1a", [f["id"] for f in c.plan(d, W)["fotos"]])

    def test_no_altera_el_mov_de_las_fotos(self):
        mov = lambda p: [f["mov"] for f in p["fotos"] if not f["id"].endswith("a")]
        self.assertEqual(mov(c.plan(sb(), W)), mov(c.plan(sb(fondos_auto=False), W)))


class BrollTest(unittest.TestCase):
    """Clips de vídeo en `foto`/`fondo`: validación, plan y el HTML que exige el lint de HyperFrames."""

    def _sb(self):
        d = sb(clips={"parque": {"commons": "File:P.webm", "desde": 4}})
        d["escenas"][0].pop("img")
        d["escenas"][0]["clip"] = "parque"
        d["escenas"][1]["fondo"] = {"clip": "parque", "opacidad": 0.3}
        return d

    def test_valida_clips(self):
        self.assertEqual(c.validar(self._sb(), W), [])
        d = self._sb(); d["escenas"][0]["clip"] = "nada"
        self.assertTrue(any("clip 'nada' no declarado" in e for e in c.validar(d, W)))
        d = self._sb(); d["escenas"][0]["img"] = "foto1"
        self.assertTrue(any("`img` O `clip`" in e for e in c.validar(d, W)))
        d = self._sb(); d["clips"]["parque"] = {"desde": 1}
        self.assertTrue(any("declara `commons`" in e for e in c.validar(d, W)))

    def test_plan_y_html(self):
        p = c.plan(self._sb(), W)
        v = [f for f in p["fotos"] if f.get("video")]
        self.assertEqual(len(v), 2)
        self.assertEqual(v[0]["desde"], 4.0)
        dur = round((v[0]["t1"] - v[0]["t0"]) * 100)
        self.assertEqual(v[0]["src"], f"parque-4-{dur}.mp4")             # archivo por duración exacta
        self.assertNotEqual(v[0]["src"], v[1]["src"])
        h = c._capa_html(v[0], 0)
        # el <video> lleva el tiempo; su contenedor NO (lint video_nested_in_timed_element)
        contenedor = h.split("<video")[0]
        self.assertNotIn("data-start", contenedor)
        self.assertIn('muted playsinline', h)
        self.assertNotIn("crossorigin", h)
        self.assertIn(f'id="{v[0]["id"]}-sh" class="clip ph"', h)       # sombra con su propia ventana

    def test_lut_1d_es_la_rampa_de_marca(self):
        import numpy as np
        from duotono import lut_1d, rampa, OSCURO, LUZ
        filas = lut_1d().splitlines()
        self.assertEqual(filas[0], "LUT_1D_SIZE 256")
        rgb = np.array([[float(x) for x in f.split()] for f in filas[3:]]) * 255
        self.assertTrue(np.allclose(rgb[0], OSCURO, atol=0.01) and np.allclose(rgb[-1], LUZ, atol=0.01))
        self.assertTrue(np.allclose(rgb[128], rampa(np.array([128 / 255], dtype=np.float32))[0], atol=0.01))
        estirada = np.array([[float(x) for x in f.split()] for f in lut_1d(bajo=0.2, alto=0.8).splitlines()[3:]])
        self.assertTrue(np.allclose(estirada[:51], estirada[0]))           # por debajo de `bajo` = negro de marca
        with self.assertRaises(ValueError):
            lut_1d(bajo=0.5, alto=0.5)

    def test_eleccion_de_archivo(self):
        import broll
        self.assertEqual(broll.mejor_derivado([{"transcodekey": "480p.vp9.webm", "src": "a"},
                                               {"transcodekey": "1080p.vp9.webm", "src": "b"}])["src"], "b")
        self.assertIsNone(broll.mejor_derivado([{"transcodekey": "240p.vp9.webm", "src": "x"}]))
        fs = [{"file_type": "video/mp4", "width": 2160, "height": 3840, "link": "4k"},
              {"file_type": "video/mp4", "width": 1080, "height": 1920, "link": "hd"},
              {"file_type": "video/mp4", "width": 720, "height": 1280, "link": "sd"}]
        self.assertEqual(broll.mejor_archivo_pexels(fs)["link"], "hd")   # cubre 1920 sin pasarse
        self.assertEqual(broll.mejor_archivo_pexels(fs[2:])["link"], "sd")
        self.assertIsNone(broll.mejor_archivo_pexels([]))

    def test_ficha_pexels(self):
        """Forma documentada de GET /videos/videos/:id -> ficha de créditos con la licencia de Pexels."""
        import broll
        v = {"id": 3843454, "width": 1080, "height": 1920, "duration": 12, "url": "https://www.pexels.com/video/x-3843454/",
             "user": {"name": "Ana", "url": "https://www.pexels.com/@ana"},
             "video_files": [{"quality": "hd", "file_type": "video/mp4", "width": 1080, "height": 1920,
                              "link": "https://videos.pexels.com/video-files/3843454/hd.mp4"}]}
        f = broll._ficha_pexels(v)
        self.assertEqual((f["clase"], f["autor"], f["titulo"]), ("pexels", "Ana", "pexels:3843454"))
        self.assertTrue(f["src"].endswith("hd.mp4"))
        self.assertIn("Footage:\n- pexels:3843454 — Ana — Pexels License", broll.texto_creditos([f]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
