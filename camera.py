"""
Captura da webcam via OpenCV, exposta como MJPEG para o navegador.

A janela do cv2.imshow() e uma janela nativa do sistema — nao da para
embutir numa pagina HTML. Entao aqui a captura e a mesma do cam.py, mas os
quadros sao codificados em JPEG e enviados no formato multipart, que o
Firefox exibe direto numa tag <img>.

Uma unica thread le a camera e guarda o ultimo quadro; todos os clientes
leem desse quadro. Assim o /dev/video nao e aberto duas vezes (recarregar a
pagina abriria uma segunda captura e daria "device busy").

Os padroes sao os mesmos do cam.py: dispositivo 0, backend automatico e
nenhuma resolucao/fps forcados (no cam.py essas linhas estao comentadas).
Forcar um modo que a camera termica nao suporta faz a captura falhar, entao
so mexa nisso se precisar:

    CAM_INDICE    indice do dispositivo      (padrao 0, como no cam.py)
    CAM_BACKEND   auto | v4l2                (padrao auto, como no cam.py)
    CAM_LARGURA   largura, se quiser forcar  (padrao: nao forca)
    CAM_ALTURA    altura, se quiser forcar   (padrao: nao forca)
    CAM_FPS       fps, se quiser forcar      (padrao: nao forca)
    CAM_ESPELHAR  1 para espelhar            (padrao 0)
    CAM_QUALIDADE qualidade do JPEG 1-100    (padrao 80)
"""

import os
import threading
import time

LIMITE = "quadro"


def _env_int(nome, padrao=None):
    valor = os.environ.get(nome)
    if valor is None or valor == "":
        return padrao
    try:
        return int(valor)
    except ValueError:
        return padrao


class Camera:
    def __init__(self):
        self.indice    = _env_int("CAM_INDICE", 0)
        self.largura   = _env_int("CAM_LARGURA")     # None = nao forca
        self.altura    = _env_int("CAM_ALTURA")
        self.fps       = _env_int("CAM_FPS")
        self.qualidade = _env_int("CAM_QUALIDADE", 80)
        self.espelhar  = os.environ.get("CAM_ESPELHAR", "0") == "1"
        self.backend   = os.environ.get("CAM_BACKEND", "auto")

        self._jpeg = None
        self._erro = None
        self._contador = 0
        self._novo = threading.Condition()
        self._thread = None
        self._parar = threading.Event()

    # ---------- controle ----------

    def iniciar(self):
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._laco, daemon=True)
        self._thread.start()

    def parar(self):
        self._parar.set()

    @property
    def erro(self):
        return self._erro

    # ---------- captura ----------

    def _abrir(self, cv2):
        if self.backend == "v4l2":
            cap = cv2.VideoCapture(self.indice, cv2.CAP_V4L2)
        else:
            cap = cv2.VideoCapture(self.indice)   # igual ao cam.py
        if self.largura:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.largura)
        if self.altura:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.altura)
        if self.fps:
            cap.set(cv2.CAP_PROP_FPS, self.fps)
        return cap

    def _laco(self):
        try:
            import cv2
        except ImportError:
            self._erro = ("OpenCV nao instalado — rode: "
                          "pip install opencv-python")
            return

        cap = None
        while not self._parar.is_set():
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                cap = self._abrir(cv2)
                if not cap.isOpened():
                    self._erro = (f"nao consegui abrir a camera {self.indice} "
                                  f"(backend {self.backend})")
                    # Tenta de novo: a camera pode aparecer depois do boot.
                    time.sleep(2)
                    continue
                self._erro = None

            ok, quadro = cap.read()
            if not ok or quadro is None:
                self._erro = "camera parou de entregar quadros"
                cap.release()
                cap = None
                time.sleep(1)
                continue

            if self.espelhar:
                quadro = cv2.flip(quadro, 1)

            ok, buf = cv2.imencode(
                ".jpg", quadro,
                [int(cv2.IMWRITE_JPEG_QUALITY), self.qualidade],
            )
            if not ok:
                continue

            with self._novo:
                self._jpeg = buf.tobytes()
                self._contador += 1
                self._erro = None
                self._novo.notify_all()

        if cap is not None:
            cap.release()

    # ---------- consumo ----------

    def quadros(self, timeout=5.0):
        """Gera os pedacos multipart do MJPEG, um por quadro novo."""
        self.iniciar()
        visto = -1
        while not self._parar.is_set():
            with self._novo:
                if self._contador == visto:
                    self._novo.wait(timeout)
                if self._contador == visto:      # timeout: camera travada
                    return
                visto = self._contador
                jpeg = self._jpeg

            if jpeg is None:                     # ainda nao veio quadro nenhum
                continue

            yield (
                b"--" + LIMITE.encode() + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                + jpeg + b"\r\n"
            )


camera = Camera()
