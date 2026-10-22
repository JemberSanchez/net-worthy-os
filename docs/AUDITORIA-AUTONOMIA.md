# Auditoría para el objetivo "sistema autónomo de marketing multirredes" — 2026-10-21

Fase 1 (auditoría) + 2 (brechas) + 3 (prioridades). Todo lo marcado **VERIFICADO** se comprobó
ejecutando algo hoy; lo demás dice de dónde sale.

## 0. Hechos verificados hoy

| Hecho                                                                                                                                                      | Cómo se verificó                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| El PC estaba 30 commits por detrás de `origin/master` (todo el v2 se hizo en la nube)                                                                      | `git fetch` + `git pull --ff-only`        |
| **No hay ninguna rutina programada.** El sistema no corre solo, ni un día                                                                                  | `RemoteTrigger list` → `[]`               |
| Último trabajo: 1-oct. Lleva 20 días parado                                                                                                                | `git log`, repo de estado                 |
| La base de estado (`net-worthy-data/omega.sql`, 3,8 KB) tiene **2 filas**: el ADN de #7 y #8. Cero `production_video`, cero analytics, cero corpus/señales | volcado descargado y contado              |
| **#7 y #8 v2 nunca se publicaron.** Hito "10 vídeos v2": **0/10**                                                                                          | ídem                                      |
| El CI de `master` estaba rojo desde el 1-oct: `rapidocr_onnxruntime>=1.3` no tiene wheel para Python 3.14                                                  | log del run 36892292717                   |
| `tools/ocr_doc.py` tampoco funcionaba en este PC (estaba instalado `rapidocr` 3, no el paquete viejo)                                                      | import                                    |
| Un test fallaba solo en Windows (conexión SQLite sin cerrar)                                                                                               | `unittest` local                          |
| Tests: 261 (tras los arreglos, todos OK en Windows)                                                                                                        | `python -m unittest discover -s tests -q` |
| Este PC no tiene `.env` ni tokens: `youtube-scan`, `publish`, Meta y `analytics-sync` **no se pueden ejecutar aquí**                                       | `ls`                                      |

**Arreglado hoy:** OCR migrado a `rapidocr>=3.4` (verificado: encuentra "BILLIONS LOST AS STOCKS
CRASH" en `crash.jpg` con 0,986; hizo falta `Det.limit_type=max`, porque con la configuración por
defecto partía el titular) y el test de Windows.

## 1. Lo que existe, contrastado con el pedido

| Pedido                | Qué hay                                                                                                                                                          | Estado real                                                                                                                                                                                                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2. Investigación      | `ingest` (RSS), `youtube-scan`/`youtube`/`related` (YouTube Data API: vistas públicas reales), `signals`, `patterns`, `trends`                                   | Código + tests. **Corpus vacío** desde el reinicio. No hay investigación de IG/FB/TikTok de terceros                                                                                                                                                                   |
| 3. Estrategia         | `decide` (tema por demanda × RPM), `think`/`record-think`, hipótesis/predicciones en `omega/reasoning`                                                           | Elige UN tema. **No hay** calendario, mezcla de objetivos ni frecuencia adaptativa                                                                                                                                                                                     |
| 4. Generación         | Motor v2 por `storyboard.json` (10 escenas, b-roll y música con licencia, OCR de pruebas, voz Kokoro, QA de puertas); `social.py` (carrusel 4:5 + historia 9:16) | El guion y el storyboard los escribe Claude dentro de `/producir`. Probado en #7 y #8. Es la parte más madura                                                                                                                                                          |
| 5. Adaptación por red | `publish_<ref>.json` con título y descripción; `ig_caption`; `social.py` saca formatos por red                                                                   | Parcial: el mismo MP4 va a las 3 redes. Sin hashtags ni horario por red                                                                                                                                                                                                |
| 6. Ciclo autónomo     | `/producir` (comando de Claude Code) encadena todo hasta el borrador privado y **para** a esperar aprobación                                                     | **No hay programador** (0 rutinas). No hay cola, ni registro de jobs, ni reintentos persistentes                                                                                                                                                                       |
| 6. Sin duplicados     | —                                                                                                                                                                | **No existía** (todo subidor volvía a subir). **Hecho hoy:** `_ya_publicado` consulta `production_video` (ref × red) en `publish`, `publish-fb`, `publish-ig`, `publish-social` y `subir_borrador`; Meta se registra al publicar en vivo; `--forzar` lo salta. 4 tests |
| 7. QA                 | Puertas deterministas en `producir.py`: lint, -14 LUFS, ritmo ≤2,5 s, contraste WCAG, anclas, cifras con fuente, licencias en lista cerrada                      | Bueno para el vídeo. Falta: similitud con lo ya publicado, ortografía, reglas YMYL como puerta                                                                                                                                                                         |
| 8. Aprendizaje        | `analytics-sync` (curva de retención de 100 puntos, tráfico, búsquedas), score v2, `rescore`, `dna`, `learnings`                                                 | Código + tests con clientes falsos. **Nunca corrió sobre un vídeo v2** (no hay ninguno publicado)                                                                                                                                                                      |
| 9. Tendencias         | `signals` con momentum, `theme_demand_history`                                                                                                                   | Sin fecha de caducidad ni evaluación de "¿sigue vigente?"                                                                                                                                                                                                              |
| 10. Panel             | `cmd_status` (texto)                                                                                                                                             | No hay panel, ni pausa global, ni límites de gasto                                                                                                                                                                                                                     |
| 11. Seguridad         | Secretos en `.env`/archivos gitignored, gitleaks, Semgrep y Actions pinneadas por SHA                                                                            | Bien. Falta: auditoría de operaciones de publicación y parada de emergencia                                                                                                                                                                                            |

## 2. Restricciones reales de plataforma (lo que decide qué se puede automatizar)

Verificadas en el código y en los commits del proyecto (no en documentación nueva):

- **YouTube:** subida privada + `publishAt` (programar) = SÍ (`publish.py`). Fijar comentario = **NO
  por API** (manual en Studio). Retención por punto = SÍ (Analytics API, con ~2-3 días de retraso).
  Métricas públicas de vídeos ajenos = SÍ (Data API, ya en `youtube-scan`).
- **Facebook:** Reels por `/video_reels` (el endpoint genérico `/videos` acepta y nunca procesa:
  bug cazado el 31-jul). Borrador = SÍ.
- **Instagram:** Reels vía contenedor + `media_publish`; **no hay borrador por API** (publicar =
  público al instante). Las imágenes deben estar en una URL pública. Historias y carruseles:
  código escrito, **nunca probados en real**.
- **Regla del proyecto, no técnica:** Meta `--publicar` solo con confirmación en el chat.

Sin verificar (no hay integración; hay que mirar la documentación oficial antes de prometer nada):
TikTok (Content Posting API; las apps no auditadas, que yo sepa, solo publican en privado), X
(API de pago), métricas de cuentas ajenas en IG (Business Discovery da conteos básicos de cuentas
business) y Meta Ad Library (cobertura limitada fuera de la UE).

## 3. El hallazgo que manda sobre todo lo demás

`docs/POLITICA.md`: _progreso = filas del dataset, no commits ni módulos_. Hoy hay **0 vídeos v2
publicados y 0 métricas**. Todo lo del pedido que "aprende" (secciones 3, 8 y 9) necesita datos que
no existen. Construir calendario, panel o investigación multirred ahora sería optimizar sin señal.
Lo que más acerca al objetivo **no es construir: es que el ciclo corra de verdad**, aunque sea con
una sola red, y empiece a producir filas.

## 4. Prioridades (impacto / riesgo / dependencias)

**Imprescindibles, en este orden:**

1. ✅ CI verde + OCR funcionando (hecho hoy).
2. ✅ **Publicación idempotente** (hecho hoy). Se reutilizó la tabla `production_video`, que ya
   tenía clave ref × red, en vez de crear otra; los formatos sociales van como red
   `instagram_carrusel`, `facebook_historia`, etc. Límite conocido (comentado en el código): no hay
   estado "subiendo", así que si la subida termina y falla el registro, el reintento duplica.
   Ampliar solo si se ve en real.
3. **Publicar #7 y #8 v2** (SETUP-NUBE, sección E). Primera fila real. Depende de: el token de
   YouTube (lo tiene el usuario).
4. **Rutina diaria programada** (routine de Claude Code en la nube → `/producir` → borrador privado →
   aprobación con 1 toque). Depende de: 2, 3 y los secretos en el entorno de la nube.
5. `analytics-sync` en la rutina, sobre vídeos reales: cierra el ciclo medir → aprender.

**Después, solo cuando haya datos (n ≥ 5 vídeos v2 medidos):** 6. Puerta de similitud con lo ya publicado (anti contenido inauténtico). 7. Adaptación por red (texto, hashtags, horario por plataforma) a partir de la retención medida en cada una. 8. Panel de solo lectura (estado de jobs, últimas métricas, fecha de actualización) + pausa global. 9. Calendario y mezcla de objetivos.

**Opcional / bloqueado:** TikTok, X y LinkedIn (requieren apps aprobadas o de pago),
investigación de competidores en IG (solo Business Discovery) y publicidad pagada (no hay cuenta de anuncios).

## 5. Decisiones que son del usuario (bloquean el punto 4)

- **Autopublicación:** ¿YouTube puede publicarse solo si pasa todas las puertas, o se mantiene la
  aprobación de 1 toque? (Meta sigue con confirmación en el chat por regla del proyecto.)
- **Dónde corre:** routine en la nube de Claude Code (gasta tokens de la suscripción en cada run)
  o tarea programada en este PC (tiene que estar encendido).
