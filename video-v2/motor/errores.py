"""Error ratchet: every gate failure class happens ONCE. Registry: errores.json (versioned).

Each entry: id, patron (regex searched in the failing rule), estado, ejemplo, desde (first seen);
a closed one adds donde (module.function of the fix), test (its test) and cerrado (date).
  abierto     seen, no fix yet: the next /producir must fix its cause before the video
  imposible   the compiler can no longer produce it
  prevenido   a static check before the voice fixes it by itself
  autoarreglo a mechanical patch in autoarreglo.py fixes it
A rule matching no entry is a NEW error: it is added as `abierto` and producir stops.
A rule matching a closed entry is a REGRESSION: tests/test_registro_errores.py fails on it.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

REGISTRO = Path(__file__).with_name("errores.json")
ESTADOS = ("abierto", "imposible", "prevenido", "autoarreglo")
_CITA = r"['\"“«].*?['\"”»]"
_NUM = r"\d+(?:[.,]\d+)?"


def cargar(ruta: Path = REGISTRO) -> list[dict]:
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else []


def patron_de(regla: str) -> str:
    """Regex for a rule's class: quoted values and numbers vary, the rest is literal. The text
    after the first ' (' (file lists, examples) is dropped: it changes from video to video."""
    sin_puerta = re.sub(
        r"^[a-z_]+: ", "", regla
    )  # --auto prefixes some with the gate name
    sin_citas = re.sub(
        _CITA, "\0", sin_puerta
    )  # before cutting: a cut must not split a quote
    base = re.split(r"\s\(", sin_citas, maxsplit=1)[0][:90]
    partes = re.split(r"(\0|\d+(?:[.,]\d+)?)", base)
    return "".join(
        re.escape(x) if i % 2 == 0 else (".+?" if x == "\0" else _NUM)
        for i, x in enumerate(partes)
    )


def reglas_de(linea: dict) -> list[str]:
    """What a logged run really failed on: with --auto, what autoarreglo could not fix;
    otherwise every failing rule."""
    if linea.get("pendientes"):
        return list(linea["pendientes"])
    return [r for rs in (linea.get("reglas") or {}).values() for r in rs]


def entrada_de(regla: str, registro: list[dict]) -> dict | None:
    return next((e for e in registro if re.search(e["patron"], regla)), None)


def revisar(reglas: list[str], ruta: Path = REGISTRO, hoy: str | None = None) -> dict:
    """Classify a failed run's rules; register the new ones as `abierto`. Returns
    {"nuevos": [...], "abiertos": [...], "regresiones": [...]} with (id, regla) pairs."""
    registro = cargar(ruta)
    out = {"nuevos": [], "abiertos": [], "regresiones": []}
    for r in dict.fromkeys(reglas):
        e = entrada_de(r, registro)
        if e is None:
            e = {
                "id": f"E{len(registro) + 1}",
                "patron": patron_de(r),
                "estado": "abierto",
                "ejemplo": r[:200],
                "desde": hoy or date.today().isoformat(),
            }
            registro.append(e)
            out["nuevos"].append((e["id"], r))
        elif e["estado"] == "abierto":
            out["abiertos"].append((e["id"], r))
        else:
            out["regresiones"].append((e["id"], r))
    if out["nuevos"]:
        ruta.write_text(
            json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return out


def avisar(out: dict) -> None:
    for i, r in out["nuevos"]:
        print(f"🆕 ERROR NUEVO {i}: {r[:160]}")
    for i, r in out["regresiones"]:
        print(f"🔁 REGRESIÓN {i} (estaba arreglado): {r[:160]}")
    for i, r in out["abiertos"]:
        print(f"⏳ abierto {i}: {r[:160]}")
    if out["nuevos"] or out["regresiones"]:
        print(
            "→ Arregla la CAUSA antes de seguir con el vídeo (imposible > prevenido > autoarreglo),"
            " con un test que lo reproduzca, y cierra la entrada en video-v2/motor/errores.json."
        )
