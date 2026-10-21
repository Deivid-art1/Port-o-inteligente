import time
from collections import deque

LIMIAR_CONFIANCA = 76.0   
JANELA_SEGUNDOS = 4.0     


class JanelaDecisao:
    """Decide pela média das leituras dentro do treino dos últimos segundos."""

    def __init__(self, janela=JANELA_SEGUNDOS, limiar=LIMIAR_CONFIANCA):
        self.janela = janela
        self.limiar = limiar
        self.inicio = time.monotonic()
        self.amostras = deque()  # pares (instante, raw_value); frames fora do treino não entram

    def adicionar(self, raw_value):
        agora = time.monotonic()
        if raw_value is not None:
            self.amostras.append((agora, raw_value))
        while self.amostras and agora - self.amostras[0][0] > self.janela:
            self.amostras.popleft()

    def decidir(self):
        decorrido = time.monotonic() - self.inicio

        if decorrido < self.janela:
            progresso = min(100, round(decorrido / self.janela * 100))
            return {
                "status": "analisando", 
                "progresso": progresso,
                "amostras": len(self.amostras)
            }

        # Nenhuma leitura dentro do treino
        if not self.amostras:
            return {
                "status": "decidido", 
                "resultado": "inconclusivo",
                "pct_rosa": None, 
                "pct_tulipa": None, 
                "amostras": 0,
                "motivo": "fora do treino"
            }

        media = sum(r for _, r in self.amostras) / len(self.amostras)
        pct_rosa = round((1.0 - media) * 100, 2)
        pct_tulipa = round(media * 100, 2)

        if pct_rosa >= self.limiar:
            resultado = "rosa"
        elif pct_tulipa >= self.limiar:
            resultado = "tulipa"
        else:
            resultado = "inconclusivo"

        return {
            "status": "decidido", 
            "resultado": resultado,
            "pct_rosa": pct_rosa, 
            "pct_tulipa": pct_tulipa,
            "amostras": len(self.amostras)
        }