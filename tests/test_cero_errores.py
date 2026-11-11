"""Each defect class of docs/CERO-ERRORES.md, reproduced in a fixture before its gate is trusted.

audio/toma_401k.json: Whisper on a real Kokoro take of "401k" over the music bed. audio/mezcla_v2.json: Whisper on
the published average-401k. Frames are synthetic arrays; OCR boxes are copied from the real renders named below.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar
from unittest import mock

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]

import construir as c
import critico
import juicio_lista
import medir_cuadros as mc
import medir_guion_audio as mga
import puertas
import puertas_final as pf
import social
import trazabilidad as tz

FIX = Path(__file__).parent / "fixtures" / "average401k"
_R = json.loads(
    (RAIZ / "video-v2" / "motor" / "rubrica.json").read_text(encoding="utf-8")
)
U = {k: v for x in _R["criterios"].values() for k, v in x.items() if k != "nombre"}
FALLO = (critico.fallo, critico.escena_en)


def cargar(v: str) -> tuple[dict, list[dict]]:
    return (
        json.loads((FIX / v / "storyboard.json").read_text(encoding="utf-8")),
        json.loads((FIX / v / "words.json").read_text(encoding="utf-8")),
    )


def plan_de(v: str) -> tuple[dict, dict]:
    sb, w = cargar(v)
    return sb, c.plan(sb, w)


def oidas(n: str) -> list[dict]:
    return json.loads((FIX / "audio" / n).read_text(encoding="utf-8"))


def guion(sb: dict) -> str:
    return " ".join(g["texto"] for g in sb["guion"])


def hablado(t: str) -> list[dict]:
    return [{"word": w, "start": 1.0, "end": 1.2} for w in t.split()]


BIEN = "you pay nineteen point seven percent on your card today"


class AudioContraGuionTest(unittest.TestCase):
    def test_toma_real_de_401k_es_grave(self):
        sb, _ = cargar("v2")
        r = mga.comparar(guion(sb), oidas("toma_401k.json"))
        self.assertEqual([d["oido"] for d in r["grave"]], ["hundred", "hundred"])

    def test_mezcla_publicada_no_es_grave(self):
        sb, _ = cargar("v2")
        self.assertEqual(mga.comparar(guion(sb), oidas("mezcla_v2.json"))["grave"], [])

    def test_cifra_cambiada_es_grave_y_mismo_valor_no(self):
        r = mga.comparar(
            "holds three hundred thirty thousand",
            hablado("holds three hundred thirteen thousand"),
        )
        self.assertTrue(r["grave"])
        self.assertEqual(
            mga.comparar("the thirty-six hours", hablado("the 36 hours"))["grave"], []
        )

    def test_frase_perdida_es_grave(self):
        self.assertTrue(
            mga.comparar("the fed held rates again this week", hablado("the fed week"))[
                "grave"
            ]
        )

    def test_mismo_sonido_no_salta(self):
        r = mga.comparar("this is a binance heist", hablado("this is a by nance heist"))
        self.assertEqual((r["grave"], r["leve"]), ([], []))

    def _revisar(self, mezcla: str, limpia: str, db: float) -> list[dict]:
        sb = {"guion": [{"texto": BIEN}]}
        with mock.patch.object(
            pf.mga, "transcribir", side_effect=[hablado(mezcla), hablado(limpia)]
        ):
            return pf.revisar_audio(
                sb,
                Path("m.mp4"),
                Path("v.mp3"),
                {"ventanas": [{"t": 1.0, "db": db}]},
                [(0, 9)],
                U,
                *FALLO,
            )

    def test_mal_tambien_en_la_voz_limpia_bloquea_como_toma(self):
        mal = "you pay ninety point seven percent on your card today"
        f = self._revisar(mal, mal, 20.0)
        self.assertEqual([(x["criterio"], x["severidad"]) for x in f], [("A1", "alta")])

    def test_solo_en_la_mezcla_con_voz_tapada_bloquea_como_mezcla(self):
        f = self._revisar("you pay on your card today", BIEN, 3.0)
        self.assertEqual([(x["criterio"], x["severidad"]) for x in f], [("M1", "alta")])

    def test_solo_en_la_mezcla_con_voz_clara_no_bloquea(self):
        """fed-vs-card: Whisper drops the first 1.7 s of the mix, and there the voice measures 22 dB over the music."""
        f = self._revisar("you pay on your card today", BIEN, 22.0)
        self.assertEqual([x["severidad"] for x in f], ["media"])

    def test_palabra_perdida_con_voz_bajo_el_fondo_bloquea(self):
        """A word gone from the mix only, where the voice measures under the background."""
        f = self._revisar(
            "you pay nineteen point seven percent on card today", BIEN, -2.6
        )
        self.assertEqual([(x["criterio"], x["severidad"]) for x in f], [("M1", "alta")])


class G2PTest(unittest.TestCase):
    D: ClassVar[dict] = {
        "desconocidas": {"Roth": "ɹˈɑθ"},
        "siglas": {"AWS": "ˈɔz", "IOU": "ˌIˌOjˈu", "US": "jˌuˈɛs"},
    }

    def test_desconocida_y_sigla_leida_como_palabra_bloquean(self):
        e = " ".join(puertas.filtrar_g2p(self.D, []))
        self.assertIn("Roth", e)
        self.assertIn("AWS", e)
        self.assertNotIn("IOU", e)
        self.assertNotIn('"US"', e)

    def test_escuchada_y_aceptada_pasa(self):
        self.assertEqual(puertas.filtrar_g2p(self.D, ["Roth", "AWS"]), [])


class TrazabilidadTest(unittest.TestCase):
    def test_lectura_de_cifras(self):
        def v(t):
            return [round(x["valor"], 2) for x in tz.de_palabras(t)]

        self.assertEqual(v("nineteen point seven percent"), [19.7])
        self.assertEqual(v("one point three trillion dollars"), [1.3e12])
        self.assertEqual(
            v("in twenty twenty five, three hundred thirty thousand"), [2025, 330000]
        )
        self.assertEqual(v("in april seventeen twenty, he sold"), [1720])
        self.assertEqual(v("one of three savers, four-oh-one-k"), [])
        self.assertEqual(
            [
                x["valor"]
                for x in tz.de_digitos("$46.0B, +0.25%, 401(k), 3 in 4, $330,186")
            ],
            [46e9, 0.25, 330186],
        )

    def test_redondeo_vale_y_otra_cifra_no(self):
        sb = {
            "cifras": [{"dato": "average $330,186"}],
            "guion": [
                {"id": "a", "texto": "about three hundred thirty thousand dollars"}
            ],
        }
        self.assertEqual(tz.sin_fuente(sb), [])
        sb["guion"][0]["texto"] = "about three hundred fifty thousand dollars"
        self.assertIn("three hundred fifty thousand", tz.sin_fuente(sb)[0])

    def test_cifra_en_pantalla_sin_fuente(self):
        sb = {
            "cifras": [{"dato": "$330,186"}],
            "escenas": [{"tipo": "titulo", "lineas": [{"texto": "$999,000"}]}],
        }
        self.assertIn("escena 0", tz.sin_fuente(sb)[0])

    def test_publicada_pasa_y_sin_cifras_no(self):
        sb, _ = cargar("v2")
        self.assertEqual(tz.sin_fuente(sb), [])
        self.assertTrue(tz.sin_fuente({**sb, "cifras": []}))


class PlanTest(unittest.TestCase):
    def test_contador_antes_de_la_voz(self):
        _, p1 = plan_de("v1")
        _, p2 = plan_de("v2")
        self.assertIn("escena 5", " ".join(puertas.contador_adelantado(p1)))
        self.assertEqual(puertas.contador_adelantado(p2), [])

    def test_documento_demasiado_breve(self):
        sb1, p1 = plan_de("v1")
        sb2, p2 = plan_de("v2")
        self.assertEqual(len(puertas.prueba_breve(sb1, p1)), 1)
        self.assertEqual(puertas.prueba_breve(sb2, p2), [])

    def test_forma_hablada_escrita(self):
        self.assertTrue(
            puertas.forma_hablada_escrita(
                {"publicacion": {"titulo": "The four-oh-one-k myth"}}
            )
        )
        self.assertEqual(
            puertas.forma_hablada_escrita(
                {"publicacion": {"titulo": "The 401(k) myth"}}
            ),
            [],
        )

    def test_cifra_de_publicacion_sin_fuente(self):
        sb = {
            "cifras": [{"dato": "$330,186"}],
            "publicacion": {"descripcion": "It is $330,186 or $999,000"},
        }
        self.assertIn("999,000", " ".join(puertas.publicacion(sb)))

    def test_historia_cortada_en_medio_de_frase(self):
        w = [
            {"text": "One", "start": 0.0, "end": 0.5},
            {"text": "two.", "start": 0.6, "end": 1.0},
            {"text": "Three", "start": 1.2, "end": 1.5},
            {"text": "four.", "start": 1.6, "end": 2.0},
        ]
        sb = {"social": {"historia": {"hasta": "0$"}}, "guion": []}
        with mock.patch("anclas.t", return_value=1.0):
            self.assertEqual(puertas.historia_corte(sb, w), [])
        with mock.patch("anclas.t", return_value=1.5):
            self.assertIn("sin terminar", puertas.historia_corte(sb, w)[0])
        with mock.patch("anclas.t", return_value=14.0):
            self.assertIn("14 s", puertas.historia_corte(sb, w)[0])

    def test_tema_con_el_asunto_descoloca_la_maqueta(self):
        """Real defect in both versions of average-401k: every frame 300 px lower, brand cut at the edge."""
        for v in ("v1", "v2"):
            self.assertEqual(len(puertas.tema_valido(cargar(v)[0])), 1)
        self.assertEqual(
            puertas.tema_valido({"tema": "editorial", "aspecto": "cine"}), []
        )
        self.assertTrue(puertas.tema_valido({"aspecto": "cine"}))

    def test_v2_solo_falla_por_el_tema(self):
        sb, p = plan_de("v2")
        self.assertEqual(puertas.errores(sb, p), puertas.tema_valido(sb))


def _video(n: int = 50, luma: int = 120) -> np.ndarray:
    """Moving noise: a healthy video for every frame measure."""
    r = np.random.default_rng(1)
    return r.integers(
        max(0, luma - 80), min(255, luma + 80), (n, 192, 108), dtype=np.uint8
    )


class CuadrosTest(unittest.TestCase):
    def test_video_sano_no_salta(self):
        fr = _video()
        self.assertEqual(mc.negros(fr, U) + mc.congelados(fr, U) + mc.planos(fr, U), [])
        self.assertIsNone(mc.banda_vacia(fr, U))

    def test_negro(self):
        fr = _video()
        fr[10:15] = 2
        self.assertEqual(mc.negros(fr, U), [{"t": 2.0, "t_fin": 3.0}])

    def test_texto_sobre_negro_no_es_negro(self):
        fr = _video()
        fr[10:15] = 2
        fr[10:15, 90:96, 10:90] = 240
        self.assertEqual(mc.negros(fr, U), [])

    def test_congelado(self):
        fr = _video()
        fr[10:20] = fr[10]
        self.assertEqual(mc.congelados(fr, U), [{"t": 2.2, "t_fin": 4.0}])

    def test_gancho_oscuro(self):
        """binance-heist: luma 16, contrast 17; the next darkest of 11 videos, 41.9 and 34.3."""
        oscuro = _video(luma=20) // 3
        self.assertLess(mc.gancho(oscuro, U)["luma"], U["gancho_luma_min"])
        f = pf.revisar_cuadros(oscuro, [], [(0, 9)], U, *FALLO)
        self.assertIn("gancho", " ".join(x["detalle"] for x in f))

    def test_pantalla_vacia_sin_texto_y_con_texto(self):
        fr = _video()
        fr[10:15] = 40 + (fr[10:15] % 9)
        self.assertEqual(mc.planos(fr, U), [{"t": 2.0, "t_fin": 3.0}])
        marca = {
            "t": 2.5,
            "lineas": [{"texto": "NET WORTHY", "caja": [0, 421, 324, 457]}],
        }
        rotulo = {
            "t": 2.5,
            "lineas": [{"texto": "THE MIDDLE", "caja": [0, 400, 800, 500]}],
        }
        f = pf.revisar_cuadros(fr, [marca], [(0, 9)], U, *FALLO)
        self.assertIn("vacía", " ".join(x["detalle"] for x in f))
        f = pf.revisar_cuadros(fr, [rotulo], [(0, 9)], U, *FALLO)
        self.assertNotIn("vacía", " ".join(x["detalle"] for x in f))

    def test_franja_vacia_de_maqueta_descolocada(self):
        fr = _video()
        fr[:, :15, :] = 30
        self.assertEqual(mc.banda_vacia(fr, U), {"lado": "arriba", "pct": 100})


def _f(t, *lineas):
    return {
        "t": t,
        "ancho": 1080,
        "alto": 1920,
        "lineas": [{"texto": x, "caja": b} for x, b in lineas],
    }


def todo(texto, t):
    return True


class CajasTest(unittest.TestCase):
    CHOQUE = (("MEDIAN", [100, 800, 900, 900]), ("AVERAGE", [120, 810, 880, 905]))

    def test_dos_rotulos_en_el_mismo_sitio_chocan(self):
        self.assertEqual(
            len(mc.colisiones([_f(t, *self.CHOQUE) for t in (20.0, 20.5)], todo, U)), 1
        )

    def test_titulo_sobre_numero_grande_no_choca(self):
        """average-401k 17.5 s: real boxes, overlapping only because OCR pads big text."""
        par = (
            ("THE EXACT MIDDLE", [167, 819, 916, 949]),
            ("$103,202", [108, 911, 968, 1228]),
        )
        self.assertEqual(
            mc.colisiones([_f(t, *par) for t in (17.5, 18.0)], todo, U), []
        )

    def test_un_solo_cuadro_es_un_fundido(self):
        self.assertEqual(mc.colisiones([_f(20.0, *self.CHOQUE)], todo, U), [])

    def test_texto_contra_el_borde(self):
        fs = [_f(t, ("$1.08", [0, 500, 400, 700])) for t in (3.5, 4.0)]
        self.assertEqual(mc.cortados(fs, todo, U)[0]["texto"], "$1.08")
        fs = [_f(t, ("$1.08", [100, 500, 400, 700])) for t in (3.5, 4.0)]
        self.assertEqual(mc.cortados(fs, todo, U), [])

    def test_subtitulo_sobre_el_texto_del_documento(self):
        def es(texto, t):
            return texto == "drag that figure"

        sub = ("drag that figure", [100, 1270, 900, 1350])
        fs = [
            _f(t, sub, ("share of financial assets", [90, 1280, 950, 1340]))
            for t in (14.5, 15.0)
        ]
        self.assertEqual(len(mc.subtitulo_sobre_documento(fs, es, U)), 1)
        fs = [
            _f(t, sub, ("share of financial assets", [90, 650, 950, 720]))
            for t in (14.5, 15.0)
        ]
        self.assertEqual(mc.subtitulo_sobre_documento(fs, es, U), [])


class PausasTest(unittest.TestCase):
    def test_coma_no_bloquea_y_sin_puntuacion_si(self):
        rv = {
            "pausas": [
                {"tipo": "dentro", "dur": 0.46, "t": 8.1, "tras": "savers,"},
                {"tipo": "dentro", "dur": 1.08, "t": 9.0, "tras": "lines"},
            ]
        }
        f = pf.pausas_sin_puntuacion(rv, [(0, 9)], U, *FALLO)
        self.assertEqual(len(f), 1)
        self.assertIn("lines", f[0]["detalle"])


class SocialTest(unittest.TestCase):
    def test_titulo_no_leido_y_texto_al_borde(self):
        car = [{"titulo": "*Below* average", "texto": "You can be under the average"}]
        lectura = {
            "ancho": 1080,
            "alto": 1350,
            "lineas": [
                {"texto": "You can be under the average", "caja": [0, 900, 700, 960]}
            ],
        }
        with mock.patch.object(mc, "ocr_imagen", return_value=lectura):
            e = social.revisar_activos(car, [Path("01.jpg")], None)
        self.assertEqual(len(e), 2)
        self.assertIn("título", e[0])
        self.assertIn("borde", e[1])

    def test_diapositiva_correcta_pasa(self):
        car = [{"titulo": "*Below* average", "texto": "x"}]
        lectura = {
            "ancho": 1080,
            "alto": 1350,
            "lineas": [{"texto": "Below average", "caja": [100, 400, 900, 500]}],
        }
        with mock.patch.object(mc, "ocr_imagen", return_value=lectura):
            self.assertEqual(social.revisar_activos(car, [Path("01.jpg")], None), [])

    def test_historia_en_negro(self):
        fr = _video(60)
        fr[5:15] = 2
        with mock.patch.object(mc, "leer_grises", return_value=fr):
            self.assertIn("negro", social.revisar_activos([], [], Path("h.mp4"))[0])


class JuicioTest(unittest.TestCase):
    LISTA: ClassVar[dict] = {
        "escenas": [{"escena": 0}, {"escena": 1}],
        "cifras": [{"i": 0, "dato": "x"}],
    }

    @staticmethod
    def _rev(**kw):
        e = {"imagen_es_la_palabra": True, "texto_completo": True}
        return {
            "fallos": [],
            "revision": {
                "escenas": [{"escena": 0, **e}, {"escena": 1, **e, **kw}],
                "cifras": [{"i": 0, "coincide_con_fuente": True}],
            },
        }

    def test_pase_vago_no_vale(self):
        self.assertEqual(len(juicio_lista.faltan({"fallos": []}, self.LISTA)), 5)

    def test_completo_vale(self):
        self.assertEqual(juicio_lista.faltan(self._rev(), self.LISTA), [])

    def test_un_no_exige_su_fallo(self):
        j = self._rev(imagen_es_la_palabra=False)
        self.assertEqual(len(juicio_lista.faltan(j, self.LISTA)), 1)
        j["fallos"] = [{"escena": 1, "detalle": "plano viejo"}]
        self.assertEqual(juicio_lista.faltan(j, self.LISTA), [])

    def test_cifra_sin_comprobar_no_vale(self):
        j = self._rev()
        j["revision"]["cifras"] = []
        self.assertIn("cifra 0", juicio_lista.faltan(j, self.LISTA)[0])

    def test_checklist_del_plan_real(self):
        sb, p = plan_de("v2")
        lista = juicio_lista.checklist(sb, p)
        self.assertEqual(len(lista["escenas"]), len(p["escenas"]))
        self.assertEqual(len(lista["cifras"]), len(sb["cifras"]))

    def test_juicio_de_exige_el_checklist(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "checklist.json").write_text(json.dumps(self.LISTA), encoding="utf-8")
            (d / "juicio.json").write_text(
                json.dumps({"mp4_sha256": "a", "fallos": []}), encoding="utf-8"
            )
            self.assertFalse(critico.juicio_de(d, "a"))
            (d / "juicio.json").write_text(
                json.dumps({"mp4_sha256": "a", **self._rev()}), encoding="utf-8"
            )
            self.assertTrue(critico.juicio_de(d, "a"))
            self.assertFalse(critico.juicio_de(d, "b"))


if __name__ == "__main__":
    unittest.main()
