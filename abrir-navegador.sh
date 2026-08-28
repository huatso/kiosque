#!/usr/bin/env bash
# Espera o servidor local subir e abre o Firefox em modo kiosque.
set -u

PORTA="${PORTA:-8000}"
URL="http://localhost:$PORTA/"

# O autostart dispara o servidor e o navegador ao mesmo tempo. Se o Firefox
# chegar antes, ele para na tela de erro dele — e ali a nossa pagina nem
# carregou, entao nada reconecta sozinho: a tela fica morta ate alguem
# apertar F5.
#
# Nao basta esperar a porta abrir: entre o bind e a primeira resposta HTTP
# ainda ha uma janela. Espera-se o 200 de verdade.
pronto=0
for _ in $(seq 1 150); do          # ate 30s
  if curl -s -o /dev/null -m 2 -f "$URL"; then pronto=1; break; fi
  sleep 0.2
done

if [ "$pronto" != 1 ]; then
  echo "servidor nao respondeu em $URL depois de 30s; abrindo mesmo assim" >&2
fi

exec firefox --kiosk "$URL"
