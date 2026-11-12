"""producir.py --auto (video-v2/motor/autoarreglo.py): each mechanical fix, built from a REAL failure
of the transcripts (12-nov), must clear its gate message; a non-mechanical one must come back untouched.

Cases: the two first-draft storyboards regenerated from their sessions' scripts
(tests/fixtures/autoarreglo/) and committed storyboards with the real failing field put back."""

from __future__ import annotations

import copy
import importlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]
anclas = importlib.import_module("anclas")
A = importlib.import_module("autoarreglo")
construir = importlib.import_module("construir")
critico = importlib.import_module("critico")
edicion = importlib.import_module("edicion")
producir = importlib.import_module("producir")
puertas = importlib.import_module("puertas")

FIX = RAIZ / "tests" / "fixtures" / "autoarreglo"
V2 = RAIZ / "video-v2"


def cargar(ref: str) -> tuple[Path, dict, list[dict]]:
    proy = V2 / ref
    return (
        proy,
        json.loads((proy / "storyboard.json").read_text(encoding="utf-8")),
        json.loads((proy / "assets" / "words.json").read_text(encoding="utf-8")),
    )


def borrador(ref: str) -> dict:
    return json.loads((FIX / f"{ref}.storyboard.json").read_text(encoding="utf-8"))


def errores(proy: Path, sb: dict, words: list[dict]) -> list[str]:
    """The static gate of construir --validar, in process (minus repetition/script/clips_sin_ver)."""
    sb = copy.deepcopy(sb)
    e = construir.validar(sb, words)
    if e:
        return e
    if edicion.preparar(proy, sb) is not None:
        e = construir.errores_seleccion(sb, proy)
    return e + puertas.errores(sb, construir.plan(sb, words))


def bucle(proy, sb, words, rondas=4):
    for _ in range(rondas):
        sb, hechos, _ = A.arreglar_storyboard(sb, words, errores(proy, sb, words))
        if not hechos:
            break
    return sb, errores(proy, sb, words)


def con(e: list[str], trozo: str) -> list[str]:
    return [x for x in e if trozo in x]


class AnclasTest(unittest.TestCase):
    def test_desplazar_suma_el_desplazamiento(self):
        self.assertEqual(A.desplazar("6:shares$+0.2", 0.3), "6:shares$+0.5")
        self.assertEqual(A.desplazar("4:x", -0.47), "4:x-0.47")
        self.assertEqual(A.desplazar("4:x+0.2", -0.2), "4:x")

    def test_ancla_de_palabra_es_la_inversa(self):
        _, _, w = cargar("anne-scheiber")
        for i in (0, 7, len(w) // 2, len(w) - 1):
            self.assertEqual(anclas.palabra(w, A.ancla_de_palabra(w, i))[0], i)
            self.assertTrue(anclas.palabra(w, A.ancla_de_palabra(w, i, True))[1])

    def test_guion_renumerado_da_las_anclas_que_puso_la_persona(self):
        # anne-scheiber draft (session e248c34b): anchors written against guion entries, not sentences
        proy, final, w = cargar("anne-scheiber")
        sb = borrador("anne-scheiber")
        e = errores(proy, sb, w)
        self.assertTrue(con(e, "ancla '4:tax'"))
        nuevo, _, pend = A.arreglar_storyboard(sb, w, e)
        txt = json.dumps(nuevo)
        for ok in (
            '"6:tax"',
            '"5:missing"',
            '"8:bigger"',
        ):  # what the committed storyboard says
            self.assertIn(ok, txt)
            self.assertIn(ok, json.dumps(final))
        # 'decades' is said twice: picking one is a guess, not a fix
        self.assertTrue(con(pend, "'9:decades'"))
        self.assertIn('"9:decades"', txt)

    def test_fin_de_frase_sin_palabra(self):
        # hot-inflation draft (session 020d7224): "4$"
        proy, final, w = cargar("hot-inflation")
        sb = borrador("hot-inflation")
        e = errores(proy, sb, w)
        self.assertEqual(
            e, ["ancla mal escrita: '4$' (formato: 'frase[:palabra[#n]][$][+seg]')"]
        )
        _, hechos, _ = A.arreglar_storyboard(sb, w, e)
        self.assertEqual(hechos, ["ancla '4$' -> '4:missing$'"])
        self.assertIn('"4:missing$"', json.dumps(final))

    def test_palabra_dentro_de_compuesta(self):
        # session 16ecbfd9: '2:ninety' in «Two thousand: ninety-three cents.»
        _, sb, w = cargar("interest-vs-defense")
        txt = json.dumps(sb)
        viejo = next(a for a in txt.split('"') if a.startswith("2:ninety-three"))
        sb = json.loads(txt.replace(f'"{viejo}"', '"2:ninety"'))
        e = construir.validar(copy.deepcopy(sb), w)
        self.assertTrue(con(e, "'ninety' aparece 0 vez/veces en la frase 2"))
        nuevo, _, pend = A.arreglar_storyboard(sb, w, e)
        self.assertEqual(pend, [])
        self.assertEqual(construir.validar(nuevo, w), [])


class TiemposTest(unittest.TestCase):
    def test_borrador_hot_inflation_solo_deja_lo_no_mecanico(self):
        # real sequence: '4$', then an empty title screen 2.5 s, then three texts shown < 0.5 s
        proy, _, w = cargar("hot-inflation")
        sb = borrador("hot-inflation")
        nuevo, quedan = bucle(proy, sb, w)
        for msg in ("se ve solo", "pantalla vacía", "ancla"):
            self.assertEqual(con(quedan, msg), [], msg)
        # "3.7" missing from `cifras` is content: it must still fail, untouched
        self.assertTrue(con(quedan, '"3.7" no sale de `cifras`'))
        self.assertEqual(nuevo["cifras"], sb["cifras"])
        self.assertEqual(nuevo["guion"], sb["guion"])

    def test_prueba_breve_alarga_hasta(self):
        # session 020d7224: "prueba airspace: se ve 0.94s ... pide 1.07s"
        proy, sb, w = cargar("hot-inflation")
        x = sb["pruebas"][0]
        x["hasta"] = A.desplazar(x["en"], 0.94)
        self.assertTrue(con(errores(proy, sb, w), "prueba airspace: se ve 0.94s"))
        _, quedan = bucle(proy, sb, w)
        self.assertEqual(con(quedan, "prueba airspace"), [])

    def test_ambiente_sin_dur(self):
        # session e248c34b: "sonidos[0]: 'maquina' es ambiente: lleva `dur` (s)"
        proy, sb, w = cargar("anne-scheiber")
        sb["sonidos"][0] = {"sfx": "maquina", "en": sb["sonidos"][0]["en"]}
        self.assertTrue(con(errores(proy, sb, w), "'maquina' es ambiente"))
        nuevo, quedan = bucle(proy, sb, w)
        self.assertEqual(con(quedan, "es ambiente"), [])
        self.assertGreaterEqual(nuevo["sonidos"][0]["dur"], 1.0)

    def test_contador_anclado_a_la_cifra(self):
        # session e248c34b: "escena 1: el contador de 22,000,000 arranca 0.69s antes"
        proy, sb, w = cargar("anne-scheiber")
        sb["escenas"][1]["en"] = "1"
        self.assertTrue(con(errores(proy, sb, w), "contador de 22,000,000 arranca"))
        nuevo, quedan = bucle(proy, sb, w)
        self.assertEqual(con(quedan, "contador"), [])
        self.assertEqual(
            nuevo["escenas"][1]["en"], "1:twenty-two"
        )  # what the person wrote


class CineTest(unittest.TestCase):
    def test_titulo_de_foto_cine_pasa_a_rotulo(self):
        # session 906488db: "escena 12: con aspecto cine el texto va en `rotulos` (con `pos`)"
        proy, sb, w = cargar("oseola-mccarty")
        s = sb["escenas"][12]
        s["titulo"] = s.pop("rotulos")[0]
        s.pop("pos")
        self.assertTrue(con(errores(proy, sb, w), "escena 12: con aspecto cine"))
        nuevo, quedan = bucle(proy, sb, w)
        self.assertEqual(con(quedan, "aspecto cine"), [])
        r = nuevo["escenas"][12]["rotulos"]
        self.assertEqual([x["texto"] for x in r], ["*44* students, by 2014"])

    def test_dos_textos_en_foto_cine_no_es_mecanico(self):
        proy, sb, w = cargar("oseola-mccarty")
        s = sb["escenas"][12]
        s["titulo"] = s.pop("rotulos")[0]
        s["kicker"] = {"texto": "By 2014", "en": s["en"]}
        nuevo, _, pend = A.arreglar_storyboard(sb, w, errores(proy, sb, w))
        self.assertEqual(nuevo["escenas"][12], sb["escenas"][12])
        self.assertTrue(con(pend, "escena 12: con aspecto cine"))

    def test_duotono_sin_archivo_va_en_color(self):
        # session 906488db: "imagenes.tabla: duotono solo para archivo real"
        proy, sb, w = cargar("oseola-mccarty")
        sb["imagenes"]["tabla"].pop("color")
        self.assertTrue(con(errores(proy, sb, w), "imagenes.tabla: duotono"))
        nuevo, quedan = bucle(proy, sb, w)
        self.assertEqual(con(quedan, "duotono"), [])
        self.assertIs(nuevo["imagenes"]["tabla"]["color"], True)

    def test_rotulos_solapados(self):
        # session 906488db: '"Hattiesburg, Mississippi" y "Campus: *blocks away*" se solapan'
        proy, sb, w = cargar("oseola-mccarty")
        sb["escenas"][7]["rotulos"].insert(
            0, {"texto": "Hattiesburg, Mississippi", "en": "9", "estilo": "big"}
        )
        self.assertTrue(con(errores(proy, sb, w), "se solapan"))
        nuevo, quedan = bucle(proy, sb, w)
        self.assertEqual(con(quedan, "se solapan"), [])
        self.assertEqual(nuevo["escenas"][7]["rotulos"][0]["hasta"], "9:blocks")


class NoMecanicoTest(unittest.TestCase):
    """Real non-mechanical messages: nothing changes, every one comes back."""

    REALES = (
        "hay `cifras` y ninguna `pruebas`: enseña el documento real (mínimo 1)",
        'descripción: "3.7" no sale de `cifras`',
        'guion data: "three point seven" no sale de `cifras` (añade el dato con su fuente o corrige la cifra)',
        "fuente 'desierto' usada 3 veces (máx. 2): metraje nuevo para cada idea",
        "misma apertura: foto",
        "mismo final: revelacion",
        "variedad: `foto` + `titulo` son el 80% de las escenas (≤70%): cambia alguna por `grafica`",
        "G-GIRO: hueco máx. sin giro 12.6 s (≤10 s)",
        "clips.cartas: `visto` sin hoja (origen cambiado o sin bajar). Corre `python tools/broll.py lote <proyecto>` y mírala",
    )

    def test_nada_cambia(self):
        _, sb, w = cargar("hot-inflation")
        nuevo, hechos, pend = A.arreglar_storyboard(sb, w, self.REALES)
        self.assertEqual((nuevo, hechos, pend), (sb, [], list(self.REALES)))


class ProyectoTemporal(unittest.TestCase):
    """arreglar() writes the storyboard: always on a copy."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.proy = self.tmp / "hot-inflation"
        (self.proy / "assets").mkdir(parents=True)
        for f in ("storyboard.json", "index.html", "assets/words.json"):
            shutil.copy(V2 / "hot-inflation" / f, self.proy / f)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sb(self):
        return json.loads((self.proy / "storyboard.json").read_text(encoding="utf-8"))

    def test_contraste_fondo_suave_y_foto_pendiente(self):
        html = (self.proy / "index.html").read_text(encoding="utf-8")
        vs = critico.ventanas(critico.plan_de_html(html))
        esc = self.sb()["escenas"]
        no_foto = next(
            k
            for k, e in enumerate(esc)
            if e["tipo"] != "foto" and not e.get("fondo_suave")
        )
        foto = next(k for k, e in enumerate(esc) if e["tipo"] == "foto")
        t1, t2 = (sum(vs[k]) / 2 for k in (no_foto, foto))
        detalle = f'2 textos ilegibles: "Now" 2.84:1 (< 3) en t≈{t1:.2f}s; "or" 2.59:1 (< 3) en t≈{t2:.2f}s'
        hechos, pend, voz = A.arreglar(self.proy, {"contraste": detalle})
        self.assertTrue(self.sb()["escenas"][no_foto]["fondo_suave"])
        self.assertEqual(len(hechos), 1)
        self.assertEqual(
            len(pend), 1
        )  # fondo_suave does not exist for a photo: Claude decides
        self.assertFalse(voz)

    def test_ritmo_golpe_en_el_tramo_quieto(self):
        w = json.loads(
            (self.proy / "assets" / "words.json").read_text(encoding="utf-8")
        )
        t = w[len(w) // 2]["start"]
        detalle = f"Tramo quieto más largo : 4.8 s (desde t≈{t - 2:.1f} s)\n✗ Hay 4.8 s sin nada nuevo"
        hechos, pend, _ = A.arreglar(self.proy, {"ritmo": detalle})
        self.assertTrue(hechos and hechos[0].startswith("golpe"))
        self.assertEqual(pend, [])

    def test_critico_v1_resintetiza_m1_parchea_resto_pendiente(self):
        def f(crit, sev, det, parche=None):
            return {
                "criterio": crit,
                "severidad": sev,
                "t": 3.0,
                "t_fin": None,
                "escena": 1,
                "detalle": det,
                "parche": parche,
            }

        fallos = [
            f(
                "V1",
                "media",
                'silencio de 0.9s dentro de frase tras "dollars" (se arregla re-sintetizando la voz, no en el storyboard)',
            ),
            f(
                "M1",
                "media",
                "música tapa la voz",
                {"op": "musica_volumen", "valor": 0.2},
            ),
            f("G1", "media", "gancho flojo"),
            f("V1", "baja", "silencio de 0.5s entre frases"),
        ]
        informe = {"rondas": [{"fallos": fallos}]}
        _, pend, voz = A.arreglar(self.proy, {}, informe, ("alta", "media"))
        self.assertTrue(voz)
        self.assertEqual(self.sb()["musica"]["volumen"], 0.2)
        self.assertEqual([x.split()[1] for x in pend], ["V1", "G1"])  # V1 pending until re-measured

    def test_otra_puerta_es_pendiente_y_no_escribe(self):
        antes = (self.proy / "storyboard.json").read_text(encoding="utf-8")
        hechos, pend, _ = A.arreglar(self.proy, {"repeticion": "mismo final: cta"})
        self.assertEqual((hechos, pend), ([], ["repeticion: mismo final: cta"]))
        self.assertEqual(
            (self.proy / "storyboard.json").read_text(encoding="utf-8"), antes
        )


class BucleProducirTest(unittest.TestCase):
    """producir_auto: fixes BEFORE the same gates, stops when nothing mechanical is left."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.orig = producir.producir, A.arreglar

    def tearDown(self):
        producir.producir, A.arreglar = self.orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def falla(self, veces):
        llamadas = []

        def falso(proy):
            llamadas.append(proy)
            producir.DETALLES.clear()
            if len(llamadas) <= veces:
                producir.DETALLES["storyboard"] = (False, "storyboard inválido:\n  - x")
                raise SystemExit("✗ puertas fallidas: storyboard")
            producir.DETALLES["storyboard"] = (True, "")
            return {"ok": True}

        producir.producir = falso
        return llamadas

    def test_arregla_y_vuelve_a_pasar_las_puertas(self):
        llamadas = self.falla(1)
        A.arreglar = lambda *a, **k: (["ancla '4$' -> '4:missing$'"], [], False)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(
                producir.producir_auto(self.tmp, critico_=False), {"ok": True}
            )
        self.assertEqual(len(llamadas), 2)

    def test_sin_arreglo_mecanico_para_y_lista_lo_pendiente(self):
        self.falla(9)
        A.arreglar = lambda *a, **k: (
            [],
            ['descripción: "3.7" no sale de `cifras`'],
            False,
        )
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            producir.producir_auto(self.tmp, critico_=False)
        self.assertIn('"3.7" no sale de `cifras`', out.getvalue())

    def test_maximo_de_rondas(self):
        llamadas = self.falla(99)
        A.arreglar = lambda *a, **k: (["algo"], [], False)
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            producir.producir_auto(self.tmp, critico_=False)
        self.assertEqual(len(llamadas), producir.RONDAS_AUTO + 1)


if __name__ == "__main__":
    unittest.main()
