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
        user = create_user("admin", "admin123")
        assert user.username == "admin"
        assert user.role == "admin"

    def test_create_user_duplicate_fails(self):
        create_user("admin", "admin123")
        with pytest.raises(ValueError, match="ja existe"):
            create_user("admin", "outra_senha")

    def test_authenticate_correct(self):
        create_user("admin", "admin123")
        user = authenticate_user("admin", "admin123")
        assert user is not None
        assert user.username == "admin"

    def test_authenticate_wrong_password(self):
        create_user("admin", "admin123")
        user = authenticate_user("admin", "errada")
        assert user is None

    def test_authenticate_nonexistent(self):
        user = authenticate_user("naoexiste", "senha")
        assert user is None

    def test_get_user(self):
        create_user("admin", "admin123")
        user = get_user("admin")
        assert user is not None

    def test_list_users(self):
        create_user("admin", "admin123")
        create_user("user", "user123", role="user")
        users = list_users()
        assert len(users) == 2

    def test_delete_user(self):
        create_user("admin", "admin123")
        assert delete_user("admin") is True
        assert get_user("admin") is None

    def test_delete_nonexistent(self):
        assert delete_user("naoexiste") is False

    def test_user_roles(self):
        create_user("admin", "admin123", role="admin")
        create_user("operador", "oper123", role="user")
        create_user("consulta", "cons123", role="readonly")
        assert get_user("admin").role == "admin"
        assert get_user("operador").role == "user"
        assert get_user("consulta").role == "readonly"

    def test_user_to_dict(self):
        user = create_user("admin", "admin123")
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
