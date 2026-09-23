"""Busca y descarga imagen REAL con licencia segura para los Shorts v2, y deja la atribución escrita.

    python tools/imagenes_libres.py buscar "Jack Delano Brattleboro" [--n 12]
    python tools/imagenes_libres.py bajar "File:Main street in Brattleboro....jpg" video-v2/read-janitor/assets/img/brattleboro.jpg
    python tools/imagenes_libres.py lote lista.txt      # líneas "destino.jpg|File:titulo" (1 consulta)
    python tools/imagenes_libres.py pexels "stock market" [--n 10]          # necesita PEXELS_API_KEY

Por qué existe
--------------
El motor v1 no usaba ni una imagen. Imagen real es el salto de calidad pendiente del v2
(docs/V2-CALIDAD.md), pero una imagen sin licencia clara es una reclamación de copyright
esperando a pasar — y en un canal monetizable eso es desmonetización o baja. Así que la
licencia no se "revisa luego": se FILTRA al buscar y se REGISTRA al bajar.

Política de licencias (lista cerrada, no heurística)
----------------------------------------------------
- Wikimedia Commons: solo **dominio público, CC0 y CC BY** (con atribución). Fuera: CC BY-SA
  (el share-alike podría extenderse al vídeo entero), NC (el canal monetiza), ND (tratar la imagen
  en verde/dorado ES una obra derivada), GFDL y todo lo que no se reconozca.
- Pexels: licencia propia, uso comercial y modificación permitidos, sin atribución obligatoria
  (se registra igual, por trazabilidad).
- ⚠ Una licencia libre del ARCHIVO no cubre el derecho de imagen de quien sale en él. Las fotos de
  prensa de personas reales (p. ej. Ronald Read) tienen copyright: no buscarlas por nombre.

Cada `bajar` añade una entrada a `creditos.json` en la carpeta destino (título, autor, licencia,
URL de origen). De ahí sale el texto de créditos de la descripción del vídeo.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_COMMONS = "https://commons.wikimedia.org/w/api.php"
API_PEXELS = "https://api.pexels.com/v1/search"
# Wikimedia exige un User-Agent identificable; sin él responde 403 o limita antes.
UA = "NetWorthyOS/1.0 (https://github.com/jembersanchez/net-worthy-os) python-urllib"
ALTO_MIN = 2100         # alto mínimo útil: 1920 del cuadro + margen para el zoom lento
# Commons solo sirve miniaturas en tamaños ESTÁNDAR (1024 y 2560 -> 400 "Use thumbnail sizes
# listed on https://w.wiki/GHai"; 960, 1920 y 3840 -> 200, medido el 23-sep).
ANCHOS_ESTANDAR = (500, 960, 1280, 1920, 3840)
ESPERA_MAX = 90         # s: por encima de esto no se espera, se aborta con mensaje

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(errors="replace")


def licencia_ok(nombre_corto: str) -> str | None:
    """Clasifica la licencia de Commons. Devuelve 'pd' | 'cc0' | 'cc-by' o None si NO se admite.
    Función pura: es la puerta de copyright, así que tiene test propio."""
    n = (nombre_corto or "").strip().lower()
    if not n:
        return None
    if any(x in n for x in ("-sa", " sa", "nc", "-nd", " nd", "gfdl", "fair use", "non-free")):
        return None
    if n in ("public domain", "pd") or n.startswith("pd-") or n.startswith("pd "):
        return "pd"
    if n.startswith("cc0") or n == "cc-zero":
        return "cc0"
    if re.fullmatch(r"cc[ -]by[ -]\d(\.\d)?", n) or n in ("cc by", "cc-by"):
        return "cc-by"
    return None


def _limpiar(texto: str) -> str:
    """extmetadata viene en HTML: quita etiquetas Y decodifica entidades (`&amp;` -> `&`)."""
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", texto or ""))).strip()


def _get(url: str, headers: dict | None = None, intentos: int = 6) -> bytes:
    """GET con backoff. Wikimedia responde 429 si se le pide rápido; se respeta Retry-After."""
    h = {"User-Agent": UA, **(headers or {})}
    for k in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or k == intentos - 1:
                raise
            espera = int(e.headers.get("Retry-After") or 0) or 5 * 2 ** k
            if espera > ESPERA_MAX:
                # Medido el 23-sep: tras varios 429 seguidos Commons pasó a Retry-After 600. Dormir
                # 10 min en silencio parece un cuelgue; mejor fallar claro y reintentar más tarde.
                raise SystemExit(f"{e.code} de {urllib.parse.urlsplit(url).netloc}: pide esperar "
                                 f"{espera}s (límite por IP; en la nube la IP es compartida). "
                                 "Reintenta más tarde.")
            print(f"  {e.code}: espero {espera}s", file=sys.stderr)
            time.sleep(espera)
    raise RuntimeError("inalcanzable")


def _info_commons(params: dict) -> list[dict]:
    p = {"action": "query", "format": "json", "prop": "imageinfo",
         "iiprop": "url|size|extmetadata|mime", **params}
    d = json.loads(_get(API_COMMONS + "?" + urllib.parse.urlencode(p)))
    out = []
    for pg in (d.get("query", {}).get("pages") or {}).values():
        if "imageinfo" not in pg:
            continue
        ii = pg["imageinfo"][0]
        em = ii.get("extmetadata", {})
        lic = _limpiar(em.get("LicenseShortName", {}).get("value", ""))
        out.append({
            "titulo": pg["title"], "mime": ii.get("mime", ""),
            "ancho": ii.get("width"), "alto": ii.get("height"),
            "licencia": lic, "clase": licencia_ok(lic),
            "autor": _limpiar(em.get("Artist", {}).get("value", "")) or "Unknown",
            "url_licencia": em.get("LicenseUrl", {}).get("value", ""),
            "fuente": ii.get("descriptionurl", ""),
            "thumb": miniatura(pg["title"], ii.get("width"), ii.get("height")) or ii.get("url"),
        })
    return out


def miniatura(titulo: str, ancho: int | None, alto: int | None) -> str | None:
    """URL de miniatura en upload.wikimedia.org (determinista: md5 del nombre).

    El cuadro es VERTICAL, así que lo que limita es el ALTO: se elige el menor ancho estándar que
    dé >= ALTO_MIN de alto; si ninguno llega sin pasarse del original, el mayor que quepa. Nunca
    el ORIGINAL: medido el 23-sep, los originales caen antes en 429 (Retry-After 600) que las
    miniaturas, y pedir una miniatura más ancha que el original tampoco funciona."""
    if not ancho or not alto:
        return None
    validos = [w for w in ANCHOS_ESTANDAR if w < ancho]
    if not validos:
        return None
    w = next((w for w in validos if alto * w / ancho >= ALTO_MIN), validos[-1])
    nombre = titulo.removeprefix("File:").replace(" ", "_")
    h = hashlib.md5(nombre.encode()).hexdigest()
    q = urllib.parse.quote(nombre)
    # Los TIFF se sirven como JPG de su primera página.
    suf = (f"lossy-page1-{w}px-{q}.jpg" if nombre.lower().endswith((".tif", ".tiff"))
           else f"{w}px-{q}")
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{suf}"


def buscar_commons(q: str, n: int = 12) -> list[dict]:
    res = _info_commons({"generator": "search", "gsrsearch": q, "gsrnamespace": "6",
                         "gsrlimit": str(n)})
    return [r for r in res if r["mime"].startswith("image/") and r["clase"]]


def bajar_commons(pares: list[tuple[str, Path]]) -> list[dict]:
    """Baja varias imágenes con UNA sola consulta de metadatos (la API admite 50 títulos).

    La API de Commons limita por IP (429 `x-envoy-ratelimited`, Retry-After ~30 s) y en la nube
    la IP de salida es compartida: una consulta por imagen se atasca minutos. Las miniaturas salen
    de upload.wikimedia.org, que no comparte ese límite."""
    pares = [(t if t.startswith("File:") else "File:" + t, d) for t, d in pares]
    info: dict[str, dict] = {}
    for i in range(0, len(pares), 50):
        titulos = "|".join(t for t, _ in pares[i:i + 50])
        for r in _info_commons({"titles": titulos}):
            info[_clave(r["titulo"])] = r
    fichas = []
    for titulo, destino in pares:
        r = info.get(_clave(titulo))
        if not r:
            print(f"  ✗ no existe en Commons: {titulo}", file=sys.stderr)
            continue
        if not r["clase"]:
            print(f"  ✗ licencia NO admitida ({r['licencia']!r}): {titulo}", file=sys.stderr)
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(_get(r["thumb"]))
        ficha = {"archivo": destino.name, "origen": "wikimedia", "titulo": r["titulo"],
                 "autor": r["autor"], "licencia": r["licencia"], "clase": r["clase"],
                 "url_licencia": r["url_licencia"], "fuente": r["fuente"]}
        _registrar(destino.parent, ficha)
        fichas.append(ficha)
    return fichas


def _clave(titulo: str) -> str:
    """La API normaliza el título (guiones bajos, primera mayúscula): comparar normalizado."""
    t = titulo.replace("_", " ").strip()
    return t[:5] + t[5:6].upper() + t[6:] if t.startswith("File:") else t


def buscar_pexels(q: str, n: int = 10) -> list[dict]:
    clave = os.environ.get("PEXELS_API_KEY")
    if not clave:
        raise SystemExit("Falta PEXELS_API_KEY (gratis en pexels.com/api). En la nube: secreto del entorno.")
    d = json.loads(_get(API_PEXELS + "?" + urllib.parse.urlencode(
        {"query": q, "per_page": n, "orientation": "portrait"}), {"Authorization": clave}))
    return [{"titulo": f"pexels:{p['id']}", "autor": p["photographer"], "licencia": "Pexels License",
             "clase": "pexels", "fuente": p["url"], "thumb": p["src"]["large2x"],
             "ancho": p["width"], "alto": p["height"]} for p in d.get("photos", [])]


def _registrar(carpeta: Path, ficha: dict) -> None:
    ruta = carpeta / "creditos.json"
    fichas = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else []
    fichas = [f for f in fichas if f["archivo"] != ficha["archivo"]] + [ficha]
    ruta.write_text(json.dumps(fichas, ensure_ascii=False, indent=1), encoding="utf-8")


def texto_creditos(fichas: list[dict]) -> str:
    """Bloque para la descripción del vídeo. CC BY lo exige; PD/CC0 no, pero se cita igual."""
    lineas = []
    for f in fichas:
        lic = f["licencia"] + (f" ({f['url_licencia']})" if f.get("url_licencia") else "")
        lineas.append(f"- {f['titulo'].removeprefix('File:')} — {f['autor']} — {lic} — {f['fuente']}")
    return "Images:\n" + "\n".join(lineas)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, arg = sys.argv[1], sys.argv[2]
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 12
    if cmd == "buscar":
        for r in buscar_commons(arg, n):
            print(f"[{r['clase']:5}] {r['ancho']}x{r['alto']}  {r['titulo']}  — {r['autor'][:50]}")
    elif cmd == "pexels":
        for r in buscar_pexels(arg, n):
            print(f"{r['ancho']}x{r['alto']}  {r['fuente']}  — {r['autor']}")
    elif cmd in ("bajar", "lote"):
        if cmd == "bajar":
            if len(sys.argv) < 4:
                raise SystemExit("bajar <File:titulo> <destino.jpg>")
            pares = [(arg, Path(sys.argv[3]))]
        else:
            lista = Path(arg)
            pares = [(t.strip(), lista.parent / d.strip()) for d, t in
                     (ln.split("|", 1) for ln in lista.read_text(encoding="utf-8").splitlines()
                      if "|" in ln and not ln.lstrip().startswith("#"))]
        for f in bajar_commons(pares):
            print(f"✓ {f['archivo']}  [{f['clase']}] {f['licencia']} — {f['autor'][:60]}")
    elif cmd == "creditos":
        print(texto_creditos(json.loads(Path(arg, "creditos.json").read_text(encoding="utf-8"))))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
