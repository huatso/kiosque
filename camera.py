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

import glob
import json
import os
import threading
import time

LIMITE = "quadro"

# Guarda a camera escolhida na tela para sobreviver ao reboot do kiosque.
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# A GuideCamera nao comeca a mandar video sozinha: ela enumera no USB, aceita
# a configuracao de formato e o STREAMON, mas nao entrega buffer nenhum ate
# receber um comando pelo canal serial (interface CDC da propria camera). E o
# mesmo comando que o app do Transpetro dispara ao abrir o "Camera Viewer".
# Protocolo: 55aa + payload + XOR do payload + f0.
SERIAL = os.environ.get("CAM_SERIAL", "/dev/ttyACM0")
SERIAL_PAYLOAD = os.environ.get("CAM_SERIAL_CMD", "0703000600000003")


def _quadro_guide(payload_hex):
    corpo = bytes.fromhex(payload_hex)
    xor = 0
    for byte in corpo:
        xor ^= byte
    return bytes.fromhex("55aa") + corpo + bytes([xor]) + bytes.fromhex("f0")


def acordar_camera():
    """Manda o comando de inicializacao pela serial da camera.

    Devolve a resposta em hex, ou None se nao deu. Falhar aqui nao e fatal:
    se a camera ja estiver mandando video, o comando so e redundante.
    """
    import termios

    if not SERIAL or not os.path.exists(SERIAL):
        return None
    fd = None
    try:
        fd = os.open(SERIAL, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attrs = termios.tcgetattr(fd)
        attrs[4] = attrs[5] = termios.B115200
        attrs[3] &= ~(termios.ICANON | termios.ECHO | termios.ECHOE | termios.ISIG)
        attrs[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        os.write(fd, _quadro_guide(SERIAL_PAYLOAD))
        time.sleep(0.5)
        try:
            return os.read(fd, 256).hex() or None
        except BlockingIOError:
            return None
    except OSError:
        return None
    finally:
        if fd is not None:
            os.close(fd)


def dispositivos():
    """Indices dos /dev/videoN presentes na maquina."""
    indices = []
    for caminho in sorted(glob.glob("/dev/video*")):
        sufixo = caminho[len("/dev/video"):]
        if sufixo.isdigit():
            indices.append(int(sufixo))
    return sorted(indices)


def _ler_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


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
        salvo = _ler_config()
        # A variavel de ambiente, se vier definida, manda; senao vale o que
        # foi escolhido na tela; senao o padrao do cam.py.
        self.indice    = _env_int("CAM_INDICE", salvo.get("indice", 0))
        self.largura   = _env_int("CAM_LARGURA", salvo.get("largura"))
        self.altura    = _env_int("CAM_ALTURA", salvo.get("altura"))
        self.fps       = _env_int("CAM_FPS", salvo.get("fps"))
        self.qualidade = _env_int("CAM_QUALIDADE", 80)
        self.espelhar  = os.environ.get("CAM_ESPELHAR", "0") == "1"
        self.backend   = os.environ.get(
            "CAM_BACKEND", salvo.get("backend", "auto"))

        self._jpeg = None
        self._erro = None
        self._formato = None
        self._contador = 0
        self._novo = threading.Condition()
        self._thread = None
        self._parar = threading.Event()
        self._troca = threading.Lock()

    # ---------- controle ----------

    def iniciar(self):
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()
        self._thread = threading.Thread(target=self._laco, daemon=True)
        self._thread.start()

    def parar(self):
        self._parar.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def trocar(self, indice=None, backend=None):
        """Troca a camera em uso e guarda a escolha."""
        with self._troca:
            if indice is not None:
                self.indice = int(indice)
            if backend is not None:
                self.backend = backend

            self.parar()
            with self._novo:
                self._jpeg = None      # nao mostra o quadro da camera antiga
                self._erro = None
                self._formato = None
            self._parar.clear()
            self.iniciar()

            try:
                with open(CONFIG, "w") as f:
                    json.dump({"indice": self.indice,
                               "backend": self.backend,
                               "largura": self.largura,
                               "altura": self.altura,
                               "fps": self.fps}, f)
            except OSError:
                pass               # nao poder salvar nao impede a troca

    def estado(self):
        return {
            "indice": self.indice,
            "backend": self.backend,
            "disponiveis": dispositivos(),
            "erro": self._erro,
            "largura": self.largura,
            "altura": self.altura,
            "formato": self._formato,      # shape e dtype do ultimo quadro
            "quadros": self._contador,
            "ok": self._erro is None and self._jpeg is not None,
        }

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
                acordar_camera()
                cap = self._abrir(cv2)
                if not cap.isOpened():
                    # A causa mais comum e outro processo segurando o
                    # dispositivo — inclusive um server.py antigo esquecido.
                    self._erro = (
                        f"não consegui abrir a câmera {self.indice} "
                        f"(backend {self.backend}) — em uso por outro "
                        f"programa? veja: fuser -v /dev/video{self.indice}"
                    )
                    # Tenta de novo: a camera pode aparecer depois do boot.
                    time.sleep(2)
                    continue

            ok, quadro = cap.read()
            if not ok or quadro is None:
                self._erro = (
                    f"a câmera {self.indice} abre mas não entrega imagem "
                    f"(select() timeout). Teste fora do kiosque: "
                    f"v4l2-ctl -d /dev/video{self.indice} --stream-mmap "
                    f"--stream-count=3"
                )
                cap.release()
                cap = None
                time.sleep(1)
                continue

            self._formato = f"{quadro.shape} {quadro.dtype}"

            try:
                jpeg = self._para_jpeg(cv2, quadro)
            except Exception as e:
                # Sem este try, um formato inesperado derruba a thread e a
                # tela fica preta sem dizer por que.
                self._erro = f"não consegui converter o quadro {self._formato}: {e}"
                time.sleep(1)
                continue

            if jpeg is None:
                self._erro = f"não consegui codificar o quadro ({self._formato})"
                time.sleep(1)
                continue

            with self._novo:
                self._jpeg = jpeg
                self._contador += 1
                self._erro = None      # so aqui: chegou imagem de verdade
                self._novo.notify_all()

        if cap is not None:
            cap.release()

    def _para_jpeg(self, cv2, quadro):
        """Converte um quadro do OpenCV em JPEG, lidando com formatos que o
        codificador nao aceita direto."""
        if self.espelhar:
            quadro = cv2.flip(quadro, 1)

        # Camera termica costuma entregar 16 bits (Y16). O cv2.imshow() do
        # cam.py escala isso sozinho ao exibir; o JPEG so aceita 8 bits, e
        # sem normalizar a imagem sai estourada.
        if quadro.dtype != "uint8":
            quadro = cv2.normalize(quadro, None, 0, 255,
                                   cv2.NORM_MINMAX).astype("uint8")

        # O codificador so aceita 1, 3 ou 4 canais. Um quadro de 2 canais
        # (YUYV cru) faz o imencode levantar excecao, nao devolver False.
        if quadro.ndim == 3 and quadro.shape[2] == 2:
            quadro = quadro[:, :, 0]

        ok, buf = cv2.imencode(
            ".jpg", quadro,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.qualidade],
        )
        return buf.tobytes() if ok else None

    # ---------- consumo ----------

    def quadros(self, timeout=5.0, espera_inicial=30.0):
        """Gera os pedacos multipart do MJPEG, um por quadro novo.

        A primeira espera e mais longa: no boot a camera leva alguns segundos
        para entregar o primeiro quadro, e desistir cedo faria o <img> dar
        erro logo de cara.
        """
        self.iniciar()
        visto = -1
        primeiro = True
        while not self._parar.is_set():
            with self._novo:
                if self._contador == visto:
                    self._novo.wait(espera_inicial if primeiro else timeout)
                if self._contador == visto:      # timeout: camera travada
                    return
                primeiro = False
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
