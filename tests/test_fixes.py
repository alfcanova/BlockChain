"""Testes de regressao dos fixes F1-F3 (rotas genericas, validacao, CORS, DB)."""
import pytest
from fastapi.testclient import TestClient
from web_app import app, chains, im_chains, mo_chains, co_chains, em_chains, ac_chains, an_chains
from blockchain_pf.auth import init_default_users, _users_db

client = TestClient(app)


def login_admin():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def cleanup():
    from web_app import db as _db

    def _clear():
        for store in (chains, im_chains, mo_chains, co_chains, em_chains, ac_chains, an_chains):
            store.clear()
        _users_db.clear()
        if _db:
            with _db._transaction() as conn:
                conn.execute("DELETE FROM users")
                conn.execute("DELETE FROM chains")
                conn.execute("DELETE FROM cross_references")

    _clear()
    init_default_users()
    yield
    _clear()


PF = "12345678901"


def _create_pf_chain():
    t = login_admin()
    h = hdr(t)
    client.post(f"/api/chain?cpf={PF}", json={"difficulty": 2}, headers=h)
    client.post(f"/api/chain/{PF}/event/nascimento", json={
        "cpf": PF, "nome_completo": "Maria Clara", "data_nascimento": "15/03/2000",
        "sexo": "F", "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP", "nome_mae": "Ana",
    }, headers=h)
    return t, h


BODY_MO = {
    "placa": "ABC1D23", "renavan": "12345678901", "chassis": "9BWZZZ377VT004251",
    "marca": "Volkswagen", "modelo": "Gol", "ano_fabricacao": 2020, "ano_modelo": 2021,
    "cor": "Preto", "combustivel": "GASOLINA", "cilindradas": 1000, "potencia_cv": 75.0, "uf": "SP", "cidade": "Sao Paulo",
}
BODY_CO = {
    "cnpj": "11222333000181", "razao_social": "Empresa Teste SA",
    "nome_fantasia": "Teste", "data_constituicao": "01/01/2020", "tipo_empresa": "SA",
    "porte": "MEDIA", "capital_social": 100000.00, "natureza_juridica": "S/A",
    "atividade_principal": "Comercio", "uf": "SP", "cidade": "Sao Paulo",
}
BODY_EM = {
    "registro_nr": "EM-001", "nome_embarcacao": "Barco Teste", "tipo_embarcacao": "LANCHA",
    "porte": "PEQUENO", "comprimento_m": 12.5, "beam_m": 3.0, "pontal_m": 1.5,
    "calado_m": 0.8, "deslocamento_ton": 5.0, "casco_material": "ALUMINIO",
    "motorizacao": "DIESEL", "motor_potencia_cv": 150.0, "uf": "SP", "cidade": "Sao Paulo",
}
BODY_AC = {
    "matricula": "PT-ABC", "nome_aeronave": "Aviao Teste", "fabricante": "Cessna",
    "modelo": "172", "tipo_aeronave": "MONOMOTOR", "ano_fabricacao": 2018,
    "peso_max_decolagem_kg": 1100.0, "motorizacao": "PISTAO", "num_motores": 1, "uf": "SP", "cidade": "Sao Paulo",
}
BODY_AN = {
    "nome": "Rex", "especie": "CACHORRO", "raca": "SRD", "sexo": "M",
    "data_nascimento": "01/01/2019", "cor": "CARAMELO", "peso_kg": 20.5,
    "proprietario_cpf": PF, "proprietario_nome": "Maria Clara", "uf": "SP", "cidade": "Sao Paulo",
}


class TestGenericEventPF:
    def test_generic_event_no_auth(self):
        _create_pf_chain()
        r = client.post(f"/api/chain/{PF}/event", json={"event_type": "ALTERACAO_NOME", "payload": {}})
        assert r.status_code == 401

    def test_generic_event_ok(self):
        t, h = _create_pf_chain()
        r = client.post(f"/api/chain/{PF}/event", json={
            "event_type": "ALTERACAO_NOME",
            "payload": {"nome_anterior": "Maria Clara", "nome_novo": "Maria Santos", "data_alteracao": "15/03/2018"},
        }, headers=h)
        assert r.status_code == 201
        assert r.json()["data"]["assinado"]
        assert len(client.get(f"/api/chain/{PF}/timeline").json()["data"]) == 2

    def test_generic_event_invalid_type(self):
        t, h = _create_pf_chain()
        r = client.post(f"/api/chain/{PF}/event", json={
            "event_type": "TIPO_INEXISTENTE", "payload": {"x": 1},
        }, headers=h)
        assert r.status_code == 400
        assert "Permitidos" in r.json()["detail"]


class TestCreateEndpoints:
    def test_mo_create_ok(self):
        t, h = login_admin(), None
        h = hdr(t)
        r = client.post("/api/mo", json=BODY_MO, headers=h)
        assert r.status_code == 201
        assert r.json()["data"]["placa"] == "ABC1D23"

    def test_mo_create_missing_required_422(self):
        t = login_admin()
        body = dict(BODY_MO)
        del body["renavan"]
        r = client.post("/api/mo", json=body, headers=hdr(t))
        assert r.status_code == 422

    def test_mo_create_extra_fields_ignored(self):
        t = login_admin()
        body = dict(BODY_MO, campo_desconhecido="xyz", outro={"a": 1})
        r = client.post("/api/mo", json=body, headers=hdr(t))
        assert r.status_code == 201

    def test_co_create_ok(self):
        t = login_admin()
        r = client.post("/api/co", json=BODY_CO, headers=hdr(t))
        assert r.status_code == 201
        assert r.json()["data"]["cnpj"] == "11222333000181"

    def test_co_create_missing_required_422(self):
        t = login_admin()
        body = dict(BODY_CO)
        del body["razao_social"]
        assert client.post("/api/co", json=body, headers=hdr(t)).status_code == 422

    def test_em_create_ok(self):
        t = login_admin()
        assert client.post("/api/em", json=BODY_EM, headers=hdr(t)).status_code == 201

    def test_em_create_missing_required_422(self):
        t = login_admin()
        body = dict(BODY_EM)
        del body["registro_nr"]
        assert client.post("/api/em", json=body, headers=hdr(t)).status_code == 422

    def test_ac_create_ok(self):
        t = login_admin()
        assert client.post("/api/ac", json=BODY_AC, headers=hdr(t)).status_code == 201

    def test_ac_create_missing_required_422(self):
        t = login_admin()
        body = dict(BODY_AC)
        del body["num_motores"]
        assert client.post("/api/ac", json=body, headers=hdr(t)).status_code == 422

    def test_an_create_ok(self):
        t = login_admin()
        assert client.post("/api/an", json=BODY_AN, headers=hdr(t)).status_code == 201

    def test_an_create_missing_required_422(self):
        t = login_admin()
        body = dict(BODY_AN)
        del body["proprietario_nome"]
        assert client.post("/api/an", json=body, headers=hdr(t)).status_code == 422


class TestWhitelistDomainEvents:
    def test_mo_invalid_event_type_400(self):
        t = login_admin()
        h = hdr(t)
        client.post("/api/mo", json=BODY_MO, headers=h)
        r = client.post("/api/mo/ABC1D23/event", json={
            "event_type": "FOOBAR", "payload": {},
        }, headers=h)
        assert r.status_code == 400
        assert "Permitidos" in r.json()["detail"]

    def test_mo_valid_cor_event_ok(self):
        t = login_admin()
        h = hdr(t)
        client.post("/api/mo", json=BODY_MO, headers=h)
        r = client.post("/api/mo/ABC1D23/event", json={
            "event_type": "MUDANCA_COR", "payload": {"cor": "Vermelho", "data_mudanca": "10/10/2025"},
        }, headers=h)
        assert r.status_code == 201

    def test_an_invalid_event_type_400(self):
        t = login_admin()
        h = hdr(t)
        r = client.post("/api/an", json=BODY_AN, headers=h)
        aid = r.json()["data"]["animal_id"]
        r2 = client.post(f"/api/an/{aid}/event", json={"event_type": "XX", "payload": {}}, headers=h)
        assert r2.status_code == 400


class TestCrossVinculo:
    def test_create_missing_fields_422(self):
        t = login_admin()
        assert client.post("/api/cross/vinculo", json={}, headers=hdr(t)).status_code == 422

    def test_delete_missing_fields_422(self):
        t = login_admin()
        r = client.request("DELETE", "/api/cross/vinculo", json={}, headers=hdr(t))
        assert r.status_code == 422

    def test_create_and_delete_ok(self):
        t = login_admin()
        h = hdr(t)
        _create_pf_chain()
        client.post("/api/mo", json=BODY_MO, headers=h)
        r = client.post("/api/cross/vinculo", json={
            "origem_tipo": "PF", "origem_id": PF,
            "destino_tipo": "MO", "destino_id": "ABC1D23",
            "tipo_vinculo": "PROPRIETARIO",
        }, headers=h)
        assert r.status_code == 201
        r2 = client.request("DELETE", "/api/cross/vinculo", json={
            "origem_tipo": "PF", "origem_id": PF,
            "destino_tipo": "MO", "destino_id": "ABC1D23",
            "tipo_vinculo": "PROPRIETARIO",
        }, headers=h)
        assert r2.status_code == 200
        assert r2.json()["data"]["desativados"] == 1


class TestCORS:
    def test_cors_defaults_localhost(self):
        r = client.options("/api/health", headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "GET",
        })
        assert r.status_code == 200
        assert "http://localhost:8000" in r.headers.get("access-control-allow-origin", "")