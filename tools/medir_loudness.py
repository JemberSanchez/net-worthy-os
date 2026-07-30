"""Mide el volumen del MP4 exportado contra el estándar real de YouTube/Facebook.

    python tools/medir_loudness.py data/net-worthy-read-janitor.mp4

Por qué existe
---------------
El motor mezcla voz+música+sfx con heurísticas propias (auto-gain a -20dB bajo la voz) que nunca se
compararon contra nada externo. YouTube y Facebook normalizan TODO lo que subes a **-14 LUFS
integrado** con el pico verdadero por debajo de **-1 dBTP** — si el video llega más flojo, la
plataforma lo sube (a veces con artefactos); si llega más fuerte, lo baja. En ningún caso suena como
se mezcló.

Mide con `pyloudnorm` (implementación del estándar ITU-R BS.1770-4, el mismo algoritmo que usan las
plataformas) sobre el AUDIO REAL del archivo exportado — no sobre el modelo de mezcla del motor, así
que también pillaría un fallo introducido en el muxer/encoder que el motor nunca vería.

Qué NO hace
-----------
No toca la mezcla. El motor sigue congelado (docs/POLITICA.md): esto es una regla, no un arreglo.
Si el gap es grande y consistente entre videos, ESO sería la limitación concreta que justifica tocar
`construirMezcla`/`mezclarMusica` — no antes.
"""
from __future__ import annotations

import sys

for _s in (sys.stdout, sys.stderr):     # cp1252 no tiene "⚠"/"✓"; no tumbar el cálculo por eso
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(errors="replace")

OBJETIVO_LUFS = -14.0
OBJETIVO_PICO_DBTP = -1.0


def medir(ruta: str) -> None:
    import av
    import numpy as np
    import pyloudnorm as pyln

    cont = av.open(ruta)
    stream = cont.streams.audio[0]
    if stream is None:
        raise SystemExit(f"{ruta} no tiene pista de audio")
    sr = stream.rate
    trozos = [f.to_ndarray() for f in cont.decode(stream)]
    cont.close()
    if not trozos:
        raise SystemExit("no se decodificó ningún frame de audio")

    audio = np.concatenate(trozos, axis=1).T.astype(np.float64)  # (muestras, canales), ya en [-1,1]

    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(audio)
    pico_dbtp = 20 * np.log10(max(1e-9, float(np.abs(audio).max())))

    print(f"Archivo : {ruta}")
    print(f"Canales : {audio.shape[1]}  ·  SR: {sr}Hz  ·  {audio.shape[0]/sr:.2f}s\n")
    print(f"Loudness integrado : {lufs:6.2f} LUFS   (objetivo {OBJETIVO_LUFS:.0f}, YouTube/FB)")
    print(f"Pico real           : {pico_dbtp:6.2f} dBTP  (objetivo < {OBJETIVO_PICO_DBTP:.0f})")

    gap = lufs - OBJETIVO_LUFS
    if abs(gap) <= 1.0:
        print(f"\n✓ Dentro de ±1 dB del objetivo ({gap:+.2f} dB). La plataforma casi no toca la mezcla.")
    else:
        direccion = "más flojo" if gap < 0 else "más fuerte"
        print(f"\n⚠ {abs(gap):.1f} dB {direccion} que el objetivo. La plataforma lo va a re-normalizar.")
    if pico_dbtp > OBJETIVO_PICO_DBTP:
        print(f"⚠ El pico real supera {OBJETIVO_PICO_DBTP:.0f} dBTP: riesgo de distorsión al recodificar.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    medir(sys.argv[1])
