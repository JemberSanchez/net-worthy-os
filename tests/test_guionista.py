"""Tests de video-v2/motor/guionista.py: puertas medibles del guion, combinación de ganchos y elección."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "video-v2" / "motor"))

import guionista as G

RELLENO_10 = "word " * 10


def puerta(frases, pid):
    return next(p for p in G.puertas(frases) if p["id"] == pid)


class TestCifra(unittest.TestCase):
    def test_numeros_en_palabras_y_digitos(self):
        self.assertTrue(G.tiene_cifra("This janitor died with eight million dollars."))
        self.assertTrue(G.tiene_cifra("Rates hit 7.3% this week."))
        self.assertTrue(G.tiene_cifra("Thirty-nine months in a row."))
        self.assertFalse(G.tiene_cifra("More homes are for sale than in years."))

    def test_puerta_mira_solo_la_primera_frase(self):
        self.assertFalse(
            puerta(["No number here.", "But eight million later."], "G-CIFRA")["ok"]
        )
        self.assertTrue(
            puerta(["Eight million dollars.", "Then nothing."], "G-CIFRA")["ok"]
        )


class TestLargo(unittest.TestCase):
    def test_rango_85_110(self):
        self.assertFalse(puerta(["word " * 84], "G-LARGO")["ok"])
        self.assertTrue(puerta(["word " * 85], "G-LARGO")["ok"])
        self.assertTrue(puerta(["word " * 110], "G-LARGO")["ok"])
        self.assertFalse(puerta(["word " * 111], "G-LARGO")["ok"])


class TestRelleno(unittest.TestCase):
    def test_detecta_muletillas(self):
        p = puerta(
            ["So basically, he saved money.", "You see, it worked."], "G-RELLENO"
        )
        self.assertFalse(p["ok"])
        self.assertIn("basically", p["detalle"])
        self.assertTrue(puerta(["He saved money.", "It worked."], "G-RELLENO")["ok"])

    def test_no_confunde_subcadenas(self):
        # "factually" contiene "actually" pero no es relleno
        self.assertTrue(puerta(["That is factually true."], "G-RELLENO")["ok"])


class TestGiro(unittest.TestCase):
    def test_hueco_largo_sin_giro_falla(self):
        # 3,1 palabras/s: 40 palabras sin cifra ni giro = ~13 s de hueco
        frases = ["Eight million dollars.", "word " * 40, "word " * 5]
        p = puerta(frases, "G-GIRO")
        self.assertFalse(p["ok"])
        self.assertIn("s", p["detalle"])

    def test_giros_frecuentes_pasan(self):
        frases = [
            "Eight million dollars.",
            RELLENO_10,
            "Here's the part nobody tells you.",
            RELLENO_10,
            "Then ninety-five stocks.",
            RELLENO_10,
        ]
        self.assertTrue(puerta(frases, "G-GIRO")["ok"])

    def test_cuenta_el_hueco_final(self):
        frases = ["Eight million dollars.", "word " * 40]
        self.assertFalse(puerta(frases, "G-GIRO")["ok"])


class TestBucle(unittest.TestCase):
    def test_ultima_frase_enlaza_con_la_primera(self):
        self.assertTrue(
            puerta(
                ["This janitor died rich.", "x", "So was the janitor lucky?"], "G-BUCLE"
            )["ok"]
        )
        self.assertFalse(
            puerta(
                ["This janitor died rich.", "x", "So what do you think?"], "G-BUCLE"
            )["ok"]
        )

    def test_ignora_palabras_vacias(self):
        self.assertFalse(
            puerta(["This is what they want.", "x", "What is this?"], "G-BUCLE")["ok"]
        )

    def test_plural_y_singular_enlazan(self):
        self.assertTrue(
            puerta(["Homes are for sale.", "x", "Will that home sell?"], "G-BUCLE")[
                "ok"
            ]
        )


class TestCombinarYElegir(unittest.TestCase):
    def test_ganchos_sustituyen_la_primera_frase(self):
        est = {
            "id": "contraste",
            "frases": [
                {"id": "a", "texto": "Old hook."},
                {"id": "b", "texto": "Body."},
            ],
        }
        cands = G.candidatos_gancho(est, [{"id": "g1", "texto": "New hook."}])
        self.assertEqual([c["id"] for c in cands], ["contraste", "contraste+g1"])
        self.assertEqual(cands[1]["frases"][0], {"id": "a", "texto": "New hook."})
        self.assertEqual(cands[1]["frases"][1]["texto"], "Body.")
        self.assertEqual(
            est["frases"][0]["texto"], "Old hook."
        )  # no muta la estructura

    def test_menos_fallos_gana_antes_que_juicio(self):
        cands = [{"id": "a", "fallos": 1}, {"id": "b", "fallos": 0}]
        juicio = {
            "a": {"una_idea": 5, "bucle_abierto": 5, "giro": 5},
            "b": {"una_idea": 1, "bucle_abierto": 1, "giro": 1},
        }
        ganador, ranking = G.elegir(cands, juicio)
        self.assertEqual(ganador["id"], "b")
        self.assertEqual([c["id"] for c in ranking], ["b", "a"])

    def test_empate_de_fallos_decide_el_juicio(self):
        cands = [{"id": "a", "fallos": 0}, {"id": "b", "fallos": 0}]
        juicio = {
            "a": {"una_idea": 3, "bucle_abierto": 3, "giro": 3},
            "b": {"una_idea": 4, "bucle_abierto": 4, "giro": 4},
        }
        self.assertEqual(G.elegir(cands, juicio)[0]["id"], "b")

    def test_juicio_incompleto_lo_dice(self):
        with self.assertRaises(G.FaltaJuicio) as e:
            G.elegir(
                [{"id": "a", "fallos": 0}, {"id": "b", "fallos": 0}],
                {"a": {"una_idea": 3, "bucle_abierto": 3, "giro": 3}},
            )
        self.assertEqual(e.exception.faltan, ["b"])

    def test_nota_fuera_de_rango_rompe(self):
        with self.assertRaises(ValueError):
            G.elegir(
                [{"id": "a", "fallos": 0}],
                {"a": {"una_idea": 7, "bucle_abierto": 3, "giro": 3}},
            )


class TestCiego(unittest.TestCase):
    def test_par_ciego_guarda_la_clave_aparte(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            clave = G.par_ciego(
                d, ["Plantilla one."], ["Elegido one."], semilla=1, audio=False
            )
            textos = {k: (d / f"{k}.txt").read_text(encoding="utf-8") for k in "AB"}
            self.assertEqual(
                sorted(textos.values()), ["Elegido one.", "Plantilla one."]
            )
            guardada = json.loads((d / ".clave.json").read_text(encoding="utf-8"))
            self.assertEqual(guardada, clave)
            self.assertEqual(textos[clave["plantilla"]], "Plantilla one.")


if __name__ == "__main__":
    unittest.main()
