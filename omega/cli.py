"""CLI de El Analista.

Comandos:
  python -m omega.cli ingest     # captura RSS -> SQLite (correr a diario)
  python -m omega.cli trends     # reporte de temas en alza/caída
  python -m omega.cli signals    # extrae señales de lo observado (extractores-plugin)
  python -m omega.cli decide     # flujo completo: señales -> hipótesis -> decisión explicable
  python -m omega.cli patterns   # muestra el Creative Knowledge Base (vocabulario de craft)
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


def cmd_signals() -> None:
    """Corre todos los extractores-plugin sobre lo observado y guarda señales genéricas.

    datos (dominio) -> extractores (dominio) -> señales (kernel). El kernel solo ve
    pares (name, value) opacos.
    """
    from .extractors import load_extractors
    from .reasoning import store as kstore, signals as sigstore

    db.init()
    con = kstore.connect(str(config.DB_PATH))
    sigstore.init(con)
    extractors = load_extractors()
    print(f"Extractores cargados: {[e.name for e in extractors]}")

    with db.connect() as dc:
        rows = dc.execute("SELECT * FROM observed_content").fetchall()

    inserted = 0
    for r in rows:
        asset = {"external_id": r["external_id"], "title": r["title"],
                 "summary": r["summary"], "source": r["source"]}
        for ext in extractors:
            try:
                sigs = ext.extract(asset)
            except Exception as exc:  # noqa: BLE001 — un extractor no debe tumbar el pipeline
                print(f"  [{ext.name}] error en un asset: {exc}")
                continue
            for s in sigs:
                inserted += sigstore.add_signal(
                    con, domain="content", asset_ref=r["external_id"], source=r["source"],
                    observed_at=r["published_at"], extractor=ext.name,
                    extractor_version=getattr(ext, "version", None), **s)

    print(f"\n{inserted} señales nuevas | total: {sigstore.count_total(con)}")
    print("Señales por tipo:")
    for row in sigstore.count_by_name(con, "content"):
        print(f"  {row['name']:<16} {row['n']}")
    con.close()


def cmd_decide() -> None:
    """Flujo completo: señales -> hipótesis (dominio) -> decisión explicable (kernel).

    datos reales -> Decision Record con razonamiento reconstruible. Sin API key.
    """
    from .reasoning import (store as kstore, signals as sigstore, hypotheses as hyp,
                            opportunities as opp, decisions, decision_engine)
    from .analyze import hypothesis_engine

    db.init()
    con = kstore.connect(str(config.DB_PATH))
    for mod in (kstore, sigstore, hyp, opp, decisions):
        mod.init(con)

    # idempotencia del demo: descartar candidatas previas para no duplicar
    con.execute("UPDATE hypothesis SET status='discarded' WHERE status='candidate' AND domain='content'")
    con.commit()

    created = hypothesis_engine.generate(con, domain="content")
    print(f"Hypothesis Engine v0: {len(created)} hipótesis candidatas generadas.\n")

    result = decision_engine.decide(
        con, domain="content", weights=config.DECISION_WEIGHTS,
        abstain_threshold=config.ABSTAIN_THRESHOLD,
        horizon_days=config.PREDICTION_HORIZON_DAYS)

    print("=" * 64)
    print(decisions.render_explanation(decisions.explain(con, result["decision_id"])))
    print("=" * 64)
    con.close()


def cmd_patterns() -> None:
    """Muestra el Creative Knowledge Base: el vocabulario controlado de patrones de craft."""
    from .reasoning import store as kstore
    from .creative import patterns

    con = kstore.connect(str(config.DB_PATH))
    patterns.init(con)
    new = patterns.seed(con)
    rows = patterns.list_patterns(con)
    print(f"Creative Knowledge Base — {len(rows)} patrones ({new} nuevos)\n")
    current = None
    for r in rows:
        if r["category"] != current:
            current = r["category"]
            print(f"[{current}]")
        print(f"  {r['tag']:<18} {r['description']}")
    print("\nToda decisión creativa debe justificarse con estos tags (no texto libre).")
    print("Su tasa de éxito real se calibra con resultados publicados.")
    con.close()


def cmd_status() -> None:
    db.init()
    print(f"Base de conocimiento: {db.count_total()} documentos observados")
    print(f"DB: {config.DB_PATH}")


def main(argv: list[str]) -> int:
    cmds = {
        "ingest": cmd_ingest,
        "trends": cmd_trends,
        "signals": cmd_signals,
        "decide": cmd_decide,
        "patterns": cmd_patterns,
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
