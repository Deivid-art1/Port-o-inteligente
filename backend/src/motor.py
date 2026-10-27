import copy
import threading
import time

from src.identidade import Identidade
from src.portao import Portao


class Motor:
    def __init__(self, camera, registro):
        self.camera = camera
        self.registro = registro

        self.identidade = Identidade()
        self.portao = Portao()

        self._lock = threading.Lock()
        self._thread = None
        self._parar = threading.Event()

        self._estado = {
            "status": "inicializando",
            "resultado": "inconclusivo",
            "pct_rosa": None,
            "pct_tulipa": None,
            "progresso": 0,
            "amostras": 0,
            "camera_ativa": False,
            "identidade": {},
            "acesso": None,
            "erro": None,
        }

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        self._parar.clear()
        self._thread = threading.Thread(
            target=self._executar,
            daemon=True,
            name="motor-portao",
        )
        self._thread.start()

    def stop(self):
        self._parar.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2)

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self._estado)

    def _atualizar(self, **dados):
        with self._lock:
            self._estado.update(dados)

    def _executar(self):
        while not self._parar.is_set():
            try:
                frame = self.camera.get_frame()

                if frame is None:
                    self._atualizar(
                        camera_ativa=False,
                        status="aguardando_camera",
                        resultado="Aguardando câmera",
                        acesso=None,
                        erro=None,
                    )
                    time.sleep(0.1)
                    continue

                self._atualizar(camera_ativa=True)

                decisao_acesso = self.identidade.processar(frame)
                acesso = None

                if decisao_acesso:
                    acionado = self.portao.acionar(decisao_acesso)
                    acesso = {
                        "status": "autorizado",
                        "cadastro": decisao_acesso["cadastro"],
                        "fatores": decisao_acesso["fatores"],
                        "portao_acionado": acionado,
                    }
                    self.registro.registrar(
                        resultado=f"Reconhecido: {decisao_acesso['cadastro']}",
                        pct_rosa=None,
                        pct_tulipa=None,
                        frame=frame,
                        acao="reconhecimento_facial",
                    )

                identidade = self.identidade.estado()
                reconhecido = bool(identidade.get("evidencias_ativas"))

                self._atualizar(
                    status="decidido" if acesso else "analisando",
                    resultado=(
                        f"Autorizado: {acesso['cadastro']}" if acesso
                        else "Reconhecimento em análise" if reconhecido
                        else "Aguardando reconhecimento facial"
                    ),
                    pct_rosa=None,
                    pct_tulipa=None,
                    progresso=0,
                    amostras=0,
                    identidade=identidade,
                    acesso=acesso,
                    erro=None,
                )

            except Exception as erro:
                self._atualizar(erro=str(erro))
                print(f"Erro no motor: {erro}")
                time.sleep(0.2)

            time.sleep(0.05)
