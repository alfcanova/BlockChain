"""Testes para blockchain_em — Blockchain de Embarcações"""

import pytest
from blockchain_em import (
    VesselEventType,
    VesselEventFactory,
    VesselChainProtector,
    VesselChain,
    CrossChainEM,
)


# ── EventType ─────────────────────────────────────────────────────────


class TestVesselEventType:
    def test_all_types_exist(self):
        assert VesselEventType.CONSTRUCAO.value == "CONSTRUCAO"
        assert VesselEventType.COMPRA_VENDA.value == "COMPRA_VENDA"
        assert VesselEventType.DOACAO.value == "DOACAO"
        assert VesselEventType.LEILAO.value == "LEILAO"
        assert VesselEventType.REVISAO.value == "REVISAO"
        assert VesselEventType.INSPECAO.value == "INSPECAO"
        assert VesselEventType.LICENCIAMENTO.value == "LICENCIAMENTO"
        assert VesselEventType.MUDANCA_NOME.value == "MUDANCA_NOME"
        assert VesselEventType.BAIXA.value == "BAIXA"
        assert VesselEventType.SEGURO.value == "SEGURO"
        assert VesselEventType.SINISTRO.value == "SINISTRO"

    def test_total_types(self):
        assert len(VesselEventType) == 16


# ── Construção (Gênesis) ──────────────────────────────────────────────


class TestConstrucaoEmbarcacao:
    def test_creates_valid(self):
        dados = VesselEventFactory.construcao(

            uf="SP",
            cidade="Sao Paulo",            registro_nr="NR-001",
            nome_embarcacao="Minha Lancha",
            tipo_embarcacao="Lancha",
            porte="PEQUENO",
            comprimento_m=8.5,
            beam_m=3.0,
            pontal_m=1.5,
            calado_m=0.8,
            deslocamento_ton=2.5,
            casco_material="Fibra",
            motorizacao="Fora-de-borda",
            motor_potencia_cv=150,
        )
        assert dados["evento_tipo"] == "CONSTRUCAO"
        assert dados["registro_nr"] == "NR-001"
        assert dados["nome_embarcacao"] == "Minha Lancha"
        assert dados["situacao"] == "REGULAR"

    def test_empty_registro_raises(self):
        with pytest.raises(ValueError, match="registro"):
            VesselEventFactory.construcao(
                uf="SP",
                cidade="Sao Paulo",
                registro_nr="", nome_embarcacao="Teste",
                tipo_embarcacao="Lancha", porte="PEQUENO",
                comprimento_m=8.0, beam_m=3.0, pontal_m=1.5,
                calado_m=0.8, deslocamento_ton=2.0,
                casco_material="Fibra", motorizacao="Fora-de-borda",
                motor_potencia_cv=100,
            )

    def test_empty_nome_raises(self):
        with pytest.raises(ValueError, match="Nome"):
            VesselEventFactory.construcao(
                uf="SP",
                cidade="Sao Paulo",
                registro_nr="NR-001", nome_embarcacao="",
                tipo_embarcacao="Lancha", porte="PEQUENO",
                comprimento_m=8.0, beam_m=3.0, pontal_m=1.5,
                calado_m=0.8, deslocamento_ton=2.0,
                casco_material="Fibra", motorizacao="Fora-de-borda",
                motor_potencia_cv=100,
            )

    def test_negative_comprimento_raises(self):
        with pytest.raises(ValueError, match="Comprimento"):
            VesselEventFactory.construcao(
                uf="SP",
                cidade="Sao Paulo",
                registro_nr="NR-001", nome_embarcacao="Teste",
                tipo_embarcacao="Lancha", porte="PEQUENO",
                comprimento_m=-1.0, beam_m=3.0, pontal_m=1.5,
                calado_m=0.8, deslocamento_ton=2.0,
                casco_material="Fibra", motorizacao="Fora-de-borda",
                motor_potencia_cv=100,
            )


# ── Compra/Venda ──────────────────────────────────────────────────────


class TestCompraVendaEmbarcacao:
    def test_creates_valid(self):
        dados = VesselEventFactory.compra_venda(
            registro_nr="NR-001",
            comprador_cpf="12345678901",
            comprador_nome="João Silva",
            vendedor_cpf="98765432100",
            vendedor_nome="Maria Santos",
            valor_transacao=50000.0,
            data_transacao="01/06/2024",
        )
        assert dados["evento_tipo"] == "COMPRA_VENDA"
        assert dados["valor_transacao"] == 50000.0

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="Data inválida"):
            VesselEventFactory.compra_venda(
                registro_nr="NR-001",
                comprador_cpf="12345678901", comprador_nome="João",
                vendedor_cpf="98765432100", vendedor_nome="Maria",
                valor_transacao=50000.0, data_transacao="01-06-2024",
            )


# ── Leilão ────────────────────────────────────────────────────────────


class TestLeilaoEmbarcacao:
    def test_creates_valid_with_winner(self):
        dados = VesselEventFactory.leilao(
            registro_nr="NR-001",
            data_leilao="01/12/2024",
            valor_minimo=30000.0,
            lance_vencedor=45000.0,
            vencedor_cpf="12345678901",
            vencedor_nome="João",
        )
        assert dados["status"] == "CONCLUIDO"

    def test_creates_valid_without_winner(self):
        dados = VesselEventFactory.leilao(
            registro_nr="NR-001",
            data_leilao="01/12/2024",
            valor_minimo=30000.0,
        )
        assert dados["status"] == "AGUARDANDO"


# ── Revisão ───────────────────────────────────────────────────────────


class TestRevisaoEmbarcacao:
    def test_creates_valid(self):
        dados = VesselEventFactory.revisao(
            registro_nr="NR-001",
            data_revisao="01/09/2024",
            oficina="Marina XYZ",
            tipo_revisao="PREVENTIVA",
            itens_revisados=["Motor", "Casco", "Elétrica"],
            valor_total=2000.0,
        )
        assert dados["evento_tipo"] == "REVISAO"
        assert len(dados["itens_revisados"]) == 3


# ── Inspeção ──────────────────────────────────────────────────────────


class TestInspecaoEmbarcacao:
    def test_creates_valid(self):
        dados = VesselEventFactory.inspecao(
            registro_nr="NR-001",
            data_inspecao="01/03/2024",
            orgao_inspecao="Capitania dos Portos",
            resultado="APROVADA",
        )
        assert dados["evento_tipo"] == "INSPECAO"
        assert dados["resultado"] == "APROVADA"


# ── Licenciamento ─────────────────────────────────────────────────────


class TestLicenciamentoEmbarcacao:
    def test_creates_valid(self):
        dados = VesselEventFactory.licenciamento(
            registro_nr="NR-001",
            ano_licenciamento=2024,
            data_licenciamento="01/03/2024",
            orgao_emissor="Capitania dos Portos",
        )
        assert dados["evento_tipo"] == "LICENCIAMENTO"


# ── Mudança de Nome ───────────────────────────────────────────────────


class TestMudancaNomeEmbarcacao:
    def test_creates_valid(self):
        dados = VesselEventFactory.mudanca_nome(
            registro_nr="NR-001",
            nome_anterior="Velho Nome",
            nome_novo="Novo Nome",
            data_mudanca="01/06/2024",
        )
        assert dados["nome_novo"] == "Novo Nome"


# ── Seguro ────────────────────────────────────────────────────────────


class TestSeguroEmbarcacao:
    def test_creates_valid(self):
        dados = VesselEventFactory.seguro(
            registro_nr="NR-001",
            seguradora_nome="Porto Seguro",
            seguradora_cnpj="61198164000123",
            apolice_numero="AP-2024-001",
            data_inicio="01/01/2024",
            data_fim="01/01/2025",
            valor_segurado=100000.0,
        )
        assert dados["status"] == "ATIVA"


# ── Sinistro ──────────────────────────────────────────────────────────


class TestSinistroEmbarcacao:
    def test_creates_valid(self):
        dados = VesselEventFactory.sinistro(
            registro_nr="NR-001",
            data_sinistro="15/06/2024",
            tipo="COLISAO",
            descricao="Colisão com doca",
            valor_dano=15000.0,
        )
        assert dados["evento_tipo"] == "SINISTRO"
        assert dados["valor_dano"] == 15000.0


# ── Baixa ─────────────────────────────────────────────────────────────


class TestBaixaEmbarcacao:
    def test_creates_valid(self):
        dados = VesselEventFactory.baixa(
            registro_nr="NR-001",
            data_baixa="01/01/2025",
            motivo="Perda total",
        )
        assert dados["evento_tipo"] == "BAIXA"


# ── VesselChain ───────────────────────────────────────────────────────


class TestVesselChain:
    def _create_genesis_data(self):
        return VesselEventFactory.construcao(
            uf="SP",
            cidade="Sao Paulo",
            registro_nr="NR-001",
            nome_embarcacao="Minha Lancha",
            tipo_embarcacao="Lancha",
            porte="PEQUENO",
            comprimento_m=8.5,
            beam_m=3.0,
            pontal_m=1.5,
            calado_m=0.8,
            deslocamento_ton=2.5,
            casco_material="Fibra",
            motorizacao="Fora-de-borda",
            motor_potencia_cv=150,
        )

    def test_create_genesis(self):
        chain = VesselChain(difficulty=1)
        dados = self._create_genesis_data()
        genesis = chain.create_genesis(dados)
        assert genesis.index == 0
        assert genesis.data["evento_tipo"] == "CONSTRUCAO"
        assert len(chain) == 1

    def test_get_registro_nr(self):
        chain = VesselChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        assert chain.get_registro_nr() == "NR-001"

    def test_add_compra_venda(self):
        chain = VesselChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        block = chain.add_event(
            "COMPRA_VENDA",
            VesselEventFactory.compra_venda(
                registro_nr="NR-001",
                comprador_cpf="12345678901", comprador_nome="João",
                vendedor_cpf="98765432100", vendedor_nome="Maria",
                valor_transacao=50000.0, data_transacao="01/06/2024",
            ),
        )
        assert block.index == 1
        assert len(chain) == 2

    def test_get_estado_after_compra(self):
        chain = VesselChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "COMPRA_VENDA",
            VesselEventFactory.compra_venda(
                registro_nr="NR-001",
                comprador_cpf="12345678901", comprador_nome="João",
                vendedor_cpf="98765432100", vendedor_nome="Maria",
                valor_transacao=50000.0, data_transacao="01/06/2024",
            ),
        )
        estado = chain.get_estado_atual()
        assert len(estado["proprietarios"]) == 1
        assert estado["proprietarios"][0]["cpf"] == "12345678901"

    def test_get_estado_after_mudanca_nome(self):
        chain = VesselChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "MUDANCA_NOME",
            VesselEventFactory.mudanca_nome(
                registro_nr="NR-001",
                nome_anterior="Minha Lancha",
                nome_novo="Novo Nome",
                data_mudanca="01/06/2024",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["nome_embarcacao"] == "Novo Nome"

    def test_get_estado_after_baixa(self):
        chain = VesselChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "BAIXA",
            VesselEventFactory.baixa(
                registro_nr="NR-001",
                data_baixa="01/01/2025",
                motivo="Perda total",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["situacao"] == "BAIXADA"

    def test_validate_valid(self):
        chain = VesselChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        ok, msg = chain.validate()
        assert ok
        assert "válida" in msg

    def test_validate_empty(self):
        chain = VesselChain(difficulty=1)
        ok, msg = chain.validate()
        assert not ok

    def test_add_evento_sem_genesis(self):
        chain = VesselChain(difficulty=1)
        with pytest.raises(ValueError, match="Cadeia vazia"):
            chain.add_event("COMPRA_VENDA", {})

    def test_historico_completo(self):
        chain = VesselChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "REVISAO",
            VesselEventFactory.revisao(
                registro_nr="NR-001", data_revisao="01/09/2024",
            ),
        )
        historico = chain.get_historico_completo()
        assert len(historico) == 2


# ── VesselChainProtector ──────────────────────────────────────────────


class TestVesselChainProtector:
    def test_allows_when_regular(self):
        assert VesselChainProtector.pode_adicionar("COMPRA_VENDA", "REGULAR")

    def test_blocks_when_baixada(self):
        assert not VesselChainProtector.pode_adicionar("COMPRA_VENDA", "BAIXADA")

    def test_allows_baixa_when_baixada(self):
        assert VesselChainProtector.pode_adicionar("BAIXA", "BAIXADA")


# ── CrossChainEM ──────────────────────────────────────────────────────


class TestCrossChainEM:
    def _create_pf(self):
        from blockchain_pf import Blockchain, EventFactory
        chain = Blockchain(difficulty=1)
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="João da Silva",
            data_nascimento="15/03/1990", sexo="M",
            cidade_nascimento="São Paulo", uf_nascimento="SP",
            nome_mae="Maria da Silva",
        )
        chain.create_genesis(dados)
        return chain

    def _create_em(self):
        chain = VesselChain(difficulty=1)
        dados = VesselEventFactory.construcao(
            uf="SP",
            cidade="Sao Paulo",
            registro_nr="NR-001", nome_embarcacao="Minha Lancha",
            tipo_embarcacao="Lancha", porte="PEQUENO",
            comprimento_m=8.5, beam_m=3.0, pontal_m=1.5,
            calado_m=0.8, deslocamento_ton=2.5,
            casco_material="Fibra", motorizacao="Fora-de-borda",
            motor_potencia_cv=150,
        )
        chain.create_genesis(dados)
        return chain

    def test_create_reference(self):
        manager = CrossChainEM()
        pf = self._create_pf()
        em = self._create_em()
        manager.register_pf("12345678901", pf)
        manager.register_em("NR-001", em)

        ref = manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="EM", destino_id="NR-001",
            tipo_vinculo="PROPRIETARIO",
        )
        assert ref.entidade_origem_id == "12345678901"
        assert ref.entidade_destino_id == "NR-001"
        assert ref.ativo

    def test_get_embarcacoes_da_pessoa(self):
        manager = CrossChainEM()
        pf = self._create_pf()
        em = self._create_em()
        manager.register_pf("12345678901", pf)
        manager.register_em("NR-001", em)
        manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="EM", destino_id="NR-001",
            tipo_vinculo="PROPRIETARIO",
        )
        result = manager.get_embarcacoes_da_pessoa("12345678901")
        assert len(result) == 1
        assert result[0]["registro_nr"] == "NR-001"

    def test_stats(self):
        manager = CrossChainEM()
        pf = self._create_pf()
        em = self._create_em()
        manager.register_pf("12345678901", pf)
        manager.register_em("NR-001", em)
        manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="EM", destino_id="NR-001",
            tipo_vinculo="PROPRIETARIO",
        )
        stats = manager.stats()
        assert stats["total_cadeias_pf"] == 1
        assert stats["total_cadeias_em"] == 1
        assert stats["referencias_ativas"] == 1
