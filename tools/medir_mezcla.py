"""Mide si la MÚSICA (y los efectos) TAPAN LA VOZ en el MP4 final, con el segundo exacto.

    python tools/medir_mezcla.py <video.mp4> --voz video-v2/<ref>/assets/voice.mp3 \
        [--words video-v2/<ref>/assets/words.json] [--json]

Por qué existe
---------------
`medir_loudness.py` mide el volumen TOTAL (-14 LUFS) pero no dice si la voz se entiende: una
mezcla puede dar -14 LUFS exactos con la música encima de la voz. El ducking (carve.mjs) baja la
música bajo la voz, pero nadie medía el resultado sobre el archivo.

Cómo mide (sustracción, no "separación" con IA)
------------------------------------------------
El motor mete la voz limpia (`assets/voice.mp3`) con volumen 1 y después aplica una ganancia
LINEAL (loudnorm en 2 pasadas, `linear=true`). Así que la mezcla = g·voz(t - retardo) + resto.
1. Retardo: correlación cruzada (FFT) entre voz y mezcla (absorbe el desfase MP3/AAC).
2. Ganancia g: mínimos cuadrados sobre toda la pista (la música no está correlada con la voz).
3. resto = mezcla - g·voz  -> música + efectos tal como suenan en el archivo final.
4. Por ventana de 0,5 s con voz (según words.json): energía en la banda de la voz (300-3400 Hz)
   de g·voz contra la del resto -> relación voz/fondo en dB.

Validación del instrumento (tests/test_medir_mezcla.py): mezclas sintéticas con la relación
conocida (voz tipo habla + "música" de acordes) a 20, 10 y 0 dB -> el medidor las recupera con
error < 1 dB, también con retardo y ganancia desconocidos. El suelo lo pone el códec AAC (~30 dB):
por encima de eso el número satura (no importa: el problema está por debajo de ~10 dB).

Umbral (PROVISIONAL, docs/RUBRICA.md): voz >= 10 dB sobre el fondo en su banda. Referencia: las
guías de diálogo de TV piden que el fondo quede claramente por debajo del diálogo; el número se
calibra con las notas del usuario, no se toma como ley.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SR = 16000
BANDA = (300.0, 3400.0)
VENTANA_S = 0.5
UMBRAL_DB = 10.0
TECHO_DB = 30.0         # por encima, el número lo limita el códec, no la mezcla


def decodificar(ruta: Path, sr: int = SR) -> np.ndarray:
    """Audio mono float64 a `sr` Hz (con `av`, como medir_loudness)."""
    import av
    cont = av.open(str(ruta))
    st = cont.streams.audio[0]
    rs = av.AudioResampler(format="flt", layout="mono", rate=sr)
    trozos = []
    for fr in cont.decode(st):
        for o in rs.resample(fr):
            trozos.append(o.to_ndarray().reshape(-1))
    for o in rs.resample(None):
        trozos.append(o.to_ndarray().reshape(-1))
    cont.close()
    return np.concatenate(trozos).astype(np.float64) if trozos else np.zeros(0)


def retardo(mezcla: np.ndarray, voz: np.ndarray, max_s: float = 0.5, sr: int = SR) -> int:
    """Muestras que la voz va retrasada dentro de la mezcla (puede ser negativo). Correlación FFT."""
    n = min(len(mezcla), len(voz))
    a, b = mezcla[:n], voz[:n]
    N = 1 << (2 * n - 1).bit_length()
    c = np.fft.irfft(np.fft.rfft(a, N) * np.conj(np.fft.rfft(b, N)), N)
    m = int(max_s * sr)
    cand = np.concatenate([c[-m:], c[:m + 1]])        # lags -m..m
    return int(np.argmax(cand)) - m


def alinear(voz: np.ndarray, lag: int, n: int) -> np.ndarray:
    out = np.zeros(n)
    if lag >= 0:
        k = min(n - lag, len(voz))
        if k > 0:
            out[lag:lag + k] = voz[:k]
    else:
        k = min(n, len(voz) + lag)
        if k > 0:
            out[:k] = voz[-lag:-lag + k]
    return out


def energia_banda(x: np.ndarray, sr: int = SR, banda=BANDA) -> float:
    if len(x) == 0:
        return 0.0
    X = np.fft.rfft(x * np.hanning(len(x)))
    f = np.fft.rfftfreq(len(x), 1 / sr)
    sel = (f >= banda[0]) & (f <= banda[1])
    return float(np.sum(np.abs(X[sel]) ** 2))


def medir(mezcla: np.ndarray, voz: np.ndarray, tramos_voz: list[tuple[float, float]] | None = None,
          sr: int = SR, umbral_db: float = UMBRAL_DB) -> dict:
    """Función pura sobre señales mono a `sr`. `tramos_voz` = [(t0, t1)] con habla (si None, se
    usan las ventanas donde la voz alineada tiene energía). Devuelve relación voz/fondo por ventana."""
    lag = retardo(mezcla, voz, sr=sr)
    v = alinear(voz, lag, len(mezcla))
    g = float(np.dot(mezcla, v) / max(np.dot(v, v), 1e-12))
    resto = mezcla - g * v
    w = int(VENTANA_S * sr)
    ventanas = []
    ref = max(energia_banda(g * v[i:i + w], sr) for i in range(0, max(1, len(v) - w), w)) if len(v) > w else 1.0
    for i in range(0, len(mezcla) - w + 1, w):
        t0 = i / sr
        if tramos_voz is not None:
            # al menos media ventana con voz: una ventana con la cola de una palabra y un efecto
            # entero no dice nada de inteligibilidad (medido en el #7: "dollars." acaba a 2,56 s y
            # la caja registradora llena el resto -> -29,9 dB de un instante sin voz)
            if sum(max(0.0, min(b, t0 + VENTANA_S) - max(a, t0)) for a, b in tramos_voz) < VENTANA_S / 2:
                continue
        ev = energia_banda(g * v[i:i + w], sr)
        if tramos_voz is None and ev < ref * 1e-3:     # ventana sin voz (-30 dB del máximo)
            continue
        er = energia_banda(resto[i:i + w], sr)
        db = TECHO_DB if er <= 0 else min(TECHO_DB, 10 * np.log10(max(ev, 1e-20) / er))
        ventanas.append({"t": round(t0, 2), "db": round(float(db), 1)})
    dbs = np.array([x["db"] for x in ventanas]) if ventanas else np.array([TECHO_DB])
    malas = [x for x in ventanas if x["db"] < umbral_db]
    return {"retardo_ms": round(1000 * lag / sr, 1), "ganancia": round(g, 3),
            "mediana_db": round(float(np.median(dbs)), 1), "p10_db": round(float(np.percentile(dbs, 10)), 1),
            "min_db": round(float(dbs.min()), 1), "n_ventanas": len(ventanas),
            "pct_tapada": round(100 * len(malas) / max(1, len(ventanas)), 1),
            "tapada": _tramos(malas), "umbral_db": umbral_db, "ventanas": ventanas}


def _tramos(malas: list[dict]) -> list[dict]:
    """Ventanas malas consecutivas -> tramos {t, t_fin, min_db}."""
    out: list[dict] = []
    for x in malas:
        if out and abs(x["t"] - out[-1]["t_fin"]) < VENTANA_S + 1e-6:
            out[-1]["t_fin"] = x["t"]
            out[-1]["min_db"] = min(out[-1]["min_db"], x["db"])
        else:
            out.append({"t": x["t"], "t_fin": x["t"], "min_db": x["db"]})
    for o in out:
        o["t_fin"] = round(o["t_fin"] + VENTANA_S, 2)
    return out


def tramos_de_words(words: list[dict], margen: float = 0.05) -> list[tuple[float, float]]:
    return [(w["start"] - margen, w["end"] + margen) for w in words if w["end"] > w["start"]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mp4")
    ap.add_argument("--voz", required=True)
    ap.add_argument("--words")
    ap.add_argument("--umbral", type=float, default=UMBRAL_DB)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    tr = tramos_de_words(json.loads(Path(a.words).read_text(encoding="utf-8"))) if a.words else None
    r = medir(decodificar(Path(a.mp4)), decodificar(Path(a.voz)), tr, umbral_db=a.umbral)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    print(f"Voz sobre el fondo (banda 300-3400 Hz): mediana {r['mediana_db']} dB · p10 {r['p10_db']} dB · "
          f"mín {r['min_db']} dB  (objetivo >= {r['umbral_db']} dB)")
    print(f"Tiempo con la voz tapada: {r['pct_tapada']} % de {r['n_ventanas']} ventanas" +
          "".join(f"\n  t={x['t']}-{x['t_fin']}s ({x['min_db']} dB)" for x in r["tapada"][:5]))
    print(f"(retardo {r['retardo_ms']} ms, ganancia de la voz en la mezcla {r['ganancia']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
