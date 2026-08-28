# kiosque

Página de kiosque que mostra a imagem da câmera térmica em tela cheia, com
uma faixa preta fixa no topo mascarando a área que não aparece na tela, e
botões de desligar / reiniciar a máquina.

## Instalação na máquina do kiosque

```bash
git clone git@github.com:huatso/kiosque.git ~/Documents/kiosque
cd ~/Documents/kiosque
./instalar-autostart.sh
```

O `instalar-autostart.sh` faz, nesta ordem:

1. procura um python que já tenha `opencv-python` e `numpy`, nesta ordem:
   `$PYTHON` (se você passar), o venv local `.venv`, o ambiente conda
   (**se houver conda na máquina** — não é obrigatório) e o `python3` do
   sistema;
2. se nenhum servir, cria o venv local `.venv` (com
   `--system-site-packages`, para aproveitar um `python3-opencv` vindo do
   apt) e instala os pacotes que faltam nele;
3. avisa se não houver `/dev/video*` ou `firefox`;
4. grava duas entradas em `~/.config/autostart`:
   - `kiosque-server.desktop` — sobe o `server.py` **com o python do
     ambiente conda**, gravado por caminho absoluto (o `python3` do PATH da
     sessão gráfica pode ser outro, sem o `cv2`);
   - `firefox-kiosk.desktop` — espera a porta responder e abre
     `firefox --kiosk http://localhost:8000/`.

Para forçar um interpretador específico:
`PYTHON=/caminho/do/python ./instalar-autostart.sh`
(ou `AMBIENTE=meuenv`, se a máquina tiver conda).

Se o `venv` não puder ser criado, o script diz o que instalar:
`sudo apt install python3-venv` — ou, como alternativa,
`sudo apt install python3-opencv`.

Reinicie a sessão gráfica para testar.

## Rodar na mão

```bash
python3 server.py          # http://localhost:8000
firefox --kiosk http://localhost:8000/
```

## Arquivos

- `index.html` — a página. Faixa preta fixa de `6.5vh` no topo, câmera
  ocupando os `93.5vh` restantes. `Esc` cancela uma confirmação de energia.
- `camera.py` — captura da câmera via OpenCV, servida como MJPEG.
- `testar-camera.py` — sonda quais índices/backends abrem a câmera.
- `server.py` — servidor local. Serve os arquivos e expõe `GET /cam`,
  `GET`/`POST /api/cam`, `POST /api/poweroff`, `POST /api/reboot` e
  `GET /api/erro`. Os comandos de energia só aceitam `127.0.0.1`.
- `abrir-navegador.sh` — espera a porta e abre o Firefox em kiosque.
- `instalar-autostart.sh` — verifica o ambiente conda e os pacotes, e
  instala as entradas de autostart.
- `iniciar.sh` — alternativa para Chromium (`--kiosk`), sobe servidor e
  navegador juntos e derruba o servidor ao fechar.

## Câmera

A janela do `cv2.imshow()` é uma janela nativa do sistema — não dá para
embutir numa página HTML. Então `camera.py` faz a mesma captura do
`cam.py`, codifica cada quadro em JPEG e envia como MJPEG em `/cam`; a
página exibe isso numa tag `<img>`.

Uma única thread lê a câmera e todos os clientes leem do último quadro, para
não abrir o `/dev/video` duas vezes (recarregar a página daria "device
busy"). Se a câmera não abrir, a página mostra o motivo na tela e tenta
reconectar sozinha a cada 3s.

No canto inferior direito da página há um seletor com os `/dev/videoN`
encontrados e o backend (`auto` / `v4l2`). Trocar ali reabre a captura na
hora, e a escolha fica salva em `config.json` — sobrevive ao reboot.

Se a imagem não aparecer, o motivo vem escrito na tela. Para investigar no
terminal, pare o servidor (senão ele segura o dispositivo) e rode a sonda:

```bash
pkill -f server.py
./testar-camera.py
```

Ela lista os dispositivos, mostra quem está usando cada um e testa cada
índice com os dois backends, dizendo qual funcionou e em que resolução.

Os padrões são os mesmos do `cam.py`: dispositivo `0`, backend automático e
**sem** forçar resolução ou fps. Forçar um modo que a câmera térmica não
suporta faz a captura falhar. Para ajustar, use variáveis de ambiente no
`kiosque-server.desktop` ou na linha de comando:

```bash
CAM_INDICE=2 CAM_BACKEND=v4l2 python3 server.py
```

| variável | padrão | o que faz |
|---|---|---|
| `CAM_INDICE` | `0` | índice do dispositivo (o `cam2.py` usa `2`) |
| `CAM_BACKEND` | `auto` | `auto` ou `v4l2` |
| `CAM_LARGURA` / `CAM_ALTURA` | não força | resolução, se precisar fixar |
| `CAM_FPS` | não força | fps, se precisar fixar |
| `CAM_ESPELHAR` | `0` | `1` espelha horizontalmente |
| `CAM_QUALIDADE` | `80` | qualidade do JPEG (1–100) |

Precisa do OpenCV — o `instalar-autostart.sh` cuida disso, ou na mão:
`pip install opencv-python`.

## Por que precisa do server.py

Uma página HTML não tem acesso ao sistema operacional — JavaScript no
navegador não consegue desligar o computador nem abrir `/dev/video`. Os
botões chamam o servidor local, que executa `systemctl poweroff` /
`systemctl reboot` de fato.

Abrir a página como `file://` também funciona (ela detecta e fala com
`http://localhost:8000`), mas o servidor precisa estar rodando de qualquer
jeito — por isso o autostart usa a URL `http://localhost:8000/`.

## Se o desligamento não acontecer

O `server.py` tenta `systemctl poweroff` e, se o polkit recusar, tenta
`sudo -n systemctl poweroff`. O motivo da falha aparece na própria página
(consultado em `GET /api/erro`), já que em modo kiosque não dá para abrir o
console do navegador.

Para liberar o `sudo` sem senha, crie `/etc/sudoers.d/kiosque` com
`visudo -f /etc/sudoers.d/kiosque`:

```
transpetro ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff, /usr/bin/systemctl reboot
```

(troque `transpetro` pelo usuário que roda o kiosque)
