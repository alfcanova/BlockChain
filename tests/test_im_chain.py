"""Testes completos para blockchain_im/chain.py.

Cobre: todos os branches de get_estado_atual, set_signer com genesis,
validacao com assinaturas, persistencia (save/load), busca, repr,
fluxo financeiro com leilao, onus ativos, e error paths.
"""
import os
import tempfile

import pytest

from blockchain_im import PropertyChain, PropertyEventFactory, PropertyEventType
from blockchain_pf.signatures import KeyPair, generate_authority_keypair


# ── Helpers ──────────────────────────────────────────────────────────

def _terreno_data(**overrides):
    defaults = dict(
        matricula="12345",
        endereco_logradouro="Rua das Flores, 123",
        endereco_bairro="Centro",
        endereco_cidade="Sao Paulo",
        endereco_uf="SP",
        endereco_cep="01234-567",
        lat=-23.5505,
        lon=-46.6333,
        area_terreno_m2=500.0,
    )
    defaults.update(overrides)
    return PropertyEventFactory.terreno(**defaults)


def _make_chain(**chain_kwargs):
    c = PropertyChain(difficulty=1, **chain_kwargs)
    c.create_genesis(_terreno_data())
    return c


# ══════════════════════════════════════════════════════════════════════
#  GENESIS / SIGNER
# ══════════════════════════════════════════════════════════════════════

class TestGenesisAndSigner:
    def test_genesis_signed(self):
        chain = PropertyChain(difficulty=1)
        kp = generate_authority_keypair("Cartorio SP")
        chain.set_signer(kp)
        genesis = chain.create_genesis(_terreno_data())
        assert genesis.has_signature()
        assert genesis.signature["signer_label"] == "Cartorio SP"

    def test_genesis_signed_by_default(self):
        """Genesis e obrigatoriamente assinado."""
        chain = PropertyChain(difficulty=1)
        genesis = chain.create_genesis(_terreno_data())
        assert genesis.has_signature()

    def test_set_signer_property(self):
        chain = PropertyChain(difficulty=1)
        assert chain.signer is not None  # Default signer configurado
        kp = generate_authority_keypair("Test")
        chain.set_signer(kp)
        assert chain.signer is not None
        assert chain.signer.keypair.label == "Test"

    def test_add_event_signed(self):
        chain = PropertyChain(difficulty=1)
        kp = generate_authority_keypair("Cart")
        chain.set_signer(kp)
        chain.create_genesis(_terreno_data())
        block = chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="Casa", area_construida_m2=100.0,
        ))
        assert block.has_signature()


# ══════════════════════════════════════════════════════════════════════
#  ERROR PATHS
# ══════════════════════════════════════════════════════════════════════

class TestErrorPaths:
    def test_add_event_empty_chain(self):
        chain = PropertyChain(difficulty=1)
        with pytest.raises(ValueError, match="vazia"):
            chain.add_event("CONSTRUCAO", {"foo": "bar"})

    def test_add_event_blocked_on_confiscado(self):
        chain = _make_chain()
        chain.add_event("CONFISCO", PropertyEventFactory.confisco(
            matricula="12345", autoridade="Justica", processo_numero="001",
            data_confisco="01/01/2024",
        ))
        with pytest.raises(ValueError, match="bloqueado"):
            chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
                matricula="12345", descricao="X", area_construida_m2=50.0,
            ))


# ══════════════════════════════════════════════════════════════════════
#  GET_ESTADO_ATUAL — todos os branches de evento
# ══════════════════════════════════════════════════════════════════════

class TestEstadoAtualBranches:
    def test_estado_empty(self):
        assert PropertyChain(difficulty=1).get_estado_atual() == {}

    def _chain_with(self, event_type, payload):
        chain = _make_chain()
        chain.add_event(event_type, payload)
        return chain.get_estado_atual()

    # ── CONSTRUCAO ──────────────────────────────────────────────────

    def test_construcao_increments_area(self):
        chain = _make_chain()
        chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="A", area_construida_m2=100.0,
        ))
        chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="B", area_construida_m2=50.0,
        ))
        estado = chain.get_estado_atual()
        assert estado["area_construida_m2"] == 150.0
        assert estado["situacao"] == "CONSTRUIDO"

    # ── DEMOLICAO ──────────────────────────────────────────────────

    def test_demolicao_partial(self):
        chain = _make_chain()
        chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="A", area_construida_m2=200.0,
        ))
        chain.add_event("DEMOLICAO", PropertyEventFactory.demolicao(
            matricula="12345", descricao="B", area_demolida_m2=50.0,
        ))
        estado = chain.get_estado_atual()
        assert estado["area_construida_m2"] == 150.0
        assert estado["situacao"] == "CONSTRUIDO"

    def test_demolicao_total(self):
        chain = _make_chain()
        chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="A", area_construida_m2=100.0,
        ))
        chain.add_event("DEMOLICAO", PropertyEventFactory.demolicao(
            matricula="12345", descricao="B", area_demolida_m2=100.0,
        ))
        estado = chain.get_estado_atual()
        assert estado["area_construida_m2"] == 0
        assert estado["situacao"] == "LIVRE"

    # ── REFORMA ────────────────────────────────────────────────────

    def test_reforma_ampliacao(self):
        estado = self._chain_with("REFORMA", PropertyEventFactory.reforma(
            matricula="12345", descricao="A", tipo="AMPLIACAO",
            area_anterior_m2=100.0, area_nova_m2=130.0,
        ))
        assert estado["area_construida_m2"] == 30.0

    def test_reforma_reducao(self):
        estado = self._chain_with("REFORMA", PropertyEventFactory.reforma(
            matricula="12345", descricao="A", tipo="REDUCAO",
            area_anterior_m2=100.0, area_nova_m2=70.0,
        ))
        assert estado["area_construida_m2"] == 0  # -30 clamped to 0

    # ── COMPRA_VENDA ───────────────────────────────────────────────

    def test_compra_venda_adds_comprador(self):
        estado = self._chain_with("COMPRA_VENDA", PropertyEventFactory.compra_venda(
            matricula="12345",
            comprador_cpf="11111111111", comprador_nome="Joao",
            vendedor_cpf="22222222222", vendedor_nome="Maria",
            valor_transacao=300000.0, data_transacao="01/01/2024",
        ))
        cpfs = [p["cpf"] for p in estado["proprietarios"]]
        assert "11111111111" in cpfs
        assert "22222222222" not in cpfs

    def test_compra_venda_dedup(self):
        """Comprador ja existente nao duplica."""
        chain = _make_chain()
        # Adiciona proprietario manualmente
        chain.add_event("COMPRA_VENDA", PropertyEventFactory.compra_venda(
            matricula="12345",
            comprador_cpf="11111111111", comprador_nome="Joao",
            vendedor_cpf="22222222222", vendedor_nome="Maria",
            valor_transacao=300000.0, data_transacao="01/01/2024",
        ))
        # Mesmo comprador compra novamente
        chain.add_event("COMPRA_VENDA", PropertyEventFactory.compra_venda(
            matricula="12345",
            comprador_cpf="11111111111", comprador_nome="Joao 2",
            vendedor_cpf="33333333333", vendedor_nome="Ana",
            valor_transacao=400000.0, data_transacao="01/06/2024",
        ))
        estado = chain.get_estado_atual()
        count = sum(1 for p in estado["proprietarios"] if p["cpf"] == "11111111111")
        assert count == 1

    # ── DOACAO ─────────────────────────────────────────────────────

    def test_doacao_adds_donatario(self):
        estado = self._chain_with("DOACAO", PropertyEventFactory.doacao(
            matricula="12345",
            donatario_cpf="11111111111", donatario_nome="Filho",
            doador_cpf="22222222222", doador_nome="Pai",
            data_doacao="01/01/2024",
        ))
        cpfs = [p["cpf"] for p in estado["proprietarios"]]
        assert "11111111111" in cpfs
        assert "22222222222" not in cpfs

    def test_doacao_dedup(self):
        chain = _make_chain()
        chain.add_event("DOACAO", PropertyEventFactory.doacao(
            matricula="12345",
            donatario_cpf="11111111111", donatario_nome="Filho",
            doador_cpf="22222222222", doador_nome="Pai",
            data_doacao="01/01/2024",
        ))
        chain.add_event("DOACAO", PropertyEventFactory.doacao(
            matricula="12345",
            donatario_cpf="11111111111", donatario_nome="Filho",
            doador_cpf="33333333333", doador_nome="Mae",
            data_doacao="01/06/2024",
        ))
        estado = chain.get_estado_atual()
        count = sum(1 for p in estado["proprietarios"] if p["cpf"] == "11111111111")
        assert count == 1

    # ── HERANCA ────────────────────────────────────────────────────

    def test_heranca_replaces_inventariado(self):
        estado = self._chain_with("HERANCA", PropertyEventFactory.heranca(
            matricula="12345",
            inventariado_cpf="22222222222", inventariado_nome="Falecido",
            herdeiros=[
                {"cpf": "11111111111", "nome": "A", "participacao": 50.0},
                {"cpf": "33333333333", "nome": "B", "participacao": 50.0},
            ],
            data_obito="01/01/2024",
        ))
        cpfs = [p["cpf"] for p in estado["proprietarios"]]
        assert "22222222222" not in cpfs
        assert "11111111111" in cpfs
        assert "33333333333" in cpfs

    def test_heranca_dedup_herdeiro(self):
        chain = _make_chain()
        # Herdeiro ja existente nao duplica
        chain.add_event("HERANCA", PropertyEventFactory.heranca(
            matricula="12345",
            inventariado_cpf="22222222222", inventariado_nome="Falecido",
            herdeiros=[{"cpf": "11111111111", "nome": "A", "participacao": 50.0}],
            data_obito="01/01/2024",
        ))
        chain.add_event("HERANCA", PropertyEventFactory.heranca(
            matricula="12345",
            inventariado_cpf="33333333333", inventariado_nome="Outro",
            herdeiros=[{"cpf": "11111111111", "nome": "A", "participacao": 100.0}],
            data_obito="01/06/2024",
        ))
        estado = chain.get_estado_atual()
        count = sum(1 for p in estado["proprietarios"] if p["cpf"] == "11111111111")
        assert count == 1

    # ── PROPRIETARIO ───────────────────────────────────────────────

    def test_proprietario_add(self):
        estado = self._chain_with("PROPRIETARIO", {
            "proprietario": {"cpf": "11111111111", "nome": "Joao"},
            "participacao": 60.0,
            "origem": "COMPRA",
        })
        assert any(p["cpf"] == "11111111111" for p in estado["proprietarios"])

    def test_proprietario_update(self):
        chain = _make_chain()
        chain.add_event("PROPRIETARIO", {
            "proprietario": {"cpf": "11111111111", "nome": "Joao"},
            "participacao": 60.0, "origem": "COMPRA",
        })
        chain.add_event("PROPRIETARIO", {
            "proprietario": {"cpf": "11111111111", "nome": "Joao 2"},
            "participacao": 100.0,
        })
        estado = chain.get_estado_atual()
        prop = [p for p in estado["proprietarios"] if p["cpf"] == "11111111111"][0]
        assert prop["participacao"] == 100.0
        assert prop["nome"] == "Joao 2"

    def test_proprietario_remove(self):
        chain = _make_chain()
        chain.add_event("PROPRIETARIO", {
            "proprietario": {"cpf": "11111111111", "nome": "Joao"},
            "participacao": 60.0, "origem": "COMPRA",
        })
        chain.add_event("PROPRIETARIO", {
            "proprietario": {"cpf": "11111111111", "nome": "Joao"},
            "participacao": 0,
        })
        estado = chain.get_estado_atual()
        assert not any(p["cpf"] == "11111111111" for p in estado["proprietarios"])

    # ── GARANTIA ───────────────────────────────────────────────────

    def test_garantia_adds_onus(self):
        estado = self._chain_with("GARANTIA", PropertyEventFactory.garantia(
            matricula="12345",
            credor_nome="Banco", credor_cnpj="12345678000190",
            valor_garantia=200000.0, data_garantia="01/01/2024",
            data_vencimento="01/01/2034",
        ))
        assert len(estado["onus_reais"]) == 1
        assert estado["onus_reais"][0]["status"] == "ATIVA"
        assert estado["situacao"] == "GARANTIDO"

    # ── QUITACAO ───────────────────────────────────────────────────

    def test_quitacao_marks_resolved(self):
        chain = _make_chain()
        chain.add_event("GARANTIA", PropertyEventFactory.garantia(
            matricula="12345",
            credor_nome="Banco", credor_cnpj="12345678000190",
            valor_garantia=200000.0, data_garantia="01/01/2024",
            data_vencimento="01/01/2034",
        ))
        chain.add_event("QUITACAO", PropertyEventFactory.quitacao(
            matricula="12345", garantia_index=0,
            data_quitacao="01/06/2024", valor_pago=200000.0,
        ))
        estado = chain.get_estado_atual()
        assert estado["onus_reais"][0]["status"] == "QUITADA"
        assert estado["situacao"] == "LIVRE"

    def test_quitacao_invalid_index(self):
        """Index invalido nao causa erro."""
        chain = _make_chain()
        chain.add_event("QUITACAO", PropertyEventFactory.quitacao(
            matricula="12345", garantia_index=99,
            data_quitacao="01/06/2024", valor_pago=0.0,
        ))
        # Nao deve dar erro
        assert chain.get_estado_atual()["situacao"] == "LIVRE"

    def test_quitacao_keeps_other_garantias(self):
        """Se ha outra garantia ativa, situacao permanece GARANTIDO."""
        chain = _make_chain()
        chain.add_event("GARANTIA", PropertyEventFactory.garantia(
            matricula="12345", credor_nome="B1", credor_cnpj="11111111111111",
            valor_garantia=100.0, data_garantia="01/01/2024",
            data_vencimento="01/01/2034",
        ))
        chain.add_event("GARANTIA", PropertyEventFactory.garantia(
            matricula="12345", credor_nome="B2", credor_cnpj="22222222222222",
            valor_garantia=200.0, data_garantia="01/01/2024",
            data_vencimento="01/01/2034",
        ))
        chain.add_event("QUITACAO", PropertyEventFactory.quitacao(
            matricula="12345", garantia_index=0,
            data_quitacao="01/06/2024", valor_pago=100.0,
        ))
        estado = chain.get_estado_atual()
        assert estado["onus_reais"][0]["status"] == "QUITADA"
        assert estado["onus_reais"][1]["status"] == "ATIVA"
        assert estado["situacao"] == "GARANTIDO"

    # ── LEILAO ─────────────────────────────────────────────────────

    def test_leilao_com_lance(self):
        estado = self._chain_with("LEILAO", PropertyEventFactory.leilao(
            matricula="12345", data_leilao="01/12/2024",
            valor_minimo=100000.0, lance_vencedor=150000.0,
            vencedor_cpf="11111111111", vencedor_nome="Comprador",
        ))
        assert estado["situacao"] == "LIVRE"
        assert any(p["cpf"] == "11111111111" for p in estado["proprietarios"])

    def test_leilao_sem_lance(self):
        estado = self._chain_with("LEILAO", PropertyEventFactory.leilao(
            matricula="12345", data_leilao="01/12/2024",
            valor_minimo=100000.0,
        ))
        assert estado["situacao"] == "EM_LEILAO"

    # ── CONFISCO ───────────────────────────────────────────────────

    def test_confisco_esvazia(self):
        estado = self._chain_with("CONFISCO", PropertyEventFactory.confisco(
            matricula="12345", autoridade="Justica",
            processo_numero="001", data_confisco="01/01/2024",
        ))
        assert estado["situacao"] == "CONFISCADO"
        assert estado["proprietarios"] == []

    # ── PENHORA ────────────────────────────────────────────────────

    def test_penhora_adds_onus(self):
        estado = self._chain_with("PENHORA", {
            "autoridade": "Justica Federal",
            "processo_numero": "001-2024",
            "valor_penhorado": 50000.0,
            "data_penhora": "15/03/2024",
        })
        assert len(estado["onus_reais"]) == 1
        assert estado["onus_reais"][0]["tipo"] == "PENHORA"

    # ── ZONEAMENTO ─────────────────────────────────────────────────

    def test_zoneamento(self):
        estado = self._chain_with("ZONEAMENTO", {
            "zoneamento_novo": "COMERCIAL",
        })
        assert estado["zoneamento"] == "COMERCIAL"

    # ── IPTU ───────────────────────────────────────────────────────

    def test_iptu(self):
        estado = self._chain_with("IPTU", {
            "codigo_iptu": "IPTU-9999",
        })
        assert estado["codigo_iptu"] == "IPTU-9999"

    # ── CERTIDAO ───────────────────────────────────────────────────

    def test_certidao(self):
        estado = self._chain_with("CERTIDAO", {
            "tipo_certidao": "NEGATIVA",
            "data_emissao": "01/01/2024",
            "numero": "CERT-001",
            "orgao_emissor": "Cartorio",
        })
        assert len(estado["certidoes"]) == 1
        assert estado["certidoes"][0]["tipo"] == "NEGATIVA"

    # ── MATRICULA ──────────────────────────────────────────────────

    def test_matricula_update(self):
        chain = _make_chain()
        chain.add_event("MATRICULA", {"nova_matricula": "54321"})
        estado = chain.get_estado_atual()
        assert estado["matricula"] == "54321"

    def test_get_matricula_after_update(self):
        chain = _make_chain()
        chain.add_event("MATRICULA", {"nova_matricula": "54321"})
        assert chain.get_matricula() == "54321"

    # ── LOTEAMENTO ─────────────────────────────────────────────────

    def test_loteamento(self):
        estado = self._chain_with("LOTEAMENTO", {})
        assert estado["situacao"] == "LOTEADO"

    # ── DESMEMBRAMENTO ─────────────────────────────────────────────

    def test_desmembramento(self):
        estado = self._chain_with("DESMEMBRAMENTO", {})
        assert estado["situacao"] == "DESMEMBRADO"

    # ── FUSAO ──────────────────────────────────────────────────────

    def test_fusao_updates_area(self):
        estado = self._chain_with("FUSAO", {
            "area_total_m2": 1000.0,
            "endereco": "Rua Nova, 456",
        })
        assert estado["area_terreno_m2"] == 1000.0
        assert estado["endereco"]["logradouro"] == "Rua Nova, 456"

    def test_fusao_without_endereco(self):
        estado = self._chain_with("FUSAO", {"area_total_m2": 800.0})
        assert estado["area_terreno_m2"] == 800.0


# ══════════════════════════════════════════════════════════════════════
#  BUSCA
# ══════════════════════════════════════════════════════════════════════

class TestBusca:
    def test_get_event(self):
        chain = _make_chain()
        b = chain.get_event(0)
        assert b is not None
        assert b.index == 0

    def test_get_event_out_of_range(self):
        chain = _make_chain()
        assert chain.get_event(99) is None

    def test_get_events_by_type(self):
        chain = _make_chain()
        chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="A", area_construida_m2=100.0,
        ))
        chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="B", area_construida_m2=50.0,
        ))
        blocks = chain.get_events_by_type("CONSTRUCAO")
        assert len(blocks) == 2

    def test_get_events_by_type_none(self):
        chain = _make_chain()
        assert chain.get_events_by_type("INEXISTENTE") == []

    def test_get_last_event(self):
        chain = _make_chain()
        chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="A", area_construida_m2=100.0,
        ))
        last = chain.get_last_event()
        assert last.index == 1

    def test_get_last_event_empty(self):
        assert PropertyChain(difficulty=1).get_last_event() is None

    def test_get_genesis_block(self):
        chain = _make_chain()
        genesis = chain.get_genesis_block()
        assert genesis.index == 0

    def test_get_genesis_block_empty(self):
        assert PropertyChain(difficulty=1).get_genesis_block() is None


# ══════════════════════════════════════════════════════════════════════
#  FLUXO FINANCEIRO / ONUS
# ══════════════════════════════════════════════════════════════════════

class TestFinanceiro:
    def test_fluxo_financeiro_com_leilao(self):
        chain = _make_chain()
        chain.add_event("LEILAO", PropertyEventFactory.leilao(
            matricula="12345", data_leilao="01/12/2024",
            valor_minimo=100000.0, lance_vencedor=150000.0,
            vencedor_cpf="111", vencedor_nome="C",
        ))
        fluxo = chain.get_fluxo_financeiro()
        assert len(fluxo) == 1
        assert fluxo[0]["tipo"] == "LEILAO"
        assert fluxo[0]["valor"] == 150000.0

    def test_fluxo_financeiro_leilao_sem_lance(self):
        chain = _make_chain()
        chain.add_event("LEILAO", PropertyEventFactory.leilao(
            matricula="12345", data_leilao="01/12/2024",
            valor_minimo=100000.0,
        ))
        assert chain.get_fluxo_financeiro() == []

    def test_fluxo_financeiro_vazio(self):
        chain = _make_chain()
        assert chain.get_fluxo_financeiro() == []

    def test_onus_ativos(self):
        chain = _make_chain()
        chain.add_event("GARANTIA", PropertyEventFactory.garantia(
            matricula="12345", credor_nome="Banco",
            credor_cnpj="12345678000190", valor_garantia=100.0,
            data_garantia="01/01/2024", data_vencimento="01/01/2034",
        ))
        onus = chain.get_onus_ativos()
        assert len(onus) == 1
        assert onus[0]["status"] == "ATIVA"

    def test_onus_ativos_after_quitacao(self):
        chain = _make_chain()
        chain.add_event("GARANTIA", PropertyEventFactory.garantia(
            matricula="12345", credor_nome="Banco",
            credor_cnpj="12345678000190", valor_garantia=100.0,
            data_garantia="01/01/2024", data_vencimento="01/01/2034",
        ))
        chain.add_event("QUITACAO", PropertyEventFactory.quitacao(
            matricula="12345", garantia_index=0,
            data_quitacao="01/06/2024", valor_pago=100.0,
        ))
        assert chain.get_onus_ativos() == []


# ══════════════════════════════════════════════════════════════════════
#  VALIDACAO COM ASSINATURAS
# ══════════════════════════════════════════════════════════════════════

class TestValidacaoAssinatura:
    def test_validate_with_signatures_ok(self):
        chain = PropertyChain(difficulty=1)
        kp = generate_authority_keypair("Cart")
        chain.set_signer(kp)
        chain.create_genesis(_terreno_data())
        chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="A", area_construida_m2=100.0,
        ))
        ok, msg = chain.validate(require_signatures=True)
        assert ok

    def test_validate_signature_missing_block(self):
        """Bloco sem assinatura falha quando require_signatures=True."""
        chain = PropertyChain(difficulty=1)
        kp = generate_authority_keypair("Cart")
        chain.set_signer(kp)
        chain.create_genesis(_terreno_data())
        # Remove assinatura do genesis manualmente
        chain.chain[0].signature = None
        ok, msg = chain.validate(require_signatures=True)
        assert not ok
        assert "sem assinatura" in msg

    def test_validate_signature_missing_later_block(self):
        chain = PropertyChain(difficulty=1)
        kp = generate_authority_keypair("Cart")
        chain.set_signer(kp)
        chain.create_genesis(_terreno_data())
        block = chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="A", area_construida_m2=100.0,
        ))
        block.signature = None
        ok, msg = chain.validate(require_signatures=True)
        assert not ok

    def test_verify_all_signatures_ok(self):
        chain = PropertyChain(difficulty=1)
        kp = generate_authority_keypair("Cart")
        chain.set_signer(kp)
        chain.create_genesis(_terreno_data())
        ok, msg = chain.verify_all_signatures()
        assert ok

    def test_verify_all_signatures_signed(self):
        """Todos os blocos sao assinados por padrao."""
        chain = _make_chain()
        ok, msg = chain.verify_all_signatures()
        assert ok
        assert "válidas" in msg.lower()

    def test_verify_all_signatures_invalid(self):
        """Assinatura adulterada é detectada."""
        chain = PropertyChain(difficulty=1)
        kp = generate_authority_keypair("Cart")
        chain.set_signer(kp)
        chain.create_genesis(_terreno_data())
        # Adultera a assinatura
        chain.chain[0].signature["signature_b64"] = "AAAA"
        ok, msg = chain.verify_all_signatures()
        assert not ok


# ══════════════════════════════════════════════════════════════════════
#  PERSISTENCIA
# ══════════════════════════════════════════════════════════════════════

class TestPersistencia:
    def test_save_and_load(self, tmp_path):
        chain = _make_chain()
        chain.add_event("CONSTRUCAO", PropertyEventFactory.construcao(
            matricula="12345", descricao="A", area_construida_m2=100.0,
        ))
        path = str(tmp_path / "im.json")
        chain.save_to_file(path)

        loaded = PropertyChain.load_from_file(path)
        assert len(loaded) == 2
        assert loaded.get_matricula() == "12345"
        ok, _ = loaded.validate()
        assert ok

    def test_save_creates_dirs(self, tmp_path):
        path = str(tmp_path / "sub" / "im.json")
        _make_chain().save_to_file(path)
        assert os.path.exists(path)


# ══════════════════════════════════════════════════════════════════════
#  LEN / REPR
# ══════════════════════════════════════════════════════════════════════

class TestReprLen:
    def test_len(self):
        chain = _make_chain()
        assert len(chain) == 1

    def test_repr(self):
        chain = _make_chain()
        r = repr(chain)
        assert "PropertyChain" in r
        assert "12345" in r

    def test_repr_with_signer(self):
        chain = PropertyChain(difficulty=1)
        kp = generate_authority_keypair("Cart")
        chain.set_signer(kp)
        chain.create_genesis(_terreno_data())
        r = repr(chain)
        assert "Cart" in r
