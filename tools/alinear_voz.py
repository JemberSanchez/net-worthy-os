"""Alineador de voz: pone TIEMPO REAL a cada palabra del guion.

    python tools/alinear_voz.py read-janitor

Por qué existe
--------------
El calibrador del motor REPARTE las palabras dentro de cada bloque de voz: mide dónde arranca y
acaba cada bloque (eso es exacto) pero dentro estima. Medido sobre el Short #7: 33 de 50 tarjetas
caían a tiempo y 13 llegaban 0,73 s TARDE — el "la voz va más rápida que los subtítulos". Los
tramos donde la voz no hace ninguna pausa no tienen nada que medir, así que la estimación es
irreducible por ese camino.

El .srt de CapCut lo resolvía, pero su plan gratuito solo deja exportarlo 2 veces al mes: inútil
para un canal. Esto hace lo mismo en local, gratis e ILIMITADO.

Cómo
----
1. `faster-whisper` (CTranslate2, sin PyTorch) transcribe el audio con timestamps por palabra.
2. Esa transcripción se alinea con el GUION REAL por programación dinámica (Needleman-Wunsch).
   No nos fiamos de lo que Whisper "entendió": solo de CUÁNDO lo oyó. El guion manda en el texto,
   el audio manda en el tiempo.
3. Sale `data/<voz>.align.json` con cada palabra del guion y su t0/t1 medidos.

El motor lo carga solo: al pulsar "Usar la voz del proyecto" busca el .align.json junto al MP3 y,
si está, usa esos tiempos en vez de estimar. Sin él, todo sigue funcionando como antes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Consolas Windows con codepage cp1252 (frecuente al invocar por -c o desde algunos terminales)
# tiran un UnicodeEncodeError en el primer "✓"/emoji DESPUÉS de que el .align.json ya se escribió
# — el cálculo está bien, solo revienta el print. errors='replace' evita que un símbolo tumbe una
# corrida que por lo demás terminó con éxito.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(errors="replace")

RAIZ = Path(__file__).resolve().parents[1]
MOTOR = RAIZ / "docs" / "guiones" / "short-renderer.html"
MODELO = "base.en"          # 74 MB. `small.en` (244 MB) afina poco más en una voz TTS limpia.


def guion_del_short(clave: str) -> tuple[str, list[str]]:
    """Saca del motor la voz y las frases del Short. La fuente de verdad del guion es el HTML."""
    html = MOTOR.read_text(encoding="utf-8")
    i = html.find(f"'{clave}': {{")
    if i < 0:
        raise SystemExit(f"No encuentro el Short '{clave}' en {MOTOR.name}")
    # hasta el arranque del siguiente Short (o el fin del objeto SHORTS)
    j = html.find("\n  '", i + 10)
    bloque = html[i: j if j > 0 else i + 40000]

    mvoz = re.search(r"voz:\s*'([^']+)'", bloque)
    if not mvoz:
        raise SystemExit(f"El Short '{clave}' no declara `voz`")

    textos = re.findall(r"texto:\s*\"([^\"]+)\"", bloque)
    if not textos:
        textos = re.findall(r"texto:\s*'([^']+)'", bloque)
    if not textos:
        raise SystemExit(f"No encuentro `guion.grupos[].texto` en '{clave}'")
    return mvoz.group(1), textos


def norm(p: str) -> str:
    return re.sub(r"[^a-z0-9']", "", p.lower())


def _tiempo_en_activos(frac: float, activos: list[tuple]) -> float:
    """Tiempo real en la fracción `frac` (0..1) del total ACTIVO de `activos` (ya recortados a un
    hueco) — nunca cae en un silencio entre ellos, salta directo al siguiente tramo."""
    total = sum(b - a for a, b in activos)
    objetivo = frac * total
    acumulado = 0.0
    for a, b in activos:
        dur = b - a
        if objetivo <= acumulado + dur + 1e-9:
            return a + (objetivo - acumulado)
        acumulado += dur
    return activos[-1][1]


def alinear(guion: list[str], oidas: list[dict], hay_voz=None, segmentos=None) -> list[dict]:
    """Needleman-Wunsch entre las palabras del GUION y las que Whisper oyó.

    Whisper se equivoca de palabra a veces, y el TTS puede comerse alguna: por eso no vale
    emparejar por índice. El alineamiento tolera sustituciones y huecos, y a una palabra del guion
    sin pareja se le interpola el tiempo entre sus vecinas emparejadas — que es lo mismo que hacía
    el motor, pero ahora solo para casos sueltos en vez de para tramos enteros.

    `hay_voz` (opcional): callable `t -> bool`, True si hay energía real de voz cerca de `t` en el
    audio. Whisper a veces MIDE una palabra con un tiempo que cae en silencio real (visto en
    Ronald Read: "He" medido en t=24.62 con el audio en silencio hasta t=25.18) — un error de
    medición, no un hueco. Si se pasa `hay_voz`, esas palabras se DEGRADAN a no-medidas ANTES de
    interpolar, así caen en el mismo mecanismo de interpolación de abajo en vez de arrastrar un
    tiempo falso. Sin `hay_voz` (default), el comportamiento es idéntico al de siempre.

    `segmentos` (opcional): lista de tramos [ini, fin] con voz real (ver `segmentos_voz`). Sin
    esto, una palabra sin medir se reparte en línea recta entre sus dos vecinas medidas — y si la
    mayor parte de ese hueco es silencio real (visto en Ronald Read: interpolar "He"/"held" entre
    "says." y "ninety-five" los dejaba ~0.75s ANTES de que la voz volviera a sonar), el resultado
    "dice algo" antes de que se oiga. Con `segmentos`, el reparto salta el silencio y solo usa los
    tramos con voz real dentro del hueco — si no hay ninguno, cae al reparto lineal de siempre.
    """
    n, m = len(guion), len(oidas)
    HUECO = -1.0
    # matriz de puntuación (n+1)x(m+1)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for a in range(1, n + 1):
        D[a][0] = D[a - 1][0] + HUECO
    for b in range(1, m + 1):
        D[0][b] = D[0][b - 1] + HUECO
    gn = [norm(p) for p in guion]
    on = [norm(o["word"]) for o in oidas]
    for a in range(1, n + 1):
        for b in range(1, m + 1):
            igual = 2.0 if gn[a - 1] == on[b - 1] else (
                0.5 if gn[a - 1] and on[b - 1] and (gn[a - 1][:3] == on[b - 1][:3]) else -1.0)
            D[a][b] = max(D[a - 1][b - 1] + igual, D[a - 1][b] + HUECO, D[a][b - 1] + HUECO)

    pares: dict[int, int] = {}
    a, b = n, m
    while a > 0 and b > 0:
        igual = 2.0 if gn[a - 1] == on[b - 1] else (
            0.5 if gn[a - 1] and on[b - 1] and (gn[a - 1][:3] == on[b - 1][:3]) else -1.0)
        if D[a][b] == D[a - 1][b - 1] + igual:
            pares[a - 1] = b - 1
            a, b = a - 1, b - 1
        elif D[a][b] == D[a - 1][b] + HUECO:
            a -= 1
        else:
            b -= 1

    salida: list[dict] = []
    for k, palabra in enumerate(guion):
        if k in pares:
            o = oidas[pares[k]]
            salida.append({"w": palabra, "t0": round(o["start"], 3), "t1": round(o["end"], 3),
                           "medido": True})
        else:
            salida.append({"w": palabra, "t0": None, "t1": None, "medido": False})

    if hay_voz is not None:
        for x in salida:
            if x["medido"] and not hay_voz(x["t0"]):
                x["t0"], x["t1"], x["medido"] = None, None, False

    # interpolar los huecos entre palabras medidas, y extrapolar en los extremos
    medidos = [i for i, x in enumerate(salida) if x["medido"]]
    if not medidos:
        raise SystemExit("Whisper no reconoció NADA que cuadre con el guion. ¿El MP3 es el correcto?")
    for i, x in enumerate(salida):
        if x["medido"]:
            continue
        izq = max((j for j in medidos if j < i), default=None)
        der = min((j for j in medidos if j > i), default=None)
        if izq is None:
            x["t0"], x["t1"] = salida[der]["t0"], salida[der]["t0"]
        elif der is None:
            x["t0"], x["t1"] = salida[izq]["t1"], salida[izq]["t1"]
        else:
            a0, b0 = salida[izq]["t1"], salida[der]["t0"]
            frac0 = (i - izq) / (der - izq)
            frac1 = (i + 1 - izq) / (der - izq)
            # `a > a0` estricto: un tramo de energía que ya EMPEZABA en/antes de a0 es la cola de
            # la palabra anterior apagándose (Whisper no siempre corta al mismo frame que decae la
            # energía), no contenido nuevo — contarlo como "hueco disponible" metía a "He" en la
            # cola de "says." en vez de en el silencio real seguido de "ninety-five" (visto en
            # Ronald Read: "says." mide hasta 24.08 pero su propio tramo de energía sigue hasta
            # 24.25). Solo cuenta un tramo que arranca DESPUÉS de a0: silencio real, luego voz nueva.
            activos = [(a, min(b, b0)) for a, b in (segmentos or []) if a > a0 and a < b0]
            activos = [(a, b) for a, b in activos if b > a]
            if activos:
                x["t0"] = round(_tiempo_en_activos(frac0, activos), 3)
                x["t1"] = round(_tiempo_en_activos(frac1, activos), 3)
            else:
                x["t0"] = round(a0 + (b0 - a0) * frac0, 3)
                x["t1"] = round(a0 + (b0 - a0) * frac1, 3)
    # monótono estricto (una palabra nunca empieza antes que la anterior)
    for i in range(1, len(salida)):
        if salida[i]["t0"] < salida[i - 1]["t0"]:
            salida[i]["t0"] = salida[i - 1]["t0"]
        salida[i - 1]["t1"] = min(salida[i - 1]["t1"], salida[i]["t0"])
    return salida


def envolvente_rms(ruta_audio: Path, ventana_s: float = 0.010) -> tuple:
    """RMS del audio en ventanas fijas — mismo algoritmo que `segmentarVoz` del motor
    (docs/guiones/short-renderer.html), en Python. Decodifica con `av`, igual que ya hace
    tools/medir_loudness.py (sin dependencia nueva). Devuelve (array de RMS, ventana_s)."""
    import av
    import numpy as np

    cont = av.open(str(ruta_audio))
    stream = cont.streams.audio[0]
    sr = stream.rate
    trozos = [f.to_ndarray() for f in cont.decode(stream)]
    cont.close()
    audio = np.concatenate(trozos, axis=1).mean(axis=0).astype(np.float64)  # mono

    win = max(1, int(sr * ventana_s))
    n = len(audio) // win
    recorte = audio[: n * win].reshape(n, win)
    rms = np.sqrt((recorte ** 2).mean(axis=1))
    return rms, ventana_s


def hay_voz_en(t: float, rms, ventana_s: float, thr: float, margen_s: float = 0.15) -> bool:
    """True si hay energía real por encima del umbral cerca de `t` (ventana ± margen_s)."""
    i0 = max(0, int((t - margen_s) / ventana_s))
    i1 = min(len(rms), int((t + margen_s) / ventana_s) + 1)
    return bool(i1 > i0 and rms[i0:i1].max() > thr)


def segmentos_voz(rms, ventana_s: float, thr: float, min_sil_s: float = 0.20) -> list[tuple]:
    """Tramos [ini, fin] donde rms > thr, agrupando huecos menores a min_sil_s — mismo algoritmo
    que segmentarVoz() en el motor JS (docs/guiones/short-renderer.html), aquí para decidir DÓNDE
    puede caer una palabra interpolada (ver `alinear`, parámetro `segmentos`)."""
    min_sil = max(1, round(min_sil_s / ventana_s))
    segs: list[tuple] = []
    dentro = False
    ini = 0
    sil = 0
    for i, v in enumerate(rms):
        if v > thr:
            if not dentro:
                dentro = True
                ini = i
            sil = 0
        elif dentro:
            sil += 1
            if sil >= min_sil:
                dentro = False
                segs.append((ini * ventana_s, (i - sil) * ventana_s))
    if dentro:
        segs.append((ini * ventana_s, len(rms) * ventana_s))
    return segs


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    clave = sys.argv[1]
    generar_alineamiento(clave)


def generar_alineamiento(clave: str, ruta_audio: Path | None = None) -> Path:
    """El cuerpo real, EXTRAÍDO de main() para que `generar_voz.py` pueda encadenar
    guion -> voz -> alineamiento en un solo comando sin duplicar esta lógica.
    `ruta_audio` opcional: para audio recién generado que aún no tiene el nombre en el HTML resuelto
    en disco (no debería hacer falta hoy, pero evita tener que escribir el audio antes de saber su
    ruta final). Devuelve la ruta del .align.json escrito."""
    voz, frases = guion_del_short(clave)
    audio = ruta_audio or (RAIZ / "data" / voz)
    if not audio.exists():
        raise SystemExit(f"No existe {audio}")

    from faster_whisper import WhisperModel

    print(f"Short   : {clave}")
    print(f"Audio   : {audio.name}")
    print(f"Modelo  : {MODELO} (se descarga la 1ª vez, ~74 MB)\n")

    modelo = WhisperModel(MODELO, device="cpu", compute_type="int8")
    segmentos, info = modelo.transcribe(str(audio), word_timestamps=True, language="en",
                                        vad_filter=False)
    oidas: list[dict] = []
    for seg in segmentos:
        for w in (seg.words or []):
            oidas.append({"word": w.word.strip(), "start": w.start, "end": w.end})
    print(f"Whisper oyó {len(oidas)} palabras en {info.duration:.2f}s de audio.")

    guion = [p for f in frases for p in f.split()]
    print(f"El guion tiene {len(guion)}.\n")

    # Whisper a veces MIDE una palabra con un tiempo que cae en silencio real (no un hueco: un
    # error de medición). Antes de confiar en cada tiempo "medido", se valida contra la energía
    # real del audio (mismo algoritmo que `segmentarVoz` del motor) — lo que no aguanta esa
    # validación cae a interpolación en vez de arrastrar un tiempo falso.
    rms, ventana_s = envolvente_rms(audio)
    pico = float(rms.max())
    piso = float(sorted(rms)[len(rms) // 10]) if len(rms) >= 10 else 0.0
    thr = max(pico * 0.05, piso * 2.5)
    descartadas: list[str] = []

    def hay_voz(t: float) -> bool:
        ok = hay_voz_en(t, rms, ventana_s, thr)
        if not ok:
            descartadas.append(f"t={t:.2f}s")
        return ok

    # Mismos datos de energía, reusados: si toca interpolar (palabra sin medir, o descartada
    # arriba), que reparta SOLO dentro de tramos con voz real, saltándose el silencio, en vez de
    # repartir a ciegas por todo el hueco entre las dos palabras medidas vecinas.
    tramos_voz = segmentos_voz(rms, ventana_s, thr)
    palabras = alinear(guion, oidas, hay_voz=hay_voz, segmentos=tramos_voz)
    medidas = sum(1 for p in palabras if p["medido"])
    pct = 100 * medidas / len(palabras)
    if descartadas:
        print(f"  ⚠ {len(descartadas)} palabra(s) medida(s) por Whisper pero sobre silencio real "
              f"({', '.join(descartadas)}) -> descartadas, interpoladas en su lugar.")
        if len(descartadas) / len(palabras) > 0.10:
            print("  ⚠ Más del 10% descartado: revisa el audio, puede haber un problema mayor "
                  "que palabras sueltas.")

    destino = audio.with_suffix(".align.json")
    destino.write_text(json.dumps(
        {"voz": voz, "short": clave, "modelo": MODELO,
         "palabras": [{"w": p["w"], "t0": p["t0"], "t1": p["t1"], "m": p["medido"]} for p in palabras]},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"✓ {destino.name}")
    print(f"  {medidas}/{len(palabras)} palabras con tiempo MEDIDO ({pct:.0f}%); el resto interpolado.")
    if pct < 80:
        print("  ⚠ Menos del 80% emparejado: revisa que el audio corresponda a ESTE guion.")
    return destino


if __name__ == "__main__":
    main()
