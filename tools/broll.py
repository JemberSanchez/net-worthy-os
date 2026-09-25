"""B-roll de VÍDEO con licencia registrada: Wikimedia Commons (PD/CC0/CC BY) y Pexels.

    python tools/broll.py buscar commons "<consulta>" [--n 12]
    python tools/broll.py buscar pexels  "<consulta>" [--n 10]        # necesita PEXELS_API_KEY
    python tools/broll.py lote <proyecto>      # baja y trata los `clips` del storyboard que falten

En el storyboard (video-v2/<p>/storyboard.json):
    "clips": {"parque": {"commons": "File:X.webm", "desde": 12.5},
              "monedas": {"pexels": 3843454, "desde": 0}}
y en una escena `foto` (o en un `fondo`) se usa `"clip": "parque"` en lugar de `"img"`.

Mismas reglas que las imágenes (tools/imagenes_libres.py):
  - Licencia en lista CERRADA: PD, CC0, CC BY (Commons) o Pexels License. Fuera SA/NC/ND.
  - Cada clip deja su ficha en assets/clips/creditos.json -> "Footage:" en la descripción.
  - Objetos y lugares, NO personas reconocibles (Pexels prohíbe sugerir que alguien respalda algo;
    en Commons, las noticias con personas reales traen otros derechos además del copyright).
  - Commons: una sola consulta de metadatos para N clips (límite por IP compartida en la nube) y
    siempre un DERIVADO transcodificado (1080p/720p/480p .webm), nunca el original.
  - Pexels sirve los archivos desde videos.pexels.com: ese dominio tiene que estar permitido.

Tratamiento (`preparar`): recorte a 9:16, 1080x1920, 30 fps, sin audio, y el MISMO duotono de
marca que las fotos (LUT 1D generada por duotono.lut_1d con autocontraste medido en el clip). Si
el tramo útil es más corto que la escena se hace bucle (-stream_loop). Clave de fotogramas cada
0,5 s: HyperFrames extrae fotogramas por posición y una GOP larga lo haría lento.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imagenes_libres as il  # noqa: E402

API_PEXELS_V = "https://api.pexels.com/videos"
DERIVADOS = ("1080p.vp9.webm", "720p.vp9.webm", "1080p.webm", "720p.webm", "480p.vp9.webm", "480p.webm")
W, H, FPS = 1080, 1920, 30


# ── elección de archivo (puro) ─────────────────────────────────────────────────────────────────
def mejor_derivado(derivados: list[dict]) -> dict | None:
    """El mejor transcode de Commons disponible, por orden de DERIVADOS."""
    por_clave = {d.get("transcodekey"): d for d in derivados or [] if d.get("src")}
    return next((por_clave[k] for k in DERIVADOS if k in por_clave), None)


def mejor_archivo_pexels(files: list[dict]) -> dict | None:
    """MP4 más pequeño que cubra 1920 de alto (vertical) o, si no hay, el más alto. Nunca 4K de
    más: se reescala igual y solo cuesta disco y tiempo."""
    mp4 = [f for f in files or [] if f.get("file_type") == "video/mp4" and f.get("height") and f.get("link")]
    if not mp4:
        return None
    cubren = [f for f in mp4 if min(f["height"], f["width"] * H / W) >= H]
    return min(cubren, key=lambda f: f["height"]) if cubren else max(mp4, key=lambda f: f["height"])


# ── búsqueda ────────────────────────────────────────────────────────────────────────────────────
def _info_videos(params: dict) -> list[dict]:
    p = {"action": "query", "format": "json", "prop": "videoinfo",
         "viprop": "url|size|extmetadata|mime|derivatives", **params}
    d = json.loads(il._get(il.API_COMMONS + "?" + urllib.parse.urlencode(p)))
    out = []
    for pg in (d.get("query", {}).get("pages") or {}).values():
        vi = (pg.get("videoinfo") or [None])[0]
        if not vi:
            continue
        em = vi.get("extmetadata", {})
        lic = il._limpiar(em.get("LicenseShortName", {}).get("value", ""))
        der = mejor_derivado(vi.get("derivatives"))
        out.append({"titulo": pg["title"], "ancho": vi.get("width"), "alto": vi.get("height"),
                    "duracion": round(float(vi.get("duration") or 0), 1),
                    "licencia": lic, "clase": il.licencia_ok(lic),
                    "autor": il._limpiar(em.get("Artist", {}).get("value", "")).strip(" ;,") or "Unknown",
                    "url_licencia": em.get("LicenseUrl", {}).get("value", ""),
                    "fuente": vi.get("descriptionurl", ""), "src": der["src"] if der else None})
    return out


def buscar_commons(q: str, n: int = 12) -> list[dict]:
    res = _info_videos({"generator": "search", "gsrsearch": f"{q} filetype:video",
                        "gsrnamespace": "6", "gsrlimit": str(n)})
    return [r for r in res if r["clase"] and r["src"]]


def _pexels(ruta: str, params: dict | None = None) -> dict:
    """La clave puede venir como variable (PEXELS_API_KEY) o inyectada por el proxy del entorno de
    la nube (la cabecera la añade el proxy y la clave nunca entra al contenedor — medido el 25-sep:
    sin variable, la API respondía 200). Sin ninguna de las dos, Pexels responde 401."""
    import urllib.error
    clave = os.environ.get("PEXELS_API_KEY")
    q = "?" + urllib.parse.urlencode(params) if params else ""
    try:
        return json.loads(il._get(f"{API_PEXELS_V}/{ruta}{q}", {"Authorization": clave} if clave else None))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise SystemExit("Pexels rechaza la petición (sin clave): define PEXELS_API_KEY o el secreto "
                             "del entorno para api.pexels.com (gratis en pexels.com/api).")
        raise


def _ficha_pexels(v: dict) -> dict:
    f = mejor_archivo_pexels(v.get("video_files"))
    return {"titulo": f"pexels:{v['id']}", "ancho": v.get("width"), "alto": v.get("height"),
            "duracion": v.get("duration"), "licencia": "Pexels License", "clase": "pexels",
            "autor": (v.get("user") or {}).get("name") or "Unknown",
            "url_licencia": "https://www.pexels.com/license/", "fuente": v.get("url", ""),
            "src": f["link"] if f else None}


def buscar_pexels(q: str, n: int = 10) -> list[dict]:
    d = _pexels("search", {"query": q, "per_page": n, "orientation": "portrait", "size": "medium"})
    return [x for x in map(_ficha_pexels, d.get("videos", [])) if x["src"]]


# ── descarga + tratamiento ──────────────────────────────────────────────────────────────────────
def _registrar(carpeta: Path, archivo: str, r: dict, desde: float) -> None:
    ficha = {"archivo": archivo, "origen": "pexels" if r["clase"] == "pexels" else "wikimedia",
             "titulo": r["titulo"], "autor": r["autor"], "licencia": r["licencia"], "clase": r["clase"],
             "url_licencia": r["url_licencia"], "fuente": r["fuente"], "desde": desde}
    il._registrar(carpeta, ficha)


def bajar(decl: dict[str, dict], carpeta: Path) -> dict[str, Path]:
    """{nombre: {"commons": "File:..."} | {"pexels": id}} -> crudos en `carpeta` (con créditos).
    Commons en UNA consulta; los que ya existen no se vuelven a pedir."""
    carpeta.mkdir(parents=True, exist_ok=True)
    out, faltan = {}, {}
    for k, v in decl.items():
        destino = carpeta / f"{k}.src"
        if destino.exists():
            out[k] = destino
        else:
            faltan[k] = v
    com = {k: v["commons"] if v["commons"].startswith("File:") else "File:" + v["commons"]
           for k, v in faltan.items() if v.get("commons")}
    info = {}
    for i in range(0, len(com), 50):
        for r in _info_videos({"titles": "|".join(list(com.values())[i:i + 50])}):
            info[il._clave(r["titulo"])] = r
    for k, v in faltan.items():
        if v.get("commons"):
            r = info.get(il._clave(com[k]))
            if not r:
                raise SystemExit(f"✗ clip {k!r}: no existe en Commons: {com[k]}")
        elif v.get("pexels"):
            r = _ficha_pexels(_pexels(f"videos/{int(v['pexels'])}"))
        else:
            raise SystemExit(f"✗ clip {k!r}: declara `commons` o `pexels`")
        if not r["clase"]:
            raise SystemExit(f"✗ clip {k!r}: licencia NO admitida ({r['licencia']!r}): {r['titulo']}")
        if not r["src"]:
            raise SystemExit(f"✗ clip {k!r}: sin archivo descargable (Commons sin transcode / Pexels sin MP4)")
        destino = carpeta / f"{k}.src"
        destino.write_bytes(il._get(r["src"]))
        _registrar(carpeta, destino.name, r, float(v.get("desde", 0)))
        out[k] = destino
    return out


def _duracion(ruta: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ruta)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def _geometria() -> str:
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"


def niveles(crudo: Path, desde: float, dur: float) -> tuple[float, float]:
    """Percentiles 1/99 % de luminancia en el tramo usado (autocontraste medido, como en las fotos)."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{desde:.3f}", "-t", f"{max(dur, 0.5):.3f}", "-i", str(crudo),
                        "-vf", "fps=4,scale=180:320:force_original_aspect_ratio=increase,crop=180:320,format=gray",
                        "-f", "rawvideo", "-"], capture_output=True, check=True)
    y = np.frombuffer(r.stdout, dtype=np.uint8)
    if y.size == 0:
        return 0.0, 1.0
    bajo, alto = (float(x) / 255 for x in np.percentile(y, (1, 99)))
    return (bajo, alto) if alto - bajo > 0.05 else (0.0, 1.0)


def preparar(crudo: Path, destino: Path, desde: float, dur: float, contraste: float = 1.15) -> dict:
    """Crudo -> MP4 1080x1920 con duotono de marca, sin audio, de `dur` segundos exactos."""
    from duotono import lut_1d
    total = _duracion(crudo)
    if desde >= total:
        raise SystemExit(f"✗ {crudo.name}: `desde`={desde}s pero el clip dura {total:.1f}s")
    util = total - desde
    bajo, alto = niveles(crudo, desde, min(util, dur))
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".cube", delete=False) as f:
        f.write(lut_1d(contraste, bajo, alto))
        cube = f.name
    try:
        bucle = ["-stream_loop", "-1"] if util < dur else []
        cmd = ["ffmpeg", "-v", "error", "-y", *bucle, "-ss", f"{desde:.3f}", "-i", str(crudo), "-t", f"{dur:.3f}",
               "-an", "-vf", f"{_geometria()},format=gray,format=rgb24,lut1d=file={cube}",
               "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
               "-g", str(FPS // 2), "-movflags", "+faststart", str(destino)]
        subprocess.run(cmd, check=True)
    finally:
        os.unlink(cube)
    return {"duracion": round(_duracion(destino), 2), "bucle": bool(bucle), "niveles": [round(bajo, 3), round(alto, 3)]}


def texto_creditos(fichas: list[dict]) -> str:
    lineas = []
    for f in fichas:
        lic = f["licencia"] + (f" ({f['url_licencia']})" if f.get("url_licencia") else "")
        lineas.append(f"- {f['titulo'].removeprefix('File:')} — {f['autor']} — {lic} — {f['fuente']}")
    return "Footage:\n" + "\n".join(lineas)


def main() -> None:
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == "buscar":
        n = int(a[a.index("--n") + 1]) if "--n" in a else 10
        res = buscar_commons(a[2], n) if a[1] == "commons" else buscar_pexels(a[2], n)
        for r in res:
            print(f"{r['titulo'][:70]:70} {r['duracion']:>6}s {r['ancho']}x{r['alto']}  {r['licencia']}  {r['autor'][:30]}")
        if not res:
            print("(nada con licencia admitida)")
    elif len(a) == 2 and a[0] == "lote":
        proy = Path(a[1])
        decl = json.loads((proy / "storyboard.json").read_text(encoding="utf-8")).get("clips") or {}
        for k, p in bajar(decl, proy / "assets" / "clips").items():
            print(f"✓ {k}: {p} ({_duracion(p):.1f}s)")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
