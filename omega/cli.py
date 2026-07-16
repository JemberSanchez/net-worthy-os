"""CLI de El Analista.

Comandos:
  python -m omega.cli ingest     # captura RSS -> SQLite (correr a diario)
  python -m omega.cli trends     # reporte de temas en alza/caída
  python -m omega.cli youtube <query>   # demanda REAL: qué temas mueven vistas (YouTube API)
  python -m omega.cli youtube-scan      # barre el nicho y CACHEA demanda -> alimenta 'decide'
  python -m omega.cli related <tema>    # temas ADYACENTES: qué más ve esa audiencia (#1)
  python -m omega.cli signals    # extrae señales de lo observado (extractores-plugin)
  python -m omega.cli decide     # flujo completo: señales -> hipótesis -> decisión explicable
  python -m omega.cli patterns   # muestra el Creative Knowledge Base (vocabulario de craft)
  python -m omega.cli combine <sujeto>   # divergencia: k encuadres distintos de un sujeto
  python -m omega.cli think <sujeto>     # el director PIENSA un sujeto (usa LLM si hay key)
  python -m omega.cli record-think [file]          # registra el resultado que te dio tu Claude
  python -m omega.cli record-dna [file]            # registra el ADN de produccion de un video
  python -m omega.cli record-analytics [file]      # registra CTR/AVD/retencion tras publicar
  python -m omega.cli record-cost [file]           # registra horas/coste de producir el video
  python -m omega.cli dna                          # dataset de ADN + calibracion + rendimiento/hora
  python -m omega.cli record-outcome <ref> <0..1>  # tras publicar: registra el resultado medido
  python -m omega.cli learnings                    # qué patrones funcionan (calibración acumulada)
  python -m omega.cli hypotheses # genera un prompt con la evidencia para pegar en Claude
  python -m omega.cli resolve-prediction <id> <outcome> [nota]  # cierra una predicción vencida
  python -m omega.cli backup     # zip fechado del moat (SQLite+voces+JSONs) -> copiar a nube/USB
  python -m omega.cli status     # estado de la base + predicciones vencidas sin resolver
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


def cmd_youtube() -> None:
    """Señal de DEMANDA REAL: qué videos de finanzas consiguen vistas y qué temas las mueven.

    A diferencia de 'trends' (presencia en artículos), esto usa las VISTAS reales de YouTube:
    el detector de temas serio. Necesita YOUTUBE_API_KEY en .env (cuota gratuita)."""
    from .sources import youtube
    from .analyze import demand

    query = " ".join(sys.argv[2:]).strip() or "stock market investing"
    print(f"YouTube — demanda real para: '{query}'  (últimos 30 días, orden por vistas)\n")
    try:
        videos = youtube.fetch_recent(query, days=30, max_results=25)
    except youtube.YouTubeError as exc:
        print(f"Error de YouTube API: {exc}")
        print("Revisa que YOUTUBE_API_KEY esté en .env y que la API esté habilitada en el proyecto.")
        return
    if not videos:
        print("Sin resultados para esa búsqueda.")
        return

    print("--- TOP VIDEOS POR VISTAS ---")
    for v in videos[:12]:
        print(f"  {v['views']:>12,}  {v['title'][:64]}")
        print(f"                {v['channel']}  |  {v['url']}")

    print("\n--- TEMAS QUE MUEVEN VISTAS (suma de vistas por término del título) ---")
    ranked = demand.theme_demand(videos)
    if not ranked:
        print("  (pocos títulos para agregar; sube max_results o prueba otra query)")
    for r in ranked[:15]:
        print(f"  {r['total_views']:>12,}  {r['term']:<24} "
              f"(en {r['videos']} videos, media {r['avg_views']:,})")
    print("\nEsto es DEMANDA (vistas reales), no volumen editorial. El detector de temas serio.")


def cmd_youtube_scan() -> None:
    """Sensor de DEMANDA del nicho: barre varias búsquedas, agrega vistas por tema y las CACHEA.

    A partir de aquí 'decide' pondera por demanda real (feature 'demand'), no solo por presencia
    en titulares. Corre esto como el 'ingest' de YouTube: cada cierto tiempo, no en cada decide."""
    from .sources import youtube
    from .analyze import demand

    db.init()
    queries = config.YOUTUBE_NICHE_QUERIES
    print(f"Escaneando demanda del nicho en YouTube ({len(queries)} búsquedas)...")
    for q in queries:
        print(f"  · {q}")
    try:
        rows, videos = demand.scan_nicho(queries, days=30, max_results=25)
    except youtube.YouTubeError as exc:
        print(f"\nError de YouTube API: {exc}")
        print("Revisa YOUTUBE_API_KEY en .env y que la API esté habilitada.")
        return

    scanned_at = int(time.time())
    db.clear_theme_demand()  # snapshot del presente: fuera los términos del basket anterior
    saved = db.upsert_theme_demand(rows, scanned_at)
    db.append_theme_demand_history(rows, scanned_at)  # acumula para el momentum de demanda
    db.replace_scanned_videos(videos, scanned_at)     # videos crudos para la adyacencia (related)
    print(f"\n{len(videos)} videos únicos analizados | {saved} temas con demanda cacheados.")
    print("\nTop temas por vistas reales (lo que 'decide' ahora premia):")
    for r in rows[:12]:
        print(f"  {r['total_views']:>12,}  {r['term']:<24} (en {r['videos']} videos)")
    print("\nListo. Corre 'python -m omega.cli decide' para decidir ponderando esta demanda.")


def cmd_related() -> None:
    """ADYACENCIA (#1): qué OTROS temas ve la audiencia que ve un tema dado. El input de datos a
    la reflexión creativa: 'si ven X, también les interesa Y'. Adelantarse = servir esa adyacencia
    desatendida con un ángulo inesperado. Necesita un 'youtube-scan' previo (videos crudos)."""
    from .analyze import demand

    db.init()
    root = " ".join(sys.argv[2:]).strip()
    if not root:
        print("Uso: related <tema>   (ej: related \"build wealth\")")
        return
    videos = db.fetch_scanned_videos()
    if not videos:
        print("No hay videos escaneados. Corre 'youtube-scan' primero.")
        return
    rows = demand.related(root, videos)
    print(f"Temas ADYACENTES a '{root}' — lo que TAMBIÉN ve esa audiencia:\n")
    if not rows:
        print("  (sin co-ocurrencias suficientes; usa un tema presente en el último escaneo)")
        return
    for r in rows:
        print(f"  {r['views']:>12,}  {r['term']:<24} (juntos en {r['together']} videos)")
    print("\nInput a la reflexión creativa: si ven el tema, también les interesa esto.")
    print("Adelantarse = servir esta adyacencia DESATENDIDA con un ángulo inesperado (think).")


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


def cmd_record_dna() -> None:
    """Registra el ADN de producción de un video (el 'cómo se hizo'), ANTES de publicar. Así el
    primer video ya entra instrumentado al dataset — no se pierde la señal por bloque."""
    import json
    from pathlib import Path
    from .reasoning import store as kstore
    from .creative import production_dna

    path = Path(sys.argv[2]) if len(sys.argv) > 2 else (config.DATA_DIR / "production_dna.json")
    if not path.exists():
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        tpl = {"production_ref": "<id-del-video>",
               "hook_type": "story|question|contrarian|stat|shock",
               "story_type": "personal|character|case_study|none",
               "cta_type": "session|subscribe|comment|none",
               "length_s": 450,
               "blocks": [{"block": "hook", "technique": "two_men_story", "length_s": 35},
                          {"block": "proof", "technique": "compound_curve", "length_s": 135}]}
        (config.DATA_DIR / "production_dna.template.json").write_text(
            json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"No existe {path}. Plantilla escrita en production_dna.template.json — "
              "rellénala, renómbrala a production_dna.json y reintenta.")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    con = kstore.connect(str(config.DB_PATH))
    production_dna.init(con)
    production_dna.record_dna(
        con, production_ref=data["production_ref"], blocks=data.get("blocks", []),
        hook_type=data.get("hook_type"), story_type=data.get("story_type"),
        cta_type=data.get("cta_type"), length_s=data.get("length_s"))
    print(f"ADN registrado: {data['production_ref']} — {len(data.get('blocks', []))} bloques "
          f"(hook={data.get('hook_type')}, story={data.get('story_type')}, cta={data.get('cta_type')}).")
    print("Tras publicar y medir: record-analytics + record-outcome, y luego 'dna'.")
    con.close()


def cmd_record_analytics() -> None:
    """Registra las analíticas MEDIDAS tras publicar (CTR/AVD/retención/fuente). El 'qué pasó'."""
    import json
    from pathlib import Path
    from .reasoning import store as kstore
    from .creative import production_dna

    path = Path(sys.argv[2]) if len(sys.argv) > 2 else (config.DATA_DIR / "production_analytics.json")
    if not path.exists():
        print(f"No existe {path}. Crea un JSON con: production_ref, ctr, avd_pct, retention_avg, "
              "traffic_source, retention_by_block.")
        return
    d = json.loads(path.read_text(encoding="utf-8"))
    if not d.get("production_ref") or str(d["production_ref"]).startswith("<"):
        print(f"Rechazado: falta 'production_ref' en {path} (o quedó el placeholder).")
        return
    con = kstore.connect(str(config.DB_PATH))
    production_dna.init(con)
    try:
        production_dna.record_analytics(
            con, production_ref=d["production_ref"], ctr=d.get("ctr"), avd_pct=d.get("avd_pct"),
            retention_avg=d.get("retention_avg"), views=d.get("views"),
            traffic_source=d.get("traffic_source"), retention_by_block=d.get("retention_by_block"))
    except ValueError as exc:
        print(f"Rechazado: {exc}")
        con.close()
        return
    print(f"Analíticas registradas: {d['production_ref']}.")
    con.close()


def cmd_record_cost() -> None:
    """Registra el COSTE de producir un video (horas + $ IA + tiempo a publicar). Lee
    data/production_cost.json. Habilita 'rendimiento por hora de trabajo' en 'dna'."""
    import json
    from pathlib import Path
    from .reasoning import store as kstore
    from .creative import production_dna

    path = Path(sys.argv[2]) if len(sys.argv) > 2 else (config.DATA_DIR / "production_cost.json")
    if not path.exists():
        print(f"No existe {path}. Crea un JSON con: production_ref, research_hours, script_hours, "
              "edit_hours, ai_cost_usd, time_to_publish_h.")
        return
    d = json.loads(path.read_text(encoding="utf-8"))
    con = kstore.connect(str(config.DB_PATH))
    production_dna.init(con)
    production_dna.record_cost(
        con, production_ref=d["production_ref"], research_hours=d.get("research_hours"),
        script_hours=d.get("script_hours"), edit_hours=d.get("edit_hours"),
        ai_cost_usd=d.get("ai_cost_usd"), time_to_publish_h=d.get("time_to_publish_h"))
    print(f"Coste registrado: {d['production_ref']}.")
    con.close()


def cmd_dna() -> None:
    """Muestra el dataset de ADN de producción + calibración por dimensión (con guard de rigor)."""
    from .reasoning import store as kstore
    from .creative import production_dna, decisions

    con = kstore.connect(str(config.DB_PATH))
    for mod in (production_dna, decisions):
        mod.init(con)
    rows = production_dna.list_dna(con)
    print(f"Dataset de ADN de producción: {len(rows)} videos instrumentados\n")
    for r in rows:
        print(f"  {r['production_ref']}")
        print(f"    hook={r['hook_type']} | story={r['story_type']} | cta={r['cta_type']} | "
              f"{r['block_count']} bloques | {r['length_s']}s")

    print("\n--- Calibración por dimensión (solo con resultado medido) ---")
    any_data = False
    for dim in ("hook_type", "story_type", "cta_type"):
        cal = production_dna.dna_calibration(con, dim)
        if not cal:
            continue
        any_data = True
        print(f"\n  [{dim}]")
        for c in cal:
            flag = "  ⚠ PROVISIONAL (n bajo, posible ruido)" if c["provisional"] else ""
            print(f"    {c['value']:<16} {c['success_rate']:.0%}  (n={c['n']}){flag}")
    if not any_data:
        print("  (aún sin resultados medidos: registra outcomes y vuelve)")

    eff = production_dna.efficiency(con)
    if eff:
        print("\n--- Rendimiento por esfuerzo (éxito por hora de trabajo, CRUDO) ---")
        for e in eff:
            sph = f"{e['success_per_hour']}" if e["success_per_hour"] is not None else "s/h?"
            print(f"    {e['production_ref']:<42} {e['success']:.2f} éxito / {e['total_hours']}h = {sph}")

    print("\n[!] La gráfica dice DÓNDE, no POR QUÉ. Con pocos videos cada dimensión co-varía con")
    print("    b-roll/voz/música (confounding). Aísla la variable (experiments) antes de concluir.")
    print(f"    Hito: 10 videos instrumentados antes de tratar un patrón como hipótesis. Vas por {len(rows)}.")
    con.close()


def cmd_record_outcome() -> None:
    """Tras publicar: registra el resultado MEDIDO (0..1) de una producción. Alimenta la calibración."""
    from .reasoning import store as kstore
    from .creative import patterns, decisions

    if len(sys.argv) < 4:
        print("Uso: record-outcome <production_ref> <success 0..1>")
        return
    ref = sys.argv[2]
    try:
        success = float(sys.argv[3])
    except ValueError:
        print(f"Rechazado: '{sys.argv[3]}' no es un número. success va en [0,1] (ej. 0.35).")
        return
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
    from .reasoning import store as kstore

    db.init()
    print(f"Base de conocimiento: {db.count_total()} documentos observados")
    print(f"DB: {config.DB_PATH}")

    # Deuda epistémica visible: predicciones cuya fecha de verificación llegó y nadie resolvió.
    # Sin esto, 'decide' acumula predicciones que jamás se comprueban (el fallo nº1 del kernel)
    # y la calibración ("¿cuando decimos 70% acertamos 70%?") es inevaluable.
    con = kstore.connect(str(config.DB_PATH))
    kstore.init(con)
    due = kstore.due_predictions(con)
    if due:
        print(f"\n⚠ {len(due)} predicción(es) VENCIDAS sin resolver (deuda epistémica):")
        for p in due:
            print(f"  #{p['id']}  {p['statement'][:70]}")
            print(f"        vencía {_fmt(p['expected_verification_at'])} | criterio: {p['refutation_criterion'][:60]}")
        print("Resuélvelas: python -m omega.cli resolve-prediction <id> <confirmed|refuted|inconclusive> [nota]")
    else:
        print("Sin predicciones vencidas pendientes.")
    con.close()


def cmd_resolve_prediction() -> None:
    """Cierra el ciclo epistémico: resuelve una predicción vencida contra la realidad observada.
    Resolver NO actualiza la creencia (No Silent Learning): eso es un paso explícito aparte."""
    from .reasoning import store as kstore

    if len(sys.argv) < 4:
        print("Uso: resolve-prediction <id> <confirmed|refuted|inconclusive> [nota]")
        print("Las pendientes salen en 'status'.")
        return
    try:
        pid = int(sys.argv[2])
    except ValueError:
        print(f"Rechazado: '{sys.argv[2]}' no es un id numérico de predicción.")
        return
    outcome = sys.argv[3]
    note = " ".join(sys.argv[4:]).strip()
    con = kstore.connect(str(config.DB_PATH))
    kstore.init(con)
    try:
        kstore.resolve_prediction(con, pid, outcome=outcome, note=note)
    except ValueError as exc:
        print(f"Rechazado: {exc}")
        con.close()
        return
    print(f"Predicción #{pid} -> {outcome}. La calibración del kernel acumula.")
    cal = kstore.calibration(con)
    if cal:
        print("Calibración (confianza declarada vs acierto real):")
        for b in cal:
            print(f"  banda {b['band']:.1f}: {b['actual_rate']:.0%} real (n={b['n']})")
    con.close()


def cmd_backup() -> None:
    """Backup del MOAT (SQLite consistente + voces + JSONs) en un zip fechado. El dataset es el
    activo del proyecto y vive gitignored en un solo disco: sin esto, un fallo de disco lo borra."""
    out = db.backup_snapshot()
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"Backup creado: {out}  ({size_mb:.1f} MB)")
    print("⚠ Está en el MISMO disco: cópialo a nube/USB. Un backup local solo protege de borrados.")


def main(argv: list[str]) -> int:
    cmds = {
        "ingest": cmd_ingest,
        "trends": cmd_trends,
        "youtube": cmd_youtube,
        "youtube-scan": cmd_youtube_scan,
        "related": cmd_related,
        "signals": cmd_signals,
        "decide": cmd_decide,
        "patterns": cmd_patterns,
        "combine": cmd_combine,
        "think": cmd_think,
        "record-think": cmd_record_think,
        "record-dna": cmd_record_dna,
        "record-analytics": cmd_record_analytics,
        "record-cost": cmd_record_cost,
        "dna": cmd_dna,
        "record-outcome": cmd_record_outcome,
        "learnings": cmd_learnings,
        "hypotheses": cmd_hypotheses,
        "resolve-prediction": cmd_resolve_prediction,
        "backup": cmd_backup,
        "status": cmd_status,
    }
    if len(argv) < 1 or argv[0] not in cmds:
        print(__doc__)
        return 1
    cmds[argv[0]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
