"""Testes do F6 — Integridade cross-chain.

- Delete de entidade desativa vinculos ativos que a envolvem
- GET /api/cross/orfaos lista vinculos ativos apontando para entidades
  inexistentes (visibilidade)
"""
import pytest
from fastapi.testclient import TestClient

import web_app
from web_app import (app, chains, im_chains, mo_chains,
                     cross_mo, _desativa_vinculos_da_entidade)
from blockchain_pf.auth import init_default_users

client = TestClient(app)


def login_admin():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["data"]["token"]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _ambiente_f6(monkeypatch):
    """Seeds + isolamento: salva e restaura dicts/managers globais."""
    init_default_users()
    salvo = {
        "chains": dict(chains), "mo": dict(mo_chains), "im": dict(im_chains),
        "mo_refs": list(cross_mo._references),
    }
    mo_chains.clear()
    im_chains.clear()
    chains.clear()
    cross_mo._references.clear()
    yield
    chains.clear(); chains.update(salvo["chains"])
    mo_chains.clear(); mo_chains.update(salvo["mo"])
    im_chains.clear(); im_chains.update(salvo["im"])
    cross_mo._references[:] = salvo["mo_refs"]


# ── Helper puro ──────────────────────────────────────────────────────

class TestDesativaVinculos:
    def test_desativa_vinculo_mo_envolvendo_placa(self):
        from blockchain_mo.cross_chain import VehicleCrossReference
        cross_mo._references.append(VehicleCrossReference(
            entidade_origem_tipo="PF", entidade_origem_id="11122233396",
            entidade_destino_tipo="MO", entidade_destino_id="ABC1D23",
            tipo_vinculo="PROPRIETARIO", ativo=True))
        n = _desativa_vinculos_da_entidade("mo", "ABC1D23")
        assert n == 1
        assert cross_mo._references[0].ativo is False

    def test_desativa_vinculo_mo_como_origem(self):
        from blockchain_mo.cross_chain import VehicleCrossReference
        cross_mo._references.append(VehicleCrossReference(
            entidade_origem_tipo="MO", entidade_origem_id="ABC1D23",
            entidade_destino_tipo="PF", entidade_destino_id="11122233396",
            tipo_vinculo="PROPRIETARIO", ativo=True))
        n = _desativa_vinculos_da_entidade("mo", "ABC1D23")
        assert n == 1
        assert cross_mo._references[0].ativo is False

    def test_nao_desativa_vinculo_de_outra_entidade(self):
        from blockchain_mo.cross_chain import VehicleCrossReference
        cross_mo._references.append(VehicleCrossReference(
            entidade_origem_tipo="PF", entidade_origem_id="11122233396",
            entidade_destino_tipo="MO", entidade_destino_id="XYZ9W88",
            tipo_vinculo="PROPRIETARIO", ativo=True))
        n = _desativa_vinculos_da_entidade("mo", "ABC1D23")
        assert n == 0
        assert cross_mo._references[0].ativo is True

    def test_vinculo_ja_inativo_ignorado(self):
        from blockchain_mo.cross_chain import VehicleCrossReference
        cross_mo._references.append(VehicleCrossReference(
            entidade_origem_tipo="PF", entidade_origem_id="11122233396",
            entidade_destino_tipo="MO", entidade_destino_id="ABC1D23",
            tipo_vinculo="PROPRIETARIO", ativo=False))
        assert _desativa_vinculos_da_entidade("mo", "ABC1D23") == 0

    def test_case_insensitive_no_tipo(self):
        from blockchain_mo.cross_chain import VehicleCrossReference
        cross_mo._references.append(VehicleCrossReference(
            entidade_origem_tipo="pf", entidade_origem_id="11122233396",
            entidade_destino_tipo="mo", entidade_destino_id="ABC1D23",
            tipo_vinculo="PROPRIETARIO", ativo=True))
        assert _desativa_vinculos_da_entidade("mo", "ABC1D23") == 1


# ── Integracao via API ───────────────────────────────────────────────

class TestDeleteDesativaVinculos:
    def test_delete_veiculo_desativa_vinculos(self):
        t = login_admin()
        # veiculo
        r = client.post("/api/mo", json={
            "placa": "BRA2E19", "renavan": "00987654321",
            "chassis": "9BWZZZ377VT004251", "marca": "VW", "modelo": "Gol",
            "ano_fabricacao": 2020, "ano_modelo": 2021, "cor": "PRATA",
            "combustivel": "FLEX", "uf": "SP", "cidade": "Sao Paulo",
            "cilindradas": 1000, "potencia_cv": 80,
        }, headers=hdr(t))
        assert r.status_code == 201, r.text
        # PF de origem do vinculo
        r = client.post("/api/chain?cpf=11122233396", json={"difficulty": 1}, headers=hdr(t))
        assert r.status_code == 201, r.text
        # vinculo PF→MO
        r = client.post("/api/cross/vinculo", json={
            "origem_tipo": "PF", "origem_id": "11122233396",
            "destino_tipo": "MO", "destino_id": "BRA2E19",
            "tipo_vinculo": "PROPRIETARIO",
        }, headers=hdr(t))
        assert r.status_code == 201, r.text

        # Delete do veiculo → vinculo deve ser desativado
        r = client.delete("/api/mo/BRA2E19", headers=hdr(t))
        assert r.status_code == 200
        refs = [r for r in cross_mo._references
                if r.entidade_destino_id == "BRA2E19"]
        assert refs and all(not r.ativo for r in refs)

        # Pos-delete: nenhuma referencia ATIVA para o veiculo removido
        r = client.get("/api/cross/orfaos", headers=hdr(t))
        assert r.status_code == 200
        orfaos = r.json()["data"]["orfaos"]
        ativos_mo = [o for o in orfaos
                     if o["tipo"] == "mo" and o["id"] == "BRA2E19"]
        assert ativos_mo == []

        # Limpeza
        client.delete("/api/chain/11122233396", headers=hdr(t))

    def test_orfaos_endpoint_somente_admin(self):
        init_default_users()
        t = login_admin()
        client.post("/api/auth/users", json={"username": "f6_user",
                                             "password": "Senha#F0rte", "role": "user"},
                    headers=hdr(t))
        r = client.post("/api/auth/login", json={"username": "f6_user", "password": "Senha#F0rte"})
        t2 = r.json()["data"]["token"]
        assert client.get("/api/cross/orfaos", headers=hdr(t2)).status_code == 403
        assert client.get("/api/cross/orfaos", headers=hdr(t)).status_code == 200
