"""Tests de tools/medir_texto.py: legibilidad del texto en pantalla con casos de respuesta conocida."""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import medir_texto as T  # noqa: E402

FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def frame(t, *lineas, W=1080, H=1920):
    return {"t": t, "ancho": W, "alto": H, "lineas": [dict(l) for l in lineas]}


def linea(texto, caja=(100, 800, 900, 880), conf=0.99, contraste=12.0):
    return {"texto": texto, "conf": conf, "caja": list(caja), "contraste": contraste}


class ParecidoTest(unittest.TestCase):
    def test_subcadena_es_parecido_total(self):
        self.assertEqual(T.parecido("$8 million", "THIS JANITOR DIED WITH $8 MILLION"), 1.0)

    def test_errata_de_ocr_se_tolera(self):
        self.assertGreater(T.parecido("No hot tips", "N0 HOT TIPS"), 0.8)

    def test_texto_distinto_no_se_parece(self):
        self.assertLess(T.parecido("Reinvest it", "Sixty years later"), 0.5)

    def test_marcas_de_dorado_no_cuentan(self):
        self.assertEqual(T.parecido("*Time*", "TIME"), 1.0)


class TextosDeEscenaTest(unittest.TestCase):
    def test_recoge_textos_y_quita_contadores_e_iconos(self):
        esc = {"tipo": "titulo", "en": "6", "fondo": "nyse",
               "kicker": {"texto": "Now", "en": "6"},
               "lineas": [{"texto": "The part", "en": "6"}, {"texto": "{n} stocks", "en": "7"}, {"texto": "x"}],
               "cta": {"a": {"texto": "*Skill*"}, "o": "or just"}}
        self.assertEqual(T.textos_de_escena(esc), ["Now", "The part", "stocks", "Skill", "or just"])


class AnalizarTest(unittest.TestCase):
    ESP = [{"texto": "No big salary", "escena": 3, "t0": 6.0, "t1": 8.0}]

    def test_texto_esperado_leido(self):
        r = T.analizar([frame(6.5, linea("NO BIG SALARY"))], self.ESP)
        self.assertEqual((r["leidos_pct"], r["no_leidos"]), (100.0, []))

    def test_texto_esperado_no_leido_da_escena_y_ventana(self):
        r = T.analizar([frame(6.5, linea("RONALD READ"))], self.ESP)
        self.assertEqual(r["leidos_pct"], 0.0)
        self.assertEqual((r["no_leidos"][0]["escena"], r["no_leidos"][0]["t0"]), (3, 6.0))

    def test_texto_partido_en_dos_lineas_cuenta_como_leido(self):
        r = T.analizar([frame(6.5, linea("NO BIG"), linea("SALARY"))], self.ESP)
        self.assertEqual(r["leidos_pct"], 100.0)

    def test_fuera_de_la_ventana_no_cuenta(self):
        r = T.analizar([frame(9.0, linea("NO BIG SALARY")), frame(6.5, linea("x y"))], self.ESP)
        self.assertEqual(r["leidos_pct"], 0.0)

    def test_pequeno_dudoso_bajo_contraste_y_zona_ui(self):
        fr = [frame(1.0, linea("tiny note", caja=(100, 500, 400, 520)),           # 20 px de alto
                    linea("blurry words", conf=0.5),
                    linea("grey on grey", contraste=1.3),
                    linea("under the ui", caja=(100, 1700, 900, 1780)))]
        r = T.analizar(fr, [])
        self.assertEqual([x["texto"] for x in r["pequenos"]], ["tiny note"])
        self.assertEqual([x["texto"] for x in r["dudosos"]], ["blurry words"])
        self.assertEqual([x["texto"] for x in r["bajo_contraste"]], ["grey on grey"])
        self.assertEqual([x["texto"] for x in r["zona_ui"]], ["under the ui"])

    def test_el_mismo_rotulo_en_varios_frames_es_un_hallazgo(self):
        fr = [frame(t, linea("grey", contraste=c)) for t, c in ((1.0, 2.0), (1.5, 1.5), (2.0, 2.5))]
        r = T.analizar(fr, [])["bajo_contraste"]
        self.assertEqual((len(r), r[0]["t"], r[0]["t_fin"], r[0]["contraste"]), (1, 1.0, 2.0, 2.5))

    def test_fundido_de_entrada_no_es_fallo_si_luego_se_lee(self):
        # "THE PART" en el #7: 1,64:1 en su frame de entrada, legible después
        fr = [frame(15.0, linea("THE PART", contraste=1.64)), frame(15.5, linea("THE PART", contraste=9.0))]
        self.assertEqual(T.analizar(fr, [])["bajo_contraste"], [])

    def test_texto_incidental_del_metraje_no_se_juzga(self):
        fr = [frame(18.0, linea("Tickers were an hour behind", caja=(100, 1700, 300, 1715), contraste=2.0),
                    linea("NO HOT TIPS", caja=(100, 1700, 900, 1715), contraste=2.0))]
        r = T.analizar(fr, [], diseno=[{"texto": "No big salary.", "t0": 6, "t1": 8},
                                       {"texto": "No hot tips.", "t0": 17, "t1": 19}])
        self.assertEqual([x["texto"] for x in r["bajo_contraste"]], ["NO HOT TIPS"])
        self.assertEqual([x["texto"] for x in r["pequenos"]], ["NO HOT TIPS"])

    def test_texto_disenado_fuera_de_su_ventana_no_cuenta(self):
        # "blue chips" del periódico (t=18,5) no es el aviso ("Blue chips can cut...", t=13,9-14,8)
        d = [{"texto": "Blue chips can cut dividends or fail", "t0": 13.9, "t1": 14.8}]
        self.assertFalse(T.es_disenado('"blue chips"', 18.5, d))
        self.assertTrue(T.es_disenado("BLUE CHIPS CAN CUT", 14.2, d))

    def test_palabra_suelta_del_metraje_no_casa_con_el_guion(self):
        d = [{"texto": "This janitor died with eight million dollars.", "t0": 0, "t1": 30}]
        self.assertFalse(T.es_disenado("with", 18.0, d))
        self.assertFalse(T.es_disenado("with a sudden burst of selling.", 18.0, d))


class ContrasteTest(unittest.TestCase):
    """La razón WCAG del píxel, contra los valores teóricos (blanco/negro ~19,8; 70 sobre 55 = 1,26)."""

    def caja(self, fg, bg):
        from PIL import Image, ImageDraw, ImageFont
        im = Image.new("RGB", (1080, 400), bg)
        ImageDraw.Draw(im).text((40, 150), "EIGHT MILLION", font=ImageFont.truetype(FUENTE, 70), fill=fg)
        return T.contraste_caja(np.asarray(im), [30, 140, 700, 240])

    @unittest.skipUnless(os.path.exists(FUENTE), "sin fuente DejaVu")
    def test_razones_conocidas(self):
        self.assertAlmostEqual(self.caja((255, 255, 255), (10, 10, 10)), 19.8, delta=0.5)
        self.assertAlmostEqual(self.caja((70, 70, 70), (55, 55, 55)), 1.26, delta=0.05)
        self.assertAlmostEqual(self.caja((255, 215, 0), (255, 255, 255)), 1.40, delta=0.05)


@unittest.skipUnless(importlib.util.find_spec("rapidocr") and os.path.exists(FUENTE), "sin RapidOCR")
class OcrRealTest(unittest.TestCase):
    """Validación del instrumento con el OCR de verdad: lo grande y contrastado se lee; lo diminuto
    y lo de contraste ~1,1:1 no (medido al crearlo, 28-oct)."""

    @classmethod
    def setUpClass(cls):
        import logging
        from rapidocr import RapidOCR
        logging.getLogger("RapidOCR").setLevel(logging.ERROR)
        cls.motor = RapidOCR(params={"Global.log_level": "error", "Det.limit_type": "max", "Det.limit_side_len": 1920})

    def leer(self, size, fg, bg):
        from PIL import Image, ImageDraw, ImageFont
        im = Image.new("RGB", (1080, 1920), bg)
        ImageDraw.Draw(im).text((80, 900), "NO HOT TIPS", font=ImageFont.truetype(FUENTE, size), fill=fg)
        r = self.motor(np.asarray(im))
        return " ".join(r.txts) if r.txts else ""

    def test_grande_y_contrastado_se_lee(self):
        self.assertEqual(T.parecido("No hot tips", self.leer(60, (255, 255, 255), (10, 10, 10))), 1.0)

    def test_diminuto_no_se_lee(self):
        self.assertLess(T.parecido("No hot tips", self.leer(16, (255, 255, 255), (10, 10, 10))), 0.8)

    def test_contraste_casi_nulo_no_se_lee(self):
        self.assertLess(T.parecido("No hot tips", self.leer(60, (60, 60, 60), (55, 55, 55))), 0.8)


if __name__ == "__main__":
    unittest.main()
