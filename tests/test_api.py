"""Testes de integracao para a API REST com JWT Auth."""
import pytest
from fastapi.testclient import TestClient
from web_app import app, chains
from web_app import (
    im_chains, mo_chains, co_chains, em_chains, ac_chains, an_chains,
)
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
    """Isola cada teste: limpa usuarios e todos os dicts de cadeias em memoria.

    O DELETE FROM chains no SQLite tambem remove cadeias de dominio
    (tabela unica com coluna domain). au_chains nao e limpo: preserva
    o seed das autoridades N0 feito no startup.
    """
    from web_app import db as _db
    domain_dicts = (im_chains, mo_chains, co_chains, em_chains, ac_chains, an_chains)
    chains.clear()
    for d in domain_dicts:
        d.clear()
    _users_db.clear()
    if _db:
        with _db._transaction() as conn:
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM chains")
    init_default_users()
    yield
    chains.clear()
    for d in domain_dicts:
        d.clear()
    _users_db.clear()
    if _db:
        with _db._transaction() as conn:
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM chains")

BIRTH = {"cpf":"12345678909","nome_completo":"Maria Clara","data_nascimento":"15/03/2000","sexo":"F","cidade_nascimento":"Sao Paulo","uf_nascimento":"SP","nome_mae":"Ana Paula"}
CPF = "12345678909"

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
        r = client.post("/api/auth/users", json={"username":"novo","password":"Senha#F0rte","role":"user"}, headers=hdr(t))
        assert r.status_code == 201
    def test_delete_user(self):
        t = login_admin()
        client.post("/api/auth/users", json={"username":"del","password":"Senha#F0rte"}, headers=hdr(t))
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
        _create_chain(); r = client.get(f"/api/chain/{CPF}/export", headers=hdr(login_admin()))
        assert len(r.json()["data"]["chain"]) == 1
    def test_export_no_auth(self):
        _create_chain()
        # /export e a unica rota GET protegida (H1) — exige token
        assert client.get(f"/api/chain/{CPF}/export").status_code == 401
    def test_configure_signer(self):
        t,h = _create_chain()
        r = client.post(f"/api/chain/{CPF}/sign", json={"label":"Cart"}, headers=h)
        assert r.status_code == 200

# ══════════════════════════════════════════════════════════════════════
#  E2E FULL LIFECYCLE
# ══════════════════════════════════════════════════════════════════════

class TestFullLifecycle:
    def test_full_lifecycle(self):
        CPF2 = "11122233396"
        t = login_admin(); h = hdr(t)
        client.post(f"/api/chain?cpf={CPF2}", json={"difficulty":2,"signer_label":"Cartorio"}, headers=h)
        client.post(f"/api/chain/{CPF2}/event/nascimento", json={"cpf":CPF2,"nome_completo":"Ana","data_nascimento":"20/08/1995","sexo":"F","cidade_nascimento":"Rio de Janeiro","uf_nascimento":"RJ","nome_mae":"Clara"}, headers=h)
        client.post(f"/api/chain/{CPF2}/event/alteracao_nome", json={"cpf":CPF2,"nome_anterior":"Ana","nome_novo":"Ana Lima","data_alteracao":"20/08/2013"}, headers=h)
        client.post(f"/api/chain/{CPF2}/event/casamento", json={"cpf":CPF2,"nome_conjuge":"Lucas","cpf_conjuge":"55566677720","data_casamento":"15/12/2020"}, headers=h)
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

# ══════════════════════════════════════════════════════════════════════
#  DOMÍNIOS: EM (Embarcações) — Fase 5.6
# ══════════════════════════════════════════════════════════════════════

EM_CREATE = {
    "registro_nr": "NR-TEST-001", "nome_embarcacao": "Estrela do Mar",
    "tipo_embarcacao": "Lancha", "porte": "PEQUENO",
    "comprimento_m": 8.5, "beam_m": 3.0, "pontal_m": 1.5,
    "calado_m": 0.8, "deslocamento_ton": 2.5,
    "casco_material": "Fibra", "uf": "SP", "cidade": "Sao Paulo",
    "motorizacao": "Fora-de-borda", "motor_potencia_cv": 150,
}


def _criar_em():
    t = login_admin(); h = hdr(t)
    r = client.post("/api/em", json=EM_CREATE, headers=h)
    assert r.status_code == 201, r.json()
    return t, h


class TestApiEmbarcacoes:
    def test_create_ok(self):
        _criar_em()
        r = client.get("/api/em/NR-TEST-001")
        assert r.status_code == 200
        assert r.json()["data"]["estado"]["registro_nr"] == "NR-TEST-001"

    def test_create_no_auth(self):
        assert client.post("/api/em", json=EM_CREATE).status_code == 401

    def test_create_readonly_fails(self):
        t = login_readonly()
        r = client.post("/api/em", json=EM_CREATE, headers=hdr(t))
        assert r.status_code == 403

    def test_create_duplicado(self):
        _criar_em()
        t = login_admin()
        r = client.post("/api/em", json=EM_CREATE, headers=hdr(t))
        assert r.status_code == 409

    def test_create_payload_invalido(self):
        t = login_admin(); h = hdr(t)
        bad = dict(EM_CREATE, registro_nr="NR-BAD", nome_embarcacao="")
        r = client.post("/api/em", json=bad, headers=h)
        assert r.status_code == 400

    def test_get_404(self):
        assert client.get("/api/em/NR-NAO-EXISTE").status_code == 404

    def test_list_contem_embarcacao(self):
        _criar_em()
        r = client.get("/api/em")
        assert r.status_code == 200
        assert any(e["registro_nr"] == "NR-TEST-001" for e in r.json()["data"])

    def test_evento_ok(self):
        _criar_em()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/em/NR-TEST-001/event", json={
            "event_type": "MUDANCA_NOME",
            "payload": {"registro_nr": "NR-TEST-001", "nome_anterior": "Estrela do Mar",
                        "nome_novo": "Estrela do Norte", "data_mudanca": "01/06/2024"},
        }, headers=h)
        assert r.status_code == 201
        r = client.get("/api/em/NR-TEST-001")
        assert r.json()["data"]["estado"]["nome_embarcacao"] == "Estrela do Norte"

    def test_evento_no_auth(self):
        _criar_em()
        r = client.post("/api/em/NR-TEST-001/event", json={
            "event_type": "REVISAO",
            "payload": {"registro_nr": "NR-TEST-001", "data_revisao": "01/09/2024"},
        })
        assert r.status_code == 401

    def test_evento_tipo_invalido(self):
        _criar_em()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/em/NR-TEST-001/event", json={
            "event_type": "EVENTO_INEXISTENTE", "payload": {},
        }, headers=h)
        assert r.status_code == 400

    def test_evento_payload_invalido(self):
        """Payload com data em formato errado deve retornar 400 (M9/M10 corrigido):
chain.add_event() valida o payload contra o contrato do dominio."""
        _criar_em()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/em/NR-TEST-001/event", json={
            "event_type": "MUDANCA_NOME",
            "payload": {"registro_nr": "NR-TEST-001", "nome_anterior": "A",
                        "nome_novo": "B", "data_mudanca": "01-06-2024"},
        }, headers=h)
        assert r.status_code == 400

    def test_timeline(self):
        _criar_em()
        t = login_admin(); h = hdr(t)
        client.post("/api/em/NR-TEST-001/event", json={
            "event_type": "REVISAO",
            "payload": {"registro_nr": "NR-TEST-001", "data_revisao": "01/09/2024"},
        }, headers=h)
        r = client.get("/api/em/NR-TEST-001/timeline")
        assert r.status_code == 200 and len(r.json()["data"]) == 2

    def test_validate(self):
        _criar_em()
        r = client.get("/api/em/NR-TEST-001/validate?require_signatures=true")
        assert r.status_code == 200
        assert r.json()["data"]["valida"] and r.json()["data"]["blocos"] == 1

    def test_delete_admin(self):
        _criar_em()
        r = client.delete("/api/em/NR-TEST-001", headers=hdr(login_admin()))
        assert r.status_code == 200
        assert client.get("/api/em/NR-TEST-001").status_code == 404

    def test_delete_no_auth(self):
        _criar_em()
        assert client.delete("/api/em/NR-TEST-001").status_code == 401


# ══════════════════════════════════════════════════════════════════════
#  DOMÍNIOS: AC (Aeronaves) — Fase 5.6
# ══════════════════════════════════════════════════════════════════════

AC_CREATE = {
    "matricula": "PT-TST", "nome_aeronave": "Cessna 172",
    "fabricante": "Cessna", "modelo": "172S", "tipo_aeronave": "AVIAO",
    "ano_fabricacao": 2020, "peso_max_decolagem_kg": 1111,
    "uf": "SP", "cidade": "Sao Paulo",
    "motorizacao": "PISTAO", "num_motores": 1,
}


def _criar_ac():
    t = login_admin(); h = hdr(t)
    r = client.post("/api/ac", json=AC_CREATE, headers=h)
    assert r.status_code == 201, r.json()
    return t, h


class TestApiAeronaves:
    def test_create_ok(self):
        _criar_ac()
        r = client.get("/api/ac/PT-TST")
        assert r.status_code == 200
        assert r.json()["data"]["estado"]["matricula"] == "PTTST"

    def test_create_no_auth(self):
        assert client.post("/api/ac", json=AC_CREATE).status_code == 401

    def test_create_readonly_fails(self):
        t = login_readonly()
        r = client.post("/api/ac", json=AC_CREATE, headers=hdr(t))
        assert r.status_code == 403

    def test_create_duplicado(self):
        _criar_ac()
        t = login_admin()
        r = client.post("/api/ac", json=AC_CREATE, headers=hdr(t))
        assert r.status_code == 409

    def test_create_payload_invalido(self):
        t = login_admin(); h = hdr(t)
        r = client.post("/api/ac", json=dict(AC_CREATE, matricula="PT-BAD", nome_aeronave=""), headers=h)
        assert r.status_code == 400

    def test_get_404(self):
        assert client.get("/api/ac/PT-NAOEXISTE").status_code == 404

    def test_list_contem_aeronave(self):
        _criar_ac()
        r = client.get("/api/ac")
        assert r.status_code == 200
        # Listagem usa a chave do dict (matricula uppercase, sem normalizar)
        assert any(a["matricula"] == "PT-TST" for a in r.json()["data"])

    def test_evento_ok(self):
        _criar_ac()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/ac/PT-TST/event", json={
            "event_type": "INSPECAO",
            "payload": {"matricula": "PT-TST", "data_inspecao": "01/03/2024",
                        "orgao_inspecao": "ANAC", "resultado": "APROVADA"},
        }, headers=h)
        assert r.status_code == 201

    def test_evento_no_auth(self):
        _criar_ac()
        r = client.post("/api/ac/PT-TST/event", json={
            "event_type": "REVISAO",
            "payload": {"matricula": "PT-TST", "data_revisao": "01/03/2024"},
        })
        assert r.status_code == 401

    def test_evento_tipo_invalido(self):
        _criar_ac()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/ac/PT-TST/event", json={
            "event_type": "VOO_Livre", "payload": {},
        }, headers=h)
        assert r.status_code == 400

    def test_evento_payload_invalido(self):
        """Payload com data em formato errado deve retornar 400 (M9/M10 corrigido):
chain.add_event() valida o payload contra o contrato do dominio."""
        _criar_ac()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/ac/PT-TST/event", json={
            "event_type": "INSPECAO",
            "payload": {"matricula": "PT-TST", "data_inspecao": "2024-03-01",
                        "orgao_inspecao": "ANAC", "resultado": "APROVADA"},
        }, headers=h)
        assert r.status_code == 400

    def test_timeline(self):
        _criar_ac()
        t = login_admin(); h = hdr(t)
        client.post("/api/ac/PT-TST/event", json={
            "event_type": "REVISAO",
            "payload": {"matricula": "PT-TST", "data_revisao": "01/05/2024"},
        }, headers=h)
        r = client.get("/api/ac/PT-TST/timeline")
        assert r.status_code == 200 and len(r.json()["data"]) == 2

    def test_validate(self):
        _criar_ac()
        r = client.get("/api/ac/PT-TST/validate?require_signatures=true")
        assert r.status_code == 200
        assert r.json()["data"]["valida"] and r.json()["data"]["blocos"] == 1

    def test_delete_admin(self):
        _criar_ac()
        r = client.delete("/api/ac/PT-TST", headers=hdr(login_admin()))
        assert r.status_code == 200
        assert client.get("/api/ac/PT-TST").status_code == 404

    def test_delete_no_auth(self):
        _criar_ac()
        assert client.delete("/api/ac/PT-TST").status_code == 401


# ══════════════════════════════════════════════════════════════════════
#  DOMÍNIOS: AN (Animais) — Fase 5.6
# ══════════════════════════════════════════════════════════════════════

AN_CREATE = {
    "nome": "Rex", "especie": "CAO", "raca": "Labrador", "sexo": "M",
    "data_nascimento": "15/03/2024", "cor": "Dourado", "peso_kg": 5.0,
    "uf": "SP", "cidade": "Sao Paulo",
    "proprietario_cpf": "12345678909", "proprietario_nome": "João Silva",
}


def _criar_an():
    t = login_admin(); h = hdr(t)
    r = client.post("/api/an", json=AN_CREATE, headers=h)
    assert r.status_code == 201, r.json()
    return t, h, r.json()["data"]["animal_id"]


class TestApiAnimais:
    def test_create_ok(self):
        _, _, aid = _criar_an()
        r = client.get(f"/api/an/{aid}")
        assert r.status_code == 200
        assert r.json()["data"]["estado"]["nome"] == "Rex"

    def test_create_no_auth(self):
        assert client.post("/api/an", json=AN_CREATE).status_code == 401

    def test_create_readonly_fails(self):
        t = login_readonly()
        r = client.post("/api/an", json=AN_CREATE, headers=hdr(t))
        assert r.status_code == 403

    def test_create_duplicado(self):
        _criar_an()
        t = login_admin()
        r = client.post("/api/an", json=AN_CREATE, headers=hdr(t))
        assert r.status_code == 409

    def test_create_payload_invalido(self):
        """Factory nascimento rejeita sexo invalido."""
        t = login_admin(); h = hdr(t)
        bad = dict(AN_CREATE, sexo="X")
        r = client.post("/api/an", json=bad, headers=h)
        assert r.status_code == 400

    def test_get_404(self):
        assert client.get("/api/an/nao-existe").status_code == 404

    def test_list_contem_animal(self):
        _, _, aid = _criar_an()
        r = client.get("/api/an")
        assert r.status_code == 200
        assert any(a["animal_id"] == aid for a in r.json()["data"])

    def test_evento_ok(self):
        _, _, aid = _criar_an()
        t = login_admin(); h = hdr(t)
        r = client.post(f"/api/an/{aid}/event", json={
            "event_type": "VACINACAO",
            "payload": {"nome_vacina": "Raiva", "data_vacinacao": "01/04/2024", "dose": "1a dose"},
        }, headers=h)
        assert r.status_code == 201

    def test_evento_no_auth(self):
        _, _, aid = _criar_an()
        r = client.post(f"/api/an/{aid}/event", json={
            "event_type": "VACINACAO",
            "payload": {"nome_vacina": "Raiva", "data_vacinacao": "01/04/2024"},
        })
        assert r.status_code == 401

    def test_evento_tipo_invalido(self):
        _, _, aid = _criar_an()
        t = login_admin(); h = hdr(t)
        r = client.post(f"/api/an/{aid}/event", json={
            "event_type": "BANHO", "payload": {},
        }, headers=h)
        assert r.status_code == 400

    def test_evento_payload_invalido(self):
        """Payload com data em formato errado deve retornar 400 (M9/M10 corrigido):
chain.add_event() valida o payload contra o contrato do dominio."""
        _, _, aid = _criar_an()
        t = login_admin(); h = hdr(t)
        r = client.post(f"/api/an/{aid}/event", json={
            "event_type": "VACINACAO",
            "payload": {"nome_vacina": "Raiva", "data_vacinacao": "01-04-2024"},
        }, headers=h)
        assert r.status_code == 400

    def test_timeline(self):
        _, _, aid = _criar_an()
        t = login_admin(); h = hdr(t)
        client.post(f"/api/an/{aid}/event", json={
            "event_type": "VACINACAO",
            "payload": {"nome_vacina": "Raiva", "data_vacinacao": "01/04/2024"},
        }, headers=h)
        r = client.get(f"/api/an/{aid}/timeline")
        assert r.status_code == 200 and len(r.json()["data"]) == 2

    def test_validate(self):
        _, _, aid = _criar_an()
        r = client.get(f"/api/an/{aid}/validate?require_signatures=true")
        assert r.status_code == 200
        assert r.json()["data"]["valida"] and r.json()["data"]["blocos"] == 1

    def test_delete_admin(self):
        _, _, aid = _criar_an()
        r = client.delete(f"/api/an/{aid}", headers=hdr(login_admin()))
        assert r.status_code == 200
        assert client.get(f"/api/an/{aid}").status_code == 404

    def test_delete_no_auth(self):
        _, _, aid = _criar_an()
        assert client.delete(f"/api/an/{aid}").status_code == 401


# ══════════════════════════════════════════════════════════════════════
#  DOMÍNIOS: IM (Imóveis) — Fase 5.6
# ══════════════════════════════════════════════════════════════════════

IM_CREATE = {
    "matricula": "MAT-TEST-001",
    "endereco_logradouro": "Rua das Flores, 100",
    "endereco_bairro": "Centro",
    "endereco_cidade": "Sao Paulo",
    "endereco_uf": "SP",
    "endereco_cep": "01000-000",
    "lat": -23.55, "lon": -46.63,
    "area_terreno_m2": 500.0,
    "metragem_frente": 20.0, "metragem_fundo": 25.0,
    "metragem_lado_esq": 20.0, "metragem_lado_dir": 20.0,
}


def _criar_im():
    t = login_admin(); h = hdr(t)
    r = client.post("/api/im", json=IM_CREATE, headers=h)
    assert r.status_code == 201, r.json()
    return t, h


class TestApiImoveis:
    def test_create_ok(self):
        _criar_im()
        r = client.get("/api/im/MAT-TEST-001")
        assert r.status_code == 200
        assert r.json()["data"]["matricula"] == "MAT-TEST-001"
        assert r.json()["data"]["area_terreno"] == 500.0

    def test_create_no_auth(self):
        assert client.post("/api/im", json=IM_CREATE).status_code == 401

    def test_create_readonly_fails(self):
        t = login_readonly()
        r = client.post("/api/im", json=IM_CREATE, headers=hdr(t))
        assert r.status_code == 403

    def test_create_duplicado(self):
        _criar_im()
        t = login_admin()
        r = client.post("/api/im", json=IM_CREATE, headers=hdr(t))
        assert r.status_code == 409

    def test_create_uf_invalida(self):
        """Factory terreno valida UF do endereco contra a tabela IBGE."""
        t = login_admin(); h = hdr(t)
        bad = dict(IM_CREATE, matricula="MAT-BAD", endereco_uf="XX")
        r = client.post("/api/im", json=bad, headers=h)
        assert r.status_code == 400

    def test_get_404(self):
        assert client.get("/api/im/MAT-NAO-EXISTE").status_code == 404

    def test_list_contem_imovel(self):
        _criar_im()
        r = client.get("/api/im")
        assert r.status_code == 200
        assert any(i.get("matricula") == "MAT-TEST-001" for i in r.json()["data"])

    def test_estado_endpoint(self):
        _criar_im()
        r = client.get("/api/im/MAT-TEST-001/estado")
        assert r.status_code == 200
        estado = r.json()["data"]
        assert estado["area_terreno_m2"] == 500.0

    def test_evento_construcao_ok(self):
        """Rota especializada /event/construcao (usada pelo admin)."""
        _criar_im()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/im/MAT-TEST-001/event/construcao", json={
            "matricula": "MAT-TEST-001", "descricao": "Casa",
            "area_construida_m2": 150.0, "data_inicio": "01/03/2024",
        }, headers=h)
        assert r.status_code == 201
        # Rota especializada retorna bloco_index/hash (sem campo assinado)
        assert "bloco_index" in r.json()["data"]
        estado = client.get("/api/im/MAT-TEST-001/estado").json()["data"]
        assert estado["area_construida_m2"] == 150.0
        assert estado["situacao"] == "CONSTRUIDO"

    def test_evento_generico_compra_venda(self):
        """Rota generica /event com payload no contrato do dominio."""
        _criar_im()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/im/MAT-TEST-001/event", json={
            "event_type": "COMPRA_VENDA",
            "payload": {"matricula": "MAT-TEST-001",
                        "comprador": {"cpf": "12345678909", "nome": "João"},
                        "vendedor": {"cpf": "98765432100", "nome": "Maria"},
                        "valor_transacao": 350000.0, "data_transacao": "01/06/2024"},
        }, headers=h)
        assert r.status_code == 201
        estado = client.get("/api/im/MAT-TEST-001/estado").json()["data"]
        assert any(p["cpf"] == "12345678909" for p in estado["proprietarios"])

    def test_evento_generico_payload_invalido(self):
        """M9/M10: payload sem campos obrigatorios do contrato retorna 400."""
        _criar_im()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/im/MAT-TEST-001/event", json={
            "event_type": "COMPRA_VENDA",
            "payload": {"matricula": "MAT-TEST-001", "valor_transacao": 100.0},
        }, headers=h)
        assert r.status_code == 400

    def test_evento_generico_tipo_invalido(self):
        _criar_im()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/im/MAT-TEST-001/event", json={
            "event_type": "VENDA_DE_ALMA", "payload": {},
        }, headers=h)
        assert r.status_code == 400

    def test_evento_no_auth(self):
        _criar_im()
        r = client.post("/api/im/MAT-TEST-001/event/construcao", json={
            "matricula": "MAT-TEST-001", "descricao": "Casa",
            "area_construida_m2": 50.0,
        })
        assert r.status_code == 401

    def test_timeline_e_validate(self):
        _criar_im()
        t = login_admin(); h = hdr(t)
        client.post("/api/im/MAT-TEST-001/event/construcao", json={
            "matricula": "MAT-TEST-001", "descricao": "Casa",
            "area_construida_m2": 150.0,
        }, headers=h)
        tl = client.get("/api/im/MAT-TEST-001/timeline")
        assert tl.status_code == 200 and len(tl.json()["data"]) == 2
        v = client.get("/api/im/MAT-TEST-001/validate?require_signatures=true")
        assert v.status_code == 200 and v.json()["data"]["valida"]

    def test_financeiro_e_pessoas(self):
        _criar_im()
        assert client.get("/api/im/MAT-TEST-001/financeiro").status_code == 200
        r = client.get("/api/im/MAT-TEST-001/pessoas")
        assert r.status_code == 200

    def test_delete_admin(self):
        _criar_im()
        r = client.delete("/api/im/MAT-TEST-001", headers=hdr(login_admin()))
        assert r.status_code == 200
        assert client.get("/api/im/MAT-TEST-001").status_code == 404

    def test_delete_no_auth(self):
        _criar_im()
        assert client.delete("/api/im/MAT-TEST-001").status_code == 401


# ══════════════════════════════════════════════════════════════════════
#  DOMÍNIOS: CO (Empresas) — Fase 5.6
# ══════════════════════════════════════════════════════════════════════

CO_CREATE = {
    "cnpj": "12345678000195", "razao_social": "TechSolutions LTDA",
    "nome_fantasia": "TechSol", "data_constituicao": "01/01/2024",
    "tipo_empresa": "LTDA", "porte": "ME", "capital_social": 50000.0,
    "natureza_juridica": "2062", "atividade_principal": "6201501",
    "uf": "SP", "cidade": "Sao Paulo",
}


def _criar_co():
    t = login_admin(); h = hdr(t)
    r = client.post("/api/co", json=CO_CREATE, headers=h)
    assert r.status_code == 201, r.json()
    return t, h


class TestApiEmpresas:
    def test_create_ok(self):
        _criar_co()
        r = client.get("/api/co/12345678000195")
        assert r.status_code == 200
        assert r.json()["data"]["estado"]["razao_social"] == "TechSolutions LTDA"

    def test_create_no_auth(self):
        assert client.post("/api/co", json=CO_CREATE).status_code == 401

    def test_create_readonly_fails(self):
        t = login_readonly()
        r = client.post("/api/co", json=CO_CREATE, headers=hdr(t))
        assert r.status_code == 403

    def test_create_duplicado(self):
        _criar_co()
        t = login_admin()
        r = client.post("/api/co", json=CO_CREATE, headers=hdr(t))
        assert r.status_code == 409

    def test_create_cnpj_invalido(self):
        """H7: CNPJ com digito verificador errado e rejeitado."""
        t = login_admin(); h = hdr(t)
        bad = dict(CO_CREATE, cnpj="12345678000100")
        r = client.post("/api/co", json=bad, headers=h)
        assert r.status_code == 400

    def test_get_404(self):
        assert client.get("/api/co/00000000000000").status_code == 404

    def test_list_contem_empresa(self):
        _criar_co()
        r = client.get("/api/co")
        assert r.status_code == 200
        assert any(e.get("cnpj") == "12345678000195" for e in r.json()["data"])

    def test_evento_adicao_socio(self):
        _criar_co()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/co/12345678000195/event", json={
            "event_type": "ADICAO_SOCIO",
            "payload": {"socio": {"cpf": "98765432100", "nome": "Maria Santos"},
                        "participacao": 30.0, "data_entrada": "15/06/2024"},
        }, headers=h)
        assert r.status_code == 201
        estado = client.get("/api/co/12345678000195").json()["data"]["estado"]
        assert any(s["cpf"] == "98765432100" for s in estado["socios"])

    def test_evento_mudanca_capital(self):
        _criar_co()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/co/12345678000195/event", json={
            "event_type": "MUDANCA_CAPITAL",
            "payload": {"capital_anterior": 50000.0, "capital_novo": 100000.0,
                        "data_mudanca": "01/07/2024"},
        }, headers=h)
        assert r.status_code == 201
        estado = client.get("/api/co/12345678000195").json()["data"]["estado"]
        assert estado["capital_social"] == 100000.0

    def test_evento_payload_invalido(self):
        """M9/M10: ADICAO_SOCIO sem socio/participacao retorna 400."""
        _criar_co()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/co/12345678000195/event", json={
            "event_type": "ADICAO_SOCIO", "payload": {"data_entrada": "15/06/2024"},
        }, headers=h)
        assert r.status_code == 400

    def test_evento_tipo_invalido(self):
        _criar_co()
        t = login_admin(); h = hdr(t)
        r = client.post("/api/co/12345678000195/event", json={
            "event_type": "FESTA_NA_SEDE", "payload": {},
        }, headers=h)
        assert r.status_code == 400

    def test_evento_no_auth(self):
        _criar_co()
        r = client.post("/api/co/12345678000195/event", json={
            "event_type": "MUDANCA_CAPITAL", "payload": {"capital_novo": 1.0},
        })
        assert r.status_code == 401

    def test_timeline_e_validate(self):
        _criar_co()
        t = login_admin(); h = hdr(t)
        client.post("/api/co/12345678000195/event", json={
            "event_type": "MUDANCA_CAPITAL",
            "payload": {"capital_anterior": 50000.0, "capital_novo": 100000.0,
                        "data_mudanca": "01/07/2024"},
        }, headers=h)
        tl = client.get("/api/co/12345678000195/timeline")
        assert tl.status_code == 200 and len(tl.json()["data"]) == 2
        v = client.get("/api/co/12345678000195/validate?require_signatures=true")
        assert v.status_code == 200 and v.json()["data"]["valida"]

    def test_delete_admin(self):
        _criar_co()
        r = client.delete("/api/co/12345678000195", headers=hdr(login_admin()))
        assert r.status_code == 200
        assert client.get("/api/co/12345678000195").status_code == 404

    def test_delete_no_auth(self):
        _criar_co()
        assert client.delete("/api/co/12345678000195").status_code == 401
