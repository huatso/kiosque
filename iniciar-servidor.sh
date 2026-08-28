#!/usr/bin/env bash
# Sobe o server.py guardando a saida num log. O autostart nao abre terminal
# nenhum: sem isto, uma falha no boot (porta ocupada, pacote faltando) some
# sem deixar rastro.
#
# O caminho do python vem como primeiro argumento; o instalar-autostart.sh
# preenche isso na entrada do autostart.
set -u

PASTA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${KIOSQUE_LOG:-$HOME/.cache/kiosque.log}"
PYTHON="${1:-python3}"

mkdir -p "$(dirname "$LOG")"

# Mantem so as ultimas 500 linhas para o log nao crescer sem fim.
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 500 ]; then
  tail -n 200 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

{
  echo
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') — iniciando ====="
  echo "python: $PYTHON"
} >> "$LOG"

# Rodando na mao (terminal), mostra tambem na tela: senao o erro vai so
# para o log e o comando parece falhar sem motivo. No autostart nao ha
# terminal, entao vai so para o log.
if [ -t 1 ]; then
  exec "$PYTHON" "$PASTA/server.py" 2>&1 | tee -a "$LOG"
else
  exec "$PYTHON" "$PASTA/server.py" >> "$LOG" 2>&1
fi
