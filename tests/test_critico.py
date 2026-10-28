"""Tests de video-v2/motor/critico.py: revisiones puras, anclas inversas, parches y juicio."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "video-v2" / "motor"))
sys.path.insert(0, str(RAIZ / "tools"))

import anclas  # noqa: E402
import critico as C  # noqa: E402

RUB = json.loads((RAIZ / "video-v2" / "motor" / "rubrica.json").read_text(encoding="utf-8"))
U = {k: v for c in RUB["criterios"].values() for k, v in c.items() if k != "nombre"}


def w(text, s, e):
    return {"text": text, "start": s, "end": e}


WORDS = [w("This", 0.4, 0.42), w("janitor", 0.42, 0.8), w("died", 0.8, 1.1), w("rich.", 1.1, 1.6),
         w("He", 2.0, 2.2), w("bought", 2.2, 2.6), w("stocks", 2.6, 3.0), w("and", 3.0, 3.2),
         w("bought", 3.2, 3.6), w("more.", 3.6, 4.0)]
VS = [(0.0, 1.9), (1.9, 4.5)]


class AnclaInversaTest(unittest.TestCase):
    def test_la_ancla_resuelve_a_la_palabra_mas_cercana(self):
        a = C.ancla_de(WORDS, 2.25)
        self.assertEqual(a, "1:bought")
        self.assertAlmostEqual(anclas.t(WORDS, a), 2.2)

    def test_segunda_aparicion_lleva_numero(self):
        a = C.ancla_de(WORDS, 3.25)
        self.assertEqual(a, "1:bought#2")
        self.assertAlmostEqual(anclas.t(WORDS, a), 3.2)

    def test_salta_palabras_no_medidas_y_respeta_el_rango(self):
        self.assertNotEqual(C.ancla_de(WORDS, 0.4), "0:this")       # "This" dura 0,02 s
        self.assertIsNone(C.ancla_de(WORDS, 1.0, desde=5, hasta=6))


class RevisionesTest(unittest.TestCase):
    def test_ritmo_quieto_da_golpe_en_medio_del_tramo(self):
        f = C.revisar_ritmo({"max_s": 3.0, "desde_s": 1.5}, WORDS, VS, U)
        self.assertEqual((f[0]["criterio"], f[0]["t"], f[0]["t_fin"]), ("R1", 1.5, 4.5))
        self.assertEqual(f[0]["parche"]["op"], "golpe")
        self.assertTrue(1.8 <= anclas.t(WORDS, f[0]["parche"]["ancla"]) <= 4.2)

    def test_ritmo_dentro_del_limite_no_es_fallo(self):
        self.assertEqual(C.revisar_ritmo({"max_s": 1.6, "desde_s": 0}, WORDS, VS, U), [])

    def test_hueco_sin_regancho(self):
        largo = [w(f"w{i}{'.' if i % 5 == 4 else ''}", i * 0.5, i * 0.5 + 0.4) for i in range(60)]
        f = C.revisar_reganchos({"golpes": [2.0], "fin_voz": 29.9}, largo, U)
        self.assertEqual(len(f), 1)
        self.assertEqual((f[0]["t"], f[0]["t_fin"]), (2.0, 29.9))
        self.assertEqual(f[0]["parche"]["op"], "golpe")

    def test_gancho_sin_cifra_ni_texto(self):
        f = C.revisar_gancho(WORDS, [{"t": 0.0, "lineas": []}, {"t": 0.5, "lineas": []}], U)
        crits = sorted(x["detalle"][:20] for x in f)
        self.assertEqual(len(f), 2)                                  # sin texto antes de 0,8 s + sin cifra
        self.assertTrue(any("cifra" in x["detalle"] for x in f), crits)

    def test_mezcla_culpa_al_efecto_que_suena_y_no_a_la_musica(self):
        rm = {"pct_tapada": 50.0, "n_ventanas": 4, "mediana_db": 8, "ventanas": [
            {"t": 0.0, "db": 20}, {"t": 0.5, "db": 2.0}, {"t": 1.0, "db": 4.0}, {"t": 1.5, "db": 20}]}
        ev = [{"t0": 0.6, "t1": 0.9, "fuente": "sonidos[0] caja", "sonido": 0, "vol": 0.6}]
        f = C.revisar_mezcla(rm, None, 0.5, VS, U, ev)
        por = {x["detalle"].split(" tapa")[0]: x for x in f}
        self.assertEqual(set(por), {"sonidos[0] caja", "música"})
        self.assertEqual(por["sonidos[0] caja"]["parche"]["op"], "sfx_vol")
        self.assertLess(por["sonidos[0] caja"]["parche"]["valor"], 0.6)
        self.assertEqual(por["música"]["parche"]["op"], "musica_volumen")
        self.assertLess(por["música"]["parche"]["valor"], 0.5)

    def test_con_dos_efectos_a_la_vez_culpa_al_que_mas_suena(self):
        import numpy as np
        import soundfile as sf
        with tempfile.TemporaryDirectory() as d:
            sr = 16000
            t = np.arange(sr) / sr
            sf.write(f"{d}/flojo.wav", 0.01 * np.sin(2 * np.pi * 1000 * t), sr)
            sf.write(f"{d}/fuerte.wav", 0.5 * np.sin(2 * np.pi * 1000 * t), sr)
            ev = [{"t0": 0.0, "t1": 1.0, "fuente": "flojo", "archivo": f"{d}/flojo.wav", "vol": 0.6},
                  {"t0": 0.2, "t1": 1.2, "fuente": "fuerte", "archivo": f"{d}/fuerte.wav", "vol": 0.38}]
            self.assertEqual(C.culpable({"t": 0.5}, ev)["fuente"], "fuerte")

    def test_efecto_del_motor_se_parchea_con_su_perilla(self):
        rm = {"pct_tapada": 50.0, "n_ventanas": 2, "mediana_db": 8, "ventanas": [{"t": 0.0, "db": -5}, {"t": 0.5, "db": 20}]}
        ev = [{"t0": 0.0, "t1": 0.3, "fuente": "motor whoosh (corte)", "motor": "whoosh", "vol": 0.38}]
        p = C.revisar_mezcla(rm, None, 0.5, VS, U, ev)[0]["parche"]
        self.assertEqual((p["op"], p["efecto"]), ("motor_vol", "whoosh"))
        self.assertAlmostEqual(p["valor"], round(0.38 * 10 ** (-C.PASO_MAX_DB / 20), 3))
        sb2, hechos = C.aplicar({}, [p])
        self.assertEqual(sb2["mezcla"]["whoosh"], p["valor"])

    def test_loudness_y_pico(self):
        f = C.revisar_mezcla(None, {"lufs": -16.0, "pico": -0.5}, 0.5, VS, U)
        self.assertEqual(len(f), 2)

    def test_puerta_de_contraste_de_producir_a_fallos_con_segundo(self):
        qa = {"puertas": [{"puerta": "contraste", "ok": False, "detalle":
              '2 textos ilegibles: "Illustrative · ~$170/mo reinve" 4.19:1 (< 4.5) en t≈13.97s; "75 years later" 2.2:1 (< 3) en t≈1.2s'}],
              "_aviso": ["Illustrative · ~$170/mo reinvested at ~10%/yr nominal"]}
        f = C.fallos_de_qa(qa, VS)
        self.assertEqual([(x["t"], x["escena"]) for x in f], [(13.97, "aviso"), (1.2, 0)])
        self.assertEqual([x["parche"]["op"] for x in f], ["aviso_placa", "fondo_suave"])

    def test_palabra_corta_contenida_en_el_aviso_no_es_el_aviso(self):
        qa = {"puertas": [{"puerta": "contraste", "ok": False, "detalle": '"for" 2.14:1 (< 3) en t≈1.0s'}],
              "_aviso": ["One real stock · ~15.2%/yr nominal for 75 years"]}
        self.assertEqual(C.fallos_de_qa(qa, VS)[0]["escena"], 0)

    def test_datos_sin_aviso_ni_fuentes(self):
        f = C.revisar_datos({"guion": [{"texto": "He made eight million."}]}, None)
        self.assertEqual({x["criterio"] for x in f}, {"D1"})
        self.assertEqual(len(f), 2)


class ParchesTest(unittest.TestCase):
    SB = {"golpes": ["0:rich"], "aviso": {"lineas": ["x"]}, "musica": {"volumen": 0.5},
          "sonidos": [{"sfx": "caja", "en": "0:rich", "vol": 0.6}],
          "escenas": [{"tipo": "foto"}, {"tipo": "titulo"}]}

    def test_aplica_cada_operacion_del_catalogo_sobre_una_copia(self):
        sb2, hechos = C.aplicar(self.SB, [
            {"op": "golpe", "ancla": "1:bought#2"}, {"op": "aviso_placa"}, {"op": "aviso_tam", "valor": 30},
            {"op": "musica_volumen", "valor": 0.3}, {"op": "sfx_vol", "indice": 0, "valor": 0.3},
            {"op": "fondo_suave", "escena": 1}, {"op": "set", "ruta": "escenas.1.posicion", "valor": "arriba"}])
        self.assertEqual(len(hechos), 7)
        self.assertEqual(sb2["golpes"], ["0:rich", "1:bought#2"])
        self.assertEqual((sb2["aviso"]["placa"], sb2["aviso"]["tam"]), (True, 30))
        self.assertEqual((sb2["musica"]["volumen"], sb2["sonidos"][0]["vol"]), (0.3, 0.3))
        self.assertEqual((sb2["escenas"][1]["fondo_suave"], sb2["escenas"][1]["posicion"]), (True, "arriba"))
        self.assertNotIn("placa", self.SB["aviso"])                  # el original no se toca

    def test_lo_que_no_cambia_nada_o_no_esta_permitido_no_cuenta(self):
        _, hechos = C.aplicar(self.SB, [
            {"op": "golpe", "ancla": "0:rich"},                         # ya estaba
            {"op": "musica_volumen", "valor": 0.9},                     # nunca SUBE la música
            {"op": "fondo_suave", "escena": 0},                         # una `foto` no tiene fondo
            {"op": "set", "ruta": "guion.0.texto", "valor": "otro"},    # el guion no se toca a ciegas
            {"op": "borrar_todo"}])
        self.assertEqual(hechos, [])

    def test_volcar_conserva_la_sangria_del_original(self):
        orig = '{\n "a": 1,\n "b": [\n  2\n ]\n}\n'
        self.assertEqual(C.volcar({"a": 1, "b": [2]}, orig), orig)

    def test_volumen_baja_como_mucho_un_paso_por_ronda(self):
        rm = {"pct_tapada": 50.0, "n_ventanas": 2, "mediana_db": 0, "ventanas": [{"t": 0.0, "db": -30}, {"t": 0.5, "db": 20}]}
        ev = [{"t0": 0.0, "t1": 0.3, "fuente": "sonidos[0] caja", "sonido": 0, "vol": 0.6}]
        v = C.revisar_mezcla(rm, None, 0.5, VS, U, ev)[0]["parche"]["valor"]
        self.assertAlmostEqual(v, round(0.6 * 10 ** (-C.PASO_MAX_DB / 20), 3))

    def test_puntuacion_por_severidad(self):
        self.assertEqual(C.puntuar([{"severidad": "alta"}, {"severidad": "media"}, {"severidad": "baja"}]), 6)


class JuicioYPlanTest(unittest.TestCase):
    def test_juicio_solo_admite_parches_del_catalogo(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "juicio.json").write_text(json.dumps({"fallos": [
                {"criterio": "J2", "severidad": "media", "t": 4.2, "escena": 2, "detalle": "plano no casa",
                 "parche": {"op": "set", "ruta": "escenas.2.img", "valor": "otra"}},
                {"criterio": "J6", "severidad": "baja", "detalle": "x", "parche": {"op": "rm -rf"}}]}))
            f = C.leer_juicio(Path(d))
        self.assertEqual([x["origen"] for x in f], ["juicio", "juicio"])
        self.assertEqual(f[0]["parche"]["op"], "set")
        self.assertIsNone(f[1]["parche"])

    def test_plan_de_html(self):
        html = '<script>window.PLAN = {"escenas": [{"t0": 0, "t1": 1.5}], "x": "<\\/b>"};</script>'
        p = C.plan_de_html(html)
        self.assertEqual((C.ventanas(p), p["x"]), ([(0.0, 1.5)], "</b>"))

    def test_escena_en_el_solape_es_la_que_acaba_de_entrar(self):
        self.assertEqual(C.escena_en(1.9, [(0.0, 1.92), (1.9, 3.0)]), 1)


class BucleTest(unittest.TestCase):
    """El bucle con render y revisión simulados: instantáneas, reintento tras puerta y vuelta atrás."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proy = Path(self.tmp.name) / "p"
        (self.proy / "renders").mkdir(parents=True)
        self.sb0 = '{\n "aviso": {\n  "lineas": [\n   "x"\n  ]\n },\n "escenas": [\n  {\n   "tipo": "titulo"\n  }\n ]\n}\n'
        (self.proy / "storyboard.json").write_text(self.sb0)
        (self.proy / "index.html").write_text('<script>window.PLAN = {"escenas": [{"t0": 0, "t1": 2}]};</script>')
        self.orig = (C.render, C.revisar, C.preparar_juicio)
        C.preparar_juicio = lambda *a, **k: None

    def tearDown(self):
        C.render, C.revisar, C.preparar_juicio = self.orig
        self.tmp.cleanup()

    def mp4(self, n):
        f = self.proy / "renders" / f"v{n}.mp4"
        f.write_bytes(b"x" * (n + 1))
        return f

    def test_puerta_fallida_se_parchea_y_la_mejor_ronda_medida_gana(self):
        renders = iter([(None, {"puertas": [{"puerta": "contraste", "ok": False,
                                             "detalle": '"Big title" 2.0:1 (< 3) en t≈1.0s'}]}, "✗ contraste"),
                        (self.mp4(2), {"puertas": []}, "ok")])
        C.render = lambda proy: next(renders)
        puntos = {"v0": 10, "r2": 4}
        C.revisar = lambda proy, mp4, rub, qa, juicio=None, sb=None, html=None: {
            "fallos": [], "medidas": {}, "puntuacion": puntos.get(mp4.stem, 10),
            **({"fallos": [C.fallo("L1", "alta", "aviso", parche={"op": "aviso_placa"})]} if mp4.stem == "r0" else {})}
        inf = C.bucle(self.proy, 2, self.mp4(0))
        self.assertEqual([r["puntuacion"] for r in inf["rondas"]], [10, None, 4])
        self.assertEqual(inf["elegida"], 2)
        d = self.proy / "renders" / "critica"
        self.assertTrue((d / "r0.mp4").exists() and (d / "r2.mp4").exists())
        self.assertEqual((d / "storyboard.r0.json").read_text(), self.sb0)          # instantánea intacta
        final = (self.proy / "storyboard.json").read_text()                       # se queda la mejor
        self.assertIn('"placa": true', final)
        self.assertIn('"fondo_suave": true', final)                                 # parche de la puerta

    def test_ronda_que_empeora_vuelve_al_storyboard_anterior(self):
        C.render = lambda proy: (self.mp4(1), {"puertas": []}, "ok")
        C.revisar = lambda proy, mp4, rub, qa, juicio=None, sb=None, html=None: (
            {"fallos": [C.fallo("L1", "alta", "a", parche={"op": "aviso_placa"})], "medidas": {}, "puntuacion": 5}
            if mp4.stem == "r0" else {"fallos": [], "medidas": {}, "puntuacion": 9})
        inf = C.bucle(self.proy, 2, self.mp4(0))
        self.assertEqual(inf["elegida"], 0)
        self.assertEqual((self.proy / "storyboard.json").read_text(), self.sb0)


if __name__ == "__main__":
    unittest.main()
