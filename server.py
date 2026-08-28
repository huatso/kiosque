#!/usr/bin/env python3
"""
Servidor local do kiosque.

Serve os arquivos da pasta e expoe dois endpoints que o navegador nao consegue
executar sozinho (uma pagina HTML nao tem acesso ao sistema operacional):

    POST /api/poweroff  -> systemctl poweroff
    POST /api/reboot    -> systemctl reboot
    GET  /api/erro      -> erro do ultimo comando de energia, se houve

Uso:  python3 server.py            (abre em http://localhost:8000)
      python3 server.py 8080       (outra porta)
"""

import http.server
import json
import os
import subprocess
import sys
import threading

PASTA = os.path.dirname(os.path.abspath(__file__))
PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

COMANDOS = {
    "/api/poweroff": ["systemctl", "poweroff"],
    "/api/reboot":   ["systemctl", "reboot"],
}

# Guarda o erro do ultimo comando de energia. Em modo kiosque nao da para
# abrir o console do navegador, entao a pagina consulta GET /api/erro para
# descobrir por que nada aconteceu.
ultimo_erro = None


def executar_energia(comando):
    """Roda o comando; se o polkit recusar, tenta de novo via sudo -n."""
    global ultimo_erro
    try:
        r = subprocess.run(comando, capture_output=True, text=True)
        if r.returncode == 0:
            ultimo_erro = None
            return
        erro = (r.stderr or r.stdout).strip()

        r2 = subprocess.run(["sudo", "-n"] + comando, capture_output=True, text=True)
        if r2.returncode == 0:
            ultimo_erro = None
            return
        erro2 = (r2.stderr or r2.stdout).strip()

        ultimo_erro = f"{' '.join(comando)}: {erro} | sudo: {erro2}"
    except Exception as e:
        ultimo_erro = f"{' '.join(comando)}: {e}"
    print(f"[kiosque] FALHOU -> {ultimo_erro}")


class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PASTA, **kwargs)

    def _json(self, status, payload):
        corpo = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        # Permite que a pagina aberta como file:// (origem "null") chame a API.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path == "/api/erro":
            self._json(200, {"ok": ultimo_erro is None, "erro": ultimo_erro})
            return
        super().do_GET()

    def do_POST(self):
        comando = COMANDOS.get(self.path)
        if comando is None:
            self._json(404, {"ok": False, "erro": "endpoint desconhecido"})
            return

        # So aceita chamadas da propria maquina.
        if self.client_address[0] not in ("127.0.0.1", "::1"):
            self._json(403, {"ok": False, "erro": "somente localhost"})
            return

        print(f"[kiosque] executando: {' '.join(comando)}")

        global ultimo_erro
        ultimo_erro = None

        # Responde antes de executar, senao o navegador perde a conexao
        # no meio do desligamento e mostra erro.
        self._json(200, {"ok": True, "comando": " ".join(comando)})
        try:
            self.wfile.flush()
        except Exception:
            pass

        threading.Timer(0.5, lambda: executar_energia(comando)).start()

    def log_message(self, formato, *args):
        # Silencia o log de cada arquivo estatico servido.
        pass


if __name__ == "__main__":
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", PORTA), Handler)
    print(f"[kiosque] servindo {PASTA}")
    print(f"[kiosque] http://localhost:{PORTA}")
    print("[kiosque] Ctrl+C para parar")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[kiosque] encerrado")
