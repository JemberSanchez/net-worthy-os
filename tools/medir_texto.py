"""Mide si el TEXTO EN PANTALLA de un MP4 se puede leer: OCR por frame contra lo que el guion promete.

    python tools/medir_texto.py <video.mp4> [--proyecto video-v2/<ref>] [--fps 2] [--json]

Por qué existe
---------------
La puerta WCAG de `producir.py` mide contraste en el DOM (color del texto contra su fondo
declarado), no sobre el píxel final: no ve un clip con mucho detalle detrás de las letras, una
sombra que no llega, un texto tapado por otra capa o uno que sale y entra demasiado rápido. Aquí se
mira el ARCHIVO, como lo vería alguien: si un OCR no consigue leer un texto que la escena promete,
es una alarma de legibilidad (hipótesis de trabajo, PROVISIONAL: se calibra con las notas del
usuario; ver docs/RUBRICA.md).

Qué mide (cada hallazgo con su segundo)
---------------------------------------
- Texto esperado no leído: cada texto del storyboard (kicker, título, líneas, ítems, CTA, aviso)
  se busca en los frames de SU escena; si el OCR no lo encuentra con parecido >= 0,8, falla.
- Texto pequeño: líneas leídas con alto < `alto_min` (fracción del alto del cuadro).
- Confianza baja: líneas leídas con confianza < `conf_min` (el OCR duda = el ojo duda).
- Contraste bajo: razón WCAG estimada en el píxel final de la caja (p95 vs p5 de luminancia
  relativa) < `contraste_min`. Hace falta porque el OCR lee MEJOR que una persona: validado con
  texto gris 70 sobre 55 (1,3:1, ilegible) -> RapidOCR lo lee con confianza 0,98. Que el OCR lea
  un texto no certifica nada; que NO lo lea, o que el contraste del píxel sea bajo, sí es alarma.
- Zona de la interfaz de Shorts: texto debajo de `zona_inferior` o en la franja derecha de los
  botones (lo tapa la UI del móvil).

Motor OCR: RapidOCR (el mismo de tools/ocr_doc.py, ONNX en CPU). El resultado por frame se
cachea junto al MP4 (<mp4>.ocr.json): repetir el análisis no repite el OCR.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

UMBRALES = {
    "alto_min": 0.018,       # alto de línea / alto del cuadro (35 px a 1920): por debajo, letra de pie de página
    "conf_min": 0.80,        # confianza OCR por debajo de la cual la línea "cuesta"
    "parecido_min": 0.80,    # texto esperado vs leído (mismo criterio que ocr_doc.buscar)
    "contraste_min": 3.0,    # WCAG AA para texto grande, medido en el PÍXEL final de la caja
    "zona_inferior": 0.84,   # y relativa desde la que tapa la UI de Shorts (título, canal, audio)
    "zona_derecha": 0.86,    # x relativa de la columna de botones (like, comentarios...)
    "zona_derecha_desde": 0.45,  # ...que empieza a esta altura
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9$%]+", " ", s.lower().replace("*", "")).strip()


def parecido(esperado: str, leido: str) -> float:
    """1.0 si `esperado` aparece en `leido`; si no, la mejor ventana del largo de lo esperado
    (el OCR mete erratas y junta líneas). Función pura."""
    q, t = norm(esperado), norm(leido)
    if not q or not t:
        return 0.0
    if q in t:
        return 1.0
    if len(t) <= len(q):
        return difflib.SequenceMatcher(None, t, q).ratio()
    return max(difflib.SequenceMatcher(None, t[k:k + len(q)], q).ratio() for k in range(len(t) - len(q) + 1))


def textos_de_escena(esc: dict) -> list[str]:
    """Todo texto que la escena PROMETE en pantalla (campos `texto`, `lineas`, `items`, botones...).
    Se excluyen placeholders de contador (`{n}`) y textos de 1 carácter (iconos)."""
    out: list[str] = []

    def visitar(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if k == "texto" and isinstance(x, str):
                    out.append(x)
                elif k in ("o", "sub") and isinstance(x, str):
                    out.append(x)
                else:
                    visitar(x)
        elif isinstance(v, list):
            for x in v:
                visitar(x)
    visitar({k: v for k, v in esc.items() if k not in ("tipo", "en", "fondo", "img", "clip", "imgs")})
    limpio = []
    for t in out:
        t = re.sub(r"\{[^}]*\}", "", t).replace("*", "").strip()
        if len(norm(t)) > 1:
            limpio.append(t)
    return limpio


def ventanas_escenas(html: str) -> list[tuple[float, float]]:
    """[(t0, t1)] de cada escena, del index.html que escribe construir.py (1 sección por escena)."""
    xs = re.findall(r'<section id="s(\d+)" class="clip scene" data-start="([\d.]+)" data-duration="([\d.]+)"', html)
    return [(float(a), float(a) + float(b)) for _, a, b in sorted(xs, key=lambda x: int(x[0]))]


def escena_en(t: float, ventanas: list[tuple[float, float]]) -> int | None:
    """Índice de la escena visible en `t` (la última que empezó; las ventanas se solapan ~0,02 s)."""
    k = None
    for i, (a, b) in enumerate(ventanas):
        if a <= t < b:
            k = i
    return k


def luminancia(rgb):
    """Luminancia relativa WCAG (sRGB linealizado) de un array HxWx3 uint8."""
    import numpy as np
    c = rgb.astype(np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def contraste_caja(rgb, caja: list[int]) -> float:
    """Razón de contraste WCAG estimada dentro de la caja: p95 (trazo o fondo claro) contra p5.
    Con sombras y contornos es una aproximación; validada en tests con casos de razón conocida."""
    import numpy as np
    x0, y0, x1, y1 = caja
    trozo = rgb[max(0, y0):max(y0 + 1, y1), max(0, x0):max(x0 + 1, x1)]
    if trozo.size == 0:
        return 0.0
    L = luminancia(trozo)
    hi, lo = float(np.percentile(L, 95)), float(np.percentile(L, 5))
    return round((hi + 0.05) / (lo + 0.05), 2)


def _tokens(s: str) -> list[str]:
    return norm(s).split()


def es_disenado(texto: str, t: float, diseno: list[dict]) -> bool:
    """¿La línea leída en `t` es texto PUESTO por el vídeo (rótulo, aviso, subtítulo) y no texto
    incidental del metraje (el cuerpo de un periódico, un letrero en un clip)?

    `diseno` = [{texto, t0, t1}]: cada texto solo cuenta en su ventana (escena, aviso, o mientras
    se dice su frase). Casa si (a) la línea está dentro del texto con parecido >= 0,9, tiene >= 4
    caracteres y 2+ palabras (o es al menos medio rótulo), o (b) tiene >= 2 palabras y >= 80 % de ellas están en ese texto. Medido en el #7:
    sin filtro, el 95 % de los "fallos" eran el periódico de la prueba y los certificados; con
    solo similitud difusa y sin tiempo, "with" o "blue chips" del periódico seguían colándose."""
    q = norm(texto)
    if len(q) < 3:
        return False
    tl = _tokens(texto)
    for d in diseno:
        if not d.get("t0", -1e9) - 0.25 <= t <= d.get("t1", 1e9) + 0.25:
            continue
        nd = norm(d["texto"])
        if len(q) >= 4 and (len(tl) >= 2 or len(q) >= 0.5 * len(nd)) and parecido(texto, d["texto"]) >= 0.9:
            return True                   # una palabra suelta solo si ES el rótulo ("Sell", "Time")
        td = set(_tokens(d["texto"]))
        if len(tl) >= 2 and sum(1 for x in tl if x in td) / len(tl) >= 0.8:
            return True
    return False


def analizar(frames: list[dict], esperados: list[dict], u: dict | None = None,
             diseno: list[dict] | None = None) -> dict:
    """Función pura sobre el OCR ya hecho.

    frames:    [{t, ancho, alto, lineas: [{texto, conf, caja:[x0,y0,x1,y1]}]}]
    esperados: [{texto, escena, t0, t1}]  (t0..t1 = ventana de la escena)
    diseno:    [{texto, t0, t1}] textos que el vídeo PONE (rótulos, aviso, frases del guion con
               su tiempo). Si se da, tamaño, confianza, contraste y zona solo se juzgan en las
               líneas que casan con alguno en su ventana (ver es_disenado).
    Devuelve {no_leidos[], pequenos[], dudosos[], bajo_contraste[], zona_ui[], leidos_pct, n_frames}."""
    u = {**UMBRALES, **(u or {})}
    rotulos = _agrupar([
        {"t": f["t"], "texto": l["texto"], "conf": l["conf"], "alto": round((l["caja"][3] - l["caja"][1]) / f["alto"], 4),
         "contraste": l.get("contraste"),
         "en_ui": l["caja"][3] / f["alto"] > u["zona_inferior"]
         or (l["caja"][2] / f["ancho"] > u["zona_derecha"] and l["caja"][1] / f["alto"] > u["zona_derecha_desde"])}
        for f in frames for l in f["lineas"]
        if len(norm(l["texto"])) >= 2 and (diseno is None or es_disenado(l["texto"], f["t"], diseno))])
    peq = [r for r in rotulos if r["alto"] < u["alto_min"]]
    dud = [r for r in rotulos if r["conf"] < u["conf_min"]]
    bc = [r for r in rotulos if r.get("contraste") is not None and r["contraste"] < u["contraste_min"]]
    ui = [r for r in rotulos if r["en_ui"]]
    no_leidos, leidos = [], 0
    for e in esperados:
        en_ventana = [f for f in frames if e["t0"] <= f["t"] < e["t1"]]
        mejor, t_mejor = 0.0, None
        for f in en_ventana:
            for l in f["lineas"]:
                p = parecido(e["texto"], l["texto"])
                if p > mejor:
                    mejor, t_mejor = p, f["t"]
            # el texto puede partirse en varias líneas: probar también la unión del frame
            p = parecido(e["texto"], " ".join(l["texto"] for l in f["lineas"]))
            if p > mejor:
                mejor, t_mejor = p, f["t"]
        if not en_ventana:
            continue                      # sin frames muestreados en la ventana: no se puede juzgar
        if mejor >= u["parecido_min"]:
            leidos += 1
        else:
            no_leidos.append({**e, "parecido": round(mejor, 2), "t_mejor": t_mejor})
    juzgados = leidos + len(no_leidos)
    return {"n_frames": len(frames), "esperados": juzgados,
            "leidos_pct": round(100 * leidos / juzgados, 1) if juzgados else None,
            "no_leidos": no_leidos, "pequenos": peq, "dudosos": dud, "bajo_contraste": bc, "zona_ui": ui}


def _agrupar(items: list[dict]) -> list[dict]:
    """Una entrada por texto (el mismo rótulo dura varios frames): primer y último segundo y el
    MEJOR valor visto. El mejor, no el peor: los rótulos entran con fundido y escala, así que su
    primer frame siempre es pequeño y sin contraste (medido en el #7: "THE PART" a 1,64:1 en su
    frame de entrada). Un rótulo falla si NI en su mejor momento se lee."""
    por: dict[str, dict] = {}
    for it in items:
        k = norm(it["texto"])
        if k not in por:
            por[k] = {**it, "t_fin": it["t"]}
        else:
            por[k]["t_fin"] = it["t"]
            por[k]["conf"] = max(por[k]["conf"], it["conf"])
            por[k]["alto"] = max(por[k]["alto"], it["alto"])
            if it.get("contraste") is not None:
                por[k]["contraste"] = max(por[k].get("contraste") or 0.0, it["contraste"])
            if "en_ui" in it:
                por[k]["en_ui"] = por[k]["en_ui"] and it["en_ui"]      # bajo la UI en TODOS sus frames
    return sorted(por.values(), key=lambda x: x["t"])


def esperados_de_proyecto(proy: Path) -> list[dict]:
    """Textos que promete cada escena + el aviso YMYL, con la ventana de su escena."""
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    ventanas = ventanas_escenas((proy / "index.html").read_text(encoding="utf-8"))
    out = []
    for k, esc in enumerate(sb.get("escenas") or []):
        if k >= len(ventanas):
            break
        t0, t1 = ventanas[k]
        for t in textos_de_escena(esc):
            out.append({"texto": t, "escena": k, "t0": t0, "t1": t1})
    return out


def ocr_frames(mp4: Path, fps: float = 2.0) -> list[dict]:
    """OCR de un frame cada 1/fps s (a resolución completa), cacheado en <mp4>.ocr.json."""
    cache = mp4.with_suffix(".ocr.json")
    clave = {"fps": fps, "mtime": int(mp4.stat().st_mtime), "tam": mp4.stat().st_size}
    if cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
        if d.get("clave") == clave:
            return d["frames"]
    import logging
    import cv2
    from rapidocr import RapidOCR
    logging.getLogger("RapidOCR").setLevel(logging.ERROR)
    motor = RapidOCR(params={"Global.log_level": "error", "Det.limit_type": "max", "Det.limit_side_len": 1920})
    cap = cv2.VideoCapture(str(mp4))
    fps_v = cap.get(cv2.CAP_PROP_FPS) or 30.0
    paso = max(1, round(fps_v / fps))
    frames, i = [], 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % paso == 0:
            H, W = fr.shape[:2]
            rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
            res = motor(rgb)
            lin = []
            for caja, txt, conf in zip(res.boxes, res.txts, res.scores) if res.boxes is not None else []:
                xs, ys = [p[0] for p in caja], [p[1] for p in caja]
                c = [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]
                lin.append({"texto": txt, "conf": round(float(conf), 3), "caja": c,
                            "contraste": contraste_caja(rgb, c)})
            frames.append({"t": round(i / fps_v, 2), "ancho": W, "alto": H, "lineas": lin})
        i += 1
    cap.release()
    cache.write_text(json.dumps({"clave": clave, "frames": frames}, ensure_ascii=False), encoding="utf-8")
    return frames


def medir(mp4: Path, proy: Path | None = None, fps: float = 2.0, umbrales: dict | None = None) -> dict:
    esperados = esperados_de_proyecto(proy) if proy else []
    return analizar(ocr_frames(mp4, fps), esperados, umbrales)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mp4")
    ap.add_argument("--proyecto")
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = medir(Path(a.mp4), Path(a.proyecto) if a.proyecto else None, a.fps)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    print(f"Frames analizados : {r['n_frames']}")
    if r["esperados"]:
        print(f"Textos esperados  : {r['leidos_pct']} % leídos ({r['esperados']})")
        for e in r["no_leidos"][:5]:
            print(f"  ✗ escena {e['escena']} t={e['t0']:.1f}-{e['t1']:.1f}s \"{e['texto']}\" (parecido {e['parecido']})")
    for k, nombre in (("pequenos", "Texto pequeño"), ("dudosos", "Confianza baja"),
                      ("bajo_contraste", "Contraste bajo"), ("zona_ui", "Bajo la UI")):
        print(f"{nombre:<18}: {len(r[k])}" + "".join(f"\n  t={x['t']}s \"{x['texto'][:40]}\" alto {x['alto']} conf {x['conf']}" for x in r[k][:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
