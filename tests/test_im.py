"""Testes para blockchain_im — Blockchain de Imóveis"""

import pytest
from blockchain_im import (
    PropertyEventType,
    PropertyEventFactory,
    PropertyChainProtector,
    PropertyChain,
    CrossChainManager,
)


# ── EventType ─────────────────────────────────────────────────────────

class TestPropertyEventType:
    def test_all_types_exist(self):
        assert PropertyEventType.TERRENO.value == "TERRENO"
        assert PropertyEventType.CONSTRUCAO.value == "CONSTRUCAO"
        assert PropertyEventType.DEMOLICAO.value == "DEMOLICAO"
        assert PropertyEventType.REFORMA.value == "REFORMA"
        assert PropertyEventType.LOTEAMENTO.value == "LOTEAMENTO"
        assert PropertyEventType.DESMEMBRAMENTO.value == "DESMEMBRAMENTO"
        assert PropertyEventType.FUSAO.value == "FUSAO"
        assert PropertyEventType.COMPRA_VENDA.value == "COMPRA_VENDA"
        assert PropertyEventType.DOACAO.value == "DOACAO"
        assert PropertyEventType.HERANCA.value == "HERANCA"
        assert PropertyEventType.PERMUTA.value == "PERMUTA"
        assert PropertyEventType.CONFISCO.value == "CONFISCO"
        assert PropertyEventType.GARANTIA.value == "GARANTIA"
        assert PropertyEventType.QUITACAO.value == "QUITACAO"
        assert PropertyEventType.LEILAO.value == "LEILAO"
        assert PropertyEventType.PENHORA.value == "PENHORA"
        assert PropertyEventType.MATRICULA.value == "MATRICULA"
        assert PropertyEventType.CERTIDAO.value == "CERTIDAO"
        assert PropertyEventType.IPTU.value == "IPTU"
        assert PropertyEventType.ZONEAMENTO.value == "ZONEAMENTO"
        assert PropertyEventType.PROPRIETARIO.value == "PROPRIETARIO"
        assert PropertyEventType.GARANTIA_PESSOA.value == "GARANTIA_PESSOA"

    def test_total_types(self):
        assert len(PropertyEventType) == 22


# ── Terreno (Gênesis) ─────────────────────────────────────────────────

class TestTerreno:
    def test_creates_valid_terreno(self):
        dados = PropertyEventFactory.terreno(
            matricula="12345",
            endereco_logradouro="Rua das Flores, 123",
            endereco_bairro="Jardim Primavera",
            endereco_cidade="São Paulo",
            endereco_uf="SP",
            endereco_cep="01234-567",
            lat=-23.5505,
            lon=-46.6333,
            area_terreno_m2=500.0,
        )
        assert dados["evento_tipo"] == "TERRENO"
        assert dados["matricula"] == "12345"
        assert dados["area_terreno_m2"] == 500.0
        assert dados["coordenadas"]["lat"] == -23.5505
        assert dados["situacao"] == "LIVRE"

    def test_with_proprietarios(self):
        dados = PropertyEventFactory.terreno(
            matricula="12345",
            endereco_logradouro="Rua das Flores, 123",
            endereco_bairro="Jardim Primavera",
            endereco_cidade="São Paulo",
            endereco_uf="SP",
            endereco_cep="01234-567",
            lat=-23.5505,
            lon=-46.6333,
            area_terreno_m2=500.0,
            proprietarios=[{
                "cpf": "12345678901",
                "nome": "João da Silva",
                "participacao": 100.0,
            }],
        )
        assert len(dados["proprietarios"]) == 1
        assert dados["proprietarios"][0]["cpf"] == "12345678901"

    def test_empty_matricula_raises(self):
        with pytest.raises(ValueError, match="Matrícula"):
            PropertyEventFactory.terreno(
                matricula="",
                endereco_logradouro="Rua das Flores",
                endereco_bairro="Centro",
                endereco_cidade="Sao Paulo",
                endereco_uf="SP",
                endereco_cep="00000-000",
                lat=0.0, lon=0.0,
                area_terreno_m2=100.0,
            )

    def test_invalid_uf_raises(self):
        with pytest.raises(ValueError, match="UF"):
            PropertyEventFactory.terreno(
                matricula="12345",
                endereco_logradouro="Rua das Flores",
                endereco_bairro="Centro",
                endereco_cidade="Sao Paulo",
                endereco_uf="XX",
                endereco_cep="00000-000",
                lat=0.0, lon=0.0,
                area_terreno_m2=100.0,
            )

    def test_invalid_coordenadas_raises(self):
        with pytest.raises(ValueError, match="Coordenadas"):
            PropertyEventFactory.terreno(
                matricula="12345",
                endereco_logradouro="Rua das Flores",
                endereco_bairro="Centro",
                endereco_cidade="Sao Paulo",
                endereco_uf="SP",
                endereco_cep="00000-000",
                lat=100.0, lon=0.0,
                area_terreno_m2=100.0,
            )

    def test_invalid_area_raises(self):
        with pytest.raises(ValueError, match="Área"):
            PropertyEventFactory.terreno(
                matricula="12345",
                endereco_logradouro="Rua das Flores",
                endereco_bairro="Centro",
                endereco_cidade="Sao Paulo",
                endereco_uf="SP",
                endereco_cep="00000-000",
                lat=0.0, lon=0.0,
                area_terreno_m2=-100.0,
            )


# ── Construção ────────────────────────────────────────────────────────

class TestConstrucao:
    def test_creates_valid_construcao(self):
        dados = PropertyEventFactory.construcao(
            matricula="12345",
            descricao="Casa de 2 pavimentos",
            area_construida_m2=150.0,
        )
        assert dados["evento_tipo"] == "CONSTRUCAO"
        assert dados["area_construida_m2"] == 150.0
        assert dados["situacao_obra"] == "EM_OBRA"

    def test_with_dates(self):
        dados = PropertyEventFactory.construcao(
            matricula="12345",
            descricao="Edifício comercial",
            area_construida_m2=500.0,
            tipo_construcao="COMERCIAL",
            pavimentos=4,
            data_inicio="01/01/2023",
            data_fim="31/12/2023",
        )
        assert dados["tipo_construcao"] == "COMERCIAL"
        assert dados["pavimentos"] == 4
        assert dados["situacao_obra"] == "CONCLUIDA"

    def test_empty_matricula_raises(self):
        with pytest.raises(ValueError):
            PropertyEventFactory.construcao(
                matricula="", descricao="Casa", area_construida_m2=100.0,
            )

    def test_invalid_area_raises(self):
        with pytest.raises(ValueError, match="Área"):
            PropertyEventFactory.construcao(
                matricula="12345", descricao="Casa", area_construida_m2=-10.0,
            )


# ── Demolição ─────────────────────────────────────────────────────────

class TestDemolicao:
    def test_creates_valid_demolicao(self):
        dados = PropertyEventFactory.demolicao(
            matricula="12345",
            descricao="Demolição da edificação antiga",
            area_demolida_m2=80.0,
        )
        assert dados["evento_tipo"] == "DEMOLICAO"
        assert dados["area_demolida_m2"] == 80.0

    def test_invalid_area_raises(self):
        with pytest.raises(ValueError, match="Área"):
            PropertyEventFactory.demolicao(
                matricula="12345", descricao="Teste", area_demolida_m2=0,
            )


# ── Reforma ───────────────────────────────────────────────────────────

class TestReforma:
    def test_ampliacao(self):
        dados = PropertyEventFactory.reforma(
            matricula="12345",
            descricao="Ampliação da garagem",
            tipo="AMPLIACAO",
            area_anterior_m2=100.0,
            area_nova_m2=130.0,
        )
        assert dados["tipo"] == "AMPLIACAO"
        assert dados["delta_area_m2"] == 30.0

    def test_reducao(self):
        dados = PropertyEventFactory.reforma(
            matricula="12345",
            descricao="Redução de área",
            tipo="REDUCAO",
            area_anterior_m2=130.0,
            area_nova_m2=100.0,
        )
        assert dados["tipo"] == "REDUCAO"
        assert dados["delta_area_m2"] == -30.0

    def test_invalid_tipo_raises(self):
        with pytest.raises(ValueError, match="Tipo"):
            PropertyEventFactory.reforma(
                matricula="12345", descricao="Teste",
                tipo="INVALIDO", area_anterior_m2=100.0, area_nova_m2=120.0,
            )


# ── Desmembramento ────────────────────────────────────────────────────

class TestDesmembramento:
    def test_creates_valid(self):
        dados = PropertyEventFactory.desmembramento(
            matricula_origem="12345",
            novas_matriculas=[
                {"matricula": "12345-1", "area_m2": 250.0},
                {"matricula": "12345-2", "area_m2": 250.0},
            ],
            area_total_anterior=500.0,
        )
        assert dados["quantidade_lotes"] == 2
        assert dados["area_total_nova_m2"] == 500.0

    def test_empty_novas_matriculas_raises(self):
        with pytest.raises(ValueError):
            PropertyEventFactory.desmembramento(
                matricula_origem="12345",
                novas_matriculas=[],
                area_total_anterior=500.0,
            )


# ── Fusão ─────────────────────────────────────────────────────────────

class TestFusao:
    def test_creates_valid(self):
        dados = PropertyEventFactory.fusao(
            matriculas_origem=["12345", "12346"],
            nova_matricula="12347",
            area_total_m2=1000.0,
        )
        assert dados["quantidade_imoveis"] == 2
        assert dados["nova_matricula"] == "12347"

    def test_less_than_two_raises(self):
        with pytest.raises(ValueError, match="pelo menos 2"):
            PropertyEventFactory.fusao(
                matriculas_origem=["12345"],
                nova_matricula="12346",
                area_total_m2=500.0,
            )


# ── Compra/Venda ──────────────────────────────────────────────────────

class TestCompraVenda:
    def test_creates_valid(self):
        dados = PropertyEventFactory.compra_venda(
            matricula="12345",
            comprador_cpf="12345678901",
            comprador_nome="João da Silva",
            vendedor_cpf="98765432100",
            vendedor_nome="Maria Souza",
            valor_transacao=350000.00,
            data_transacao="15/03/2025",
        )
        assert dados["evento_tipo"] == "COMPRA_VENDA"
        assert dados["valor_transacao"] == 350000.00
        assert dados["comprador"]["cpf"] == "12345678901"
        assert dados["vendedor"]["cpf"] == "98765432100"

    def test_invalid_comprador_cpf_raises(self):
        with pytest.raises(ValueError, match="comprador"):
            PropertyEventFactory.compra_venda(
                matricula="12345",
                comprador_cpf="123",
                comprador_nome="João",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria",
                valor_transacao=100.0,
                data_transacao="15/03/2025",
            )

    def test_negative_valor_raises(self):
        with pytest.raises(ValueError, match="negativo"):
            PropertyEventFactory.compra_venda(
                matricula="12345",
                comprador_cpf="12345678901",
                comprador_nome="João",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria",
                valor_transacao=-100.0,
                data_transacao="15/03/2025",
            )


# ── Doação ────────────────────────────────────────────────────────────

class TestDoacao:
    def test_creates_valid(self):
        dados = PropertyEventFactory.doacao(
            matricula="12345",
            donatario_cpf="12345678901",
            donatario_nome="Filho",
            doador_cpf="98765432100",
            doador_nome="Pai",
            data_doacao="10/06/2024",
        )
        assert dados["evento_tipo"] == "DOACAO"
        assert dados["donatario"]["cpf"] == "12345678901"


# ── Herança ───────────────────────────────────────────────────────────

class TestHeranca:
    def test_creates_valid(self):
        dados = PropertyEventFactory.heranca(
            matricula="12345",
            inventariado_cpf="12345678901",
            inventariado_nome="Falecido",
            herdeiros=[
                {"cpf": "98765432100", "nome": "Herdeiro 1", "participacao": 50.0},
                {"cpf": "11223344556", "nome": "Herdeiro 2", "participacao": 50.0},
            ],
            data_obito="01/01/2024",
        )
        assert dados["evento_tipo"] == "HERANCA"
        assert len(dados["herdeiros"]) == 2

    def test_empty_herdeiros_raises(self):
        with pytest.raises(ValueError, match="herdeiro"):
            PropertyEventFactory.heranca(
                matricula="12345",
                inventariado_cpf="12345678901",
                inventariado_nome="Falecido",
                herdeiros=[],
                data_obito="01/01/2024",
            )


# ── Garantia ──────────────────────────────────────────────────────────

class TestGarantia:
    def test_creates_valid(self):
        dados = PropertyEventFactory.garantia(
            matricula="12345",
            credor_nome="Banco XYZ",
            credor_cnpj="12345678000190",
            valor_garantia=200000.0,
            data_garantia="01/01/2024",
            data_vencimento="01/01/2034",
        )
        assert dados["evento_tipo"] == "GARANTIA"
        assert dados["status"] == "ATIVA"
        assert dados["credor"]["nome"] == "Banco XYZ"

    def test_negative_valor_raises(self):
        with pytest.raises(ValueError, match="positivo"):
            PropertyEventFactory.garantia(
                matricula="12345",
                credor_nome="Banco",
                credor_cnpj="00000000000000",
                valor_garantia=-100.0,
                data_garantia="01/01/2024",
                data_vencimento="01/01/2034",
            )


# ── Quitação ──────────────────────────────────────────────────────────

class TestQuitacao:
    def test_creates_valid(self):
        dados = PropertyEventFactory.quitacao(
            matricula="12345",
            garantia_index=0,
            data_quitacao="15/06/2024",
            valor_pago=200000.0,
        )
        assert dados["evento_tipo"] == "QUITACAO"
        assert dados["garantia_index"] == 0


# ── Leilão ────────────────────────────────────────────────────────────

class TestLeilao:
    def test_creates_valid(self):
        dados = PropertyEventFactory.leilao(
            matricula="12345",
            data_leilao="01/12/2024",
            valor_minimo=100000.0,
            lance_vencedor=150000.0,
            vencedor_cpf="12345678901",
            vencedor_nome="Comprador",
        )
        assert dados["evento_tipo"] == "LEILAO"
        assert dados["status"] == "CONCLUIDO"
        assert dados["lance_vencedor"] == 150000.0

    def test_sem_lance(self):
        dados = PropertyEventFactory.leilao(
            matricula="12345",
            data_leilao="01/12/2024",
            valor_minimo=100000.0,
        )
        assert dados["status"] == "AGUARDANDO"


# ── Confisco ──────────────────────────────────────────────────────────

class TestConfisco:
    def test_creates_valid(self):
        dados = PropertyEventFactory.confisco(
            matricula="12345",
            autoridade="Justiça Federal",
            processo_numero="001-2024",
            data_confisco="15/03/2024",
        )
        assert dados["evento_tipo"] == "CONFISCO"


# ── PropertyChain ─────────────────────────────────────────────────────

class TestPropertyChain:
    def _create_terreno_data(self):
        return PropertyEventFactory.terreno(
            matricula="12345",
            endereco_logradouro="Rua das Flores, 123",
            endereco_bairro="Centro",
            endereco_cidade="São Paulo",
            endereco_uf="SP",
            endereco_cep="01234-567",
            lat=-23.5505,
            lon=-46.6333,
            area_terreno_m2=500.0,
        )

    def test_create_genesis(self):
        chain = PropertyChain(difficulty=1)
        dados = self._create_terreno_data()
        genesis = chain.create_genesis(dados)
        assert genesis.index == 0
        assert genesis.data["evento_tipo"] == "TERRENO"
        assert len(chain) == 1

    def test_add_construcao(self):
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(self._create_terreno_data())
        block = chain.add_event(
            "CONSTRUCAO",
            PropertyEventFactory.construcao(
                matricula="12345",
                descricao="Casa",
                area_construida_m2=150.0,
            ),
        )
        assert block.index == 1
        assert len(chain) == 2

    def test_add_compra_venda(self):
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(self._create_terreno_data())
        block = chain.add_event(
            "COMPRA_VENDA",
            PropertyEventFactory.compra_venda(
                matricula="12345",
                comprador_cpf="12345678901",
                comprador_nome="João",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria",
                valor_transacao=350000.0,
                data_transacao="15/03/2025",
            ),
        )
        assert block.index == 1

    def test_get_estado_atual(self):
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(self._create_terreno_data())
        estado = chain.get_estado_atual()
        assert estado["matricula"] == "12345"
        assert estado["situacao"] == "LIVRE"
        assert estado["area_terreno_m2"] == 500.0

    def test_get_estado_after_construcao(self):
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(self._create_terreno_data())
        chain.add_event(
            "CONSTRUCAO",
            PropertyEventFactory.construcao(
                matricula="12345", descricao="Casa", area_construida_m2=150.0,
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["area_construida_m2"] == 150.0
        assert estado["situacao"] == "CONSTRUIDO"

    def test_get_estado_after_demolicao(self):
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(self._create_terreno_data())
        chain.add_event(
            "CONSTRUCAO",
            PropertyEventFactory.construcao(
                matricula="12345", descricao="Casa", area_construida_m2=150.0,
            ),
        )
        chain.add_event(
            "DEMOLICAO",
            PropertyEventFactory.demolicao(
                matricula="12345", descricao="Demolição", area_demolida_m2=150.0,
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["area_construida_m2"] == 0
        assert estado["situacao"] == "LIVRE"

    def test_validate_valid_chain(self):
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(self._create_terreno_data())
        ok, msg = chain.validate()
        assert ok
        assert "válida" in msg

    def test_validate_empty_chain(self):
        chain = PropertyChain(difficulty=1)
        ok, msg = chain.validate()
        assert not ok
        assert "vazia" in msg

    def test_get_matricula(self):
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(self._create_terreno_data())
        assert chain.get_matricula() == "12345"

    def test_get_historico(self):
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(self._create_terreno_data())
        chain.add_event(
            "CONSTRUCAO",
            PropertyEventFactory.construcao(
                matricula="12345", descricao="Casa", area_construida_m2=150.0,
            ),
        )
        historico = chain.get_historico_completo()
        assert len(historico) == 2
        assert historico[0]["tipo"] == "TERRENO"
        assert historico[1]["tipo"] == "CONSTRUCAO"

    def test_get_fluxo_financeiro(self):
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(self._create_terreno_data())
        chain.add_event(
            "COMPRA_VENDA",
            PropertyEventFactory.compra_venda(
                matricula="12345",
                comprador_cpf="12345678901",
                comprador_nome="João",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria",
                valor_transacao=350000.0,
                data_transacao="15/03/2025",
            ),
        )
        fluxo = chain.get_fluxo_financeiro()
        assert len(fluxo) == 1
        assert fluxo[0]["valor"] == 350000.0


# ── PropertyChainProtector ────────────────────────────────────────────

class TestPropertyChainProtector:
    def test_allows_events_on_livre(self):
        assert PropertyChainProtector.pode_adicionar("CONSTRUCAO", "LIVRE")
        assert PropertyChainProtector.pode_adicionar("COMPRA_VENDA", "LIVRE")

    def test_blocks_on_confiscado(self):
        assert not PropertyChainProtector.pode_adicionar("CONSTRUCAO", "CONFISCADO")
        assert not PropertyChainProtector.pode_adicionar("COMPRA_VENDA", "CONFISCADO")
        assert PropertyChainProtector.pode_adicionar("CERTIDAO", "CONFISCADO")
        assert PropertyChainProtector.pode_adicionar("ZONEAMENTO", "CONFISCADO")


# ── CrossChainManager ────────────────────────────────────────────────

class TestCrossChainManager:
    def _create_chain_pf(self):
        from blockchain_pf import Blockchain, EventFactory
        chain = Blockchain(difficulty=1)
        dados = EventFactory.nascimento(
            cpf="12345678901",
            nome_completo="João da Silva",
            data_nascimento="15/03/1990",
            sexo="M",
            cidade_nascimento="São Paulo",
            uf_nascimento="SP",
            nome_mae="Maria da Silva",
        )
        chain.create_genesis(dados)
        return chain

    def _create_chain_im(self):
        dados = PropertyEventFactory.terreno(
            matricula="12345",
            endereco_logradouro="Rua das Flores, 123",
            endereco_bairro="Centro",
            endereco_cidade="São Paulo",
            endereco_uf="SP",
            endereco_cep="01234-567",
            lat=-23.5505,
            lon=-46.6333,
            area_terreno_m2=500.0,
        )
        chain = PropertyChain(difficulty=1)
        chain.create_genesis(dados)
        return chain

    def test_register_and_validate(self):
        manager = CrossChainManager()
        pf = self._create_chain_pf()
        im = self._create_chain_im()
        manager.register_pf("12345678901", pf)
        manager.register_im("12345", im)

        ok, msg = manager.validate_cross_reference("12345678901", "12345")
        assert ok
        assert "válida" in msg

    def test_invalid_pf(self):
        manager = CrossChainManager()
        ok, msg = manager.validate_cross_reference("00000000000", "12345")
        assert not ok

    def test_invalid_im(self):
        manager = CrossChainManager()
        ok, msg = manager.validate_cross_reference("12345678901", "99999")
        assert not ok

    def test_create_reference(self):
        manager = CrossChainManager()
        pf = self._create_chain_pf()
        im = self._create_chain_im()
        manager.register_pf("12345678901", pf)
        manager.register_im("12345", im)

        ref = manager.create_reference(
            cpf="12345678901",
            matricula="12345",
            tipo_vinculo="PROPRIETARIO",
        )
        assert ref.cpf == "12345678901"
        assert ref.matricula == "12345"
        assert ref.ativo

    def test_get_imoveis_da_pessoa(self):
        manager = CrossChainManager()
        pf = self._create_chain_pf()
        im = self._create_chain_im()
        manager.register_pf("12345678901", pf)
        manager.register_im("12345", im)
        manager.create_reference("12345678901", "12345", "PROPRIETARIO")

        imoveis = manager.get_imoveis_da_pessoa("12345678901")
        assert len(imoveis) == 1
        assert imoveis[0]["matricula"] == "12345"

    def test_get_pessoas_do_imovel(self):
        manager = CrossChainManager()
        pf = self._create_chain_pf()
        im = self._create_chain_im()
        manager.register_pf("12345678901", pf)
        manager.register_im("12345", im)
        manager.create_reference("12345678901", "12345", "PROPRIETARIO")

        pessoas = manager.get_pessoas_do_imovel("12345")
        assert len(pessoas) == 1
        assert pessoas[0]["cpf"] == "12345678901"

    def test_stats(self):
        manager = CrossChainManager()
        pf = self._create_chain_pf()
        im = self._create_chain_im()
        manager.register_pf("12345678901", pf)
        manager.register_im("12345", im)
        manager.create_reference("12345678901", "12345", "PROPRIETARIO")

        stats = manager.stats()
        assert stats["total_cadeias_pf"] == 1
        assert stats["total_cadeias_im"] == 1
        assert stats["referencias_ativas"] == 1
