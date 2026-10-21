import cv2
import mediapipe as mp
import numpy as np

# Se mp.solutions não existir na sua versão do mediapipe, me avise: trocamos para a API Tasks.
_maos = mp.solutions.hands.Hands(
    static_image_mode=False, max_num_hands=2,
    min_detection_confidence=0.6, min_tracking_confidence=0.5,
)

PONTAS = [8, 12, 16, 20]        # indicador, médio, anelar, mindinho
ARTICULACOES = [6, 10, 14, 18]  # articulação logo abaixo de cada ponta


def _dedos_estendidos(lm):
    def ponto(i):
        return np.array([lm[i].x, lm[i].y])

    punho = ponto(0)

    def dist(i):
        return np.linalg.norm(ponto(i) - punho)

    # Dedo estendido: a ponta fica mais longe do punho que a articulação
    n = sum(dist(p) > dist(a) for p, a in zip(PONTAS, ARTICULACOES))
    n += int(dist(4) > dist(2))  # polegar
    return n


def contar_dedos(frame_bgr):
    """Dedos estendidos nas mãos visíveis, ou None se nenhuma mão aparecer."""
    res = _maos.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    if not res.multi_hand_landmarks:
        return None
    return min(10, sum(_dedos_estendidos(h.landmark) for h in res.multi_hand_landmarks))


class SequenciaGestos:
    """Transforma a contagem de dedos em uma sequência de dígitos estáveis."""

    def __init__(self, segura_s=0.7, reset_s=3.0, maximo=10):
        self.segura_s, self.reset_s, self.maximo = segura_s, reset_s, maximo
        self.sequencia = []
        self._digito = None
        self._desde = None
        self._gravado = False
        self._ultimo_sinal = None

    def atualizar(self, contagem, agora):
        if contagem is None:
            if self._ultimo_sinal is not None and agora - self._ultimo_sinal > self.reset_s:
                self.sequencia.clear()
                self._ultimo_sinal = None
            self._digito = None
            return

        self._ultimo_sinal = agora
        if contagem != self._digito:
            self._digito, self._desde, self._gravado = contagem, agora, False
            return
        if not self._gravado and agora - self._desde >= self.segura_s:
            self.sequencia.append(contagem)
            self.sequencia = self.sequencia[-self.maximo:]
            self._gravado = True

    def termina_com(self, codigo):
        n = len(codigo)
        return len(self.sequencia) >= n and self.sequencia[-n:] == list(codigo)

    def limpar(self):
        self.sequencia.clear()