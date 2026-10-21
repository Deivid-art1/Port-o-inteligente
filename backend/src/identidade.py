import time

import numpy as np

from src.cadastro import carregar
from src.extrator import aparencia
from src.gestos import SequenciaGestos, contar_dedos
from src.reconhecimento import extrair as extrair_rosto, similaridade

JANELA_S = 12.0          # prazo para juntar todos os fatores exigidos
COOLDOWN_S = 30.0        # intervalo mínimo entre duas liberações da mesma pessoa
INTERVALO_S = 0.5        # a identificação roda no máximo 2 vezes por segundo
LIMIAR_ROSTO = 0.363     # ponto de partida do OpenCV; calibrar com fotos reais
LIMIAR_APARENCIA = 0.85  # ponto de partida; calibrar com cena vazia como negativo


def _melhor(vec, referencias):
    if not referencias:
        return -1.0
    v = np.asarray(vec, dtype=np.float32)
    return max(similaridade(v, np.asarray(r, dtype=np.float32)) for r in referencias)


class Identidade:
    def __init__(self):
        self.cadastros = carregar()
        self.sequencia = SequenciaGestos()
        self._evidencias = {}     # (cad_id, fator) -> instante da última evidência
        self._scores = {}         # (nome, fator) -> última similaridade, para calibrar
        self._ultimo_acesso = {}  # cad_id -> instante da última liberação
        self._ultimo_calculo = 0.0

    def processar(self, frame, agora=None):
        """Devolve uma decisão de acesso quando os fatores de um cadastro são cumpridos, senão None."""
        agora = time.monotonic() if agora is None else agora
        if not self.cadastros or agora - self._ultimo_calculo < INTERVALO_S:
            return None
        self._ultimo_calculo = agora

        self.sequencia.atualizar(contar_dedos(frame), agora)

        usa = {f for c in self.cadastros for f in c["fatores_exigidos"]}
        emb_rosto = extrair_rosto(frame) if "rosto" in usa else None
        vec_app = aparencia(frame) if usa & {"veiculo", "capacete"} else None

        for cad in self.cadastros:
            cid, nome, exigidos = cad["id"], cad["nome"], cad["fatores_exigidos"]

            if emb_rosto is not None and "rosto" in exigidos:
                s = _melhor(emb_rosto, cad["rosto"])
                self._scores[(nome, "rosto")] = s
                if s >= LIMIAR_ROSTO:
                    self._evidencias[(cid, "rosto")] = agora

            if vec_app is not None:
                for grupo in ("veiculo", "capacete"):
                    if grupo in exigidos:
                        s = _melhor(vec_app, cad[grupo])
                        self._scores[(nome, grupo)] = s
                        if s >= LIMIAR_APARENCIA:
                            self._evidencias[(cid, grupo)] = agora

            if "gesto" in exigidos and cad.get("codigo") and self.sequencia.termina_com(cad["codigo"]):
                self._evidencias[(cid, "gesto")] = agora
                self.sequencia.limpar()

        return self._decidir(agora)

    def _decidir(self, agora):
        for cad in self.cadastros:
            cid, exigidos = cad["id"], cad["fatores_exigidos"]
            if agora - self._ultimo_acesso.get(cid, -1e9) < COOLDOWN_S:
                continue
            if all(agora - self._evidencias.get((cid, f), -1e9) <= JANELA_S for f in exigidos):
                self._ultimo_acesso[cid] = agora
                for f in exigidos:
                    self._evidencias.pop((cid, f), None)
                return {"status": "acesso", "cadastro": cad["nome"], "id": cid,
                        "fatores": list(exigidos), "vivacidade": False}
        return None

    def estado(self, agora=None):
        agora = time.monotonic() if agora is None else agora
        ativos = sorted(f"{cid}:{f}" for (cid, f), t in self._evidencias.items() if agora - t <= JANELA_S)
        return {
            "sequencia": list(self.sequencia.sequencia),
            "evidencias_ativas": ativos,
            "similaridades": {f"{n}:{f}": round(s, 3) for (n, f), s in self._scores.items()},
        }


if __name__ == "__main__":
    # Teste isolado: pare o uvicorn antes, porque a câmera só pode ser aberta por um processo
    from src.camera import CameraStream

    cam = CameraStream()
    time.sleep(2)
    ident = Identidade()
    print("Cadastros carregados:", [c["nome"] for c in ident.cadastros])
    while True:
        frame = cam.get_frame()
        if frame is not None:
            decisao = ident.processar(frame)
            if decisao:
                print("✅ ACESSO:", decisao)
            print(ident.estado())
        time.sleep(0.5)