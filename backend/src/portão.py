MODO = "simulacao"            # "real" só depois da vivacidade e do relé
VIVACIDADE_IMPLEMENTADA = False
PERMITIR_FATOR_UNICO = False  # True só se você aceitar esse risco conscientemente


class Portao:
    def __init__(self, modo=MODO):
        self.modo = modo

    def acionar(self, decisao):
        fatores = decisao["fatores"]
        if self.modo == "real":
            if len(fatores) < 2 and not PERMITIR_FATOR_UNICO:
                print(f"🚫 Recusado: apenas {len(fatores)} fator(es) no modo real")
                return False
            if "rosto" in fatores and not VIVACIDADE_IMPLEMENTADA:
                print("🚫 Recusado: rosto sem checagem de vivacidade")
                return False
            raise NotImplementedError("Relé ainda não implementado: use o modo simulação")
        print(f"🚪 [SIMULAÇÃO] portão acionaria para {decisao['cadastro']} com {fatores}")
        return True