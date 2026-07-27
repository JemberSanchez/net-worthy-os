# ESTADO DEL PROYECTO — documento de traspaso

> ## ▶ 2026-07-26 · #7 RONALD READ: guion técnico CERRADO y MP4 RENDERIZADO
>
> El Short #7 tiene las **22 frases decididas** (16 cambios de plano en 62,7s ≈ uno cada 3,9s) y
> sale del motor en MP4 H.264+AAC. **32 tests del motor** (eran 29) + **125 de Python**, verdes.
>
> ### Seis defectos que solo se vieron MIRANDO frames — ninguno daba error en consola
> | Dónde | Qué pasaba | Cómo se cazó |
> |---|---|---|
> | `pintarChecklist` | **Choque de nombres**: el motor ya tenía una función así (el checklist del PANEL). Dos `function` con el mismo nombre no dan error: la segunda gana en silencio y **el checklist del canvas salía en blanco**. | frame vacío |
> | `drawChecklist` | Los 3 ✗ se repartían sobre el TRAMO (6,8s) pero su plano dura 3,5s: **"NO TECH STOCKS" no llegaba a aparecer** — la voz lo decía y en pantalla no estaba. | frame t=9,05 |
> | subtítulos | Sobre las escenas-tarjeta se pintaba **el mismo texto dos veces**, superpuesto: "The machine, not" encima de "THE MACHINE.". | frames t=30,4 / 46,2 |
> | `text()` | El auto-ajuste a zonas seguras **se saltaba entero dentro de un `translate`** (medía la x LOCAL, que es 0 → hueco negativo). El **`$8,000,000` invadía 60 px** de la franja de botones. | test nuevo |
> | `text()` | Al encoger, el **`letterSpacing` no encogía**: 43 caracteres × 6 px = 258 px que no bajaban. El sub del CTA acababa en x=959 (el límite es 950) **después** de pasar por el ajuste. | test nuevo |
> | `drawSnowball` | Dos rótulos vivían en la capa MUNDO y **la cámara los arrastraba** bajo los botones. Ahora se encolan y los pinta el HUD. | test nuevo |
>
> `titulo` y `cita` tampoco usaban `localT`: declaradas por frase entraban **ya montadas y
> congeladas** (sin animación) hasta el corte siguiente.
>
> ### Tres tests nuevos que cubren el agujero que permitió todo esto
> El barrido de zonas seguras corría **sin calibrar** (sin `ULTIMA_CAL` el guion técnico ni se
> evalúa) y **paraba en t=32** de un Short de 62,7s: la mitad del video no se testeaba nunca.
> Ahora hay tres que cargan la voz real y barren el video entero — planos resueltos, ninguna LETRA
> en la franja de botones (medida con la matriz del contexto, vía el gancho `__auditText`), y
> **ningún plano en blanco** (el que habría cazado el choque de nombres).
> Para poder mirar dentro del motor desde el iframe hay `estadoMotor()`: `const SCENES` / `let CFG`
> viven en el scope de script y desde fuera **solo se ven las `function`**.
>
> ### ⚠ Trampa que costó una verificación falsa
> **`python -m http.server` cachea**: tras editar el HTML, el navegador seguía sirviendo el viejo y
> el guion "no se aplicaba". Recargar SIEMPRE con `?v=N` distinto antes de dar nada por verificado.
>
> ### 2ª RONDA (el usuario vio el video): "desfase leve de la voz con los subtítulos"
> Se midió en vez de opinar. **Las 44 tarjetas caen a 0,000 s del inicio de bloque de voz** que
> mide `segmentarVoz` sobre el MP3, y **el MP4 no añade retardo** (−4 ms comparando el onset del
> audio del MP4 con el del MP3 original, así que el AAC/muxer estaba descartado). El adelanto lo
> metían dos cosas nuestras:
> 1. **`LEAD` de subtítulos = 0,25 s.** El texto entraba un cuarto de segundo antes que su sonido.
>    Ahora **0,05** (dos frames, solo por el redondeo). Historial para no volver a subirlo a ciegas:
>    0,15 → 0,30 → 0,45 → 0,10 → 0,25 → **0,05**; las tres primeras subidas no hacían nada porque
>    el bug de `tarjetaEn` se comía la anticipación, así que la sensación de "van tarde" que las
>    motivó nunca llegó a probarse con un lead que funcionara.
> 2. **Las tarjetas de dos líneas aparecían enteras de golpe**, y la voz tarda 1-2 s en decirlas:
>    el rótulo se leía antes de oírse. Ahora cada línea entra con **su tarjeta de subtítulo**
>    (`tarjetasDelPlano`), emparejada **por CONTENIDO** — se busca la tarjeta que comparte palabra
>    con el elemento, no por índice (un plano puede tener 5 tarjetas y 2 ítems). Lo mismo para los
>    ítems de `bullets` y los ✗ del `checklist`: **cada ✗ cae cuando la voz dice su frase.**
>
> **Cuatro frames vacíos** (5,5 · 13,5 · 29,5 · 32,0) en los cortes: el plano se activa 0,2 s antes
> que su frase (`TOL_PLANO`) y sus elementos entraban con la frase → cada corte abría en negro.
> Y tres defectos de imagen más: el gancho se apagaba medio segundo antes de que entrara el
> checklist; el grado de color del tramo `payoff` volvía el fondo **marrón** (mezcla 0,14 → 0,07);
> y la bola quedaba como un disco gris detrás del CTA (`ctaDim` 0,82 → 0,90).
>
> ### ⚠⚠ LOS TESTS CORRÍAN CONTRA UNA VERSIÓN CACHEADA DEL MOTOR
> `tests-motor.html` cargaba el iframe con `src="short-renderer.html"` fijo, así que el navegador
> lo servía de su caché: **un "32 tests PASAN" podía ser sobre el código de antes de la última
> edición.** El `src` se asigna ahora por JS con cache-bust. Junto con la misma trampa en el
> renderer (`?v=N`), es el fallo de método más caro del día: invalida cualquier verificación hecha
> sin recargar de verdad.
>
> **33 tests** del motor (dos nuevos: barrido completo anti-frame-vacío en los cortes, y sincronía
> de cada tarjeta contra la voz medida) + 125 de Python.
>
> ### 3ª RONDA: "errores en el cambio de escenas" — hacía falta mirar FRAME A FRAME (30 fps)
> Un barrido a 0,2 s no ve un fallo de dos frames. Analizando los 1.882 frames aparecieron cinco
> defectos más, **todos en los cortes** y todos con la misma raíz: **la tolerancia con la que un
> plano se adelanta a su frase** (`TOL_PLANO`, 0,2 s) no estaba contemplada en nada de lo que vive
> dentro del plano.
> | Qué se veía | Causa |
> |---|---|
> | Entre dos tarjetas de título se colaba **0,2 s de la BOLA** | en los silencios del TTS ninguna frase está activa → la escena caía al fallback `CFG.escena`. Un silencio ya no cambia el plano |
> | **Dos frames en negro** donde el gancho debía seguir | `escenaPorGrupo` (tolerancia 0,25) y el guion por frase (0,20) se pisaban en la frontera. Se quitó el mecanismo por tramo: **o guion por frase, o reparto por tramo, no los dos** |
> | El contador del `stat` clavado en **"$0"** tras venir de $217.531 | `localT` restaba el inicio de la FRASE, no el del plano → reloj local negativo durante 0,2 s |
> | El subtítulo de la frase anterior **encima del plano nuevo** (al cortar del `stat` a la bola, "$8,000,000." justo bajo el "$8,000,000" del HUD) | el HOLD de 1,2 s cruzaba el corte |
> | `checklist` y `bullets` **abrían casi en blanco** viniendo de una pantalla llena | sus ítems entran uno a uno. Ahora la lista existe desde el primer frame en gris y la voz la **enciende** |
>
> **34 tests** (nuevo: ningún plano abre por debajo de 100 px de tinta — el corte que fallaba abría
> con ~40). Barrido final de los 1.882 frames: **0 vacíos, 0 flojos**. Quedan 4 saltos de brillo,
> revisados uno a uno: son los cortes duros entre una escena luminosa y una tarjeta oscura, que es
> lo que el montaje busca a propósito.
>
> ### 4ª RONDA (revisión exigente): categorías que NADIE había mirado
> Las tres primeras rondas miraron composición y cortes. Faltaban cinco familias enteras:
> | Categoría | Resultado |
> |---|---|
> | **Subtítulos vs guion hablado** (palabra por palabra) | ✅ 128 palabras, cobertura total. La única diferencia es la conversión deliberada "eight million dollars" → "$8,000,000" |
> | **Zonas seguras VERTICALES** (solo se probaban las laterales) | ✅ 0 violaciones |
> | **Solapes de texto** con cajas tipográficas reales (ascendente/descendente por tamaño) | ✅ 0 en todo el vídeo |
> | **Legibilidad**: tamaño REAL tras el auto-encogido | ⚠ el **aviso YMYL se encogía a 20,2 px**, por debajo del mínimo de 22 que el propio motor documenta. Se acortó el texto (quitando lo que no es advertencia) en vez de bajar el listón. Los rótulos de escena subieron de 20 a 24 px |
> | **Audio del MP4** | ✅ 0 muestras clipeadas, pico 0,64, sin silencios >1,2 s, cola muda 0,32 s |
> | **MOVIMIENTO entre frames** (un tirón no se ve en frames sueltos) | ⚠ **el subtítulo SALTABA de posición** al cruzar un corte: 632 px en t=9,3 y 856 px en t=52,9 |
>
> El salto del subtítulo venía de que su posición depende de la escena y se calculaba con la del
> frame ACTUAL: si la tarjeta seguía en pantalla cuando entraba el plano nuevo, se mudaba de sitio a
> mitad de lectura. Se extrajo `resolverEscena(t)` de `drawFrame` para poder preguntarla por el
> **arranque de la tarjeta**: cada subtítulo se queda donde nació.
>
> Barrido final de los 1.882 frames: **0 vacíos · 0 flojos · 0 solapes · 0 tirones · 0 fuera de
> zona segura**. 34 tests del motor + 125 de Python.
>
> ### 5ª RONDA · PESO: el MP4 baja de 74 a 43 MB **sin perder calidad** (medido)
> El motor pedía **24 Mbps** y el codificador solo usaba **8,8**: el contenido es gráfico sintético
> (fondos planos, texto vectorial, degradados) y H.264 lo comprime casi gratis. Se codificaron los
> 120 frames más exigentes —la bola con 95 partículas, con cámara y subtítulos— a siete bitrates,
> se **decodificaron** y se compararon píxel a píxel contra el canvas:
>
> | techo | real | PSNR | | techo | real | PSNR |
> |---|---|---|---|---|---|---|
> | 24 Mbps | 8827 k | 45,79 dB | | 4 Mbps | 3921 k | 45,38 dB |
> | 12 Mbps | 8692 k | 45,79 dB | | 2 Mbps | 1937 k | 44,90 dB |
> | 8 Mbps | 7143 k | 45,76 dB | | 1 Mbps | 958 k | 43,91 dB |
> | **6 Mbps** | **5475 k** | **45,68 dB** | | | | |
>
> **La calidad no depende del bitrate en este rango**: el techo de ~45,8 dB es del submuestreo de
> croma 4:2:0, no de los bits. De 24 a 6 Mbps se pierden **0,11 dB** (por encima de 40 dB ya es
> indistinguible). Verificado además MIRANDO: ampliación 2× del `$8,000,000` a 24/8/6/4/2 Mbps —
> sin ringing, sin bloques, sin banding. Y el archivo final contra el canvas en 12 keyframes:
> **PSNR 47,5-51,8 dB**. Se eligió 6 y no menos porque las plataformas recomprimen y conviene
> margen. Bonus: el render baja de ~150 s a **68 s**.
>
> ⚠ **Lo que NO se tocó y por qué**: la página ya pesa 278 KB y carga en **59 ms** sin ninguna
> dependencia — minificarla no se notaría y la dejaría ilegible. Y meterla en Docker no la haría
> más liviana: ya tiene la propiedad que da un contenedor (un archivo, cero instalación).
>
> ### 5ª RONDA — LA CAUSA REAL DEL DESFASE (no era un offset, era DISPERSIÓN)
> **`repararDuraciones` le robaba a la tarjeta siguiente su palabra `ancla`.** Una tarjeta corta
> crece robando palabras a la de al lado; si la robada es la PRIMERA de la siguiente y es un ancla
> (el instante que el micrófono midió como arranque de voz), esa tarjeta pasa a empezar en una
> palabra **interpolada**. Con `minDur` a 1,05 s el robo era sistemático.
> **Medido: solo el 34 % de las tarjetas conservaba su arranque medido; desvío medio 0,356 s y
> casos de 1,58 s TARDE.** Por eso los cinco ajustes de LEAD (0,15 → 0,45) nunca arreglaron nada:
> un LEAD mueve todas por igual y esto era dispersión.
>
> Tres arreglos, **en el motor** (valen para cualquier Short): no se roba un ancla · los
> sub-bloques de ~100 ms se usan también dentro de los tramos que eligen bloques gruesos ·
> alineamiento por **energía acumulada** (el conteo de picos subcuenta un 17 % de forma irregular).
> → **del 34 % al 66 %** de tarjetas sobre voz medida, desvío medio 0,356 → 0,261 s. El resto son
> tramos sin ninguna pausa detectable: ahí el tiempo es interpolado por narices.
>
> **Y lo que mata la sensación: PALABRA ACTIVA RESALTADA.** Con la tarjeta entera del mismo color
> el espectador no sabe por dónde va la voz: lee las tres palabras de golpe y oye cómo la voz las
> alcanza. Ahora la palabra que suena va en dorado, las dichas atenuadas, las pendientes al 45 %.
> El ojo sigue a la voz y un desvío de 150 ms deja de percibirse.
>
> **⚠ `tools/check_motor.mjs` — CORRER SIEMPRE TRAS EDITAR EL MOTOR.** Un error de sintaxis **no
> da error en consola**: el navegador aborta el script entero y las funciones globales quedan sin
> definir, así que la página "carga" y no hace nada. Ha pasado **dos veces** por un nombre ya
> declarado en otro punto del archivo (`pintarChecklist`, `reloj`). Node lo caza en 200 ms.
>
> **37 tests** (3 nuevos de sincronía, uno de ellos determinista sin audio) + 125 de Python.
> El MP4 bajó de 74 a **43,9 MB** como efecto colateral.
>
> ### ✅ DESFASE RESUELTO DE RAÍZ: alineador propio con reconocimiento de voz LOCAL
> **`python tools/alinear_voz.py read-janitor`** → `data/<voz>.align.json` con el t0/t1 REAL de
> cada palabra. El motor lo carga solo al pulsar «Usar la voz del proyecto»; si no está, calibra
> como siempre y no se rompe nada.
>
> - **`faster-whisper`** (CTranslate2, **sin PyTorch**, modelo `base.en` de 74 MB) transcribe con
>   timestamps por palabra. Local, gratis e **ILIMITADO** — a diferencia del .srt de CapCut, que
>   su plan gratuito solo deja exportar **2 veces al mes** y por eso nunca fue una opción real.
> - No nos fiamos de lo que Whisper *entendió*, solo de **cuándo lo oyó**: su transcripción se
>   alinea con el guion real por Needleman-Wunsch. **160 de 162 palabras (99 %) con tiempo medido.**
> - Si un timestamp del ASR cae en silencio, manda el arranque de voz de la energía. El ASR dice
>   QUÉ palabra y en qué orden; el micrófono, exactamente CUÁNDO empieza el sonido.
> - Con alineamiento: el ajuste heurístico se **desactiva** (corrige estimaciones, y ya no las hay)
>   y el LEAD baja a 0,08 s. **Resultado: desvío 0,000 s en las 45 tarjetas comparadas.**
>
> ⚠ **Correr el alineador ANTES de renderizar cualquier Short.** Sin él vuelve la estimación.
>
> ### Histórico: por qué el .srt de CapCut no servía

> Tras arreglar el robo de anclas, el reparto de las 50 tarjetas contra los arranques de voz
> medidos es: **33 a tiempo (±80 ms), 13 TARDE (media −0,73 s), 4 pronto.** Las 13 caen en tramos
> donde **la voz no hace ninguna pausa detectable**, así que su tiempo se ESTIMA por fuerza. Ningún
> ajuste de LEAD las arregla: un LEAD mueve las 50 por igual y esto es dispersión.
>
> **La ruta que elimina la estimación ya está construida y sin usar:** panel → *«2 · Carga el .srt
> de CapCut»*. CapCut genera los subtítulos con **reconocimiento de voz real sobre el audio**, así
> que trae tiempos medidos por frase en vez de repartidos. Se exporta desde el mismo proyecto donde
> se generó el TTS (Subtítulos automáticos → Exportar). Desde hoy el .srt también alimenta el
> resalte de palabra (`tw`).
> **Mientras no se use, el desfase de esos tramos es irreducible.** No volver a tocar el LEAD.
>
> ### Pendiente (lo de siempre: el progreso son filas, no commits)
> Publicar el #7 → `record-dna` + `record-outcome` = **7/10**. `production_cost` sigue en 0 filas.
> Y la captura sigue parada desde el 15-jul: **`/daily` antes de volver a usar `decide`**.

> ## ▶ ESTADO REAL 2026-07-24 (verificado contra la DB, no contra los docs)
>
> Los bloques de abajo quedaron desfasados: afirmaban **2/10 instrumentados y 0 medidos**. Medido
> hoy con `dna` + consultas directas a `omega.sqlite`:
>
> | | Real |
> |---|---|
> | Instrumentados (`production_dna`) | **5 de 10** del hito |
> | Medidos (`production_outcome`) | **4** |
> | `production_cost` | **0 filas** — el rendimiento/hora nunca llegó a existir |
> | Tests | **104 verdes** (corridos, no citados) |
>
> **Convención de score confirmada en código:** `success = vistas_totales(FB+YT) / 750`.
>
> ### ✅ #6 Buffett CERRADO en el moat (6/10 instrumentados, 5 medidos)
> Re-medido a 7 días el 24-jul: **FB 245 + YT 11 = 256** → `success = 0.341`. Queda **2º de 5**,
> entre S1 (0.373) y S2 (0.303). Retención media **11%** (5,9s sobre 55s de video).
>
> ⚠ **Corrección de una hipótesis que estuvo escrita aquí y era FALSA.** Este doc llegó a decir que
> "230 vistas en 17h contra 280 en 28d es rendimiento muy superior". **No lo era.** Contra el
> baseline de 17h (244 vistas · 59 de 3s · 24m01s), a los SIETE DÍAS sumó **+1 vista y +3 segundos**.
> El video no estaba acelerando: **flatlineó**. Facebook lo testeó, midió 5,9s de atención media y
> cortó la distribución. Lección transversal: en Reels **el veredicto llega en las primeras ~17h**;
> una ventana corta no subestima nada, ya es casi el número final.
>
> **Primera curva de retención del canal** (guardada en `production_context.medicion_2026_07_24`):
> **24,1% a los 3s → 10,0% a los 20s → 11% medio.** El gancho es el mejor del canal (récord de
> vistas de 3s) y aun así **se cae entre los 3s y los 20s**. Segundo dato independiente que apunta
> a lo mismo que `docs/EXPERIMENTO-RITMO.md`. Ahí está el problema, no en el gancho.
> (`reproducciones_1min = 0` es ESTRUCTURAL — el video dura 55s — no una señal de fracaso.)
>
> ### 🔴 Sigue fuera del moat
> - **#7 Ronald Read** (escena PORTFOLIO, commits del 18-jul): montado en el motor, **cero filas en
>   la DB**. Sin publicar o sin registrar.
> - **`production_cost` sigue vacío** en los 6: el rendimiento por hora no existe todavía.
>
> ### 🔴 La captura de datos está PARADA
> - Último `ingest`: **2026-07-15**. Últimas `signals`: **2026-07-12**. Van ~10 días sin observar.
> - Consecuencia directa: `decide` opera sobre un corpus congelado. **Correr `/daily` antes de
>   volver a decidir un tema.**
>
> ### ✅ Deuda epistémica saldada (hoy): predicciones #15-#18 → `inconclusive`
> Vencieron el 23-jul. **NO se refutaron: falló el instrumento, no la hipótesis.** Dos causas
> independientes, ambas verificadas:
> 1. **Hueco de datos:** horizonte 09→23-jul, pero `signals` murió el 12-jul → solo **3 de 14 días**
>    con datos.
> 2. **El extractor cambió DENTRO del horizonte:** `theme v0.2.0` (hasta 09-jul) → `v0.2.1` (desde
>    12-jul). La línea base y la medición final usan **reglas distintas**. Eso explica el falso
>    misterio de `'justin verlander'` **19 → 0**: v0.2.1 simplemente ya no produce ese tema tras el
>    arreglo del feed deportivo — no fue una caída de demanda.
>
> ### ⚠ GAP METODOLÓGICO DESTAPADO (decisión pendiente, NO implementado)
> Una predicción **no registra bajo qué versión de extractor se creó**, así que el sistema puede
> verificarse a sí mismo con una regla distinta a la que usó para la línea base — y llamarlo
> aprendizaje. Es una limitación **revelada por uso real**, no especulativa (que es lo que
> `POLITICA.md` exige para tocar código). El arreglo mínimo sería sellar `extractor_version` en la
> predicción y que `resolve-prediction` avise si cambió. **Consultarlo con el usuario antes de
> construirlo.**
>
> ### Siguiente paso sugerido
> Cerrar Buffett (re-medir 28d → `record-dna` + `record-outcome`) = 6/10. Luego #7 Read = 7/10.
> Sigue vigente: progreso = **filas del dataset**, no commits.

> ## PLAN DE MAÑANA 2026-07-17 (SUPERADO por el bloque de arriba — histórico)
>
> **1. S1 → Instagram Reels + TikTok.** La jugada de mayor valor y coste CERO: es el mejor activo
>    del canal (221 espectadores, evergreen, `story=character`) y **nadie lo ha visto ahí**; los
>    dos perfiles llevan vacíos desde el 07-16. (TikTok sigue con el perfil incompleto: Nombre
>    "Net Worthy" ⏰ candado 7 días, foto, bio — y conectar YouTube desde la APP móvil.)
> **2. HOUSING (tribunal) → YouTube + Facebook.** Le falta SOLO la voz: `docs/guiones/TTS-housing.txt`
>    → CapCut Firme Pilot → `data/voz-short-housing.mp3`. El motor calibra el resto solo.
> **3. 🔴 MEDIR RETENCIÓN de los dos.** No vistas: la CURVA (Studio + panel de FB). Van 4 Shorts
>    publicados y **0 con retención registrada** — es la variable que decide la distribución y la
>    única que explica el PORQUÉ. `retention_by_block` está vacío en los 4.
>
> **Por qué el housing sale aunque `decide` lo mande al último (0.570) y sea NOTICIA** (la
> categoría que en 39 despegues ajenos no aparece ni una vez): **el FED también es noticia**, así
> que boletín-noticia vs tribunal-noticia es una comparación **LIMPIA del tratamiento** — la
> categoría está controlada en ambos. **Expectativa honesta: el housing puede ganar al FED por
> goleada y aun así hacer ~40 vistas.** Sería una victoria INFORMATIVA (el molde tribunal
> funciona), no de negocio. Si el molde aguanta → Caso #002 sobre un tema EVERGREEN, que es donde
> hay techo. **No esperar una explosión: ningún canal de la muestra explotó en su 5º vídeo.**
>
> **Después: WARREN BUFFETT** — personaje + evergreen + (si el molde aguanta) tratamiento tribunal.
> Es donde convergen las 5 señales del día: `decide` limpio (0.658, único sobre el umbral), el ADN
> propio (el único `story=character` es el mejor Short), los outliers reales (clips de Dave Ramsey
> x1.000 y SHAQ x705) y `docs/VIRALIDAD.md`.
> ⚠ Antes de producirlo: **verificar el ruido indio** en la demanda de 'warren buffett' — el
> ejemplo top del scan es *"Rakesh Jhunjhunwala - India's Warren Buffett"*. Mismo patrón que el
> ruido de 'share market' que ya se limpió. Si la mitad del scan es de India, la demanda es un
> espejismo.
>
> ## 📊 2026-07-16 (noche) — **`docs/VIRALIDAD.md`: casi todo lo que creíamos del formato es FALSO**
>
> Primer estudio con datos AJENOS (543 Shorts EN de finanzas por API, n útil 39). **Léelo antes de
> proponer cualquier cambio de formato.** Lo valioso son los NEGATIVOS:
> **la duración NO predice nada** (parecía 57s vs nuestros 30s → era CONFOUNDER del tamaño del
> canal; dentro de canales pequeños 31-36s vs 38s, y los despegues van de **17s a 130s**) ·
> **el título casi no distingue** · **"más escenas/más producción" no aparece**: el mejor de la
> muestra hizo **25,5M con 26.800 subs en 17 SEGUNDOS**, y otro 9,8M con 3.890 subs en **6s**.
> Corrobora el dato propio: el FED es el Short más producido del canal y el peor.
>
> **Lo que SÍ:** **ninguno de los 39 despegues es NOTICIA** (edades 133-352 días, siguen
> acumulando = evergreen) — y `youtube-scan` usa `publishedAfter=30d`, así que **el evergreen es
> invisible para `decide`**. Tres formatos despegan y **el boletín no es ninguno**: clip de persona
> real · demo visual/challenge · explicador con la promesa desnuda en el título. Benchmark de
> engagement: **likes/vista 1%-3,7%**. Reproducible: `research/viral_collect.py` + `viral_compare.py`.
>
> **El cerebro, arreglado hoy (3 bugs medidos, 104 tests verdes):** el RPM lo decidía un **título
> ajeno** ('housing' heredaba $70 por la palabra "Mortgage" de otro canal) → ganaba `decide`;
> **la abstención era inalcanzable** (umbral 0.50 = confianza base exacta); y **un término nuevo
> compraba el primer puesto** (+0.400 por ruido de muestreo, con 1.000 vistas igual que con
> 700.000). Perfil de **fase CRECIMIENTO**: monetization 0.30→0.10, demand 0.30→0.45 —
> **⚠ REVERTIR cuando haya audiencia**. `decide` limpio ahora: **`warren buffett` 0.658** (único
> sobre el umbral), housing cae a 0.570.
>
> **⚠ LEE PRIMERO `docs/AUDITORIA.md` (2026-07-15):** juicio profesional del proyecto. Resumen:
> motor potente, cerebro DORMIDO — 3 videos publicados y `production_outcome`=0. La mejora #1 no es
> otra feature: es CERRAR EL LOOP (registrar analytics+outcome) + volumen/cadencia + distribución.
>
> **Para el nuevo chat:** lee este archivo entero antes de tocar nada. Luego `CLAUDE.md`,
> `docs/POLITICA.md` y `docs/VISION.md`. Ruta: `C:\Users\Asus\Desktop\Proyecto AI`
> (repo git, rama `master`). Hay memoria en `~/.claude/projects/.../memory/` que se carga sola.
>
> ## 🎬 2026-07-16 (tarde) — EL SALTO CREATIVO: **el housing ya NO es un boletín, es un TRIBUNAL**
>
> **La corrección del usuario que cambió el rumbo (hazle caso, tenía razón):** llevábamos horas
> puliendo la EJECUCIÓN (niveles de audio, sync, zonas seguras) de un formato que es **un boletín de
> noticias con tipografía bonita** (gancho → 3 bullets → número → CTA). Lo hace todo canal de
> finanzas. Y el dato lo confirma: **el mejor Short del canal (S1, 259 vistas FB) es el ÚNICO que
> cuenta una historia**; FED y housing eran más boletines. También dijo, con razón, que **la voz
> CapCut le gusta y no es el problema** — yo insistía en ElevenLabs; el problema era el ENCUADRE.
>
> **La maquinaria de diferenciación YA EXISTÍA sin usar:** `combinator.py` tiene 12 tratamientos
> (documental, terror, anime, thriller, noir, atraco, comedia, cuento, naturaleza, **tribunal**…) y
> el CKB tiene `novel_combination`, `pattern_break`, `humor_absurd`, `series_potential`.
>
> **HOUSING = `TRIBUNAL` (Caso #001: "The People vs. Your Rent").** Elegido evaluando los 12 contra
> las restricciones reales: **YMYL** (un tribunal presenta PRUEBAS y decide el jurado → *el formato
> ES el disclaimer*) · **no humillar** (el espectador es el **JURADO**, no el acusado; se acusa al
> MERCADO — por eso se DESCARTÓ el documental de naturaleza: ahí el espectador es el animal
> observado = condescendiente) · **credibilidad** (toma prestada autoridad) · **voz** (Firme Pilot =
> fiscal, coste cero) · **engagement** (el CTA ES el veredicto: un ROL, no una petición).
> Línea clave del banquillo: **"You are not on trial here. The market is."**
> Hechos IDÉNTICOS y corroborados. El humor está en el ENCUADRE, nunca en los datos.
>
> **✅ GANCHO RESUELTO (2026-07-16, decisión del usuario) — `EXHIBIT A: / YOU'RE PRICED OUT`.**
> El anterior ("THE PEOPLE vs. YOUR RENT") era intriga cerebral y tardaba ~2s; su rival del
> experimento (el FED, "YOUR SAVINGS ARE LOSING") es pérdida primal en 1s. Con ganchos desiguales el
> viernes NO se podría separar el tratamiento del gancho. Ahora el gancho ES la prueba A (el cargo)
> → visceral sin salirse del juicio. **La evidencia se renumeró a B/C** (dos "Exhibit A" distintos
> romperían el marco). Verificado: 19 tests del motor + frame del gancho renderizado y MIRADO.
> Commit `b7074f4`. **Ya NO queda ninguna decisión abierta: el housing depende solo de la VOZ.**
>
> **EL EXPERIMENTO DEL VIERNES, ahora sí interesante:** FED (boletín) vs HOUSING (tribunal) — misma
> voz, misma calidad técnica, mismo canal. La pregunta ya no es "¿qué gancho?" sino **"¿ser distinto
> compensa?"**. Si el tribunal despega → molde replicable (`Caso #002: El Pueblo vs. Tu Tarjeta`).
>
> **HOUSING: le falta SOLO la VOZ.** Guion listo para pegar en CapCut (Firme Pilot, de una toma):
> **`docs/guiones/TTS-housing.txt`** → guardar como `data/voz-short-housing.mp3`. Al cargarla, el
> motor calibra TODO solo (cortes, subtítulos, cadencia, sync del ~6.5%, gain de música).
> La fuente de verdad del guion es `SHORTS['housing-catchup'].guion.grupos` en `short-renderer.html`;
> `TTS-housing.txt` es una copia para pegar — **si cambias uno, cambia el otro**.
>
> ### Motor — lo que se automatizó hoy (todo verificado, 19 tests verdes)
> | Antes (a mano) | Ahora (solo) |
> |---|---|
> | Volumen de música a oído | **auto-gain** a −20 dB bajo la voz, **independiente de la pista** |
> | Calcular cuándo aterriza el número | **auto-sync** sobre la palabra hablada (+ el golpe de sonido) |
> | Cadencia de bullets fija | **derivada** de la ventana (mató 8s de pantalla congelada → 2.89s) |
> | Texto que se salía de pantalla | **auto-ajuste** en `text()` (embudo de TODO el texto) |
>
> Además: música con **ducking** (suena también en previsualización), **sonido sincronizado a
> eventos** (tick por bullet, riser, golpe), **fondo vivo** (drift), **iconos vectoriales
> semánticos**, stat con **decimales**.
>
> **🔴 BUG CAZADO EN UN VIDEO PUBLICADO:** el `?` de "WITH $50 A MONTH?" del **S3** caía bajo los
> botones de Shorts (los 130px derechos). Causa raíz: el CTA usaba `maxW = W*0.86` asumiendo
> márgenes SIMÉTRICOS, pero SAFE es asimétrico (izq 70 / der 130). **Ya arreglado** — importa porque
> el S3 se re-renderiza para IG/TikTok. Lo cazó el **test**, no el ojo.
>
> ### Tests del motor (NUEVO) — `docs/guiones/tests-motor.html`
> 19 verdes. Página autocontenida (iframe + aserciones, **sin Node ni dependencias**). Ábrela por
> `http://localhost:8765/docs/guiones/tests-motor.html`. Cubre auto-gain, mezcla/ducking,
> eventosSonido, autoSyncStat, cadenciaBullets, determinismo de `drawFrame`, y un **barrido de zonas
> seguras** por los 5 Shorts frame a frame. **Corre esto antes de tocar el motor.**
>
> ### Distribución (nuevo hoy)
> - **Instagram** `@networthytv`: creado, **profesional**, perfil listo, **vinculado a la Página** vía
>   Meta Business Suite → se puede publicar a FB+IG a la vez ("Crear reel").
> - **TikTok** `@networthytv`: creado pero **perfil INCOMPLETO**. Falta: Nombre → **"Net Worthy"**
>   (⏰ candado de 7 días), foto (logo), bio. Y **desde la APP MÓVIL**: Editar perfil → **Social** →
>   conectar **YouTube** (← el negocio) e Instagram. Sin mínimo de seguidores. NO pasar a Business
>   (pierde música). Facebook: no tiene enlace nativo, saltar.
> - **Música**: `data/Musica.mp3` = *Corporate Ambient Piano* (Rockot, Pixabay CC0). La M mayúscula
>   NO importa en Windows (verificado: el fetch la encuentra).
> - **Plan**: re-renderizar S1/S2/S3 con el motor de hoy y subirlos **uno por día** a IG/TikTok
>   (nunca los han visto) → siembra los perfiles + construye cadencia, sin producir nada nuevo.
>
> ### Monetización — verificado, la estrategia es CORRECTA
> - **TikTok Creator Rewards: NO disponible en Colombia** (depende de dónde estás TÚ, no del idioma
>   ni de la audiencia). Da igual: paga céntimos. **TikTok es distribución, no ingreso.**
> - **YouTube YPP: SÍ (195 países, Colombia incluida)** y **el RPM lo marca dónde está tu ESPECTADOR**
>   (CPM EE.UU. ≈ $32). Contenido EN + audiencia gringa + cobrar desde Colombia = **la jugada correcta**.
> - El dinero real: **long-form de YouTube + marcas** (las marcas no dependen de país). Shorts = embudo.
>
> ---
>
> ## 🔴 2026-07-16 — FED PUBLICADO. LO ÚNICO QUE IMPORTA: **MEDIRLO EL VIERNES 18/07**
> **4º Short PUBLICADO** hoy 10:55am local (15:55 UTC), franja sana:
> ref `fed-savings-catchup-2026-07` · [YT nT8V0JHKD-M](https://youtube.com/shorts/nT8V0JHKD-M) ·
> [FB](https://www.facebook.com/share/r/1DPe5fKhxi/) · título *"Is Your Cash Earning 4% — Or Zero?"*
> ADN instrumentado (`hook=shock`, 9 bloques, 32s) + contexto completo. Baseline verificado: 0 vistas.
>
> **⚠ EL VIERNES 18/07 (48h):** `record-analytics` + `record-outcome` + `dna`. Las vistas de YouTube
> salen por API sola: `youtube.video_stats(['nT8V0JHKD-M'])`. Las de Facebook las copia el usuario.
>
> **⚠ AVISO DE ATRIBUCIÓN (está en `production_context`):** el FED estrena **4 variables nuevas a la
> vez** — música, sonido sincronizado a eventos, fondo vivo y sync del número. S1/S2/S3 no llevan
> ninguna. Si rinde distinto, la causa puede ser **cualquiera de las 4 + el tema + el gancho**. n=1:
> NO atribuir a una sola cosa.
>
> **Motor — capacidades de producción nuevas (todas verificadas, 7 commits, ya en el remote):**
> música de fondo con **ducking sidechain** (`data/musica.mp3`, se oye también en previsualización) ·
> **sonido sincronizado a eventos** (tick por bullet, riser al stat, golpe cuando el número aterriza) ·
> **fondo vivo** (drift del glow) · **iconos vectoriales semánticos** en bullets · stat con **decimales** ·
> sync del stat calibrado a la palabra hablada.
>
> **Siguiente Short en cola: HOUSING** (`housing-affordability-catchup-2026-07`, tema por datos: RPM $70).
> Montado y verificado visualmente; **le falta la VOZ** (guion de 2 bloques en `docs/guiones/`, CapCut
> Firme Pilot → `data/voz-short-housing.mp3`). Al tenerla: calibrar su `conteo_s` como se hizo con el FED.
>
> ---
>
> **Última actualización: 2026-07-15 (loop cerrado).** Estado en una línea:
> *TRES Shorts PUBLICADOS (S3 stat 07-10 02:00 · S1 story 07-11 11:30 · S2 contrarian 07-12 10:58,
> misma voz Firme Pilot). Facebook: S1 259 vistas/3 int · S2 218/1 · S3 67/1 (S3 confundido por la
> hora 02:00). **✅ LOOP CERRADO: `production_outcome` = 3 filas** — medido en YT+FB (YT 22/21/9 ·
> FB 67/259/218), `success = alcance_total(FB+YT)/750` → S1 0.37 · S2 0.30 · S3 0.12, `dna` ya
> calibra (PROVISIONAL, n=1). **Hallazgo: las plataformas se contradicen** (FB story≈contrarian≫stat;
> YT stat≈story≫contrarian), ~10x más alcance en FB que en YT; el gancho stat queda EXONERADO (mejor
> en YT). El próximo Short está LISTO: 'FED' (catch-up), voz en `data/voz-short-fed.mp3`, calibrada —
> **se publica MAÑANA 2026-07-16 entre 9:00 y 11:30am (hora local, UTC-5)** — franja sana comparable
> con S1/S2. Motor: 24 Mbps + sfx procedural + calibrador robusto. Las 4 voces reales en `data/`
> (gitignored).*
>
> **🛡 AUDITORÍA DE INGENIERÍA (07-15, `docs/AUDITORIA-INGENIERIA.md`):** veredicto — la arquitectura
> es correcta y NO debe evolucionar, debe PROTEGERSE. Implementado: comando **`backup`** (zip fechado
> del moat: SQLite consistente + voces + JSONs → `backups/`, gitignored; **copiarlo a nube/USB es del
> humano**), `status` muestra predicciones vencidas + **`resolve-prediction`** (cierra el ciclo
> epistémico del kernel), filtro anti-autobombo de canales en la demanda, guards de entrada,
> `http.server` ya no se expone a la LAN. **⚠ PENDIENTE HUMANO: crear repo remoto privado y
> `git push` — el código sigue viviendo en UN solo disco.** 98 tests verdes.
>
> **✅ PRIORIDAD #1 (cerrar el loop) — HECHA el 2026-07-15.** Registrados los 3 outcomes + analytics
> (vistas). De paso se cazó y arregló un bug: `production_analytics` en la BD no tenía columna `views`
> (esquema viejo; `CREATE TABLE IF NOT EXISTS` no migra) → `init()` ahora migra idempotente, +2 tests
> (94 verdes), commit `4981900`. El S2 no tenía DNA: registrado.
> **Pendiente para enriquecer:** CTR/retención por bloque desde YouTube Studio (fracción 0..1) y
> horas reales de trabajo por Short (`record-cost`). **Siguiente prioridad:** volumen/cadencia (1/día
> misma hora) + distribución (TikTok/IG Reels) + arreglar `decide` (ruido de nombres de fuente).
> Detalle: `docs/AUDITORIA.md`.

---

## 1. Qué es
Sistema que decide **QUÉ** contenido crear (por datos: demanda + dinero) y acumula **qué funciona**.
NO es un generador de video — el video es el primer producto, el activo es el conocimiento calibrado.
Nicho: **finanzas/inversiones/crypto, faceless, audiencia EN**. Canal: **Net Worthy** (@networthytv).

## 2. El reparto mental (lo más importante)
```
SISTEMA decide QUÉ (tema, por demanda+RPM)  →  TU CLAUDE piensa CÓMO (ángulo estructurado)
                                            →  SISTEMA acumula QUÉ FUNCIONA (record-outcome)
```
Regla dura (memoria [[raw-term-is-que-not-video]]): un término del detector ("build wealth") es
una **señal de demanda, NO un video**. Estructurarlo siempre + aviso YMYL.

---

## 3. ⚠️ LO ÚNICO QUE IMPORTA AHORA
El Short #1 se publicó. **`production_outcome` sigue en 0 filas.** El moat no se llena al publicar,
se llena al **medir**.

**Sábado 2026-07-12** (48h), con YouTube Studio y Facebook abiertos:
```
python -m omega.cli record-analytics    # ctr/avd/retención como FRACCIÓN 0..1, NUNCA %
python -m omega.cli record-cost         # horas REALES del usuario
python -m omega.cli record-outcome build-wealth-short-03-stat <0..1>
python -m omega.cli dna
```
`data/production_analytics.json` y `data/production_cost.json` ya existen con ceros y con el aviso
del formato. **Si el usuario escribe `4.5` en vez de `0.045`, el comando lo rechaza** (guard añadido).

Las **vistas/likes/comentarios** se pueden sacar por API sin copiar nada:
```python
from omega.sources import youtube
youtube.video_stats(['HMkPACqdvV8'])
```
CTR y retención **no son públicos**: solo en Studio. Eso lo copia el usuario.

> ⚠️ **CONFOUNDER ANOTADO.** Se publicó a las **02:00 hora local (UTC-5)** y la audiencia es EN/US.
> Si la velocidad inicial es baja, puede ser la HORA, no el gancho. **No lo atribuyas a
> `hook_type=stat`.** Está guardado en `production_context`. Es la Regla 3 de POLITICA.md.

---

## 4. El video publicado
| | |
|---|---|
| `production_ref` | **`build-wealth-short-03-stat`** |
| Publicado | 2026-07-10 · 07:00:32 UTC (02:00 local) |
| YouTube | https://youtube.com/shorts/HMkPACqdvV8 (id `HMkPACqdvV8`) |
| Facebook | https://www.facebook.com/share/r/1CiuGzWcRV/ |
| Archivo | MP4 H.264+AAC · 1080x1920 · 30.00 fps exactos · 24.03s · 13 MB |
| ADN | `hook=stat, story=none, cta=comment`, 7 bloques |
| Voz | CapCut TTS "Firme Pilot" (`data/voz-short-03.mp3`, gitignored) |
| Música | **ninguna** |

Todo el contexto (motor de voz, motor de visuales, fps, confounder, URLs) está en la tabla
`production_context`, escrito con `omega.creative.decisions.record_context` — una API que ya existía.

---

## 5. EL MOTOR DE VIDEO — `docs/guiones/short-renderer.html`
Un solo HTML, sin dependencias, se abre con doble clic. **Genera el Short entero**: intro, curva
compuesta, número dorado, CTA y subtítulos quemados, con la voz incrustada. **No hace falta CapCut.**

**Desde 2026-07-10 es MULTI-SHORT** (selector arriba): cada Short es un bloque en `SHORTS[...]` con
su `escena` (`chart` = curva del S3 · `columns` = dos columnas del S1), su `voz` (`data/voz-short-NN.mp3`),
su guion y su CTA. La escena `columns` narra SPENT vs OWNED con monedas por las ramas, año corriendo,
conteo al millón, fuga y chispas — **todo determinista** (`drawFrame` sigue siendo pura: verificado
por comparación de píxeles). **Desde 2026-07-10 (tarde) hay COMPOSITOR MULTI-ESCENA**: un Short tiene
una escena base + `overlays[]` componibles (portada, cierre) que se funden por alpha sin tocar el
interior de la base. El S1 estrena una **portada** ("TWO MEN. / SAME SALARY.") que se disuelve en las
columnas. Escenas registradas: `chart`, `columns`, `titulo`, `outro`. Arquitectura completa y ruta a
long-form (8-10 min) en **`docs/ARQUITECTURA-MULTIESCENA.md`** — el cuello de botella no son las
escenas (ya están) sino memoria (ffmpeg + render por segmentos), voz por segmento y layout horizontal. Hay un **checklist de producción que se marca solo** (voz → calibración →
previsualización entera → MP4). Guards añadidos tras auditoría: sin voz o sin cortes medidos no se
graba (ahora también en el camino MP4), el audio decodificado se suelta al cambiar de Short (antes el
S1 habría salido CON LA VOZ DEL S3), la calibración manual del S3 solo se aplica si el S3 está activo,
y el `.srt` deriva los cortes del guion activo (ya no está cableado al S3).

```
1. Servirlo por http (el botón "Usar la voz del proyecto" hace fetch y file:// lo bloquea):
   .claude/launch.json ya tiene un servidor estático -> http://localhost:8765/docs/guiones/short-renderer.html
2. "🎙 Usar la voz del proyecto" -> carga data/voz-short-03.mp3 y calibra
3. "⏺ Grabar y descargar el Short" -> MP4 listo para subir. ~1 min. Puedes cambiar de pestaña.
4. "⬇ Frame final" -> PNG del número dorado (miniatura YT + portada FB)
```

### Datos vs motor
`SHORTS['s3-stat']` contiene **todo** lo que define un Short: `spec` (3 líneas de la intro), `cta`,
`pmt/years/rate`, y un `guion` con:
- `grupos[]` — el texto **hablado**, partido en bloques narrativos. **Sus arranques SON los cortes.**
- `cifras[]` — spans hablados → token que se pinta (`"a hundred and eighty thousand dollars"` → `"$180,000"`)
- `subtitulos[]` — qué grupos llevan subtítulos
- `curvaLlegaEn` — la curva termina cuando la voz acaba de decir esa cifra
- `omitirEnSubtitulos[]` — muletillas que se oyen pero no se escriben

El resto del archivo es motor y **no se toca por Short**.

### Calibrador automático (lo más valioso)
Dado el MP3 + el guion, deduce solo los cortes, el spec drop y los subtítulos:
1. segmenta la voz por energía (RMS 10 ms, silencio ≥250 ms)
2. reparte los grupos entre los segmentos con **programación dinámica** (el mapeo 1:1 es FALSO:
   en el S3 exigía 11.1 sílabas/s en un bloque)
3. dentro de cada grupo alinea palabra a palabra sobre el tiempo de **voz real**, saltándose las
   pausas → la deriva no se acumula

**Verificado:** contra `voz-short-03.mp3` reproduce **exactamente** lo que se calibró a mano —
cortes `5.94 / 12.80 / 15.99 / 22.44`, spec `[-0.30, 2.15, 4.41]` y **11 de 11 subtítulos idénticos**.
Método completo en `docs/guiones/calibracion-voz-short-03.md`.

El S3 (ya publicado) usa su calibración manual; no se re-renderiza lo que está en la calle.

### Exportador MP4
`MediaRecorder` **no sirve**: `isTypeSupported('video/mp4')` devuelve `true` y luego produce **0 bytes**.
Y **Facebook no acepta WebM** (su lista oficial: mp4, mov, mkv, avi, ogv… sin webm).
Por eso el MP4 se construye a mano: `drawFrame(t)` es pura → render offline frame a frame →
**WebCodecs** (`VideoEncoder` H.264 + `AudioEncoder` AAC) → **muxer ISO BMFF escrito a mano**
(`ftyp | mdat | moov`, orden que evita el huevo-y-la-gallina de los offsets `stco`).
Regalo: 30 fps exactos, cero frames perdidos, y no depende de `requestAnimationFrame` (se puede
cambiar de pestaña; el yield usa `MessageChannel`, no `setTimeout`, que se estrangula en background).

---

## 6. ZONAS SEGURAS (no las muevas sin medir)
```js
SAFE = { top: 190, bottom: 360, left: 70, right: 130 }   // sobre 1080x1920
```
YouTube Shorts tapa los **350 px inferiores** (canal/título/música) y **120 px** a la derecha.
Facebook Reels, ~290 px abajo. El `$429,985` y el aviso YMYL **estaban dentro de esa franja** y no se
veían. Hay un interruptor "ver zonas seguras" en el renderizador para comprobarlo a ojo.

---

## 7. CIFRAS VERIFICADAS (tres eran falsas)
| Cosa | Estaba mal | Correcto |
|---|---|---|
| Gap del compuesto | $420,000 | **$429,985** ($609,985 final, no ~$600k) |
| Convención | ambigua | **7% nominal capitalizado mensual** ($500/mes × 360) |
| El café | "$18,000 invertido" | $18,250 es el ahorro **SIN invertir**; invertido: **$26,323** |
| S&P 500 | "9,5%" | ~10,4–10,7% **nominal** · ~6,5–6,8% **real** desde 1957 |

**Regla YMYL:** si dices "10% histórico" tienes que decir "≈7% tras inflación", o el número final no
cuadra. Y **nunca** llamar al S&P "sólido" o "seguro": cayó **-57%** en 2007-09.

---

## 8. VOZ — estado real
- **Ahora se usa CapCut TTS** (voz "Firme Pilot"). Gratis, uso comercial según CapCut.
- **ElevenLabs está APLAZADO**, y por dos razones verificadas:
  1. su **plan gratis no da derechos comerciales**, y los derechos se conceden **AL GENERAR**
     (lo hecho en gratis no se legaliza pagando después). Hace falta Starter ($5/mes).
  2. sus voces **Default (Brian, Adam, Antoni…) EXPIRAN el 31-dic-2026**. Para un canal faceless la
     voz ES la identidad. Si se paga, hay que usar **Voice Design** (permanente y única).
- Si el usuario decide pagar: el prompt de voz elegido está en `docs/guiones/voice-design.txt`
  (prompt B, *"el que te cuenta la verdad"*). Ajustes: stability 40 / similarity 75 / style 20.
- **Cambiar de motor de voz rompe la comparabilidad.** Se anota como bloque en `production_dna.blocks`.

---

## 9. QUÉ HACER DESPUÉS (reordenado por la AUDITORÍA 2026-07-15 — leer `docs/AUDITORIA.md`)
1. **CERRAR EL LOOP DE MEDICIÓN (prioridad #1, ~15 min, no es una feature).** Registrar los 3 Shorts
   publicados con los números de Facebook (S1 259 vistas/3 int · S2 218/1 · S3 67/1):
   `record-analytics` (vistas + `traffic_source`; CTR/retención solo si hay YouTube Studio, como
   **fracción 0..1**) + `record-cost` (horas reales — preguntar al usuario) + `record-outcome <ref>
   <0..1>` + `dna`. Contexto (URLs/hora/voz) ya está en `production_context`. **Sin esto el sistema
   no aprende nada y todo lo demás es a ciegas.**
2. **Publicar el 'FED'** (ya montado y calibrado; voz en `data/voz-short-fed.mp3`). El usuario publica
   una MAÑANA (su franja fija, ~11:30 — aísla la hora como el resto). Título/desc en el historial de
   chat y en el runbook. Tras 48h: medir y registrar (paso 1).
3. **Volumen + cadencia + distribución:** 1 Short/día a la misma hora; subir el MISMO MP4 también a
   **TikTok e Instagram Reels** (3× at-bats, coste ~0). Quedan S4 (`shock`) y S5 (`question`) del
   pack + temas por datos (warren/housing/gold del youtube-scan).
4. **Arreglar `decide`** (stoplist de nombres de fuente: saca "cryptonews net", "empery digital"…) →
   que el sistema vuelva a elegir tema. Y **tests del motor** (deuda: 2.558 líneas sin cobertura).
5. **Sync por palabra** en checklist/bullets (usar los tiempos que el calibrador ya calcula) — el
   arreglo de fondo de la desincronía. Verificar contra las voces reales que están en `data/`.

**NO construir un generador de posts de texto.** Verificado: el alcance orgánico de una Página de
Facebook es el **1-6% de sus seguidores**, y el canal tiene **cero**. Los posts de texto no se
distribuyen a no-seguidores; los Reels sí. Los Community posts de YouTube tampoco (van a suscriptores).
"Contenido diario" = **más Shorts**, no más formatos.

---

## 10. TRAMPAS CONOCIDAS (le costaron horas a la sesión anterior)
- **`MediaRecorder.isTypeSupported()` MIENTE.** Hay que sondear grabando de verdad, y sondear el
  **vídeo aislado**: con una pista de audio adjunta, un contenedor sin códec de vídeo igual emite
  bytes (los del audio) y el sondeo da un falso positivo → archivo con voz y sin imagen.
- **`+duration.toFixed(2)` redondea HACIA ARRIBA** la mitad de las veces → `currentTime` nunca
  alcanza el límite → bucle infinito al grabar. Usar `Math.floor` y `audioEl.ended`.
- **La pestaña en segundo plano estrangula `requestAnimationFrame`** → vídeo a saltos, sin avisar.
  Hay guards; el camino MP4 (WebCodecs) no lo sufre.
- **Los subtítulos NUNCA se reparten proporcionalmente.** Ese fue el desfase del S3: el habla no es
  un metrónomo. Sin tiempos medidos → sin subtítulos, y grabar está vetado.
- **El panel de preview de Claude reporta `document.hidden = true`** y estrangula rAF: los guards
  saltan. Para verificar hay que tomar una captura antes (trae la pestaña al frente) o sondear
  la lógica directamente.
- **PowerShell rompe los mensajes de commit** con comillas/`&`/`$`. Escribir el mensaje a un archivo
  y usar `git commit -F <archivo>`.
- Hay un hook de plugin roto (`validate_antipatterns.py` no existe) que escupe un error tras cada
  edición. **Es ruido, se ignora.** Las ediciones se aplican bien.

---

## 11. Qué está construido (código)
- **92 tests verdes** (`python -m unittest discover -s tests -q`). Correr SIEMPRE antes de commitear lógica.
- **Kernel** `omega/reasoning/` (domain-agnostic, test de pureza por AST): beliefs/predictions,
  signals, hypotheses, opportunities, decision_engine (score = confianza + Σ peso·feature), decisions.
- **Observación + decisión** `omega/`: `sources/rss.py` (12 feeds) · `sources/youtube.py` (API, filtro
  solo-EN) · `analyze/momentum.py` · `analyze/demand.py` · `analyze/monetization.py` (RPM) ·
  `analyze/hypothesis_engine.py`.
- **`decide`** pondera demand · gap · demand_momentum · **monetization** (dinero, no viralidad).
- **Creativo** `omega/creative/`: patterns (CKB), decisions+calibración, combinator, experiments,
  production_dna (ADN + analíticas + coste, con guard de confounding).
- **Auditoría 2026-07-09:** 3 bugs de señal arreglados (contracciones inglesas esquivaban las
  stopwords; `record_analytics` sin validación de rango; `feeds.json` arrastraba retiros DEPORTIVOS
  vía "OR retirement" — "justin verlander" llegó a **ganar** `decide`).

## 12. Comandos
Diario: `ingest` · `youtube-scan` · `signals` · `decide` (atajo **`/daily`**).
Explorar: `trends` · `youtube <q>` · `related <tema>` · `patterns` · `combine`.
Tras publicar: `record-dna` · `record-cost` · `record-analytics` · `record-outcome <ref> <0..1>` ·
`dna` · `learnings`.

## 13. Convenciones
- Responder en **español**; el contenido del canal va en **inglés**.
- **Verificar antes de afirmar.** Esta sesión encontró 3 cifras falsas y ~8 bugs; ninguno se evitó
  "siendo cuidadoso", todos aparecieron al **medir**. Es el activo del proyecto.
- `data/` y `.env` gitignored. Rama `master`. Commits terminan con
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Windows + PowerShell. Kernel `omega/reasoning/` es domain-agnostic (test de pureza): nada de video.

## 14. Cómo arrancar el nuevo chat
> *"Lee `docs/ESTADO.md`. Estamos en: Short #1 publicado, `production_outcome = 0`.
> [Si es sábado 12 o después] Vamos a medir y cerrar el bucle.
> [Si no] Vamos a producir el S1: necesito la escena de las dos columnas."*

**No empieces a construir nada sin leer `docs/POLITICA.md`.** El motor creativo está congelado.
Progreso del proyecto = **filas del dataset**, no commits ni módulos. Van 2 de 10 instrumentados,
y **0 medidos**.
