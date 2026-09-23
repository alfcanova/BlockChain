"""Testes para blockchain_ac — Blockchain de Aeronaves"""

import pytest
from blockchain_ac import (
    AircraftEventType,
    AircraftEventFactory,
    AircraftChainProtector,
    AircraftChain,
    CrossChainAC,
)


# ── EventType ─────────────────────────────────────────────────────────


class TestAircraftEventType:
    def test_all_types_exist(self):
        assert AircraftEventType.FABRICACAO.value == "FABRICACAO"
        assert AircraftEventType.COMPRA_VENDA.value == "COMPRA_VENDA"
        assert AircraftEventType.DOACAO.value == "DOACAO"
        assert AircraftEventType.LEILAO.value == "LEILAO"
        assert AircraftEventType.REVISAO.value == "REVISAO"
        assert AircraftEventType.INSPECAO.value == "INSPECAO"
        assert AircraftEventType.AIRWORTHINESS.value == "AIRWORTHINESS"
        assert AircraftEventType.LICENCA_VOO.value == "LICENCA_VOO"
        assert AircraftEventType.REGISTRO.value == "REGISTRO"
        assert AircraftEventType.MUDANCA_NOME.value == "MUDANCA_NOME"
        assert AircraftEventType.BAIXA.value == "BAIXA"
        assert AircraftEventType.SEGURO.value == "SEGURO"
        assert AircraftEventType.SINISTRO.value == "SINISTRO"

    def test_total_types(self):
        assert len(AircraftEventType) == 17


# ── Fabricação (Gênesis) ──────────────────────────────────────────────


class TestFabricacao:
    def test_creates_valid(self):
        dados = AircraftEventFactory.fabricacao(

            uf="SP",
            cidade="Sao Paulo",            matricula="PT-ABC",
            nome_aeronave="Cessna 172",
            fabricante="Cessna",
            modelo="172S",
            tipo_aeronave="AVIAO",
            ano_fabricacao=2020,
            peso_max_decolagem_kg=1111,
            motorizacao="PISTAO",
            num_motores=1,
            motor_potencia_cv=180,
        )
        assert dados["evento_tipo"] == "FABRICACAO"
        assert dados["matricula"] == "PTABC"
        assert dados["nome_aeronave"] == "Cessna 172"
        assert dados["situacao"] == "REGULAR"

    def test_empty_matricula_raises(self):
        with pytest.raises(ValueError, match="Matrícula"):
            AircraftEventFactory.fabricacao(
                uf="SP",
                cidade="Sao Paulo",
                matricula="", nome_aeronave="Teste",
                fabricante="Teste", modelo="T",
                tipo_aeronave="AVIAO", ano_fabricacao=2020,
                peso_max_decolagem_kg=1000, motorizacao="PISTAO",
                num_motores=1, motor_potencia_cv=100,
            )

    def test_empty_nome_raises(self):
        with pytest.raises(ValueError, match="Nome"):
            AircraftEventFactory.fabricacao(
                uf="SP",
                cidade="Sao Paulo",
                matricula="PT-ABC", nome_aeronave="",
                fabricante="Teste", modelo="T",
                tipo_aeronave="AVIAO", ano_fabricacao=2020,
                peso_max_decolagem_kg=1000, motorizacao="PISTAO",
                num_motores=1, motor_potencia_cv=100,
            )

    def test_empty_fabricante_raises(self):
        with pytest.raises(ValueError, match="Fabricante"):
            AircraftEventFactory.fabricacao(
                uf="SP",
                cidade="Sao Paulo",
                matricula="PT-ABC", nome_aeronave="Teste",
                fabricante="", modelo="T",
                tipo_aeronave="AVIAO", ano_fabricacao=2020,
                peso_max_decolagem_kg=1000, motorizacao="PISTAO",
                num_motores=1, motor_potencia_cv=100,
            )

    def test_negative_peso_raises(self):
        with pytest.raises(ValueError, match="Peso máximo"):
            AircraftEventFactory.fabricacao(
                uf="SP",
                cidade="Sao Paulo",
                matricula="PT-ABC", nome_aeronave="Teste",
                fabricante="Cessna", modelo="T",
                tipo_aeronave="AVIAO", ano_fabricacao=2020,
                peso_max_decolagem_kg=-100, motorizacao="PISTAO",
                num_motores=1, motor_potencia_cv=100,
            )


# ── Compra/Venda ──────────────────────────────────────────────────────


class TestCompraVendaAeronave:
    def test_creates_valid(self):
        dados = AircraftEventFactory.compra_venda(
            matricula="PT-ABC",
            comprador_cpf="12345678901",
            comprador_nome="João Silva",
            vendedor_cpf="98765432100",
            vendedor_nome="Maria Santos",
            valor_transacao=500000.0,
            data_transacao="01/06/2024",
        )
        assert dados["evento_tipo"] == "COMPRA_VENDA"
        assert dados["valor_transacao"] == 500000.0

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="Data inválida"):
            AircraftEventFactory.compra_venda(
                matricula="PT-ABC",
                comprador_cpf="12345678901", comprador_nome="João",
                vendedor_cpf="98765432100", vendedor_nome="Maria",
                valor_transacao=500000.0, data_transacao="01-06-2024",
            )


# ── Doação ────────────────────────────────────────────────────────────


class TestDoacaoAeronave:
    def test_creates_valid(self):
        dados = AircraftEventFactory.doacao(
            matricula="PT-ABC",
            donatario_cpf="12345678901", donatario_nome="João",
            doador_cpf="98765432100", doador_nome="Maria",
            data_doacao="01/06/2024",
        )
        assert dados["evento_tipo"] == "DOACAO"


# ── Revisão ───────────────────────────────────────────────────────────


class TestRevisaoAeronave:
    def test_creates_valid(self):
        dados = AircraftEventFactory.revisao(
            matricula="PT-ABC",
            data_revisao="01/09/2024",
            oficina="Aero Maintenance",
            tipo_revisao="ANUAL",
            itens_revisados=["Motor", "Asas", "Sistema elétrico"],
            valor_total=15000.0,
        )
        assert dados["evento_tipo"] == "REVISAO"
        assert len(dados["itens_revisados"]) == 3


# ── Inspeção ──────────────────────────────────────────────────────────


class TestInspecaoAeronave:
    def test_creates_valid(self):
        dados = AircraftEventFactory.inspecao(
            matricula="PT-ABC",
            data_inspecao="01/03/2024",
            orgao_inspecao="ANAC",
            resultado="APROVADA",
        )
        assert dados["resultado"] == "APROVADA"


# ── Airworthiness ─────────────────────────────────────────────────────


class TestAirworthiness:
    def test_creates_valid(self):
        dados = AircraftEventFactory.airworthiness(
            matricula="PT-ABC",
            data_emissao="01/01/2024",
            data_validade="01/01/2025",
            numero_certificado="CVA-2024-001",
            orgao_emissor="ANAC",
        )
        assert dados["evento_tipo"] == "AIRWORTHINESS"
        assert dados["status"] == "ATIVA"


# ── Seguro ────────────────────────────────────────────────────────────


class TestSeguroAeronave:
    def test_creates_valid(self):
        dados = AircraftEventFactory.seguro(
            matricula="PT-ABC",
            seguradora_nome="Tokio Marine",
            seguradora_cnpj="61198164000123",
            apolice_numero="AP-AC-2024-001",
            data_inicio="01/01/2024",
            data_fim="01/01/2025",
            valor_segurado=500000.0,
        )
        assert dados["status"] == "ATIVA"


# ── Sinistro ──────────────────────────────────────────────────────────


class TestSinistroAeronave:
    def test_creates_valid(self):
        dados = AircraftEventFactory.sinistro(
            matricula="PT-ABC",
            data_sinistro="15/06/2024",
            tipo="POUSO_FORA_PISTA",
            descricao="Pouso de emergência",
            valor_dano=50000.0,
        )
        assert dados["evento_tipo"] == "SINISTRO"


# ── Baixa ─────────────────────────────────────────────────────────────


class TestBaixaAeronave:
    def test_creates_valid(self):
        dados = AircraftEventFactory.baixa(
            matricula="PT-ABC",
            data_baixa="01/01/2025",
            motivo="Sinistro perda total",
        )
        assert dados["evento_tipo"] == "BAIXA"


# ── Registro ──────────────────────────────────────────────────────────


class TestRegistroAeronave:
    def test_creates_valid(self):
        dados = AircraftEventFactory.registro(
            matricula="PT-ABC",
            nova_matricula="N12345",
            data_registro="01/06/2024",
            orgao="FAA",
        )
        assert dados["nova_matricula"] == "N12345"


# ── Mudança de Nome ───────────────────────────────────────────────────


class TestMudancaNomeAeronave:
    def test_creates_valid(self):
        dados = AircraftEventFactory.mudanca_nome(
            matricula="PT-ABC",
            nome_anterior="Velho Nome",
            nome_novo="Novo Nome",
            data_mudanca="01/06/2024",
        )
        assert dados["nome_novo"] == "Novo Nome"


# ── AircraftChain ─────────────────────────────────────────────────────


class TestAircraftChain:
    def _create_genesis_data(self):
        return AircraftEventFactory.fabricacao(
            uf="SP",
            cidade="Sao Paulo",
            matricula="PT-ABC",
            nome_aeronave="Cessna 172",
            fabricante="Cessna",
            modelo="172S",
            tipo_aeronave="AVIAO",
            ano_fabricacao=2020,
            peso_max_decolagem_kg=1111,
            motorizacao="PISTAO",
            num_motores=1,
            motor_potencia_cv=180,
        )

    def test_create_genesis(self):
        chain = AircraftChain(difficulty=1)
        dados = self._create_genesis_data()
        genesis = chain.create_genesis(dados)
        assert genesis.index == 0
        assert genesis.data["evento_tipo"] == "FABRICACAO"
        assert len(chain) == 1

    def test_get_matricula(self):
        chain = AircraftChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        assert chain.get_matricula() == "PTABC"

    def test_add_compra_venda(self):
        chain = AircraftChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        block = chain.add_event(
            "COMPRA_VENDA",
            AircraftEventFactory.compra_venda(
                matricula="PT-ABC",
                comprador_cpf="12345678901", comprador_nome="João",
                vendedor_cpf="98765432100", vendedor_nome="Maria",
                valor_transacao=500000.0, data_transacao="01/06/2024",
            ),
        )
        assert block.index == 1
        assert len(chain) == 2

    def test_get_estado_after_compra(self):
        chain = AircraftChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "COMPRA_VENDA",
            AircraftEventFactory.compra_venda(
                matricula="PT-ABC",
                comprador_cpf="12345678901", comprador_nome="João",
                vendedor_cpf="98765432100", vendedor_nome="Maria",
                valor_transacao=500000.0, data_transacao="01/06/2024",
            ),
        )
        estado = chain.get_estado_atual()
        assert len(estado["proprietarios"]) == 1
        assert estado["proprietarios"][0]["cpf"] == "12345678901"

    def test_get_estado_after_baixa(self):
        chain = AircraftChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "BAIXA",
            AircraftEventFactory.baixa(
                matricula="PT-ABC", data_baixa="01/01/2025", motivo="Sinistro",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["situacao"] == "BAIXADA"

    def test_get_estado_after_mudanca_nome(self):
        chain = AircraftChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "MUDANCA_NOME",
            AircraftEventFactory.mudanca_nome(
                matricula="PT-ABC", nome_anterior="Cessna 172",
                nome_novo="Minha Cessna", data_mudanca="01/06/2024",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["nome_aeronave"] == "Minha Cessna"

    def test_get_estado_after_airworthiness(self):
        chain = AircraftChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "AIRWORTHINESS",
            AircraftEventFactory.airworthiness(
                matricula="PT-ABC", data_emissao="01/01/2024",
                data_validade="01/01/2025", numero_certificado="CVA-001",
            ),
        )
        estado = chain.get_estado_atual()
        assert len(estado["airworthiness"]) == 1

    def test_validate_valid(self):
        chain = AircraftChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        ok, msg = chain.validate()
        assert ok
        assert "válida" in msg

    def test_validate_empty(self):
        chain = AircraftChain(difficulty=1)
        ok, msg = chain.validate()
        assert not ok

    def test_add_evento_sem_genesis(self):
        chain = AircraftChain(difficulty=1)
        with pytest.raises(ValueError, match="Cadeia vazia"):
            chain.add_event("COMPRA_VENDA", {})

    def test_historico_completo(self):
        chain = AircraftChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "REVISAO",
            AircraftEventFactory.revisao(matricula="PT-ABC", data_revisao="01/09/2024"),
        )
        historico = chain.get_historico_completo()
        assert len(historico) == 2


# ── AircraftChainProtector ────────────────────────────────────────────


class TestAircraftChainProtector:
    def test_allows_when_regular(self):
        assert AircraftChainProtector.pode_adicionar("COMPRA_VENDA", "REGULAR")

    def test_blocks_when_baixada(self):
        assert not AircraftChainProtector.pode_adicionar("COMPRA_VENDA", "BAIXADA")

    def test_allows_baixa_when_baixada(self):
        assert AircraftChainProtector.pode_adicionar("BAIXA", "BAIXADA")


# ── CrossChainAC ──────────────────────────────────────────────────────


class TestCrossChainAC:
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

    def _create_ac(self):
        chain = AircraftChain(difficulty=1)
        dados = AircraftEventFactory.fabricacao(
            uf="SP",
            cidade="Sao Paulo",
            matricula="PT-ABC", nome_aeronave="Cessna 172",
            fabricante="Cessna", modelo="172S", tipo_aeronave="AVIAO",
            ano_fabricacao=2020, peso_max_decolagem_kg=1111,
            motorizacao="PISTAO", num_motores=1, motor_potencia_cv=180,
        )
        chain.create_genesis(dados)
        return chain

    def test_create_reference(self):
        manager = CrossChainAC()
        pf = self._create_pf()
        ac = self._create_ac()
        manager.register_pf("12345678901", pf)
        manager.register_ac("PTABC", ac)

        ref = manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="AC", destino_id="PT-ABC",
            tipo_vinculo="PROPRIETARIO",
        )
        assert ref.entidade_origem_id == "12345678901"
        assert ref.entidade_destino_id == "PTABC"
        assert ref.ativo

    def test_get_aeronaves_da_pessoa(self):
        manager = CrossChainAC()
        pf = self._create_pf()
        ac = self._create_ac()
        manager.register_pf("12345678901", pf)
        manager.register_ac("PTABC", ac)
        manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="AC", destino_id="PT-ABC",
            tipo_vinculo="PROPRIETARIO",
        )
        result = manager.get_aeronaves_da_pessoa("12345678901")
        assert len(result) == 1
        assert result[0]["matricula"] == "PTABC"

    def test_stats(self):
        manager = CrossChainAC()
        pf = self._create_pf()
        ac = self._create_ac()
        manager.register_pf("12345678901", pf)
        manager.register_ac("PTABC", ac)
        manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="AC", destino_id="PT-ABC",
            tipo_vinculo="PROPRIETARIO",
        )
        stats = manager.stats()
        assert stats["total_cadeias_pf"] == 1
        assert stats["total_cadeias_ac"] == 1
        assert stats["referencias_ativas"] == 1
