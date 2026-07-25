# Content Intelligence OS — canal **Net Worthy**

Un sistema que **decide QUÉ contenido crear** (por datos: demanda real + RPM) y **acumula qué
funciona** (un dataset calibrado por resultados medidos). **No es un generador de videos** — el
video es el primer producto; el activo durable es el conocimiento calibrado.

> Nicho: finanzas / inversiones / crypto, faceless, audiencia EN. Canal: **Net Worthy** (@networthytv).

```
SISTEMA decide QUÉ (tema, por demanda+RPM)  →  el humano piensa el CÓMO (ángulo estructurado)
                                            →  SISTEMA acumula QUÉ FUNCIONA (outcome medido)
```

El valor no está en acertar el primer video, sino en que **cada video publicado mejora las
decisiones del siguiente**. Un sistema que adivina se estanca; uno que mide mejora para siempre.

---

## Por qué este repo es interesante (para un ojo técnico)

- **Kernel de razonamiento domain-agnostic** (`omega/reasoning/`) con un **test de pureza por AST**
  que garantiza que no se cuela nada de dominio (video) en el núcleo. El kernel solo hace
  `score = confianza + Σ peso·feature`; no conoce el significado de las features.
- **Cada creencia es una predicción falsable.** Una decisión crea una `prediction` con método de
  verificación, criterio de refutación pre-comprometido y fecha de evaluación. Sin esos tres campos
  no es una predicción, es una opinión — y el código lo rechaza. La calibración mide *"cuando
  decimos 70%, ¿acertamos ~70%?"*.
- **"No Silent Learning" como enforcement estructural**, no como convención: la confianza de una
  creencia solo se puede mutar por un único camino que exige causa válida + rationale, y deja log
  append-only. No existe otro setter.
- **Guards de captura-en-origen**: las métricas se validan al entrar (fracción vs porcentaje,
  rangos, tags obligatorios del vocabulario controlado). Un `4.5` donde va `0.045` se rechaza en vez
  de envenenar el dataset en silencio.
- **Anti-sobreingeniería como política escrita** (`docs/POLITICA.md`): el motor está **congelado**;
  no se añade capacidad sin que un experimento publicado revele la limitación. El progreso se mide
  en **filas del dataset**, no en commits.
- **Cero fricción de despliegue**: SQLite, una sola dependencia de runtime (`feedparser`),
  `anthropic` opcional. Arranca en cualquier máquina, sin build. Modo **$0** honesto: sin API key,
  el sistema piensa con tu cuenta de Claude vía export-prompt y acumula igual.

Auditorías de ingeniería y de producto en `docs/AUDITORIA-INGENIERIA.md` y `docs/AUDITORIA.md`.

---

## Arquitectura

```
feeds.json (12 RSS) ──► sources/rss ─┐
YouTube Data API ──────► sources/youtube ─┤  captura
                                          ▼
                    omega.sqlite  (observed_content · theme_demand · scanned_video)
                                          │
        extractors/* ──► signals          analyze/ (demand · momentum · monetization/RPM)
                                          ▼
                    analyze/hypothesis_engine   (DOMINIO: interpreta señales)
                                          ▼
      reasoning/*  ── KERNEL domain-agnostic (beliefs · predicciones falsables ·
                       decision_engine · abstención como decisión de 1ª clase · calibración)
                                          ▼
      creative/*   ── CKB de patrones · decisiones justificadas ·
                       production_dna + analytics + outcome  ◄── EL MOAT (qué funciona, medido)
                                          ▼
                                cli.py  (dispatch, stdlib pura)

   docs/guiones/short-renderer.html  ── motor de video CONGELADO (HTML sin dependencias:
      genera el Short entero + voz + subtítulos quemados → MP4 H.264/AAC). Acoplado al
      cerebro SOLO por archivos (data/voz-*.mp3 + JSONs de instrumentación).
```

La ruta de crecimiento está aislada: fuentes como plugins (`sources/base.py`), almacenamiento tras
`db.py` (migración futura a Postgres+pgvector sin tocar el resto), análisis reemplazable.

---

## Estado actual

- **3 Shorts publicados** (S1 story · S2 contrarian · S3 stat), instrumentados con su ADN.
- **Loop de medición CERRADO**: `production_outcome` con resultados medidos en YouTube + Facebook;
  `dna` ya calibra por tipo de gancho/historia/CTA (marcado PROVISIONAL mientras n es bajo —
  correcto). Hallazgo real: las plataformas se contradicen (~10× más alcance en FB que en YT), la
  variable dominante hoy es la plataforma, no el gancho.
- **104 tests verdes** (`python -m unittest discover -s tests -q`).
- **Hito activo**: 10 videos instrumentados con ADN + resultado + coste antes de tratar cualquier
  patrón como hipótesis.

---

## Uso

```bash
pip install -r requirements.txt          # única dep de runtime: feedparser

# --- Diario: observar y decidir ---
python -m omega.cli ingest               # captura RSS -> SQLite (correr a diario)
python -m omega.cli youtube-scan         # demanda REAL por tema (vistas de YouTube)
python -m omega.cli signals              # extrae señales de lo observado
python -m omega.cli decide               # Decision Record: mejor tema por demanda+RPM, o ABSTENERSE
#   atajo de los cuatro: .claude/commands/daily.md  (/daily)

# --- Pensar un ángulo (LLM si hay ANTHROPIC_API_KEY; si no, modo $0 export-prompt) ---
python -m omega.cli think "<tema>"       # -> paquete para pegar en Claude -> record-think

# --- Tras publicar: cerrar el loop (esto es lo que llena el moat) ---
python -m omega.cli record-dna <file>            # el 'cómo se hizo' (antes de publicar)
python -m omega.cli record-analytics <file>      # el 'qué pasó' (vistas, CTR, retención)
python -m omega.cli record-cost <file>           # horas reales -> rendimiento por hora
python -m omega.cli record-outcome <ref> <0..1>  # el resultado medido
python -m omega.cli dna                          # dataset + calibración por dimensión

# --- Higiene del sistema ---
python -m omega.cli status               # estado + predicciones vencidas sin resolver
python -m omega.cli resolve-prediction <id> <confirmed|refuted|inconclusive> [nota]
python -m omega.cli backup               # zip fechado del moat -> COPIAR a nube/USB
```

`YOUTUBE_API_KEY` (y opcional `ANTHROPIC_API_KEY`) van en un `.env` en la raíz (gitignored).

---

## Documentación

| Documento | Qué es |
|---|---|
| `docs/ESTADO.md` | Traspaso — **empieza aquí**; trae las trampas conocidas. |
| `docs/POLITICA.md` | Política de ingeniería: congela el motor, genera datos. |
| `docs/VISION.md` | Arquitectura y visión a largo plazo. |
| `docs/AUDITORIA-INGENIERIA.md` | Auditoría de ingeniería (nivel Principal Engineer). |
| `docs/AUDITORIA.md` | Auditoría de producto/crecimiento. |
| `docs/guiones/` | Guiones, motor de video, calibración de voz. |

---

## Licencia

Propietario — **todos los derechos reservados**. Ver [`LICENSE`](LICENSE). El código es visible
para evaluación; su uso, copia, distribución o derivados requieren permiso escrito del autor.
