"""Rotas do painel administrativo: API em /admin/api e o site estático em /admin."""
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse

from src import auth
from src.cadastro import cadastrar, carregar, parse_codigo, quadros_de_origem, remover

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DIR = os.path.join(BASE_DIR, "admin")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
CAPTURAS_DIR = os.path.join(BASE_DIR, "capturas")
EXTENSOES_ACEITAS = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi", ".mkv"}
TAMANHO_MAX_BYTES = 200 * 1024 * 1024


def exigir_admin(request: Request) -> str:
    usuario = auth.usuario_da_sessao(request.cookies.get(auth.COOKIE_NOME))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sessão expirada ou não autenticada.")
    return usuario


def _resumo(cad: dict) -> dict:
    # Nunca devolve os vetores biométricos, só o que o painel precisa mostrar
    return {
        "id": cad["id"],
        "nome": cad["nome"],
        "fatores_exigidos": cad["fatores_exigidos"],
        "tem_codigo": bool(cad.get("codigo")),
        "amostras": {g: len(cad[g]) for g in ("rosto", "veiculo", "capacete")},
        "criado_em": cad["criado_em"],
    }


def _salvar_upload(arquivo: UploadFile) -> str:
    ext = os.path.splitext(arquivo.filename)[1].lower()
    if ext not in EXTENSOES_ACEITAS:
        raise HTTPException(status_code=400, detail=f"Formato não aceito: {arquivo.filename}")

    # Nome aleatório: nada vindo do cliente entra no caminho do arquivo
    destino = os.path.join(UPLOADS_DIR, uuid.uuid4().hex + ext)
    total = 0
    try:
        with open(destino, "wb") as saida:
            while bloco := arquivo.file.read(1024 * 1024):
                total += len(bloco)
                if total > TAMANHO_MAX_BYTES:
                    raise HTTPException(status_code=413, detail=f"{arquivo.filename} passa de 200 MB.")
                saida.write(bloco)
    except Exception:
        if os.path.exists(destino):
            os.remove(destino)
        raise
    return destino


def criar_router(registro, motor):
    router = APIRouter()
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    @router.post("/login")
    def login(response: Response, usuario: str = Form(...), senha: str = Form(...)):
        usuario = usuario.strip()
        token = auth.autenticar(usuario, senha)
        if token is None:
            raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")
        response.set_cookie(
            key=auth.COOKIE_NOME, value=token, httponly=True,
            samesite="strict", max_age=auth.SESSAO_HORAS * 3600, path="/",
        )
        return {"usuario": usuario}

    @router.post("/logout")
    def logout(request: Request, response: Response):
        auth.encerrar(request.cookies.get(auth.COOKIE_NOME))
        response.delete_cookie(auth.COOKIE_NOME, path="/")
        return {"ok": True}

    @router.get("/sessao")
    def sessao(usuario: str = Depends(exigir_admin)):
        return {"usuario": usuario}

    @router.get("/cadastros", dependencies=[Depends(exigir_admin)])
    def listar_cadastros():
        return [_resumo(c) for c in carregar()]

    @router.post("/cadastros", status_code=201, dependencies=[Depends(exigir_admin)])
    def criar_cadastro(
        nome: str = Form(...),
        exigir: str = Form("rosto,veiculo"),
        codigo: str = Form(""),
        rosto: list[UploadFile] | None = File(default=None),
        veiculo: list[UploadFile] | None = File(default=None),
        capacete: list[UploadFile] | None = File(default=None),
    ):
        nome = nome.strip()
        if not nome:
            raise HTTPException(status_code=400, detail="Informe o nome.")
        fatores = [f.strip() for f in exigir.split(",") if f.strip()]
        try:
            cod = parse_codigo(codigo) if codigo.strip() else None
        except ValueError as erro:
            raise HTTPException(status_code=400, detail=str(erro))

        salvos = []
        try:
            quadros = {"rosto": [], "veiculo": [], "capacete": []}
            for grupo, arquivos in (("rosto", rosto), ("veiculo", veiculo), ("capacete", capacete)):
                for arquivo in arquivos or []:
                    if not arquivo.filename:
                        continue  # campo de upload vazio
                    caminho = _salvar_upload(arquivo)
                    salvos.append(caminho)
                    quadros[grupo].extend(quadros_de_origem(caminho))
            cad = cadastrar(nome, fatores, quadros, cod)
        except ValueError as erro:
            raise HTTPException(status_code=400, detail=str(erro))
        finally:
            for caminho in salvos:
                if os.path.exists(caminho):
                    os.remove(caminho)

        motor.identidade.recarregar()
        return _resumo(cad)

    @router.delete("/cadastros/{cid}", dependencies=[Depends(exigir_admin)])
    def apagar_cadastro(cid: str):
        try:
            remover(cid)
        except KeyError:
            raise HTTPException(status_code=404, detail="Cadastro não encontrado.")
        motor.identidade.recarregar()
        return {"removido": cid}

    @router.get("/eventos", dependencies=[Depends(exigir_admin)])
    def listar_eventos(limite: int = Query(50, ge=1, le=500)):
        return [
            {
                "id": e["id"],
                "timestamp": e["timestamp"],
                "resultado": e["resultado"],
                "pct_rosa": e["pct_rosa"],
                "pct_tulipa": e["pct_tulipa"],
                "acao": e["acao"],
                "foto_url": f"/admin/api/eventos/{e['id']}/foto",
            }
            for e in registro.listar(limite)
        ]

    @router.get("/eventos/{evento_id}/foto", dependencies=[Depends(exigir_admin)])
    def foto_evento(evento_id: int):
        caminho = registro.foto_do_evento(evento_id)
        if not caminho:
            raise HTTPException(status_code=404, detail="Evento não encontrado.")
        real = os.path.realpath(caminho)
        pasta = os.path.realpath(CAPTURAS_DIR)
        if not real.startswith(pasta + os.sep) or not os.path.isfile(real):
            raise HTTPException(status_code=404, detail="Foto não encontrada.")
        return FileResponse(real, media_type="image/jpeg")

    return router
