"""What this Claude Code session cost, measured from its transcript (PLAN 4.2: cost per video).

    python tools/costo_sesion.py video-v2/<ref>     # writes <ref>/renders/costo.json and prints it

Reads the newest transcript of this project (the running session). A transcript repeats the usage of
one API message on every content block, so messages are counted once by id: counting lines doubled
the turns and the cache reads (11-nov).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def medir(transcript: Path) -> dict:
    usos, t0, t1 = {}, None, None
    for linea in transcript.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            o = json.loads(linea)
        except ValueError:
            continue
        if o.get("timestamp"):
            t0, t1 = t0 or o["timestamp"], o["timestamp"]
        m = o.get("message")
        if isinstance(m, dict) and m.get("usage") and m.get("id"):
            usos[m["id"]] = m["usage"]

    def suma(k: str) -> int:
        return sum(u.get(k) or 0 for u in usos.values())

    def seg(t: str) -> float:
        return datetime.fromisoformat(t).timestamp()

    return {
        "turnos": len(usos),
        "cache_leida": suma("cache_read_input_tokens"),
        "cache_escrita": suma("cache_creation_input_tokens"),
        "salida": suma("output_tokens"),
        "minutos": round((seg(t1) - seg(t0)) / 60) if t0 and t1 else None,
    }


# Step of /producir a tool call belongs to: first rule whose pattern appears in the call wins.
PASOS = (
    (
        "entregar",
        r"estado-subir|produccion-guardar|omega\.cli publicar|entregar\.py|SendUserFile|costo_sesion|record-|omega\.cli (comentar|programar)",
    ),
    (
        "setup",
        r"setup_nube|estado-bajar|analytics-sync|meta-sync|omega\.cli (ingest|youtube-scan|signals|decide)|/daily|cola\.py|\bcola\b",
    ),
    ("guion", r"guionista|guiones\.(json|md)"),
    ("voz", r"voz\.py|generar_voz|alinear_voz"),
    (
        "medios",
        r"imagenes_libres|broll\.py|ocr_doc|duotono|musica_libre|sfx_libre|\.hoja\.|assets[/\\]",
    ),
    (
        "producir",
        r"producir\.py|critico\.py|construir\.py|juicio|check_motor|lint_motor|renders[/\\]|cadena\.py",
    ),
    ("storyboard", r"storyboard\.json"),
)


def paso_de(bloque: dict) -> str:
    texto = (
        bloque.get("name", "")
        + " "
        + json.dumps(bloque.get("input", {}), ensure_ascii=False)
    )
    return next((p for p, rx in PASOS if re.search(rx, texto)), "sondeo")


def pasos(transcript: Path) -> dict:
    """Minutes per step, split into model time (writing the turn) and tool time (waiting for a
    foreground tool). Each gap between transcript lines is charged to the line that ends it:
    an assistant line = model time of its message's step; a tool_result = tool time of its call.
    User prompts and background notifications end idle gaps (user or machine): not charged."""
    lineas = []
    for linea in transcript.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            o = json.loads(linea)
        except ValueError:
            continue
        if o.get("timestamp") and isinstance(o.get("message"), dict):
            lineas.append(o)
    paso_msg, paso_uso, ultimo = {}, {}, "setup"
    for o in lineas:
        m = o["message"]
        if o.get("type") == "assistant" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if b.get("type") == "tool_use":
                    paso_uso[b["id"]] = paso_de(b)
                    paso_msg.setdefault(m.get("id"), paso_uso[b["id"]])
    out: dict[str, dict[str, float]] = {}
    previo = None
    for o in lineas:
        t = datetime.fromisoformat(o["timestamp"]).timestamp()
        dt, m = (t - previo) if previo else 0.0, o["message"]
        previo = t
        c = m.get("content")
        if o.get("type") == "assistant":
            ultimo = paso_msg.get(m.get("id"), ultimo)
            out.setdefault(ultimo, {"modelo": 0.0, "herramienta": 0.0})["modelo"] += dt
        elif isinstance(c, list) and any(
            b.get("type") == "tool_result" for b in c if isinstance(b, dict)
        ):
            uso = next(b["tool_use_id"] for b in c if isinstance(b, dict) and b.get("type") == "tool_result")
            p = paso_uso.get(uso, ultimo)
            out.setdefault(p, {"modelo": 0.0, "herramienta": 0.0})["herramienta"] += dt
    return {
        p: {k: round(v / 60, 1) for k, v in d.items()} for p, d in sorted(out.items())
    }


def transcript_actual() -> Path:
    carpeta = (
        Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(RAIZ))
    )
    return max(carpeta.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    try:
        tr = (
            Path(sys.argv[sys.argv.index("--transcript") + 1])
            if "--transcript" in sys.argv
            else transcript_actual()
        )
    except ValueError:  # max() of no transcripts: cloud run or another machine
        raise SystemExit(
            "sin transcript de Claude Code para este proyecto: coste no medido"
        ) from None
    costo = {**medir(tr), "pasos": pasos(tr)}
    salida = Path(sys.argv[1]) / "renders" / "costo.json"
    if salida.parent.exists():
        salida.write_text(json.dumps(costo, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(costo))
