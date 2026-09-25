"""Subida de un Short ya renderizado a YouTube (YouTube Data API v3, videos.insert).

Excepción deliberada a "sin dependencias" (ver requirements.txt): OAuth2 + resumable upload a
mano con urllib es alto riesgo de error/baneo. Usa las librerías oficiales de Google.

Credenciales (gitignored, en DATA_DIR):
  youtube_client_secret.json  — descargado una vez de Google Cloud Console (OAuth client, Desktop app)
  youtube_token.json          — generado por _get_credentials() en el primer run, se refresca solo

Scope: youtube (gestión completa del canal) -- youtube.upload solo alcanzaba para subir, no para
editar título/descripción después (videos.update pedía más permiso). Sigue siendo tu propio canal,
no accede a nada de terceros.
Cuota: videos.insert cuesta 1600 unidades de las 10.000/día gratis -> 6 subidas/día de margen.
No usar este comando como sandbox de pruebas repetidas sin necesidad.
"""
from __future__ import annotations
import time
from pathlib import Path

from . import config

# youtube: subir y editar (videos.update). yt-analytics.readonly: retención por segundo y términos
# de búsqueda (analítica automática). Se piden JUNTOS para autorizar una sola vez: cambiar los
# scopes invalida el token y obliga a repetir el login.
SCOPES = ["https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]
CLIENT_SECRET_PATH = config.DATA_DIR / "youtube_client_secret.json"
TOKEN_PATH = config.DATA_DIR / "youtube_token.json"

# Errores transitorios: vale la pena reintentar (caída momentánea de red/servidor).
_RETRIABLE_STATUS = {500, 502, 503, 504}
_MAX_RETRIES = 5


class PublishError(Exception):
    """Fallo fatal al subir (credenciales inválidas, cuota agotada, body rechazado). No reintentar."""


def _get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not CLIENT_SECRET_PATH.exists():
            raise PublishError(
                f"No existe {CLIENT_SECRET_PATH}. Descárgalo de Google Cloud Console "
                "(OAuth client ID, tipo 'Desktop app') y guárdalo con ese nombre.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload_video(video_path: Path, title: str, description: str, *, tags: list[str] | None = None,
                  category_id: str = "27", privacy_status: str = "private",
                  made_for_kids: bool = False) -> dict:
    """Sube video_path a YouTube. Devuelve {"video_id": ..., "url": ...}.

    category_id default "27" (Education): no existe categoría "Finance" en la taxonomía de
    YouTube; Education encaja mejor con el tono explicativo del canal que "25" (News & Politics).
    privacy_status default "private": nunca publicar en público por accidente.
    """
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    if not video_path.exists():
        raise PublishError(f"No existe el video: {video_path}")

    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    attempt = 0
    while response is None:
        try:
            _status, response = request.next_chunk()
        except HttpError as exc:
            status = exc.resp.status if exc.resp is not None else None
            if status in _RETRIABLE_STATUS and attempt < _MAX_RETRIES:
                attempt += 1
                time.sleep(2 ** attempt)
                continue
            raise PublishError(f"Subida rechazada por YouTube (HTTP {status}): {exc}") from exc

    video_id = response["id"]
    return {"video_id": video_id, "url": f"https://youtu.be/{video_id}"}


# ── Borrador privado + publicación programada (tarea 8b) ─────────────────────────────────────────
# La rutina diaria sube el Short como PRIVADO en cuanto pasa el QA (así no se pierde si el
# contenedor de la nube se recicla antes de que el usuario apruebe). Aprobar = programarlo a la
# hora pico de la audiencia (EE. UU.) o hacerlo público ya. Motivo del horario: el S3 salió a las
# 02:00 hora local con audiencia EN/US, confounder anotado en CLAUDE.md.
HORA_PICO = "12:00"                 # hora de Nueva York; ajustable con --hora
ZONA_AUDIENCIA = "America/New_York"


def proximo_slot(ahora_utc, hora: str = HORA_PICO, zona: str = ZONA_AUDIENCIA, margen_min: int = 20,
                 dias: int = 0):
    """Próximo instante `hora` en `zona` que caiga al menos `margen_min` después de ahora, más
    `dias` días (para escalonar: uno al día rinde más que dos a la vez). Devuelve un datetime en
    UTC. Función pura (horario de verano incluido vía zoneinfo: se suma en calendario LOCAL)."""
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(zona)
    h, m = (int(x) for x in hora.split(":"))
    local = ahora_utc.astimezone(tz)
    cand = local.replace(hour=h, minute=m, second=0, microsecond=0)
    if cand < local + timedelta(minutes=margen_min):
        cand = (local + timedelta(days=1)).replace(hour=h, minute=m, second=0, microsecond=0)
        cand = datetime(cand.year, cand.month, cand.day, h, m, tzinfo=tz)   # re-normaliza DST
    if dias:
        d = cand.date() + timedelta(days=dias)
        cand = datetime(d.year, d.month, d.day, h, m, tzinfo=tz)
    return cand.astimezone(timezone.utc)


def _actualizar_status(video_id: str, cambios: dict, youtube=None) -> dict:
    """videos.update REEMPLAZA el bloque status entero: se lee el actual y se modifica encima, para
    no perder selfDeclaredMadeForKids, licencia, etc."""
    if youtube is None:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", credentials=_get_credentials())
    items = youtube.videos().list(part="status", id=video_id).execute().get("items", [])
    if not items:
        raise PublishError(f"YouTube no encuentra el video {video_id} (¿borrado o de otro canal?)")
    status = {k: v for k, v in items[0]["status"].items()
              if k in ("privacyStatus", "publishAt", "selfDeclaredMadeForKids", "license",
                       "embeddable", "publicStatsViewable", "containsSyntheticMedia")}
    status.update(cambios)
    status = {k: v for k, v in status.items() if v is not None}
    return youtube.videos().update(part="status", body={"id": video_id, "status": status}).execute()


def programar(video_id: str, publish_at_utc, youtube=None) -> dict:
    """Programa la publicación: YouTube exige privacyStatus=private + publishAt en el futuro."""
    iso = publish_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return _actualizar_status(video_id, {"privacyStatus": "private", "publishAt": iso}, youtube)


def hacer_publico(video_id: str, youtube=None) -> dict:
    return _actualizar_status(video_id, {"privacyStatus": "public", "publishAt": None}, youtube)
