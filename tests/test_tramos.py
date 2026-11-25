"""Per-scene re-render (video-v2/motor/tramos.py): what changed, which scenes, the trimmed page and the
splice. A wrong "only these scenes" ships a stale video, so every unplaceable change must say "whole"."""

from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "video-v2" / "motor")]
T = importlib.import_module("tramos")


def pagina(
    escenas=None, css="body{}", fondo=1.0, s1="Hola", audio_vol="0.5", video="a.mp4"
):
    plan = {
        "D": 9.0,
        "escenas": escenas
        or [
            {"t0": 0.0, "t1": 3.0, "fondo": {"opacidad": fondo}},
            {"t0": 3.0, "t1": 6.0},
            {"t0": 6.0, "t1": 9.0},
        ],
        "golpes": [4.5],
        "calientes": ["Nvidia"],
        "musica_volumen": 0.5,
    }
    return "\n".join(
        [
            "<html><head><style>",
            css,
            "</style></head><body>",
            '<div id="root" data-start="0" data-duration="9">',
            f'<audio id="vo" src="assets/voice.mp3" data-start="0" data-volume="{audio_vol}"></audio>',
            '<section id="s0" class="clip scene" data-start="0.000" data-duration="3.000"><b>A</b></section>',
            f'<section id="s1" class="clip scene" data-start="3.000" data-duration="3.000"><b>{s1}</b></section>',
            '<section id="s2" class="clip scene" data-start="6.000" data-duration="3.000"><b>C</b></section>',
            f'<div id="ph0" class="ph"><video id="ph0-img" class="clip" src="assets/v/{video}" data-start="6.000" data-duration="3.000" muted></video></div>',
            "</div>",
            "<script>window.PLAN = "
            + json.dumps(plan)
            + ";</script>",  # as construir writes it
            "</body></html>",
        ]
    )


def tramos(viejo, nuevo, av=None, an=None):
    spans, motivo = T.cambios(viejo, nuevo, av or {}, an or {})
    if spans is None:
        return None, motivo
    plan, _ = T._plan(nuevo)
    return T.ventanas(spans, plan)


class CambiosTest(unittest.TestCase):
    def test_cambio_que_con_su_margen_cubre_la_pelicula_pide_el_completo(
        self,
    ):
        v, m = tramos(pagina(), pagina(s1="Adiós"))
        # s1 spans 3-6: the 1 s margin touches s0 (ends at 3) and s2 (starts at 6)
        self.assertEqual(v, None)  # 9 s of a 9 s film: over MAX_FRAC, whole render
        self.assertIn("completo", m)

    def test_cambio_en_el_plan_marca_solo_su_escena(self):
        largo: list[dict] = [{"t0": float(i), "t1": float(i + 1)} for i in range(9)]
        viejo = pagina(escenas=largo)
        nuevo_esc = [dict(e) for e in largo]
        nuevo_esc[4]["fondo"] = {"opacidad": 0.5}
        v, _ = tramos(viejo, pagina(escenas=nuevo_esc))
        self.assertEqual(
            v, [(3.0, 6.0)]
        )  # scene 4 (4-5) +-1 s -> scenes 3, 4, 5 merged

    def test_cambios_sin_tiempo_piden_el_completo(self):
        for nuevo, motivo in [
            (pagina(css="body{color:red}"), "sin tiempo"),
            (pagina(audio_vol="0.7"), "audio"),
        ]:
            v, m = tramos(pagina(), nuevo)
            self.assertIsNone(v)
            self.assertIn(motivo, m)
        viejo = pagina().replace(
            '"calientes": ["Nvidia"]', '"calientes": ["Nvidia", "AMD"]'
        )
        self.assertIn("PLAN.calientes", tramos(pagina(), viejo)[1])
        viejo = pagina().replace('"musica_volumen": 0.5', '"musica_volumen": 0.4')
        self.assertIn("audio", tramos(pagina(), viejo)[1])

    def test_asset_cambiado_marca_donde_se_ve_y_si_no_se_sabe_pide_el_completo(self):
        largo = [{"t0": float(i), "t1": float(i + 1)} for i in range(9)]
        p = pagina(escenas=largo)
        av = {"assets/v/a.mp4": "1", "assets/voice.mp3": "1", "assets/x.png": "1"}
        self.assertEqual(
            tramos(p, p, av, {**av, "assets/v/a.mp4": "2"})[0], [(5.0, 9.0)]
        )  # the video shows 6-9
        self.assertIn("audio", tramos(p, p, av, {**av, "assets/voice.mp3": "2"})[1])
        self.assertIn("no sé dónde", tramos(p, p, av, {**av, "assets/x.png": "2"})[1])
        # used in the CSS too: the whole film, even though a scene line also names it
        p = pagina(escenas=largo, css="body{background:url(assets/img/fondo.jpg)}")
        p = p.replace("<b>C</b>", "<b>fondo</b>")
        av = {"assets/img/fondo.jpg": "1"}
        self.assertIn(
            "toda la película", tramos(p, p, av, {"assets/img/fondo.jpg": "2"})[1]
        )

    def test_listas_que_no_son_eventos_y_audio_anidado_piden_el_completo(self):
        viejo = pagina().replace('"golpes"', '"subtitulos": [2.0, 4.0], "golpes"')
        nuevo = viejo.replace("[2.0, 4.0]", "[2.0, 8.0]")  # a range, not two points
        self.assertIn("PLAN.subtitulos", tramos(viejo, nuevo)[1])
        nuevo = pagina(s1='Hola<audio src="assets/sfx/x.wav" data-start="4"></audio>')
        self.assertIn("audio", tramos(pagina(), nuevo)[1])

    def test_sin_cambios_no_hay_tramos(self):
        self.assertEqual(tramos(pagina(), pagina()), (None, "sin cambios visibles"))


class RecortarTest(unittest.TestCase):
    def test_quita_el_audio_y_los_videos_fuera_del_tramo_y_deja_el_dom(self):
        r = T.recortar(pagina(), 3.0, 6.0)
        self.assertNotIn("<audio", r)
        self.assertNotIn("<video", r)
        self.assertIn('<div id="ph0" class="ph"></div>', r)  # motor.js looks it up
        self.assertEqual(r.count("<section"), 3)
        self.assertIn("<video", T.recortar(pagina(), 5.0, 7.0))

    def test_frame_redondea_como_hyperframes(self):
        self.assertEqual(T.frame(46.38, 30), 1391)
        self.assertEqual(
            T.frame(0.05, 30), 2
        )  # 1.5 -> 2 (Math.round), Python's round gives 2 too
        self.assertEqual(T.frame(0.15, 30), 5)  # 4.5 -> 5; round() would give 4


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs ffmpeg")
class EmpalmarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def color(self, nombre, color, dur, audio=False):
        out = self.tmp / nombre
        cmd = [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color={color}:s=64x64:r=30:d={dur}",
        ]
        if audio:
            cmd += ["-f", "lavfi", "-i", f"sine=f=440:d={dur}", "-c:a", "aac"]
        subprocess.run(
            [*cmd, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)], check=True
        )
        return out

    def rojo(self, mp4, f):
        r = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(mp4),
                "-vf",
                f"select=eq(n\\,{f})",
                "-frames:v",
                "1",
                "-s",
                "1x1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ],
            capture_output=True,
            check=True,
        ).stdout
        return r[0] > 200 and r[2] < 60

    def test_reemplaza_solo_el_tramo_y_conserva_frames_y_audio(self):
        viejo = self.color("viejo.mp4", "blue", 3, audio=True)
        tramo = self.color("t.mp4", "red", 1)
        salida = self.tmp / "nuevo.mp4"
        ok, det = T.empalmar(viejo, [(1.0, 2.0, tramo)], 30, salida, gpu=False)
        self.assertTrue(ok, det)
        self.assertEqual(T.n_frames(salida), 90)
        self.assertEqual(
            [self.rojo(salida, f) for f in (29, 30, 59, 60)], [False, True, True, False]
        )
        a = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "csv=p=0",
                str(salida),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(a, "aac")

    def test_tramo_con_frames_de_mas_no_se_empalma(self):
        viejo = self.color("viejo.mp4", "blue", 3)
        ok, det = T.empalmar(
            viejo,
            [(1.0, 2.0, self.color("t.mp4", "red", 1.5))],
            30,
            self.tmp / "n.mp4",
            False,
        )
        self.assertFalse(ok)
        self.assertIn("45 frames", det)


if __name__ == "__main__":
    unittest.main()
