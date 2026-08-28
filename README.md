# kiosque

Página de kiosque com uma barra preta no topo (altura ajustável em `vh`) e
botões de desligar / reiniciar a máquina.

## Rodar

```bash
./iniciar.sh          # sobe o servidor e abre o Chromium em --kiosk
```

Ou separadamente:

```bash
python3 server.py     # http://localhost:8000
```

## Arquivos

- `index.html` — a página. Barra preta fixa no topo em `6.5vh` (padrão),
  ajustável em tempo real pelo slider/campo numérico. Tecla `c` mostra ou
  esconde o painel de ajuste; `Esc` cancela uma confirmação de energia.
- `server.py` — servidor local. Serve os arquivos e expõe
  `POST /api/poweroff` e `POST /api/reboot`, que rodam `systemctl poweroff`
  e `systemctl reboot`. Só aceita chamadas de `127.0.0.1`.
- `iniciar.sh` — sobe o servidor e abre o navegador em modo kiosque.

## Por que precisa do server.py

Uma página HTML não tem acesso ao sistema operacional — JavaScript no
navegador não consegue desligar o computador. Os botões chamam o servidor
local, que executa o comando de fato.

Se `systemctl poweroff` pedir senha (sessão não considerada ativa pelo
polkit), libere sem senha em `/etc/sudoers.d/kiosque`:

```
tso ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff, /usr/bin/systemctl reboot
```

e troque os comandos em `server.py` para `["sudo", "systemctl", "poweroff"]`.
