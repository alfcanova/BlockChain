"""Testes unitarios para blockchain_pf/auth.py"""

import pytest
from blockchain_pf.auth import (
    create_user, authenticate_user, get_user, list_users, delete_user,
    create_access_token, decode_access_token, init_default_users,
    _hash_password, _verify_password,
)


@pytest.fixture(autouse=True)
def clean_users():
    """Limpa usuarios entre testes."""
    from blockchain_pf.auth import _users_db, _db
    _users_db.clear()
    if _db:
        with _db._transaction() as conn:
            conn.execute("DELETE FROM users")
    yield
    _users_db.clear()
    if _db:
        with _db._transaction() as conn:
            conn.execute("DELETE FROM users")


# ── Password Hashing ───────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_produces_different_salts(self):
        h1 = _hash_password("senha123")
        h2 = _hash_password("senha123")
        assert h1 != h2  # Salts diferentes

    def test_verify_correct_password(self):
        h = _hash_password("senha123")
        assert _verify_password("senha123", h) is True

    def test_verify_wrong_password(self):
        h = _hash_password("senha123")
        assert _verify_password("errada", h) is False

    def test_verify_invalid_format(self):
        assert _verify_password("senha", "sem_sifrlo") is False


# ── User Management ────────────────────────────────────────────────────

class TestUserManagement:
    def test_create_user(self):
        user = create_user("admin", "Admin#123")
        assert user.username == "admin"
        assert user.role == "admin"

    def test_create_user_duplicate_fails(self):
        create_user("admin", "Admin#123")
        with pytest.raises(ValueError, match="ja existe"):
            create_user("admin", "Outra#Senha9")

    def test_authenticate_correct(self):
        create_user("admin", "Admin#123")
        user = authenticate_user("admin", "Admin#123")
        assert user is not None
        assert user.username == "admin"

    def test_authenticate_wrong_password(self):
        create_user("admin", "Admin#123")
        user = authenticate_user("admin", "errada")
        assert user is None

    def test_authenticate_nonexistent(self):
        user = authenticate_user("naoexiste", "senha")
        assert user is None

    def test_get_user(self):
        create_user("admin", "Admin#123")
        user = get_user("admin")
        assert user is not None

    def test_list_users(self):
        create_user("admin", "Admin#123")
        create_user("user", "User#123", role="user")
        users = list_users()
        assert len(users) == 2

    def test_delete_user(self):
        create_user("admin", "Admin#123")
        assert delete_user("admin") is True
        assert get_user("admin") is None

    def test_delete_nonexistent(self):
        assert delete_user("naoexiste") is False

    def test_user_roles(self):
        create_user("admin", "Admin#123", role="admin")
        create_user("operador", "Oper#123", role="user")
        create_user("consulta", "Cons#123", role="readonly")
        assert get_user("admin").role == "admin"
        assert get_user("operador").role == "user"
        assert get_user("consulta").role == "readonly"

    def test_user_to_dict(self):
        user = create_user("admin", "Admin#123")
        d = user.to_dict()
        assert "username" in d
        assert "role" in d
        assert "password_hash" not in d  # Nao expoe hash

    def test_init_default_users(self):
        init_default_users()
        assert get_user("admin") is not None
        assert get_user("operador") is not None
        assert get_user("consulta") is not None

    def test_init_default_users_idempotent(self):
        init_default_users()
        init_default_users()
        users = list_users()
        assert len(users) == 3


# ── JWT Tokens ─────────────────────────────────────────────────────────

class TestJWTTokens:
    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "admin", "role": "admin"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"

    def test_token_has_expiry(self):
        token = create_access_token({"sub": "admin"})
        payload = decode_access_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_token_with_custom_expiry(self):
        token = create_access_token({"sub": "admin"}, expires_delta=3600)
        payload = decode_access_token(token)
        assert payload is not None

    def test_invalid_token_returns_none(self):
        payload = decode_access_token("token_invalido")
        assert payload is None

    def test_empty_token_returns_none(self):
        payload = decode_access_token("")
        assert payload is None

    def test_tampered_token_returns_none(self):
        token = create_access_token({"sub": "admin"})
        # Corrompe o token
        tampered = token[:-5] + "XXXXX"
        payload = decode_access_token(tampered)
        assert payload is None




# ── JWT Secret persistido — restart simulado (Fase 5.7 / C2) ──────────


class TestJwtSecretRestart:
    """O segredo JWT deve sobreviver a restarts da aplicacao.

    C2: antes da correcao, SECRET_KEY era regenerada a cada processo e
    todos os tokens de sessoes anteriores ficavam invalidos. Hoje o
    segredo persiste em .jwt_secret (ou vem de JWT_SECRET_KEY).

    O restart e simulado chamando _load_or_create_secret() — o mesmo
    ponto de entrada avaliado na importacao do modulo em cada processo —
    sem reload do modulo (o que destruiria o estado global testado).
    """

    def test_token_valido_apos_recarregar_segredo(self, monkeypatch, tmp_path):
        """Segredo lido do arquivo equivale ao da geracao — token antigo valido."""
        import blockchain_pf.auth as auth_mod

        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        secret_file = tmp_path / ".jwt_secret"

        # 1a "execucao": segredo nao existe — gera e persiste
        monkeypatch.setattr(auth_mod, "_SECRET_FILE", str(secret_file))
        segredo_1 = auth_mod._load_or_create_secret()
        assert secret_file.exists()
        assert len(segredo_1) == 64  # token_hex(32)

        # token emitido na 1a "execucao"
        token_antes = auth_mod.create_access_token({"sub": "admin", "role": "admin"})

        # 2a "execucao": leitura pura do arquivo deve devolver o mesmo segredo
        segredo_2 = auth_mod._load_or_create_secret()
        assert segredo_2 == segredo_1

        # O segredo em uso pelo modulo (SECRET_KEY avaliado na importacao)
        # tambem vem do mesmo arquivo — token emitido na 1a "execucao"
        # decodifica normalmente apos o "restart" (C2 resolvido).
        payload = auth_mod.decode_access_token(token_antes)
        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"

    def test_arquivo_gerado_uma_vez_e_reutilizado(self, monkeypatch, tmp_path):
        """Segunda carga nao reescreve o segredo (idempotente)."""
        import blockchain_pf.auth as auth_mod

        secret_file = tmp_path / ".jwt_secret"
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.setattr(auth_mod, "_SECRET_FILE", str(secret_file))

        s1 = auth_mod._load_or_create_secret()
        mtime1 = secret_file.stat().st_mtime_ns
        s2 = auth_mod._load_or_create_secret()
        assert s1 == s2
        assert secret_file.stat().st_mtime_ns == mtime1

    def test_env_var_tem_prioridade_sobre_arquivo(self, monkeypatch, tmp_path):
        """JWT_SECRET_KEY (env) vence o arquivo — 12 fatores / deploy."""
        import blockchain_pf.auth as auth_mod

        secret_file = tmp_path / ".jwt_secret"
        secret_file.write_text("segredo-do-arquivo", encoding="utf-8")
        monkeypatch.setenv("JWT_SECRET_KEY", "segredo-do-env")
        monkeypatch.setattr(auth_mod, "_SECRET_FILE", str(secret_file))

        assert auth_mod._load_or_create_secret() == "segredo-do-env"

    def test_arquivo_vazio_e_regenerado(self, monkeypatch, tmp_path):
        """Arquivo corrompido/vazio nao derruba a app — regenera segredo."""
        import blockchain_pf.auth as auth_mod

        secret_file = tmp_path / ".jwt_secret"
        secret_file.write_text("   \n", encoding="utf-8")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.setattr(auth_mod, "_SECRET_FILE", str(secret_file))

        segredo = auth_mod._load_or_create_secret()
        assert len(segredo) == 64
        assert secret_file.read_text(encoding="utf-8").strip() == segredo

    def test_token_de_segredo_diferente_e_rejeitado(self, monkeypatch, tmp_path):
        """Token emitido com segredo A nao decodifica com segredo B (isolamento)."""
        import jwt as pyjwt
        import blockchain_pf.auth as auth_mod

        token_a = auth_mod.create_access_token({"sub": "admin"})

        outro = "outro-segredo-completamente-diferente-0123456789abcdef"
        with pytest.raises(pyjwt.InvalidTokenError):
            pyjwt.decode(token_a, outro, algorithms=["HS256"])
