import argparse
import glob
import json
import os
import time
import uuid

import cv2
import numpy as np

from src.extrator import aparencia
from src.reconhecimento import extrair as extrair_rosto

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CADASTROS_PATH = os.path.join(BASE_DIR, "models_store", "cadastros.json")

FATORES_VALIDOS = {"rosto", "veiculo", "capacete", "gesto"}
MINIMO = {"rosto": 5, "veiculo": 5, "capacete": 5}  # quadros úteis por fator
ROTEIRO = [
    ("rosto", "Olhe para a câmera SEM capacete"),
    ("capacete", "Fique COM capacete (viseira aberta, se puder)"),
    ("veiculo", "Posicione o VEÍCULO na frente da câmera, sem ninguém na frente"),
]


def carregar():
    if not os.path.exists(CADASTROS_PATH):
        return []
    with open(CADASTROS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _salvar(cadastros):
    os.makedirs(os.path.dirname(CADASTROS_PATH), exist_ok=True)
    with open(CADASTROS_PATH, "w", encoding="utf-8") as f:
        json.dump(cadastros, f)


def parse_codigo(texto):
    """'4,5,2' ou '452' -> [4, 5, 2]. Para o dígito 10, use vírgula: '1,0' é diferente de '10'."""
    t = texto.replace(" ", "")
    partes = t.split(",") if "," in t else list(t)
    codigo = [int(p) for p in partes]
    if not codigo or any(d < 0 or d > 10 for d in codigo):
        raise ValueError("código inválido: use dígitos de 0 a 10")
    return codigo


def quadros_de_video(caminho, a_cada_s=0.5, maximo=60):
    cap = cv2.VideoCapture(caminho)
    passo = max(1, int((cap.get(cv2.CAP_PROP_FPS) or 25) * a_cada_s))
    quadros, i = [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % passo == 0:
            quadros.append(f)
        i += 1
    cap.release()
    if len(quadros) > maximo:
        idx = np.linspace(0, len(quadros) - 1, maximo).astype(int)
        quadros = [quadros[i] for i in idx]
    return quadros


def quadros_de_pasta(pasta):
    quadros = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        for arq in sorted(glob.glob(os.path.join(pasta, ext))):
            img = cv2.imread(arq)
            if img is not None:
                quadros.append(img)
    return quadros


def quadros_de_origem(origem):
    if os.path.isdir(origem):
        return quadros_de_pasta(origem)
    if not os.path.isfile(origem):
        raise FileNotFoundError(origem)
    if origem.lower().endswith((".jpg", ".jpeg", ".png")):
        img = cv2.imread(origem)
        return [img] if img is not None else []
    return quadros_de_video(origem)


def quadros_da_camera(camera, segundos=10, a_cada_s=0.5):
    quadros, fim = [], time.monotonic() + segundos
    while time.monotonic() < fim:
        f = camera.get_frame()
        if f is not None:
            quadros.append(f)
        time.sleep(a_cada_s)
    return quadros


def cadastrar(nome, fatores_exigidos, quadros, codigo=None):
    """quadros: dicionário com listas de imagens por fator ('rosto', 'veiculo', 'capacete')."""
    fatores = set(fatores_exigidos)
    if not fatores <= FATORES_VALIDOS:
        raise ValueError(f"fatores inválidos: {fatores - FATORES_VALIDOS}")
    if "gesto" in fatores and not codigo:
        raise ValueError("o fator 'gesto' exige um código")

    cad = {
        "id": uuid.uuid4().hex[:8],
        "nome": nome,
        "fatores_exigidos": sorted(fatores),
        "codigo": codigo,
        "rosto": [], "veiculo": [], "capacete": [],
        "criado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    for grupo in ("rosto", "veiculo", "capacete"):
        for q in quadros.get(grupo, []):
            if grupo == "rosto":
                e = extrair_rosto(q)
                if e is not None:
                    cad["rosto"].append(e.tolist())
            else:
                cad[grupo].append(aparencia(q).tolist())

    for f in fatores & set(MINIMO):
        if len(cad[f]) < MINIMO[f]:
            raise ValueError(f"fator '{f}': só {len(cad[f])} quadros úteis (mínimo {MINIMO[f]})")

    cadastros = carregar()
    cadastros.append(cad)
    _salvar(cadastros)
    print(f"✅ {nome} cadastrado (id {cad['id']}). Fatores: {cad['fatores_exigidos']} | "
          f"rosto={len(cad['rosto'])} veiculo={len(cad['veiculo'])} capacete={len(cad['capacete'])}")
    return cad


def _principal():
    p = argparse.ArgumentParser(description="Cadastro rápido de pessoa e veículo")
    p.add_argument("--nome", required=True)
    p.add_argument("--exigir", default="rosto,veiculo",
                   help="fatores separados por vírgula: rosto,veiculo,capacete,gesto")
    p.add_argument("--codigo", help="sequência de dedos, ex.: 4,5,2 ou 452")
    p.add_argument("--rosto", help="vídeo ou pasta de fotos, sem capacete")
    p.add_argument("--veiculo", help="vídeo ou pasta de fotos do veículo")
    p.add_argument("--capacete", help="vídeo ou pasta com a pessoa de capacete")
    p.add_argument("--camera", action="store_true", help="captura pela câmera do portão")
    a = p.parse_args()

    fatores = [f.strip() for f in a.exigir.split(",") if f.strip()]
    codigo = parse_codigo(a.codigo) if a.codigo else None
    quadros = {}

    if a.camera:
        # Pare o uvicorn antes: a câmera só pode ser aberta por um processo
        from src.camera import CameraStream
        cam = CameraStream()
        time.sleep(2)
        for grupo, instrucao in ROTEIRO:
            if grupo in fatores:
                input(f"\n{instrucao}. Pressione Enter para capturar 10 segundos...")
                quadros[grupo] = quadros_da_camera(cam, segundos=10)
                print(f"   {len(quadros[grupo])} quadros capturados")
        cam.release()
    else:
        for grupo, caminho in [("rosto", a.rosto), ("veiculo", a.veiculo), ("capacete", a.capacete)]:
            if caminho:
                quadros[grupo] = quadros_de_origem(caminho)

    cadastrar(a.nome, fatores, quadros, codigo)


def remover(cid):
    cadastros = carregar()
    restantes = [c for c in cadastros if c["id"] != cid]
    if len(restantes) == len(cadastros):
        raise KeyError(cid)
    _salvar(restantes)


if __name__ == "__main__":
    _principal()