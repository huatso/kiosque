#!/usr/bin/env bash
# Espera o servidor local subir e abre o Firefox em modo kiosque.
set -u

PORTA="${PORTA:-8000}"
URL="http://localhost:$PORTA/"

# O autostart dispara o servidor e o navegador ao mesmo tempo; sem esperar,
# o Firefox pode abrir antes da porta responder e mostrar erro de conexao.
for _ in $(seq 1 100); do
  (echo > /dev/tcp/127.0.0.1/"$PORTA") 2>/dev/null && break
  sleep 0.1
done

exec firefox --kiosk "$URL"
