"""Testes completos para blockchain_mo/cross_chain.py e blockchain_co/cross_chain.py.

Cobre: registro/unregistros, validação, criação/desativação de referências,
consultas cruzadas (pessoa↔veículo, veículo↔imóvel, pessoa↔empresa, etc.),
serialização, stats, repr.
"""
import json
import os
import tempfile
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from blockchain_mo.cross_chain import CrossChainMO, VehicleCrossReference
from blockchain_co.cross_chain import CrossChainCO, CompanyCrossReference


# ══════════════════════════════════════════════════════════════════════
#  MOCK CHAINS
# ══════════════════════════════════════════════════════════════════════

def _make_mock_chain(birth_data=None, estado=None, last_hash="abc123"):
    """Cria uma mock chain com a interface esperada pelos cross-chains."""
    chain = MagicMock()

    if birth_data is None:
        birth_data = {}
    birth_block = MagicMock()
    birth_block.data = {"payload": birth_data}
    chain.get_birth_block.return_value = birth_block

    if estado is None:
        estado = {}
    chain.get_estado_atual.return_value = estado

    last_block = MagicMock()
    last_block.hash = last_hash
    chain.chain = [last_block]

    return chain


def _pf_chain(nome="Joao Silva", cpf="11122233344"):
    return _make_mock_chain(birth_data={"nome_completo": nome, "cpf": cpf})


def _im_chain(logradouro="Rua A, 123"):
    return _make_mock_chain(estado={"endereco": {"logradouro": logradouro}, "situacao": "regular"})


def _mo_chain(marca="Fiat", modelo="Argo", cor="Prata", situacao="regular"):
    return _make_mock_chain(estado={"marca": marca, "modelo": modelo, "cor": cor, "situacao": situacao})


def _co_chain(razao_social="Empresa X LTDA", situacao="ATIVA"):
    return _make_mock_chain(estado={"razao_social": razao_social, "situacao_cadastral": situacao})


# ══════════════════════════════════════════════════════════════════════
#  CrossChainMO
# ══════════════════════════════════════════════════════════════════════

class TestCrossChainMO:
    @pytest.fixture
    def mgr(self):
        return CrossChainMO()

    @pytest.fixture
    def mgr_populated(self):
        m = CrossChainMO()
        m.register_pf("11122233344", _pf_chain("Joao", "11122233344"))
        m.register_pf("55566677788", _pf_chain("Maria", "55566677788"))
        m.register_im("MAT-001", _im_chain("Rua A"))
        m.register_mo("ABC1D23", _mo_chain("Fiat", "Argo", "Prata"))
        m.register_mo("DEF4E56", _mo_chain("VW", "Gol", "Preto"))
        return m

    # ── Registro / Unregister ────────────────────────────────────────

    def test_register_pf(self, mgr):
        mgr.register_pf("11122233344", _pf_chain())
        assert "11122233344" in mgr._pf_chains

    def test_register_pf_normaliza(self, mgr):
        mgr.register_pf("111.222.333-44", _pf_chain())
        assert "11122233344" in mgr._pf_chains

    def test_register_im(self, mgr):
        mgr.register_im("MAT-001", _im_chain())
        assert "MAT-001" in mgr._im_chains

    def test_register_mo(self, mgr):
        mgr.register_mo("abc-1d23", _mo_chain())
        assert "ABC1D23" in mgr._mo_chains

    def test_unregister_pf(self, mgr):
        mgr.register_pf("111", _pf_chain())
        assert mgr.unregister_pf("111")
        assert "111" not in mgr._pf_chains

    def test_unregister_pf_not_found(self, mgr):
        assert not mgr.unregister_pf("999")

    def test_unregister_im(self, mgr):
        mgr.register_im("M1", _im_chain())
        assert mgr.unregister_im("M1")

    def test_unregister_im_not_found(self, mgr):
        assert not mgr.unregister_im("M9")

    def test_unregister_mo(self, mgr):
        mgr.register_mo("ABC1D23", _mo_chain())
        assert mgr.unregister_mo("ABC1D23")

    def test_unregister_mo_not_found(self, mgr):
        assert not mgr.unregister_mo("XYZ9999")

    # ── Validação ───────────────────────────────────────────────────

    def test_validate_pf_exists(self, mgr_populated):
        ok, msg = mgr_populated.validate_pf_exists("11122233344")
        assert ok
        assert "Joao" in msg

    def test_validate_pf_not_exists(self, mgr):
        ok, msg = mgr.validate_pf_exists("00000000000")
        assert not ok

    def test_validate_im_exists(self, mgr_populated):
        ok, msg = mgr_populated.validate_im_exists("MAT-001")
        assert ok
        assert "Rua A" in msg

    def test_validate_im_not_exists(self, mgr):
        ok, msg = mgr.validate_im_exists("MAT-999")
        assert not ok

    def test_validate_mo_exists(self, mgr_populated):
        ok, msg = mgr_populated.validate_mo_exists("ABC1D23")
        assert ok
        assert "Fiat" in msg

    def test_validate_mo_not_exists(self, mgr):
        ok, msg = mgr.validate_mo_exists("XYZ9999")
        assert not ok

    def test_validate_cross_reference_ok(self, mgr_populated):
        ok, msg = mgr_populated.validate_cross_reference("PF", "11122233344", "MO", "ABC1D23")
        assert ok

    def test_validate_cross_reference_tipo_invalido(self, mgr):
        ok, msg = mgr.validate_cross_reference("XX", "1", "MO", "ABC1D23")
        assert not ok
        assert "inválido" in msg

    def test_validate_cross_reference_origem_falha(self, mgr_populated):
        ok, msg = mgr_populated.validate_cross_reference("PF", "00000000000", "MO", "ABC1D23")
        assert not ok

    def test_validate_cross_reference_destino_falha(self, mgr_populated):
        ok, msg = mgr_populated.validate_cross_reference("PF", "11122233344", "MO", "ZZZ")
        assert not ok

    # ── Criação de referências ──────────────────────────────────────

    def test_create_reference_pf_mo(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "PF", "11122233344", "MO", "ABC1D23", "PROPRIETARIO",
            bloco_origem=1, bloco_destino=2, dados={"valor": 50000},
        )
        assert ref.entidade_origem_tipo == "PF"
        assert ref.entidade_origem_id == "11122233344"
        assert ref.entidade_destino_tipo == "MO"
        assert ref.entidade_destino_id == "ABC1D23"
        assert ref.tipo_vinculo == "PROPRIETARIO"
        assert ref.bloco_origem == 1
        assert ref.bloco_destino == 2
        assert ref.dados["valor"] == 50000
        assert ref.ativo is True
        assert ref.hash_cadeia_origem == "abc123"

    def test_create_reference_mo_pf(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "MO", "DEF4E56", "PF", "55566677788", "GARANTIDOR",
        )
        assert ref.entidade_origem_tipo == "MO"
        assert ref.entidade_origem_id == "DEF4E56"

    def test_create_reference_im_mo(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "IM", "MAT-001", "MO", "ABC1D23", "GARAGEM",
        )
        assert ref.entidade_origem_tipo == "IM"

    def test_create_reference_mo_mo(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "MO", "ABC1D23", "MO", "DEF4E56", "PECA_ORIGEM",
            dados={"peca": "motor"},
        )
        assert ref.entidade_origem_tipo == "MO"
        assert ref.entidade_destino_tipo == "MO"
        assert ref.dados["peca"] == "motor"

    def test_create_reference_normaliza_pf(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "PF", "111.222.333-44", "MO", "ABC1D23", "PROPRIETARIO",
        )
        assert ref.entidade_origem_id == "11122233344"

    def test_create_reference_normaliza_mo(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "PF", "11122233344", "MO", "abc-1d23", "PROPRIETARIO",
        )
        assert ref.entidade_destino_id == "ABC1D23"

    def test_create_reference_hash_not_registered(self, mgr):
        """Hash retorna '' quando entidade não está registrada."""
        ref = mgr.create_reference(
            "PF", "000", "MO", "ZZZ", "TESTE",
        )
        assert ref.hash_cadeia_origem == ""
        assert ref.hash_cadeia_destino == ""

    # ── Desativação ────────────────────────────────────────────────

    def test_deactivate_reference(self, mgr_populated):
        mgr_populated.create_reference("PF", "11122233344", "MO", "ABC1D23", "PROPRIETARIO")
        count = mgr_populated.deactivate_reference("PF", "11122233344", "MO", "ABC1D23")
        assert count == 1
        assert not mgr_populated._references[0].ativo

    def test_deactivate_com_filtro_tipo(self, mgr_populated):
        mgr_populated.create_reference("PF", "11122233344", "MO", "ABC1D23", "PROPRIETARIO")
        mgr_populated.create_reference("PF", "11122233344", "MO", "ABC1D23", "GARANTIDOR")
        count = mgr_populated.deactivate_reference(
            "PF", "11122233344", "MO", "ABC1D23", "PROPRIETARIO",
        )
        assert count == 1
        assert mgr_populated._references[0].ativo is False
        assert mgr_populated._references[1].ativo is True

    def test_deactivate_normaliza_pf(self, mgr_populated):
        mgr_populated.create_reference("PF", "11122233344", "MO", "ABC1D23", "PROPRIETARIO")
        count = mgr_populated.deactivate_reference("PF", "111.222.333-44", "MO", "ABC1D23")
        assert count == 1

    def test_deactivate_normaliza_mo(self, mgr_populated):
        mgr_populated.create_reference("PF", "11122233344", "MO", "ABC1D23", "PROPRIETARIO")
        count = mgr_populated.deactivate_reference("PF", "11122233344", "MO", "abc-1d23")
        assert count == 1

    def test_deactivate_nao_encontrado(self, mgr):
        assert mgr.deactivate_reference("PF", "000", "MO", "ZZZ") == 0

    def test_deactivate_inativo(self, mgr_populated):
        ref = mgr_populated.create_reference("PF", "11122233344", "MO", "ABC1D23", "X")
        ref.ativo = False
        assert mgr_populated.deactivate_reference("PF", "11122233344", "MO", "ABC1D23") == 0

    # ── Consultas ───────────────────────────────────────────────────

    def test_get_veiculos_da_pessoa_direto(self, mgr_populated):
        mgr_populated.create_reference("PF", "11122233344", "MO", "ABC1D23", "PROPRIETARIO")
        result = mgr_populated.get_veiculos_da_pessoa("11122233344")
        assert len(result) == 1
        assert result[0]["placa"] == "ABC1D23"
        assert result[0]["marca"] == "Fiat"
        assert result[0]["modelo"] == "Argo"

    def test_get_veiculos_da_pessoa_inverso(self, mgr_populated):
        mgr_populated.create_reference("MO", "ABC1D23", "PF", "11122233344", "PROPRIETARIO")
        result = mgr_populated.get_veiculos_da_pessoa("11122233344")
        assert len(result) == 1
        assert result[0]["placa"] == "ABC1D23"

    def test_get_veiculos_da_pessoa_inativo(self, mgr_populated):
        ref = mgr_populated.create_reference("PF", "11122233344", "MO", "ABC1D23", "X")
        ref.ativo = False
        assert mgr_populated.get_veiculos_da_pessoa("11122233344") == []

    def test_get_veiculos_da_pessoa_sem_chain(self, mgr):
        """Veículo não registrado retorna info sem enriquecimento."""
        mgr.create_reference("PF", "111", "MO", "ZZZ", "TESTE")
        result = mgr.get_veiculos_da_pessoa("111")
        assert len(result) == 1
        assert result[0]["placa"] == "ZZZ"
        assert "marca" not in result[0]

    def test_get_pessoas_do_veiculo_direto(self, mgr_populated):
        mgr_populated.create_reference("PF", "11122233344", "MO", "ABC1D23", "PROPRIETARIO")
        result = mgr_populated.get_pessoas_do_veiculo("ABC1D23")
        assert len(result) == 1
        assert result[0]["cpf"] == "11122233344"
        assert result[0]["nome"] == "Joao"

    def test_get_pessoas_do_veiculo_inverso(self, mgr_populated):
        mgr_populated.create_reference("MO", "ABC1D23", "PF", "11122233344", "PROPRIETARIO")
        result = mgr_populated.get_pessoas_do_veiculo("ABC1D23")
        assert len(result) == 1
        assert result[0]["cpf"] == "11122233344"
        assert result[0]["nome"] == "Joao"

    def test_get_pessoas_do_veiculo_inativo(self, mgr_populated):
        ref = mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        ref.ativo = False
        assert mgr_populated.get_pessoas_do_veiculo("ABC") == []

    def test_get_veiculos_no_imovel(self, mgr_populated):
        mgr_populated.create_reference("IM", "MAT-001", "MO", "ABC1D23", "GARAGEM")
        result = mgr_populated.get_veiculos_no_imovel("MAT-001")
        assert len(result) == 1
        assert result[0]["placa"] == "ABC1D23"
        assert result[0]["marca"] == "Fiat"

    def test_get_veiculos_no_imovel_inverso(self, mgr_populated):
        mgr_populated.create_reference("MO", "ABC1D23", "IM", "MAT-001", "GARAGEM")
        result = mgr_populated.get_veiculos_no_imovel("MAT-001")
        assert len(result) == 1

    def test_get_veiculos_no_imovel_inativo(self, mgr_populated):
        ref = mgr_populated.create_reference("IM", "MAT-001", "MO", "ABC", "GARAGEM")
        ref.ativo = False
        assert mgr_populated.get_veiculos_no_imovel("MAT-001") == []

    def test_get_veiculos_no_imovel_sem_chain(self, mgr):
        mgr.create_reference("IM", "MAT-001", "MO", "ZZZ", "GARAGEM")
        result = mgr.get_veiculos_no_imovel("MAT-001")
        assert len(result) == 1
        assert "marca" not in result[0]

    def test_get_pecas_de_veiculo(self, mgr_populated):
        mgr_populated.create_reference(
            "MO", "ABC1D23", "MO", "DEF4E56", "PECA_ORIGEM",
            dados={"peca": "motor", "km": 50000},
        )
        result = mgr_populated.get_pecas_de_veiculo("DEF4E56")
        assert len(result) == 1
        assert result[0]["veiculo_origem"] == "ABC1D23"
        assert result[0]["dados"]["peca"] == "motor"
        assert result[0]["marca_origem"] == "Fiat"

    def test_get_pecas_de_veiculo_inativo(self, mgr_populated):
        ref = mgr_populated.create_reference("MO", "ABC", "MO", "DEF", "PECA_ORIGEM")
        ref.ativo = False
        assert mgr_populated.get_pecas_de_veiculo("DEF") == []

    def test_get_pecas_tipo_diferente(self, mgr_populated):
        """Apenas PECA_ORIGEM retorna peças."""
        mgr_populated.create_reference("MO", "ABC", "MO", "DEF", "OUTRO_TIPO")
        assert mgr_populated.get_pecas_de_veiculo("DEF") == []

    # ── Vinculos ativos (filtros) ──────────────────────────────────

    def test_get_vinculos_ativos_todos(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        mgr_populated.create_reference("PF", "555", "MO", "DEF", "Y")
        assert len(mgr_populated.get_vinculos_ativos()) == 2

    def test_get_vinculos_ativos_filtro_origem_tipo(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        mgr_populated.create_reference("IM", "M1", "MO", "DEF", "Y")
        result = mgr_populated.get_vinculos_ativos(origem_tipo="PF")
        assert len(result) == 1

    def test_get_vinculos_ativos_filtro_origem_id(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        mgr_populated.create_reference("PF", "555", "MO", "DEF", "Y")
        result = mgr_populated.get_vinculos_ativos(origem_id="111")
        assert len(result) == 1

    def test_get_vinculos_ativos_filtro_destino_tipo(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        mgr_populated.create_reference("PF", "111", "IM", "M1", "Y")
        result = mgr_populated.get_vinculos_ativos(destino_tipo="MO")
        assert len(result) == 1

    def test_get_vinculos_ativos_filtro_destino_id(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        mgr_populated.create_reference("PF", "111", "MO", "DEF", "Y")
        result = mgr_populated.get_vinculos_ativos(destino_id="ABC")
        assert len(result) == 1

    def test_get_vinculos_ativos_filtro_vinculo(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "PROPRIETARIO")
        mgr_populated.create_reference("PF", "111", "MO", "DEF", "GARANTIDOR")
        result = mgr_populated.get_vinculos_ativos(tipo_vinculo="PROPRIETARIO")
        assert len(result) == 1

    def test_get_vinculos_exclui_inativos(self, mgr_populated):
        ref = mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        ref.ativo = False
        assert mgr_populated.get_vinculos_ativos() == []

    # ── Stats ───────────────────────────────────────────────────────

    def test_stats_vazio(self, mgr):
        s = mgr.stats()
        assert s["total_cadeias_pf"] == 0
        assert s["total_cadeias_im"] == 0
        assert s["total_cadeias_mo"] == 0
        assert s["total_referencias"] == 0
        assert s["referencias_ativas"] == 0

    def test_stats_populado(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        s = mgr_populated.stats()
        assert s["total_cadeias_pf"] == 2
        assert s["total_cadeias_im"] == 1
        assert s["total_cadeias_mo"] == 2
        assert s["total_referencias"] == 2
        assert s["referencias_ativas"] == 2
        assert "X" in s["por_tipo_vinculo"]
        assert s["por_tipo_vinculo"]["X"] == 2

    def test_stats_com_inativos(self, mgr_populated):
        ref = mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        ref.ativo = False
        s = mgr_populated.stats()
        assert s["referencias_ativas"] == 0
        assert s["referencias_inativas"] == 1

    # ── Serialização ────────────────────────────────────────────────

    def test_to_dict(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "X")
        d = mgr_populated.to_dict()
        assert "referencias" in d
        assert "stats" in d
        assert len(d["referencias"]) == 1

    def test_save_and_load_file(self, mgr_populated, tmp_path):
        mgr_populated.create_reference("PF", "111", "MO", "ABC", "PROPRIETARIO")
        path = str(tmp_path / "cross_mo.json")
        mgr_populated.save_to_file(path)

        loaded = CrossChainMO.load_from_file(path)
        assert len(loaded._references) == 1
        assert loaded._references[0].entidade_origem_id == "111"
        assert loaded._references[0].entidade_destino_id == "ABC"

    def test_save_to_nested_dir(self, mgr, tmp_path):
        path = str(tmp_path / "sub" / "cross.json")
        mgr.save_to_file(path)
        assert os.path.exists(path)

    # ── Repr ────────────────────────────────────────────────────────

    def test_repr(self, mgr_populated):
        r = repr(mgr_populated)
        assert "CrossChainMO" in r
        assert "pf=2" in r
        assert "mo=2" in r


# ══════════════════════════════════════════════════════════════════════
#  CrossChainCO
# ══════════════════════════════════════════════════════════════════════

class TestCrossChainCO:
    @pytest.fixture
    def mgr(self):
        return CrossChainCO()

    @pytest.fixture
    def mgr_populated(self):
        m = CrossChainCO()
        m.register_pf("11122233344", _pf_chain("Joao", "11122233344"))
        m.register_pf("55566677788", _pf_chain("Maria", "55566677788"))
        m.register_im("MAT-001", _im_chain("Rua A"))
        m.register_mo("ABC1D23", _mo_chain("Fiat", "Argo"))
        m.register_co("12345678000190", _co_chain("Empresa X LTDA", "ATIVA"))
        m.register_co("98765432000110", _co_chain("Empresa Y S/A", "INATIVA"))
        return m

    # ── Registro / Unregister ────────────────────────────────────────

    def test_register_pf(self, mgr):
        mgr.register_pf("11122233344", _pf_chain())
        assert "11122233344" in mgr._pf_chains

    def test_register_im(self, mgr):
        mgr.register_im("MAT-001", _im_chain())
        assert "MAT-001" in mgr._im_chains

    def test_register_mo(self, mgr):
        mgr.register_mo("ABC-1D23", _mo_chain())
        assert "ABC1D23" in mgr._mo_chains

    def test_register_co(self, mgr):
        mgr.register_co("12.345.678/0001-90", _co_chain())
        assert "12345678000190" in mgr._co_chains

    def test_unregister_pf(self, mgr):
        mgr.register_pf("111", _pf_chain())
        assert mgr.unregister_pf("111")

    def test_unregister_pf_not_found(self, mgr):
        assert not mgr.unregister_pf("999")

    def test_unregister_im(self, mgr):
        mgr.register_im("M1", _im_chain())
        assert mgr.unregister_im("M1")

    def test_unregister_im_not_found(self, mgr):
        assert not mgr.unregister_im("M9")

    def test_unregister_mo(self, mgr):
        mgr.register_mo("ABC", _mo_chain())
        assert mgr.unregister_mo("ABC")

    def test_unregister_mo_not_found(self, mgr):
        assert not mgr.unregister_mo("XYZ")

    def test_unregister_co(self, mgr):
        mgr.register_co("12345678000190", _co_chain())
        assert mgr.unregister_co("12345678000190")
        assert "12345678000190" not in mgr._co_chains

    def test_unregister_co_normaliza(self, mgr):
        mgr.register_co("12345678000190", _co_chain())
        assert mgr.unregister_co("12.345.678/0001-90")

    def test_unregister_co_not_found(self, mgr):
        assert not mgr.unregister_co("00000000000000")

    # ── Validação ───────────────────────────────────────────────────

    def test_validate_pf_exists(self, mgr_populated):
        ok, msg = mgr_populated.validate_pf_exists("11122233344")
        assert ok and "Joao" in msg

    def test_validate_pf_not_exists(self, mgr):
        ok, _ = mgr.validate_pf_exists("000")
        assert not ok

    def test_validate_co_exists(self, mgr_populated):
        ok, msg = mgr_populated.validate_co_exists("12345678000190")
        assert ok and "Empresa X" in msg

    def test_validate_co_normaliza(self, mgr_populated):
        ok, _ = mgr_populated.validate_co_exists("12.345.678/0001-90")
        assert ok

    def test_validate_co_not_exists(self, mgr):
        ok, _ = mgr.validate_co_exists("00000000000000")
        assert not ok

    def test_validate_im_exists(self, mgr_populated):
        ok, msg = mgr_populated.validate_im_exists("MAT-001")
        assert ok and "Rua A" in msg

    def test_validate_im_not_exists(self, mgr):
        ok, _ = mgr.validate_im_exists("M9")
        assert not ok

    def test_validate_mo_exists(self, mgr_populated):
        ok, msg = mgr_populated.validate_mo_exists("ABC1D23")
        assert ok and "Fiat" in msg

    def test_validate_mo_not_exists(self, mgr):
        ok, _ = mgr.validate_mo_exists("ZZZ")
        assert not ok

    # ── Criação de referências ──────────────────────────────────────

    def test_create_reference_pf_co(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "PF", "11122233344", "CO", "12345678000190", "SOCIO",
            bloco_origem=1, bloco_destino=2, dados={"participacao": 40},
        )
        assert ref.entidade_origem_tipo == "PF"
        assert ref.entidade_destino_tipo == "CO"
        assert ref.tipo_vinculo == "SOCIO"
        assert ref.dados["participacao"] == 40
        assert ref.hash_cadeia_origem == "abc123"

    def test_create_reference_co_co(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "CO", "12345678000190", "CO", "98765432000110", "CONSÓRCIO",
        )
        assert ref.entidade_origem_tipo == "CO"

    def test_create_reference_co_im(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "CO", "12345678000190", "IM", "MAT-001", "SEDE",
        )
        assert ref.entidade_destino_tipo == "IM"

    def test_create_reference_co_mo(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "CO", "12345678000190", "MO", "ABC1D23", "FROTA",
        )
        assert ref.entidade_destino_tipo == "MO"

    def test_create_reference_normaliza_cnpj_origem(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "CO", "12.345.678/0001-90", "PF", "11122233344", "SOCIO",
        )
        assert ref.entidade_origem_id == "12345678000190"

    def test_create_reference_normaliza_cnpj_destino(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "PF", "11122233344", "CO", "12.345.678/0001-90", "SOCIO",
        )
        assert ref.entidade_destino_id == "12345678000190"

    def test_create_reference_normaliza_pf(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "PF", "111.222.333-44", "CO", "12345678000190", "SOCIO",
        )
        assert ref.entidade_origem_id == "11122233344"

    def test_create_reference_normaliza_mo(self, mgr_populated):
        ref = mgr_populated.create_reference(
            "MO", "abc-1d23", "CO", "12345678000190", "FROTA",
        )
        assert ref.entidade_origem_id == "ABC1D23"

    def test_create_reference_hash_not_registered(self, mgr):
        ref = mgr.create_reference("PF", "000", "CO", "000", "X")
        assert ref.hash_cadeia_origem == ""
        assert ref.hash_cadeia_destino == ""

    # ── Desativação ────────────────────────────────────────────────

    def test_deactivate_reference(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "12345678000190", "SOCIO")
        count = mgr_populated.deactivate_reference("PF", "111", "CO", "12345678000190")
        assert count == 1
        assert not mgr_populated._references[0].ativo

    def test_deactivate_com_filtro_tipo(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "123", "SOCIO")
        mgr_populated.create_reference("PF", "111", "CO", "123", "ADMIN")
        count = mgr_populated.deactivate_reference("PF", "111", "CO", "123", "SOCIO")
        assert count == 1
        assert mgr_populated._references[1].ativo is True

    def test_deactivate_nao_encontrado(self, mgr):
        assert mgr.deactivate_reference("PF", "000", "CO", "000") == 0

    def test_deactivate_inativo(self, mgr_populated):
        ref = mgr_populated.create_reference("PF", "111", "CO", "123", "X")
        ref.ativo = False
        assert mgr_populated.deactivate_reference("PF", "111", "CO", "123") == 0

    # ── Consultas ───────────────────────────────────────────────────

    def test_get_socios_da_empresa(self, mgr_populated):
        mgr_populated.create_reference("PF", "11122233344", "CO", "12345678000190", "SOCIO")
        mgr_populated.create_reference("PF", "55566677788", "CO", "12345678000190", "ADMIN")
        result = mgr_populated.get_socios_da_empresa("12345678000190")
        assert len(result) == 2
        cpfs = {s["cpf"] for s in result}
        assert "11122233344" in cpfs
        assert "55566677788" in cpfs

    def test_get_socios_normaliza_cnpj(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "12345678000190", "SOCIO")
        result = mgr_populated.get_socios_da_empresa("12.345.678/0001-90")
        assert len(result) == 1

    def test_get_socios_sem_chain(self, mgr):
        mgr.create_reference("PF", "111", "CO", "123", "SOCIO")
        result = mgr.get_socios_da_empresa("123")
        assert len(result) == 1
        assert "nome" not in result[0]

    def test_get_empresas_da_pessoa(self, mgr_populated):
        mgr_populated.create_reference("PF", "11122233344", "CO", "12345678000190", "SOCIO")
        mgr_populated.create_reference("PF", "11122233344", "CO", "98765432000110", "ADMIN")
        result = mgr_populated.get_empresas_da_pessoa("11122233344")
        assert len(result) == 2
        cnpjs = {e["cnpj"] for e in result}
        assert "12345678000190" in cnpjs
        assert "98765432000110" in cnpjs

    def test_get_empresas_da_pessoa_normaliza(self, mgr_populated):
        mgr_populated.create_reference("PF", "11122233344", "CO", "12345678000190", "SOCIO")
        result = mgr_populated.get_empresas_da_pessoa("111.222.333-44")
        assert len(result) == 1

    def test_get_empresas_da_pessoa_inativo(self, mgr_populated):
        ref = mgr_populated.create_reference("PF", "111", "CO", "123", "X")
        ref.ativo = False
        assert mgr_populated.get_empresas_da_pessoa("111") == []

    def test_get_empresas_sem_chain(self, mgr):
        mgr.create_reference("PF", "111", "CO", "123", "SOCIO")
        result = mgr.get_empresas_da_pessoa("111")
        assert len(result) == 1
        assert "razao_social" not in result[0]

    # ── Vinculos ativos (filtros) ──────────────────────────────────

    def test_get_vinculos_ativos_todos(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "123", "X")
        mgr_populated.create_reference("PF", "555", "CO", "456", "Y")
        assert len(mgr_populated.get_vinculos_ativos()) == 2

    def test_get_vinculos_filtro_origem_tipo(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "123", "X")
        mgr_populated.create_reference("IM", "M1", "CO", "456", "Y")
        assert len(mgr_populated.get_vinculos_ativos(origem_tipo="PF")) == 1

    def test_get_vinculos_filtro_origem_id(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "123", "X")
        mgr_populated.create_reference("PF", "555", "CO", "456", "Y")
        assert len(mgr_populated.get_vinculos_ativos(origem_id="111")) == 1

    def test_get_vinculos_filtro_destino_tipo(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "123", "X")
        mgr_populated.create_reference("PF", "111", "IM", "M1", "Y")
        assert len(mgr_populated.get_vinculos_ativos(destino_tipo="CO")) == 1

    def test_get_vinculos_filtro_destino_id(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "123", "X")
        mgr_populated.create_reference("PF", "111", "CO", "456", "Y")
        assert len(mgr_populated.get_vinculos_ativos(destino_id="123")) == 1

    def test_get_vinculos_exclui_inativos(self, mgr_populated):
        ref = mgr_populated.create_reference("PF", "111", "CO", "123", "X")
        ref.ativo = False
        assert mgr_populated.get_vinculos_ativos() == []

    # ── Stats ───────────────────────────────────────────────────────

    def test_stats_vazio(self, mgr):
        s = mgr.stats()
        assert s["total_cadeias_pf"] == 0
        assert s["total_cadeias_co"] == 0
        assert s["total_referencias"] == 0

    def test_stats_populado(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "123", "SOCIO")
        ref = mgr_populated.create_reference("PF", "555", "CO", "456", "ADMIN")
        ref.ativo = False
        s = mgr_populated.stats()
        assert s["total_cadeias_pf"] == 2
        assert s["total_cadeias_co"] == 2
        assert s["total_referencias"] == 2
        assert s["referencias_ativas"] == 1
        assert s["referencias_inativas"] == 1

    # ── Serialização ────────────────────────────────────────────────

    def test_to_dict(self, mgr_populated):
        mgr_populated.create_reference("PF", "111", "CO", "123", "SOCIO")
        d = mgr_populated.to_dict()
        assert len(d["referencias"]) == 1
        assert "stats" in d

    def test_save_and_load_file(self, mgr_populated, tmp_path):
        mgr_populated.create_reference("PF", "111", "CO", "123", "SOCIO")
        path = str(tmp_path / "cross_co.json")
        mgr_populated.save_to_file(path)

        loaded = CrossChainCO.load_from_file(path)
        assert len(loaded._references) == 1
        assert loaded._references[0].entidade_origem_id == "111"
        assert loaded._references[0].entidade_destino_id == "123"

    # ── Repr ────────────────────────────────────────────────────────

    def test_repr(self, mgr_populated):
        r = repr(mgr_populated)
        assert "CrossChainCO" in r
        assert "co=2" in r


# ══════════════════════════════════════════════════════════════════════
#  VehicleCrossReference / CompanyCrossReference
# ══════════════════════════════════════════════════════════════════════

class TestCrossReferenceDataclasses:
    def test_vehicle_cross_reference_to_dict(self):
        ref = VehicleCrossReference(
            entidade_origem_tipo="PF",
            entidade_origem_id="111",
            entidade_destino_tipo="MO",
            entidade_destino_id="ABC",
            tipo_vinculo="PROPRIETARIO",
        )
        d = ref.to_dict()
        assert d["entidade_origem_tipo"] == "PF"
        assert d["ativo"] is True
        assert d["dados"] == {}

    def test_company_cross_reference_to_dict(self):
        ref = CompanyCrossReference(
            entidade_origem_tipo="PF",
            entidade_origem_id="111",
            entidade_destino_tipo="CO",
            entidade_destino_id="123",
            tipo_vinculo="SOCIO",
        )
        d = ref.to_dict()
        assert d["tipo_vinculo"] == "SOCIO"
