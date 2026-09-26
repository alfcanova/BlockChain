"""Testes do F7 — Rebuild do grafo de relacionamentos a partir das cadeias PF.

- POST /api/pf/graph/rebuild (admin only) reconstrói o grafo
- NASCIMENTO cria no + arestas MAE/PAI
- CASAMENTO cria aresta CONJUGE; DIVORCIO desativa e cria EX_CONJUGE
- OBITO marca o no como falecido
- Round-trip: grafo zerado → rebuild reproduz o estado
"""
import pytest
from fastapi.testclient import TestClient

import web_app
from web_app import app, chains, pf_graph
from blockchain_pf.auth import init_default_users
from blockchain_pf.graph import RelationType

client = TestClient(app)


def login_admin():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _ambiente_f7():
    """Seeds + isolamento dos dicts globais e do grafo."""
    init_default_users()
    salvo = {
        "chains": dict(chains),
        "grafo_nos": dict(pf_graph.nodes),
        "grafo_arestas": list(pf_graph.edges),
        "grafo_idx": {k: list(v) for k, v in pf_graph._edge_index.items()},
    }
    chains.clear()
    pf_graph.nodes.clear()
    pf_graph.edges.clear()
    pf_graph._edge_index.clear()
    yield
    chains.clear(); chains.update(salvo["chains"])
    pf_graph.nodes.clear(); pf_graph.nodes.update(salvo["grafo_nos"])
    pf_graph.edges[:] = salvo["grafo_arestas"]
    pf_graph._edge_index.clear()
    for k, v in salvo["grafo_idx"].items():
        pf_graph._edge_index[k] = list(v)


def _cadeia_com_nascimento(cpf, nome, cpf_mae="", nome_mae="", cpf_pai="", nome_pai=""):
    """Cria cadeia PF via API (rota /api/chain + evento NASCIMENTO)."""
    t = login_admin()
    r = client.post(f"/api/chain?cpf={cpf}", json={"difficulty": 1}, headers=hdr(t))
    assert r.status_code == 201, r.text
    payload = {
        "cpf": cpf, "nome_completo": nome,
        "data_nascimento": "15/03/2000", "sexo": "F",
        "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
    }
    if nome_mae:
        payload["nome_mae"] = nome_mae
    if cpf_mae:
        payload["cpf_mae"] = cpf_mae
    if nome_pai:
        payload["nome_pai"] = nome_pai
    if cpf_pai:
        payload["cpf_pai"] = cpf_pai
    r = client.post(f"/api/chain/{cpf}/event",
                    json={"event_type": "NASCIMENTO", "payload": payload},
                    headers=hdr(t))
    assert r.status_code == 201, r.text
    return t


class TestF7RebuildGraph:
    def test_rebuild_somente_admin(self):
        t = login_admin()
        client.post("/api/auth/users", json={"username": "f7_user",
                                             "password": "Senha#F0rte", "role": "user"},
                    headers=hdr(t))
        t2 = client.post("/api/auth/login",
                         json={"username": "f7_user", "password": "Senha#F0rte"}
                         ).json()["data"]["token"]
        assert client.post("/api/pf/graph/rebuild", headers=hdr(t2)).status_code == 403
        assert client.post("/api/pf/graph/rebuild", headers=hdr(t)).status_code == 200

    def test_rebuild_cria_nos_e_arestas_de_parentesco(self):
        t = _cadeia_com_nascimento("12345678909", "Maria F7",
                                   cpf_mae="98765432100", nome_mae="Ana Mae F7")
        # Nao criar no manualmente: o rebuild deve reconstituir
        r = client.post("/api/pf/graph/rebuild", headers=hdr(t))
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["cadeias_varridas"] == 1
        assert data["eventos_aplicados"] >= 1
        assert "12345678909" in pf_graph.nodes
        assert "98765432100" in pf_graph.nodes
        arestas_mae = [e for e in pf_graph.edges
                       if e.tipo == RelationType.MAE
                       and e.from_cpf == "98765432100"
                       and e.to_cpf == "12345678909"]
        assert len(arestas_mae) == 1

    def test_rebuild_casamento_divorcio_obito(self):
        t = _cadeia_com_nascimento("11122233396", "Pessoa A F7")
        # Segunda PF
        r = client.post("/api/chain?cpf=15350946056", json={"difficulty": 1}, headers=hdr(t))
        assert r.status_code == 201
        r = client.post("/api/chain/15350946056/event", json={
            "event_type": "NASCIMENTO",
            "payload": {"cpf": "15350946056", "nome_completo": "Pessoa B F7",
                        "data_nascimento": "10/07/1998", "sexo": "M",
                        "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP"}},
            headers=hdr(t))
        assert r.status_code == 201
        # Casamento da A com B
        r = client.post("/api/chain/11122233396/event", json={
            "event_type": "CASAMENTO",
            "payload": {"cpf": "11122233396", "cpf_conjuge": "15350946056",
                        "nome_conjuge": "Pessoa B F7",
                        "regime_bens": "COMUNHAO_PARCIAL", "data_casamento": "01/02/2020"}},
            headers=hdr(t))
        assert r.status_code == 201, r.text
        # Divorcio
        r = client.post("/api/chain/11122233396/event", json={
            "event_type": "DIVORCIO",
            "payload": {"cpf": "11122233396", "tipo": "CONSENSUAL",
                        "data_divorcio": "01/03/2022"}},
            headers=hdr(t))
        assert r.status_code == 201, r.text
        # Obito da B
        r = client.post("/api/chain/15350946056/event", json={
            "event_type": "OBITO",
            "payload": {"cpf": "15350946056", "data_obito": "01/05/2025",
                        "local_obito": "Sao Paulo"}},
            headers=hdr(t))
        assert r.status_code == 201, r.text

        # Zera o grafo e reconstrói
        pf_graph.nodes.clear()
        pf_graph.edges.clear()
        pf_graph._edge_index.clear()
        r = client.post("/api/pf/graph/rebuild", headers=hdr(t))
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["eventos_aplicados"] >= 4

        # Nos recriados
        assert "11122233396" in pf_graph.nodes
        assert "15350946056" in pf_graph.nodes

        # Ex-conjuge (CONJUGE desativada + EX_CONJUGE ativa)
        ex = [e for e in pf_graph.edges if e.tipo == RelationType.EX_CONJUGE]
        assert len(ex) == 1
        conj_ativas = [e for e in pf_graph.edges
                       if e.tipo == RelationType.CONJUGE and e.ativo]
        assert conj_ativas == []

        # Falecido
        assert pf_graph.nodes["15350946056"].ativo is False

    def test_rebuild_persiste_no_db(self):
        t = _cadeia_com_nascimento("39053344705", "Persistida F7")
        pf_graph.nodes.clear()
        pf_graph.edges.clear()
        pf_graph._edge_index.clear()
        r = client.post("/api/pf/graph/rebuild", headers=hdr(t))
        assert r.status_code == 200
        # No gravado no SQLite (leitura direta da tabela graph_nodes)
        conn = web_app.db._get_conn()
        row = conn.execute(
            "SELECT nome FROM graph_nodes WHERE cpf = ?", ("39053344705",)
        ).fetchone()
        assert row is not None and row["nome"] == "Persistida F7"

    def test_rebuild_sem_cadeias_zera_grafo(self):
        t = login_admin()
        pf_graph.add_node("12345678909", "Orfano")
        r = client.post("/api/pf/graph/rebuild", headers=hdr(t))
        assert r.status_code == 200
        assert len(pf_graph.nodes) == 0
        assert len(pf_graph.edges) == 0
