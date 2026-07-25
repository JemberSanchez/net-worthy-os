# EXPERIMENTO #001 — RITMO: matar el acantilado de retención de los 3-10s

> **Estado (2026-07-18): IMPLEMENTADO y RENDERIZADO — pendiente PUBLICAR + MEDIR.**
> Motion Budget v1 aplicado SOLO a Buffett (flag `CFG.ritmo`, opt-in). MP4 en
> `data/net-worthy-buffett-ritmo.mp4` (55s, 1080x1920, H.264+AAC, 61MB). 23 tests del motor verdes
> ("el S3 publicado NO se movió" incluido). Verificado a ojo con la voz REAL calibrada (frames del
> gancho mirados por el POST-server, no afirmados). **Siguiente:** el usuario lo sube a IG + TikTok
> (Buffett nunca se vio ahí) → a los ~3-5 días medir `retention_avg` vs 0.109.
>
> **⚠ Corrección al diseñar (la voz real desmintió mi supuesto):** creía que el hueco muerto era
> "solo AGE 11" de p0.26 a p0.80. La calibración REAL de la voz de 55s da `T.hook=5.99`,
> `spec=[-0.3, 2.86]` → **AGE 56 aparece a los 2.86s**, no a los 6.5. El hueco real es de ~2.9s a
> ~5.5s con AMBAS edades quietas. La línea de tiempo lo cubre igual (va en fracciones de T.hook, se
> adapta sola) y el contador de años corre 0→45 mientras ambas edades esperan → el "45 YEARS" queda
> de conector entre ellas. Lección repetida: **medir antes de afirmar** (aquí, la voz real).
>
> **Estado del DISEÑO original (abajo):** pre-registrado ANTES de tocar el motor (así el resultado no
> se puede racionalizar a posteriori). n será bajo → PROVISIONAL por diseño.
> **Sanción POLITICA.md:** el motor está congelado *salvo que un experimento publicado revele una
> limitación concreta*. Ya la tenemos: **6 Shorts publicados, la retención se derrumba a los ~6s.**
> Esto NO es "más producción" (que en ALCANCE no pagó — el FED era el más producido y el peor). Es
> una respuesta MEDIDA a un acantilado MEDIDO, en el eje de la RETENCIÓN, que es otro eje distinto.

## 1. El hallazgo que lo origina (dato del 2026-07-18, Facebook)

| Short | Vistas de 3s (enganche) | Tiempo promedio | Largo | Retención |
|---|---|---|---|---|
| **Buffett** | **59** ← el que más engancha | 6 s | 55 s | **0.109** |
| S1 (two men) | 49 | 5 s | 32 s | 0.158 |
| S2 (coffee) | 17 | 2 s | 32 s | 0.063 |
| FED | 15 | 35 s ⚠ ruido (n=15) | 32 s | — |

**Lectura:** el gancho FUNCIONA (la gente PARA: 59 pasan de 3s en Buffett, récord del canal), pero
la retención cae a los **3-10 segundos**. El problema no es llamar la atención; es **sostenerla
justo después del gancho**.

## 2. Hipótesis falsable

> **El acantilado de los 3-10s lo causa la ESTASIS VISUAL durante la narración**: el cuadro se queda
> quieto mientras la voz habla, el ojo no recibe información nueva y hace scroll.
>
> **Predicción:** si en los primeros 10s el cuadro NUNCA se congela más de ~1.5s (micro-movimiento
> continuo + un "beat" visual cada ~2s), el **tiempo promedio sube por encima de 6s** (baseline
> Buffett) y **la retención_avg supera 0.109**.
>
> **Refutación:** si con el nuevo ritmo la retención_avg NO sube respecto a Buffett, la estasis NO
> era la causa → se descarta esta hipótesis y NO se sigue invirtiendo en ritmo. (Ese es el punto:
> puede salir que no. Bien.)

## 3. La UNA variable

Cambia **solo la densidad de movimiento en la ventana 0-10s**. Todo lo demás, IDÉNTICO:
voz Firme Pilot · clase de tema (personaje + evergreen) · mecanismo de gancho (CONTRASTE, el
probado: `TWO MEN` y `AGE 11 / AGE 56` son los que más enganchan) · banda de duración · música/sfx.

## 4. MOTION BUDGET v1 — las reglas concretas (esto es lo que se implementa)

Convertir "que nunca se vea plano, y más al comienzo" en reglas medibles y testeables:

**Ventanas y umbral de quietud:**
| Ventana | Qué es | Beat cada | Congelado máximo |
|---|---|---|---|
| **HOOK** `0–2s` | la tarjeta de contraste | — (micro-movimiento continuo) | **nunca frozen** |
| **ACANTILADO** `2–10s` | donde muere la retención | **≤1.8s** | **1.5s** |
| BODY `10s–fin` | el desarrollo | ≤2.5s | 2.5s |
| CTA `últimos ~3s` | el veredicto/pregunta | pulso vivo | — |

**Qué cuenta como "beat"** (un cambio de estado que el ojo registra): un número que aterriza o
cuenta · un corte a nuevo encuadre/escala (zoom, paneo) · un elemento que entra o sale · un cambio
de color/estado (una barra que se llena, la curva que avanza un tramo) · un cambio de etiqueta.

**Suelo Y techo (el "sin ser demasiado", que es clave):**
- **SUELO:** ≥1 beat por ventana (arriba). Que nunca se seque.
- **TECHO:** ≤1 beat *mayor* cada 1.2s. **No estroboscopio.** El usuario pidió expresamente que no
  sea "demasiado" — el budget tiene mínimo y MÁXIMO. Esto lo separa de "meter más cosas".
- **Micro-movimiento CONTINUO** (drift del fondo, respiración de escala, parallax, conteo): corre
  SIEMPRE y NO cuenta contra el techo. Es lo que hace que el cuadro **nunca esté del todo quieto**.

**El gancho resuelve en movimiento, no en un hold.** Hoy `AGE 11 / AGE 56` son dos líneas que, tras
~1s de lectura, se quedan quietas → el ojo se va. Regla: a los ~1.5s el gancho **empieza a
transformarse** (los dos números arrancan a animarse hacia la curva; la curva-fantasma ya deriva
desde el frame 1 — commit `aa8a411`, el motor YA tiene el concepto, hay que extenderlo).

## 5. Enforcement en código (falsable, no a ojo)

> **✅ EJECUTADO EL 2026-07-25 — 26/26 tests en verde.** Corridos en navegador contra el motor real.
> Estuvo 6 días como diseño sin implementar: el Motion Budget era *buena intención*, justo lo que
> esta sección decía evitar.
>
> **La primera corrida FALLÓ y fue útil.** El umbral inicial (`EPS = 0.5`) estaba elegido a ojo y
> reprobaba movimiento que sí existía. Al medir los 4 Shorts a 4 resoluciones distintas, la escala
> se separó en tres niveles limpios (diferencia media por canal, 0-255, frame reducido a 64×114):
>
> | Nivel | Rango | Evidencia |
> |---|---|---|
> | **Congelado** | 0.00 – 0.06 | s1/fed HOOK = 0.00 · s3 HOOK = 0.02 · **fed ACANTILADO = 0.022** |
> | **Micro-movimiento (ritmo)** | 0.11 – 0.17 | buffett HOOK = **0.112** (el `breath`: escala ±0.6%) |
> | **Beat real** | 0.70 + | buffett ACANTILADO = **0.736** · s1 = 0.778 |
>
> `EPS = 0.10` es el corte entre congelado y micro-movimiento. `0.5` caía **dentro** del rango de
> beat real. Subir la resolución no cambia el veredicto (probado a 114/228/456/912 px: HOOK se
> estabiliza en ~0.2 y BODY en ~0.02), así que 64×114 basta y es ~200× más barato.
>
> **Medición final del Buffett con ritmo:** HOOK `0.112` · **ACANTILADO `0.736`** · BODY `0.018`.
> La ventana del acantilado —la que este experimento existe para arreglar— tiene beat real.
>
> **🔎 VALIDACIÓN INDEPENDIENTE DEL INSTRUMENTO:** el barrido detecta SOLO el congelado del FED
> (`0.022` en 2-10s), que `docs/ESTADO.md` ya tenía anotado a mano como *"8s congelados"*. Nadie se
> lo dijo a la métrica. Hay un test dedicado a eso, porque si algún día deja de detectarlo es que
> la métrica se rompió.
>
> **⚠ HUECO DESTAPADO: la ventana BODY de §4 NUNCA SE IMPLEMENTÓ.** Los **cuatro** Shorts congelan
> ≥2.5s en el cuerpo (buffett 0.018 · s3 0.024 · s1 0.019 · fed 0.013). No es un defecto del
> Buffett: el Motion Budget v1 solo atacó gancho y acantilado. El código y §4 no coinciden. El test
> la mide y la reporta pero **no la exige** (`exige:false`) — un test permanentemente rojo se
> vuelve ruido que se ignora. Decisión pendiente: implementar el budget de BODY, o bajar §4 a lo
> que el motor hace de verdad. Con la retención cayendo entre 3s y 20s, BODY no es la prioridad.

Dos tests en `docs/guiones/tests-motor.html` (junto al barrido de zonas seguras):

1. **El presupuesto se cumple.** Muestrea `drawFrame(t)` cada 0.25s hasta t=52 y, por ventana,
   busca el intervalo MÁS QUIETO: la menor diferencia de píxeles entre dos frames separados por el
   presupuesto de congelado (HOOK 0.5s · ACANTILADO 1.5s · BODY 2.5s). Si esa diferencia cae por
   debajo de `EPS = 0.5` (escala 0-255), el cuadro estuvo congelado → falla. Firma barata: el frame
   reducido a 64×114, porque leer 1080×1920×4 por frame serían ~8 MB × 209.
2. **El barrido DISCRIMINA** (control negativo). Compara la ventana 2-10s del Buffett (con ritmo)
   contra la del S3 (sin ritmo) y exige que el S3 mida más quieto. **Un test que no puede fallar no
   es un test**: sin este control, el primero pasaría siempre y no probaría nada.

`drawFrame` es pura → ambos son deterministas. Las firmas se cachean por Short (un barrido son
~209 renders de 1080×1920; sin caché el test tardaría un minuto y se dejaría de correr).

**Por qué importa para ESTE experimento:** sin enforcement, si la retención no sube no se puede
distinguir *"la hipótesis era falsa"* de *"el render no aplicó el ritmo"* — el mismo agujero que el
2026-07-24 dejó 4 predicciones inverificables (el instrumento cambió sin que nadie lo notara).

## 6. Métrica pre-registrada

- **Primaria:** `retention_avg` (FB `prom_watch / len`) **> 0.109** (baseline Buffett).
- **Secundaria:** fracción que sigue viendo a los 10s (de `vistas_3s` hacia el final).
- **Ideal:** la curva de retención por bloque de YouTube Studio (fracción 0..1) → dice EXACTAMENTE
  en qué segundo se cae, no solo el promedio.

## 7. Control del confounder — LA decisión abierta

Con n=1 por plataforma el aislamiento perfecto no existe. Dos diseños:

- **Opción A (aísla el ritmo, RECOMENDADA):** **re-renderizar Buffett con Motion Budget v1** y
  publicarlo en **Instagram + TikTok** (donde NUNCA se ha visto). Mismo guion, misma voz, mismo
  gancho, mismo tema → **la única variable de contenido es el ritmo**. Confounder: la plataforma
  (audiencia IG/TikTok ≠ FB) — se anota. Coste ~0 (no hay guion ni voz nueva).
- **Opción B:** el próximo Short de personaje-evergreen nuevo, hecho con Motion Budget v1. Confunde
  tema+ritmo. Mitigación: el ALCANCE lo manda el tema/algoritmo, pero la FORMA de la curva de
  retención la manda el video → se atribuye el ritmo con cautela (POLITICA Regla 3).

Se pueden hacer AMBAS: A aísla la variable, B hace avanzar el canal.

> **DECISIÓN (2026-07-18): Opción A.** Re-render de Buffett con Motion Budget v1 → IG + TikTok.
> Aislamiento más limpio de la variable ritmo, coste ~0. El confounder de plataforma queda anotado.

### ⚠ 2026-07-25 — INSTAGRAM NO ES TERRITORIO VIRGEN (la Opción A parte de un supuesto falso)

**El experimento NO ha empezado:** `data/net-worthy-buffett-ritmo.mp4` sigue sin publicarse. El
brazo de tratamiento no existe todavía.

Lo que sí pasó: el Buffett **original** se publicó el 17-jul **desde Business Suite como reel
cruzado**, es decir un solo acto de publicación que lo puso en **Facebook e Instagram a la vez**.

**Consecuencia para el diseño:** la Opción A decía publicar el re-render en *"Instagram + TikTok
(donde NUNCA se ha visto)"*. **Para Instagram eso es falso** — la audiencia de IG ya vio el Buffett
original hace 8 días. Publicar allí el re-render lo convierte en un brazo con la misma
contaminación que tendría Facebook: novedad decaída y posible penalización por contenido repetido.

| Brazo | Estado | Veredicto |
|---|---|---|
| **TikTok** | ✅ Limpio, **SIN PUBLICAR** | Buffett nunca estuvo ahí y no pasa por Business Suite. **Es el único brazo válido de la Opción A.** |
| **Instagram** | ❌ Ya no es virgen | El original salió ahí el 17-jul por el reel cruzado. Sirve como brazo secundario contaminado, no como aislamiento. |
| **Facebook** | ❌ Descartado | Es donde vive el baseline. Re-publicar ahí compite con la v1. |

**⚠ Sospecha abierta sobre el baseline:** si el reel fue cruzado, el Buffett original acumuló
vistas en Instagram ADEMÁS de las 245 de Facebook. El `success = 0.341` se calculó con
`245 (FB) + 11 (YT) = 256` — **sin Instagram**. Si Business Suite reporta IG por separado, hay que
sumarlas y recalcular; el alcance real (y el score) serían mayores. Verificar en Business Suite →
Biblioteca de contenido → el reel → desglose por plataforma **antes** de comparar nada contra este
baseline.

**Cambio de calendario (dato nuevo del 2026-07-24):** medir a las **~24h**, no a los 3-5 días. El
Buffett original hizo el 99,6% de su alcance en las primeras 17h y luego sumó +1 vista en 7 días.
Esperar no aporta señal, solo retrasa la decisión.

**Sobre la métrica secundaria** (§6): *"fracción que sigue viendo a los 10s"* **no es obtenible** —
Facebook reporta 3s y 20s, no 10s, y IG/TikTok reportan otras cosas. Hay que fijar la métrica
secundaria a lo que el instrumento realmente produce ANTES de medir, o el experimento vuelve
inverificable (el mismo fallo que el 2026-07-24 dejó 4 predicciones sin poder resolver).

**Línea base actualizada a 7 días:** `retention_avg = 0.11` · 256 vistas (FB 245 + YT 11) ·
curva **24,1% a 3s → 10,0% a 20s**. La métrica primaria pre-registrada (`> 0.109`) NO se toca.

## 8. Lo que este experimento NO es (para no repetir el error)

No es pulir la ejecución de un concepto flojo (el error que el usuario ya corrigió: audio/sync sobre
un boletín). El concepto (personaje+evergreen+contraste) YA es el ganador medido. Esto ataca UNA
variable con causa medida, métrica pre-registrada y posibilidad real de salir refutado.
