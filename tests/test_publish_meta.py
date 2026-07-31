"""Tests de la subida a Facebook/Instagram (omega/publish_meta.py). Todo con mocks: sin red,
sin credenciales reales, sin publicar nada. Validan: construcción del resultado, que
published/publish=False es el default REAL (nunca se llama a media_publish sin pedirlo), el
polling de status_code (FINISHED/ERROR/timeout), y reintentos solo en 500-504."""
from __future__ import annotations
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega import publish_meta  # noqa: E402


def _resp(status=200, data=None):
    r = mock.Mock(status_code=status, ok=200 <= status < 300)
    r.json.return_value = data or {}
    r.content = b"{}"
    r.text = str(data)
    return r


FAKE_CREDS = {"page_id": "page1", "page_name": "Net Worthy",
              "page_access_token": "PAGE_TOKEN", "ig_user_id": "ig1"}


class UploadFacebookReelTest(unittest.TestCase):
    """Endpoint /video_reels (3 fases: start/transferir/finish). NO el genérico /videos --
    probado en real (2026-07-31): ese acepta la subida (HTTP 200, published:true) pero el video
    queda con video_status:"error" y publishing_phase:"not_started" con contenido vertical, sin
    avisar. /video_reels es el que de verdad procesa Reels."""

    def setUp(self):
        self.video_path = Path(__file__)
        mock.patch.object(publish_meta, "_get_page_token", return_value=FAKE_CREDS).start()
        self.addCleanup(mock.patch.stopall)

    def _calls(self):
        return [
            _resp(200, {"video_id": "999", "upload_url": "https://rupload.facebook.com/video-upload/999"}),
            _resp(200, {"success": True}),
            _resp(200, {"success": True}),
        ]

    def test_rejects_missing_video(self):
        with self.assertRaises(publish_meta.PublishError):
            publish_meta.upload_facebook_reel(Path("no-existe.mp4"), "t", "d")

    def test_uploads_as_draft_by_default(self):
        with mock.patch("requests.request", side_effect=self._calls()) as req:
            result = publish_meta.upload_facebook_reel(self.video_path, "Título", "Descripción")
        self.assertEqual(result, {"video_id": "999", "url": "https://www.facebook.com/reel/999/"})
        # la fase "finish" (última llamada) NO pidió video_state=PUBLISHED por defecto
        last_kwargs = req.call_args_list[-1].kwargs
        self.assertEqual(last_kwargs["data"]["video_state"], "DRAFT")

    def test_publicar_flag_marks_published_true(self):
        with mock.patch("requests.request", side_effect=self._calls()) as req:
            publish_meta.upload_facebook_reel(self.video_path, "t", "d", published=True)
        self.assertEqual(req.call_args_list[-1].kwargs["data"]["video_state"], "PUBLISHED")

    def test_uploads_binary_to_the_upload_url_returned_by_start_phase(self):
        with mock.patch("requests.request", side_effect=self._calls()) as req:
            publish_meta.upload_facebook_reel(self.video_path, "t", "d")
        transfer_call = req.call_args_list[1]
        self.assertEqual(transfer_call.args[1], "https://rupload.facebook.com/video-upload/999")


class UploadInstagramReelTest(unittest.TestCase):
    def setUp(self):
        self.video_path = Path(__file__)
        mock.patch.object(publish_meta, "_get_page_token", return_value=FAKE_CREDS).start()
        mock.patch("time.sleep").start()
        self.addCleanup(mock.patch.stopall)

    def test_rejects_missing_video(self):
        with self.assertRaises(publish_meta.PublishError):
            publish_meta.upload_instagram_reel(Path("no-existe.mp4"), "cap")

    def test_rejects_when_no_ig_account_linked(self):
        creds = {**FAKE_CREDS, "ig_user_id": None}
        with mock.patch.object(publish_meta, "_get_page_token", return_value=creds):
            with self.assertRaises(publish_meta.PublishError):
                publish_meta.upload_instagram_reel(self.video_path, "cap")

    def test_stops_before_media_publish_by_default(self):
        calls = [
            _resp(200, {"id": "container1"}),                       # crear contenedor
            _resp(200, {"success": True}),                          # subir binario a rupload
            _resp(200, {"status_code": "FINISHED"}),                # polling
        ]
        with mock.patch("requests.request", side_effect=calls) as req:
            result = publish_meta.upload_instagram_reel(self.video_path, "caption")
        self.assertEqual(result, {"container_id": "container1", "status": "listo, sin publicar"})
        # NUNCA se llamó a media_publish: solo 3 requests, ninguna a esa URL
        urls = [c.args[1] for c in req.call_args_list]
        self.assertFalse(any("media_publish" in u for u in urls))

    def test_publish_true_calls_media_publish(self):
        calls = [
            _resp(200, {"id": "container1"}),
            _resp(200, {"success": True}),
            _resp(200, {"status_code": "FINISHED"}),
            _resp(200, {"id": "media1"}),
            # el permalink real usa un shortcode, NO el media_id -- se pide a la API, no se arma
            # a mano (probado en real, 2026-07-31: armarlo a mano dio una URL rota).
            _resp(200, {"permalink": "https://www.instagram.com/reel/DbdyTKJkoe2/"}),
        ]
        with mock.patch("requests.request", side_effect=calls) as req:
            result = publish_meta.upload_instagram_reel(self.video_path, "caption", publish=True)
        self.assertEqual(result, {"media_id": "media1",
                                   "url": "https://www.instagram.com/reel/DbdyTKJkoe2/"})
        self.assertIn("media_publish", req.call_args_list[-2].args[1])

    def test_polling_retries_until_finished(self):
        calls = [
            _resp(200, {"id": "container1"}),
            _resp(200, {"success": True}),
            _resp(200, {"status_code": "IN_PROGRESS"}),
            _resp(200, {"status_code": "IN_PROGRESS"}),
            _resp(200, {"status_code": "FINISHED"}),
        ]
        with mock.patch("requests.request", side_effect=calls):
            result = publish_meta.upload_instagram_reel(self.video_path, "caption")
        self.assertEqual(result["status"], "listo, sin publicar")

    def test_polling_error_status_raises(self):
        calls = [
            _resp(200, {"id": "container1"}),
            _resp(200, {"success": True}),
            _resp(200, {"status_code": "ERROR"}),
        ]
        with mock.patch("requests.request", side_effect=calls):
            with self.assertRaises(publish_meta.PublishError):
                publish_meta.upload_instagram_reel(self.video_path, "caption")

    def test_polling_timeout_raises(self):
        calls = [
            _resp(200, {"id": "container1"}),
            _resp(200, {"success": True}),
        ] + [_resp(200, {"status_code": "IN_PROGRESS"})] * 5
        times = iter([0, 0, 0] + [i * 100 for i in range(1, 20)])  # supera _POLL_TIMEOUT_S rápido
        with mock.patch("requests.request", side_effect=calls), \
             mock.patch.object(publish_meta.time, "time", side_effect=lambda: next(times)):
            with self.assertRaises(publish_meta.PublishError):
                publish_meta.upload_instagram_reel(self.video_path, "caption")


class RequestHelperTest(unittest.TestCase):
    def test_retries_only_on_5xx(self):
        calls = [_resp(503), _resp(200, {"ok": True})]
        with mock.patch("requests.request", side_effect=calls), mock.patch("time.sleep"):
            result = publish_meta._request("GET", "https://example.com")
        self.assertEqual(result, {"ok": True})

    def test_does_not_retry_4xx(self):
        with mock.patch("requests.request", return_value=_resp(400, {"error": "bad"})) as req:
            with self.assertRaises(publish_meta.PublishError):
                publish_meta._request("GET", "https://example.com")
        self.assertEqual(req.call_count, 1)

    def test_retriable_false_never_retries_5xx(self):
        with mock.patch("requests.request", return_value=_resp(503)) as req:
            with self.assertRaises(publish_meta.PublishError):
                publish_meta._request("GET", "https://example.com", retriable=False)
        self.assertEqual(req.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
