"""Gates against the defects of the first published average-401k (6-nov-2026).

fixtures/average401k/v1 is that storyboard, rebuilt from the session's recorded fix script: its timings
come from the corrected voice (the first take was re-synthesized), so "401k" sits on the corrected word.
v2 is what was republished after those fixes: the gates must flag v1 and leave v2 alone.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]

import construir as c
import critico
import medir_texto
import puertas

from omega import cli, config, publish, publish_meta

FIX = Path(__file__).parent / "fixtures" / "average401k"


def cargar(v: str) -> tuple[dict, list[dict]]:
    return (
        json.loads((FIX / v / "storyboard.json").read_text(encoding="utf-8")),
        json.loads((FIX / v / "words.json").read_text(encoding="utf-8")),
    )


def plan_de(v: str) -> tuple[dict, dict]:
    sb, words = cargar(v)
    return sb, c.plan(sb, words)


class PrimeraVersionTest(unittest.TestCase):
    """Each defect the user saw, flagged at its scene."""

    def test_limpio_con_voz_es_voz_sin_subtitulo(self):
        _, p = plan_de("v1")
        err = " ".join(puertas.voz_sin_subtitulo(p))
        for k in (2, 4, 13):
            self.assertIn(f"escena {k}", err)

    def test_401k_se_pronuncia_mal(self):
        sb, _ = plan_de("v1")
        err = puertas.pronunciacion(sb)
        self.assertEqual(len(err), 2)  # hook and close
        self.assertIn("four-oh-one-k", err[0])

    def test_fondo_tenue_sin_texto_es_pantalla_vacia(self):
        _, p = plan_de("v1")
        err = " ".join(puertas.pantalla_vacia(p))
        for k in (11, 14):
            self.assertIn(f"escena {k}", err)

    def test_linea_del_gancho_dura_demasiado_poco(self):
        _, p = plan_de("v1")
        err = puertas.texto_breve(p)
        self.assertEqual(len(err), 1, err)
        self.assertIn("Still ahead", err[0])

    def test_dos_rotulos_en_la_misma_posicion_se_solapan(self):
        _, p = plan_de("v1")
        err = puertas.rotulos_solapados(p)
        self.assertEqual(len(err), 1, err)
        self.assertIn("escena 10", err[0])

    def test_la_version_corregida_solo_falla_por_el_tema(self):
        """`tema` went unnoticed through v2: see test_cero_errores.PlanTest."""
        sb, p = plan_de("v2")
        self.assertEqual(puertas.errores(sb, p), puertas.tema_valido(sb))


class ReglasTest(unittest.TestCase):
    def _plan(self, **escena):
        s = {"tipo": "foto", "t0": 0.0, "t1": 4.0, "texto_visible": []} | escena
        return {"escenas": [s], "words": [], "subtitulos": [0, 0]}

    def test_variedad_rechaza_el_patron_clip_y_texto(self):
        def esc(*ts):
            return {"ref": "nuevo", "escenas": [{"tipo": t} for t in ts]}

        mal = puertas.variedad_escenas(esc(*["foto", "titulo"] * 6, "cta"))
        self.assertEqual(len(mal), 2, mal)  # 92 % in the pair and only 3 types
        bien = esc(*["foto"] * 4, *["titulo"] * 3, "grafica", "puntos", "revelacion")
        self.assertEqual(puertas.variedad_escenas(bien), [])
        viejo = esc("foto", "titulo") | {"ref": "nvidia-weight"}
        self.assertEqual(puertas.variedad_escenas(viejo), [])

    def test_otros_terminos_medidos_en_misaki(self):
        for mal in ("a 401(k)", "your 403(b)", "the 403b", "a 457(b)", "a 529 plan"):
            self.assertTrue(puertas.pronunciacion({"guion": [{"texto": mal}]}), mal)
        for bien in ("four-oh-one-k", "five twenty-nine plan", "401 people", "$529"):
            self.assertEqual(
                puertas.pronunciacion({"guion": [{"texto": bien}]}), [], bien
            )

    def test_rotulos_que_no_coinciden_no_se_solapan(self):
        r = lambda en, **k: {"texto": "x", "en": en, **k}
        for rotulos in (
            [r(0.5, hasta=1.5), r(1.5)],  # one leaves as the other enters
            [r(0.5, top=200), r(1.0, top=900)],  # different height
        ):
            self.assertEqual(
                puertas.rotulos_solapados(self._plan(rotulos=rotulos)), [], rotulos
            )

    def test_foto_a_plena_opacidad_no_es_pantalla_vacia(self):
        p = self._plan(rotulos=[{"texto": "x", "en": 3.0}])
        self.assertEqual(puertas.pantalla_vacia(p), [])

    def test_titulo_sin_fondo_con_texto_tarde_es_pantalla_vacia(self):
        p = self._plan(tipo="titulo", lineas=[{"texto": "x", "en": 2.0}])
        self.assertTrue(puertas.pantalla_vacia(p))

    def test_voz_fuera_del_rango_de_subtitulos_sin_texto_en_escena(self):
        p = self._plan()
        p["words"] = [
            {"text": "hola", "start": 1.0, "end": 1.2},
            {"text": "x", "start": 9, "end": 9.1},
        ]
        p["subtitulos"] = [1, 1]
        self.assertTrue(puertas.voz_sin_subtitulo(p))

    def test_limpio_en_una_pausa_de_voz_no_falla(self):
        p = self._plan(limpio=True)
        p["words"] = [{"text": "hola", "start": 5.0, "end": 5.2}]
        self.assertEqual(puertas.voz_sin_subtitulo(p), [])

    def test_videos_anteriores_a_la_puerta_quedan_exentos(self):
        sb, p = plan_de("v1")
        self.assertEqual(puertas.errores({**sb, "ref": "grace-groner"}, p), [])


class ValidarDeUnaVezTest(unittest.TestCase):
    def _proyecto(self, v: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        proy = tmp / "video"
        (proy / "assets").mkdir(parents=True)
        shutil.copy(FIX / v / "storyboard.json", proy)
        shutil.copy(FIX / v / "words.json", proy / "assets")
        return proy

    def _validar(self, proy: Path, contraste=("contraste: sale mal",)):
        with (
            mock.patch(
                "medir_parecido.puerta_repeticion", return_value=(False, "repite X")
            ),
            mock.patch("guionista.puerta_guion", return_value=(False, "G-CIERRE: mal")),
            mock.patch.object(
                c, "errores_contraste", return_value=list(contraste)
            ) as con,
            self.assertRaises(c.StoryboardError) as ctx,
        ):
            c.construir(proy, solo_validar=True)
        return str(ctx.exception), con

    def test_reporta_todos_los_fallos_juntos(self):
        msg, con = self._validar(self._proyecto("v1"))
        for trozo in (
            "four-oh-one-k",
            "voz sin subtítulo",
            "pantalla vacía",
            "Still ahead",
            "se solapan",
            "repite X",
            "G-CIERRE",
            "contraste: sale mal",
        ):
            self.assertIn(trozo, msg)
        con.assert_called_once()

    def test_error_estructural_no_oculta_los_demas_y_avisa_del_contraste(self):
        proy = self._proyecto("v1")
        sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
        sb["escenas"][1]["tipo"] = "no-existe"
        (proy / "storyboard.json").write_text(json.dumps(sb), encoding="utf-8")
        msg, con = self._validar(proy)
        for trozo in ("no-existe", "four-oh-one-k", "repite X", "contraste: no medido"):
            self.assertIn(trozo, msg)
        con.assert_not_called()

    def test_producir_deja_el_contraste_para_su_propia_puerta(self):
        with (
            mock.patch("medir_parecido.puerta_repeticion", return_value=(True, "")),
            mock.patch("guionista.puerta_guion", return_value=(True, "")),
            mock.patch.object(c, "errores_contraste") as con,
            self.assertRaises(c.StoryboardError),
        ):
            c.construir(self._proyecto("v1"), solo_validar=True, sin_contraste=True)
        con.assert_not_called()

    def test_build_completo_tambien_bloquea_las_puertas_nuevas(self):
        with self.assertRaises(c.StoryboardError) as ctx:
            c.construir(self._proyecto("v1"))
        self.assertIn("four-oh-one-k", str(ctx.exception))


class AvisoFinalL1Test(unittest.TestCase):
    """OCR of the real final MP4 (t=33.5 s, renders/critica/r0.ocr.json): the screen shows `completo`,
    while the critic searched for the short `lineas` and reported an unread disclaimer."""

    COMPLETO = (
        "Not financial advice. Source: Vanguard How America Saves 2026, plan participants 65+, balances at "
        "Dec 31, 2025. Excludes IRAs, pensions and Social Security. Vanguard plans skew toward larger employers."
    )
    OCR = (
        "Not financial advice. Source: Vanguard How America",
        "Saves 2026, plan participants 65+, balances at Dec 31,",
        "2025. Excludes IRAs, pensions and Social Security.",
        "Vanguard plans skew toward larger employers.",
    )
    AV: ClassVar[dict] = {
        "lineas": [
            "Not financial advice · Vanguard plans, 2025 · excludes IRAs, pensions"
        ],
        "completo": COMPLETO,
        "ventanas": [[5.0, 26.5]],
        "final": 33.2,
    }

    def test_en_la_tarjeta_final_se_espera_el_texto_completo(self):
        esp = critico.esperados_aviso(self.AV, 34.6)
        self.assertEqual(
            [(e["texto"], e["t0"]) for e in esp],
            [(self.AV["lineas"][0], 5.0), (self.COMPLETO, 33.6)],
        )

    def test_sin_completo_sigue_esperando_las_lineas(self):
        esp = critico.esperados_aviso(
            {**self.AV, "completo": None, "ventanas": []}, 34.6
        )
        self.assertEqual([e["texto"] for e in esp], self.AV["lineas"])

    def test_el_ocr_real_lee_el_aviso_completo(self):
        cajas = [
            {"texto": t, "conf": 1.0, "caja": [100, 1000 + 60 * i, 900, 1050 + 60 * i]}
            for i, t in enumerate(self.OCR)
        ]
        r = medir_texto.analizar(
            [{"t": 34.0, "ancho": 1080, "alto": 1920, "lineas": cajas}],
            critico.esperados_aviso({**self.AV, "ventanas": []}, 34.6),
        )
        self.assertEqual(r["no_leidos"], [])


class VeredictoTest(unittest.TestCase):
    def _ronda(self, *severidades):
        return {"fallos": [critico.fallo("L1", s, "x") for s in severidades]}

    def test_sin_fallos_bloqueantes_y_con_juicio_aprueba(self):
        v = critico.veredicto(self._ronda("media", "baja"), ["alta"], con_juicio=True)
        self.assertTrue(v["aprobado"], v)

    def test_un_fallo_alto_bloquea(self):
        v = critico.veredicto(self._ronda("alta"), ["alta"], con_juicio=True)
        self.assertFalse(v["aprobado"])
        self.assertEqual(len(v["bloqueantes"]), 1)

    def test_la_rubrica_bloquea_fallos_medios(self):
        """User decision 12-nov: medium faults (voice masked, mid-phrase silence) do not ship.
        Low stays a warning until L1's Shorts-UI zone is checked against a real phone capture."""
        rubrica = Path(critico.__file__).with_name("rubrica.json")
        bloquean = json.loads(rubrica.read_text(encoding="utf-8"))["severidad_bloquea"]
        self.assertFalse(
            critico.veredicto(self._ronda("media"), bloquean, con_juicio=True)[
                "aprobado"
            ]
        )
        self.assertTrue(
            critico.veredicto(self._ronda("baja"), bloquean, con_juicio=True)[
                "aprobado"
            ]
        )

    def test_sin_mirar_el_video_no_aprueba(self):
        v = critico.veredicto(self._ronda(), ["alta"], con_juicio=False)
        self.assertFalse(v["aprobado"])
        self.assertIn("juicio", v["motivo"])


class JuicioDeEseArchivoTest(unittest.TestCase):
    def test_un_juicio_de_otro_render_no_cuenta(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.assertFalse(critico.juicio_de(tmp, "abc"))
        (tmp / "checklist.json").write_text(
            '{"escenas": [], "cifras": []}', encoding="utf-8"
        )
        (tmp / "juicio.json").write_text(
            '{"fallos": [], "mp4_sha256": "viejo"}', encoding="utf-8"
        )
        self.assertFalse(critico.juicio_de(tmp, "abc"))
        self.assertTrue(critico.juicio_de(tmp, "viejo"))


class ExigirCriticoTest(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.mp4 = tmp / "final.mp4"
        self.mp4.write_bytes(b"video bueno")
        self.dir = tmp / "video-v2" / "r" / "renders" / "critica"
        self.dir.mkdir(parents=True)
        self.raiz = tmp

    def _aprobar(self, aprobado=True):
        (self.dir / "aprobacion.json").write_text(
            json.dumps(
                {
                    publish.sha256_de(self.mp4): {
                        "aprobado": aprobado,
                        "motivo": "1 fallos alta",
                    }
                }
            ),
            encoding="utf-8",
        )

    def _exigir(self):
        return publish.exigir_critico("r", self.mp4, self.raiz)

    def test_sin_critico_no_se_publica(self):
        self.assertIn("no hay crítico", self._exigir())

    def test_aprobado_sobre_ese_archivo_se_publica(self):
        self._aprobar()
        self.assertIsNone(self._exigir())

    def test_el_critico_rechazo_ese_archivo(self):
        self._aprobar(False)
        self.assertIn("1 fallos alta", self._exigir())

    def test_otro_archivo_aunque_el_critico_aprobara_uno(self):
        self._aprobar()
        self.mp4.write_bytes(b"re-render posterior")
        self.assertIn("otro archivo", self._exigir())


class PublicarExigeCriticoTest(unittest.TestCase):
    """Going live without the critic's pass on that file is refused; private uploads are not publishing."""

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.mp4 = tmp / "f.mp4"
        self.mp4.write_bytes(b"x")
        data = tmp / "data"
        data.mkdir()
        (data / "publish_r.json").write_text(
            json.dumps(
                {
                    "production_ref": "r",
                    "video_path": str(self.mp4),
                    "title": "t",
                    "description": "d",
                    "privacy_status": "public",
                    "video_id": "abc",
                }
            ),
            encoding="utf-8",
        )
        for p in (
            mock.patch.object(config, "DATA_DIR", data),
            mock.patch.object(config, "DB_PATH", data / "omega.sqlite"),
            mock.patch.object(publish, "RAIZ_PROYECTO", tmp),
        ):
            p.start()
        self.addCleanup(mock.patch.stopall)
        self.tmp = tmp

    def _cli(self, fn, *args):
        with (
            mock.patch.object(sys, "argv", ["omega.cli", *args]),
            mock.patch("sys.stdout"),
        ):
            try:
                fn()
            except SystemExit:
                pass

    def test_las_cuatro_salidas_en_vivo_se_rechazan(self):
        casos = [
            (cli.cmd_publish, ("publish", "r"), publish, "upload_video"),
            (
                cli.cmd_publish_fb,
                ("publish-fb", "r", "--publicar"),
                publish_meta,
                "upload_facebook_reel",
            ),
            (
                cli.cmd_publish_ig,
                ("publish-ig", "r", "--publicar"),
                publish_meta,
                "upload_instagram_reel",
            ),
            (
                cli.cmd_programar,
                ("programar", "r", "--ahora"),
                publish,
                "hacer_publico",
            ),
            (cli.cmd_programar, ("programar", "r"), publish, "programar"),
        ]
        for fn, args, mod, nombre in casos:
            with self.subTest(args=args), mock.patch.object(mod, nombre) as subir:
                self._cli(fn, *args)
                subir.assert_not_called()

    def test_carrusel_e_historia_en_vivo_se_rechazan(self):
        plan = {"carrusel": ["a.png"], "historia": "h.mp4"}
        with (
            mock.patch.object(
                cli, "_proyecto_de", return_value=self.tmp / "video-v2" / "r"
            ),
            mock.patch.object(publish_meta, "plan_social", return_value=plan),
            mock.patch.object(
                sys, "argv", ["omega.cli", "publish-social", "r", "--publicar"]
            ),
            mock.patch("sys.stdout"),
            self.assertRaises(SystemExit),
        ):
            cli.cmd_publish_social()

    def test_borradores_privados_no_piden_critico(self):
        d = config.DATA_DIR / "publish_r.json"
        j = json.loads(d.read_text(encoding="utf-8"))
        d.write_text(json.dumps({**j, "privacy_status": "private"}), encoding="utf-8")
        ok = {"video_id": "v", "url": "u", "id": "1", "status": "s"}
        with mock.patch.object(publish, "upload_video", return_value=ok) as yt:
            self._cli(cli.cmd_publish, "publish", "r")
        yt.assert_called_once()
        with mock.patch.object(
            publish_meta, "upload_facebook_reel", return_value=ok
        ) as fb:
            self._cli(cli.cmd_publish_fb, "publish-fb", "r")
        fb.assert_called_once()


if __name__ == "__main__":
    unittest.main()
