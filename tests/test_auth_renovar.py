"""Revoked or expired YouTube refresh token: `youtube-auth` must log in again, the rest must say so."""

import socket
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from google.auth.exceptions import RefreshError

from omega import analytics_yt, publish


def _creds_revocadas():
    creds = mock.Mock(expired=True, refresh_token="x", valid=False)
    creds.refresh.side_effect = RefreshError("invalid_grant: Token has been expired or revoked.")
    return creds


def _navegador_con_preconexion(flow):
    """Browser stand-in: an empty connection, an idle one, then the real redirect."""

    def abrir(**_kw):
        def visitar():
            puerto = int(flow.redirect_uri.rsplit(":", 1)[1].strip("/"))
            socket.create_connection(("127.0.0.1", puerto)).close()
            flow.ociosa = socket.create_connection(("127.0.0.1", puerto))
            urllib.request.urlopen(f"http://127.0.0.1:{puerto}/?state=s&code=c", timeout=5).read()

        threading.Thread(target=visitar, daemon=True).start()
        return "https://accounts.example/auth", "s"

    return abrir


class TokenRevocado(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.token = Path(d.name) / "youtube_token.json"
        self.token.write_text("{}", encoding="utf-8")
        self.secreto = Path(d.name) / "client.json"
        self.secreto.write_text("{}", encoding="utf-8")
        for p in (
            mock.patch.object(publish, "TOKEN_PATH", self.token),
            mock.patch.object(publish, "CLIENT_SECRET_PATH", self.secreto),
            mock.patch("webbrowser.open"),
            mock.patch(
                "google.oauth2.credentials.Credentials.from_authorized_user_file",
                return_value=_creds_revocadas(),
            ),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_sin_relogin_no_abre_navegador_y_avisa(self):
        with mock.patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file") as flow:
            with self.assertRaisesRegex(publish.PublishError, "youtube-auth"):
                publish._get_credentials()
        flow.assert_not_called()

    def test_relogin_abre_login_y_guarda_token_nuevo(self):
        nuevas = mock.Mock(valid=True, refresh_token="y")
        nuevas.to_json.return_value = '{"nuevo": true}'
        with mock.patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file") as flow:
            flow.return_value.credentials = nuevas
            flow.return_value.authorization_url.side_effect = _navegador_con_preconexion(flow.return_value)
            self.assertIs(publish._get_credentials(relogin=True), nuevas)
        self.assertEqual(self.token.read_text(encoding="utf-8"), '{"nuevo": true}')
        respuesta = flow.return_value.fetch_token.call_args.kwargs["authorization_response"]
        self.assertTrue(respuesta.startswith("https://"), respuesta)
        self.assertIn("code=c", respuesta)
        flow.return_value.ociosa.close()

    def test_analytics_avisa_con_el_comando(self):
        with self.assertRaisesRegex(analytics_yt.AnalyticsError, "youtube-auth"):
            analytics_yt._clientes()


if __name__ == "__main__":
    unittest.main()
