"""Música REAL con licencia registrada (Wikimedia Commons: PD / CC0 / CC BY) para los Shorts.

    python tools/musica_libre.py buscar "<consulta>" [--n 20]
    python tools/musica_libre.py muestras <carpeta> "File:A.ogg" "File:B.ogg" ...   # fragmentos para escuchar

Por qué: la música generada por código (video-v2/motor/musica.py) era el eslabón más débil. En
Commons está buena parte del catálogo de Kevin MacLeod (incompetech), la música con licencia
más usada de YouTube, bajo CC BY 3.0: se puede monetizar citando "Title — Kevin MacLeod
(incompetech.com) — CC BY 3.0 — <url>", que la descripción ya añade sola ("Music:").

En el storyboard:  "musica": {"pista": {"commons": "File:Kevin MacLeod - X.ogg", "desde": 12}}
construir.py la baja (créditos en assets/musica/creditos.json) y hace la cama a la duración exacta
del vídeo (fundido de entrada/salida, bucle si hace falta, nivel de cama) antes del ducking.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imagenes_libres as il  # noqa: E402

NIVEL_CAMA = -20.0      # LUFS de la cama ANTES del ducking: presente sin pelear con la voz (-14 final)


def _info(params: dict) -> list[dict]:
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
        mp3 = next((x["src"] for x in vi.get("derivatives") or [] if x.get("transcodekey") == "mp3"), None)
        out.append({"titulo": pg["title"], "duracion": round(float(vi.get("duration") or 0), 1),
                    "licencia": lic, "clase": il.licencia_ok(lic),
                    "autor": il._limpiar(em.get("Artist", {}).get("value", "")).strip(" ;,") or "Unknown",
                    "url_licencia": em.get("LicenseUrl", {}).get("value", ""),
                    "fuente": vi.get("descriptionurl", ""), "src": mp3 or vi.get("url")})
    return out


def buscar(q: str, n: int = 20) -> list[dict]:
    res = _info({"generator": "search", "gsrsearch": f"{q} filetype:audio", "gsrnamespace": "6", "gsrlimit": str(n)})
    return [r for r in res if r["clase"] and r["src"] and r["duracion"] >= 30]


def bajar(titulos: dict[str, str], carpeta: Path) -> dict[str, Path]:
    """{nombre: "File:..."} -> crudos en `carpeta` + creditos.json. UNA consulta para todos."""
    carpeta.mkdir(parents=True, exist_ok=True)
    out, faltan = {}, {}
    for k, t in titulos.items():
        dst = carpeta / f"{k}.src"
        if dst.exists():
            out[k] = dst
        else:
            faltan[k] = t if t.startswith("File:") else "File:" + t
    if faltan:
        info = {il._clave(r["titulo"]): r for r in _info({"titles": "|".join(faltan.values())})}
        for k, t in faltan.items():
            r = info.get(il._clave(t))
            if not r:
                raise SystemExit(f"✗ pista {k!r}: no existe en Commons: {t}")
            if not r["clase"]:
                raise SystemExit(f"✗ pista {k!r}: licencia NO admitida ({r['licencia']!r})")
            dst = carpeta / f"{k}.src"
            dst.write_bytes(il._get(r["src"]))
            il._registrar(carpeta, {"archivo": dst.name, "origen": "wikimedia", "titulo": r["titulo"], "autor": r["autor"],
                                    "licencia": r["licencia"], "clase": r["clase"], "url_licencia": r["url_licencia"],
                                    "fuente": r["fuente"]})
            out[k] = dst
    return out


def _duracion(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def cama(crudo: Path, destino: Path, dur: float, desde: float = 0.0, fundido: float = 1.2) -> dict:
    """Pista -> WAV 48 kHz estéreo de `dur` s exactos al nivel de cama (loudnorm en 2 pasadas).
    Bucle si la pista (desde `desde`) es más corta que el vídeo."""
    total = _duracion(crudo)
    desde = desde % max(total - 5, 1) if desde >= total else desde
    bucle = ["-stream_loop", "-1"] if total - desde < dur else []
    base = (f"afade=t=in:st=0:d=0.4,afade=t=out:st={max(0.0, dur - fundido):.2f}:d={fundido:.2f},"
            f"loudnorm=I={NIVEL_CAMA}:TP=-3:LRA=11")
    medir = subprocess.run(["ffmpeg", "-hide_banner", *bucle, "-ss", f"{desde:.2f}", "-i", str(crudo), "-t", f"{dur:.3f}",
                            "-af", base + ":print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    import re
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", medir.stderr)
    af = base
    if m:
        med = json.loads(m.group(0))
        af += (f":measured_I={med['input_i']}:measured_TP={med['input_tp']}:measured_LRA={med['input_lra']}"
               f":measured_thresh={med['input_thresh']}:offset={med['target_offset']}:linear=true")
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *bucle, "-ss", f"{desde:.2f}", "-i", str(crudo), "-t", f"{dur:.3f}",
                    "-af", af + ",aresample=48000", "-ac", "2", "-c:a", "pcm_s16le", str(destino)], check=True)
    return {"duracion": round(_duracion(destino), 2), "bucle": bool(bucle)}


def texto_creditos(fichas: list[dict]) -> str:
    lineas = []
    for f in fichas:
        autor = f["autor"] + (" (incompetech.com)" if "macleod" in f["autor"].lower() else "")
        lic = f["licencia"] + (f" ({f['url_licencia']})" if f.get("url_licencia") else "")
        lineas.append(f"- {f['titulo'].removeprefix('File:').rsplit('.', 1)[0]} — {autor} — {lic} — {f['fuente']}")
    return "Music:\n" + "\n".join(lineas)


def main() -> None:
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "buscar":
        n = int(a[a.index("--n") + 1]) if "--n" in a else 20
        for r in buscar(a[1], n):
            print(f"{r['titulo'][5:75]:70} {r['duracion']:>6}s  {r['licencia']}")
    elif len(a) >= 3 and a[0] == "muestras":
        dst = Path(a[1])
        crudos = bajar({f"m{i + 1}": t for i, t in enumerate(a[2:])}, dst)
        for k, p in crudos.items():
            total = _duracion(p)
            mp3 = dst / f"{k}-muestra.mp3"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(20.0, total * 0.25):.1f}", "-i", str(p), "-t", "25",
                            "-af", "afade=t=in:d=0.5,afade=t=out:st=23.5:d=1.5", "-b:a", "160k", str(mp3)], check=True)
            print(f"✓ {k}: {mp3.name}  ({total:.0f}s)  {a[2 + int(k[1:]) - 1]}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
