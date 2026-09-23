"""Motor v2: storyboard.json + voz medida -> composición HyperFrames lista para renderizar.

    python video-v2/motor/construir.py video-v2/<proyecto>            # valida + genera index.html
    python video-v2/motor/construir.py video-v2/<proyecto> --validar  # solo valida (sin escribir)

Un proyecto es una carpeta con:
    storyboard.json       guion + escenas del catálogo + imágenes + subtítulos/aviso (lo único a mano)
    assets/voice.mp3      la voz (tools/generar_voz.py)
    assets/words.json     tiempos MEDIDOS por palabra (tools/alinear_voz.py -> {text,start,end})

Qué hace, en orden (y por qué en este orden):
  1. VALIDA antes de gastar nada: tipos del catálogo, anclas que resuelven contra la voz real,
     imágenes declaradas, un solo contador3d. Un storyboard roto (a mano o de un LLM) muere aquí
     con un mensaje que dice qué frase y qué palabra, no a los 6 min de render.
  2. Resuelve anclas -> segundos y calcula las ventanas de escena (la escena k dura hasta que
     arranca la k+1; la última, hasta el final de la voz + `cola_s`).
  3. Imágenes: baja de Commons (UNA consulta, licencia filtrada, créditos) y hornea el duotono
     de las que falten.
  4. Genera markup + PLAN (JSON) + música que sigue la forma del guion + sfx en los cortes.
  5. Ducking con carve.mjs (skill hyperframes-audio) DESPUÉS de escribir el HTML.

El catálogo (10 tipos) salió del #7 v2 hecho a mano: cada tipo ya se vio funcionar en un vídeo real.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parent
RAIZ = MOTOR.parents[1]
sys.path.insert(0, str(MOTOR))
sys.path.insert(0, str(RAIZ / "tools"))

import anclas  # noqa: E402

CATALOGO = ("foto", "revelacion", "lista", "titulo", "tarjetas", "contador3d", "curva", "puntos", "anios", "cta")
PRE = 0.14            # la escena entra un poco antes de que la voz empiece su frase
MOVS = ("push", "izq", "sube", "der", "pull")


class StoryboardError(ValueError):
    pass


# ───────────────────────────── utilidades de texto ─────────────────────────────
def txt(s: str) -> str:
    """Escapa HTML y convierte *énfasis* en dorado."""
    return re.sub(r"\*([^*]+)\*", r'<span class="gold">\1</span>', html.escape(s or ""))


def nrm(w: str) -> str:
    return re.sub(r"[^a-z0-9'$]", "", w.lower())


def palabras_de(obj) -> set[str]:
    """Todo el texto visible de una escena, normalizado palabra a palabra (para no duplicarlo en
    subtítulos: si la escena ya lo dice escrito, el subtítulo sobra)."""
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("texto", "o", "sub", "kicker", "etiqueta") and isinstance(v, str):
                out |= {nrm(p) for p in v.replace("*", "").split()}
            else:
                out |= palabras_de(v)
    elif isinstance(obj, list):
        for x in obj:
            out |= palabras_de(x)
    return {p for p in out if p}


# ───────────────────────────── validación ─────────────────────────────
def validar(sb: dict, words: list[dict]) -> list[str]:
    errores = []
    esc = sb.get("escenas") or []
    if not esc:
        errores.append("storyboard sin `escenas`")
    imgs = set((sb.get("imagenes") or {}).keys())
    n3d = 0
    for k, s in enumerate(esc):
        tipo = s.get("tipo")
        if tipo not in CATALOGO:
            errores.append(f"escena {k}: tipo {tipo!r} no existe (catálogo: {', '.join(CATALOGO)})")
            continue
        if "en" not in s:
            errores.append(f"escena {k} ({tipo}): falta `en`")
        n3d += tipo == "contador3d"
        for ref in _imagenes_usadas(s):
            if ref not in imgs:
                errores.append(f"escena {k} ({tipo}): imagen {ref!r} no declarada en `imagenes`")
    if n3d > 1:
        errores.append("más de un `contador3d`: la capa 3D es única por vídeo")
    try:
        anclas.resolver(sb, words)
    except anclas.AnclaError as e:
        errores.append(str(e))
    sueltas = [a for par in (sb.get("aviso") or {}).get("ventanas") or [] for a in par]
    sueltas += list(sb.get("golpes") or []) + list((sb.get("musica") or {}).get("oscuro") or [])
    sueltas += [str(x) for x in (sb.get("subtitulos") or [])]
    for a in sueltas:
        try:
            anclas.t(words, a)
        except anclas.AnclaError as e:
            errores.append(str(e))
    tiempos = []
    for k, s in enumerate(esc):
        try:
            tiempos.append(anclas.t(words, s["en"]) if "en" in s else None)
        except anclas.AnclaError:
            tiempos.append(None)
    for k in range(1, len(tiempos)):
        if tiempos[k] is not None and tiempos[k - 1] is not None and tiempos[k] <= tiempos[k - 1]:
            errores.append(f"escena {k}: empieza ({tiempos[k]:.2f}s) antes o a la vez que la {k - 1} ({tiempos[k - 1]:.2f}s)")
    for c in sb.get("cifras") or []:
        if not str(c.get("fuente", "")).startswith("http"):
            errores.append(f"cifra {c.get('dato')!r} sin `fuente` (URL): en un canal YMYL cada número lleva su fuente")
    if (sb.get("cifras") or sb.get("aviso")) and not (sb.get("aviso") or {}).get("lineas"):
        errores.append("hay cifras pero no `aviso.lineas` (aviso YMYL obligatorio)")
    return errores


# Tipos con movimiento continuo propio (Ken Burns, contador, 3D, años que corren): no se quedan
# quietos aunque no haya eventos anclados dentro.
_CONTINUOS = {"foto", "contador3d", "anios", "curva", "puntos", "tarjetas"}


def huecos_estaticos(p: dict, maximo: float = 2.5) -> list[str]:
    """Aviso BARATO antes del render: tramos de más de `maximo` s sin ningún evento anclado en
    escenas sin movimiento propio. Es un proxy (la puerta real es tools/medir_ritmo.py sobre el
    MP4), pero habría cazado en <1 s el CTA de Grace Groner que se comió 5 min de render: 4,6 s
    con solo "HOLD" en pantalla mientras la voz decía una frase larga."""
    avisos = []
    for k, s in enumerate(p["escenas"]):
        if s["tipo"] in _CONTINUOS or s.get("fondo"):
            continue
        fin = min(s["t1"], p["fin_voz"])            # tras la voz, la tarjeta final tiene su propio movimiento
        t = sorted({s["t0"], fin} | {x for x in _tiempos(s) if s["t0"] <= x <= fin})
        for a, b in zip(t, t[1:]):
            if b - a > maximo:
                avisos.append(f"escena {k} ({s['tipo']}): {b - a:.1f}s sin nada nuevo ({a:.1f}-{b:.1f}s) — "
                              "añade un elemento anclado o parte la frase en otra escena")
    return avisos


def _tiempos(obj) -> list[float]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in anclas.CLAVES and isinstance(v, (int, float)):
                out.append(float(v))
            else:
                out += _tiempos(v)
    elif isinstance(obj, list):
        for x in obj:
            out += _tiempos(x)
    return out


def _imagenes_usadas(s: dict) -> list[str]:
    refs = []
    if s.get("tipo") == "foto":
        refs.append(s.get("img"))
    f = s.get("fondo")
    if f:
        refs.append(f if isinstance(f, str) else f.get("img"))
    refs += [c.get("img") for c in s.get("imgs") or []]
    if (s.get("cae") or {}).get("img"):
        refs.append(s["cae"]["img"])
    if (s.get("pregunta") or {}).get("fondo"):
        refs.append(s["pregunta"]["fondo"])
    return [r for r in refs if r]


# ───────────────────────────── markup por tipo ─────────────────────────────
def m_foto(s, id_):
    k = f'<div id="{id_}-kicker" class="kicker plate" style="font-size:44px">{txt(s["kicker"]["texto"])}</div>' if s.get("kicker") else ""
    sub = f'<div id="{id_}-sub" class="sub plate" style="color:var(--ink);margin-top:14px">{txt(s["sub"]["texto"])}</div>' if s.get("sub") else ""
    t = f'<div class="stack"><div id="{id_}-titulo" class="huge shadow">{txt(s["titulo"]["texto"])}</div></div>' if s.get("titulo") else ""
    return t + (f'<div class="stack abajo">{k}{sub}</div>' if k or sub else "")


def m_revelacion(s, id_):
    return (f'<div class="stack"><div id="{id_}-l1" class="mid mute" style="margin-bottom:50px">{txt(s["linea1"]["texto"])}</div>'
            f'<div id="{id_}-l2" class="huge gold shadow">{txt(s["linea2"]["texto"])}</div></div><div id="{id_}-burst" class="burst"></div>')


_X = '<path pathLength="1" d="M18 18 L82 82" /><path pathLength="1" d="M82 18 L18 82" />'
_CHECK = '<path pathLength="1" d="M20 52 L42 74 L80 28" />'


def m_lista(s, id_):
    ic = s.get("icono", "check")
    filas = "".join(
        f'<div class="row {ic}" id="{id_}-i{k}"><svg class="mk" viewBox="0 0 100 100">{_X if ic == "x" else _CHECK}</svg>'
        f'<div class="tx {it.get("color", "")}">{txt(it["texto"])}</div></div>' for k, it in enumerate(s["items"]))
    return f'<div class="stack">{filas}</div>'


_GEAR = ('<circle cx="50" cy="50" r="17" /><path d="M50 8 L50 22 M50 78 L50 92 M8 50 L22 50 M78 50 L92 50 '
         'M20 20 L30 30 M70 70 L80 80 M80 20 L70 30 M30 70 L20 80" /><circle cx="50" cy="50" r="31" />')


def m_titulo(s, id_):
    partes = []
    if s.get("icono"):
        partes.append(f'<svg class="gear" id="{id_}-ico" viewBox="0 0 100 100">{_GEAR}</svg>')
    if s.get("kicker"):
        partes.append(f'<div id="{id_}-k" class="kicker {s["kicker"].get("color", "")}">{txt(s["kicker"]["texto"])}</div>')
    tachar = (s.get("tachar") or {}).get("linea")
    for k, l in enumerate(s.get("lineas") or []):
        estilo = l.get("estilo", "big")
        t = txt(l["texto"])
        if s.get("contador") and s["contador"].get("linea") == k:
            t = t.replace("{n}", f'<span id="{id_}-n">0</span>')
        cls = "boton" if estilo == "boton" else f'{estilo} {l.get("color", "")} shadow'
        tam = f' style="font-size:{int(l["tam"])}px"' if l.get("tam") else ""
        strike = f'<div class="strike" id="{id_}-t{k}"></div>' if tachar == k else ""
        partes.append(f'<div class="linea" id="{id_}-l{k}"><div class="{cls}"{tam}>{t}</div>{strike}</div>')
    if s.get("cheque"):
        c = s["cheque"]
        partes.append(f'<div class="cheque" id="{id_}-cheque"><div class="r"><span>{txt(c.get("etiqueta", "PAYCHECK"))}</span>'
                      f'<span>WEEKLY</span></div><div class="amt">{txt(c["monto"])}</div><div class="strike"></div></div>')
    scan = f'<div class="scan" id="{id_}-scan"></div>' if s.get("alarma") else ""
    pos = {"arriba": " arriba", "abajo": " abajo"}.get(s.get("posicion", ""), "")
    return f'<div class="stack{pos}">{"".join(partes)}</div>{scan}'


def m_tarjetas(s, id_):
    out = ""
    if s.get("titulo"):
        out += f'<div id="{id_}-tit" class="tag gold" style="top:220px;left:0;right:0;text-align:center">{txt(s["titulo"]["texto"])}</div>'
    out += "".join(f'<div class="cert" id="{id_}-c{k}"><img src="assets/t/{c["img"]}.jpg" alt="" /></div>' for k, c in enumerate(s["imgs"]))
    if s.get("flujo"):
        f = s["flujo"]
        out += f'<div id="{id_}-coins"></div><div id="{id_}-flujo" class="tag green" style="top:880px;left:0;right:0;text-align:center">{txt(f["texto"])}</div>'
        if f.get("contador"):     # opcional: sin un número real verificable, no se inventa uno
            out += (f'<div class="cnt" id="{id_}-cnt"><div class="n"><span id="{id_}-cntn">{f["contador"]["desde"]}</span></div>'
                    f'<div class="sub" style="margin-top:0">{txt(f["contador"].get("etiqueta", ""))}</div></div>')
    return out


def m_contador3d(s, id_):
    k = f'<div id="{id_}-k" class="kicker" style="position:absolute;top:250px;width:100%">{txt(s["kicker"]["texto"])}</div>' if s.get("kicker") else ""
    p = (f'<div style="position:absolute;top:520px;width:100%;text-align:center"><span class="pill line" id="{id_}-pill">'
         f'{txt(s["pill"]["texto"])}</span></div>') if s.get("pill") else ""
    return f'<canvas id="three-layer" width="1080" height="1920"></canvas>{k}<div class="money" id="{id_}-money">{s.get("prefijo", "$")}0</div>{p}'


def serie(sr: dict) -> list[tuple[float, float]]:
    """Curva ILUSTRATIVA de interés compuesto mensual, rematada en la cifra redonda `final`.
    `inicial` = pago único al principio (Grace Groner: $180 en 1935); `mensual` = aporte periódico."""
    r, v = sr["tasa"] / 12, float(sr.get("inicial", 0))
    out = [(0.0, v)]
    for m in range(1, int(sr["anios"] * 12) + 1):
        v = v * (1 + r) + sr.get("mensual", 0)
        if m % 6 == 0:
            out.append((m / 12, v))
    k = sr.get("final", out[-1][1]) / out[-1][1]
    return [(a, x * k) for a, x in out]


def m_curva(s, id_):
    W, H = 860, 620
    pts = serie(s["serie"])
    top = pts[-1][1]
    xy = [(a / s["serie"]["anios"] * W, H - v / top * H) for a, v in pts]
    linea = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    area = linea + f" L{W},{H} L0,{H} Z"
    aport = s["serie"].get("mensual", 0) * 12 * s["serie"]["anios"] + s["serie"].get("inicial", 0)
    py = H - aport / top * H
    out = (f'<svg class="chart" id="{id_}-svg" viewBox="0 0 {W} {H}"><defs><linearGradient id="gArea" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="#d8b25a" stop-opacity="0.75" /><stop offset="1" stop-color="#d8b25a" stop-opacity="0.05" /></linearGradient></defs>'
           f'<line class="axis" x1="0" y1="{H}" x2="{W}" y2="{H}" /><path class="area" id="{id_}-area" d="{area}" />'
           f'<path class="curve" id="{id_}-curve" pathLength="1" d="{linea}" />'
           + (f'<line class="paid" id="{id_}-paid" x1="0" y1="{H}" x2="{W}" y2="{py:.1f}" />' if s.get("aportado") else "") + "</svg>")
    if s.get("ilustrativo"):
        out += f'<div class="tag mute" id="{id_}-ill" style="top:250px;right:90px;font-size:26px">Illustrative</div>'
    if s.get("aportado"):
        out += f'<div class="tag green" id="{id_}-ap" style="top:1030px;left:110px">{txt(s["aportado"]["texto"])}</div>'
    if s.get("area"):
        out += f'<div class="tag ink" id="{id_}-ar" style="top:600px;left:150px;right:150px;text-align:center;font-size:52px">{txt(s["area"]["texto"])}</div>'
    if s.get("titulo"):
        out += f'<div class="tag gold" id="{id_}-tit" style="top:250px;left:0;right:0;text-align:center;font-size:52px">{txt(s["titulo"]["texto"])}</div>'
    escalas = s.get("escalas") or ([{"texto": s["etiqueta_max"]}] if s.get("etiqueta_max") else [])
    top_css = 330 if s.get("titulo") else 320
    out += "".join(f'<div class="tag gold" id="{id_}-e{k}" style="top:{top_css}px;right:100px;font-size:48px">{txt(e["texto"])}</div>'
                   for k, e in enumerate(escalas))
    s["escalas"] = escalas
    return out


def m_puntos(s, id_):
    out = (f'<div id="{id_}-num" style="position:absolute;top:280px;width:100%;text-align:center"><div class="huge" style="font-size:190px">'
           f'<span id="{id_}-n">0</span> <span class="gold">{txt(s.get("etiqueta", ""))}</span></div></div><div class="dots" id="{id_}-dots"></div>')
    c = s.get("cae") or {}
    if c.get("img"):
        out += f'<div class="card" id="{id_}-card"><img src="assets/t/{c["img"]}.jpg" alt="" /></div>'
    if c.get("texto"):
        out += f'<div class="tag gold" id="{id_}-l1" style="top:1110px;left:0;right:0;text-align:center">{txt(c["texto"])}</div>'
    a = s.get("atenuar") or {}
    if a.get("texto"):
        out += f'<div class="tag red" id="{id_}-l2" style="top:1110px;left:0;right:0;text-align:center">{txt(a["texto"])}</div>'
    return out


def m_anios(s, id_):
    k = f'<div id="{id_}-k" class="kicker">{txt(s["kicker"])}</div>' if s.get("kicker") else ""
    hitos = "".join(f'<div class="hito" id="{id_}-h{j}">{y} · {txt(t)}</div>' for j, (y, t) in enumerate(s.get("hitos") or []))
    e = f'<div class="tag gold" id="{id_}-l" style="top:1060px;left:0;right:0;text-align:center">{txt(s["etiqueta"]["texto"])}</div>' if s.get("etiqueta") else ""
    return (f'<div class="stack arriba">{k}<div class="yr" id="{id_}-yr">{s["desde"]}</div></div>{hitos}'
            f'<div class="track"><div class="fill" id="{id_}-fill"></div></div>{e}')


def m_cta(s, id_):
    out = (f'<div class="vs" id="{id_}-vs"><div class="half" id="{id_}-a"><div class="huge" style="font-size:170px">{txt(s["a"]["texto"])}</div></div>'
           f'<div class="o" id="{id_}-o">{txt(s.get("o", "or"))}</div>'
           f'<div class="half" id="{id_}-b"><div class="huge gold" style="font-size:170px">{txt(s["b"]["texto"])}</div></div></div>')
    if s.get("pregunta"):
        out += f'<div id="{id_}-q" class="tag ink" style="top:860px;left:60px;right:60px;text-align:center;font-size:58px">{txt(s["pregunta"]["texto"])}</div>'
    bot = s.get("botones") or []
    if bot:
        out += ('<div style="position:absolute;top:1040px;left:0;right:0;display:flex;justify-content:center;gap:30px">'
                + "".join(f'<div class="pill {"gold" if k == len(bot) - 1 else "line"}" id="{id_}-p{k}">{txt(b["texto"])}</div>' for k, b in enumerate(bot))
                + "</div>")
    out += f'<div class="luz" id="{id_}-luz"></div>'
    out += f'<div id="{id_}-s" class="sub ink" style="position:absolute;top:1170px;left:0;right:0">{txt(s.get("sub", ""))}</div>'
    return out


MARKUP = {"foto": m_foto, "revelacion": m_revelacion, "lista": m_lista, "titulo": m_titulo, "tarjetas": m_tarjetas,
          "contador3d": m_contador3d, "curva": m_curva, "puntos": m_puntos, "anios": m_anios, "cta": m_cta}


# ───────────────────────────── imágenes ─────────────────────────────
def asegurar_imagenes(proy: Path, imagenes: dict) -> None:
    faltan = {k: v for k, v in imagenes.items() if not (proy / "assets" / "t" / f"{k}.jpg").exists()}
    if not faltan:
        return
    import imagenes_libres as il
    from duotono import duotono
    from PIL import Image
    crudos = [(v["commons"], proy / "assets" / "img" / f"{k}.jpg") for k, v in faltan.items()
              if not (proy / "assets" / "img" / f"{k}.jpg").exists()]
    if crudos:
        il.bajar_commons(crudos)
    (proy / "assets" / "t").mkdir(parents=True, exist_ok=True)
    for k, v in faltan.items():
        crudo = proy / "assets" / "img" / f"{k}.jpg"
        if not crudo.exists():
            raise StoryboardError(f"imagen {k!r}: no se pudo bajar {v.get('commons')!r} (¿licencia no admitida o 429?)")
        duotono(Image.open(crudo), v.get("recorte", 0.02), v.get("contraste", 1.15), 1600).save(
            proy / "assets" / "t" / f"{k}.jpg", quality=82)


# ───────────────────────────── construcción ─────────────────────────────
def plan(sb: dict, words: list[dict]) -> dict:
    """Storyboard + palabras -> plan con tiempos absolutos (función pura: testeable sin disco)."""
    fr = anclas.frases(words)
    r = anclas.resolver(sb, words, fr)
    fin_voz = words[-1]["end"]
    END = round(fin_voz + float(sb.get("cola_s", 3.0)), 2)
    esc = r["escenas"]
    for k, s in enumerate(esc):
        s["t0"] = 0.0 if k == 0 else round(s["en"] - PRE, 3)
    for k, s in enumerate(esc):
        s["t1"] = round(esc[k + 1]["t0"] + 0.02, 3) if k + 1 < len(esc) else END
        s["texto_visible"] = sorted(palabras_de(s))
    # fotos: escena `foto` a opacidad plena; `fondo` al 40 %; la pregunta del CTA al 55 %
    fotos, mi = [], 0
    for k, s in enumerate(esc):
        if s["tipo"] == "foto":
            fotos.append({"id": f"ph{k}", "img": s["img"], "t0": s["t0"], "t1": min(END, s["t1"] + 0.3),
                          "mov": s.get("mov", MOVS[mi % len(MOVS)]), "opacidad": 1})
            mi += 1
        if s.get("fondo"):
            f = s["fondo"] if isinstance(s["fondo"], dict) else {"img": s["fondo"]}
            fotos.append({"id": f"ph{k}b", "img": f["img"], "t0": s["t0"], "t1": s["t1"] + 0.04,
                          "mov": f.get("mov", MOVS[mi % len(MOVS)]), "opacidad": f.get("opacidad", 0.4)})
            mi += 1
        if s["tipo"] == "cta" and (s.get("pregunta") or {}).get("fondo"):
            fotos.append({"id": f"ph{k}q", "img": s["pregunta"]["fondo"], "t0": s["pregunta"]["en"] - 0.3, "t1": END,
                          "mov": "final", "opacidad": 0.55, "aparece": s["pregunta"]["en"] - 0.29})
    sub = sb.get("subtitulos")
    rango = [fr[int(sub[0])][0], fr[int(sub[1])][-1]] if sub else [0, len(words) - 1]
    av = r.get("aviso") or {}
    golpes = [s["golpe"] for s in esc if s["tipo"] == "revelacion" and s.get("golpe") is not None]
    golpes += [s["llega"] for s in esc if s["tipo"] == "contador3d"]
    golpes += [anclas.t(words, g, fr) for g in sb.get("golpes", [])]
    impactos = [s["tachar"]["en"] for s in esc if s["tipo"] == "titulo" and s.get("tachar")
                and (s.get("lineas") or [{}])[s["tachar"]["linea"]].get("estilo") == "boton"]
    impactos += [s["cae"]["en"] for s in esc if s["tipo"] == "puntos" and s.get("cae")]
    oscuro = (sb.get("musica") or {}).get("oscuro")
    cta = next((s["t0"] for s in esc if s["tipo"] == "cta"), None)
    return {
        "D": END, "fin_voz": fin_voz, "words": words, "escenas": esc, "fotos": fotos,
        "subtitulos": rango, "calientes": sb.get("calientes", []),
        "aviso": {"lineas": av.get("lineas", []),
                  "ventanas": [[av_a, av_b] for av_a, av_b in (av.get("ventanas_t") or [])],
                  "final": fin_voz + 0.1 if av.get("final", True) and av.get("lineas") else None},
        "golpes": sorted(golpes), "impactos": sorted(impactos),
        "oscuro": [anclas.t(words, oscuro[0], fr) - 0.25, anclas.t(words, oscuro[1], fr) - 0.1] if oscuro else None,
        "cta": cta,
    }


def _html(p: dict) -> str:
    tpl = (MOTOR / "plantilla.tpl").read_text(encoding="utf-8")
    esc_html = []
    for k, s in enumerate(p["escenas"]):
        a, b = s["t0"], s["t1"]
        esc_html.append(f'      <section id="s{k}" class="clip scene" data-start="{a:.3f}" data-duration="{b - a:.3f}" '
                        f'data-track-index="{30 + k}">{MARKUP[s["tipo"]](s, f"s{k}")}</section>')
    fotos = "\n".join(
        f'      <div id="{f["id"]}" class="clip ph" data-start="{f["t0"]:.3f}" data-duration="{f["t1"] - f["t0"]:.3f}" '
        f'data-track-index="{2 + j}"><img id="{f["id"]}-img" src="assets/t/{f["img"]}.jpg" alt="" /><div class="shade"></div></div>'
        for j, f in enumerate(p["fotos"]))
    audio = ['      <audio id="vo" src="assets/voice.mp3" data-start="0" data-track-index="20" data-volume="1"></audio>',
             '      <audio id="music-bed" src="assets/music-bed.wav" data-start="0" data-track-index="19" data-volume="0.5"></audio>']
    sfx, ult = [], -9.0
    for s in p["escenas"][1:]:                       # whoosh en los cortes, sin ametrallar
        if s["t0"] - ult >= 1.2:
            sfx.append(("whoosh.wav", s["t0"] - 0.12, 0.38)); ult = s["t0"]
    sfx += [("impact.wav", g - 0.02, 0.6) for g in p["golpes"]] + [("ding.wav", g, 0.5) for g in p["golpes"][1:2]]
    sfx += [("impact.wav", t, 0.45) for t in p["impactos"]]
    audio += [f'      <audio id="sfx{j}" src="assets/_motor/{f}" data-start="{max(0, t):.3f}" data-track-index="{21 + j}" data-volume="{v}"></audio>'
              for j, (f, t, v) in enumerate(sfx)]
    aviso = '<span style="display:block">' + '</span><span style="display:block">'.join(html.escape(x) for x in p["aviso"]["lineas"]) + "</span>"
    tiene3d = any(s["tipo"] == "contador3d" for s in p["escenas"])
    rep = {
        "__END__": f'{p["D"]}', "__AUDIO__": "\n".join(audio), "__FOTOS__": fotos, "__ESCENAS__": "\n".join(esc_html),
        "__AVISO__": aviso if p["aviso"]["lineas"] else "",
        "__PLAN__": json.dumps(p, ensure_ascii=False).replace("</", "<\\/"),
        "__MOTORJS__": (MOTOR / "motor.js").read_text(encoding="utf-8"),
        "__MOTOR3D__": ('    <script type="module">\n' + (MOTOR / "motor3d.js").read_text(encoding="utf-8") + "\n    </script>") if tiene3d else "",
    }
    for k, v in rep.items():
        tpl = tpl.replace(k, v)
    return tpl


def construir(proy: Path, *, solo_validar: bool = False, con_musica: bool = True, con_carve: bool = True) -> Path:
    proy = Path(proy).resolve()
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    words = json.loads((proy / "assets" / "words.json").read_text(encoding="utf-8"))
    errores = validar(sb, words)
    if errores:
        raise StoryboardError("storyboard inválido:\n  - " + "\n  - ".join(errores))
    # ventanas del aviso: anclas -> segundos (van aparte porque son pares, no claves `en`)
    av = sb.get("aviso") or {}
    if av.get("ventanas"):
        av["ventanas_t"] = [[anclas.t(words, a), anclas.t(words, b)] for a, b in av["ventanas"]]
    p = plan(sb, words)
    for aviso in huecos_estaticos(p):
        print(f"⚠ ritmo: {aviso}")
    if solo_validar:
        print(f"✓ storyboard válido: {len(p['escenas'])} escenas, {len(p['fotos'])} fotos, {p['D']}s")
        return proy / "storyboard.json"
    asegurar_imagenes(proy, sb.get("imagenes") or {})
    dst = proy / "assets" / "_motor"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(MOTOR / "assets", dst)
    if con_musica:
        import musica
        musica.generar(proy / "assets" / "music-bed.wav", p["D"], p["golpes"],
                       tuple(p["oscuro"]) if p["oscuro"] else None, p["cta"])
    out = proy / "index.html"
    out.write_text(_html(p), encoding="utf-8")
    _andamiaje(proy)
    print(f"✓ {out.relative_to(RAIZ)}  {len(p['escenas'])} escenas · {len(p['fotos'])} fotos · {p['D']}s")
    if con_carve:
        _carve(out)
    return out


def _andamiaje(proy: Path) -> None:
    """hyperframes.json / package.json / .gitignore mínimos si el proyecto es nuevo."""
    if not (proy / "hyperframes.json").exists():
        (proy / "hyperframes.json").write_text(json.dumps({
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
            "media": {"autoProxy": True}}, indent=2) + "\n")
    if not (proy / "package.json").exists():
        (proy / "package.json").write_text(json.dumps({
            "name": proy.name, "private": True, "type": "module",
            "scripts": {"build": f"python ../motor/construir.py .",
                        "lint": "npx --yes hyperframes@0.8.62 lint",
                        "render": f"npx --yes hyperframes@0.8.62 render --quality high --output renders/{proy.name}.mp4"}},
            indent=2) + "\n")
    gi = proy / ".gitignore"
    if not gi.exists():
        gi.write_text("renders/\nsnapshots/\n.hyperframes/\nnode_modules/\nassets/_motor/\nassets/music-bed.wav\nassets/img/*.jpg\n")


def _carve(out: Path) -> None:
    carve = os.environ.get("HF_CARVE", str(Path.home() / ".claude/skills/hyperframes-audio/scripts/carve.mjs"))
    core = os.environ.get("HF_CORE")
    if Path(carve).exists() and core:
        r = subprocess.run(["node", carve, "--comp", str(out), "--bed", "music-bed", "--voice", "vo", "--core", core],
                           capture_output=True, text=True)
        print("✓ carve (ducking)" if r.returncode == 0 else "✗ carve falló:\n" + r.stderr[-800:])
    else:
        print("⚠ SIN ducking: define HF_CORE (carpeta con @hyperframes/core@0.8.62) y la skill hyperframes-audio. "
              "La música pisará la voz.")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    try:
        construir(Path(sys.argv[1]), solo_validar="--validar" in sys.argv)
    except (StoryboardError, anclas.AnclaError) as e:
        raise SystemExit(f"✗ {e}")


if __name__ == "__main__":
    main()
