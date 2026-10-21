import cv2
import numpy as np
from PIL import Image
from tensorflow.keras.applications import EfficientNetV2B0

_modelo = None


def _modelo_efficientnet():
    global _modelo
    if _modelo is None:
        _modelo = EfficientNetV2B0(weights="imagenet", include_top=False,
                                   pooling="avg", input_shape=(224, 224, 3))
    return _modelo


def aparencia(frame_bgr):
    """Vetor normalizado da aparência do quadro inteiro (veículo, capacete, cena)."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb).resize((224, 224), Image.Resampling.NEAREST)
    x = np.asarray(img, dtype=np.float32)[np.newaxis, ...]
    v = _modelo_efficientnet().predict(x, verbose=0)[0]
    return v / (np.linalg.norm(v) + 1e-12)