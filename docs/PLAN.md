# PLAN — de "técnicamente correcto" a "profesional" (28-oct-2026)

> **Regla del usuario (28-oct): primero que el resultado sea bueno; la autonomía va AL FINAL y solo
> cuando él lo diga.** "De nada sirve que trabaje solo si el resultado es malo."
> Cada fase termina con una métrica MEDIDA (docs/POLITICA.md), no con "ya está hecho".

## Dónde estamos (medido el 28-oct)

- Crítico automático (Fase 1) hecho: #7 pasó de 39 a 10 en la puntuación del crítico y de 26 fallos a 10. #8 pasó de 25 a 20. Los dos pasan todas las puertas.
- 1.ª calificación a ciegas del usuario: prefiere la versión del crítico (coincide, n=1), **pero** "todavía puede
  mejorar mucho en lo creativo, en lo que cuenta y cómo lo cuenta".
- Los defectos técnicos se miden; la **historia, la narrativa y la elección de tema no**. Ese es el hueco.

## Criterio para pasar de fase

Una pieza nueva calificada a ciegas por el usuario contra la mejor anterior. Se avanza si la nueva
gana o si su nota sube. Meta de calidad antes de pensar en autonomía: **nota ≥ 8/10 en 3 piezas
seguidas** (umbral PROVISIONAL, lo fija el usuario).

---

## Bloque 1 — CONTENIDO (lo que cuenta y cómo lo cuenta) · empezar ya

**1.1 Guion de nivel (F2).** Por vídeo: 3-5 ganchos y 2-3 estructuras narrativas distintas
(misterio/revelación, contraste, cuenta atrás, error común, "lo que nadie dice"). Un crítico de
guion las puntúa con criterios explícitos (cifra en la 1.ª frase, pregunta abierta que se cierra
tarde, giro cada 8-10 s, final en bucle, una sola idea, cero relleno) y elige; el usuario ve las
alternativas descartadas. **HECHO 28-oct** (`video-v2/motor/guionista.py`). 1.ª prueba a ciegas
(#9 housing-turn): el usuario prefirió la PLANTILLA → crítico de guion 0/1 (docs/RUBRICA.md).
_Listo (cambiado 28-oct, decisión del usuario):_ el usuario no es nativo en inglés y no puede pesar
el guion → el guion lo juzga la **referencia del nicho** (3.1: distancia a Shorts que funcionan) y,
al publicar, la **retención real** (4.x, estructuras alternadas entre vídeos). El usuario aprueba
temas, exactitud e imagen; ya no elige entre guiones en inglés.

**1.2 Contar con imagen.** El storyboard se planifica frase a frase con un plano distinto para cada una
("¿qué ve el espectador mientras oye esto?"). Más variedad de escenas, sin clips repetidos dentro de
un vídeo, cortes al pulso de la música y escenas de datos más ricas (comparativas, mapas, líneas
de tiempo). _Listo:_ J2 (imagen = palabra) sin fallos y estructura con parecido < 0,6 respecto a
los vídeos previos (`medir_parecido`).

**1.3 Variedad de formato** (antiplantilla, riesgo de "contenido repetitivo"): 3-4 formatos con
identidad propia (historia de personaje, explicador de noticia, mito vs. realidad, "si hubieras
invertido X en…"). _Listo:_ parecido de estructura < 0,6 entre vídeos consecutivos.

**1.4 Voz.** Prueba a ciegas, mismo guion: Kokoro (actual) contra 1-2 voces premium o humanas
(derechos comerciales verificados). _Listo:_ el usuario elige con audio real.

**1.5 Música y sonido.** Pista elegida por el tono de la historia, cortes al pulso, y el whoosh y el
riser recalibrados (el crítico los bajó mucho: verificar que los cortes no perdieron energía).

## Bloque 2 — VERDAD Y PULIDO (barato, evita errores graves)

**2.1 Verificación de cifras contra la fuente**: cada número del guion se coteja con el texto de su
URL (no solo "tiene fuente"). Lo de "He put in: $122,400" lo cazó el juicio a mano; tiene que
cazarlo una máquina.
**2.2 Ortografía y estilo** en textos de pantalla, título y descripción (puerta del crítico).
**2.3 Lint del motor v2** (`video-v2/motor/motor.js`) en `lint_motor.mjs`: hoy solo se revisa el
motor v1.
**2.4 Versiones fijadas** de lo que se baja de fuera (skill de ducking, HyperFrames, PyAV) + un test que
avise si cambian (hoy rompieron el render y el alineador).
**2.5 Podar la documentación**: ESTADO.md (75 KB, mezcla v1 y v2) y CLAUDE.md ("Estado actual
2026-09-25", motor v1 descrito como actual) → un traspaso corto y verdadero.
**2.6 Calibrar el crítico** con cada nota del usuario (docs/RUBRICA.md, tabla de calibración);
añadir criterios de narrativa cuando 1.1 los tenga.

## Bloque 3 — QUÉ CONTAR (tema) · necesita YouTube habilitado

Requisito: dominios `www.youtube.com`, `youtube.com`, `www.googleapis.com`, `i.ytimg.com` permitidos
en la red del entorno + secreto `YOUTUBE_API_KEY`. Lo configura el usuario.
**3.1 Referencia del nicho**: medir 20-30 Shorts de finanzas con muchas vistas (segundo del gancho,
cortes/s, texto, palabras/min, duración, estructura) → distancia nuestra a la referencia, métrica (b) de POLITICA.
**3.2 Elección de tema**: volver a llenar el corpus (`/daily`), separar temas atemporales de noticias,
medir saturación (cuántos vídeos hay ya), y que el rendimiento propio pese cuando lo haya.
**3.3 Calendario y anticipación**: Fed, inflación (CPI), resultados de empresas, fechas cripto → guiones
con 2-3 finales posibles preparados ANTES; tras el dato, solo cifra + voz + render.
**3.4 Noticia urgente**: detectar picos, puntuar (relevancia × urgencia × verificabilidad × RPM),
borrador corto con fuentes oficiales y aprobación del usuario. Sin fotos de prensa (licencia):
gráficos de datos reales y documentos oficiales.

## Bloque 4 — PUBLICAR Y MEDIR · cuando el usuario apruebe la calidad

**4.1 Primer vídeo v2 público** (YouTube, aprobación de 1 toque) → `analytics-sync` → primera curva.
**4.2 Coste por vídeo** (`record-cost`: horas, tokens, renders).
**4.3 Experimentos** con `creative/experiments.py`: título, hora y gancho, con su prueba de significancia.
**4.4 Adaptación por red** (texto, hashtags, hora) + probar en real carruseles e historias de IG/FB
(confirmación del usuario en el chat para Meta).
**4.5 Vídeos largos (hasta 10 min)**: medir primero el render (hoy ≈7× la duración en CPU) antes
de prometer nada.

## Bloque 5 — AUTONOMÍA · SOLO cuando el usuario lo diga

- Estado con escritura en la nube (`estado-subir` / `produccion-guardar`: hoy solo lectura).
- Rutina diaria programada (`/producir`), cola de trabajos con reintentos y limpieza de renders
  (680 MB + 396 MB solo el 28-oct).
- Panel de solo lectura + pausa general.
- Multi-cuenta aislada (F5) y TikTok/X (requieren apps aprobadas o de pago).
- Decisión del usuario: ¿YouTube se publica solo si pasa todas las puertas, o se mantiene la aprobación de 1 toque?

## Orden de trabajo

`1.1 ✓ → 3.1 (referencia, YouTube ya habilitado en local) → 1.2 → 2.1/2.2/2.3 (baratos, en paralelo) → 1.3/1.4/1.5 → 3.2/3.3 → 3.4 → 4.x → [usuario] 5`
