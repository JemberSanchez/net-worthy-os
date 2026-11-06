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

Tratamiento (`preparar`): recorte a 9:16, 1080x1920, 30 fps, sin audio y, por defecto, COLOR real
con el grado de marca (GRADO_MARCA); `"duotono": true` en el clip le aplica el mismo duotono que a
las fotos (LUT 1D de duotono.lut_1d con autocontraste medido en el clip). Si
el tramo útil es más corto que la escena se hace bucle (-stream_loop). Clave de fotogramas cada
0,5 s: HyperFrames extrae fotogramas por posición y una GOP larga lo haría lento.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import imagenes_libres as il

import omega.config  # noqa: F401 -- loads .env (PEXELS_API_KEY) into os.environ

API_PEXELS_V = "https://api.pexels.com/videos"
DERIVADOS = (
    "1080p.vp9.webm",
    "720p.vp9.webm",
    "1080p.webm",
    "720p.webm",
    "480p.vp9.webm",
    "480p.webm",
)
W, H, FPS = 1080, 1920, 30


# ── elección de archivo (puro) ─────────────────────────────────────────────────────────────────
def mejor_derivado(derivados: list[dict]) -> dict | None:
    """El mejor transcode de Commons disponible, por orden de DERIVADOS."""
    por_clave = {d.get("transcodekey"): d for d in derivados or [] if d.get("src")}
    return next((por_clave[k] for k in DERIVADOS if k in por_clave), None)


def mejor_archivo_pexels(files: list[dict]) -> dict | None:
    """MP4 más pequeño que cubra 1920 de alto (vertical) o, si no hay, el más alto. Nunca 4K de
    más: se reescala igual y solo cuesta disco y tiempo."""
    mp4 = [
        f
        for f in files or []
        if f.get("file_type") == "video/mp4" and f.get("height") and f.get("link")
    ]
    if not mp4:
        return None
    cubren = [f for f in mp4 if min(f["height"], f["width"] * H / W) >= H]
    return (
        min(cubren, key=lambda f: f["height"])
        if cubren
        else max(mp4, key=lambda f: f["height"])
    )


# ── búsqueda ────────────────────────────────────────────────────────────────────────────────────
def _info_videos(params: dict) -> list[dict]:
    p = {
        "action": "query",
        "format": "json",
        "prop": "videoinfo",
        "viprop": "url|size|extmetadata|mime|derivatives",
        **params,
    }
    d = json.loads(il._get(il.API_COMMONS + "?" + urllib.parse.urlencode(p)))
    out = []
    for pg in (d.get("query", {}).get("pages") or {}).values():
        vi = (pg.get("videoinfo") or [None])[0]
        if not vi:
            continue
        em = vi.get("extmetadata", {})
        lic = il._limpiar(em.get("LicenseShortName", {}).get("value", ""))
        der = mejor_derivado(vi.get("derivatives"))
        out.append(
            {
                "titulo": pg["title"],
                "ancho": vi.get("width"),
                "alto": vi.get("height"),
                "duracion": round(float(vi.get("duration") or 0), 1),
                "licencia": lic,
                "clase": il.licencia_ok(lic),
                "autor": il._limpiar(em.get("Artist", {}).get("value", "")).strip(" ;,")
                or "Unknown",
                "url_licencia": em.get("LicenseUrl", {}).get("value", ""),
                "fuente": vi.get("descriptionurl", ""),
                "src": der["src"] if der else None,
                "descripcion": il._limpiar(em.get("ImageDescription", {}).get("value", "")),
                "fecha": il._limpiar(em.get("DateTimeOriginal", {}).get("value", "")),
            }
        )
    return out


def buscar_commons(q: str, n: int = 12) -> list[dict]:
    res = _info_videos(
        {
            "generator": "search",
            "gsrsearch": f"{q} filetype:video",
            "gsrnamespace": "6",
            "gsrlimit": str(n),
        }
    )
    return [r for r in res if r["clase"] and r["src"]]


def _pexels(ruta: str, params: dict | None = None) -> dict:
    """La clave puede venir como variable (PEXELS_API_KEY) o inyectada por el proxy del entorno de
    la nube (la cabecera la añade el proxy y la clave nunca entra al contenedor — medido el 25-sep:
    sin variable, la API respondía 200). Sin ninguna de las dos, Pexels responde 401."""
    import urllib.error

    clave = os.environ.get("PEXELS_API_KEY")
    q = "?" + urllib.parse.urlencode(params) if params else ""
    try:
        return json.loads(
            il._get(
                f"{API_PEXELS_V}/{ruta}{q}", {"Authorization": clave} if clave else None
            )
        )
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise SystemExit(
                "Pexels rechaza la petición (sin clave): define PEXELS_API_KEY o el secreto "
                "del entorno para api.pexels.com (gratis en pexels.com/api)."
            )
        raise


def _ficha_pexels(v: dict) -> dict:
    f = mejor_archivo_pexels(v.get("video_files"))
    return {
        "titulo": f"pexels:{v['id']}",
        "ancho": v.get("width"),
        "alto": v.get("height"),
        "duracion": v.get("duration"),
        "licencia": "Pexels License",
        "clase": "pexels",
        "autor": (v.get("user") or {}).get("name") or "Unknown",
        "url_licencia": "https://www.pexels.com/license/",
        "fuente": v.get("url", ""),
        "src": f["link"] if f else None,
        # Pexels has no description field: the page slug is the only text about the content.
        "descripcion": v.get("url", "").rstrip("/").rsplit("/", 1)[-1].replace("-", " "),
        "fecha": "",
    }


def buscar_pexels(q: str, n: int = 10) -> list[dict]:
    d = _pexels(
        "search",
        {"query": q, "per_page": n},  # portrait+medium hid specific footage; preparar crops anyway
    )
    return [x for x in map(_ficha_pexels, d.get("videos", [])) if x["src"]]


# ── selección: puntuar candidatos contra la frase ──────────────────────────────────────────────
GENERICO = frozenset(
    "business businessman businesswoman handshake coins coin skyline laptop typing person people "
    "man woman office pointing money abstract animation background concept".split()
)
PESOS = {"rel": 0.35, "esp": 0.25, "res": 0.15, "mov": 0.10, "lic": 0.05, "nuevo": 0.10}
VALOR_LICENCIA = {"pd": 1.0, "cc0": 1.0, "pexels": 0.8, "cc-by": 0.7}


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def usados(raiz: Path = Path(__file__).resolve().parents[1] / "video-v2") -> set[str]:
    """Titles already credited in any of our videos."""
    return {
        f["titulo"]
        for p in raiz.glob("*/assets/clips/creditos.json")
        for f in json.loads(p.read_text(encoding="utf-8"))
    }


def puntuar(
    c: dict,
    terminos: str,
    anio: int | None = None,
    veto: tuple[str, ...] = (),
    vistos: set[str] | frozenset[str] = frozenset(),
    mov: float | None = None,
) -> float | None:
    """0..1, or None when rejected: no licence, under 1080 px, a vetoed event, or nothing in its
    metadata matching the sentence. Reads only metadata; `mov` comes from movimiento() after download."""
    texto = f"{c['titulo']} {c.get('descripcion', '')} {c.get('fecha', '')}"
    t, pedidos = _tokens(texto), _tokens(terminos)
    corto = min(c.get("alto") or 0, (c.get("ancho") or 0) * H / W)
    if not c.get("clase") or corto < 1080 or not t & pedidos:
        return None
    if any(v.lower() in texto.lower() for v in veto):
        return None
    esp = max(0.0, 1 - 0.34 * len(t & GENERICO))
    if anio and str(anio) not in t:
        esp *= 0.5  # a period shot without the period in its metadata cannot be trusted
    partes = {
        "rel": len(t & pedidos) / len(pedidos),
        "esp": esp,
        "res": min(1.0, corto / 2160),
        "mov": 0.5 if mov is None else min(1.0, mov / 15),
        "lic": VALOR_LICENCIA[c["clase"]],
        "nuevo": 0.0 if c["titulo"] in vistos else 1.0,
    }
    return round(sum(PESOS[k] * v for k, v in partes.items()), 3)


def movimiento(crudo: Path, desde: float = 0.0, segundos: float = 14.0) -> float:
    """Mean absolute luma change between frames at 2 fps (0-255). Measured 3-nov: carrier deck 19.2,
    tax form 14.0, static building 3.3."""
    import numpy as np

    raw = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-ss", f"{desde:.2f}", "-i", str(crudo), "-t", f"{segundos:.2f}",
            "-vf", "fps=2,scale=160:90,format=gray", "-f", "rawvideo", "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 90, 160).astype(np.float32)
    return round(float(np.abs(np.diff(f, axis=0)).mean()), 1) if len(f) > 1 else 0.0


# ── descarga + tratamiento ──────────────────────────────────────────────────────────────────────
def _registrar(carpeta: Path, archivo: str, r: dict, desde: float) -> None:
    ficha = {
        "archivo": archivo,
        "origen": "pexels" if r["clase"] == "pexels" else "wikimedia",
        "titulo": r["titulo"],
        "autor": r["autor"],
        "licencia": r["licencia"],
        "clase": r["clase"],
        "url_licencia": r["url_licencia"],
        "fuente": r["fuente"],
        "desde": desde,
    }
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
    com = {
        k: v["commons"] if v["commons"].startswith("File:") else "File:" + v["commons"]
        for k, v in faltan.items()
        if v.get("commons")
    }
    info = {}
    for i in range(0, len(com), 50):
        for r in _info_videos({"titles": "|".join(list(com.values())[i : i + 50])}):
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
            raise SystemExit(
                f"✗ clip {k!r}: licencia NO admitida ({r['licencia']!r}): {r['titulo']}"
            )
        if not r["src"]:
            raise SystemExit(
                f"✗ clip {k!r}: sin archivo descargable (Commons sin transcode / Pexels sin MP4)"
            )
        destino = carpeta / f"{k}.src"
        destino.write_bytes(il._get(r["src"]))
        _registrar(carpeta, destino.name, r, float(v.get("desde", 0)))
        out[k] = destino
    return out


def _duracion(ruta: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(ruta),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())


def _geometria() -> str:
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"


def niveles(crudo: Path, desde: float, dur: float) -> tuple[float, float]:
    """Percentiles 1/99 % de luminancia en el tramo usado (autocontraste medido, como en las fotos)."""
    import numpy as np

    r = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{desde:.3f}",
            "-t",
            f"{max(dur, 0.5):.3f}",
            "-i",
            str(crudo),
            "-vf",
            "fps=4,scale=180:320:force_original_aspect_ratio=increase,crop=180:320,format=gray",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    y = np.frombuffer(r.stdout, dtype=np.uint8)
    if y.size == 0:
        return 0.0, 1.0
    bajo, alto = (float(x) / 255 for x in np.percentile(y, (1, 99)))
    return (bajo, alto) if alto - bajo > 0.05 else (0.0, 1.0)


# Grado de marca para metraje MODERNO en color (decisión del usuario 26-sep, comparativa A/B vista):
# sombras hacia verde-azulado, altas luces hacia dorado, saturación contenida y viñeta. Las fotos de
# archivo siguen en duotono (casi todas son B/N de 1900-1950: en color quedarían grises).
GRADO_MARCA = (
    "eq=contrast=1.08:saturation=0.82:brightness=-0.03,"
    "colorbalance=rs=-0.06:gs=0.02:bs=0.03:rh=0.06:gh=0.03:bh=-0.07,vignette=PI/4.5"
)
# Fondo detrás de texto: desenfoque fuerte (reducir -> desenfocar -> ampliar: igual a la vista y
# ~10x más rápido que un gblur a 1080x1920).
DESENFOQUE_FONDO = "scale=540:960,gblur=sigma=3,scale=1080:1920"  # 26-sep: la mitad de desenfoque (más metraje real)
# Light grade (aspecto "cine"): only ties sources together; no tint and no vignette, which is what turned
# every video into the same green-black (docs/mejora/auditoria.md, tell 3: 72-83 % green-yellow pixels).
GRADO_LIGERO = "eq=contrast=1.04:saturation=0.94"
MODOS = ("color", "duotono", "natural", "ligero")


# Clip con mucho detalle (broll.detalle > construir.UMBRAL_DETALLE) detrás de texto: con sigma 3 un
# teletipo seguía leyéndose detrás del titular (1-oct). Fuerte = forma y luz, nunca cifras legibles.
DESENFOQUE_FUERTE = "scale=540:960,gblur=sigma=11,scale=1080:1920"


# HDR (HLG/PQ) -> SDR bt709. Un clip HDR que llega al render hace que hyperframes capture TODO el
# vídeo por screenshot (30-oct: Pexels HLG, 0.55 fps, 33 min en vez de 2) y además se ve lavado.
TRANSFER_HDR = ("arib-std-b67", "smpte2084")
A_SDR = (
    "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
    "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
)


def es_hdr(transfer: str) -> bool:
    return transfer in TRANSFER_HDR


def _transfer(ruta: Path) -> str:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=color_transfer",
            "-of",
            "csv=p=0",
            str(ruta),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout.strip()


def filtro(
    modo: str, fondo: bool | str, cube: str | None = None, hdr: bool = False
) -> str:
    """Cadena -vf de ffmpeg para tratar un clip. Función pura (testeable sin ffmpeg)."""
    if modo not in MODOS:
        raise ValueError(f"modo {modo!r} no existe ({', '.join(MODOS)})")
    color = (
        GRADO_MARCA
        if modo == "color"
        else GRADO_LIGERO
        if modo == "ligero"
        else "null"  # natural: untouched colour, the brand grade read as a green filter (docs/mejora/auditoria.md)
        if modo == "natural"
        else f"format=gray,format=rgb24,lut1d=file={cube}"
    )
    blur = DESENFOQUE_FUERTE if fondo == "fuerte" else DESENFOQUE_FONDO
    return (
        (f"{A_SDR}," if hdr else "")
        + f"{_geometria()},{color}"
        + (f",{blur}" if fondo else "")
    )


def preparar(
    crudo: Path,
    destino: Path,
    desde: float,
    dur: float,
    contraste: float = 1.15,
    modo: str = "color",
    fondo: bool | str = False,
) -> dict:
    """Crudo -> MP4 1080x1920 sin audio, de `dur` segundos exactos. `modo`: "color" (grado de
    marca, por defecto para metraje moderno) o "duotono" (la misma rampa que las fotos, vía LUT 1D).
    `fondo=True`: además, desenfocado, para ir detrás de texto."""
    from duotono import lut_1d

    total = _duracion(crudo)
    if desde >= total:  # fondos que reutilizan un clip avanzan de tramo: dar la vuelta
        desde = desde % max(total - 0.5, 0.5)
    util = total - desde
    destino.parent.mkdir(parents=True, exist_ok=True)
    cube, niveles_ = None, None
    if modo == "duotono":
        bajo, alto = niveles(crudo, desde, min(util, dur))
        niveles_ = [round(bajo, 3), round(alto, 3)]
        with tempfile.NamedTemporaryFile("w", suffix=".cube", delete=False) as f:
            f.write(lut_1d(contraste, bajo, alto))
            cube = f.name
    try:
        bucle = ["-stream_loop", "-1"] if util < dur else []
        cmd = [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            *bucle,
            "-ss",
            f"{desde:.3f}",
            "-i",
            str(crudo),
            "-t",
            f"{dur:.3f}",
            "-an",
            "-vf",
            filtro(modo, fondo, cube, hdr=es_hdr(_transfer(crudo))),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-g",
            str(FPS // 2),
            "-movflags",
            "+faststart",
            str(destino),
        ]
        subprocess.run(cmd, check=True)
    finally:
        if cube:
            os.unlink(cube)
    return {
        "duracion": round(_duracion(destino), 2),
        "bucle": bool(bucle),
        "niveles": niveles_,
    }


def texto_creditos(fichas: list[dict]) -> str:
    lineas = []
    for f in fichas:
        lic = f["licencia"] + (
            f" ({f['url_licencia']})" if f.get("url_licencia") else ""
        )
        lineas.append(
            f"- {f['titulo'].removeprefix('File:')} — {f['autor']} — {lic} — {f['fuente']}"
        )
    return "Footage:\n" + "\n".join(lineas)


BANDA_TEXTO = (250, 1150)  # px de 1920 donde viven los textos de escena (plantilla.tpl)


def detalle(crudo: Path, desde: float = 0.0, segundos: float = 8.0) -> float:
    """Cuánto "ruido visual" tiene el clip en la banda del texto: gradiente medio (0-255) de 1 fps
    en 270x480. Medido (1-oct): teletipo de bolsa 18,1 (el texto encima no se lee), suelo de
    madera 13,6 y monedas 12,8 (se leen), gasolinera 7,9, reloj 3,1."""
    import numpy as np

    raw = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{desde:.2f}",
            "-i",
            str(crudo),
            "-t",
            f"{segundos:.2f}",
            "-vf",
            "fps=1,scale=270:480:force_original_aspect_ratio=increase,crop=270:480,format=gray",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 480, 270).astype(np.float32)
    a, b = (round(x / 4) for x in BANDA_TEXTO)
    f = f[:, a:b, :]
    return round(
        float(np.abs(np.diff(f, axis=2)).mean() + np.abs(np.diff(f, axis=1)).mean()), 1
    )


def main() -> None:
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == "buscar":
        n = int(a[a.index("--n") + 1]) if "--n" in a else 10
        res = buscar_commons(a[2], n) if a[1] == "commons" else buscar_pexels(a[2], n)
        terminos = a[a.index("--terminos") + 1] if "--terminos" in a else a[2]
        anio = int(a[a.index("--anio") + 1]) if "--anio" in a else None
        veto = tuple(a[a.index("--veto") + 1].split(",")) if "--veto" in a else ()
        vistos = usados()
        res = [(puntuar(r, terminos, anio, veto, vistos), r) for r in res]
        res = sorted((x for x in res if x[0] is not None), key=lambda x: -x[0])
        for s, r in res:
            print(
                f"{s:.2f} {r['titulo'][:60]:60} {r['duracion']:>6}s {r['ancho']}x{r['alto']}  {r['licencia']}  {r['fuente']}"
            )
            print(f"     {r['descripcion'][:110]}")
        if not res:
            print("(nada admitido: licencia, resolución, veto o sin relación con los términos)")
    elif len(a) == 2 and a[0] == "lote":
        proy = Path(a[1])
        decl = (
            json.loads((proy / "storyboard.json").read_text(encoding="utf-8")).get(
                "clips"
            )
            or {}
        )
        for k, p in bajar(decl, proy / "assets" / "clips").items():
            print(f"✓ {k}: {p} ({_duracion(p):.1f}s)")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
