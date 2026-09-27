"""Efectos de sonido REALES y sincronizados (grabaciones de Commons: PD / CC0 / CC BY).

    python tools/sfx_libre.py muestras <carpeta>          # cada efecto del catálogo, tratado, para escuchar

Por qué: los whoosh/impact del motor son sintéticos y suenan igual en todos los vídeos. Lo que
separa un Short "de canal grande" es el sonido DIEGÉTICO: si se ve una máquina de escribir, se oye
la máquina; si sale "$8 million", suena la caja registradora. Grabaciones reales, no clip-art sonoro.

Catálogo curado en video-v2/motor/sfx.json (verificado: sin voz hablada, licencia de la lista
cerrada). En el storyboard:
    "clips":    {"typing": {..., "sfx": "maquina"}}          # ambiente mientras el clip está en pantalla
    "imagenes": {"cert1":  {..., "sfx": "obturador"}}        # golpe cuando la foto entra
    "sonidos":  [{"sfx": "caja", "en": "0:dollars"}]         # golpe anclado a una palabra
construir.py baja, trata (golpe: transitorio EXACTO en el instante 0; ambiente: bucle + fundidos
al nivel de ambiente) y registra créditos en assets/sfx/creditos.json ("Sound effects:").
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import musica_libre as ml  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO_PATH = RAIZ / "video-v2" / "motor" / "sfx.json"
NIVEL_AMBIENTE = -20.0   # LUFS del ambiente: textura bajo la voz, nunca protagonista
PICO_GOLPE = -3.0        # dBFS del golpe tratado (el volumen final lo pone data-volume)
BAJO_PICO = 12.0         # el golpe "llega" cuando su energía está a menos de 12 dB de su máximo


def catalogo() -> dict:
    return {k: v for k, v in json.loads(CATALOGO_PATH.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def archivo(nombre: str, tipo: str, dur: float | None = None) -> str:
    """Nombre del tratado: el ambiente lleva su duración (cada tramo de clip es un archivo)."""
    return f"{nombre}.wav" if tipo == "golpe" else f"{nombre}-{round((dur or 0) * 100)}.wav"


def arranque(x, sr: int, bajo: float = BAJO_PICO) -> float:
    """Segundos hasta el TRANSITORIO: primera ventana de 5 ms a menos de `bajo` dB de la ventana
    más fuerte, menos 10 ms de aire. Por energía, no por silencio: un "silenceremove" se dispara con
    el ruido mecánico previo (la caja registradora llegaba 150 ms tarde, medido)."""
    import numpy as np
    w = max(1, int(sr * 0.005))
    n = len(x) // w
    if n == 0:
        return 0.0
    rms = np.sqrt(np.mean(np.asarray(x[:n * w], dtype=np.float64).reshape(n, w) ** 2, axis=1)) + 1e-12
    db = 20 * np.log10(rms)
    i = int(np.argmax(db >= db.max() - bajo))
    return max(0.0, i * w / sr - 0.01)


def _pcm(crudo: Path, desde: float, dur: float, sr: int = 48000):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{desde:.3f}", "-i", str(crudo), "-t", f"{dur:.3f}",
                          "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def golpe(crudo: Path, destino: Path, desde: float, dur: float) -> dict:
    """Un impacto con el transitorio EXACTO en t=0 (es lo que se ancla a la palabra), pico
    normalizado con limitador (sin clip al remuestrear) y cola fundida."""
    import numpy as np
    x = _pcm(crudo, desde, dur)
    t0 = arranque(x, 48000)                       # el golpe perceptible, no el ruido previo
    pico = 20 * np.log10(float(np.abs(x).max()) + 1e-9)
    lim = 10 ** (PICO_GOLPE / 20)
    af = (f"aresample=48000,volume={PICO_GOLPE - pico:.2f}dB,alimiter=limit={lim:.3f}:attack=1:release=40:level=0,"
          f"afade=t=out:st={max(0.05, dur - t0 - 0.3):.2f}:d=0.3")
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{desde + t0:.3f}", "-i", str(crudo), "-t", f"{dur - t0:.3f}",
                    "-af", af, "-ac", "2", "-c:a", "pcm_s16le", str(destino)], check=True)
    return {"duracion": round(ml._duracion(destino), 2), "recorte": round(t0, 3)}


def ambiente(crudo: Path, destino: Path, desde: float, dur: float) -> dict:
    """El sonido del metraje durante `dur` s: bucle si hace falta, fundidos cortos, nivel de ambiente."""
    fundido = min(0.35, dur / 4)
    return ml.cama(crudo, destino, dur, desde, fundido=fundido, nivel=NIVEL_AMBIENTE, entrada=min(0.2, dur / 4))


def asegurar(usos: list[dict], carpeta: Path) -> list[dict]:
    """usos = [{"sfx", "tipo", "dur"?}] -> baja lo que falte (UNA consulta) y trata cada uso.
    Devuelve los usos con `archivo` relleno. Idempotente: lo ya tratado no se toca."""
    cat = catalogo()
    faltan = {u["sfx"] for u in usos if not (carpeta / archivo(u["sfx"], u["tipo"], u.get("dur"))).exists()}
    crudos = ml.bajar({n: cat[n]["commons"] for n in sorted(faltan)}, carpeta) if faltan else {}
    for u in usos:
        u["archivo"] = archivo(u["sfx"], u["tipo"], u.get("dur"))
        dst = carpeta / u["archivo"]
        if dst.exists():
            continue
        c = cat[u["sfx"]]
        if u["tipo"] == "golpe":
            golpe(crudos[u["sfx"]], dst, float(c.get("desde", 0)), float(c.get("dur", 1.5)))
        else:
            ambiente(crudos[u["sfx"]], dst, float(c.get("desde", 0)), float(u["dur"]))
    return usos


def texto_creditos(fichas: list[dict]) -> str:
    return ml.texto_creditos(fichas, titulo="Sound effects")


def main() -> None:
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "muestras":
        dst = Path(a[1])
        usos = [{"sfx": k, "tipo": v["tipo"], "dur": 4.0} for k, v in catalogo().items()]
        for u in asegurar(usos, dst):
            print(f"✓ {u['sfx']:10} {u['tipo']:9} {dst / u['archivo']}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
