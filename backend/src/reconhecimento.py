import os
import glob
import numpy as np
import cv2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(BASE_DIR, "models_store")
YUNET = os.path.join(MODELS, "face_detection_yunet_2023mar.onnx")
SFACE = os.path.join(MODELS, "face_recognition_sface_2021dec.onnx")
PESSOA_DEIVID = os.path.join(MODELS, "pessoa_deivid.npy")

_detector = cv2.FaceDetectorYN.create(YUNET, "", (320, 320), 0.8, 0.3, 5000)
_recognizer = cv2.FaceRecognizerSF.create(SFACE, "")


def extrair(img_bgr):
    h, w = img_bgr.shape[:2]
    _detector.setInputSize((w, h))
    _, faces = _detector.detect(img_bgr)
    if faces is None:
        return None
    rosto = max(faces, key=lambda f: f[2] * f[3])  # o maior rosto da imagem
    alinhado = _recognizer.alignCrop(img_bgr, rosto)
    return _recognizer.feature(alinhado).flatten()


def similaridade(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def cadastrar(pasta_fotos, saida=PESSOA_DEIVID):
    fotos = glob.glob(os.path.join(pasta_fotos, "*.jpg"))
    embs = [e for e in (extrair(cv2.imread(f)) for f in fotos) if e is not None]
    print(f"{len(embs)} de {len(fotos)} fotos com rosto detectado")
    np.save(saida, np.array(embs, dtype=np.float32))
    return len(embs)
