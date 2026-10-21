import threading
import time
import cv2


class CameraStream:
    def __init__(self, device="/dev/video1", width=640, height=480):
        self.cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # reduz atraso entre o mundo real e o frame

        self.frame = None
        self.lock = threading.Lock()
        self.running = self.cap.isOpened()

        if self.running:
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
        else:
            print(f"⚠️ Não foi possível abrir a câmera {device}")

    def _update(self):
        # Lê a câmera em segundo plano, para o websocket sempre pegar o frame mais recente
        while self.running:
            ok, frame = self.cap.read()
            if ok:
                with self.lock:
                    self.frame = frame
            else:
                time.sleep(0.05)

    def get_frame(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def release(self):
        self.running = False
        self.cap.release()