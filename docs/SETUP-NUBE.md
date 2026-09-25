# Activar la producción diaria en la nube — checklist

Lo que falta para que la rutina diaria (`/producir`) funcione sola es CONFIGURACIÓN, no código.
Los pasos web los puede hacer **Claude in Chrome** con el prompt de abajo. El único paso que exige
terminal es el token de YouTube (paso B).

## A) Prompt para Claude in Chrome (copiar y pegar tal cual)

```
Necesito que configures mi proyecto "Net Worthy OS" en el navegador. Reglas: NUNCA escribas en
ningún chat ni en ningún campo que no sea el indicado el valor de una clave o token; si algo pide
confirmación de pago, de borrar datos o de permisos a terceros que no sean los que te indico, para
y pregúntame. Hazlo en este orden y al final dime qué hiciste y qué quedó pendiente.

1. GitHub (github.com, cuenta JemberSanchez):
   a) Crea un repositorio nuevo llamado "net-worthy-data", PRIVADO, marcando "Add a README".
      Descripción: "Estado privado de Net Worthy OS (base de datos y producciones). Sin tokens."
   b) Ve a https://github.com/settings/installations, abre la app "Claude" -> Configure ->
      Repository access. Si está en "Only select repositories", añade "net-worthy-data" y guarda.

2. Google Cloud Console (console.cloud.google.com, el proyecto donde está la YouTube Data API):
   a) "APIs y servicios" -> "Pantalla de consentimiento de OAuth" (o "Google Auth Platform" ->
      "Público"). Si el estado de publicación es "En prueba"/"Testing", pulsa "Publicar app" /
      "Pasar a producción" y confirma. (En prueba, el token caduca cada 7 días.)
   b) "APIs y servicios" -> "Biblioteca": busca "YouTube Analytics API" y pulsa "Habilitar" si no
      lo está.
   c) "APIs y servicios" -> "Credenciales" -> "Claves de API": copia al portapapeles el valor de la
      clave que ya existe (NO crees una nueva). La usarás en el paso 3.

3. Entorno de la nube de Claude Code (claude.ai/code): abre la sesión del proyecto net-worthy-os,
   menú del entorno en la barra de título -> "Edit".
   a) Variables de entorno: añade
      - YOUTUBE_API_KEY = (pega la clave del paso 2c)
      - ESTADO_REPO = https://github.com/JemberSanchez/net-worthy-data.git
   b) Acceso de red / dominios permitidos: añade estos dominios (uno por línea) sin quitar los que
      ya hay:
      news.google.com
      cointelegraph.com
      www.coindesk.com
      finance.yahoo.com
      feeds.marketwatch.com
      www.reddit.com
      en.wikipedia.org
      suggestqueries.google.com
      graph.facebook.com
      rupload.facebook.com
   c) Guarda.

4. Dime cuáles de los pasos 1-3 quedaron hechos y cuáles no, sin mostrar ningún valor secreto.
```

## B) En tu PC (terminal, 3 minutos) — lo único que Chrome no puede hacer
**Atajo en un comando** (descarga antes el JSON del cliente OAuth "Escritorio" de Google Cloud →
Credenciales, y el script `tools/preparar_pc.ps1` desde GitHub):
```powershell
powershell -ExecutionPolicy Bypass -File preparar_pc.ps1 -ClientSecret "$HOME\Downloads\client_secret_XXXX.json"
```
Paso a paso, si prefieres hacerlo a mano:
```powershell
git clone https://github.com/JemberSanchez/net-worthy-os.git ; cd net-worthy-os
pip install -r requirements.txt
# descarga el JSON del cliente OAuth "Escritorio" desde Google Cloud -> Credenciales y guárdalo como:
#   data\youtube_client_secret.json
python -m omega.cli youtube-auth          # abre el navegador; elige la cuenta del canal Net Worthy
Get-Content data\youtube_token.json -Raw | Set-Clipboard
```
Pega el portapapeles en el entorno de la nube como variable **`YOUTUBE_TOKEN_JSON`**.

En el PC que tiene la base de datos (una sola vez, con `ESTADO_REPO` en su `.env`):
```powershell
python -m omega.cli estado-subir
```

Meta (opcional, cuando quieras publicar también en Facebook/Instagram): `.env` con
`META_APP_ID`/`META_APP_SECRET` → `python -m omega.cli meta-auth` → contenido de
`data\meta_token.json` en la variable `META_TOKEN_JSON`. Caduca a los 60 días.

## C) Después
Abre una **sesión nueva** (las variables solo entran al arrancar) y pide: "ejecuta una prueba
vigilada de /producir y programa la rutina diaria". Claude verifica todo, produce el primer vídeo
de punta a punta (queda como borrador PRIVADO en YouTube) y deja la rutina programada.
Aprobar cada día = `python -m omega.cli programar <ref>` (lo publica a las 12:00 de Nueva York).
