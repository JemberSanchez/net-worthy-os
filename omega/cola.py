"""Topic queue prepared in the cloud so /producir starts from a decided topic, not from setup.

    python -m omega.cli cola-preparar   # cloud (nube/cola.yml): data pipeline + decide + media -> cola/
    python -m omega.cli cola            # session: print the queue that estado-bajar brought

Runs in GitHub Actions of the PRIVATE state repo (nothing periodic on the user's PC, 14-nov). It
writes `cola/actual.json` and `cola/medios/<tema>/<k>.hoja.{jpg,txt}` next to `omega.sql`, so the
same `estado-bajar` that syncs the DB brings the queue. Figures here come from HEADLINES: they are
leads with their URL, never verified data (the script still needs the real source in `cifras`).
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from . import config, estado

# analytics-sync before decide: its rescore feeds the beliefs decide reads.
PASOS = ("ingest", "youtube-scan", "signals", "analytics-sync", "meta-sync", "decide")
TEMAS = 3  # winner + 2 runners-up: the session may discard the winner (already made, no data)
CLIPS_POR_TEMA = 4
CIFRA = re.compile(
    r"[$€£]\s?\d[\d,.]*\s?(?:million|billion|trillion|bn\b|[kmbt]\b)?|\d[\d,.]*\s?(?:%|percent|bps|x\b)|\b(?:19|20)\d\d\b",
    re.IGNORECASE,
)


def tema_de(statement: str) -> str:
    """ "Demanda creciente en torno a 'long-term investors'" -> "long-term investors"."""
    m = re.search(r"'(.+)'", statement or "")
    return m.group(1) if m else (statement or "").strip()


def slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")[:40] or "tema"


def fuentes(
    con: sqlite3.Connection, tema: str, dias: int = 7, n: int = 6
) -> list[dict]:
    """Recent observed headlines that mention every word of the topic, newest first, with the
    numbers they quote (leads to verify, not figures to use)."""
    palabras = [w for w in re.findall(r"[a-z0-9']+", tema.lower()) if len(w) > 2]
    if not palabras:
        return []
    desde = int(time.time()) - dias * 86400
    filas = con.execute(
        "SELECT source, title, summary, url, published_at FROM observed_content "
        "WHERE published_at >= ? ORDER BY published_at DESC",
        (desde,),
    ).fetchall()
    out = []
    for fuente, titulo, resumen, url, pub in filas:
        texto = f"{titulo} {resumen or ''}"
        if all(re.search(rf"\b{re.escape(w)}\b", texto.lower()) for w in palabras):
            out.append(
                {
                    "titulo": titulo,
                    "url": url,
                    "fuente": fuente,
                    "fecha": datetime.fromtimestamp(pub or 0, UTC).strftime("%Y-%m-%d"),
                    "cifras": list(
                        dict.fromkeys(m.group(0).strip() for m in CIFRA.finditer(texto))
                    ),
                }
            )
            if len(out) == n:
                break
    return out


def _correr(paso: str) -> dict:
    t = time.time()
    r = subprocess.run(
        [sys.executable, "-m", "omega.cli", paso],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=config.ROOT,
    )
    salida = (r.stdout + r.stderr).strip().splitlines()
    return {
        "paso": paso,
        "ok": r.returncode == 0,
        "s": round(time.time() - t),
        "salida": salida[-25:]
        if paso in ("analytics-sync", "decide") or r.returncode
        else salida[-3:],
    }


def _temas(con: sqlite3.Connection) -> list[dict]:
    from .reasoning import decisions

    con.row_factory = sqlite3.Row
    fila = con.execute(
        "SELECT id FROM decision_record ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not fila:
        return []
    e = decisions.explain(con, fila["id"])
    if e["decision"] == "abstain":
        cands = [
            {"statement": d.get("statement"), "score": d.get("score")}
            for d in e["discarded_hypotheses"]
        ]
    else:
        cands = [{**e["why"], "por_que": e.get("evidence_for", [])}] + [
            {"statement": d.get("statement"), "score": d.get("score")}
            for d in e["discarded_hypotheses"]
        ]
    temas = []
    for c in cands:
        t = tema_de(c["statement"])
        if t and slug(t) not in {x["ref"] for x in temas}:
            temas.append(
                {
                    "tema": t,
                    "ref": slug(t),
                    "score": c.get("score"),
                    "por_que": c.get("por_que", []),
                }
            )
    return temas[:TEMAS]


def _medios(tema: str, carpeta: Path) -> list[dict]:
    """Best licensed clips for the topic, downloaded only to make their contact sheet + OCR (the slow
    part of `broll.py lote`), then the raw file is dropped: the session re-downloads in seconds."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import broll

    cands = []
    for buscar in (broll.buscar_pexels, broll.buscar_commons):
        try:
            cands += buscar(tema)
        except (SystemExit, Exception) as e:  # noqa: BLE001 -- a source down (no key, rate limit) must not sink the queue
            print(f"⚠ {buscar.__name__}: {e}")
    vistos = broll.usados()
    puntuados = sorted(
        ((broll.puntuar(c, tema, vistos=vistos), c) for c in cands),
        key=lambda x: -(x[0] or 0),
    )
    elegidos = [c for s, c in puntuados if s is not None][:CLIPS_POR_TEMA]
    decl = {}
    for i, c in enumerate(elegidos, 1):
        origen = (
            {"commons": c["titulo"]}
            if c["clase"] != "pexels"
            else {"pexels": int(c["titulo"].split(":", 1)[1])}  # titulo = "pexels:<id>"
        )
        decl[f"c{i}"] = origen
    out = []
    if not decl:
        return out
    carpeta.mkdir(parents=True, exist_ok=True)
    try:
        crudos = broll.bajar(decl, carpeta)
        for (k, origen), c in zip(decl.items(), elegidos):
            crudo = crudos[k]
            texto = broll.hoja_clip(crudo)
            out.append(
                {
                    "clave": k,
                    **origen,
                    "titulo": c["titulo"],
                    "licencia": c["licencia"],
                    "fuente": c["fuente"],
                    "segundos": c.get("duracion"),
                    "texto_ocr": texto,
                    "hoja": f"{k}.hoja.jpg",
                }
            )
            crudo.unlink(missing_ok=True)
            broll._origen_ruta(crudo).unlink(missing_ok=True)
    finally:  # a failed sheet must not leave MBs of raw clips for `git add -A cola`
        for f in [*carpeta.glob("*.src"), *carpeta.glob("*.origen")]:
            f.unlink(missing_ok=True)
    (carpeta / "creditos.json").unlink(missing_ok=True)
    return out


def preparar() -> str:
    t0 = time.time()
    clon = estado._clon()
    print(estado.bajar())  # cloud: no local DB, so it restores; PC: never overwrites unsynced work
    pasos = []
    for p in PASOS:
        pasos.append(_correr(p))
        print(f"{'✓' if pasos[-1]['ok'] else '✗'} {p} ({pasos[-1]['s']} s)")
    con = sqlite3.connect(config.DB_PATH)
    temas = _temas(con)
    for t in temas:
        t["fuentes"] = fuentes(con, t["tema"])
    con.close()
    dst = clon / "cola"
    shutil.rmtree(dst / "medios", ignore_errors=True)
    for t in temas:
        tm = time.time()
        try:
            t["medios"] = _medios(t["tema"], dst / "medios" / t["ref"])
        except (SystemExit, Exception) as e:  # noqa: BLE001 -- media are a head start, not a requirement
            t["medios"], t["medios_error"] = [], str(e)[:300]
        t["medios_s"] = round(time.time() - tm)
    dst.mkdir(parents=True, exist_ok=True)
    cola = {
        "preparada": datetime.now(UTC).isoformat(timespec="minutes"),
        "pasos": pasos,
        "temas": temas,
        "segundos": round(time.time() - t0),
    }
    (dst / "actual.json").write_text(
        json.dumps(cola, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    estado._git("add", "-A", "cola", cwd=clon)
    r = estado.subir(
        mensaje=f"cola: {', '.join(t['ref'] for t in temas) or 'sin tema'}"
    )
    if estado._git(
        "status", "--porcelain", "cola", cwd=clon
    ).strip():  # DB unchanged: commit the queue alone
        estado._git(
            "-c",
            "user.name=net-worthy-os",
            "-c",
            "user.email=net-worthy-os@users.noreply.github.com",
            "commit",
            "-q",
            "-m",
            "cola: actualizada",
            cwd=clon,
        )
        estado._git("push", "-q", cwd=clon)
    return f"{r} · cola con {len(temas)} tema(s) en {cola['segundos']} s"


def mostrar(cola: dict, raiz: Path) -> str:
    """The queue as /producir reads it: one block per topic, failures only for the pipeline."""
    lineas = [
        f"Cola preparada {cola['preparada']} UTC ({cola['segundos']} s en la nube)"
    ]
    for p in cola["pasos"]:
        if not p["ok"]:
            lineas.append(f"✗ {p['paso']}: {' | '.join(p['salida'][-3:])}")
    sync = next((p for p in cola["pasos"] if p["paso"] == "analytics-sync"), None)
    if sync and sync["ok"]:
        lineas += ["analytics-sync:"] + [f"  {x}" for x in sync["salida"][-12:]]
    for i, t in enumerate(cola["temas"], 1):
        lineas.append(f"\n{i}. {t['tema']}  (ref {t['ref']}, score {t.get('score')})")
        lineas += [f"   + {x}" for x in t.get("por_que", [])]
        for f in t.get("fuentes", []):
            cif = f" · cifras: {', '.join(f['cifras'])}" if f["cifras"] else ""
            lineas.append(f"   [{f['fecha']}] {f['titulo']}{cif}\n      {f['url']}")
        for m in t.get("medios", []):
            origen = f"pexels {m['pexels']}" if "pexels" in m else m["commons"]
            ocr = " | ".join(m["texto_ocr"])[:120] or "sin texto"
            lineas.append(
                f"   clip {origen} · {m['titulo'][:50]} · OCR: {ocr}\n      hoja: {raiz / t['ref'] / m['hoja']}"
            )
        if t.get("medios_error"):
            lineas.append(f"   ⚠ medios: {t['medios_error']}")
    return "\n".join(lineas)


def _origen(v: dict) -> str:
    """pexels id or Commons file, with or without "File:" (broll.bajar accepts both)."""
    return str(v.get("commons") or v.get("pexels")).removeprefix("File:")


def hojas_previas(decl: dict, cola_medios: Path) -> dict[str, Path]:
    """{clip key of a storyboard: precomputed contact sheet} for clips whose source the cloud already
    sheeted. Matched by source (pexels id / Commons file), never by key name."""
    por_origen = {}
    actual = cola_medios.parent / "actual.json"
    if not actual.exists():
        return {}
    for t in json.loads(actual.read_text(encoding="utf-8"))["temas"]:
        for m in t.get("medios", []):
            por_origen[_origen(m)] = (
                cola_medios / t["ref"] / m["hoja"]
            )
    out = {}
    for k, v in decl.items():
        h = por_origen.get(_origen(v))
        if h and h.exists():
            out[k] = h
    return out
