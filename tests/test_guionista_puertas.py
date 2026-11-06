"""Retention gates added to guionista.py (docs/mejora/guion/): hook, viewer stake, figures, stock phrases, closes."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "video-v2" / "motor"))

import guionista as G


def puerta(frases, pid, **kw):
    return next(p for p in G.puertas(frases, **kw) if p["id"] == pid)


class TestGancho(unittest.TestCase):
    def test_cifra_sola_falla(self):
        for hook in (
            "Nineteen point seven percent. That's what the card charges.",
            "Six point three billion dollars, gone in one night.",
            "Twenty-three percent of Amazon's sales. Sixty-three percent of its profit.",
            "$7.2 million.",
        ):
            with self.subTest(hook=hook):
                self.assertFalse(puerta([hook], "G-GANCHO")["ok"])

    def test_cifra_con_sujeto_o_contraste_pasa(self):
        for hook in (
            "The president's party lost Congress, and the Dow jumped fifteen hundred points.",
            "This janitor died with eight million dollars.",
            "The economy grew three point four percent, and almost everyone reads it wrong.",
            "Eight million dollars, but he never earned a big salary.",
        ):
            with self.subTest(hook=hook):
                self.assertTrue(puerta([hook], "G-GANCHO")["ok"])

    def test_sin_cifra_tambien_pasa(self):
        # Removes the old G-CIFRA requirement: a figure is neither needed nor enough
        self.assertTrue(
            puerta(
                ["More homes are for sale than in years,", "and prices still went up."],
                "G-GANCHO",
            )["ok"]
        )

    def test_gancho_abarca_frases_hasta_el_punto(self):
        # The contrast lives in the 2nd phrase: must not be judged on the 1st alone
        self.assertTrue(
            puerta(
                ["Three million dollars,", "but the janitor never knew."], "G-GANCHO"
            )["ok"]
        )

    def test_nombre_o_sigla_sin_explicar_falla(self):
        for hook in (
            "The heist at Binance took four minutes.",
            "Investors love what AWS did this quarter.",
            "Nobody expected Grace Groner to die rich.",
        ):
            with self.subTest(hook=hook):
                p = puerta([hook], "G-GANCHO")
                self.assertFalse(p["ok"])
                self.assertIn("sin explicar", p["detalle"])

    def test_nombre_explicado_o_conocido_pasa(self):
        for hook in (
            "Hackers drained Binance, the world's biggest crypto exchange.",
            "Half of Amazon's profit comes from one quiet business.",
            "A secretary named Grace Groner, a quiet saver, died rich.",
        ):
            with self.subTest(hook=hook):
                self.assertTrue(puerta([hook], "G-GANCHO")["ok"])

    def test_nombre_al_inicio_se_detecta_si_reaparece(self):
        p = puerta(
            ["Binance lost it all in one night.", "Then Binance froze withdrawals."],
            "G-GANCHO",
        )
        self.assertFalse(p["ok"])

    def test_pronombre_sin_referente_falla(self):
        self.assertFalse(puerta(["They lost everything overnight."], "G-GANCHO")["ok"])


class TestTu(unittest.TestCase):
    def test_tu_a_tiempo(self):
        self.assertTrue(
            puerta(["Your bank charges a markup on every card."], "G-TU")["ok"]
        )

    def test_tu_justo_en_el_limite(self):
        relleno = "word " * (G.TU_PALABRA_MAX - 1)
        self.assertTrue(puerta([relleno + "you"], "G-TU")["ok"])
        self.assertFalse(puerta([relleno + "word you"], "G-TU")["ok"])

    def test_nunca_dice_tu(self):
        p = puerta(["The Fed held rates this week."], "G-TU")
        self.assertFalse(p["ok"])

    def test_equivalentes(self):
        for t in ("Most people read this wrong.", "Almost everyone reads it wrong."):
            with self.subTest(t=t):
                self.assertTrue(puerta([t], "G-TU")["ok"])

    def test_no_confunde_subcadenas(self):
        self.assertFalse(puerta(["The young yourt seller left."], "G-TU")["ok"])


class TestCifrasProtagonistas(unittest.TestCase):
    def test_agrupa_una_cifra_dicha_en_varias_palabras(self):
        self.assertEqual(
            len(
                G.cifras_protagonistas(
                    "Amazon sold two hundred one point nine billion dollars."
                )
            ),
            1,
        )
        self.assertEqual(
            len(G.cifras_protagonistas("It pays one dollar and eight cents.")), 1
        )
        self.assertEqual(
            len(
                G.cifras_protagonistas(
                    "She died with seven million, two hundred thousand dollars."
                )
            ),
            1,
        )

    def test_repetir_la_misma_no_suma(self):
        self.assertEqual(
            len(
                G.cifras_protagonistas(
                    "Sixty-three percent. So sixty-three percent of it."
                )
            ),
            1,
        )

    def test_a_hundred_es_one_hundred(self):
        self.assertEqual(
            len(
                G.cifras_protagonistas(
                    "She paid one hundred and eighty dollars. A hundred and eighty."
                )
            ),
            1,
        )

    def test_excluye_anios_y_cuentas_pequenas(self):
        self.assertEqual(
            G.cifras_protagonistas(
                "In nineteen eighty, one night, two officials and not one dollar, in 1935."
            ),
            [],
        )

    def test_cuenta_digitos_y_palabras(self):
        self.assertEqual(
            len(
                G.cifras_protagonistas(
                    "Rates hit 7.3% and homes cost $417,000 after thirty-nine months."
                )
            ),
            3,
        )

    def test_puerta_max_tres(self):
        tres = "Rates hit 7.3%, homes cost $417,000, it took thirty-nine months."
        self.assertTrue(puerta([tres], "G-CIFRAS")["ok"])
        cuatro = tres + " Inventory hit one point six million."
        p = puerta([cuatro], "G-CIFRAS")
        self.assertFalse(p["ok"])
        self.assertIn("4", p["detalle"])


class TestComodin(unittest.TestCase):
    def test_detecta_variantes(self):
        for t in (
            "Here's the part nobody tells you.",
            "Here’s the part nobody tells you.",
            "Here is the uncomfortable part.",
            "And nobody talks about this.",
            "Let that sink in.",
        ):
            with self.subTest(t=t):
                self.assertFalse(puerta([t], "G-COMODIN")["ok"])

    def test_frase_propia_pasa(self):
        self.assertTrue(
            puerta(["They rehearsed for thirty-six hours."], "G-COMODIN")["ok"]
        )

    def test_comodin_no_cuenta_como_giro(self):
        # A stock phrase must not satisfy the re-hook gate either
        self.assertFalse(G._es_giro({"texto": "Here's the part nobody tells you."}))


class TestCierre(unittest.TestCase):
    def test_clasifica(self):
        casos = {
            "So was it skill, or just time?": "dicotomia",
            "Could you sit on it for seventy-five years?": "pregunta",
            "Ask which part of your money moved.": "imperativo",
            "Her stake is worth seventy-five million dollars today.": "dato",
            "And not one dollar pays down the debt.": "afirmacion",
        }
        for t, tipo in casos.items():
            with self.subTest(t=t):
                self.assertEqual(G.tipo_cierre(["Intro.", t]), tipo)

    def test_veta_tipo_reciente(self):
        fin = ["Intro.", "So was it skill, or just time?"]
        self.assertFalse(
            puerta(fin, "G-CIERRE", previos=["pregunta", "dicotomia", "dato"])["ok"]
        )
        self.assertTrue(
            puerta(fin, "G-CIERRE", previos=["pregunta", "afirmacion", "dato"])["ok"]
        )

    def test_solo_mira_la_ventana(self):
        fin = ["Intro.", "So was it skill, or just time?"]
        previos = ["pregunta", "afirmacion", "dato", "dicotomia"]
        self.assertTrue(puerta(fin, "G-CIERRE", previos=previos)["ok"])

    def test_sin_historial_no_veta(self):
        self.assertTrue(puerta(["Intro.", "Skill, or time?"], "G-CIERRE")["ok"])


def _proyecto(raiz: Path, nombre: str, ultima: str, final: bool = False) -> Path:
    p = raiz / nombre
    (p / "renders").mkdir(parents=True)
    (p / "storyboard.json").write_text(
        json.dumps({"ref": nombre, "guion": [{"id": "a", "texto": ultima}]}),
        encoding="utf-8",
    )
    if final:
        (p / "renders" / f"{nombre}-final.mp4").write_bytes(b"x")
    return p


class TestPublicados(unittest.TestCase):
    def test_exento_si_ya_tiene_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _proyecto(Path(tmp), "viejo", "Six point three billion dollars.", True)
            ok, detalle = G.puerta_guion(p, publicados=[])
            self.assertTrue(ok)
            self.assertIn("exento", detalle)

    def test_exento_si_esta_publicado(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _proyecto(Path(tmp), "viejo", "Six point three billion dollars.")
            self.assertTrue(G.puerta_guion(p, publicados=["viejo"])[0])

    def test_guion_nuevo_malo_falla_y_dice_cual(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _proyecto(Path(tmp), "nuevo", "Six point three billion dollars.")
            ok, detalle = G.puerta_guion(p, publicados=[])
            self.assertFalse(ok)
            self.assertIn("G-GANCHO", detalle)

    def test_guion_nuevo_sin_formato_falla(self):
        # without `formato` edicion.preparar exempts the video from the repetition gate
        with tempfile.TemporaryDirectory() as tmp:
            p = _proyecto(Path(tmp), "nuevo", "Six point three billion dollars.")
            ok, detalle = G.puerta_guion(p, publicados=[])
            self.assertFalse(ok)
            self.assertIn("G-FORMATO", detalle)

    def test_cierres_previos_en_orden_de_publicacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            _proyecto(r, "a", "Skill, or time?")
            _proyecto(r, "b", "Could you wait?")
            p = _proyecto(r, "c", "Ask your bank.")
            # newest first, excludes itself, ignores unknown dirs
            self.assertEqual(
                G.cierres_previos(p, publicados=["c", "b", "gone", "a"]),
                ["pregunta", "dicotomia"],
            )


@unittest.skipUnless(
    (RAIZ / "docs" / "mejora" / "guion" / "demo.json").exists(),
    "docs/mejora is gitignored",
)
class TestDemo(unittest.TestCase):
    def test_guion_demo_pasa_todas_las_puertas(self):
        demo = json.loads(
            (RAIZ / "docs" / "mejora" / "guion" / "demo.json").read_text(
                encoding="utf-8"
            )
        )
        for variante, gancho in demo["ganchos"].items():
            frases = [gancho, *demo["cuerpo"]]
            fallan = [
                p["id"]
                for p in G.puertas(frases, previos=demo["cierres_previos"])
                if not p["ok"]
            ]
            with self.subTest(variante=variante):
                self.assertEqual(fallan, [])


if __name__ == "__main__":
    unittest.main()
