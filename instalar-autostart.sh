#!/usr/bin/env bash
# Instala as entradas de autostart apontando para esta pasta.
set -euo pipefail

PASTA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINO="$HOME/.config/autostart"

mkdir -p "$DESTINO"
for arquivo in kiosque-server firefox-kiosk; do
  sed "s|__PASTA__|$PASTA|g" "$PASTA/autostart/$arquivo.desktop" > "$DESTINO/$arquivo.desktop"
  echo "instalado: $DESTINO/$arquivo.desktop"
done

echo
echo "Pronto. Reinicie a sessao grafica para testar."
