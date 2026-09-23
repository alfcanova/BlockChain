"""Testes para blockchain_co — Blockchain de Empresas (CNPJ)"""

import pytest
from blockchain_co import (
    CompanyEventType,
    CompanyEventFactory,
    CompanyChainProtector,
    CompanyChain,
    CrossChainCO,
)


# ── EventType ─────────────────────────────────────────────────────────


class TestCompanyEventType:
    def test_all_types_exist(self):
        assert CompanyEventType.CONSTITUICAO.value == "CONSTITUICAO"
        assert CompanyEventType.ADICAO_SOCIO.value == "ADICAO_SOCIO"
        assert CompanyEventType.REMOCAO_SOCIO.value == "REMOCAO_SOCIO"
        assert CompanyEventType.MUDANCA_QUOTA.value == "MUDANCA_QUOTA"
        assert CompanyEventType.ALTERACAO_CONTRATUAL.value == "ALTERACAO_CONTRATUAL"
        assert CompanyEventType.MUDANCA_ENDERECO.value == "MUDANCA_ENDERECO"
        assert CompanyEventType.MUDANCA_CAPITAL.value == "MUDANCA_CAPITAL"
        assert CompanyEventType.FUSAO.value == "FUSAO"
        assert CompanyEventType.CISAO.value == "CISAO"
        assert CompanyEventType.INCORPORACAO.value == "INCORPORACAO"
        assert CompanyEventType.SUSPENSAO.value == "SUSPENSAO"
        assert CompanyEventType.REABERTURA.value == "REABERTURA"
        assert CompanyEventType.LIQUIDACAO.value == "LIQUIDACAO"
        assert CompanyEventType.BAIXA.value == "BAIXA"
        assert CompanyEventType.CERTIDAO.value == "CERTIDAO"
        assert CompanyEventType.GARANTIA.value == "GARANTIA"
        assert CompanyEventType.QUITACAO.value == "QUITACAO"

    def test_total_types(self):
        assert len(CompanyEventType) == 23


# ── Constituição (Gênesis) ────────────────────────────────────────────


class TestConstituicao:
    def test_creates_valid(self):
        dados = CompanyEventFactory.constituicao(

            uf="SP",
            cidade="Sao Paulo",            cnpj="12345678000190",
            razao_social="Empresa Teste LTDA",
            nome_fantasia="Teste",
            data_constituicao="01/01/2024",
            tipo_empresa="LTDA",
            porte="ME",
            capital_social=10000.0,
            natureza_juridica="2062",
            atividade_principal="6201501",
        )
        assert dados["evento_tipo"] == "CONSTITUICAO"
        assert dados["cnpj"] == "12345678000190"
        assert dados["razao_social"] == "Empresa Teste LTDA"
        assert dados["capital_social"] == 10000.0
        assert dados["situacao_cadastral"] == "ATIVA"

    def test_with_endereco(self):
        dados = CompanyEventFactory.constituicao(
            uf="SP",
            cidade="Sao Paulo",
            cnpj="12345678000190",
            razao_social="Empresa Teste",
            nome_fantasia="Teste",
            data_constituicao="01/01/2024",
            tipo_empresa="LTDA",
            porte="ME",
            capital_social=10000.0,
            natureza_juridica="2062",
            atividade_principal="6201501",
            endereco_sede={"logradouro": "Rua A, 100", "cidade": "SP", "uf": "SP"},
        )
        assert dados["endereco_sede"]["logradouro"] == "Rua A, 100"

    def test_invalid_cnpj_raises(self):
        with pytest.raises(ValueError, match="CNPJ inválido"):
            CompanyEventFactory.constituicao(
                uf="SP",
                cidade="Sao Paulo",
                cnpj="123", razao_social="Teste", nome_fantasia="T",
                data_constituicao="01/01/2024", tipo_empresa="LTDA",
                porte="ME", capital_social=10000, natureza_juridica="2062",
                atividade_principal="6201501",
            )

    def test_empty_razao_social_raises(self):
        with pytest.raises(ValueError, match="Razão social"):
            CompanyEventFactory.constituicao(
                uf="SP",
                cidade="Sao Paulo",
                cnpj="12345678000190", razao_social="", nome_fantasia="T",
                data_constituicao="01/01/2024", tipo_empresa="LTDA",
                porte="ME", capital_social=10000, natureza_juridica="2062",
                atividade_principal="6201501",
            )

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="Data inválida"):
            CompanyEventFactory.constituicao(
                uf="SP",
                cidade="Sao Paulo",
                cnpj="12345678000190", razao_social="Teste", nome_fantasia="T",
                data_constituicao="01-01-2024", tipo_empresa="LTDA",
                porte="ME", capital_social=10000, natureza_juridica="2062",
                atividade_principal="6201501",
            )

    def test_negative_capital_raises(self):
        with pytest.raises(ValueError, match="negativo"):
            CompanyEventFactory.constituicao(
                uf="SP",
                cidade="Sao Paulo",
                cnpj="12345678000190", razao_social="Teste", nome_fantasia="T",
                data_constituicao="01/01/2024", tipo_empresa="LTDA",
                porte="ME", capital_social=-100, natureza_juridica="2062",
                atividade_principal="6201501",
            )


# ── Adição de Sócio ──────────────────────────────────────────────────


class TestAdicaoSocio:
    def test_creates_valid(self):
        dados = CompanyEventFactory.adicao_socio(
            cnpj="12345678000190",
            socio_cpf="98765432100",
            socio_nome="Maria Santos",
            participacao=30.0,
            data_entrada="15/06/2024",
        )
        assert dados["evento_tipo"] == "ADICAO_SOCIO"
        assert dados["socio"]["cpf"] == "98765432100"
        assert dados["participacao"] == 30.0

    def test_invalid_cpf_raises(self):
        with pytest.raises(ValueError, match="CPF do sócio inválido"):
            CompanyEventFactory.adicao_socio(
                cnpj="12345678000190", socio_cpf="123",
                socio_nome="Maria", participacao=30.0,
                data_entrada="15/06/2024",
            )

    def test_invalid_participacao_raises(self):
        with pytest.raises(ValueError, match="Participação inválida"):
            CompanyEventFactory.adicao_socio(
                cnpj="12345678000190", socio_cpf="98765432100",
                socio_nome="Maria", participacao=150.0,
                data_entrada="15/06/2024",
            )


# ── Remoção de Sócio ─────────────────────────────────────────────────


class TestRemocaoSocio:
    def test_creates_valid(self):
        dados = CompanyEventFactory.remocao_socio(
            cnpj="12345678000190",
            socio_cpf="98765432100",
            socio_nome="Maria Santos",
            data_saida="01/01/2025",
            motivo="Saída voluntária",
        )
        assert dados["evento_tipo"] == "REMOCAO_SOCIO"
        assert dados["motivo"] == "Saída voluntária"


# ── Fusão ─────────────────────────────────────────────────────────────


class TestFusao:
    def test_creates_valid(self):
        dados = CompanyEventFactory.fusao(
            cnpj_origem="12345678000190",
            cnpj_destino="98765432000110",
            razao_social_nova="Fusionada S/A",
            cnpj_novo="11223344000155",
            data_fusao="01/01/2025",
        )
        assert dados["evento_tipo"] == "FUSAO"
        assert dados["razao_social_nova"] == "Fusionada S/A"


# ── Baixa ─────────────────────────────────────────────────────────────


class TestBaixa:
    def test_creates_valid(self):
        dados = CompanyEventFactory.baixa(
            cnpj="12345678000190",
            data_baixa="01/01/2025",
            motivo="Encerramento voluntário",
        )
        assert dados["evento_tipo"] == "BAIXA"


# ── Certidão ──────────────────────────────────────────────────────────


class TestCertidao:
    def test_creates_valid(self):
        dados = CompanyEventFactory.certidao(
            cnpj="12345678000190",
            tipo_certidao="NEGATIVA",
            numero="CERT-2024-001",
            data_emissao="01/06/2024",
            orgao_emissor="Receita Federal",
        )
        assert dados["evento_tipo"] == "CERTIDAO"
        assert dados["tipo_certidao"] == "NEGATIVA"


# ── Garantia ──────────────────────────────────────────────────────────


class TestGarantiaEmpresa:
    def test_creates_valid(self):
        dados = CompanyEventFactory.garantia(
            cnpj="12345678000190",
            credor_nome="Banco XYZ",
            credor_cnpj="98765432000110",
            valor_garantia=500000.0,
            data_garantia="01/01/2024",
            data_vencimento="01/01/2034",
        )
        assert dados["evento_tipo"] == "GARANTIA"
        assert dados["status"] == "ATIVA"

    def test_negative_valor_raises(self):
        with pytest.raises(ValueError, match="positivo"):
            CompanyEventFactory.garantia(
                cnpj="12345678000190", credor_nome="Banco",
                credor_cnpj="98765432000110", valor_garantia=-100,
                data_garantia="01/01/2024", data_vencimento="01/01/2034",
            )


# ── CompanyChain ─────────────────────────────────────────────────────


class TestCompanyChain:
    def _create_genesis_data(self):
        return CompanyEventFactory.constituicao(
            uf="SP",
            cidade="Sao Paulo",
            cnpj="12345678000190",
            razao_social="Empresa Teste LTDA",
            nome_fantasia="Teste",
            data_constituicao="01/01/2024",
            tipo_empresa="LTDA",
            porte="ME",
            capital_social=10000.0,
            natureza_juridica="2062",
            atividade_principal="6201501",
        )

    def test_create_genesis(self):
        chain = CompanyChain(difficulty=1)
        dados = self._create_genesis_data()
        genesis = chain.create_genesis(dados)
        assert genesis.index == 0
        assert genesis.data["evento_tipo"] == "CONSTITUICAO"
        assert len(chain) == 1

    def test_get_cnpj(self):
        chain = CompanyChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        assert chain.get_cnpj() == "12345678000190"

    def test_add_adicao_socio(self):
        chain = CompanyChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        block = chain.add_event(
            "ADICAO_SOCIO",
            CompanyEventFactory.adicao_socio(
                cnpj="12345678000190",
                socio_cpf="98765432100",
                socio_nome="Maria Santos",
                participacao=30.0,
                data_entrada="15/06/2024",
            ),
        )
        assert block.index == 1
        assert len(chain) == 2

    def test_get_estado_after_adicao_socio(self):
        chain = CompanyChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "ADICAO_SOCIO",
            CompanyEventFactory.adicao_socio(
                cnpj="12345678000190",
                socio_cpf="98765432100",
                socio_nome="Maria Santos",
                participacao=30.0,
                data_entrada="15/06/2024",
            ),
        )
        estado = chain.get_estado_atual()
        assert len(estado["socios"]) == 1
        assert estado["socios"][0]["cpf"] == "98765432100"

    def test_get_estado_after_remocao_socio(self):
        chain = CompanyChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "ADICAO_SOCIO",
            CompanyEventFactory.adicao_socio(
                cnpj="12345678000190",
                socio_cpf="98765432100",
                socio_nome="Maria Santos",
                participacao=30.0,
                data_entrada="15/06/2024",
            ),
        )
        chain.add_event(
            "REMOCAO_SOCIO",
            CompanyEventFactory.remocao_socio(
                cnpj="12345678000190",
                socio_cpf="98765432100",
                socio_nome="Maria Santos",
                data_saida="01/01/2025",
            ),
        )
        estado = chain.get_estado_atual()
        assert len(estado["socios"]) == 0

    def test_get_estado_after_mudanca_capital(self):
        chain = CompanyChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "MUDANCA_CAPITAL",
            CompanyEventFactory.mudanca_capital(
                cnpj="12345678000190",
                capital_anterior=10000.0,
                capital_novo=50000.0,
                data_mudanca="01/01/2025",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["capital_social"] == 50000.0

    def test_get_estado_after_suspensao(self):
        chain = CompanyChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "SUSPENSAO",
            CompanyEventFactory.suspensao(
                cnpj="12345678000190",
                data_suspensao="01/01/2025",
                motivo="Inatividade",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["situacao_cadastral"] == "SUSPENSA"

    def test_get_estado_after_baixa(self):
        chain = CompanyChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "BAIXA",
            CompanyEventFactory.baixa(
                cnpj="12345678000190",
                data_baixa="01/01/2025",
                motivo="Encerramento",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["situacao_cadastral"] == "BAIXADA"

    def test_validate_valid(self):
        chain = CompanyChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        ok, msg = chain.validate()
        assert ok
        assert "válida" in msg

    def test_validate_empty(self):
        chain = CompanyChain(difficulty=1)
        ok, msg = chain.validate()
        assert not ok
        assert "vazia" in msg

    def test_add_evento_sem_genesis(self):
        chain = CompanyChain(difficulty=1)
        with pytest.raises(ValueError, match="Cadeia vazia"):
            chain.add_event("ADICAO_SOCIO", {})

    def test_historico_completo(self):
        chain = CompanyChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "ADICAO_SOCIO",
            CompanyEventFactory.adicao_socio(
                cnpj="12345678000190",
                socio_cpf="98765432100",
                socio_nome="Maria Santos",
                participacao=30.0,
                data_entrada="15/06/2024",
            ),
        )
        historico = chain.get_historico_completo()
        assert len(historico) == 2
        assert historico[0]["tipo"] == "CONSTITUICAO"
        assert historico[1]["tipo"] == "ADICAO_SOCIO"


# ── CompanyChainProtector ─────────────────────────────────────────────


class TestCompanyChainProtector:
    def test_allows_when_ativa(self):
        assert CompanyChainProtector.pode_adicionar("ADICAO_SOCIO", "ATIVA")

    def test_blocks_when_baixada(self):
        assert not CompanyChainProtector.pode_adicionar("ADICAO_SOCIO", "BAIXADA")

    def test_allows_certidao_when_baixada(self):
        assert CompanyChainProtector.pode_adicionar("CERTIDAO", "BAIXADA")


# ── CrossChainCO ──────────────────────────────────────────────────────


class TestCrossChainCO:
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

    def _create_co(self):
        chain = CompanyChain(difficulty=1)
        dados = CompanyEventFactory.constituicao(
            uf="SP",
            cidade="Sao Paulo",
            cnpj="12345678000190", razao_social="Empresa Teste",
            nome_fantasia="Teste", data_constituicao="01/01/2024",
            tipo_empresa="LTDA", porte="ME", capital_social=10000,
            natureza_juridica="2062", atividade_principal="6201501",
        )
        chain.create_genesis(dados)
        return chain

    def test_create_reference(self):
        manager = CrossChainCO()
        pf = self._create_pf()
        co = self._create_co()
        manager.register_pf("12345678901", pf)
        manager.register_co("12345678000190", co)

        ref = manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="CO", destino_id="12345678000190",
            tipo_vinculo="SOCIO",
        )
        assert ref.entidade_origem_id == "12345678901"
        assert ref.entidade_destino_id == "12345678000190"
        assert ref.ativo

    def test_get_empresas_da_pessoa(self):
        manager = CrossChainCO()
        pf = self._create_pf()
        co = self._create_co()
        manager.register_pf("12345678901", pf)
        manager.register_co("12345678000190", co)
        manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="CO", destino_id="12345678000190",
            tipo_vinculo="SOCIO",
        )
        empresas = manager.get_empresas_da_pessoa("12345678901")
        assert len(empresas) == 1
        assert empresas[0]["cnpj"] == "12345678000190"

    def test_stats(self):
        manager = CrossChainCO()
        pf = self._create_pf()
        co = self._create_co()
        manager.register_pf("12345678901", pf)
        manager.register_co("12345678000190", co)
        manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="CO", destino_id="12345678000190",
            tipo_vinculo="SOCIO",
        )
        stats = manager.stats()
        assert stats["total_cadeias_pf"] == 1
        assert stats["total_cadeias_co"] == 1
        assert stats["referencias_ativas"] == 1
