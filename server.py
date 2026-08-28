#!/usr/bin/env python3
"""
Servidor local do kiosque.

Serve os arquivos da pasta e expoe dois endpoints que o navegador nao consegue
executar sozinho (uma pagina HTML nao tem acesso ao sistema operacional):

    POST /api/poweroff  -> systemctl poweroff
    POST /api/reboot    -> systemctl reboot

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


class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PASTA, **kwargs)

    def _json(self, status, payload):
        corpo = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

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

        # Responde antes de executar, senao o navegador perde a conexao
        # no meio do desligamento e mostra erro.
        self._json(200, {"ok": True, "comando": " ".join(comando)})
        try:
            self.wfile.flush()
        except Exception:
            pass

        threading.Timer(0.5, lambda: subprocess.run(comando)).start()

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
