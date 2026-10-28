"""Crítico automático: revisa el vídeo TERMINADO, señala fallos con su segundo y su escena, parchea el
storyboard y re-renderiza (máx. 2 rondas). Nunca publica.

    python video-v2/motor/critico.py video-v2/<ref>                    # bucle completo (render incluido)
    python video-v2/motor/critico.py video-v2/<ref> --mp4 <x.mp4>      # ronda 0 sobre un MP4 ya hecho
    python video-v2/motor/critico.py video-v2/<ref> --solo-revisar     # lista de fallos, sin parchear
    python video-v2/motor/critico.py video-v2/<ref> --rondas 1

Dos mitades, como el resto del sistema (el sistema MIDE, Claude JUZGA):
  1. Medidores deterministas sobre el MP4 final y el storyboard (tools/medir_*.py), contra los
     umbrales de la rúbrica (`video-v2/motor/rubrica.json`, PROVISIONAL; `<proyecto>/rubrica.json`
     la sustituye para otra marca). Cada fallo sale con criterio, segundo, escena y evidencia.
  2. Juicio: deja en `renders/critica/rN/` fotogramas clave + guion + rúbrica (`juicio.md`). Quien
     ejecuta /producir (Claude) escribe `renders/critica/rN/juicio.json` con el mismo esquema de
     fallos; si existe, se suma (y sus parches entran). Sin él, solo medidores (y lo dice).

Parches: solo operaciones del catálogo `OPS` (perillas que el motor ya entiende). Lo que no tiene
perilla segura (guion, voz, parecido) se REPORTA con su segundo, no se toca a ciegas. Una ronda se
queda solo si su puntuación de fallos mejora (docs/POLITICA.md: entra lo que sube una métrica medida);
si empeora, se vuelve al mejor storyboard y se para.

Nada de datos de marca aquí: umbrales en la rúbrica; corpus de parecido = proyectos con el mismo
`storyboard.marca`.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parent
RAIZ = MOTOR.parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(MOTOR))
PY = sys.executable

SEV = {"alta": 3, "media": 2, "baja": 1}
# Un parche de volumen nunca baja más de esto por ronda: la siguiente ronda vuelve a medir. Sin tope,
# una ventana con poca voz y un efecto entero (-29,9 dB en el #7) mandaba la caja de 0,6 a 0,05.
PASO_MAX_DB = 6.0
OPACIDAD_MIN = 0.3      # escalón final de `fondo_suave`: por debajo, la escena queda vacía
NUMEROS = re.compile(r"\$|\d|%|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                     r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|"
                     r"billion|trillion)\b", re.I)


# ---------------------------------------------------------------------------------------------
# utilidades

def cargar_rubrica(proy: Path, ruta: Path | None = None) -> dict:
    for c in (ruta, proy / "rubrica.json", MOTOR / "rubrica.json"):
        if c and c.exists():
            return json.loads(c.read_text(encoding="utf-8"))
    raise SystemExit("no hay rúbrica (video-v2/motor/rubrica.json)")


def plan_de_html(html: str) -> dict:
    """El plan resuelto (segundos) que construir.py incrusta en index.html."""
    m = re.search(r"window\.PLAN = (\{.*?\});</script>", html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</")) if m else {}


def ventanas(plan: dict) -> list[tuple[float, float]]:
    return [(float(e["t0"]), float(e["t1"])) for e in plan.get("escenas") or []]


def escena_en(t: float | None, vs: list[tuple[float, float]]) -> int | None:
    if t is None:
        return None
    k = None
    for i, (a, b) in enumerate(vs):
        if a <= t < b:
            k = i
    return k


def fallo(criterio: str, sev: str, detalle: str, t: float | None = None, t_fin: float | None = None,
          escena=None, parche: dict | None = None, evidencia: str = "", origen: str = "medidor") -> dict:
    return {"criterio": criterio, "severidad": sev, "t": None if t is None else round(float(t), 2),
            "t_fin": None if t_fin is None else round(float(t_fin), 2), "escena": escena,
            "detalle": detalle, "evidencia": evidencia, "parche": parche, "origen": origen}


def ancla_de(words: list[dict], t: float, desde: float | None = None, hasta: float | None = None) -> str | None:
    """Ancla `frase:palabra[#n]` de la palabra que ARRANCA más cerca de `t` (dentro de [desde, hasta]).
    Es la inversa de anclas.t: el crítico habla en segundos, el storyboard en anclas."""
    import anclas
    fr = anclas.frases(words)
    mejor = None
    for k, idx in enumerate(fr):
        for i in idx:
            s = words[i]["start"]
            if words[i]["end"] - s < 0.03:          # palabra no medida: su tiempo no es fiable
                continue
            if (desde is not None and s < desde) or (hasta is not None and s > hasta):
                continue
            if mejor is None or abs(s - t) < abs(words[mejor[1]]["start"] - t):
                mejor = (k, i)
    if mejor is None:
        return None
    k, i = mejor
    n = anclas.norm(words[i]["text"])
    nth = sum(1 for j in fr[k] if j <= i and anclas.norm(words[j]["text"]) == n)
    return f"{k}:{n}" + (f"#{nth}" if nth > 1 else "")


# ---------------------------------------------------------------------------------------------
# revisiones (puras: reciben medidas, devuelven fallos)

def revisar_gancho(words: list[dict], frames_ocr: list[dict], u: dict) -> list[dict]:
    import anclas
    out = []
    if words and words[0]["start"] > u["voz_arranca_max_s"]:
        out.append(fallo("G1", "media", f"la voz arranca a los {words[0]['start']:.2f}s (> {u['voz_arranca_max_s']}s)",
                         t=0, t_fin=words[0]["start"], escena=0))
    if frames_ocr and not any(f["t"] < u["texto_antes_de_s"] and f["lineas"] for f in frames_ocr):
        out.append(fallo("G1", "alta", f"ningún texto legible en pantalla antes de {u['texto_antes_de_s']}s",
                         t=0, t_fin=u["texto_antes_de_s"], escena=0, evidencia="OCR de los primeros fotogramas vacío"))
    fr = anclas.frases(words) if words else []
    k = int(u.get("cifra_en_frase", 0))
    if fr and k < len(fr):
        texto = " ".join(words[i]["text"] for i in fr[k])
        if not NUMEROS.search(texto):
            out.append(fallo("G1", "media", f"la frase {k} del gancho no dice ninguna cifra: «{texto}»",
                             t=words[fr[k][0]]["start"], escena=0))
    return out


def revisar_reganchos(plan: dict, words: list[dict], u: dict) -> list[dict]:
    golpes = sorted(float(g) for g in plan.get("golpes") or [])
    fin = float(plan.get("fin_voz") or (words[-1]["end"] if words else 0))
    marcas = [0.0] + golpes + [fin]
    out = []
    vs = ventanas(plan)
    for a, b in zip(marcas, marcas[1:]):
        if b - a > u["hueco_max_s"]:
            medio = (a + b) / 2
            ancla = ancla_de(words, medio, a + 2, b - 2)
            out.append(fallo("G2", "media", f"{b - a:.1f}s sin re-gancho ({a:.1f}-{b:.1f}s)", t=a, t_fin=b,
                             escena=escena_en(medio, vs), parche={"op": "golpe", "ancla": ancla} if ancla else None))
    return out


def revisar_texto(rt: dict, vs: list[tuple[float, float]], u: dict) -> list[dict]:
    out = []
    for e in rt.get("no_leidos") or []:
        esc = e["escena"]
        p = {"op": "aviso_placa"} if esc == "aviso" else {"op": "fondo_suave", "escena": esc}
        out.append(fallo("L1", "alta", f"\"{e['texto']}\" no se lee en el MP4 (OCR, parecido {e['parecido']})",
                         t=e["t0"], t_fin=e["t1"], escena=esc, parche=p, evidencia="tools/medir_texto.py"))
    for x in rt.get("bajo_contraste") or []:
        esc = escena_en(x["t"], vs)
        out.append(fallo("L1", "alta", f"\"{x['texto'][:40]}\" con contraste {x['contraste']}:1 en el píxel final "
                         f"(< {u['contraste_min']})", t=x["t"], t_fin=x.get("t_fin"), escena=esc,
                         parche=_parche_texto(x, esc, rt), evidencia="tools/medir_texto.py"))
    for x in rt.get("pequenos") or []:
        esc = escena_en(x["t"], vs)
        es_aviso = _es_aviso(x["texto"], rt)
        out.append(fallo("L1", "media", f"\"{x['texto'][:40]}\" mide {x['alto'] * 1920:.0f}px de alto "
                         f"(< {u['alto_min'] * 1920:.0f}px a 1920)", t=x["t"], t_fin=x.get("t_fin"),
                         escena="aviso" if es_aviso else esc,
                         parche={"op": "aviso_tam", "valor": 30} if es_aviso else None))
    for x in rt.get("zona_ui") or []:
        out.append(fallo("L1", "baja", f"\"{x['texto'][:40]}\" cae bajo la interfaz de Shorts", t=x["t"],
                         t_fin=x.get("t_fin"), escena=escena_en(x["t"], vs)))
    return out


def _es_aviso(texto: str, rt: dict) -> bool:
    import medir_texto as T
    return any(T.parecido(texto, a) >= 0.8 or T.parecido(a, texto) >= 0.8 for a in rt.get("aviso_lineas") or [])


def _parche_texto(x: dict, esc, rt: dict) -> dict | None:
    if _es_aviso(x["texto"], rt):
        return {"op": "aviso_placa"}
    return {"op": "fondo_suave", "escena": esc} if esc is not None else None


def revisar_ritmo(rr: dict, words: list[dict], vs, u: dict) -> list[dict]:
    if rr["max_s"] <= u["quieto_max_s"]:
        return []
    a, b = rr["desde_s"], rr["desde_s"] + rr["max_s"]
    ancla = ancla_de(words, (a + b) / 2, a + 0.3, b - 0.3)
    return [fallo("R1", "alta", f"{rr['max_s']}s sin nada nuevo en pantalla", t=a, t_fin=b,
                  escena=escena_en(a, vs), parche={"op": "golpe", "ancla": ancla} if ancla else None,
                  evidencia="tools/medir_ritmo.py")]


def revisar_voz(rv: dict, vs, u: dict) -> list[dict]:
    out = []
    if not u["wpm_min"] <= rv["wpm"] <= u["wpm_max"]:
        out.append(fallo("V1", "media", f"voz a {rv['wpm']:.0f} palabras/min (fuera de {u['wpm_min']}-{u['wpm_max']})"))
    for p in rv["pausas"]:
        lim = u["pausa_dentro_s"] if p["tipo"] == "dentro" else u["pausa_entre_s"]
        if p["dur"] > lim:
            out.append(fallo("V1", "media" if p["tipo"] == "dentro" else "baja",
                             f"silencio de {p['dur']}s {p['tipo']} de frase tras \"{p['tras']}\" "
                             "(se arregla re-sintetizando la voz, no en el storyboard)",
                             t=p["t"], t_fin=p["t"] + p["dur"], escena=escena_en(p["t"], vs)))
    if rv["silencio_inicial_s"] > u["silencio_inicial_max_s"]:
        out.append(fallo("V1", "media", f"{rv['silencio_inicial_s']}s de silencio antes de la primera palabra", t=0, escena=0))
    return out


def revisar_sincronia(rv: dict, vs, u: dict) -> list[dict]:
    out = []
    if rv["pct_medidas"] < u["medidas_min_pct"]:
        malas = rv["degeneradas"] + rv["sobre_silencio"]
        out.append(fallo("S1", "media", f"solo el {rv['pct_medidas']} % de las palabras tiene tiempo medido "
                         f"({len(rv['degeneradas'])} de duración 0, {len(rv['sobre_silencio'])} sobre silencio): "
                         "sus subtítulos y anclas no son exactos — "
                         + ", ".join(f"\"{m['palabra']}\"@{m['t']}s" for m in malas[:5]),
                         t=malas[0]["t"] if malas else None, escena=escena_en(malas[0]["t"], vs) if malas else None,
                         evidencia="tools/medir_voz.py"))
    return out


def eventos_sonido(plan: dict, proy: Path, sb: dict, words: list[dict]) -> list[dict]:
    """Cada efecto que suena, con su tramo REAL (duración del WAV) y de dónde sale:
    `sonidos[i]` del storyboard (perilla `vol`), sfx de un clip/imagen, o del motor (whoosh de
    corte, impacto/riser de golpe: sin perilla en el storyboard)."""
    import anclas
    import soundfile as sf

    def dur(ruta: Path, defecto: float = 0.8) -> float:
        try:
            return float(sf.info(str(ruta)).duration)
        except Exception:                                # noqa: BLE001 - archivo ausente: estimación
            return defecto
    fr = anclas.frases(words) if words else []
    sb_t = []
    for i, x in enumerate(sb.get("sonidos") or []):
        try:
            sb_t.append((i, x["sfx"], anclas.t(words, x["en"], fr)))
        except (anclas.AnclaError, KeyError):
            pass
    ev = []
    for s in plan.get("sonidos") or []:
        d = s.get("dur") or dur(proy / "assets" / "sfx" / s["archivo"])
        i = next((i for i, n, t in sb_t if n == s["sfx"] and abs(t - s["t"]) < 0.06), None)
        ev.append({"t0": s["t"], "t1": s["t"] + d, "fuente": f"sonidos[{i}] {s['sfx']}" if i is not None else f"sfx {s['sfx']}",
                   "sonido": i, "vol": s.get("vol"), "archivo": str(proy / "assets" / "sfx" / s["archivo"])})
    m = MOTOR / "assets"
    vm = {"whoosh": 0.38, "impacto": 0.6, "riser": 0.3, **(plan.get("vol_motor") or {})}   # = construir.VOL_MOTOR
    ev += [{"t0": t - 0.12, "t1": t - 0.12 + dur(m / "whoosh.wav"), "fuente": "motor whoosh (corte)", "motor": "whoosh",
            "archivo": str(m / "whoosh.wav"), "vol": vm["whoosh"]} for t in plan.get("cortes") or []]
    ev += [{"t0": g - 0.02, "t1": g + dur(m / "impact.wav"), "fuente": "motor impacto (golpe)", "motor": "impacto",
            "archivo": str(m / "impact.wav"), "vol": vm["impacto"]} for g in plan.get("golpes") or []]
    ev += [{"t0": g - 1.0, "t1": g, "fuente": "motor riser (golpe)", "motor": "riser",
            "archivo": str(m / "riser.wav"), "vol": vm["riser"]} for g in plan.get("golpes") or [] if g - 1.0 >= 0.5]
    if plan.get("serie"):
        t = float(plan["serie"]["t0"])
        ev.append({"t0": t, "t1": t + dur(proy / "assets" / "_motor" / "logo.wav", 1.5), "fuente": "motor logo de serie"})
    return ev


def energia_evento(e: dict, t: float, w: float = 0.5) -> float:
    """Energía en la banda de voz que mete el efecto `e` (su WAV a su volumen) en [t, t+w].
    Sirve para repartir la culpa cuando suenan varios a la vez. Sin archivo legible: 0."""
    import medir_mezcla as M
    import numpy as np
    import soundfile as sf
    try:
        x, sr = sf.read(e["archivo"], always_2d=True)
    except Exception:                                    # noqa: BLE001
        return 0.0
    x = x.mean(axis=1) * float(e.get("vol") or 0.5)
    a, b = int(max(0.0, t - e["t0"]) * sr), int(max(0.0, t + w - e["t0"]) * sr)
    seg = x[a:b]
    if len(seg) < 64:
        return 0.0
    return M.energia_banda(np.asarray(seg, dtype=np.float64), sr)


def culpable(x: dict, eventos: list[dict], w: float = 0.5) -> dict | None:
    """El efecto que MÁS energía mete en la ventana (medido sobre su WAV), no el primero de la
    lista: en el #7 (2,5-3,0 s) se culpó a la caja, se bajó 6 dB y la ventana no se movió
    (-29,9 -> -30,0 dB): sonaba también el whoosh del corte de 2,76 s."""
    hits = [e for e in eventos if e["t0"] < x["t"] + w and e["t1"] > x["t"]]
    if len(hits) <= 1:
        return hits[0] if hits else None
    return max(hits, key=lambda e: energia_evento(e, x["t"], w) if e.get("archivo") else 0.0)


def revisar_mezcla(rm: dict | None, loud: dict | None, vol_actual: float, vs, u: dict,
                   eventos: list[dict] | None = None, sb: dict | None = None) -> list[dict]:
    """Ventanas con la voz tapada, separadas por CULPABLE: efecto que suena en esa ventana o, si
    no suena ninguno, la música. Cada uno se parchea con su propia perilla (o se reporta)."""
    import numpy as np
    out = []
    if rm and rm["pct_tapada"] > u["tapada_max_pct"]:
        lim = u["voz_sobre_fondo_db"]
        w = 0.5
        malas = [x for x in rm.get("ventanas") or [] if x["db"] < lim]
        culpa: dict[str, list[dict]] = {}
        for x in malas:
            c = culpable(x, eventos or [], w)
            culpa.setdefault(c["fuente"] if c else "música", []).append(x)
        n = max(1, rm["n_ventanas"])
        solo_mus = [x["db"] for x in rm.get("ventanas") or []
                    if not any(e["t0"] < x["t"] + w and e["t1"] > x["t"] for e in eventos or [])]
        for fuente, xs in sorted(culpa.items(), key=lambda kv: -len(kv[1])):
            peor = min(xs, key=lambda x: x["db"])
            parche = None
            if fuente == "música" and solo_mus:
                # bajar la cama lo justo para que solo `tapada_max_pct` de sus ventanas quede bajo el umbral
                deficit = min(PASO_MAX_DB, max(0.0, lim - float(np.percentile(solo_mus, u["tapada_max_pct"]))))
                nuevo = round(max(0.05, vol_actual * 10 ** (-deficit / 20)), 3)
                parche = {"op": "musica_volumen", "valor": nuevo} if nuevo < vol_actual else None
            elif fuente.startswith("motor ") and any(e.get("motor") for e in eventos if e["fuente"] == fuente):
                e = next(e for e in eventos if e["fuente"] == fuente)
                bajar = min(PASO_MAX_DB, max(3.0, lim - peor["db"]))
                parche = {"op": "motor_vol", "efecto": e["motor"],
                          "valor": round(max(0.0, float(e["vol"]) * 10 ** (-bajar / 20)), 3)}
            elif fuente.startswith("sonidos["):
                e = next(e for e in eventos if e["fuente"] == fuente)
                bajar = min(PASO_MAX_DB, max(3.0, lim - peor["db"]))
                parche = {"op": "sfx_vol", "indice": e["sonido"],
                          "valor": round(max(0.05, (e["vol"] or 0.5) * 10 ** (-bajar / 20)), 3)}
            sev = "alta" if len(xs) / n * 100 > 3 * u["tapada_max_pct"] else "media"
            out.append(fallo("M1", sev, f"{fuente} tapa la voz en {len(xs)} ventana(s) de {w}s "
                             f"(peor {peor['db']} dB < {lim} dB)" + ("" if parche or fuente == "música"
                                                                     else " — sin perilla en el storyboard (motor)"),
                             t=peor["t"], t_fin=peor["t"] + w, escena=escena_en(peor["t"], vs), parche=parche,
                             evidencia=f"tools/medir_mezcla.py · voz/fondo mediana {rm['mediana_db']} dB, "
                                       f"{rm['pct_tapada']} % tapada"))
    if loud:
        if abs(loud["lufs"] - u["lufs"]) > u["lufs_tol"]:
            out.append(fallo("M1", "alta", f"loudness {loud['lufs']} LUFS (objetivo {u['lufs']} ±{u['lufs_tol']})"))
        if loud["pico"] >= u["pico_max_dbtp"]:
            out.append(fallo("M1", "media", f"pico real {loud['pico']} dBTP (objetivo < {u['pico_max_dbtp']}): "
                             "riesgo de clipping al recodificar la plataforma (motor: loudnorm/AAC, no storyboard)"))
    return out


def revisar_datos(sb: dict, rt: dict | None) -> list[dict]:
    out = []
    guion = " ".join(g["texto"] for g in sb.get("guion") or [])
    if NUMEROS.search(guion) and not sb.get("cifras"):
        out.append(fallo("D1", "alta", "el guion da cifras y el storyboard no trae `cifras` con fuente"))
    for c in sb.get("cifras") or []:
        if not str(c.get("fuente", "")).startswith("http"):
            out.append(fallo("D1", "alta", f"cifra sin fuente verificable: {c.get('dato', '')[:60]}"))
    if (sb.get("cifras") or NUMEROS.search(guion)) and not (sb.get("aviso") or {}).get("lineas"):
        out.append(fallo("D1", "alta", "sin aviso YMYL en pantalla"))
    return out


def revisar_parecido(rp: dict, u: dict) -> list[dict]:
    out = []
    lims = {"visual": u["visual_max"], "guion": u["guion_max"], "estructura": u["estructura_max"], "recursos": u["recursos_max"]}
    for k, lim in lims.items():
        m = (rp.get("max") or {}).get(k)
        if m and m["valor"] is not None and m["valor"] > lim:
            extra = ""
            if k == "recursos":
                fila = next(f for f in rp["filas"] if f["ref"] == m["ref"])
                extra = f": {', '.join(fila['recursos_comunes'][:4])}"
            out.append(fallo("P1", "media", f"parecido {k} {m['valor']} con {m['ref']} (> {lim}){extra} — "
                             "variar en el guion/storyboard (riesgo de contenido repetitivo)"))
    return out


def fallos_de_qa(qa: dict, vs) -> list[dict]:
    """Una puerta de producir.py que falló ANTES del render (contraste WCAG) -> fallos con segundo."""
    out = []
    for p in qa.get("puertas") or []:
        if p["ok"]:
            continue
        if p["puerta"] == "contraste":
            for txt, ratio, req, t in re.findall(r'"([^"]*)" ([\d.]+):1 \(< ([\d.]+)\) en t≈([\d.]+)s', p["detalle"]):
                esc = escena_en(float(t), vs)
                # `check` corta el texto a 30 caracteres desde el PRINCIPIO: el aviso se reconoce por
                # prefijo; por subcadena, "for" (un rótulo del CTA del #8) pasaba por aviso
                aviso = len(txt) >= 6 and any(a.lower().startswith(txt.lower()) for a in (qa.get("_aviso") or []))
                out.append(fallo("L1", "alta", f"\"{txt}\" {ratio}:1 en el DOM (< {req}, WCAG AA)", t=float(t),
                                 escena="aviso" if aviso else esc,
                                 parche={"op": "aviso_placa"} if aviso else ({"op": "fondo_suave", "escena": esc} if esc is not None else None),
                                 evidencia="producir.py · puerta contraste (hyperframes check)"))
        else:
            out.append(fallo("QA", "alta", f"puerta '{p['puerta']}' fallida: {p['detalle'][-200:]}"))
    return out


# ---------------------------------------------------------------------------------------------
# parches

OPS = ("golpe", "aviso_placa", "aviso_tam", "musica_volumen", "sfx_vol", "motor_vol", "fondo_suave", "set")
SET_PERMITIDO = re.compile(r"^(escenas\.\d+\.[a-z_.0-9]+|aviso\.[a-z_]+|musica\.volumen|golpes|calientes)$")


def aplicar(sb: dict, parches: list[dict]) -> tuple[dict, list[str]]:
    """Aplica parches del catálogo OPS sobre una COPIA. Devuelve (storyboard, descripciones aplicadas).
    Un parche fuera del catálogo o que no cambia nada se ignora (y no cuenta como aplicado)."""
    sb = copy.deepcopy(sb)
    hechos: list[str] = []
    for p in parches:
        op = (p or {}).get("op")
        if op == "golpe" and p.get("ancla"):
            g = sb.setdefault("golpes", [])
            if p["ancla"] not in g:
                g.append(p["ancla"])
                hechos.append(f"golpe (re-gancho) en {p['ancla']}")
        elif op == "aviso_placa" and sb.get("aviso") and not sb["aviso"].get("placa"):
            sb["aviso"]["placa"] = True
            hechos.append("aviso con placa oscura")
        elif op == "aviso_tam" and sb.get("aviso") and sb["aviso"].get("tam", 23) < p.get("valor", 30):
            sb["aviso"]["tam"] = int(p.get("valor", 30))
            hechos.append(f"aviso a {sb['aviso']['tam']}px")
        elif op == "musica_volumen":
            m = sb.setdefault("musica", {})
            v = round(float(p["valor"]), 3)
            if v < float(m.get("volumen", 0.5)):
                m["volumen"] = v
                hechos.append(f"música a volumen {v}")
        elif op == "sfx_vol" and isinstance(p.get("indice"), int) and p["indice"] < len(sb.get("sonidos") or []):
            x = sb["sonidos"][p["indice"]]
            v = round(float(p["valor"]), 3)
            if v < float(x.get("vol", 1.0)):
                x["vol"] = v
                hechos.append(f"efecto sonidos[{p['indice']}] ({x.get('sfx')}) a volumen {v}")
        elif op == "motor_vol" and p.get("efecto") in ("whoosh", "impacto", "riser"):
            m = sb.setdefault("mezcla", {})
            v = round(float(p["valor"]), 3)
            if v < float(m.get(p["efecto"], {"whoosh": 0.38, "impacto": 0.6, "riser": 0.3}[p["efecto"]])):
                m[p["efecto"]] = v
                hechos.append(f"efecto del motor '{p['efecto']}' a volumen {v}")
        elif op == "fondo_suave" and isinstance(p.get("escena"), int):
            esc = (sb.get("escenas") or [])
            e = esc[p["escena"]] if p["escena"] < len(esc) else None
            if e is not None and e.get("tipo") != "foto":
                if not e.get("fondo_suave"):
                    e["fondo_suave"] = True
                    hechos.append(f"escena {p['escena']}: fondo suave tras el texto")
                elif float(e.get("fondo_opacidad", 1.0)) > OPACIDAD_MIN:
                    # ya suavizado y sigue sin leerse (#7 tras realinear la voz: "stocks" 2,95:1):
                    # siguiente escalón, el fondo pesa menos
                    e["fondo_opacidad"] = round(max(OPACIDAD_MIN, float(e.get("fondo_opacidad", 1.0)) * 0.6), 2)
                    hechos.append(f"escena {p['escena']}: fondo más tenue (opacidad {e['fondo_opacidad']})")
        elif op == "set" and SET_PERMITIDO.match(str(p.get("ruta", ""))):
            obj, partes = sb, p["ruta"].split(".")
            try:
                for k in partes[:-1]:
                    obj = obj[int(k)] if isinstance(obj, list) else obj.setdefault(k, {})
                ult = int(partes[-1]) if isinstance(obj, list) else partes[-1]
                if (obj[ult] if isinstance(obj, list) else obj.get(ult)) != p.get("valor"):
                    obj[ult] = p.get("valor")
                    hechos.append(f"{p['ruta']} = {json.dumps(p.get('valor'), ensure_ascii=False)[:60]}")
            except (KeyError, IndexError, ValueError, TypeError):
                pass
    return sb, list(dict.fromkeys(hechos))


def volcar(sb: dict, original: str) -> str:
    """JSON con la MISMA sangría que el storyboard original: el diff de un parche debe leerse en
    una línea, no reformatear 900 (pasó en la 1ª ronda del #7: indent=2 sobre un archivo en 1)."""
    m = re.search(r"\n( +)\S", original)
    fin = "\n" if original.endswith("\n") else ""
    return json.dumps(sb, ensure_ascii=False, indent=len(m.group(1)) if m else 1) + fin


def puntuar(fallos: list[dict]) -> int:
    return sum(SEV.get(f["severidad"], 1) for f in fallos)


# ---------------------------------------------------------------------------------------------
# medición sobre un proyecto + MP4

def medir_loudness(mp4: Path) -> dict | None:
    r = subprocess.run([PY, str(RAIZ / "tools" / "medir_loudness.py"), str(mp4)], capture_output=True, text=True)
    lufs = re.search(r"integrado\s*:\s*(-?[\d.]+)", r.stdout)
    pico = re.search(r"Pico real\s*:\s*(-?[\d.]+)", r.stdout)
    return {"lufs": float(lufs.group(1)), "pico": float(pico.group(1))} if lufs and pico else None


def revisar(proy: Path, mp4: Path, rub: dict, qa: dict | None = None, juicio: Path | None = None,
            sb: dict | None = None, html: str | None = None) -> dict:
    """Todos los medidores + revisiones (+ el juicio de esa ronda, si existe). Devuelve
    {fallos, medidas, puntuacion}. La puntuación cuenta SOLO los medidores: es lo que se compara
    entre rondas (una ronda sin juicio escrito no debe parecer mejor por tener menos fallos)."""
    import medir_mezcla
    import medir_parecido
    import medir_ritmo
    import medir_texto
    import medir_voz
    u = {k: v for c in rub["criterios"].values() for k, v in c.items() if k != "nombre"}
    # storyboard y plan DEL VÍDEO que se revisa (instantánea de su ronda), no los actuales del
    # proyecto: una ronda abortada dejó un index.html de otro storyboard y el crítico revisó el r0
    # con el plan equivocado (28-oct: caja a 0,05 "medida" sobre un plan que ya la tenía a 0,05)
    sb = sb if sb is not None else json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    plan = plan_de_html(html if html is not None else (proy / "index.html").read_text(encoding="utf-8"))
    vs = ventanas(plan)
    words = json.loads((proy / "assets" / "words.json").read_text(encoding="utf-8"))
    med: dict = {}
    fallos: list[dict] = []
    if qa:
        qa = {**qa, "_aviso": (sb.get("aviso") or {}).get("lineas") or []}
        fallos += fallos_de_qa(qa, vs)

    # L1 legibilidad: textos de cada escena + líneas del aviso en sus ventanas (segundos del plan)
    frames = medir_texto.ocr_frames(mp4, 2.0)
    esperados = []
    for k, esc in enumerate(sb.get("escenas") or []):
        if k < len(vs):
            esperados += [{"texto": t, "escena": k, "t0": vs[k][0], "t1": vs[k][1]} for t in medir_texto.textos_de_escena(esc)]
    av = plan.get("aviso") or {}
    vent_aviso = list(av.get("ventanas") or [])
    if av.get("final") is not None:
        vent_aviso.append([av["final"] + 0.4, float(plan.get("D") or av["final"] + 1)])   # tras su fundido
    for a, b in vent_aviso:
        esperados += [{"texto": l, "escena": "aviso", "t0": a, "t1": b} for l in av.get("lineas") or []]
    for pr in plan.get("pruebas") or []:
        src = next((x for x in sb.get("pruebas") or [] if x.get("img") == pr.get("img")), {})
        if src.get("texto"):
            esperados.append({"texto": src["texto"], "escena": escena_en(pr["t0"], vs), "t0": pr["t0"], "t1": pr["t1"]})
    import anclas
    fr = anclas.frases(words)
    diseno = [{"texto": e["texto"], "t0": e["t0"], "t1": e["t1"]} for e in esperados]
    diseno += [{"texto": " ".join(words[i]["text"] for i in idx), "t0": words[idx[0]]["start"] - 0.5,
                "t1": words[idx[-1]]["end"] + 0.5} for idx in fr]          # subtítulos: mientras se dice
    rt = medir_texto.analizar(frames, esperados, {k: u[k] for k in medir_texto.UMBRALES if k in u}, diseno=diseno)
    rt["aviso_lineas"] = av.get("lineas") or []
    med["texto"] = {k: rt[k] for k in ("leidos_pct", "esperados", "n_frames")}
    fallos += revisar_texto(rt, vs, u)
    fallos += revisar_gancho(words, frames, u)
    fallos += revisar_reganchos(plan, words, u)

    rr = medir_ritmo.tramo_quieto(medir_ritmo.leer_frames(str(mp4)))
    med["ritmo"] = rr
    fallos += revisar_ritmo(rr, words, vs, u)

    rv = medir_voz.medir(words, voz_en=medir_voz.detector_voz(proy / "assets" / "voice.mp3"),
                         pausa_dentro=u["pausa_dentro_s"], pausa_entre=u["pausa_entre_s"])
    med["voz"] = {k: rv[k] for k in ("wpm", "silencio_inicial_s", "pct_medidas")} | {"pausas": len(rv["pausas"])}
    fallos += revisar_voz(rv, vs, u) + revisar_sincronia(rv, vs, u)

    rm = medir_mezcla.medir(medir_mezcla.decodificar(mp4), medir_mezcla.decodificar(proy / "assets" / "voice.mp3"),
                            medir_mezcla.tramos_de_words(words), umbral_db=u["voz_sobre_fondo_db"])
    loud = medir_loudness(mp4)
    med["mezcla"] = {k: rm[k] for k in ("mediana_db", "p10_db", "pct_tapada")} | (loud or {})
    fallos += revisar_mezcla(rm, loud, float(plan.get("musica_volumen", 0.5)), vs, u,
                             eventos_sonido(plan, proy, sb, words), sb)

    fallos += revisar_datos(sb, rt)
    rp = medir_parecido.medir(proy, mp4=mp4)
    med["parecido"] = rp["max"]
    fallos += revisar_parecido(rp, u)

    medidos = puntuar(fallos)
    if juicio is not None:
        fallos += leer_juicio(juicio)
    fallos.sort(key=lambda f: (-SEV.get(f["severidad"], 1), f["t"] if f["t"] is not None else 1e9))
    return {"fallos": fallos, "medidas": med, "puntuacion": medidos}


# ---------------------------------------------------------------------------------------------
# juicio (Claude / persona): fotogramas clave + guion + rúbrica -> juicio.json

JUICIO = """# Juicio del crítico — {ref}

Mira los fotogramas (`{dir}/f_*.jpg`, el nombre lleva el segundo) y el guion. Escribe
`{dir}/juicio.json` (juicio de ESTA ronda; vuelve a correr el crítico con `--mp4 {dir}.mp4`) = `{{"fallos": [{{"criterio", "severidad": "alta|media|baja", "t", "escena",
"detalle", "parche"}}]}}`. `parche` solo con operaciones del catálogo: {ops}
(`set` admite rutas `escenas.N.campo`, `aviso.*`, `musica.volumen`, `golpes`, `calientes`).
Sin parche = se reporta y no se toca. No repitas lo que ya midieron los medidores (abajo).

Criterios de juicio (docs/RUBRICA.md, PROVISIONAL):
- J1 Gancho: en 1-2 s, ¿se entiende el resultado raro con su cifra y la imagen frena el scroll?
- J2 Imagen = palabra: ¿cada plano muestra lo que dice la voz en ese segundo?
- J3 Exactitud: ¿cada cifra del guion coincide con su fuente (`cifras`)? ¿algo suena a consejo?
- J4 Honestidad: ¿está la parte incómoda (riesgo, sesgo de superviviente)?
- J5 Cierre: ¿UNA dicotomía clara y el final enlaza con el inicio?
- J6 Acabado: textos cortados, solapes, elementos fuera de cuadro, faltas de ortografía.

## Guion
{guion}

## Cifras y fuentes
{cifras}

## Escenas (segundos)
{escenas}

## Ya medido ({n} fallos)
{medidos}
"""


def preparar_juicio(proy: Path, mp4: Path, sb: dict, plan: dict, fallos: list[dict], dir_: Path) -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    ts = {0.0, 0.5, 1.2, 2.5}
    ts |= {round((a + b) / 2, 2) for a, b in ventanas(plan)}
    ts |= {f["t"] for f in fallos if f["t"] is not None}
    for f in dir_.glob("f_*.jpg"):
        f.unlink()
    for t in sorted(ts):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t}", "-i", str(mp4), "-frames:v", "1",
                        "-vf", "scale=540:-2", str(dir_ / f"f_{t:06.2f}.jpg")], check=False)
    esc = "\n".join(f"- {k} `{e['tipo']}` {a:.2f}-{b:.2f}s" for k, (e, (a, b)) in
                    enumerate(zip(sb.get("escenas") or [], ventanas(plan))))
    txt = JUICIO.format(ref=sb.get("ref", proy.name), dir=dir_.relative_to(RAIZ) if dir_.is_relative_to(RAIZ) else dir_,
                        ops=", ".join(OPS), guion="\n".join(f"- [{g['id']}] {g['texto']}" for g in sb.get("guion") or []),
                        cifras="\n".join(f"- {c['dato']} — {c['fuente']}" for c in sb.get("cifras") or []) or "(ninguna)",
                        escenas=esc, n=len(fallos), medidos="\n".join(f"- {linea(f)}" for f in fallos) or "(ninguno)")
    (dir_ / "juicio.md").write_text(txt, encoding="utf-8")
    return dir_ / "juicio.md"


def leer_juicio(dir_: Path) -> list[dict]:
    f = dir_ / "juicio.json"
    if not f.exists():
        return []
    d = json.loads(f.read_text(encoding="utf-8"))
    out = []
    for x in d.get("fallos") or []:
        p = x.get("parche")
        out.append(fallo(x.get("criterio", "J"), x.get("severidad", "media"), x.get("detalle", ""), x.get("t"),
                         x.get("t_fin"), x.get("escena"), p if (p or {}).get("op") in OPS else None,
                         x.get("evidencia", ""), origen="juicio"))
    return out


# ---------------------------------------------------------------------------------------------
# bucle

def linea(f: dict) -> str:
    t = "" if f["t"] is None else (f"t={f['t']:.1f}s" + (f"-{f['t_fin']:.1f}s" if f.get("t_fin") else "") + " ")
    e = "" if f["escena"] is None else f"escena {f['escena']} · "
    return f"[{f['severidad']}] {f['criterio']} {t}{e}{f['detalle']}" + (" → parche" if f.get("parche") else "")


def render(proy: Path) -> tuple[Path | None, dict, str]:
    """producir.py SIN subir (las rondas del crítico nunca salen de la máquina)."""
    r = subprocess.run([PY, str(MOTOR / "producir.py"), str(proy), "--sin-subir"], capture_output=True, text=True)
    qa_f = proy / "renders" / "qa.json"
    qa = json.loads(qa_f.read_text(encoding="utf-8")) if qa_f.exists() else {}
    mp4 = Path(qa["final"]) if r.returncode == 0 and qa.get("final") else None
    return mp4, qa, (r.stdout + r.stderr)[-800:]


def instantanea(proy: Path, dir_: Path, r: int, mp4: Path | None, qa: dict) -> dict:
    """Congela lo que corresponde al vídeo de la ronda r: MP4, index.html, qa.json y storyboard.
    producir.py reescribe todo eso en cada render; sin copia, la ronda r se revisaría (o se
    elegiría) con los archivos de otra."""
    out = {"sb": (proy / "storyboard.json").read_text(encoding="utf-8"), "qa": qa, "mp4": None,
           "html": (proy / "index.html").read_text(encoding="utf-8") if (proy / "index.html").exists() else ""}
    (dir_ / f"storyboard.r{r}.json").write_text(out["sb"], encoding="utf-8")
    (dir_ / f"r{r}.index.html").write_text(out["html"], encoding="utf-8")
    (dir_ / f"r{r}.qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=1), encoding="utf-8")
    if mp4 is not None:
        copia = dir_ / f"r{r}.mp4"
        if mp4.resolve() != copia.resolve():
            shutil.copy2(mp4, copia)
        out["mp4"] = copia
    return out


def bucle(proy: Path, rondas: int = 2, mp4: Path | None = None, rub_ruta: Path | None = None,
          solo_revisar: bool = False) -> dict:
    proy = proy.resolve()
    rub = cargar_rubrica(proy, rub_ruta)
    dir_ = proy / "renders" / "critica"
    dir_.mkdir(parents=True, exist_ok=True)
    sb_f = proy / "storyboard.json"
    original = sb_f.read_text(encoding="utf-8")
    qa: dict = {}
    if mp4 is None:
        mp4, qa, log = render(proy)
    else:
        # MP4 dado: el index.html y el qa.json del proyecto deben ser los de ESE vídeo
        html_f = proy / "index.html"
        if html_f.exists() and html_f.stat().st_mtime > mp4.stat().st_mtime + 1:
            print(f"⚠ index.html es más nuevo que {mp4.name}: el plan puede no ser el de ese vídeo "
                  "(reconstruye con construir.py el storyboard de ese render antes de revisarlo)")
        if (proy / "renders" / "qa.json").exists():   # las puertas que fallaron antes también cuentan
            qa = json.loads((proy / "renders" / "qa.json").read_text(encoding="utf-8"))
    historia: list[dict] = []
    mejor = None
    for r in range(rondas + 1):
        foto = instantanea(proy, dir_, r, mp4, qa)
        sb = json.loads(foto["sb"])
        plan = plan_de_html(foto["html"]) if foto["html"] else {}
        if foto["mp4"] is None:               # una puerta paró el render: sus fallos (con parche) mandan
            fallos = fallos_de_qa({**qa, "_aviso": (sb.get("aviso") or {}).get("lineas") or []}, ventanas(plan))
            res = {"fallos": fallos, "medidas": {}, "puntuacion": None}
        else:
            res = revisar(proy, foto["mp4"], rub, qa, juicio=dir_ / f"r{r}", sb=sb, html=foto["html"])
            preparar_juicio(proy, foto["mp4"], sb, plan, res["fallos"], dir_ / f"r{r}")
        ronda = {"ronda": r, "mp4": str(foto["mp4"]) if foto["mp4"] else None, "puntuacion": res["puntuacion"],
                 "fallos": res["fallos"], "medidas": res["medidas"], "parches": []}
        historia.append(ronda)
        estado = "SIN VÍDEO (puerta)" if res["puntuacion"] is None else f"puntuación {res['puntuacion']} (menos es mejor)"
        print(f"\n== Ronda {r}: {len(res['fallos'])} fallos · {estado}")
        for f in res["fallos"]:
            print("  " + linea(f))
        if res["puntuacion"] is not None:
            if mejor is not None and res["puntuacion"] >= mejor["puntuacion"]:
                print(f"✗ la ronda {r} no mejora a la {mejor['ronda']} ({res['puntuacion']} >= {mejor['puntuacion']}): "
                      "se vuelve a su storyboard")
                break
            mejor = {"ronda": r, "puntuacion": res["puntuacion"], "storyboard": foto["sb"], "mp4": foto["mp4"]}
        if solo_revisar or r == rondas:
            break
        sb2, hechos = aplicar(sb, [f["parche"] for f in res["fallos"] if f.get("parche")])
        if not hechos:
            print("· nada parcheable: lo que queda necesita guion/voz nuevos o decisión humana")
            break
        ronda["parches"] = hechos
        sb_f.write_text(volcar(sb2, original), encoding="utf-8")
        print("→ parches: " + "; ".join(hechos))
        mp4, qa, log = render(proy)
        if mp4 is None:
            print(f"  (render de la ronda {r + 1} parado en una puerta: {log.strip().splitlines()[-1] if log.strip() else '?'})")
    if mejor is not None:                     # el proyecto queda con el storyboard de la mejor ronda medida
        sb_f.write_text(mejor["storyboard"], encoding="utf-8")
    con_juicio = [h["ronda"] for h in historia if (dir_ / f"r{h['ronda']}" / "juicio.json").exists()]
    informe = {"ref": proy.name, "rubrica": rub.get("version"), "rondas": historia,
               "elegida": mejor["ronda"] if mejor else None,
               "mp4_elegido": str(mejor["mp4"]) if mejor and mejor["mp4"] else None,
               "juicio": f"rondas {con_juicio}" if con_juicio else "pendiente (solo medidores)"}
    (dir_ / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    (dir_ / "informe.md").write_text(informe_md(informe), encoding="utf-8")
    print(f"\n✓ informe: {dir_ / 'informe.md'} · ronda elegida {informe['elegida']} · {informe['mp4_elegido']}")
    if mejor is not None and mejor["ronda"] != historia[-1]["ronda"]:
        print("  (index.html y renders/ son de la última ronda probada: reconstruye antes de reutilizarlos)")
    return informe


def informe_md(inf: dict) -> str:
    out = [f"# Crítico — {inf['ref']} (rúbrica {inf['rubrica']}, PROVISIONAL)", "",
           f"Ronda elegida: **{inf['elegida']}** · vídeo: `{inf['mp4_elegido']}` · juicio: {inf['juicio']}", ""]
    for r in inf["rondas"]:
        out += [f"## Ronda {r['ronda']} — {len(r['fallos'])} fallos, puntuación {r['puntuacion']}", ""]
        if r["medidas"]:
            out += ["```", json.dumps(r["medidas"], ensure_ascii=False)[:900], "```", ""]
        out += [f"- {linea(f)}" for f in r["fallos"]] or ["- (sin fallos)"]
        if r["parches"]:
            out += ["", "Parches aplicados → siguiente ronda: " + "; ".join(r["parches"])]
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("proyecto")
    ap.add_argument("--mp4")
    ap.add_argument("--rondas", type=int, default=2)
    ap.add_argument("--rubrica")
    ap.add_argument("--solo-revisar", action="store_true")
    a = ap.parse_args()
    bucle(Path(a.proyecto), min(2, max(0, a.rondas)), Path(a.mp4).resolve() if a.mp4 else None,
          Path(a.rubrica) if a.rubrica else None, a.solo_revisar)


if __name__ == "__main__":
    main()
