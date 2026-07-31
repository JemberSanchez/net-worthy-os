"""Tests de la subida a YouTube (omega/publish.py). Todo con mocks: sin red, sin credenciales
reales, sin gastar cuota. Validan: construcción del resultado, manejo de errores fatales vs
transitorios, y el refresh de credenciales cacheadas."""
from __future__ import annotations
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega import publish  # noqa: E402


def _fake_http_error(status: int):
    from googleapiclient.errors import HttpError
    resp = mock.Mock(status=status)
    return HttpError(resp, b"error body")


class UploadVideoTest(unittest.TestCase):
    def setUp(self):
        self.video_path = Path(__file__)  # cualquier archivo existente sirve para el chequeo de existencia
        self.creds_patch = mock.patch.object(publish, "_get_credentials", return_value=mock.Mock())
        self.creds_patch.start()

    def tearDown(self):
        self.creds_patch.stop()

    def test_rejects_missing_video(self):
        with self.assertRaises(publish.PublishError):
            publish.upload_video(Path("no-existe.mp4"), "t", "d")

    def test_returns_video_id_and_url_on_success(self):
        request = mock.Mock()
        request.next_chunk.side_effect = [(mock.Mock(), None), (None, {"id": "abc123"})]
        with mock.patch("googleapiclient.discovery.build") as build, \
             mock.patch("googleapiclient.http.MediaFileUpload"):
            youtube = build.return_value
            youtube.videos.return_value.insert.return_value = request
            result = publish.upload_video(self.video_path, "Título", "Descripción")
        self.assertEqual(result, {"video_id": "abc123", "url": "https://youtu.be/abc123"})

    def test_fatal_http_error_raises_publish_error_without_retry(self):
        request = mock.Mock()
        request.next_chunk.side_effect = _fake_http_error(403)
        with mock.patch("googleapiclient.discovery.build") as build, \
             mock.patch("googleapiclient.http.MediaFileUpload"):
            youtube = build.return_value
            youtube.videos.return_value.insert.return_value = request
            with self.assertRaises(publish.PublishError):
                publish.upload_video(self.video_path, "Título", "Descripción")
        self.assertEqual(request.next_chunk.call_count, 1)  # sin reintento: 403 no es transitorio

    def test_transient_http_error_retries_then_succeeds(self):
        request = mock.Mock()
        request.next_chunk.side_effect = [
            _fake_http_error(503), (None, {"id": "xyz789"})]
        with mock.patch("googleapiclient.discovery.build") as build, \
             mock.patch("googleapiclient.http.MediaFileUpload"), \
             mock.patch("time.sleep"):
            youtube = build.return_value
            youtube.videos.return_value.insert.return_value = request
            result = publish.upload_video(self.video_path, "Título", "Descripción")
        self.assertEqual(result["video_id"], "xyz789")
        self.assertEqual(request.next_chunk.call_count, 2)


class GetCredentialsTest(unittest.TestCase):
    def test_refreshes_expired_token_without_new_consent(self):
        fake_creds = mock.Mock(expired=True, refresh_token="rt", valid=False)
        fake_creds.to_json.return_value = "{}"
        with mock.patch.object(publish, "TOKEN_PATH") as token_path, \
             mock.patch("google.oauth2.credentials.Credentials.from_authorized_user_file",
                         return_value=fake_creds), \
             mock.patch("google.auth.transport.requests.Request"), \
             mock.patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file") as flow:
            token_path.exists.return_value = True
            publish._get_credentials()
            fake_creds.refresh.assert_called_once()
            flow.assert_not_called()  # no hace falta re-consentir: había refresh_token válido
            token_path.write_text.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
