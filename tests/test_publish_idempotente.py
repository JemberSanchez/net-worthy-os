"""Un reintento de publicación NO puede duplicar: requisito para que una rutina programada corra sola.

La base (`production_video`, clave ref × red) es la fuente de verdad: si ya tiene ese ref en esa
red, el subidor no vuelve a llamar a la API.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omega import cli, config, publish, publish_meta


class PublicarIdempotenteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        data = Path(self.tmp.name)
        mp4 = data / "x.mp4"
        mp4.write_bytes(b"x")
        (data / "publish_s9.json").write_text(
            json.dumps(
                {
                    "production_ref": "s9",
                    "video_path": str(mp4),
                    "title": "T",
                    "description": "D",
                }
            ),
            encoding="utf-8",
        )
        self.p = [
            mock.patch.object(config, "DATA_DIR", data),
            mock.patch.object(config, "DB_PATH", data / "omega.sqlite"),
        ]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        self.tmp.cleanup()

    def _cli(self, *args):
        with mock.patch.object(sys, "argv", ["omega.cli", *args]):
            {
                "publish": cli.cmd_publish,
                "publish-ig": cli.cmd_publish_ig,
                "publish-fb": cli.cmd_publish_fb,
            }[args[0]]()

    def test_youtube_reintento_no_resube(self):
        up = mock.Mock(return_value={"video_id": "yt1", "url": "u"})
        with mock.patch.object(publish, "upload_video", up):
            self._cli("publish", "s9")
            self._cli("publish", "s9")
        self.assertEqual(up.call_count, 1)
        self.assertEqual(cli._video_id("s9"), "yt1")

    def test_instagram_en_vivo_se_registra_y_no_se_repite(self):
        up = mock.Mock(return_value={"media_id": "ig1", "url": "u"})
        with mock.patch.object(publish_meta, "upload_instagram_reel", up):
            self._cli("publish-ig", "s9", "--publicar")
            self._cli("publish-ig", "s9", "--publicar")
        self.assertEqual(up.call_count, 1)
        self.assertEqual(cli._video_id("s9", "instagram"), "ig1")

    def test_borrador_de_facebook_no_bloquea_publicar(self):
        up = mock.Mock(return_value={"video_id": "fb1", "url": "u"})
        with mock.patch.object(publish_meta, "upload_facebook_reel", up):
            self._cli("publish-fb", "s9")  # borrador: invisible, no cuenta
            self._cli("publish-fb", "s9", "--publicar")
            self._cli("publish-fb", "s9", "--publicar")
        self.assertEqual(up.call_count, 2)

    def test_forzar_resube(self):
        cli._registrar_video("s9", "viejo")
        up = mock.Mock(return_value={"video_id": "yt2", "url": "u"})
        with mock.patch.object(publish, "upload_video", up):
            self._cli("publish", "s9", "--forzar")
        self.assertEqual(up.call_count, 1)
        self.assertEqual(cli._video_id("s9"), "yt2")


if __name__ == "__main__":
    unittest.main()
