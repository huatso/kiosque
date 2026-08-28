#!/usr/bin/env bash
# Sobe o servidor local e abre o Chromium em modo kiosque.
set -euo pipefail

PASTA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORTA="${PORTA:-8000}"

# Navegador: usa o primeiro que existir
NAVEGADOR=""
for c in chromium chromium-browser google-chrome google-chrome-stable; do
  if command -v "$c" >/dev/null 2>&1; then NAVEGADOR="$c"; break; fi
done
if [ -z "$NAVEGADOR" ]; then
  echo "Nenhum Chromium/Chrome encontrado." >&2
  exit 1
fi

# Servidor
python3 "$PASTA/server.py" "$PORTA" &
SERVIDOR=$!
trap 'kill "$SERVIDOR" 2>/dev/null || true' EXIT

# Espera a porta responder
for _ in $(seq 1 50); do
  if (echo > /dev/tcp/127.0.0.1/"$PORTA") 2>/dev/null; then break; fi
  sleep 0.1
done

"$NAVEGADOR" \
  --kiosk \
  --no-first-run \
  --disable-session-crashed-bubble \
  --disable-infobars \
  --incognito \
  "http://localhost:$PORTA/"

# Ao fechar o navegador, o trap derruba o servidor.
