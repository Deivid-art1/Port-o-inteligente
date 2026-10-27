"""Autenticação do painel: senhas com scrypt e sessões em memória."""
import hashlib
import hmac
import json
import os
import secrets
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMINS_PATH = os.path.join(BASE_DIR, "dados", "admins.json")
COOKIE_NOME = "sessao_admin"
SESSAO_HORAS = 8

_sessoes = {}  # token -> (usuario, expira_em)


def _hash_senha(senha, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(senha.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return f"{salt.hex()}${digest.hex()}"


def _carregar():
    if not os.path.exists(ADMINS_PATH):
        return {}
    with open(ADMINS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _salvar(admins):
    os.makedirs(os.path.dirname(ADMINS_PATH), exist_ok=True)
    with open(ADMINS_PATH, "w", encoding="utf-8") as f:
        json.dump(admins, f, indent=2)
    os.chmod(ADMINS_PATH, 0o600)


def criar_admin(usuario, senha):
    if not usuario:
        raise ValueError("informe o usuário")
    if len(senha) < 10:
        raise ValueError("a senha precisa ter pelo menos 10 caracteres")
    admins = _carregar()
    if usuario in admins:
        raise ValueError("usuário já existe")
    admins[usuario] = _hash_senha(senha)
    _salvar(admins)


def autenticar(usuario, senha):
    armazenado = _carregar().get(usuario)
    if armazenado is None:
        _hash_senha(senha, salt=b"0" * 16)  # mesmo custo de tempo, sem revelar se o usuário existe
        return None
    salt_hex, _ = armazenado.split("$")
    if not hmac.compare_digest(_hash_senha(senha, bytes.fromhex(salt_hex)), armazenado):
        return None
    token = secrets.token_urlsafe(32)
    _sessoes[token] = (usuario, time.time() + SESSAO_HORAS * 3600)
    return token


def usuario_da_sessao(token):
    if not token or token not in _sessoes:
        return None
    usuario, expira_em = _sessoes[token]
    if time.time() > expira_em:
        _sessoes.pop(token, None)
        return None
    return usuario


def encerrar(token):
    if token:
        _sessoes.pop(token, None)
