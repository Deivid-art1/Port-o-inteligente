import os
import cv2
import numpy as np
import tensorflow as tf


class ImageClassifier:
    def __init__(self):
        self.model = None
        self.has_model = False
        self._carregar_modelo()

    def _carregar_modelo(self):
        caminhos = [
            "models_store/modelo_flores_224.keras",
            "../models_store/modelo_flores_224.keras",
            os.path.join(os.path.dirname(__file__), "..", "models_store", "modelo_flores_224.keras")
        ]

        for path in caminhos:
            if os.path.exists(path):
                try:
                    self.model = tf.keras.models.load_model(path)
                    self.has_model = True
                    print(f"🧠 Modelo carregado com sucesso de: {path}")
                    return
                except Exception as e:
                    print(f"⚠️ Erro ao carregar de {path}: {e}")

        print("⚠️ Aviso: Arquivo 'modelo_flores_224.keras' não foi encontrado.")
        self.has_model = False

    def predict_frame(self, frame):
        if not self.has_model or self.model is None:
            return {"raw_value": 0.5}

        if frame is None or frame.size == 0:
            return {"raw_value": 0.5}

        # 1. OpenCV entrega BGR; o treino foi feito em RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 2. Redimensionamento 224x224
        img = cv2.resize(frame_rgb, (224, 224))
        img = np.array(img, dtype=np.float32)
        
        # 3. Normalização simples (0 a 1), a mais comum em treinamentos customizados
        img = img / 255.0
        img = np.expand_dims(img, axis=0)

        # 4. Predição real do modelo
        raw_value = float(self.model.predict(img, verbose=0)[0][0])
        
        # Imprime no terminal do Uvicorn para você acompanhar o valor real mudando
        print(f"🔍 Raw Value do Modelo: {raw_value:.4f}")

        return {
            "raw_value": round(raw_value, 4)
        }