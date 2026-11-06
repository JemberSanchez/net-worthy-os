"""`publicar`: one command for every network, which never lets an older render pass as uploaded."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "video-v2" / "motor"))

import hfversion
import producir

from omega import cli, config, publish, publish_meta


class PublicarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        data = Path(self.tmp.name)
        self.mp4 = data / "x.mp4"
        self.mp4.write_bytes(b"x")
        self.pub = data / "publish_s9.json"
        self.pub.write_text(
            json.dumps(
                {
                    "production_ref": "s9",
                    "video_path": str(self.mp4),
                    "title": "T",
                    "description": "D",
                }
            ),
            encoding="utf-8",
        )
        self.reel = mock.Mock(
            return_value={"media_id": "ig1", "url": "u", "status": "ok"}
        )
        self.fb = mock.Mock(return_value={"video_id": "fb1", "url": "u"})
        self.yt = mock.Mock(return_value={"video_id": "yt1", "url": "u"})
        self.prog = mock.Mock()
        for p in (
            mock.patch.object(config, "DATA_DIR", data),
            mock.patch.object(config, "DB_PATH", data / "omega.sqlite"),
            mock.patch.object(publish, "exigir_critico", return_value=None),
            mock.patch.object(publish, "upload_video", self.yt),
            mock.patch.object(publish, "programar", self.prog),
            mock.patch.object(publish_meta, "upload_facebook_reel", self.fb),
            mock.patch.object(publish_meta, "upload_instagram_reel", self.reel),
            mock.patch.object(
                publish_meta,
                "plan_social",
                return_value={"carrusel": [], "historia": None},
            ),
            mock.patch.object(cli, "_proyecto_de", return_value=data),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _publicar(self, *args):
        with mock.patch.object(sys, "argv", ["omega.cli", "publicar", "s9", *args]):
            cli.cmd_publicar()

    def test_sin_flag_no_envia_nada(self):
        self._publicar()
        self.yt.assert_not_called()
        self.fb.assert_not_called()
        self.reel.assert_not_called()

    def test_critico_no_aprobado_para_todo(self):
        with (
            mock.patch.object(publish, "exigir_critico", return_value="no"),
            self.assertRaises(SystemExit),
        ):
            self._publicar("--publicar")
        self.yt.assert_not_called()

    def test_sube_todo_y_repetir_no_duplica(self):
        self._publicar("--publicar")
        self._publicar("--publicar")
        self.assertEqual(self.yt.call_count, 1)
        self.assertEqual(self.fb.call_count, 1)
        self.assertEqual(self.reel.call_count, 1)
        self.assertEqual(self.prog.call_count, 1)

    def test_render_reemplazado_para_hasta_nombrarlo(self):
        self._publicar("--publicar")
        self.mp4.write_bytes(b"otro render")
        with self.assertRaises(SystemExit) as e:
            self._publicar("--publicar")
        self.assertIn("--reemplazar youtube,facebook,instagram", str(e.exception))
        self.assertEqual(self.reel.call_count, 1)

        self._publicar("--publicar", "--reemplazar", "instagram,youtube,facebook")
        self.assertEqual(self.reel.call_count, 2)
        self.assertEqual(self.yt.call_count, 2)
        d = json.loads(self.pub.read_text(encoding="utf-8"))
        self.assertEqual(d["subido"]["instagram"], publish.sha256_de(self.mp4))

    def test_estado_red(self):
        d = {"subido": {"youtube": "a"}}
        self.assertEqual(cli.estado_red(d, None, "youtube", "a"), "falta")
        self.assertEqual(cli.estado_red(d, "v", "youtube", "a"), "al dia")
        self.assertEqual(cli.estado_red(d, "v", "youtube", "b"), "reemplazado")
        self.assertEqual(cli.estado_red(d, "v", "facebook", "a"), "sin huella")


class AlinearCoreTest(unittest.TestCase):
    def test_solo_instala_si_la_version_difiere(self):
        with tempfile.TemporaryDirectory() as d:
            with (
                mock.patch.object(hfversion, "version", return_value="9.9.9"),
                mock.patch.object(hfversion, "version_core", return_value="9.9.9"),
                mock.patch.object(hfversion.subprocess, "run") as run,
            ):
                hfversion.alinear_core(d)
                run.assert_not_called()
            with (
                mock.patch.object(hfversion, "version", return_value="9.9.9"),
                mock.patch.object(hfversion, "version_core", return_value="1.0.0"),
                mock.patch.object(hfversion.subprocess, "run") as run,
            ):
                hfversion.alinear_core(d)
                self.assertIn("@hyperframes/core@9.9.9", run.call_args.args[0])

    def test_sin_core_no_hace_nada(self):
        with mock.patch.object(hfversion.subprocess, "run") as run:
            hfversion.alinear_core(None)
            run.assert_not_called()


class FallosCriticoTest(unittest.TestCase):
    def test_baja_solo_se_cuenta(self):
        inf = {
            "rondas": [
                {
                    "fallos": [
                        {"severidad": "alta", "x": 1},
                        {"severidad": "baja"},
                        {"severidad": "baja"},
                    ]
                }
            ]
        }
        out = producir.fallos_critico(inf, lambda f: f"L{f['x']}")
        self.assertEqual(out[0], "L1")
        self.assertIn("2 fallos baja", out[1])


if __name__ == "__main__":
    unittest.main()
