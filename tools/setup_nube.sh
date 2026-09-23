#!/usr/bin/env bash
# Deja una sesión NUEVA en la nube lista para producir un Short v2. Idempotente: si algo ya está,
# lo salta (una 2ª ejecución tarda segundos). Lo corre la rutina diaria como primer paso.
#
#   bash tools/setup_nube.sh            # instala todo
#   source <(bash tools/setup_nube.sh --env)   # solo exporta HF_CORE / HYPERFRAMES_BROWSER_PATH
#
# Secretos que lee del ENTORNO (se configuran en el entorno de la nube, nunca en el repo):
#   YOUTUBE_API_KEY      -> demanda (youtube-scan). Lo lee omega.config directamente.
#   ESTADO_REPO          -> URL del repo PRIVADO de datos (estado-bajar / estado-subir).
#   YOUTUBE_TOKEN_JSON   -> contenido de data/youtube_token.json (subida a YouTube). Opcional.
#   META_TOKEN_JSON      -> contenido de data/meta_token.json (Facebook/Instagram). Opcional.
# Lecciones medidas el 23-sep (docs/V2-CALIDAD.md): ffmpeg CON ffprobe; el Chrome de Playwright
# sin ventana; `apt-get install` sin `update` previo da 404 en este contenedor.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
HF_CORE_DIR="${HOME}/.cache/hfcore"
BROWSER="/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell"

if [[ "${1:-}" == "--env" ]]; then
  echo "export HF_CORE=${HF_CORE_DIR}"
  echo "export HYPERFRAMES_BROWSER_PATH=${BROWSER}"
  exit 0
fi

paso() { printf '\n== %s\n' "$*"; }

paso "ffmpeg + ffprobe"
if ! command -v ffprobe >/dev/null; then
  apt-get update -qq >/dev/null && apt-get install -y -qq ffmpeg >/dev/null
fi
ffprobe -version | head -1

paso "Python (dependencias del proyecto)"
# opencv headless: el contenedor no tiene libGL; la versión con GUI no importa.
python3 -m pip install -q -r <(grep -vE '^(opencv-python|piper-tts)' "$RAIZ/requirements.txt") opencv-python-headless lameenc 2>&1 | grep -vi "running pip as the 'root'" || true

paso "Kokoro (venv 3.12 aparte: kokoro -> misaki -> spacy no instala en 3.13+)"
VENV="$RAIZ/tools/.venv-voces"
if [[ ! -x "$VENV/bin/python" ]] || ! "$VENV/bin/python" -c "import kokoro" 2>/dev/null; then
  python3.12 -m venv "$VENV"
  "$VENV/bin/python" -m pip install -q "kokoro>=0.9.4" soundfile
fi
echo "kokoro OK"

paso "HyperFrames (skill de audio para el ducking + @hyperframes/core fijado)"
if [[ ! -f "$HOME/.claude/skills/hyperframes-audio/scripts/carve.mjs" ]]; then
  npx --yes hyperframes@0.8.62 skills update hyperframes-audio >/dev/null 2>&1
fi
if [[ ! -d "$HF_CORE_DIR/node_modules/@hyperframes/core" ]]; then
  mkdir -p "$HF_CORE_DIR" && (cd "$HF_CORE_DIR" && npm init -y >/dev/null && npm i -s @hyperframes/core@0.8.62)
fi
echo "carve + core OK"

paso "Credenciales desde el entorno -> data/ (gitignored)"
mkdir -p "$RAIZ/data"
[[ -n "${YOUTUBE_TOKEN_JSON:-}" ]] && printf '%s' "$YOUTUBE_TOKEN_JSON" > "$RAIZ/data/youtube_token.json" && echo "youtube_token.json"
[[ -n "${META_TOKEN_JSON:-}" ]] && printf '%s' "$META_TOKEN_JSON" > "$RAIZ/data/meta_token.json" && echo "meta_token.json"
for v in YOUTUBE_API_KEY ESTADO_REPO; do
  [[ -n "${!v:-}" ]] && echo "$v: definido" || echo "⚠ $v: NO definido (ver la cabecera de este script)"
done

paso "Listo. Para los comandos de render:"
echo "  source <(bash tools/setup_nube.sh --env)"
