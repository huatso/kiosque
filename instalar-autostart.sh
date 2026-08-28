#!/usr/bin/env bash
# Descobre um python com os pacotes necessarios (instalando o que faltar) e
# instala as entradas de autostart apontando para esta pasta.
#
# Ordem de preferencia do interpretador:
#   1. $PYTHON, se voce passar          PYTHON=/caminho/python ./instalar-autostart.sh
#   2. o venv local desta pasta         .venv/bin/python
#   3. o python do ambiente conda       (se houver conda na maquina)
#   4. o python3 do sistema
# Se nenhum tiver os pacotes, cria o venv local e instala neles.
set -uo pipefail

PASTA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINO="$HOME/.config/autostart"
AMBIENTE="${AMBIENTE:-base}"
VENV="$PASTA/.venv"

# Modulos necessarios: "modulo_python pacote_pip"
REQUISITOS=(
  "cv2 opencv-python"
  "numpy numpy"
)

falhar() { echo "ERRO: $*" >&2; exit 1; }

# Diz se o python passado importa todos os modulos requeridos.
tem_tudo() {
  local py="$1" requisito modulo
  [ -x "$py" ] || return 1
  for requisito in "${REQUISITOS[@]}"; do
    modulo="${requisito%% *}"
    "$py" -c "import $modulo" >/dev/null 2>&1 || return 1
  done
  return 0
}

listar_versoes() {
  local py="$1" requisito modulo pacote versao
  for requisito in "${REQUISITOS[@]}"; do
    modulo="${requisito%% *}"; pacote="${requisito##* }"
    versao=$("$py" -c "import $modulo; print(getattr($modulo,'__version__','ok'))" 2>/dev/null) \
      && echo "  ok       $pacote ($versao)" \
      || echo "  FALTANDO $pacote"
  done
}

# ------------------------------------------------------ achar candidatos

echo "== interpretador python =="

candidatos=()
[ -n "${PYTHON:-}" ] && candidatos+=("$PYTHON")
candidatos+=("$VENV/bin/python")

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
if [ -n "$raiz_conda" ] && [ -x "$raiz_conda/bin/conda" ]; then
  echo "conda encontrado em $raiz_conda (ambiente '$AMBIENTE')"
  if [ "$AMBIENTE" = "base" ]; then
    candidatos+=("$raiz_conda/bin/python")
  else
    candidatos+=("$raiz_conda/envs/$AMBIENTE/bin/python")
  fi
else
  echo "conda não encontrado — seguindo sem ele"
fi

candidatos+=("$(command -v python3 2>/dev/null)" "/usr/bin/python3")

PYTHON_ESCOLHIDO=""
for py in "${candidatos[@]}"; do
  [ -n "$py" ] || continue
  if tem_tudo "$py"; then PYTHON_ESCOLHIDO="$py"; break; fi
done

# ---------------------------------------------- instalar o que faltar

if [ -n "$PYTHON_ESCOLHIDO" ]; then
  echo "python:   $PYTHON_ESCOLHIDO ($("$PYTHON_ESCOLHIDO" --version 2>&1))"
  echo
  echo "== pacotes =="
  listar_versoes "$PYTHON_ESCOLHIDO"
else
  echo "Nenhum python com os pacotes necessários. Faltando:"
  base_py="$(command -v python3 2>/dev/null || echo /usr/bin/python3)"
  listar_versoes "$base_py"

  echo
  echo "Criando o venv em $VENV"
  # --system-site-packages: se o opencv vier do apt (python3-opencv), o venv
  # enxerga e nao precisa baixar de novo.
  if [ ! -x "$VENV/bin/python" ]; then
    "$base_py" -m venv --system-site-packages "$VENV" \
      || falhar "não consegui criar o venv. No Ubuntu/Debian instale primeiro:
    sudo apt install python3-venv"
  fi
  PYTHON_ESCOLHIDO="$VENV/bin/python"

  faltando=()
  for requisito in "${REQUISITOS[@]}"; do
    modulo="${requisito%% *}"; pacote="${requisito##* }"
    "$PYTHON_ESCOLHIDO" -c "import $modulo" >/dev/null 2>&1 || faltando+=("$pacote")
  done

  if [ ${#faltando[@]} -gt 0 ]; then
    echo "Instalando: ${faltando[*]}"
    "$PYTHON_ESCOLHIDO" -m pip install --upgrade pip >/dev/null 2>&1
    "$PYTHON_ESCOLHIDO" -m pip install "${faltando[@]}" \
      || falhar "pip install falhou. Alternativa pelo sistema:
    sudo apt install python3-opencv"
  fi

  tem_tudo "$PYTHON_ESCOLHIDO" \
    || falhar "os pacotes continuam faltando depois da instalação"

  echo
  echo "== pacotes =="
  listar_versoes "$PYTHON_ESCOLHIDO"
fi

# ------------------------------------------------------------- avisos

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
      -e "s|__PYTHON__|$PYTHON_ESCOLHIDO|g" \
      "$PASTA/autostart/$arquivo.desktop" > "$DESTINO/$arquivo.desktop"
  echo "  instalado: $DESTINO/$arquivo.desktop"
done

echo
echo "Pronto. O servidor vai subir com $PYTHON_ESCOLHIDO."
echo "Reinicie a sessão gráfica para testar."
