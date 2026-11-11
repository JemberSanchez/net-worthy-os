"""Edit choices per video (video-v2/motor/edicion.py) and the repetition gate (medir_parecido, P1)."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]

import construir as c
import edicion as ed
import medir_parecido as mp

LISTA = {"Public domain", "Public Domain", "CC0", "CC BY 3.0", "CC BY 4.0"}
FRASES = [
    "Rates hit a record today.",
    "Nobody expected that move.",
    "Banks cut prices fast.",
    "So what happens next?",
    "Tell me below.",
]
GUION = [
    {"id": "a", "texto": " ".join(FRASES[:2])},
    {"id": "b", "texto": FRASES[2]},
    {"id": "c", "texto": " ".join(FRASES[3:])},
]


def palabras():
    out, t = [], 0.0
    for f in FRASES:
        for w in f.split():
            out.append({"text": w, "start": round(t, 2), "end": round(t + 0.5, 2)})
            t += 0.8
    return out


def sb_nuevo(ref="nuevo", **extra):
    return {
        "ref": ref,
        "formato": "grafica-viva",
        "guion": GUION,
        "escenas": [
            {"tipo": "foto", "en": "0", "clip": "k", "parallax": False},
            {"tipo": "foto", "en": "1", "clip": "j"},
            {"tipo": "foto", "en": "2", "clip": "k"},
            {"tipo": "foto", "en": "3", "clip": "j"},
        ],
        "clips": {
            "k": {"pexels": 1},
            "j": {"pexels": 2},
        },  # max. 2 uses per source (errores_seleccion)
        "golpes": ["1:expected", "3:happens"],
        "calientes": [],
        "sonidos": [
            {"sfx": "thud", "en": "0:record"},
            {"sfx": "tick", "en": "2:cut", "vol": 0.05},
            {"sfx": "riser_gong", "en": "1"},
        ],
        **extra,
    }


def crear(raiz: Path, sb: dict) -> Path:
    d = raiz / sb["ref"]
    (d / "assets").mkdir(parents=True)
    (d / "storyboard.json").write_text(json.dumps(sb), encoding="utf-8")
    (d / "assets" / "words.json").write_text(json.dumps(palabras()), encoding="utf-8")
    return d


def construido(raiz: Path, sb: dict) -> tuple[dict, dict]:
    """The same steps as construir() up to the gate, plus the registry write of a full build."""
    d = raiz / sb["ref"]
    s = json.loads((d / "storyboard.json").read_text(encoding="utf-8"))
    ed.preparar(d, s)
    p = c.plan(s, palabras())
    return p, s


class SeleccionTest(unittest.TestCase):
    def test_determinista_y_depende_de_la_ref(self):
        a, b = ed.elegir(sb_nuevo(), []), ed.elegir(sb_nuevo(), [])
        self.assertEqual(a, b)
        otras = {
            json.dumps(ed.elegir(sb_nuevo(f"r{i}"), [])["camara"]) for i in range(8)
        }
        self.assertGreater(len(otras), 1)

    def test_evita_lo_usado_en_la_ventana(self):
        previa = ed.elegir(sb_nuevo("r0"), [])
        firma = {
            "transiciones": previa["transiciones"],
            "camara": previa["camara"],
            "punch": [previa["punch"]],
            "texto": [previa["texto"]],
        }
        e = ed.elegir(sb_nuevo("r1"), [firma])
        self.assertFalse(set(e["transiciones"]) & set(previa["transiciones"]))
        self.assertFalse(set(e["camara"]) & set(previa["camara"]))
        self.assertNotEqual(e["punch"], previa["punch"])
        self.assertNotEqual(e["texto"], previa["texto"])

    def test_override_manual_manda(self):
        e = ed.elegir(
            sb_nuevo(
                edicion={"punch": "seco", "camara": ["push"], "sfx": {"thud": "thud"}}
            ),
            [],
        )
        self.assertEqual(
            (e["punch"], e["camara"], e["sfx"]["thud"]), ("seco", ["push"], "thud")
        )

    def test_tipografia_rota_y_los_videos_viejos_cuentan_como_serif(self):
        # rows written before 11-nov have no `tipografia`: they all used the serif
        primera = ed.elegir(sb_nuevo("r1"), [{}, {}])["tipografia"]
        self.assertIn(primera, ("grotesca", "condensada"))
        segunda = ed.elegir(sb_nuevo("r2"), [{"tipografia": [primera]}, {}])
        self.assertNotIn(segunda["tipografia"], (primera, "serif"))
        tercera = ed.elegir(
            sb_nuevo("r3"),
            [{"tipografia": [segunda["tipografia"]]}, {"tipografia": [primera]}, {}],
        )
        self.assertEqual(
            tercera["tipografia"], "serif"
        )  # the longest unused comes back
        manual = sb_nuevo(edicion={"tipografia": "serif"})
        self.assertEqual(ed.elegir(manual, [])["tipografia"], "serif")
        malo = sb_nuevo(edicion={"tipografia": "comic"})
        self.assertIn("tipografia", " ".join(ed.errores_manual(malo, {})))

    def test_tema_editorial_solo_transiciones_sobrias(self):
        e = ed.elegir(sb_nuevo(tema="editorial"), [])
        self.assertTrue(all(ed.TRANSICIONES[t]["sobria"] for t in e["transiciones"]))

    def test_capas_de_una_grabacion_cambian_juntas(self):
        sb = sb_nuevo(
            sonidos=[
                {"sfx": "braam_sub", "en": "1"},
                {"sfx": "braam_cuerpo", "en": "1"},
            ]
        )
        cat = ed._cat_sfx()
        e = ed.elegir(sb, [{"efectos": [ed._archivo(cat, "braam_sub")]}])
        self.assertEqual(
            cat[e["sfx"]["braam_sub"]]["par"], cat[e["sfx"]["braam_cuerpo"]]["par"]
        )
        self.assertNotEqual(cat[e["sfx"]["braam_sub"]]["par"], "braam")

    def test_cadena_larga_no_se_bloquea(self):
        """12 videos seguidos con la misma receta: el catalogo aguanta la ventana y la puerta pasa."""
        for tema in (None, "editorial"):
            with tempfile.TemporaryDirectory() as t:
                raiz = Path(t)
                for i in range(12):
                    sb = sb_nuevo(f"v{i}", **({"tema": tema} if tema else {}))
                    d = crear(raiz, sb)
                    p, s = construido(raiz, sb)
                    self.assertEqual(ed.puerta(d, p, s), [], f"{tema} video {i}")
                    ed.registrar(d, p, s)


class PuertaTest(unittest.TestCase):
    def test_todo_igual_al_anterior_falla_y_con_seleccion_pasa(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            a = crear(raiz, sb_nuevo("a"))
            pa, sa = construido(raiz, sb_nuevo("a"))
            ed.registrar(a, pa, sa)
            e = sa["_edicion"]
            copia = {
                k: e[k]
                for k in ("transiciones", "camara", "punch", "texto", "sfx", "motor")
            }
            crear(
                raiz,
                sb_nuevo(
                    "copia",
                    edicion=copia,
                    musica={"pista": {"commons": e["musica"]["commons"]}},
                ),
            )
            pc, sc = construido(raiz, sb_nuevo("copia"))
            motivos = ed.puerta(raiz / "copia", pc, sc)
            self.assertTrue(any(m.startswith("punch") for m in motivos), motivos)
            self.assertTrue(any(m.startswith("camara") for m in motivos), motivos)
            self.assertTrue(any(m.startswith("musica") for m in motivos), motivos)
            crear(raiz, sb_nuevo("auto"))
            pb, sb = construido(raiz, sb_nuevo("auto"))
            self.assertEqual(ed.puerta(raiz / "auto", pb, sb), [])

    def test_construir_validar_bloquea_y_no_escribe(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            a = crear(raiz, sb_nuevo("a"))
            pa, sa = construido(raiz, sb_nuevo("a"))
            ed.registrar(a, pa, sa)
            antes = (raiz / "usado.json").read_text(encoding="utf-8")
            e = sa["_edicion"]
            d = crear(raiz, sb_nuevo("b", edicion={"punch": e["punch"]}))
            with self.assertRaisesRegex(c.StoryboardError, "punch"):
                c.construir(d, solo_validar=True, sin_contraste=True)
            d2 = crear(raiz, sb_nuevo("c"))
            # toy script: this test covers the edit gate and usado.json, not script or text repetition
            with (
                mock.patch("medir_parecido.puerta_repeticion", return_value=(True, "")),
                mock.patch("guionista.puerta_guion", return_value=(True, "")),
                mock.patch("puertas.clips_sin_ver", return_value=[]),
                mock.patch("puertas.variedad_escenas", return_value=[]),
            ):
                c.construir(d2, solo_validar=True, sin_contraste=True)
            self.assertEqual((raiz / "usado.json").read_text(encoding="utf-8"), antes)

    def test_legacy_y_sin_formato_no_cambian(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            sb = sb_nuevo("viejo")
            d = crear(raiz, sb)
            (raiz / "usado.json").write_text(
                json.dumps({"videos": [{"ref": "viejo", "legacy": True, "firma": {}}]}),
                encoding="utf-8",
            )
            self.assertIsNone(ed.preparar(d, json.loads(json.dumps(sb))))
            sin = json.loads(json.dumps(sb))
            del sin["formato"]
            self.assertIsNone(ed.preparar(raiz / "otro", sin))
            self.assertNotIn("transiciones", c.plan(sin, palabras()))

    def test_eleccion_congelada_al_reconstruir(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            a = crear(raiz, sb_nuevo("a"))
            pa, sa = construido(raiz, sb_nuevo("a"))
            ed.registrar(a, pa, sa)
            crear(raiz, sb_nuevo("b"))
            pb, sb = construido(raiz, sb_nuevo("b"))
            ed.registrar(raiz / "b", pb, sb)
            _, otra = construido(raiz, sb_nuevo("a"))
            self.assertEqual(otra["_edicion"], sa["_edicion"])

    def test_todos_los_publicados_siguen_validando(self):
        sbs = sorted((RAIZ / "video-v2").glob("*/storyboard.json"))
        # a checkout has no renders or local base and both history gates order by storyboard mtime (their documented
        # shortcut), so a touched storyboard fails on an older video's turn: history is tested in this class's own cases
        with (
            mock.patch(
                "guionista.refs_publicadas", return_value=[f.parent.name for f in sbs]
            ),
            mock.patch("medir_parecido.puerta_repeticion", return_value=(True, "")),
        ):
            for f in sbs:
                if (f.parent / "assets" / "words.json").exists():
                    c.construir(f.parent, solo_validar=True, sin_contraste=True)


class MedidorTest(unittest.TestCase):
    def test_instrumento_contra_si_mismo_y_contra_distinto(self):
        lims = {"ventana": 3, **{f"{d}_max": 0.34 for d in mp.DIMS_EDICION}}
        a = {d: [f"{d}1", f"{d}2"] for d in mp.DIMS_EDICION}
        b = {d: [f"{d}8", f"{d}9"] for d in mp.DIMS_EDICION}
        mismo = mp.repeticion_edicion(a, [{"ref": "a", "firma": a}], lims)
        self.assertTrue(all(x["valor"] == 1.0 for x in mismo["dims"].values()))
        self.assertEqual(len(mismo["motivos"]), len(mp.DIMS_EDICION))
        otro = mp.repeticion_edicion(a, [{"ref": "b", "firma": b}], lims)
        self.assertTrue(all(x["valor"] == 0.0 for x in otro["dims"].values()))
        self.assertEqual(otro["motivos"], [])

    def test_ventana_olvida_lo_antiguo(self):
        lims = {"ventana": 1, **{f"{d}_max": 0.0 for d in mp.DIMS_EDICION}}
        a = {"punch": ["x"]}
        previas = [
            {"ref": "b", "firma": {"punch": ["y"]}},
            {"ref": "c", "firma": {"punch": ["x"]}},
        ]
        self.assertEqual(mp.repeticion_edicion(a, previas, lims)["motivos"], [])

    def test_efectos_por_archivo_dos_cortes_de_una_grabacion_repiten(self):
        cat = ed._cat_sfx()
        self.assertEqual(
            ed._archivo(cat, "swell_corto"), ed._archivo(cat, "riser_platillo")
        )


class CatalogoTest(unittest.TestCase):
    def test_licencias_en_la_lista_cerrada(self):
        for k, v in ed._cat_sfx().items():
            self.assertIn(v["licencia"], LISTA, k)
            self.assertIn("rol", v, k)
        for k, v in ed.cat_musica().items():
            self.assertIn(v["licencia"], LISTA, k)

    def test_cada_rol_cambiable_aguanta_la_ventana(self):
        cat = ed._cat_sfx()
        for rol in ed.ROLES_CAMBIABLES:
            archivos = {ed._archivo(cat, n) for n in cat if cat[n]["rol"] == rol}
            self.assertGreaterEqual(len(archivos), 4, rol)

    def test_camara_nunca_descubre_el_borde(self):
        ancho, alto = 1080, 1920
        for cid, c_ in ed.CAMARA.items():
            for f in (c_["a"], c_["b"]):
                sobra_x = ancho * (f["scale"] - 1) / 2
                sobra_y = alto * (f["scale"] - 1) / 2
                self.assertLessEqual(abs(f["x"]), sobra_x, cid)
                self.assertLessEqual(abs(f["y"]), sobra_y, cid)
                rad = abs(f.get("rotation", 0)) * 3.14159 / 180
                self.assertGreaterEqual(f["scale"], 1 + rad * alto / ancho, cid)

    def test_motor_es_determinista(self):
        js = (RAIZ / "video-v2" / "motor" / "motor.js").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"Math\.random|Date\.now|new Date\(")

    def test_opciones_superan_la_ventana(self):
        n = mp.limites_repeticion()["ventana"] + 1
        for cat in (ed.PUNCH, ed.TEXTO, ed.cat_musica()):
            self.assertGreaterEqual(len(cat), n)
        sobrias = [k for k, v in ed.TRANSICIONES.items() if v["sobria"]]
        self.assertGreaterEqual(len(sobrias), n * ed.N_TRANS_SOBRIA)
        self.assertGreaterEqual(len(ed.CAMARA), n * ed.N_CAM)


class TransicionesTest(unittest.TestCase):
    def test_corte_seco_por_defecto_transicion_en_cambio_de_idea(self):
        sb = sb_nuevo()
        ed.aplicar(sb, ed.elegir(sb, []))
        p = c.plan(sb, palabras())
        escenas = len(p["escenas"]) - 1
        self.assertLess(len(p["transiciones"]), escenas)
        fr_b = palabras()[len(" ".join(FRASES[:2]).split())]["start"]
        self.assertTrue(
            any(abs(t["t"] - (fr_b - c.PRE)) < 0.01 for t in p["transiciones"])
        )
        self.assertEqual(p["cortes"], [t["t"] for t in p["transiciones"]])

    def test_escena_puede_pedir_o_quitar_transicion(self):
        sb = sb_nuevo()
        sb["escenas"][1]["transicion"] = "iris"
        sb["escenas"][2]["transicion"] = "corte"
        ed.aplicar(sb, ed.elegir(sb, []))
        p = c.plan(sb, palabras())
        self.assertEqual(p["transiciones"][0]["tipo"], "iris")
        self.assertEqual(
            sum(
                1
                for t in p["transiciones"]
                if abs(t["t"] - p["escenas"][2]["t0"]) < 0.01
            ),
            0,
        )

    def test_motor_silenciado_no_suena_y_efectos_del_motor_son_reales(self):
        sb = sb_nuevo(mezcla={"whoosh": 0, "impacto": 0, "riser": 0})
        ed.aplicar(sb, ed.elegir(sb, []))
        p = c.plan(sb, palabras())
        self.assertFalse([u for u in p["sonidos"] if u.get("motor")])
        sb2 = sb_nuevo()
        ed.aplicar(sb2, ed.elegir(sb2, []))
        p2 = c.plan(sb2, palabras())
        self.assertTrue([u for u in p2["sonidos"] if u.get("motor") == "impacto"])
        html = c._html(p2)
        self.assertNotIn("_motor/whoosh.wav", html)
        self.assertNotIn("_motor/impact.wav", html)

    def test_catalogo_de_transicion_vuelve_al_reposo(self):
        for k, v in ed.TRANSICIONES.items():
            for clave in set(v["sale"]) | set(v["entra"]):
                self.assertIn(clave, v["reposo"], k)
            self.assertLess(v["dur_sale"] + v["dur_entra"], 0.7, k)
            if v["reflejo"]:
                self.assertEqual(len(v["reflejo"]), 2, k)

    def test_clip_path_interpolable(self):
        patron = re.compile(r"\d+%")
        for k, v in ed.TRANSICIONES.items():
            if "clipPath" in v["reposo"]:
                n = len(patron.findall(v["reposo"]["clipPath"]))
                self.assertEqual(len(patron.findall(v["sale"]["clipPath"])), n, k)
                self.assertEqual(len(patron.findall(v["entra"]["clipPath"])), n, k)


if __name__ == "__main__":
    unittest.main()
