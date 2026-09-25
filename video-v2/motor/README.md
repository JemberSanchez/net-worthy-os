# Motor v2 — un Short desde `storyboard.json`

```
python video-v2/motor/construir.py video-v2/<proyecto> --validar   # ¿el storyboard es correcto? (<1 s)
HF_CORE=<dir con @hyperframes/core@0.8.62> python video-v2/motor/construir.py video-v2/<proyecto>
cd video-v2/<proyecto> && npx hyperframes@0.8.62 lint && npx hyperframes@0.8.62 render --quality high -o renders/x.mp4
```
Proyecto = `storyboard.json` + `assets/voice.mp3` + `assets/words.json` (tiempos medidos por
`tools/alinear_voz.py`). Todo lo demás (imágenes con licencia, duotono, música, sfx, ducking,
subtítulos) lo pone el motor. **Nadie escribe HTML ni segundos**: se escriben anclas.

## Anclas (frase:palabra, nunca segundos)
Las frases del guion se numeran desde 0 (corta en `. ? !`). Un ancla es un string:

| Ancla | Significa |
|---|---|
| `"6"` | cuando arranca la frase 6 |
| `"6:reinvested"` | cuando arranca la 1ª "reinvested" de la frase 6 (sin mayúsculas ni puntuación) |
| `"21:team#2"` | la 2ª "team" de la frase 21 |
| `"14:it$"` | cuando TERMINA esa palabra |
| `"6:shares+0.34"` | desplazamiento en segundos (también `-0.1`) |

Claves que llevan ancla: `en`, `hasta`, `llega`, `fin`, `marca`, `golpe`, `tachar` (un número
en esas claves, p. ej. `"hasta": 2014` en `anios`, no es ancla). Un ancla que no resuelve **rompe
el build con el motivo** (qué frase, qué palabra): esa es la puerta para storyboards de un LLM.

## Nivel superior
| Clave | Qué |
|---|---|
| `ref`, `adn` | id del vídeo y ADN (`hook_type`, `story_type`, `cta_type`, `renderer_version`) |
| `guion` | `[{id, texto}]` — lo que dice la voz, en inglés. Fuente de verdad del texto |
| `cifras` | `[{dato, fuente}]` — **cada número con URL** (YMYL); sin fuente no construye |
| `aviso` | `{lineas: [..], ventanas: [[ancla, ancla]], final: true}` — obligatorio si hay cifras |
| `imagenes` | `{id: {commons: "File:…", recorte: 0.04}}` — solo PD/CC0/CC BY (lo filtra `imagenes_libres`) |
| `clips` | `{id: {commons: "File:….webm" \| pexels: <id>, desde: s, [contraste]}}` — b-roll de vídeo (`tools/broll.py`): mismas licencias + Pexels License; se trata a 1080x1920 con el MISMO duotono (LUT 1D), sin audio y con la duración exacta de su escena (`assets/v/`, regenerable) |
| `subtitulos` | `[frase_desde, frase_hasta]` — normalmente sin el gancho ni el CTA (llevan su texto) |
| `calientes` | palabras que se resaltan en dorado en el subtítulo |
| `musica` | `{oscuro: [frase, frase]}` — tramo en que la música cae (p. ej. "the part nobody says") |
| `golpes` | anclas extra de impacto (los de `revelacion` y `contador3d` ya son automáticos). Úsalos como **re-ganchos** en las frases de giro: cada golpe trae riser 1 s antes, impacto y punch-in de cámara. El validador avisa si pasan >12 s sin ninguno |
| `fondos_auto` | `true` por defecto: las escenas de texto sin `fondo` reciben una imagen del proyecto desenfocada al 30 % (nunca texto sobre verde vacío). `false` lo apaga; `"fondo": false` en una escena, solo en esa |
| `cola_s` | segundos tras la última palabra (tarjeta final). Por defecto 3.0 |

Texto: `*así*` sale en dorado. Cada escena dura desde su `en` hasta el `en` de la siguiente.

## Catálogo (10 tipos, todos vistos funcionar en el #7 v2)
Campos opcionales entre corchetes. `fondo` (cualquier escena) = foto de fondo al 40 %.

| Tipo | Campos | Para qué |
|---|---|---|
| `foto` | `img` o `clip`, `[mov], [kicker{texto,en}], [titulo{texto,en}], [sub{texto,en}]` | imagen real a sangre con Ken Burns (`mov`: push/pull/izq/der/sube), o metraje real (`clip`) con un empuje suave. `fondo` también admite `{clip, opacidad}` |
| `revelacion` | `linea1{texto}, linea2{texto,en}, [golpe]` | contraste de 2 líneas + estallido de monedas en `golpe` |
| `lista` | `icono: x\|check, items[{texto,en,[marca],[color]}]` | ✗ que caen (negaciones) o ✓ (receta) |
| `titulo` | `lineas[{texto,en,[estilo],[color],[tam]}], [kicker{texto,en,color}], [contador{linea,valor,en}], [tachar{linea,en}], [icono{tipo:"engranaje",en}], [cheque{monto,en,tachar}], [alarma], [posicion]` | frases fuertes. `estilo`: huge/big/mid/boton; `{n}` en una línea = contador |
| `tarjetas` | `imgs[{img,en}], [titulo{texto,en}], [flujo{texto,en,hasta,contador{desde,valor,etiqueta}}]` | documentos/certificados que se apilan; monedas que fluyen a un contador |
| `contador3d` | `valor, llega, [prefijo], [columnas], [kicker{texto,en}], [pill{texto,en}]` | cifra grande + columnas 3D sincronizadas; aterriza en `llega`. **Máx. 1 por vídeo** |
| `curva` | `serie{mensual,tasa,anios,final}, [fin], [aportado{texto,en}], [area{texto,en}], [etiqueta_max], [ilustrativo], [titulo{texto,en}], [escalas[{texto,en}]], [encoger{en,hasta}]` | interés compuesto ILUSTRATIVO; `escalas` = misma curva, otra escala |
| `puntos` | `n, etiqueta, cuenta{en}, [cae{en,hasta,img,texto}], [atenuar{en,n,texto}]` | cartera de N posiciones; una cae, algunas se atenúan |
| `anios` | `desde, hasta, cuenta{en}, fin, [kicker], [hitos[[año,texto]]], [etiqueta{texto,en}]` | línea de años que corre con hitos (hechos históricos) |
| `cta` | `a{texto,en}, [o], b{texto,en}, [pregunta{texto,en,fondo}], [botones[{texto,en}]], [sub]` | UNA dicotomía para comentarios + tarjeta final con movimiento |

Referencia completa y verificada: `video-v2/read-janitor/storyboard.json` (el #7).

## Puertas (en este orden, cada una barata antes que la siguiente)
1. `construir.py --validar` — esquema, anclas, imágenes declaradas, fuentes de cifras, aviso.
2. `hyperframes lint` — 0 errores.
3. **Contraste WCAG AA** (`hyperframes check`, un instante por escena en pasadas de 5): ningún texto
   ilegible. Solo contraste: su auditoría de maquetación da falsos positivos con capas decorativas.
4. Render → `loudnorm` → `tools/medir_loudness.py` (-14 ±1 LUFS) → `tools/medir_ritmo.py --max 2.5`.

Lenguaje de edición automático (sale del plan, nadie lo escribe): punch-in de cámara (zoom-cut)
en golpes y palabras `calientes` con 1,8 s de separación mínima, riser→impacto en cada golpe,
franja oscura central sobre imagen/vídeo y sombra en todo texto grande. Avisos de retención al
validar: gancho sin imagen/clip, gancho sin texto antes de 0,8 s, >12 s sin re-gancho.
