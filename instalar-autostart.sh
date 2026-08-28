#!/usr/bin/env bash
# Verifica o ambiente conda e instala as entradas de autostart apontando
# para esta pasta.
set -uo pipefail

PASTA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINO="$HOME/.config/autostart"
AMBIENTE="${AMBIENTE:-base}"

# Modulos necessarios: "modulo_python pacote_pip"
REQUISITOS=(
  "cv2 opencv-python"
  "numpy numpy"
)

falhar() { echo "ERRO: $*" >&2; exit 1; }

# ---------------------------------------------------------------- conda

echo "== ambiente conda =="

raiz_conda=""
if [ -n "${CONDA_EXE:-}" ]; then
  raiz_conda="$(dirname "$(dirname "$CONDA_EXE")")"
elif command -v conda >/dev/null 2>&1; then
  raiz_conda="$(conda info --base 2>/dev/null)"
else
  for c in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/miniforge3" /opt/conda; do
    [ -x "$c/bin/conda" ] && raiz_conda="$c" && break
  done
fi

[ -n "$raiz_conda" ] && [ -x "$raiz_conda/bin/conda" ] \
  || falhar "conda não encontrado (procurei em CONDA_EXE, PATH, ~/miniconda3, ~/anaconda3, ~/miniforge3, /opt/conda)"
echo "conda:    $raiz_conda"

# Ativa o ambiente. O hook funciona mesmo em shell nao-interativo, onde o
# 'conda activate' sozinho falharia por falta do init no .bashrc.
eval "$("$raiz_conda/bin/conda" shell.bash hook 2>/dev/null)" \
  || falhar "não consegui carregar o conda"

conda env list | awk '{print $1}' | grep -qx "$AMBIENTE" \
  || falhar "ambiente '$AMBIENTE' não existe (veja: conda env list)"

conda activate "$AMBIENTE" || falhar "não consegui ativar o ambiente '$AMBIENTE'"

PYTHON="$(command -v python)"
echo "ambiente: $AMBIENTE"
echo "python:   $PYTHON ($("$PYTHON" --version 2>&1))"

# ------------------------------------------------------------- pacotes

echo
echo "== pacotes =="

faltando=()
for requisito in "${REQUISITOS[@]}"; do
  modulo="${requisito%% *}"
  pacote="${requisito##* }"
  if versao=$("$PYTHON" -c "import $modulo; print(getattr($modulo, '__version__', 'ok'))" 2>/dev/null); then
    echo "  ok       $pacote ($versao)"
  else
    echo "  FALTANDO $pacote"
    faltando+=("$pacote")
  fi
done

if [ ${#faltando[@]} -gt 0 ]; then
  echo
  echo "Instalando em '$AMBIENTE': ${faltando[*]}"
  "$PYTHON" -m pip install "${faltando[@]}" || falhar "pip install falhou"

  for requisito in "${REQUISITOS[@]}"; do
    modulo="${requisito%% *}"
    "$PYTHON" -c "import $modulo" 2>/dev/null \
      || falhar "'$modulo' continua faltando depois da instalação"
  done
  echo "Pacotes instalados."
fi

# Se a camera nao abre nao da para instalar nada, mas avisar agora e melhor
# do que descobrir no boot com a tela preta.
if ! ls /dev/video* >/dev/null 2>&1; then
  echo
  echo "AVISO: nenhum /dev/video* encontrado — a câmera está conectada?"
fi

command -v firefox >/dev/null 2>&1 \
  || echo "AVISO: firefox não encontrado no PATH"

# ------------------------------------------------------------ autostart

echo
echo "== autostart =="

mkdir -p "$DESTINO"
for arquivo in kiosque-server firefox-kiosk; do
  sed -e "s|__PASTA__|$PASTA|g" \
      -e "s|__PYTHON__|$PYTHON|g" \
      "$PASTA/autostart/$arquivo.desktop" > "$DESTINO/$arquivo.desktop"
  echo "  instalado: $DESTINO/$arquivo.desktop"
done

echo
echo "Pronto. O servidor vai subir com $PYTHON."
echo "Reinicie a sessão gráfica para testar."
