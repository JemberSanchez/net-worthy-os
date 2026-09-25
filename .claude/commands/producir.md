---
description: Producción diaria de un Short v2 de punta a punta (tema → guion → storyboard → render → QA → preview). NO publica sin aprobación.
---

Produce el Short de hoy con el motor v2. Responde en español; el contenido del canal, en inglés.
Lee antes `CLAUDE.md` y `video-v2/motor/README.md` (catálogo de escenas y anclas).

## 0. Entorno y estado (sesión nueva en la nube)
1. `bash tools/setup_nube.sh` — idempotente. Si falla, para y reporta qué paso y su salida.
2. `python -m omega.cli estado-bajar` — si falta `ESTADO_REPO`, PARA: sin la base, `decide` no
   tiene historia y el tema saldría a ciegas. Reporta qué secreto falta.
   Después, `python -m omega.cli analytics-sync`: mide los vídeos ya publicados (curva de
   retención, fuente de tráfico, búsquedas) y re-puntúa sus outcomes. "Sin datos aún" o "aún
   privado" es normal (Analytics va ~2-3 días tarde); un ✗ de permisos se reporta pero NO para la
   rutina. Guarda del resumen: el punto de la curva donde más cae y las búsquedas que trajeron gente.

## 1. Qué contar (el sistema decide, no el gusto)
3. `/daily`: `ingest`, `youtube-scan`, `signals`, `decide`. Si un paso falla por red (dominio no
   permitido), anota el dominio exacto y sigue con los demás.
4. Tema = ganador de `decide`. Regla dura: el término crudo es un QUÉ, no un vídeo → conviértelo en
   un explainer. Descarta si ya existe un proyecto con ese tema (`ls video-v2/`) o si no hay
   datos verificables para contarlo: en ese caso toma el siguiente de la lista y dilo.
   Si `analytics-sync` mostró búsquedas reales que encajan con un candidato de `decide`, ese
   candidato gana el empate (demanda medida en NUESTRO canal > demanda estimada). Dilo en el resumen.

## 2. Guion (inglés, 110-160 palabras ≈ 35-50 s con Kokoro)
5. Estructura: gancho de contraste (≤2 frases, la primera palabra ya dice algo) → qué pasó / datos
   → por qué funciona → **la parte honesta** (riesgo, sesgo de superviviente) → "y a ti qué" →
   CTA con UNA sola dicotomía para comentarios. Frases cortas: cada frase es un ancla.
   Técnicas de retención de Shorts (por qué: la curva del canal cae entre 3 s y 20 s):
   - **Gancho en 1 s con la cifra de payoff**: la primera frase ya dice el resultado raro
     ("died with $7.2 million") — no se guarda el dato para el final. Nada de "hoy vamos a…".
   - **Open loop**: la primera o segunda frase abre una pregunta que se cierra tarde ("how?",
     "nobody knew"). El espectador se queda por la respuesta.
   - **Re-gancho cada ~8-10 s**: una frase de giro ("But here's the part nobody tells you",
     "That's not the crazy part") o una cifra nueva. El validador avisa si pasan >12 s sin golpe.
   - **Final en bucle**: la última frase del CTA enlaza con la primera, para que la repetición
     suene continua (una vista repetida sube el % visto por encima de 100 %).
   - Ritmo de voz 150-175 palabras/min; nada de frases de relleno ("so basically", "you see").
6. **Cada cifra con fuente** (URL en `cifras`). Si no puedes verificar un número, no lo uses. Nada
   de consejo financiero personalizado; las curvas son ILUSTRATIVAS y se dice.

## 3. Storyboard (`video-v2/<ref>/storyboard.json`)
7. Copia la forma de `video-v2/read-janitor/storyboard.json`. Reglas:
   - un cambio visual cada ≤2,5 s (una escena por frase, o sub-anclas dentro de la escena);
   - ≥3 imágenes reales: `python tools/imagenes_libres.py buscar "<q>"` (Commons, solo PD/CC0/CC BY;
     UNA búsqueda por concepto, sin bucles: la API limita por IP). Nunca fotos de prensa de
     personas reales. Declara cada imagen en `imagenes` con su `commons`;
   - 1-3 clips de vídeo (b-roll) donde más ayude el movimiento real — SIEMPRE el gancho (0-3 s):
     `python tools/broll.py buscar commons "<q>"` (o `buscar pexels` si hay PEXELS_API_KEY y
     videos.pexels.com está permitido). Declara en `clips` (`{"commons": "File:X.webm", "desde": s}`
     o `{"pexels": id, "desde": s}`) y usa `"clip": "<nombre>"` en lugar de `"img"` en esa `foto`
     (o en un `fondo`). Antes de fijar `desde`, mira UNA hoja de miniaturas
     (`ffmpeg -i assets/clips/<n>.src -vf "fps=1/2,scale=192:108,tile=8x2" -frames:v 1 hoja.jpg`):
     objetos/manos/lugares sí; caras reconocibles, logos o noticias con personas reales, no;
   - subtítulos sin el gancho ni el CTA; como mucho un `contador3d`;
   - `publicacion` con título (≤100), descripción, tags y hashtags; `adn` con `renderer_version: v2-hyperframes`.
   Lecciones del ensayo del 23-sep (Grace Groner), no repetirlas:
   - Genera la voz ANTES de escribir las escenas (`python video-v2/motor/voz.py video-v2/<ref>`,
     con solo `guion` en el storyboard) y lista las frases con sus palabras exactas: las anclas
     se escriben contra ese listado (p. ej. "—" es una palabra; "seventy-five" va con guion).
   - Imágenes: busca OBJETOS y lugares ("vintage typewriter", "stock certificate"), no personas:
     Commons responde mal a conceptos genéricos de gente y las fotos de personas traen contexto
     (una "stenographer" resultó ser de un campo de internamiento de 1942). Reutiliza las del
     catálogo ya bajado (`video-v2/*/assets/t/` + su creditos.json) antes de buscar.
   - CTA: la `pregunta` va ANTES que los `botones` (los botones la ocultan al entrar).
8. `python video-v2/motor/construir.py video-v2/<ref> --validar` hasta que pase. El mensaje dice
   qué frase y qué palabra fallan: corrige el storyboard, no el validador. Después revisa una
   hoja de contactos (`npx hyperframes snapshot --at ...`) ANTES del render: el validador no ve
   solapes ni textos que no caben.

## 4. Producir y medir
9. `python video-v2/motor/producir.py video-v2/<ref>` — voz, build, lint, render, loudness, ritmo.
   Si una puerta falla, arregla la CAUSA (máx. 2 rondas). Nunca subas un umbral para pasar.

## 5. Entregar y PARAR
10. `python -m omega.cli estado-subir` y `python -m omega.cli produccion-guardar video-v2/<ref>`
    (el proyecto va al repo PRIVADO, no a una rama suelta del repo de código). `producir.py` ya lo
    habrá subido a YouTube como PRIVADO si hay token.
11. Envía la preview con SendUserFile y un resumen corto: tema y por qué ganó, el guion, las
    fuentes, la tabla de puertas de `renders/qa.json`, título y descripción propuestos.
12. **PARA aquí.** No publiques nada. Espera la aprobación explícita del usuario en esta sesión.

## 6. Solo si el usuario aprueba
13. YouTube: `python -m omega.cli programar <ref>` (lo publica a las 12:00 de Nueva York, hora
    pico de la audiencia; `--hora HH:MM` para otra) o `--ahora` si lo pide ya. Si no se subió como
    borrador (sin token), antes `python -m omega.cli publish <ref>`.
14. Facebook/Instagram: **solo con confirmación explícita para Meta** (regla del proyecto):
    `publish-fb <ref> --publicar` / `publish-ig <ref> --publicar`.
15. `python -m omega.cli record-dna video-v2/<ref>/adn.json` y `estado-subir`.
