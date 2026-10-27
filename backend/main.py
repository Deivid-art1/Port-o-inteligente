from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import base64
import cv2
import json
import numpy as np

from src.camera import CameraStream
from src.registro import Registro
from src.motor import Motor
from src.admin_api import ADMIN_DIR, criar_router

app = FastAPI(title="API Portão Inteligente - IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

camera = CameraStream()
registro = Registro()
motor = Motor(camera, registro)
motor.start()


@app.get("/health")
def health_check():
    return {"status": "online", "face_recognition": "YuNet + SFace"}


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Cliente conectado ao WebSocket.")

    try:
        while True:
            estado = motor.snapshot()

            frame = camera.get_frame()

            if frame is not None:
                sucesso, buffer = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                )

                if sucesso:
                    estado["image"] = base64.b64encode(
                        buffer.tobytes()
                    ).decode("utf-8")

            estado["analysis"] = {
                "classe": estado.get("resultado", "Aguardando..."),
                "confianca": estado.get("pct_rosa") or 0
            }

            def converter_numpy(obj):
                if isinstance(obj, np.generic):
                    return obj.item()
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                raise TypeError(f"Tipo não serializável: {type(obj).__name__}")

            await websocket.send_text(
                json.dumps(estado, default=converter_numpy, ensure_ascii=False)
            )
            await asyncio.sleep(0.2)

    except WebSocketDisconnect:
        print("Cliente desconectado do WebSocket.")


# A ordem importa: a API vem antes do site, senão o /admin captura as rotas da API
app.include_router(criar_router(registro, motor), prefix="/admin/api")
app.mount("/admin", StaticFiles(directory=ADMIN_DIR, html=True), name="admin")
