import os

# Altere "0" para a URL RTSP da sua câmara iCSee/Yoosee quando estiver conectada
# Exemplo: "rtsp://admin:senha@192.168.1.100:554/onvif1"
RTSP_URL = os.getenv("RTSP_URL", "0") 
MODEL_PATH = "models_store/modelo_flores_224.keras"
