import os
import sqlite3
import threading
import uuid
from datetime import datetime

import cv2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pasta backend
CAPTURAS_DIR = os.path.join(BASE_DIR, "capturas")
DB_PATH = os.path.join(BASE_DIR, "historico", "eventos.db")

COLUNAS = ["id", "timestamp", "resultado", "pct_rosa", "pct_tulipa",
           "foto_path", "autorizado", "acao"]


class Registro:
    def __init__(self):
        os.makedirs(CAPTURAS_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        self._lock = threading.Lock()
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                resultado TEXT NOT NULL,
                pct_rosa REAL,
                pct_tulipa REAL,
                foto_path TEXT NOT NULL,
                autorizado INTEGER,          -- NULL = sem verificação de identidade
                acao TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def registrar(self, resultado, pct_rosa, pct_tulipa, frame, acao="registrado"):
        agora = datetime.now()
        nome = f"{agora.strftime('%Y-%m-%d_%H-%M-%S')}_{uuid.uuid4().hex[:6]}.jpg"
        foto = os.path.join(CAPTURAS_DIR, nome)
        cv2.imwrite(foto, frame)

        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO eventos
                   (timestamp, resultado, pct_rosa, pct_tulipa, foto_path, autorizado, acao)
                   VALUES (?, ?, ?, ?, ?, NULL, ?)""",
                (agora.isoformat(timespec="seconds"), resultado, pct_rosa, pct_tulipa, foto, acao),
            )
            self._conn.commit()
            return cur.lastrowid

    def listar(self, limite=20):
        with self._lock:
            linhas = self._conn.execute(
                f"SELECT {', '.join(COLUNAS)} FROM eventos ORDER BY id DESC LIMIT ?",
                (limite,),
            ).fetchall()
        return [dict(zip(COLUNAS, linha)) for linha in linhas]

    def foto_do_evento(self, evento_id):
        with self._lock:
            linha = self._conn.execute(
                "SELECT foto_path FROM eventos WHERE id = ?", (evento_id,)
            ).fetchone()
        return linha[0] if linha else None
