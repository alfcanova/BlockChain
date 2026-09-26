"""Testes do F12 — Backup/restore (bundle JSON).

- GET /api/admin/backup exporta cadeias + grafo + cross-references
- POST /api/admin/restore importa o bundle (upsert por id)
- Round-trip: backup → delete → restore recria as cadeias
"""
import pytest
from fastapi.testclient import TestClient

import web_app
from web_app import app, chains, mo_chains, im_chains, co_chains, em_chains, ac_chains, an_chains, au_chains
from blockchain_pf.auth import init_default_users

client = TestClient(app)


def login_admin():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _ambiente_f12():
    """Seeds + isolamento dos dicts globais e do grafo."""
    init_default_users()
    salvo = {
        "chains": dict(chains), "mo": dict(mo_chains), "im": dict(im_chains),
        "co": dict(co_chains), "em": dict(em_chains), "ac": dict(ac_chains),
        "an": dict(an_chains), "au": dict(au_chains),
        "grafo_nos": dict(web_app.pf_graph.nodes),
        "grafo_arestas": list(web_app.pf_graph.edges),
        "mo_refs": list(web_app.cross_mo._references),
    }
    for d in (chains, mo_chains, im_chains, co_chains, em_chains, ac_chains, an_chains, au_chains):
        d.clear()
    web_app.pf_graph.nodes.clear()
    web_app.pf_graph.edges.clear()
    web_app.cross_mo._references.clear()
    yield
    chains.clear(); chains.update(salvo["chains"])
    mo_chains.clear(); mo_chains.update(salvo["mo"])
    im_chains.clear(); im_chains.update(salvo["im"])
    co_chains.clear(); co_chains.update(salvo["co"])
    em_chains.clear(); em_chains.update(salvo["em"])
    ac_chains.clear(); ac_chains.update(salvo["ac"])
    an_chains.clear(); an_chains.update(salvo["an"])
    au_chains.clear(); au_chains.update(salvo["au"])
    web_app.pf_graph.nodes.clear()
    web_app.pf_graph.nodes.update(salvo["grafo_nos"])
    web_app.pf_graph.edges[:] = salvo["grafo_arestas"]
    web_app.cross_mo._references[:] = salvo["mo_refs"]


def cria_veiculo(t, placa="BRA2E19"):
    r = client.post("/api/mo", json={
        "placa": placa, "renavan": "00987654321",
        "chassis": "9BWZZZ377VT004251", "marca": "VW", "modelo": "Gol",
        "ano_fabricacao": 2020, "ano_modelo": 2021, "cor": "PRATA",
        "combustivel": "FLEX", "uf": "SP", "cidade": "Sao Paulo",
        "cilindradas": 1000, "potencia_cv": 80,
    }, headers=hdr(t))
    assert r.status_code == 201, r.text
    return r


class TestF12BackupRestore:
    def test_backup_download_headers(self):
        t = login_admin()
        r = client.get("/api/admin/backup", headers=hdr(t))
        assert r.status_code == 200
        assert "attachment" in r.headers.get("content-disposition", "")
        body = r.json()
        assert body["meta"]["versao"] == 1
        assert "chains" in body and "graph" in body and "cross_references" in body

    def test_backup_somente_admin(self):
        t = login_admin()
        client.post("/api/auth/users", json={"username": "f12_user",
                                             "password": "Senha#F0rte", "role": "user"},
                    headers=hdr(t))
        t2 = client.post("/api/auth/login",
                         json={"username": "f12_user", "password": "Senha#F0rte"}
                         ).json()["data"]["token"]
        assert client.get("/api/admin/backup", headers=hdr(t2)).status_code == 403
        assert client.post("/api/admin/restore", json={}, headers=hdr(t2)).status_code == 403

    def test_bundle_reflete_cadeias(self):
        t = login_admin()
        cria_veiculo(t)
        r = client.get("/api/admin/backup", headers=hdr(t))
        bundle = r.json()
        assert bundle["meta"]["counts"]["mo"] == 1
        placa, data = next(iter(bundle["chains"]["mo"].items()))
        assert data["chain"][0]["data"]["evento_tipo"] == "FABRICACAO"

    def test_restore_bundle_invalido_400(self):
        t = login_admin()
        r = client.post("/api/admin/restore", json={"lixo": True}, headers=hdr(t))
        assert r.status_code == 400

    def test_round_trip_backup_delete_restore(self):
        t = login_admin()
        cria_veiculo(t)

        # 1. backup
        bundle = client.get("/api/admin/backup", headers=hdr(t)).json()
        assert bundle["meta"]["counts"]["mo"] == 1

        # 2. delete da entidade
        r = client.delete("/api/mo/BRA2E19", headers=hdr(t))
        assert r.status_code == 200
        assert "BRA2E19" not in mo_chains

        # 3. restore recria a cadeia em memoria e no DB
        r = client.post("/api/admin/restore", json=bundle, headers=hdr(t))
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["cadeias_restauradas"].get("mo") == 1
        assert "BRA2E19" in mo_chains
        estado = mo_chains["BRA2E19"].get_estado_atual()
        assert estado.get("placa") == "BRA2E19"

    def test_restore_persiste_no_db(self, tmp_path):
        t = login_admin()
        cria_veiculo(t)
        bundle = client.get("/api/admin/backup", headers=hdr(t)).json()
        client.delete("/api/mo/BRA2E19", headers=hdr(t))
        client.post("/api/admin/restore", json=bundle, headers=hdr(t))

        # Simula restart: rebuild direto do snapshot persistido
        salvo = web_app.db.load_domain_chain("mo", "BRA2E19")
        assert salvo and len(salvo["chain"]) >= 1
        chain = web_app._rebuild_chain(web_app.VehicleChain, salvo, "detran",
                                       domain="mo", cid="BRA2E19")
        assert chain.get_estado_atual().get("placa") == "BRA2E19"

    def test_restore_grafo_e_cross_references(self):
        t = login_admin()
        # Popula grafo + referencia MO
        web_app.pf_graph.add_node("11122233396", "Pessoa F12")
        web_app.cross_mo._references.append(
            web_app.VehicleCrossReference(
                entidade_origem_tipo="PF", entidade_origem_id="11122233396",
                entidade_destino_tipo="MO", entidade_destino_id="BRA2E19",
                tipo_vinculo="PROPRIETARIO", ativo=True))
        bundle = client.get("/api/admin/backup", headers=hdr(t)).json()

        # Zera tudo e restaura
        web_app.pf_graph.nodes.clear()
        web_app.pf_graph.edges.clear()
        web_app.cross_mo._references.clear()
        r = client.post("/api/admin/restore", json=bundle, headers=hdr(t))
        assert r.status_code == 200
        assert "11122233396" in web_app.pf_graph.nodes
        assert len(web_app.cross_mo._references) == 1
        assert web_app.cross_mo._references[0].ativo is True
