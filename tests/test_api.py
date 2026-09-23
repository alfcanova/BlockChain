"""Testes de integracao para a API REST com JWT Auth."""
import pytest
from fastapi.testclient import TestClient
from web_app import app, chains
from blockchain_pf.auth import init_default_users, _users_db

client = TestClient(app)

def login_admin():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]

def login_user():
    r = client.post("/api/auth/login", json={"username": "operador", "password": "oper123"})
    return r.json()["data"]["token"]

def login_readonly():
    r = client.post("/api/auth/login", json={"username": "consulta", "password": "cons123"})
    return r.json()["data"]["token"]

def hdr(token):
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def cleanup():
    from web_app import db as _db
    chains.clear()
    _users_db.clear()
    if _db:
        with _db._transaction() as conn:
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM chains")
    init_default_users()
    yield
    chains.clear()
    _users_db.clear()
    if _db:
        with _db._transaction() as conn:
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM chains")

BIRTH = {"cpf":"12345678901","nome_completo":"Maria Clara","data_nascimento":"15/03/2000","sexo":"F","cidade_nascimento":"Sao Paulo","uf_nascimento":"SP","nome_mae":"Ana Paula"}
CPF = "12345678901"

def _create_chain():
    t = login_admin(); h = hdr(t)
    client.post(f"/api/chain?cpf={CPF}", json={"difficulty":2}, headers=h)
    client.post(f"/api/chain/{CPF}/event/nascimento", json=BIRTH, headers=h)
    return t, h

# ══════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════

class TestAuth:
    def test_login_ok(self):
        r = client.post("/api/auth/login", json={"username":"admin","password":"admin123"})
        assert r.status_code == 200 and "token" in r.json()["data"]
    def test_login_wrong(self):
        r = client.post("/api/auth/login", json={"username":"admin","password":"errada"})
        assert r.status_code == 401
    def test_me(self):
        t = login_admin(); r = client.get("/api/auth/me", headers=hdr(t))
        assert r.status_code == 200
    def test_me_no_auth(self):
        assert client.get("/api/auth/me").status_code == 401
    def test_list_users(self):
        t = login_admin(); r = client.get("/api/auth/users", headers=hdr(t))
        assert r.status_code == 200 and len(r.json()["data"]) == 3
    def test_create_user(self):
        t = login_admin()
        r = client.post("/api/auth/users", json={"username":"novo","password":"s1","role":"user"}, headers=hdr(t))
        assert r.status_code == 201
    def test_delete_user(self):
        t = login_admin()
        client.post("/api/auth/users", json={"username":"del","password":"s1"}, headers=hdr(t))
        r = client.delete("/api/auth/users/del", headers=hdr(t))
        assert r.status_code == 200
    def test_cannot_delete_admin(self):
        t = login_admin()
        assert client.delete("/api/auth/users/admin", headers=hdr(t)).status_code == 400

# ══════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════

class TestHealth:
    def test_health(self):
        r = client.get("/api/health")
        assert r.status_code == 200 and r.json()["status"] == "ok"

# ══════════════════════════════════════════════════════════════════════
#  CHAIN CRUD
# ══════════════════════════════════════════════════════════════════════

class TestChainCRUD:
    def test_create_chain(self):
        t,h = _create_chain(); assert True
    def test_create_no_auth(self):
        assert client.post(f"/api/chain?cpf={CPF}", json={"difficulty":2}).status_code == 401
    def test_create_readonly_fails(self):
        t = login_readonly()
        assert client.post(f"/api/chain?cpf={CPF}", json={"difficulty":2}, headers=hdr(t)).status_code == 403
    def test_list_chains(self):
        _create_chain()
        r = client.get("/api/chains"); assert len(r.json()["data"]) == 1
    def test_get_chain(self):
        _create_chain()
        r = client.get(f"/api/chain/{CPF}"); assert r.status_code == 200
    def test_delete_chain(self):
        t,h = _create_chain()
        assert client.delete(f"/api/chain/{CPF}", headers=hdr(t)).status_code == 200
    def test_delete_no_auth(self):
        _create_chain()
        assert client.delete(f"/api/chain/{CPF}").status_code == 401

# ══════════════════════════════════════════════════════════════════════
#  EVENTOS
# ══════════════════════════════════════════════════════════════════════

class TestEvents:
    def test_nascimento_ok(self):
        _create_chain()
        assert client.get(f"/api/chain/{CPF}/validate").json()["data"]["valida"]
    def test_nascimento_signed(self):
        t = login_admin(); h = hdr(t)
        client.post(f"/api/chain?cpf={CPF}", json={"difficulty":2,"signer_label":"Cartorio"}, headers=h)
        r = client.post(f"/api/chain/{CPF}/event/nascimento", json=BIRTH, headers=h)
        assert r.json()["data"]["assinado"]
    def test_casamento_ok(self):
        t,h = _create_chain()
        r = client.post(f"/api/chain/{CPF}/event/casamento", json={"cpf":CPF,"nome_conjuge":"Pedro","cpf_conjuge":"98765432100","data_casamento":"20/06/2022"}, headers=h)
        assert r.status_code == 201
    def test_casamento_no_auth(self):
        _create_chain()
        r = client.post(f"/api/chain/{CPF}/event/casamento", json={"cpf":CPF,"nome_conjuge":"Pedro","cpf_conjuge":"98765432100","data_casamento":"20/06/2022"})
        assert r.status_code == 401
    def test_divorcio_ok(self):
        t,h = _create_chain()
        client.post(f"/api/chain/{CPF}/event/casamento", json={"cpf":CPF,"nome_conjuge":"Pedro","cpf_conjuge":"98765432100","data_casamento":"20/06/2022"}, headers=h)
        r = client.post(f"/api/chain/{CPF}/event/divorcio", json={"cpf":CPF,"data_divorcio":"05/01/2025"}, headers=h)
        assert r.status_code == 201
    def test_adocao_ok(self):
        t,h = _create_chain()
        r = client.post(f"/api/chain/{CPF}/event/adocao", json={"cpf":CPF,"data_adocao":"10/11/2023","nome_mae_adotiva":"Maria"}, headers=h)
        assert r.status_code == 201
    def test_obito_ok(self):
        t,h = _create_chain()
        r = client.post(f"/api/chain/{CPF}/event/obito", json={"cpf":CPF,"data_obito":"01/01/2050","cidade_obito":"SP","uf_obito":"SP"}, headers=h)
        assert r.status_code == 201
    def test_obito_blocks_events(self):
        t,h = _create_chain()
        client.post(f"/api/chain/{CPF}/event/obito", json={"cpf":CPF,"data_obito":"01/01/2050","cidade_obito":"SP","uf_obito":"SP"}, headers=h)
        r = client.post(f"/api/chain/{CPF}/event/casamento", json={"cpf":CPF,"nome_conjuge":"X","cpf_conjuge":"000","data_casamento":"01/01/2051"}, headers=h)
        assert r.status_code == 400
    def test_obito_allows_alteracao_nome(self):
        t,h = _create_chain()
        client.post(f"/api/chain/{CPF}/event/obito", json={"cpf":CPF,"data_obito":"01/01/2050","cidade_obito":"SP","uf_obito":"SP"}, headers=h)
        r = client.post(f"/api/chain/{CPF}/event/alteracao_nome", json={"cpf":CPF,"nome_anterior":"Maria","nome_novo":"Maria X","data_alteracao":"15/03/2018"}, headers=h)
        assert r.status_code == 201
    def test_alteracao_nome_ok(self):
        t,h = _create_chain()
        r = client.post(f"/api/chain/{CPF}/event/alteracao_nome", json={"cpf":CPF,"nome_anterior":"Maria","nome_novo":"Maria Santos","data_alteracao":"15/03/2018"}, headers=h)
        assert r.status_code == 201
    def test_disvinculacao_materna(self):
        t,h = _create_chain()
        r = client.post(f"/api/chain/{CPF}/event/disvinculacao", json={"cpf":CPF,"data_disvinculacao":"15/03/2026","motivo":"Ausencia","tipo":"M"}, headers=h)
        assert r.status_code == 201
    def test_disvinculacao_paterna(self):
        t,h = _create_chain()
        r = client.post(f"/api/chain/{CPF}/event/disvinculacao", json={"cpf":CPF,"data_disvinculacao":"15/03/2026","motivo":"Abandono","tipo":"P"}, headers=h)
        assert r.status_code == 201

# ══════════════════════════════════════════════════════════════════════
#  READ-ONLY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

class TestReadOnly:
    def test_validate(self):
        _create_chain(); r = client.get(f"/api/chain/{CPF}/validate")
        assert r.status_code == 200 and r.json()["data"]["valida"]
    def test_signatures(self):
        t = login_admin(); h = hdr(t)
        client.post(f"/api/chain?cpf={CPF}", json={"difficulty":2,"signer_label":"Cart"}, headers=h)
        client.post(f"/api/chain/{CPF}/event/nascimento", json=BIRTH, headers=h)
        r = client.get(f"/api/chain/{CPF}/signatures")
        assert r.json()["data"]["todas_validas"]
    def test_timeline(self):
        _create_chain(); r = client.get(f"/api/chain/{CPF}/timeline")
        assert len(r.json()["data"]) == 1
    def test_predictions(self):
        _create_chain(); r = client.get(f"/api/chain/{CPF}/predictions")
        assert len(r.json()["data"]["predicoes"]) > 0
    def test_export(self):
        _create_chain(); r = client.get(f"/api/chain/{CPF}/export")
        assert len(r.json()["data"]["chain"]) == 1
    def test_configure_signer(self):
        t,h = _create_chain()
        r = client.post(f"/api/chain/{CPF}/sign", json={"label":"Cart"}, headers=h)
        assert r.status_code == 200

# ══════════════════════════════════════════════════════════════════════
#  E2E FULL LIFECYCLE
# ══════════════════════════════════════════════════════════════════════

class TestFullLifecycle:
    def test_full_lifecycle(self):
        CPF2 = "11122233344"
        t = login_admin(); h = hdr(t)
        client.post(f"/api/chain?cpf={CPF2}", json={"difficulty":2,"signer_label":"Cartorio"}, headers=h)
        client.post(f"/api/chain/{CPF2}/event/nascimento", json={"cpf":CPF2,"nome_completo":"Ana","data_nascimento":"20/08/1995","sexo":"F","cidade_nascimento":"Rio de Janeiro","uf_nascimento":"RJ","nome_mae":"Clara"}, headers=h)
        client.post(f"/api/chain/{CPF2}/event/alteracao_nome", json={"cpf":CPF2,"nome_anterior":"Ana","nome_novo":"Ana Lima","data_alteracao":"20/08/2013"}, headers=h)
        client.post(f"/api/chain/{CPF2}/event/casamento", json={"cpf":CPF2,"nome_conjuge":"Lucas","cpf_conjuge":"55566677788","data_casamento":"15/12/2020"}, headers=h)
        client.post(f"/api/chain/{CPF2}/event/adocao", json={"cpf":CPF2,"data_adocao":"01/06/2022","nome_mae_adotiva":"Ana"}, headers=h)
        client.post(f"/api/chain/{CPF2}/event/divorcio", json={"cpf":CPF2,"data_divorcio":"01/03/2024"}, headers=h)
        client.post(f"/api/chain/{CPF2}/event/disvinculacao", json={"cpf":CPF2,"data_disvinculacao":"15/06/2025","motivo":"Ausencia","tipo":"P"}, headers=h)
        tl = client.get(f"/api/chain/{CPF2}/timeline").json()["data"]
        assert len(tl) == 6
        v = client.get(f"/api/chain/{CPF2}/validate?require_signatures=true").json()["data"]
        assert v["valida"]
        s = client.get(f"/api/chain/{CPF2}/signatures").json()["data"]
        assert s["todas_validas"]
        client.post(f"/api/chain/{CPF2}/event/obito", json={"cpf":CPF2,"data_obito":"01/01/2080","cidade_obito":"RJ","uf_obito":"RJ"}, headers=h)
        assert client.post(f"/api/chain/{CPF2}/event/casamento", json={"cpf":CPF2,"nome_conjuge":"X","cpf_conjuge":"000","data_casamento":"01/01/2081"}, headers=h).status_code == 400
        client.post(f"/api/chain/{CPF2}/event/alteracao_nome", json={"cpf":CPF2,"nome_anterior":"Ana Lima","nome_novo":"Ana Lima (In Memoriam)","data_alteracao":"01/01/2080"}, headers=h)
        v2 = client.get(f"/api/chain/{CPF2}/validate?require_signatures=true").json()["data"]
        assert v2["valida"] and v2["assinados"] == 8
