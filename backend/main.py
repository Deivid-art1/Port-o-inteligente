from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import cv2
import base64
import asyncio
from src.decisor import JanelaDecisao
from src.camera import CameraStream
from src.predictor import ImageClassifier


app = FastAPI(title="API Portão Inteligente - IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

camera = CameraStream()
classifier = ImageClassifier()


@app.get("/health")
def health_check():
    return {"status": "online", "model_loaded": classifier.has_model}


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Cliente conectado ao WebSocket.")
    decisor = JanelaDecisao()  # uma janela por conexão
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                await asyncio.sleep(0.1)
                continue

            leitura = await asyncio.to_thread(classifier.predict_frame, frame)
            decisor.adicionar(leitura["raw_value"])
            analise = decisor.decidir()

            _, buffer = cv2.imencode(".jpg", frame)
            frame_base64 = base64.b64encode(buffer).decode("utf-8")

            await websocket.send_json({
                "image": f"data:image/jpeg;base64,{frame_base64}",
                "analysis": analise,
            })
            await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        print("Cliente desconectado do WebSocket.")
    except Exception as e:
        print(f"Erro no WebSocket: {type(e).__name__}: {e}")
        try:
            await websocket.close()
        except Exception:
            pass