"""CLI de El Analista.

Comandos:
  python -m omega.cli ingest     # captura RSS -> SQLite (correr a diario)
  python -m omega.cli trends     # reporte de temas en alza/caída
  python -m omega.cli hypotheses # genera un prompt con la evidencia para pegar en Claude
  python -m omega.cli status     # estado de la base de conocimiento
"""
from __future__ import annotations
import sys
import time
from datetime import datetime, timezone

# Forzar UTF-8 en la consola de Windows (evita los caracteres '?').
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from . import config, db
from .analyze import momentum
from .sources import rss


def _fmt(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def cmd_ingest() -> None:
    db.init()
    feeds = config.load_feeds()
    print(f"Ingesta de {len(feeds)} fuentes RSS...")
    items, errors = rss.fetch_all(feeds)
    inserted = db.upsert_items(items)
    print(f"\n{len(items)} items recibidos | {inserted} NUEVOS guardados | "
          f"{len(items) - inserted} duplicados ignorados")
    if errors:
        print(f"{len(errors)} fuentes con error (ignoradas).")
    print(f"Total acumulado en la base: {db.count_total()}")


def cmd_trends() -> None:
    db.init()
    r = momentum.compute()
    print("=" * 64)
    print(f"REPORTE DE MOMENTUM  ({_fmt(r['now'])})")
    print(f"Ventana reciente: {config.RECENT_WINDOW_DAYS}d ({r['recent_docs']} docs) | "
          f"baseline previo: {config.PRIOR_WINDOW_DAYS}d ({r['prior_docs']} docs)")
    print("=" * 64)
    if r["recent_docs"] < 5:
        print("\n[!] Pocos documentos. Corre 'ingest' a diario unos días para que el")
        print("    momentum tenga señal real. El sistema mejora cuanto más observa.")
    print("\n--- TEMAS EN ALZA (momentum = log2 del cambio de presencia) ---")
    if not r["rising"]:
        print("  (sin señal todavía)")
    for x in r["rising"]:
        print(f"  +{x['momentum']:>5}  {x['term']:<22} (docs: {x['prior_df']}->{x['recent_df']})")
        print(f"            ej: {x['examples'][0][:70] if x['examples'] else ''}")
    print("\n--- TEMAS EN CAÍDA ---")
    if not r["declining"]:
        print("  (sin señal todavía)")
    for x in r["declining"]:
        print(f"  {x['momentum']:>6}  {x['term']:<22} (docs: {x['prior_df']}->{x['recent_df']})")


def cmd_hypotheses() -> None:
    """Modo cero-coste: empaqueta la evidencia en un prompt para pegar en Claude.

    Cuando haya presupuesto, este mismo prompt se manda por API automáticamente.
    """
    db.init()
    r = momentum.compute()
    lines = [
        "Eres un estratega de contenido. Abajo hay temas en ALZA y en CAÍDA",
        "detectados observando noticias/foros (frecuencia de aparición, no opinión).",
        "Plataforma objetivo: YouTube (largo + Shorts como embudo).",
        "",
        "Genera EXACTAMENTE 3 propuestas de video. Para cada una indica:",
        "  1) Ángulo/tema y por qué AHORA (cita la evidencia de abajo).",
        "  2) Hook de los primeros 3 segundos.",
        "  3) Qué parte está RESPALDADA por la evidencia vs qué es HIPÓTESIS a validar.",
        "  4) Formato sugerido (largo +8min o Shorts) y por qué.",
        "",
        "=== EVIDENCIA: TEMAS EN ALZA ===",
    ]
    for x in r["rising"][:10]:
        lines.append(f"- '{x['term']}' (presencia {x['prior_df']}->{x['recent_df']}, "
                     f"momentum {x['momentum']}). Ej: {x['examples'][0] if x['examples'] else ''}")
    lines.append("\n=== EVIDENCIA: TEMAS EN CAÍDA (evitar / contrarian) ===")
    for x in r["declining"][:5]:
        lines.append(f"- '{x['term']}' (momentum {x['momentum']})")

    out = config.DATA_DIR / "hypotheses_prompt.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[Guardado en {out}]")
    print(">> Pega este texto en Claude para obtener las 3 propuestas (cero coste de API).")


def cmd_status() -> None:
    db.init()
    print(f"Base de conocimiento: {db.count_total()} documentos observados")
    print(f"DB: {config.DB_PATH}")


def main(argv: list[str]) -> int:
    cmds = {
        "ingest": cmd_ingest,
        "trends": cmd_trends,
        "hypotheses": cmd_hypotheses,
        "status": cmd_status,
    }
    if len(argv) < 1 or argv[0] not in cmds:
        print(__doc__)
        return 1
    cmds[argv[0]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
