"""Ratchet entries E2, E3, E4, E9, E10 (video-v2/motor/errores.json), each reproduced from its real failure
(renders/corridas.jsonl + the session transcript that fixed it by hand) before its fix.

E2  strategy-underwater 14-nov: "Hay 2.8 s sin nada nuevo" over the 8-K proof; the punch-in Claude added
    changed nothing (motor.js drops a punch < 1.8 s from another, and the proof sits outside #cam).
E3  strategy-underwater: carousel slide 2 on `img:filing` (the proof document): OCR read the filing's own
    text at the edge ("ce (in", "(2)").
E4  strategy-underwater: slide 6 title unreadable on `clip:grafico@1`; fixed by hand with another background.
E9  berkshire-1999 16-nov: "burst" 1.92:1 after four --auto rounds of fondo_suave (already at its floor):
    the hot word of the caption; fixed by hand by removing it from `calientes`.
E10 strategy-underwater/berkshire-1999: dark hook clip ('pantalla' raw luma 16.5); fixed by hand with a
    reviewed brighter clip ('torres' 124.5)."""

from __future__ import annotations

import copy
import importlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]
anclas = importlib.import_module("anclas")
A = importlib.import_module("autoarreglo")
construir = importlib.import_module("construir")
critico = importlib.import_module("critico")
puertas = importlib.import_module("puertas")

V2 = RAIZ / "video-v2"
_R = json.loads((V2 / "motor" / "rubrica.json").read_text(encoding="utf-8"))
U = {k: v for x in _R["criterios"].values() for k, v in x.items() if k != "nombre"}


def cargar(ref: str) -> tuple[dict, list[dict]]:
    return (
        json.loads((V2 / ref / "storyboard.json").read_text(encoding="utf-8")),
        json.loads((V2 / ref / "assets" / "words.json").read_text(encoding="utf-8")),
    )


class RitmoE2Test(unittest.TestCase):
    def test_golpe_del_parche_no_cae_en_el_hueco_de_otro(self):
        # same structure on the committed take: proof from sentence 2 (8.4 s), punch at "seventy-five" 8.98 s
        sb, w = cargar("strategy-underwater")
        p = construir.plan(copy.deepcopy(sb), w)
        f = critico.revisar_ritmo(
            {"max_s": 2.8, "desde_s": 8.4}, w, critico.ventanas(p), U, p["golpes"]
        )
        t = anclas.t(w, f[0]["parche"]["ancla"])
        self.assertTrue(8.4 <= t <= 11.2)
        self.assertGreaterEqual(
            min(abs(t - g) for g in p["golpes"]), critico.HUECO_PUNCH
        )

    def test_sin_hueco_libre_no_hay_parche(self):
        _, w = cargar("strategy-underwater")
        golpes = [x["start"] for x in w]  # every word already punched
        f = critico.revisar_ritmo({"max_s": 2.8, "desde_s": 8.4}, w, [], U, golpes)
        self.assertIsNone(f[0]["parche"])

    def test_el_punch_mueve_tambien_la_prueba(self):
        sb, w = cargar("strategy-underwater")
        p = construir.plan(copy.deepcopy(sb), w)
        self.assertTrue(p.get("pruebas"))
        js = (V2 / "motor" / "motor.js").read_text(encoding="utf-8")
        self.assertIn('"#cam, .ppunch"', js)
        tpl = (V2 / "motor" / "plantilla.tpl").read_text(encoding="utf-8")
        self.assertIn(".prueba .ppunch", tpl)
        self.assertIn('class="ppunch"', construir.html_pruebas(p))


class SocialFondoTest(unittest.TestCase):
    def setUp(self):
        self.sb, self.w = cargar("strategy-underwater")

    def test_documento_de_fondo_que_toca_el_borde_pasa_a_otro_que_no_es_documento(self):  # E3
        # a proof document behind a slide is not always a failure (a published video passed OCR with one)
        self.sb["social"]["carrusel"][1]["fondo"] = "img:filing"
        reglas = ['diapositiva 2: "ce (in" toca el borde', 'diapositiva 2: "(2)" toca el borde']
        nuevo, hechos, pend = A.arreglar_storyboard(self.sb, self.w, reglas)
        self.assertEqual((len(hechos), pend), (1, []))
        f = nuevo["social"]["carrusel"][1]["fondo"]
        self.assertNotIn(f.removeprefix("img:"), {pr["img"] for pr in self.sb["pruebas"]})

    def test_borde_y_titulo_ilegible_cambian_el_fondo_una_vez_por_diapositiva(
        self,
    ):  # E3 + E4
        car = self.sb["social"]["carrusel"]
        car[5]["fondo"] = "clip:grafico@1"
        reglas = [
            'diapositiva 2: "ce (in" toca el borde',
            'diapositiva 2: "(2)" toca el borde',
            'diapositiva 6: el título "Would you hold a bitcoin vault?" no se lee en la imagen',
        ]
        antes = [d["fondo"] for d in car]
        nuevo, hechos, pend = A.arreglar_storyboard(self.sb, self.w, reglas)
        despues = [d["fondo"] for d in nuevo["social"]["carrusel"]]
        self.assertEqual(pend, [])
        self.assertEqual(len(hechos), 2)
        self.assertEqual(
            [k for k in range(len(antes)) if antes[k] != despues[k]], [1, 5]
        )
        refs = [f.split("@")[0] for f in despues]
        self.assertEqual(len(refs), len(set(refs)))  # no background used twice
        import social

        self.assertEqual(social.validar(nuevo), [])

    def test_por_la_puerta_social_de_producir(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            proy = tmp / "strategy-underwater"
            (proy / "assets").mkdir(parents=True)
            for f in ("storyboard.json", "index.html", "assets/words.json"):
                shutil.copy(V2 / "strategy-underwater" / f, proy / f)
            det = 'social con defectos:\n  - diapositiva 6: el título "X" no se lee en la imagen'
            hechos, pend, _ = A.arreglar(proy, {"social": det})
            self.assertEqual((len(hechos), pend), (1, []))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ContrasteCalienteE9Test(unittest.TestCase):
    def test_palabra_caliente_ilegible_sale_de_calientes(self):
        sb, _ = cargar("berkshire-1999")
        sb["calientes"].append("burst")  # the hand fix removed it
        vs = critico.ventanas(
            critico.plan_de_html(
                (V2 / "berkshire-1999" / "index.html").read_text(encoding="utf-8")
            )
        )
        t = sum(vs[3]) / 2
        qa = {
            "puertas": [
                {
                    "puerta": "contraste",
                    "ok": False,
                    "detalle": f'1 textos ilegibles: "burst" 1.92:1 (< 3) en t≈{t:.1f}s',
                }
            ],
            "_aviso": sb["aviso"]["lineas"],
            "_calientes": sb["calientes"],
        }
        f = critico.fallos_de_qa(qa, vs)
        nuevo, hechos = critico.aplicar(sb, [f[0]["parche"]])
        self.assertTrue(hechos)
        self.assertNotIn("burst", nuevo["calientes"])

    def test_texto_que_no_es_caliente_sigue_con_fondo_suave(self):
        qa = {
            "puertas": [
                {
                    "puerta": "contraste",
                    "ok": False,
                    "detalle": '1 textos ilegibles: "Tech bubble bursts" 2.33:1 (< 3) en t≈12.6s',
                }
            ],
            "_calientes": ["burst"],
        }
        f = critico.fallos_de_qa(qa, [(11.3, 13.4)])
        self.assertEqual(f[0]["parche"], {"op": "fondo_suave", "escena": 0})


class GanchoClaroE10Test(unittest.TestCase):
    """Raw lumas from the real luma.json caches: pantalla@2 16.5, chart@0 50, torres@0 124.5."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.proy = self.tmp / "strategy-underwater"
        clips = self.proy / "assets" / "clips"
        clips.mkdir(parents=True)
        for f in ("storyboard.json", "index.html", "assets/words.json"):
            shutil.copy(V2 / "strategy-underwater" / f, self.proy / f)
        sb = json.loads((self.proy / "storyboard.json").read_text(encoding="utf-8"))
        sb["escenas"][0]["fondo"] = {"clip": "pantalla"}  # the failing hook of 14-nov
        (self.proy / "storyboard.json").write_text(json.dumps(sb), encoding="utf-8")
        (clips / "luma.json").write_text(
            json.dumps({"pantalla@2": 16.5, "chart@0": 50.0, "torres@0": 124.5}),
            encoding="utf-8",
        )
        for c in ("pantalla", "chart", "torres"):
            (clips / f"{c}.src").write_bytes(b"")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lumas(self, sb):
        w = json.loads(
            (self.proy / "assets" / "words.json").read_text(encoding="utf-8")
        )
        p = construir.plan(copy.deepcopy(sb), w)
        g = puertas.GANCHO_S
        return puertas.gancho_clip_oscuro(
            p, construir.lumas_gancho(self.proy, sb, p, g), g
        )

    def test_clip_oscuro_del_gancho_pasa_a_uno_visto_y_claro(self):
        sb = json.loads((self.proy / "storyboard.json").read_text(encoding="utf-8"))
        e = self.lumas(sb)
        self.assertEqual(len(e), 1)
        hechos, pend, _ = A.arreglar(
            self.proy, {"storyboard": "✗ storyboard inválido:\n  - " + e[0]}
        )
        nuevo = json.loads((self.proy / "storyboard.json").read_text(encoding="utf-8"))
        self.assertEqual((len(hechos), pend), (1, []))
        self.assertEqual(nuevo["escenas"][0]["fondo"]["clip"], "torres")
        self.assertEqual(self.lumas(nuevo), [])

    def test_sin_clip_claro_medido_queda_pendiente(self):
        clips = self.proy / "assets" / "clips"
        (clips / "torres.src").unlink()  # not on disk and not measured: no luma to trust
        (clips / "luma.json").write_text('{"pantalla@2": 16.5, "chart@0": 50.0}', encoding="utf-8")
        sb = json.loads((self.proy / "storyboard.json").read_text(encoding="utf-8"))
        e = self.lumas(sb)
        hechos, pend, _ = A.arreglar(self.proy, {"storyboard": "x:\n  - " + e[0]})
        self.assertEqual((hechos, len(pend)), ([], 1))


if __name__ == "__main__":
    unittest.main()
