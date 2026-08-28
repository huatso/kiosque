# kiosque

Página de kiosque com uma barra preta no topo (altura ajustável em `vh`) e
botões de desligar / reiniciar a máquina.

## Instalação na máquina do kiosque

```bash
git clone git@github.com:huatso/kiosque.git ~/Documents/kiosque
cd ~/Documents/kiosque
./instalar-autostart.sh
```

Isso grava duas entradas em `~/.config/autostart`:

- `kiosque-server.desktop` — sobe o `server.py`
- `firefox-kiosk.desktop`  — espera a porta responder e abre
  `firefox --kiosk http://localhost:8000/`

Reinicie a sessão gráfica para testar.

## Rodar na mão

```bash
python3 server.py          # http://localhost:8000
firefox --kiosk http://localhost:8000/
```

## Arquivos

- `index.html` — a página. Barra preta fixa no topo em `6.5vh` (padrão),
  ajustável em tempo real pelo slider/campo numérico. Tecla `c` mostra ou
  esconde o painel de ajuste; `Esc` cancela uma confirmação de energia.
- `server.py` — servidor local. Serve os arquivos e expõe
  `POST /api/poweroff`, `POST /api/reboot` e `GET /api/erro`. Só aceita
  chamadas de `127.0.0.1`.
- `abrir-navegador.sh` — espera a porta e abre o Firefox em kiosque.
- `instalar-autostart.sh` — instala as entradas de autostart.
- `iniciar.sh` — alternativa para Chromium (`--kiosk`), sobe servidor e
  navegador juntos e derruba o servidor ao fechar.

## Por que precisa do server.py

Uma página HTML não tem acesso ao sistema operacional — JavaScript no
navegador não consegue desligar o computador. Os botões chamam o servidor
local, que executa `systemctl poweroff` / `systemctl reboot` de fato.

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
