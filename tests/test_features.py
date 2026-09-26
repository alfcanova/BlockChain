"""Testes das features F2, F3, F4, F8, F9, F10 e F11.

- F2  Rate limiting (middleware, 429)
- F3  Refresh tokens + logout (revogacao)
- F4  Complexidade de senha
- F8  Health enriquecido (DB + memoria)
- F9  Metricas Prometheus
- F10 Migracoes versionadas (schema_version)
- F11 Audit log de chamadas de API
"""
import time

import pytest
from fastapi.testclient import TestClient

import web_app
from web_app import app, _METRICS, _rate_buckets
from blockchain_pf.database import Database
from blockchain_pf.auth import init_default_users
from blockchain_pf import auth as auth_mod

client = TestClient(app)


def login_admin():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _limpa_estado_features():
    """Isola cada teste: garante seeds e zera buckets/contadores."""
    init_default_users()
    _rate_buckets.clear()
    _METRICS["http_requests_total"].clear()
    _METRICS["http_request_duration_seconds"].clear()
    _METRICS["auth_login_attempts_total"].clear()
    yield
    _rate_buckets.clear()
    _METRICS["http_requests_total"].clear()
    _METRICS["http_request_duration_seconds"].clear()
    _METRICS["auth_login_attempts_total"].clear()


# ══════════════════════════════════════════════════════════════════════
# F4 — Complexidade de senha
# ══════════════════════════════════════════════════════════════════════

class TestF4PasswordComplexity:
    def test_senhas_fracas_rejeitadas(self):
        fracas = [
            "curta",            # < 8 chars
            "minusculas1!",     # sem maiuscula
            "MAIUSCULAS1!",     # sem minuscula
            "SemNumero!",       # sem numero
            "SemEspecial1",     # sem especial
        ]
        for senha in fracas:
            assert auth_mod.validate_password_strength(senha) is not None, senha

    def test_senha_forte_aceita(self):
        assert auth_mod.validate_password_strength("Senha#F0rte") is None

    def test_api_rejeita_senha_fraca_400(self):
        t = login_admin()
        r = client.post("/api/auth/users",
                        json={"username": "fraco_user", "password": "s1", "role": "user"},
                        headers=hdr(t))
        assert r.status_code == 400
        assert "Senha" in r.json()["detail"]

    def test_api_aceita_senha_forte_201(self):
        t = login_admin()
        r = client.post("/api/auth/users",
                        json={"username": "forte_user", "password": "Senha#F0rte", "role": "user"},
                        headers=hdr(t))
        assert r.status_code == 201

    def test_create_user_duplicata_prevalece_sobre_senha(self):
        """Usuario ja existente continua retornando 'ja existe' (ordem de checks)."""
        auth_mod.create_user("dup", "Senha#F0rte", _internal=False)
        with pytest.raises(ValueError, match="ja existe"):
            auth_mod.create_user("dup", "fraca", _internal=False)


# ══════════════════════════════════════════════════════════════════════
# F3 — Refresh tokens + logout
# ══════════════════════════════════════════════════════════════════════

class TestF3RefreshTokens:
    def test_login_retorna_refresh_token(self):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        data = r.json()["data"]
        assert "refresh_token" in data
        assert data["refresh_token"] != data["token"]

    def test_refresh_renova_access_token(self):
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).json()["data"]
        r = client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert r.status_code == 200
        novo = r.json()["data"]["token"]
        assert novo != login["token"]

    def test_refresh_token_invalido_401(self):
        r = client.post("/api/auth/refresh", json={"refresh_token": "lixo"})
        assert r.status_code == 401

    def test_refresh_token_nao_serve_como_access(self):
        """typ=refresh deve ser rejeitado quando o endpoint exige access."""
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).json()["data"]
        payload = auth_mod.decode_access_token(login["refresh_token"], expected_type="access")
        assert payload is None

    def test_logout_revoga_tokens(self):
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).json()["data"]
        r = client.post("/api/auth/logout", headers=hdr(login["token"]))
        assert r.status_code == 200
        # access token emitido antes do logout nao autentica mais
        r2 = client.get("/api/auth/me", headers=hdr(login["token"]))
        assert r2.status_code == 401


# ══════════════════════════════════════════════════════════════════════
# F2 — Rate limiting
# ══════════════════════════════════════════════════════════════════════

class TestF2RateLimit:
    def test_rate_check_bloqueia_apos_limite(self, monkeypatch):
        """_rate_check puro: janela fixa de 60s por chave."""
        web_app.RATE_LIMIT_ENABLED = True
        try:
            for _ in range(5):
                assert web_app._rate_check("t:chave", 5) is True
            assert web_app._rate_check("t:chave", 5) is False
        finally:
            web_app.RATE_LIMIT_ENABLED = False

    def test_rate_check_janela_expirada_reinicia(self, monkeypatch):
        web_app.RATE_LIMIT_ENABLED = True
        try:
            for _ in range(5):
                web_app._rate_check("t:exp", 5)
            assert web_app._rate_check("t:exp", 5) is False
            # Simula passagem da janela (60s)
            _rate_buckets["t:exp"][0] -= 61.0
            assert web_app._rate_check("t:exp", 5) is True
        finally:
            web_app.RATE_LIMIT_ENABLED = False

    def test_login_excedido_retorna_429(self, monkeypatch):
        """Com limiter ativo e bucket preenchido, login recebe 429."""
        monkeypatch.setattr(web_app, "RATE_LIMIT_ENABLED", True)
        _rate_buckets["login:testclient"] = [time.time(), 999]
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 429

    def test_desligado_nao_bloqueia(self, monkeypatch):
        monkeypatch.setattr(web_app, "RATE_LIMIT_ENABLED", False)
        _rate_buckets["login:testclient"] = [time.time(), 999]
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# F9 — Metricas Prometheus
# ══════════════════════════════════════════════════════════════════════

class TestF9Metrics:
    def test_metrics_content_type_prometheus(self):
        r = client.get("/api/metrics")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]

    def test_metrics_contem_contadores(self):
        login_admin()  # gera trafego + contador de login
        r = client.get("/api/metrics")
        body = r.text
        assert "http_requests_total" in body
        assert "auth_login_attempts_total" in body
        assert 'outcome="ok"' in body
        assert "/api/metrics" not in body  # rota excluida da contagem

    def test_login_falha_contabilizada(self):
        client.post("/api/auth/login", json={"username": "admin", "password": "errada"})
        body = client.get("/api/metrics").text
        assert 'outcome="falha"' in body


# ══════════════════════════════════════════════════════════════════════
# F8 — Health enriquecido
# ══════════════════════════════════════════════════════════════════════

class TestF8Health:
    def test_health_tem_db_e_memoria(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["database"]["status"] == "ok"
        assert "schema_version" in data["database"]
        assert data["memoria"] is not None
        assert "rss_mb" in data["memoria"]
        assert "AU" in data["blockchains"]

    def test_health_sem_auth(self):
        assert client.get("/api/health").status_code == 200


# ══════════════════════════════════════════════════════════════════════
# F10 — Migracoes versionadas
# ══════════════════════════════════════════════════════════════════════

class TestF10Migracoes:
    def test_schema_version_apos_criar_db(self, tmp_path):
        db = Database(str(tmp_path / "migr.db"))
        assert db.schema_version() == 1  # migracao 1 (audit_log) aplicada

    def test_migracao_idempotente(self, tmp_path):
        path = str(tmp_path / "migr2.db")
        db1 = Database(path)
        n1 = db1.count_audit_entries()
        db1.close()
        db2 = Database(path)  # reabre: nao deve re-executar nem duplicar
        assert db2.schema_version() == 1
        assert db2.count_audit_entries() == n1
        db2.close()

    def test_tabela_audit_existe(self, tmp_path):
        db = Database(str(tmp_path / "migr3.db"))
        conn = db._get_conn()
        tables = {r["name"] for r in
                  conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "audit_log" in tables
        db.close()


# ══════════════════════════════════════════════════════════════════════
# F11 — Audit log
# ══════════════════════════════════════════════════════════════════════

class TestF11AuditLog:
    def test_chamadas_sao_registradas(self):
        t = login_admin()
        client.get("/api/chains", headers=hdr(t))
        r = client.get("/api/audit?limit=5", headers=hdr(t))
        assert r.status_code == 200
        entradas = r.json()["data"]
        assert len(entradas) > 0
        # A entrada mais recente e a chamada anterior ao proprio audit
        # (o registro da requisicao /api/audit em si e gravado apos a resposta)
        assert entradas[0]["path"] == "/api/chains"
        assert entradas[0]["username"] == "admin"
        assert entradas[0]["status"] == 200

    def test_health_e_metrics_nao_auditados(self):
        login_admin()
        r = client.get("/api/audit?limit=50", headers=hdr(login_admin()))
        paths = {e["path"] for e in r.json()["data"]}
        assert "/api/health" not in paths
        assert "/api/metrics" not in paths

    def test_audit_somente_admin(self):
        t = login_admin()
        # usuario comum nao pode ler o audit log
        client.post("/api/auth/users", json={"username": "aud_nao_admin",
                                             "password": "Senha#F0rte", "role": "user"},
                    headers=hdr(t))
        login_user = client.post("/api/auth/login",
                                 json={"username": "aud_nao_admin", "password": "Senha#F0rte"})
        t2 = login_user.json()["data"]["token"]
        r = client.get("/api/audit", headers=hdr(t2))
        assert r.status_code == 403
