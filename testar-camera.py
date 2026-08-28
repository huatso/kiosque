#!/usr/bin/env python3
"""
Descobre qual indice/backend abre a camera e o que ela entrega.

Rode com o server.py PARADO — enquanto ele roda, ele segura o /dev/video e
o teste vai acusar "device busy":

    pkill -f server.py
    ./testar-camera.py

No fim ele mostra a linha de configuracao para usar no kiosque.
"""

import glob
import os
import subprocess
import sys

print("== dispositivos ==")
dispositivos = sorted(glob.glob("/dev/video*"))
print("  " + (", ".join(dispositivos) if dispositivos else "nenhum /dev/video*"))

try:
    saida = subprocess.run(["v4l2-ctl", "--list-devices"],
                           capture_output=True, text=True, timeout=10).stdout
    if saida.strip():
        print("\n== v4l2-ctl --list-devices ==")
        for linha in saida.strip().splitlines():
            print("  " + linha)
except (FileNotFoundError, subprocess.TimeoutExpired):
    print("  (v4l2-ctl ausente: sudo apt install v4l-utils)")

print("\n== quem esta usando ==")
try:
    r = subprocess.run(["fuser", "-v"] + dispositivos,
                       capture_output=True, text=True, timeout=10)
    print(("  " + (r.stderr or r.stdout).strip().replace("\n", "\n  "))
          if (r.stderr or r.stdout).strip() else "  ninguem")
except (FileNotFoundError, subprocess.TimeoutExpired):
    print("  (fuser ausente)")

try:
    import cv2
except ImportError:
    print("\nERRO: OpenCV não instalado neste python:", sys.executable)
    print("Rode o ./instalar-autostart.sh, ou:")
    print(f"  {sys.executable} -m pip install opencv-python")
    sys.exit(1)

print(f"\n== abrindo (OpenCV {cv2.__version__}, {sys.executable}) ==")

# Silencia os avisos do backend, que poluem a saida a cada tentativa falha.
os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass

# Indices dos /dev/videoN existentes; se nao houver nenhum, tenta 0..5.
indices = [int(d.removeprefix("/dev/video")) for d in dispositivos
           if d.removeprefix("/dev/video").isdigit()] or list(range(6))

funcionaram = []
for indice in indices:
    for nome, backend in (("auto", cv2.CAP_ANY), ("v4l2", cv2.CAP_V4L2)):
        cap = cv2.VideoCapture(indice, backend)
        if not cap.isOpened():
            print(f"  video{indice} {nome:4} -> não abriu")
            cap.release()
            continue
        ok, quadro = cap.read()
        if ok and quadro is not None:
            altura, largura = quadro.shape[:2]
            canais = quadro.shape[2] if quadro.ndim > 2 else 1
            fps = cap.get(cv2.CAP_PROP_FPS)
            # O cam.py so precisa exibir o quadro; o kiosque precisa
            # codificar em JPEG, que e mais exigente quanto ao formato.
            try:
                from camera import Camera
                jpeg = Camera()._para_jpeg(cv2, quadro)
                conversao = f"jpeg {len(jpeg)}B" if jpeg else "JPEG FALHOU"
            except Exception as e:
                conversao = f"JPEG FALHOU ({type(e).__name__})"
            print(f"  video{indice} {nome:4} -> OK  {largura}x{altura} "
                  f"{canais}ch  {fps:.0f}fps  dtype={quadro.dtype}  {conversao}")
            funcionaram.append((indice, nome))
        else:
            print(f"  video{indice} {nome:4} -> abriu mas não leu quadro")
        cap.release()

print()
if not funcionaram:
    print("Nenhuma combinação funcionou.")
    print("Verifique se a câmera está conectada, se o server.py está parado")
    print("e se o usuário está no grupo 'video':  id -nG | grep video")
    sys.exit(1)

indice, backend = funcionaram[0]
print(f"Funcionou: video{indice} com backend {backend}.")
if (indice, backend) != (0, "auto"):
    print("\nConfigure o kiosque com isto — coloque no Exec do arquivo")
    print("~/.config/autostart/kiosque-server.desktop, antes do python:")
    print(f"\n  env CAM_INDICE={indice} CAM_BACKEND={backend} <python> "
          f"<pasta>/server.py\n")
    print("Ou teste na mão:")
    print(f"  CAM_INDICE={indice} CAM_BACKEND={backend} python3 server.py")
else:
    print("É o padrão do kiosque, não precisa configurar nada.")
