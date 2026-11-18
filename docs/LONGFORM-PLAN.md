# PLAN LONG-FORM: del Short al vídeo de 8-10 min (18-nov-2026)

> Documento de DISEÑO. No hay código del motor escrito. Las decisiones marcadas **[CONFIRMADO]**
> eran recomendaciones; el usuario confirmó Q1-Q6 el 18-nov.
> Objetivo único: **ingresos**. Cada fase se juzga por cuánto acerca al primer dólar y al YPP.

## 1. Datos del canal (18-nov, API YouTube Data + Analytics, DB local)

| Métrica                   | Net Worthy                     | YPP hoy                         | YPP nuevos desde 1-feb-2027 |
| ------------------------- | ------------------------------ | ------------------------------- | --------------------------- |
| Suscriptores              | **3**                          | 1.000                           | 1.000                       |
| Vistas de Shorts, 90 días | **1.937** (2.146 en total)     | 10 M                            | 20 M                        |
| Horas long-form, 12 meses | **0** (6,2 h, todas de Shorts) | 4.000                           | 8.000                       |
| Fan funding (secundario)  | —                              | 500 subs + 3.000 h o 3 M Shorts | sin cambio                  |

- 29 Shorts públicos (jul 6, ago 1, oct 3, nov 19); 22 en los últimos 30 días ≈ 5/semana.
- Retención: % medio visto 74 % (90 d); "se quedaron" ponderado 38,8 % (n=19); score v4 medio 0,52.
- Mejores: huang-exit 553 vistas, midterm-rally 497, ronald-wayne 241. 9 de 19 con ≥ 30 vistas.
- Conversión: **1,4 suscriptores por 1.000 vistas** (3 / 2.146). FB+IG: 42 reels, ~13-230 vistas cada uno.
- `production_cost` sigue vacío.

Fuentes de umbrales: [YPP oficial](https://support.google.com/youtube/answer/72851) (1.000 subs + 4.000 h
o 10 M Shorts/90 d; las horas de Shorts NO cuentan), [cambios 2027, oficial](https://support.google.com/youtube/answer/12843009)
y [ppc.land](https://ppc.land/new-youtube-creators-face-8-000-hour-bar-for-ad-revenue-from-february-2027/)
(8.000 h o 20 M; los miembros actuales conservan su estado).
Detalle y URLs de monetización: nota `monetizacion.md` del grupo de sesiones (resumen en §6).

## 2. Decisión: empezar el long-form YA [CONFIRMADO 18-nov]

1. **La vía Shorts no es realista:** 1.937 vistas / 90 d contra 20 M = 10.000× por debajo.
2. **Las horas de Shorts nunca cuentan.** Con 3 subs no llegaremos antes del 1-feb-2027, así que la meta
   real es **8.000 h de long-form**. Ese reloj solo corre cuando existe long-form, y hoy está en 0.
3. **Dinero por vista:** long-form de finanzas da un RPM de $5-15 (supuesto de planificación; los blogs
   dicen $8-40, AIR da una mediana de $2 con n=3 canales). Los Shorts dan el 3-14 % de eso
   ([AIR](https://air.io/en/air-data-findings/what-is-youtube-shorts-rpm-in-your-niche-in-2026)).
   Los mid-rolls se activan desde 8 min ([oficial](https://support.google.com/youtube/answer/6175006)).
4. **Tamaño del objetivo:** 8.000 h ≈ 120.000-150.000 vistas de un vídeo de 9-10 min con 35-40 % de
   retención. Con un vídeo por semana, eso pide ~3.000 vistas por vídeo durante un año. Es difícil,
   pero es la única vía. Los afiliados y el correo dan ingresos antes (§6).
5. **Los Shorts siguen, como embudo:** bajan a ~3/semana y cada uno enlaza a un long-form con
   "related video". Este enlace se pone a mano en Studio, porque la API pública no lo permite ([oficial](https://support.google.com/youtube/answer/14075157)).

Contra-argumento honesto: con 1,4 subs por 1.000 vistas el embudo es débil, y un long-form sin
suscriptores depende de la búsqueda y del "suggested". Por eso los temas salen de la demanda medida (`decide`,
`youtube-scan`) y de los Shorts que ya retuvieron, y la miniatura y el título son entregables de primera clase.

## 3. Política nueva [CONFIRMADO 18-nov]

Aplicado en `docs/POLITICA.md` (18-nov):

- **Puertas que BLOQUEAN, solo lo irreversible o lo roto:** YMYL (aviso, nada de consejo
  personalizado, cifras corregidas), licencias (lista cerrada), reglas de YouTube (inautenticidad, estafas,
  divulgación de IA realista y de promoción pagada), **cada cifra con URL** y lo técnico roto (texto
  ilegible o fuera de cuadro, loudness, voz cortada).
- **Lo creativo NO bloquea:** rúbrica J1-J6, P1 parecido, ritmo, gancho y repetición pasan a ser AVISOS
  en el informe. Juez de lo creativo = **retención real + suscriptores por 1.000 vistas**,
  publicado.
- "Mejora solo con métrica medida" se mantiene solo para cambios CAROS del motor (>1 día). Lo barato
  y reversible se publica y se mide.
- El hito "juez automático = usuario" deja de ser requisito previo para publicar. Sigue siendo el
  requisito para la autonomía total.

## 4. Pruebas baratas ya hechas (18-nov, n=1, HyperFrames 0.9.67, RTX 5050)

Copia de `huang-exit` a 1920x1080, estirada ×2,5 hasta 91,6 s, render `--quality high` (scripts en el scratchpad
de la sesión, nada del repo tocado):

| Medida                           | 16:9, 91,6 s                              | Short, ~37 s (referencia)    |
| -------------------------------- | ----------------------------------------- | ---------------------------- |
| Render                           | 168 s = **1,83 s/s**                      | 77-114 s = 2,1-2,6 s/s       |
| Pico de RAM del árbol de render  | **3,98 GB** (sistema 9,4 → 12,4 de 16 GB) | sin dato                     |
| GPU                              | NVIDIA (hardware, D3D11)                  | —                            |
| OCR del crítico (2 fps, 6 proc.) | 184 frames en 201 s = **2,20 s/s**        | 74 frames en 89 s = 2,43 s/s |

Extrapolación lineal a 10 min (estimada, no medida): render ~18-19 min, OCR ~22 min, crítico entero
~25-28 min. **Una ronda limpia ≈ 45 min de máquina.** La RAM no debería crecer con la duración, porque la captura
va en streaming al encoder (supuesto). **No hace falta render por segmentos** para empezar.

Bloqueo hallado: el layout está en píxeles fijos de 9:16 (texto enorme y cortado a 1920x1080). El
trabajo real es el layout 16:9, no la resolución.

## 5. Diseño técnico (motor v2, sin romper Shorts)

Referencias: nota `motor-longform-map.md` del grupo (líneas exactas) y `critico-escala.md` (resumen en §5.5).

### 5.1 Formato como dato

- `storyboard.json` gana `"formato": "short" | "largo"` (por defecto `short`; los Shorts quedan idénticos).
- Cambio de constantes (~35-45 líneas): `plantilla.tpl` (6, 21, 103, 149, 239), `construir.py` (727, 959,
  1263-1294), `motor3d.js` (15, 21), `puertas.py:187` ANCHO_UTIL, `tools/broll.py` (54, 499, 508, 654, recortes
  9:16), `profundidad.py:59`, `imagenes_libres.py` (46 ALTO_MIN, 197 orientación), `critico.py:1171`.
- Layout 16:9 (~200-300 líneas): bloque CSS `#root.ancho` aparte en `plantilla.tpl` (111 líneas con px),
  marcado inline de `construir.py` m_* (600-904), coordenadas de `motor.js` (gráfica 850x830, cámaras) y
  `edicion.py:75-114`.
- Zonas seguras 16:9 en `rubrica.json` por formato: margen ~5 %, sin texto en el 10 % inferior (barra de
  progreso), esquina superior derecha libre (tarjetas) y los últimos 5-20 s libres para la pantalla final.
- `social.py`: el long-form NO hace carrusel. Hace la miniatura (§5.4).

### 5.2 Guion y voz por capítulos

- Guion = lista de capítulos `{titulo, frases[]}`. Anclas `frase:palabra` sin cambio (numeración global).
- Estructura obligatoria por capítulo (regla `raw-term-is-que-not-video`): gancho → qué cambió → datos →
  alcista → riesgo → "y a mí qué" → cierre. Intro: la promesa dicha antes de 30 s.
- `guionista.py:34` hoy bloquea todo long-form (85-110 palabras, máx. 3 cifras): límites por formato
  (~1.300-1.600 palabras, cifras sin tope y todas con URL).
- Voz: Kokoro `am_adam` y la alineación de siempre. `voz.py` sintetiza **por capítulo** (~40-60 líneas):
  si un capítulo falla, se repite solo ese. Concatena en UN `voice.mp3` + UN `words.json`, con un solo
  realineamiento final. Kokoro trocea el texto por dentro y Needleman-Wunsch con 10 min ≈ 2,3 M celdas: aguanta.
- Descripción con la lista de capítulos `0:00 …`. YouTube exige ≥ 3 capítulos, el primero en 0:00 y cada uno ≥ 10 s.

### 5.3 Escenas nuevas (catálogo cerrado; 11 tipos hoy)

| Pedido              | Hoy                                                                         | Trabajo                                 |
| ------------------- | --------------------------------------------------------------------------- | --------------------------------------- |
| Capítulo            | `titulo` + `transicion` (sin número)                                        | variante `capitulo`: número + título    |
| Cifra grande        | `contador3d` (máx. 1 por vídeo, `construir.py:276`) o `titulo` con contador | subir el tope en `largo`                |
| Comparación         | `cta` A/o/B, `revelacion`, `grafica`                                        | **nueva** `comparacion` a dos columnas  |
| Rótulo sobre b-roll | `foto` + `clip` + `rotulos` `pos:"ter"`                                     | solo layout 16:9                        |
| Cita de fuente      | `pruebas` (documento real); `fuente` solo va a la descripción               | **nuevo** sello "Source: …" en pantalla |

### 5.4 Miniatura y título (entregable de primera clase)

- Hoy no hay miniatura y la subida no la manda (`producir.py:244-250`). Plan: miniatura 1280x720 con la
  captura de `social.py` (172-273), con 2-3 variantes de miniatura y de título por vídeo.
- **Test & Compare** de YouTube: hasta 3 variantes, gana la de más tiempo visto; requiere funciones
  avanzadas ([oficial](https://support.google.com/youtube/answer/16391400)). El usuario aprueba las variantes.
- Puertas de la miniatura: texto ≤ 4 palabras, legible a 168x94 (OCR sobre la miniatura reducida) y sin
  promesas de "get rich quick" ([política de estafas](https://support.google.com/youtube/answer/2801973)).

### 5.5 Crítico que escala

Naive = ~1.900-2.300 s a 10 min. Propuesta (estimada): **~420-700 s** en la primera pasada y **~90-180 s**
al re-renderizar un capítulo:

1. **OCR disperso desde el plan:** `muestreo_previo` (`critico.py:337-367`) ya elige 1 fotograma por texto.
   Se pasa a 2 por texto, más pares donde dos textos se solapan, y 2 fps densos SOLO en la ventana que falle
   (el muestreo disperso dio 4 "no leídos" en 98 textos, de los que se confirmó como mucho 1).
2. **Una sola decodificación** en gris a 5 fps para ritmo, C1, dHash de P1 y detección de cambios (hoy hay 4).
3. Límite de hilos en `ocr_en` (`medir_texto.py:353`) y en `medir_cuadros.ocr_imagen` (209). Fuera los duplicados:
   Whisper dos veces, y ritmo y loudness dos veces.
4. Caché por capítulo (hash del trozo del plan + assets), al estilo de `clave_critico`.
5. Reglas long-form (PROVISIONAL, sin calibrar): promesa antes de 30 s, cambio visual cada ≤ 4-6 s,
   un re-gancho cada 45-90 s, 140-180 wpm, cortes de mid-roll en fronteras de capítulo con pausa ≥ 0,9 s
   y una hoja de contactos por capítulo.

Orden: el punto 1 primero (es lo que más rinde). Hasta tenerlo, el primer vídeo largo acepta ~25 min de crítico.

### 5.6 Puertas duras (lo que bloquea)

- Ya bloquean: `cifras` con URL y aviso YMYL (`construir.py:239-361`), `trazabilidad.sin_fuente`, `licencia_ok`
  (lista cerrada), contraste WCAG, lint, loudnorm y pausas de voz.
- **Hueco:** el punto 2.1 del PLAN (la cifra coincide con el texto de la fuente) NO es una puerta de máquina;
  solo lo cubre el juicio J3. Para 10 min, con decenas de cifras, se propone una puerta que baje la URL y busque el número
  (con tolerancia de formato) y bloquee si no aparece. Es lo único nuevo que bloquea.

### 5.7 Riesgo de "contenido inauténtico" [CONFIRMADO 18-nov]

La [política oficial](https://support.google.com/youtube/answer/1311392) desmonetiza lo hecho en masa con plantillas, lo
repetitivo entre vídeos y las **personas IA que dan consejo financiero como expertos humanos**.
Cómo evitarlo:

- Voz Kokoro **sin persona** ni nombre, explainer con fuentes y nunca "deberías comprar".
- Un vídeo por semana, cada uno con tesis, estructura y metraje propios. P1 parecido sigue midiendo la
  distancia entre vídeos del canal (aviso, y bloqueo solo si es casi idéntico).
- Valor añadido visible: datos reales con ejes reales, documentos reales (`pruebas`) y comentario propio, nunca leer
  una noticia ajena (política de contenido reutilizado).
- La [divulgación de contenido alterado o sintético](https://support.google.com/youtube/answer/14328491) se marca cuando
  hay escenas realistas generadas. Una línea "AI narration" en la descripción (suposición: no reduce el alcance).

## 6. Embudo e ingresos fuera del YPP [CONFIRMADO 18-nov]

- **Embudo:** cada long-form amplía el tema de un Short que retuvo (huang-exit, midterm-rally,
  ronald-wayne, jesse-livermore). Se hacen 2-3 Shorts nuevos por long-form, cortados de sus capítulos, con
  "related video" (a mano en Studio). El AIR (18.000 canales, correlacional) recomienda que los Shorts sean el 25-40 % de las subidas.
- **Correo:** Beehiiv gratis (2.500 subs, landing incluida, [oficial](https://www.beehiiv.com/pricing)). La lista se abre
  con el primer long-form. Como lead magnet, la hoja de datos de cada vídeo (las cifras con sus URLs ya existen).
  La cuenta la crea el usuario.
- **Afiliados que un canal nuevo puede conseguir:** TradingView (pago único de $10-400, sin mínimos,
  [oficial](https://www.tradingview.com/partner-rules/)), referidos de bróker (basta con ser cliente) y Amazon
  libros (4,5 %, exige 3 ventas en 180 días). Divulgación FTC en audio y en pantalla, y la casilla de
  [promoción pagada](https://support.google.com/youtube/answer/154235). El resto (Rocket Money, M1, Seeking Alpha…) cuando haya
  ~1.000 vistas/mes. Las cuentas las crea el usuario; nunca se automatizan.

## 7. Fases (cada una con su criterio medible y su efecto en ingresos)

| Fase                                | Qué                                                                                                                                                                                     | Criterio de "hecho" (medido)                                                                                                                                                                                                                              | Efecto en ingresos                                                              |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **F0** (0 código, ~1 h del usuario) | Confirmar Q1-Q6; POLITICA.md nueva; cuentas Beehiiv y TradingView; Shorts a 3/semana                                                                                                    | Política commiteada; landing de correo con URL; enlace de afiliado en la plantilla de descripción                                                                                                                                                         | Primera vía de ingreso que no depende del YPP                                   |
| **F1** MVP long-form                | `formato` + layout 16:9 de las escenas existentes, guion y voz por capítulos, lista de capítulos, miniatura 1280x720, límites de `guionista` por formato, puerta de cifra contra fuente | **1 vídeo de 8-10 min publicado**; puertas duras en verde; máquina ≤ 60 min por ronda; Shorts al píxel (tests `test_zona_segura` y regresión)                                                                                                             | Empieza a correr el reloj de las 8.000 h; mid-rolls listos para cuando haya YPP |
| **F2** Validar el formato           | 4 long-forms (1/semana) + 2-3 Shorts embudo por cada uno; escenas `comparacion` y sello de fuente                                                                                       | A los 14 días de cada uno: duración media vista, CTR de la miniatura, subs por 1.000 vistas frente a 1,4 de los Shorts. **Seguir** si la media de vistas ≥ 3 min y los subs/1.000 ≥ 3. **Revisar tema/miniatura (no el motor)** si < 100 vistas por vídeo | Mide si el long-form convierte mejor que los Shorts: decide dónde va la máquina |
| **F3** Velocidad                    | OCR disperso + decodificación única + caché por capítulo (§5.5)                                                                                                                         | Crítico de 10 min ≤ 12 min; re-render de 1 capítulo ≤ 3 min de crítico                                                                                                                                                                                    | Más vídeos por semana con el mismo tiempo del usuario                           |
| **F4** Monetizar                    | Afiliados extra con ~1.000 vistas/mes; fan funding con 500 subs + 3.000 h; YPP con 1.000 + 8.000 h                                                                                      | Primer pago de afiliado; solicitud al YPP                                                                                                                                                                                                                 | Ingresos de anuncios                                                            |

Lo que NO se hace (y por qué): render por segmentos y concatenación (la prueba muestra RAM plana y 1,8 s/s);
carrusel para el long-form; generador de posts de texto (regla vigente); un selector de modo en la UI.

## 8. Riesgos abiertos

- Todas las cifras de tiempo de 10 min son extrapolaciones de n=1 a 92 s.
- RPM de finanzas con un rango amplio ($2-40): el plan usa $5-15 como supuesto.
- El "related video" es manual: si se olvida, el embudo se rompe en silencio.
- El layout 16:9 es rediseño, no reescalado: es la mayor parte de F1.

## 9. Alternativas evaluadas (18-nov, GitHub + historial propio)

Detalle con estrellas, licencias y URLs: nota `alternativas-github.md` del grupo de sesiones.

- **Generadores faceless** (MoneyPrinterTurbo 144k★, MoneyPrinterV2, ShortGPT, short-video-maker): **ignorar**.
  Son clips de stock + TTS + subtítulos con plantilla, sin datos reales ni QA: justo lo que la política de
  inautenticidad desmonetiza, y la sanción cae sobre el canal entero.
- **Cambiar de framework** (Remotion, Revideo, Motion Canvas, MoviePy): **ignorar**. Remotion ya se descartó
  (`docs/V2-CALIDAD.md:39-41`) y ninguno publica s/s medidos; el único dato real es nuestro 1,83 s/s.
- **Lo que HyperFrames ya trae y no usamos → ADOPTAR en F1/F3:**
  1. `hyperframes check` para layout/oclusión (overflow, clipping, overlaps, `text_occluded`, `--range`).
     Hoy `producir.py:539` solo lee el contraste. Caza texto cortado antes del render.
  2. `render --start/--end` para re-renderizar **solo un capítulo** + `ffmpeg` concat-copy. Medir antes de adoptar:
     `--gpu` (NVENC) y `--workers` (en el Short, más workers fue ruido: `VELOCIDAD-PLAN.md:70-73`).
  3. `hyperframes lambda`/Cloud Run por chunks: solo si el render local de 10 min no alcanza (coste en la nube).
- **OCR guiado por la timeline** (§5.5): nadie lo publica, hay que montarlo nosotros (poco código). Considerar
  después, con medición: reconocimiento solo sobre recortes del DOM (`use_det=False`), detector a 960, onnxruntime-gpu.
- **TTS:** seguir con Kokoro. Chatterbox-Turbo (MIT) es el único rival comercial limpio, pero el repo está
  archivado: solo en prueba a ciegas. F5, XTTS, Higgs y Fish quedan fuera por licencia (ya en `docs/mejora/sonido/PLAN.md`).
- **Alineador:** ctc-forced-aligner (BSD-2) alinea el texto exacto sin ASR. Solo si se mide deriva en 10 min;
  la sincronía de los Shorts está resuelta.
- **Miniaturas:** no hay herramienta abierta creíble. Test & Compare de YouTube Studio + variantes propias (§5.4).

Corrección a §7: "render por segmentos" se mantiene fuera para la PRIMERA pasada, pero el re-render de un capítulo
con `--start/--end` entra en F3.
