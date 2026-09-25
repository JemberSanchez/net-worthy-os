"""Analytics AUTOMÁTICO de YouTube: el "qué pasó" sin teclear números de Studio.

    python -m omega.cli analytics-sync [<ref>] [--dry-run]
    python -m omega.cli vincular <ref> <video_id>          # videos subidos antes de que existiera esto

Por cada video publicado (production_video) trae de YouTube Analytics:
  - vistas, vistas comprometidas (si la API las da) y % medio visto  -> production_analytics
  - curva de retención completa (100 puntos)                         -> production_retention
  - retención al inicio de cada bloque del ADN (o 3s/10s/20s/fin)    -> retention_by_block
  - fuente de tráfico dominante                                      -> traffic_source
  - términos de búsqueda que trajeron vistas                          -> production_search_terms
y recalcula el outcome con la fórmula versionada (scoring.py). Nada se teclea a mano: la regla
"sustituir juicio por medición" aplicada al dataset.

Límites conocidos (no son bugs):
  - YouTube Analytics va con ~2-3 días de retraso: un video de ayer da "sin datos aún".
  - En Shorts el % medio visto y audienceWatchRatio pueden pasar de 100 % (bucles). El dato bruto
    se guarda tal cual; al score y a retention_by_block va recortado a 1 (su contrato es [0,1]).
  - CTR de miniatura no existe en la API para Shorts: `ctr` queda NULL.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import date, datetime, timezone

from . import config

# insightTrafficSourceType -> vocabulario de production_analytics.traffic_source
TRAFICO = {"SHORTS": "shorts", "YT_SEARCH": "search", "RELATED_VIDEO": "suggested",
           "SUBSCRIBER": "browse", "BROWSE": "browse", "EXT_URL": "external", "YT_CHANNEL": "channel",
           "PLAYLIST": "playlist", "NOTIFICATION": "notification", "END_SCREEN": "end_screen",
           "HASHTAGS": "hashtags", "SOUND_PAGE": "sound_page"}
PUNTOS_CONTROL = (3, 10, 20)          # segundos que el canal ya usa para comparar (3s -> 20s)


class AnalyticsError(RuntimeError):
    pass


# ── Parseo y cálculo (puro, testeado sin red) ──────────────────────────────────────────────────
def filas(resp: dict) -> list[dict]:
    """Respuesta de reports.query -> lista de dicts {columna: valor}."""
    cols = [c["name"] for c in resp.get("columnHeaders", [])]
    return [dict(zip(cols, r)) for r in resp.get("rows") or []]


def duracion_iso(s: str) -> float:
    """'PT1M5S' -> 65.0 (contentDetails.duration)."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", s or "")
    if not m:
        raise AnalyticsError(f"duración ISO no reconocida: {s!r}")
    d, h, mi, se = (float(x) if x else 0.0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def retencion_en(curva: list[tuple[float, float]], ratio: float) -> float | None:
    """Interpolación lineal de la curva [(t_ratio, watch_ratio)] en `ratio` (0..1)."""
    if not curva:
        return None
    pts = sorted(curva)
    if ratio <= pts[0][0]:
        return pts[0][1]
    for (t0, w0), (t1, w1) in zip(pts, pts[1:]):
        if t0 <= ratio <= t1:
            return w0 if t1 == t0 else w0 + (w1 - w0) * (ratio - t0) / (t1 - t0)
    return pts[-1][1]


def por_bloques(curva, blocks: list[dict] | None, dur: float) -> dict:
    """Retención al INICIO de cada bloque del ADN (dónde se va la gente, en el lenguaje del guion).
    Sin ADN usable: puntos de control 3s/10s/20s/fin. Recortado a [0,1] (contrato de la tabla)."""
    out: dict = {}
    if blocks and dur > 0 and all(b.get("length_s") for b in blocks):
        t = 0.0
        for i, b in enumerate(blocks):
            nombre = b.get("block") or f"b{i + 1}"
            if nombre in out:
                nombre = f"{nombre}#{i + 1}"
            out[nombre] = t / dur
            t += float(b["length_s"])
    else:
        for s in PUNTOS_CONTROL:
            if s < dur:
                out[f"{s}s"] = s / dur
        out["fin"] = 1.0
    res = {}
    for k, r in out.items():
        w = retencion_en(curva, min(1.0, r))
        if w is not None:
            res[k] = round(min(1.0, max(0.0, w)), 4)
    return res


def puntos_control(curva, dur: float) -> dict:
    """{'3s': w, '10s': w, '20s': w, 'fin': w} SIN recortar (para leer bucles de Shorts)."""
    res = {f"{s}s": retencion_en(curva, s / dur) for s in PUNTOS_CONTROL if dur and s < dur}
    res["fin"] = retencion_en(curva, 1.0)
    return {k: round(v, 4) for k, v in res.items() if v is not None}


def trafico_dominante(filas_trafico: list[dict]) -> str | None:
    if not filas_trafico:
        return None
    top = max(filas_trafico, key=lambda f: f.get("views") or 0)
    tipo = top.get("insightTrafficSourceType", "")
    return TRAFICO.get(tipo, tipo.lower() or None)


def resumen(basicas: dict, curva, filas_trafico: list[dict], blocks, dur: float) -> dict:
    """Todo lo medido -> kwargs de production_dna.record_analytics. Función pura."""
    pct = basicas.get("averageViewPercentage")
    frac = None if pct is None else round(min(1.0, max(0.0, pct / 100.0)), 4)
    return {
        "views": int(basicas["views"]) if basicas.get("views") is not None else None,
        "engaged_views": int(basicas["engagedViews"]) if basicas.get("engagedViews") is not None else None,
        "avg_view_pct_raw": None if pct is None else round(pct / 100.0, 4),
        "avd_pct": frac,
        "retention_avg": frac,
        "traffic_source": trafico_dominante(filas_trafico),
        "retention_by_block": por_bloques(curva, blocks, dur) or None,
    }


# ── I/O contra las APIs ─────────────────────────────────────────────────────────────────────────
def _clientes():
    from . import publish
    if not publish.TOKEN_PATH.exists():
        raise AnalyticsError("no hay data/youtube_token.json (YOUTUBE_TOKEN_JSON en el entorno de la nube "
                             "o `youtube-auth` en el PC)")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(str(publish.TOKEN_PATH), publish.SCOPES)
    if not creds.valid:
        if not creds.refresh_token:
            raise AnalyticsError("token sin refresh_token: repetir `youtube-auth`")
        creds.refresh(Request())
        publish.TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return (build("youtube", "v3", credentials=creds, cache_discovery=False),
            build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False))


def consultar(video_id: str, yt=None, yta=None, hoy: date | None = None) -> dict:
    """Trae todo lo de un video. Devuelve {'estado': 'ok'|'privado'|'sin_datos', ...}."""
    if yt is None or yta is None:
        yt, yta = _clientes()
    items = yt.videos().list(part="snippet,status,contentDetails", id=video_id).execute().get("items", [])
    if not items:
        raise AnalyticsError(f"YouTube no encuentra {video_id} (¿borrado o de otro canal?)")
    v = items[0]
    if v["status"].get("privacyStatus") != "public":
        return {"estado": "privado", "publish_at": v["status"].get("publishAt")}
    dur = duracion_iso(v["contentDetails"]["duration"])
    inicio = v["snippet"]["publishedAt"][:10]
    fin = (hoy or datetime.now(timezone.utc).date()).isoformat()

    def q(**kw):
        return filas(yta.reports().query(ids="channel==MINE", startDate=inicio, endDate=fin, **kw).execute())

    base = f"video=={video_id}"
    try:           # engagedViews es reciente: si la API no la acepta, se sigue sin ella
        basicas = q(metrics="views,engagedViews,averageViewPercentage,averageViewDuration", filters=base)
    except Exception:                                              # noqa: BLE001
        basicas = q(metrics="views,averageViewPercentage,averageViewDuration", filters=base)
    if not basicas or not basicas[0].get("views"):
        return {"estado": "sin_datos", "duracion": dur}
    ret = q(dimensions="elapsedVideoTimeRatio", metrics="audienceWatchRatio,relativeRetentionPerformance",
            filters=base)
    traf = q(dimensions="insightTrafficSourceType", metrics="views", filters=base, sort="-views")
    busq = q(dimensions="insightTrafficSourceDetail", metrics="views",
             filters=f"{base};insightTrafficSourceType==YT_SEARCH", sort="-views", maxResults=25)
    return {"estado": "ok", "duracion": dur, "basicas": basicas[0],
            "curva": [(float(f["elapsedVideoTimeRatio"]), float(f["audienceWatchRatio"]),
                       f.get("relativeRetentionPerformance")) for f in ret],
            "trafico": traf,
            "busquedas": [(f["insightTrafficSourceDetail"], int(f["views"])) for f in busq]}


def guardar(con: sqlite3.Connection, ref: str, datos: dict, now: int | None = None) -> dict:
    """Escribe lo consultado en las tres tablas. Devuelve el resumen registrado."""
    from .creative import production_dna
    now = now or int(time.time())
    fila = con.execute("SELECT blocks FROM production_dna WHERE production_ref=?", (ref,)).fetchone()
    blocks = json.loads(fila[0]) if fila else None
    curva2 = [(t, w) for t, w, _ in datos["curva"]]
    r = resumen(datos["basicas"], curva2, datos["trafico"], blocks, datos["duracion"])
    production_dna.record_analytics(con, production_ref=ref, now=now, **r)
    con.execute("DELETE FROM production_retention WHERE production_ref=?", (ref,))
    con.executemany("INSERT INTO production_retention VALUES (?,?,?,?)",
                    [(ref, t, w, rel) for t, w, rel in datos["curva"]])
    con.execute("DELETE FROM production_search_terms WHERE production_ref=?", (ref,))
    con.executemany("INSERT INTO production_search_terms VALUES (?,?,?,?)",
                    [(ref, term, n, now) for term, n in datos["busquedas"]])
    con.commit()
    r["puntos_control"] = puntos_control(curva2, datos["duracion"])
    r["busquedas"] = datos["busquedas"][:3]
    return r


def video_desde_archivos(ref: str) -> str | None:
    """Backfill: el video_id que dejaron `publish`/producir.py en data/ antes de guardarse en la DB."""
    p = config.DATA_DIR / f"publish_{ref}.json"
    if p.exists():
        vid = json.loads(p.read_text(encoding="utf-8")).get("video_id")
        if vid:
            return vid
    log = config.DATA_DIR / "publish_log.jsonl"
    if log.exists():
        for linea in reversed(log.read_text(encoding="utf-8").splitlines()):
            try:
                d = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if d.get("production_ref") == ref and d.get("video_id"):
                return d["video_id"]
    return None


def refs_publicados(con: sqlite3.Connection) -> list[str]:
    """Refs con video en la DB + los que solo tienen rastro en data/ (se vinculan al vuelo)."""
    refs = {r[0] for r in con.execute("SELECT production_ref FROM production_video WHERE platform='youtube'")}
    for p in config.DATA_DIR.glob("publish_*.json"):
        refs.add(p.stem[len("publish_"):])
    log = config.DATA_DIR / "publish_log.jsonl"
    if log.exists():
        for linea in log.read_text(encoding="utf-8").splitlines():
            try:
                refs.add(json.loads(linea)["production_ref"])
            except (json.JSONDecodeError, KeyError):
                pass
    return sorted(refs)
