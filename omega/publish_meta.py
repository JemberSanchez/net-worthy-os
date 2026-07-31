"""Subida de un Short ya renderizado a Facebook (Página) e Instagram (Reels), Graph API de Meta.

Excepción deliberada a "sin dependencias" (ver requirements.txt), mismo criterio que
omega/publish.py: Meta no ofrece un SDK oficial de Python mantenido, así que se habla el
protocolo HTTP directo con `requests` en vez de reinventar multipart/resumable con urllib.

Credenciales (gitignored, en DATA_DIR):
  .env: META_APP_ID, META_APP_SECRET       — de la app creada en Meta for Developers
  meta_token.json                          — generado por _authorize() en el primer run:
                                              {page_id, page_name, page_access_token, ig_user_id}

El Page Access Token sale de un token de usuario de LARGA duración (60 días) vía /me/accounts:
no caduca por sí solo mientras el usuario no revoque el permiso ni cambie su contraseña.

SEGURIDAD POR DEFECTO (mismo espíritu que privacy_status="private" en publish.py):
  - upload_facebook_reel(..., published=False)  -> sube en BORRADOR salvo que se pida lo contrario.
  - upload_instagram_reel(..., publish=False)   -> sube y valida el contenedor pero NO llama a
    media_publish. Instagram no tiene borrador vía API: una vez publicado, es público al instante.
"""
from __future__ import annotations
import time
from pathlib import Path
from urllib.parse import urlencode

from . import config

API_VERSION = "v25.0"
GRAPH = f"https://graph.facebook.com/{API_VERSION}"
TOKEN_PATH = config.DATA_DIR / "meta_token.json"

SCOPES = ["pages_show_list", "pages_read_engagement", "pages_manage_posts",
          "business_management", "instagram_business_basic", "instagram_business_content_publish"]
REDIRECT_URI = "https://localhost/"

# Errores transitorios: vale la pena reintentar (caída momentánea de red/servidor).
_RETRIABLE_STATUS = {500, 502, 503, 504}
_MAX_RETRIES = 5
_POLL_INTERVAL_S = 3
_POLL_TIMEOUT_S = 180


class PublishError(Exception):
    """Fallo fatal al subir/publicar (credenciales inválidas, contenedor rechazado). No reintentar."""


def _app_credentials() -> tuple[str, str]:
    import os
    app_id, app_secret = os.environ.get("META_APP_ID"), os.environ.get("META_APP_SECRET")
    if not app_id or not app_secret:
        raise PublishError(
            "Faltan META_APP_ID/META_APP_SECRET en .env. Créalos en Meta for Developers "
            "(developers.facebook.com) y agrégalos al .env del proyecto.")
    return app_id, app_secret


def _request(method: str, url: str, *, retriable: bool = True, **kwargs) -> dict:
    """POST/GET con reintento SOLO en 500-504 (fallo transitorio). Cualquier otro código -> PublishError."""
    import requests

    attempt = 0
    while True:
        resp = requests.request(method, url, timeout=120, **kwargs)
        if resp.ok:
            return resp.json() if resp.content else {}
        if retriable and resp.status_code in _RETRIABLE_STATUS and attempt < _MAX_RETRIES:
            attempt += 1
            time.sleep(2 ** attempt)
            continue
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise PublishError(f"Meta rechazó la llamada (HTTP {resp.status_code}) a {url}: {detail}")


def _authorize() -> dict:
    """Flujo de un solo uso, interactivo por terminal: Meta no tiene equivalente al
    run_local_server() de Google, así que el usuario pega a mano la URL de redirección."""
    import requests

    app_id, app_secret = _app_credentials()
    auth_url = "https://www.facebook.com/" + API_VERSION + "/dialog/oauth?" + urlencode({
        "client_id": app_id, "redirect_uri": REDIRECT_URI,
        "scope": ",".join(SCOPES), "response_type": "code",
    })
    print("1. Abre esta URL, inicia sesión y aprueba los permisos:\n")
    print(f"   {auth_url}\n")
    print("2. El navegador caerá en una página que NO carga (https://localhost/?code=...) "
          "— es normal, no hay nada escuchando ahí. Copia la URL COMPLETA de la barra de "
          "direcciones y pégala aquí.\n")
    pasted = input("URL pegada: ").strip()

    if "code=" not in pasted:
        raise PublishError("Esa URL no trae un parámetro 'code'. Repite el paso 1.")
    code = pasted.split("code=", 1)[1].split("&", 1)[0]

    short = _request("GET", f"{GRAPH}/oauth/access_token", params={
        "client_id": app_id, "redirect_uri": REDIRECT_URI,
        "client_secret": app_secret, "code": code,
    })
    long_lived = _request("GET", f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id,
        "client_secret": app_secret, "fb_exchange_token": short["access_token"],
    })
    user_token = long_lived["access_token"]

    accounts = _request("GET", f"{GRAPH}/me/accounts", params={"access_token": user_token})
    pages = accounts.get("data", [])
    if not pages:
        raise PublishError("Tu usuario no administra ninguna Página de Facebook.")
    if len(pages) == 1:
        page = pages[0]
    else:
        print("\nTenés varias Páginas — elegí una:")
        for i, p in enumerate(pages):
            print(f"  [{i}] {p['name']}")
        idx = int(input("Índice: ").strip())
        page = pages[idx]

    page_id, page_token = page["id"], page["access_token"]
    ig = _request("GET", f"{GRAPH}/{page_id}", params={
        "fields": "instagram_business_account", "access_token": page_token,
    })
    ig_user_id = (ig.get("instagram_business_account") or {}).get("id")
    if not ig_user_id:
        print(f"⚠ La Página '{page['name']}' no tiene una cuenta de Instagram Business vinculada "
              "— publish-ig no funcionará hasta que la vincules desde Meta Business Suite.")

    data = {"page_id": page_id, "page_name": page["name"],
             "page_access_token": page_token, "ig_user_id": ig_user_id}
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    import json
    TOKEN_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nListo: {TOKEN_PATH.name} guardado (Página '{page['name']}'"
          f"{', IG vinculado' if ig_user_id else ', SIN Instagram vinculado'}).")
    return data


def _get_page_token() -> dict:
    import json
    if not TOKEN_PATH.exists():
        return _authorize()
    return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))


def upload_facebook_reel(video_path: Path, title: str, description: str, *,
                          published: bool = False) -> dict:
    """Sube video_path como video de la Página. Devuelve {"video_id": ..., "url": ...}.

    published=False por defecto: nunca público sin que alguien lo pida explícitamente.
    """
    import requests

    if not video_path.exists():
        raise PublishError(f"No existe el video: {video_path}")
    creds = _get_page_token()
    app_id, _ = _app_credentials()
    page_id, page_token = creds["page_id"], creds["page_access_token"]
    size = video_path.stat().st_size

    start = _request("POST", f"{GRAPH}/{app_id}/uploads", params={
        "file_name": video_path.name, "file_length": size,
        "file_type": "video/mp4", "access_token": page_token,
    })
    session_id = start["id"]  # viene como "upload:<ID>"

    with video_path.open("rb") as f:
        binary = f.read()
    transfer = _request("POST", f"{GRAPH}/{session_id}", headers={
        "Authorization": f"OAuth {page_token}", "file_offset": "0",
    }, data=binary, retriable=False)
    # El endpoint trocea el archivo en varios handles internos, uno por línea (medido: 34 para
    # 33 MB) -- pasar el bloque entero pegado falla ("problema al subir el video"). El ÚLTIMO
    # representa el archivo COMPLETO; los anteriores son handles de trozos parciales.
    file_handle = transfer["h"].strip().split("\n")[-1]

    result = _request("POST", f"{GRAPH}/{page_id}/videos", data={
        "access_token": page_token, "title": title, "description": description,
        "fbuploader_video_file_chunk": file_handle, "published": "true" if published else "false",
    }, retriable=False)
    video_id = result["id"]
    return {"video_id": video_id, "url": f"https://www.facebook.com/{video_id}"}


def upload_instagram_reel(video_path: Path, caption: str, *, publish: bool = False) -> dict:
    """Sube video_path como Reel de Instagram. Devuelve el estado del contenedor, o si
    publish=True, {"media_id": ..., "url": ...} tras publicarlo.

    publish=False por defecto: Instagram NO tiene borrador vía API — media_publish es
    inmediato e irreversible, así que solo se llama si se pide explícitamente.
    """
    if not video_path.exists():
        raise PublishError(f"No existe el video: {video_path}")
    creds = _get_page_token()
    ig_user_id, page_token = creds.get("ig_user_id"), creds["page_access_token"]
    if not ig_user_id:
        raise PublishError(
            "No hay una cuenta de Instagram Business vinculada a la Página (meta_token.json "
            "sin ig_user_id). Vincúlala en Meta Business Suite y corre 'meta-auth' de nuevo.")
    size = video_path.stat().st_size

    container = _request("POST", f"{GRAPH}/{ig_user_id}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "access_token": page_token,
    })
    container_id = container["id"]

    with video_path.open("rb") as f:
        binary = f.read()
    _request("POST", f"https://rupload.facebook.com/ig-api-upload/{API_VERSION}/{container_id}",
              headers={"Authorization": f"OAuth {page_token}", "offset": "0",
                       "file_size": str(size)}, data=binary, retriable=False)

    deadline = time.time() + _POLL_TIMEOUT_S
    status = None
    while time.time() < deadline:
        status_resp = _request("GET", f"{GRAPH}/{container_id}", params={
            "fields": "status_code", "access_token": page_token,
        })
        status = status_resp.get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise PublishError(f"Instagram rechazó el video subido (contenedor {container_id}).")
        time.sleep(_POLL_INTERVAL_S)
    else:
        raise PublishError(
            f"Timeout ({_POLL_TIMEOUT_S}s) esperando a que Instagram procese el video "
            f"(contenedor {container_id}, último estado: {status}).")

    if not publish:
        return {"container_id": container_id, "status": "listo, sin publicar"}

    published = _request("POST", f"{GRAPH}/{ig_user_id}/media_publish", data={
        "creation_id": container_id, "access_token": page_token,
    }, retriable=False)
    media_id = published["id"]
    return {"media_id": media_id, "url": f"https://www.instagram.com/reel/{media_id}"}
