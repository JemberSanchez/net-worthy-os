---
description: Producción diaria de un Short v2 de punta a punta (tema → guion → storyboard → render → QA → preview). NO publica sin aprobación.
---

Produce el Short de hoy con el motor v2. Responde en español; el contenido del canal, en inglés.
Lee antes `CLAUDE.md` y `video-v2/motor/README.md` (catálogo de escenas y anclas).

## 0. Entorno y estado (sesión nueva en la nube)
1. `bash tools/setup_nube.sh` — idempotente. Si falla, para y reporta qué paso y su salida.
2. `python -m omega.cli estado-bajar` — si falta `ESTADO_REPO`, PARA: sin la base, `decide` no
   tiene historia y el tema saldría a ciegas. Reporta qué secreto falta.

## 1. Qué contar (el sistema decide, no el gusto)
3. `/daily`: `ingest`, `youtube-scan`, `signals`, `decide`. Si un paso falla por red (dominio no
   permitido), anota el dominio exacto y sigue con los demás.
4. Tema = ganador de `decide`. Regla dura: el término crudo es un QUÉ, no un vídeo → conviértelo en
   un explainer. Descarta si ya existe un proyecto con ese tema (`ls video-v2/`) o si no hay
   datos verificables para contarlo: en ese caso toma el siguiente de la lista y dilo.

## 2. Guion (inglés, 110-160 palabras ≈ 35-50 s con Kokoro)
5. Estructura: gancho de contraste (≤2 frases, la primera palabra ya dice algo) → qué pasó / datos
   → por qué funciona → **la parte honesta** (riesgo, sesgo de superviviente) → "y a ti qué" →
   CTA con UNA sola dicotomía para comentarios. Frases cortas: cada frase es un ancla.
6. **Cada cifra con fuente** (URL en `cifras`). Si no puedes verificar un número, no lo uses. Nada
   de consejo financiero personalizado; las curvas son ILUSTRATIVAS y se dice.

## 3. Storyboard (`video-v2/<ref>/storyboard.json`)
7. Copia la forma de `video-v2/read-janitor/storyboard.json`. Reglas:
   - un cambio visual cada ≤2,5 s (una escena por frase, o sub-anclas dentro de la escena);
   - ≥3 imágenes reales: `python tools/imagenes_libres.py buscar "<q>"` (Commons, solo PD/CC0/CC BY;
     UNA búsqueda por concepto, sin bucles: la API limita por IP). Nunca fotos de prensa de
     personas reales. Declara cada imagen en `imagenes` con su `commons`;
   - subtítulos sin el gancho ni el CTA; como mucho un `contador3d`;
   - `publicacion` con título (≤100), descripción, tags y hashtags; `adn` con `renderer_version: v2-hyperframes`.
8. `python video-v2/motor/construir.py video-v2/<ref> --validar` hasta que pase. El mensaje dice
   qué frase y qué palabra fallan: corrige el storyboard, no el validador.

## 4. Producir y medir
9. `python video-v2/motor/producir.py video-v2/<ref>` — voz, build, lint, render, loudness, ritmo.
   Si una puerta falla, arregla la CAUSA (máx. 2 rondas). Nunca subas un umbral para pasar.

## 5. Entregar y PARAR
10. `python -m omega.cli estado-subir` y commit + push del proyecto (sin `renders/` ni `assets/_motor/`).
11. Envía la preview con SendUserFile y un resumen corto: tema y por qué ganó, el guion, las
    fuentes, la tabla de puertas de `renders/qa.json`, título y descripción propuestos.
12. **PARA aquí.** No publiques nada. Espera la aprobación explícita del usuario en esta sesión.

## 6. Solo si el usuario aprueba
13. YouTube: pon `"privacy_status": "public"` en `data/publish_<ref>.json` (o déjalo privado si
    lo pide) y `python -m omega.cli publish <ref>`.
14. Facebook/Instagram: **solo con confirmación explícita para Meta** (regla del proyecto):
    `publish-fb <ref> --publicar` / `publish-ig <ref> --publicar`.
15. `python -m omega.cli record-dna video-v2/<ref>/adn.json` y `estado-subir`.
