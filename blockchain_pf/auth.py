"""
blockchain_pf/auth.py
Autenticacao JWT para a API REST.

Gerencia:
  - Usuarios (em memoria para demo)
  - Geracao de tokens JWT
  - Verificacao de tokens
  - Hash de senhas com bcrypt-like (SHA-256 + salt)
  - Dependencia FastAPI para protecao de endpoints

Uso:
  POST /api/auth/login  → retorna token JWT
  Header: Authorization: Bearer <token>  → autentica
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# ── Configuracao ───────────────────────────────────────────────────────

SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY",
    "blockchain-pf-secret-key-change-in-production-" + secrets.token_hex(16),
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas


# ── Usuarios (em memoria) ─────────────────────────────────────────────

@dataclass
class User:
    """Usuario do sistema."""
    username: str
    password_hash: str
    role: str = "admin"  # admin | user | readonly
    ativo: bool = True
    nivel: int = 0          # Nivel de autoridade: 0 (Brasil) | 1 (UF) | 2 (cidade)
    escopo: str = ""        # Dominio governado: pf|im|mo|co|em|ac|an (autoridade)
    uf: str = ""            # Regiao da autoridade (N1/N2)
    cidade: str = ""        # Municipio da autoridade (N2 apenas)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "role": self.role,
            "ativo": self.ativo,
            "nivel": self.nivel,
            "escopo": self.escopo,
            "uf": self.uf,
            "cidade": self.cidade,
        }

    @staticmethod
    def _from_row(row: dict[str, Any]) -> "User":
        """Converte um row do SQLite (com novas colunas) em User."""
        return User(
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            ativo=bool(row["ativo"]),
            nivel=int(row.get("nivel") or 0),
            escopo=row.get("escopo") or "",
            uf=row.get("uf") or "",
            cidade=row.get("cidade") or "",
        )


# Usuarios em memoria (fallback quando nao ha DB)
_users_db: dict[str, User] = {}
_db = None  # Database instance (opcional)


def set_database(db) -> None:
    """Configura o banco de dados para persistencia."""
    global _db
    _db = db


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    """Gera hash da senha com salt (SHA-256)."""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${h}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verifica senha contra hash armazenado."""
    if "$" not in stored_hash:
        return False
    salt, _ = stored_hash.split("$", 1)
    return hmac.compare_digest(_hash_password(password, salt), stored_hash)


# ── Gerenciamento de Usuarios ──────────────────────────────────────────

def create_user(
    username: str,
    password: str,
    role: str = "admin",
    nivel: int = 0,
    escopo: str = "",
    uf: str = "",
    cidade: str = "",
) -> User:
    """Cria um novo usuario."""
    if username in _users_db:
        raise ValueError(f"Usuario '{username}' ja existe.")
    user = User(
        username=username,
        password_hash=_hash_password(password),
        role=role,
        nivel=nivel,
        escopo=escopo,
        uf=uf,
        cidade=cidade,
    )
    _users_db[username] = user
    if _db:
        _db.save_user(username, user.password_hash, role, True, nivel, escopo, uf, cidade)
    return user


def update_user_metadata(
    username: str,
    nivel: Optional[int] = None,
    escopo: Optional[str] = None,
    uf: Optional[str] = None,
    cidade: Optional[str] = None,
    ativo: Optional[bool] = None,
) -> Optional[User]:
    """
    Atualiza metadados de um usuario existente (nivel/escopo/regiao).
    Usado ao criar/alterar/revogar contas de autoridade no au.
    """
    user = get_user(username)
    if not user:
        return None
    if nivel is not None:
        user.nivel = int(nivel)
    if escopo is not None:
        user.escopo = escopo
    if uf is not None:
        user.uf = uf
    if cidade is not None:
        user.cidade = cidade
    if ativo is not None:
        user.ativo = bool(ativo)
    _users_db[username] = user
    if _db:
        _db.update_user(
            username,
            ativo=user.ativo,
            nivel=user.nivel,
            escopo=user.escopo,
            uf=user.uf,
            cidade=user.cidade,
        )
    return user


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Autentica usuario e retorna o objeto User ou None."""
    # Busca no DB se disponivel
    if _db and username not in _users_db:
        row = _db.load_user(username)
        if row:
            _users_db[username] = User._from_row(row)
    user = _users_db.get(username)
    if not user or not user.ativo:
        return None
    if not _verify_password(password, user.password_hash):
        return None
    return user


def get_user(username: str) -> Optional[User]:
    """Retorna usuario pelo username."""
    if _db and username not in _users_db:
        row = _db.load_user(username)
        if row:
            _users_db[username] = User._from_row(row)
    return _users_db.get(username)


def list_users() -> list[dict]:
    """Lista todos os usuarios (sem senha)."""
    if _db:
        rows = _db.load_all_users()
        return [{
            "username": r["username"],
            "role": r["role"],
            "ativo": bool(r["ativo"]),
            "nivel": int(r.get("nivel") or 0),
            "escopo": r.get("escopo") or "",
            "uf": r.get("uf") or "",
            "cidade": r.get("cidade") or "",
        } for r in rows]
    return [u.to_dict() for u in _users_db.values()]


def delete_user(username: str) -> bool:
    """Remove um usuario."""
    if username in _users_db:
        del _users_db[username]
    if _db:
        return _db.delete_user(username)
    return username in _users_db


# ── Tokens JWT ─────────────────────────────────────────────────────────

def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[int] = None,
) -> str:
    """
    Gera um token JWT.
    
    Args:
        data:           Dados a codificar no token.
        expires_delta:  Tempo de expiracao em segundos.
    
    Returns:
        Token JWT codificado.
    """
    to_encode = data.copy()
    expire = time.time() + (expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    to_encode.update({"exp": expire, "iat": time.time()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decodifica e valida um token JWT.
    
    Returns:
        Payload do token ou None se invalido.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── FastAPI Security ───────────────────────────────────────────────────

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict[str, Any]:
    """
    Dependencia FastAPI: extrai e valida o token JWT.
    
    Retorna o payload do token (contendo username, role, etc.).
    Levanta 401 se o token for invalido ou ausente.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticacao ausente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def require_write_access(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Dependencia FastAPI: exige papel admin ou user para escrita.
    """
    role = user.get("role", "")
    if role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissao insuficiente para escrita.",
        )
    return user


async def require_admin(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Dependencia FastAPI: exige papel admin.
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta acao.",
        )
    return user


def require_nivel_atual(min_nivel: int):
    """
    Fabrica de dependencia FastAPI: exige autoridade com nivel >= min_nivel.

    Rele o registro do usuario (nivel vigente gravado em users), nao apenas
    o token — assim a revogacao no livro-razao AU invalida o acesso de fato.
    """

    async def _dep(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        username = user.get("sub", "")
        u = get_user(username)
        if not u:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario nao encontrado.",
            )
        if u.nivel < min_nivel:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissao insuficiente: requer nivel >= {min_nivel}.",
            )
        return {"username": username, "nivel": u.nivel, "user": u}

    return _dep


# ── Inicializacao ──────────────────────────────────────────────────────

def init_default_users() -> None:
    """Cria usuarios padrao para demonstracao."""
    if "admin" not in _users_db:
        create_user("admin", "admin123", role="admin")
    if "operador" not in _users_db:
        create_user("operador", "oper123", role="user")
    if "consulta" not in _users_db:
        create_user("consulta", "cons123", role="readonly")


def init_default_authorities() -> None:
    """
    Seeds das 3 autoridades de nivel 0 (Brasil).

    admin01/@dmin01BR, admin02/@dmin02BR, admin03/@dmin03BR
    —— escopo vazio: governam qualquer escopo/UF; poderes identicos
    (redundancia, sem ponto unico de falha).
    """
    for username, password in [
        ("admin01", "@dmin01BR"),
        ("admin02", "@dmin02BR"),
        ("admin03", "@dmin03BR"),
    ]:
        if get_user(username) is None:
            create_user(username, password, role="admin", nivel=0)
