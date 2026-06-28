"""CLI de El Analista.

Comandos:
  python -m omega.cli ingest     # captura RSS -> SQLite (correr a diario)
  python -m omega.cli trends     # reporte de temas en alza/caída
  python -m omega.cli signals    # extrae señales de lo observado (extractores-plugin)
  python -m omega.cli decide     # flujo completo: señales -> hipótesis -> decisión explicable
  python -m omega.cli patterns   # muestra el Creative Knowledge Base (vocabulario de craft)
  python -m omega.cli combine <sujeto>   # divergencia: k encuadres distintos de un sujeto
  python -m omega.cli think <sujeto>     # el director PIENSA un sujeto (usa LLM si hay key)
  python -m omega.cli record-think [file]          # registra el resultado que te dio tu Claude
  python -m omega.cli record-outcome <ref> <0..1>  # tras publicar: registra el resultado medido
  python -m omega.cli learnings                    # qué patrones funcionan (calibración acumulada)
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


def cmd_think() -> None:
    """Pone al director creativo a PENSAR un sujeto. Con ANTHROPIC_API_KEY usa el LLM real;
    sin key, corre en modo $0 (export-prompt) y muestra qué pasos necesitarían un modelo."""
    from .reasoning import store as kstore
    from .creative import thinking
    from .llm import get_llm, make_think_fn

    subject = " ".join(sys.argv[2:]).strip() or "tiburones"
    llm = get_llm()
    print(f"LLM: {llm.name}\nSujeto: '{subject}'\n")

    con = kstore.connect(str(config.DB_PATH))
    session = thinking.ThinkingSession(con, think_fn=make_think_fn(llm, tier="smart"))
    r = session.run(subject)

    if r["executed_think_steps"] == 0:
        # Modo $0: el sistema no piensa solo, pero TÚ tienes Claude. Exporta el paquete a pegar.
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        pack_path = config.DATA_DIR / "think_pack.txt"
        lines = [f"# Paquete de pensamiento — sujeto: '{subject}'",
                 "# Pega esto en tu Claude (claude.ai o Claude Code) y responde cada paso en orden.",
                 "# Eso ES el pensamiento del sistema, hecho con tu cuenta, a coste $0.", ""]
        for i, p in enumerate(session.pending, 1):
            lines.append(f"--- PASO {i} ---\n{p}\n")
        pack_path.write_text("\n".join(lines), encoding="utf-8")
        # plantilla para devolver el resultado al sistema (puente de vuelta)
        import json
        tpl = {"subject": subject, "production_ref": "<id-unico-del-video>",
               "decision_type": "angle",
               "angle": "<pega aquí el ángulo elegido que te dio Claude>",
               "pattern_tags": ["curiosity_gap", "novel_combination", "pattern_break"]}
        (config.DATA_DIR / "think_result.template.json").write_text(
            json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Modo $0 (sin API key): el sistema NO puede pensar solo — pero tu Claude sí.")
        print(f"Paquete listo para pegar guardado en: {pack_path}\n")
        for i, p in enumerate(session.pending, 1):
            print(f"[PASO {i}] {p}\n")
        print("Cuando Claude responda: copia data/think_result.template.json a "
              "data/think_result.json, rellénalo y corre 'record-think'.")
    else:
        print(f"Pensó en {r['executed_think_steps']} pasos. Mejor ángulo:\n  {r['best']}\n")
        print("Traza:")
        for t in r["trace"]:
            if t.get("status") == "done" and t["kind"] != "diverge" and t.get("output"):
                print(f"  [{t['kind']}] {t['output'][:200]}")
    con.close()


def cmd_combine() -> None:
    """Operador de divergencia: k encuadres distintos de un sujeto, rankeados por novedad."""
    from .reasoning import store as kstore
    from .creative import combinator

    subject = " ".join(sys.argv[2:]).strip() or "historia romana"
    con = kstore.connect(str(config.DB_PATH))
    combinator.init(con)
    combos = combinator.generate(con, subject, k=6)
    print(f"Divergencia sobre: '{subject}'  (k encuadres distintos, no el obvio)\n")
    for c in combos:
        flag = "  (encuadre por defecto)" if c["is_default"] else ""
        print(f"  novedad {c['novelty']:<5}  {c['statement']}{flag}")
    print("\nLa novedad decae con el uso: el sistema busca lo que nunca se combinó.")
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


def cmd_record_think() -> None:
    """Puente de vuelta: registra en el sistema el resultado que pensó tu Claude (a mano, $0).

    Lee data/think_result.json (o el archivo pasado como argumento) y guarda la decisión creativa
    justificada con tags del CKB. Así el sistema acumula conocimiento aunque el pensar sea manual.
    """
    import json
    from pathlib import Path
    from .reasoning import store as kstore
    from .creative import patterns, decisions

    path = Path(sys.argv[2]) if len(sys.argv) > 2 else (config.DATA_DIR / "think_result.json")
    if not path.exists():
        print(f"No existe {path}. Corre 'think <sujeto>', copia la plantilla "
              "data/think_result.template.json a data/think_result.json y rellénala.")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    angle = (data.get("angle") or "").strip()
    tags = data.get("pattern_tags") or []
    ref = data.get("production_ref") or f"manual-{int(time.time())}"
    if not angle or "<" in angle or not tags:
        print("Faltan 'angle' o 'pattern_tags' (o quedó el placeholder). Rellena el JSON primero.")
        return

    con = kstore.connect(str(config.DB_PATH))
    for mod in (patterns, decisions):
        mod.init(con)
    patterns.seed(con)
    try:
        decisions.record_decision(con, production_ref=ref, decision_type=data.get("decision_type", "angle"),
                                  choice=angle, pattern_tags=tags)
    except ValueError as exc:
        print(f"Rechazado: {exc}")
        print("Tags válidos del CKB:", ", ".join(sorted(patterns.vocabulary(con))))
        con.close()
        return
    print(f"Registrado. produccion='{ref}', tags={tags}")
    print(f"  Ángulo: {angle[:120]}")
    print(f"\nCuando publiques el video, mide su rendimiento y corre:")
    print(f"  python -m omega.cli record-outcome {ref} <0..1>")
    con.close()


def cmd_record_outcome() -> None:
    """Tras publicar: registra el resultado MEDIDO (0..1) de una producción. Alimenta la calibración."""
    from .reasoning import store as kstore
    from .creative import patterns, decisions

    if len(sys.argv) < 4:
        print("Uso: record-outcome <production_ref> <success 0..1>")
        return
    ref, success = sys.argv[2], float(sys.argv[3])
    con = kstore.connect(str(config.DB_PATH))
    for mod in (patterns, decisions):
        mod.init(con)
    try:
        decisions.record_outcome(con, ref, success)
    except ValueError as exc:
        print(f"Rechazado: {exc}")
        con.close()
        return
    print(f"Resultado registrado: {ref} -> {success}. Corre 'learnings' para ver la calibración.")
    con.close()


def cmd_learnings() -> None:
    """El moat visible: qué patrones de craft funcionan según resultados REALES (no opinión)."""
    from .reasoning import store as kstore
    from .creative import patterns, decisions

    con = kstore.connect(str(config.DB_PATH))
    for mod in (patterns, decisions):
        mod.init(con)
    cal = decisions.pattern_calibration(con)
    if not cal:
        print("Aún no hay aprendizaje calibrado. Registra decisiones (record-think) y, tras "
              "publicar, resultados (record-outcome). Con suficientes datos aparecerán aquí.")
    else:
        print("Aprendizaje creativo (patrón -> tasa de éxito real, nº de producciones):\n")
        for c in cal:
            print(f"  {c['pattern']:<18} {c['success_rate']:.0%}   (n={c['n']})")
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
        "combine": cmd_combine,
        "think": cmd_think,
        "record-think": cmd_record_think,
        "record-outcome": cmd_record_outcome,
        "learnings": cmd_learnings,
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
