"""Testes para blockchain_an — Blockchain de Animais"""

import pytest
from blockchain_an import (
    AnimalEventType,
    AnimalEventFactory,
    AnimalChainProtector,
    AnimalChain,
    CrossChainAN,
)


# ── EventType ─────────────────────────────────────────────────────────


class TestAnimalEventType:
    def test_all_types_exist(self):
        assert AnimalEventType.NASCIMENTO.value == "NASCIMENTO"
        assert AnimalEventType.COMPRA_VENDA.value == "COMPRA_VENDA"
        assert AnimalEventType.DOACAO.value == "DOACAO"
        assert AnimalEventType.ADOCAO.value == "ADOCAO"
        assert AnimalEventType.VACINACAO.value == "VACINACAO"
        assert AnimalEventType.CASTRACAO.value == "CASTRACAO"
        assert AnimalEventType.TRATAMENTO.value == "TRATAMENTO"
        assert AnimalEventType.MICROCHIP.value == "MICROCHIP"
        assert AnimalEventType.LICENCA.value == "LICENCA"
        assert AnimalEventType.MUDANCA_NOME.value == "MUDANCA_NOME"
        assert AnimalEventType.OBITO.value == "OBITO"
        assert AnimalEventType.PERDA_TOTAL.value == "PERDA_TOTAL"
        assert AnimalEventType.CERTIDAO.value == "CERTIDAO"

    def test_total_types(self):
        assert len(AnimalEventType) == 20


# ── Nascimento (Gênesis) ──────────────────────────────────────────────


class TestNascimento:
    def test_creates_valid(self):
        dados = AnimalEventFactory.nascimento(

            uf="SP",
            cidade="Sao Paulo",            nome="Rex",
            especie="CAO",
            raca="Labrador",
            sexo="M",
            data_nascimento="15/03/2024",
            cor="Dourado",
            peso_kg=5.0,
            proprietario_cpf="12345678901",
            proprietario_nome="João Silva",
        )
        assert dados["evento_tipo"] == "NASCIMENTO"
        assert dados["nome"] == "Rex"
        assert dados["especie"] == "CAO"
        assert dados["situacao"] == "VIVO"
        assert dados["proprietario"]["cpf"] == "12345678901"

    def test_empty_nome_raises(self):
        with pytest.raises(ValueError, match="Nome"):
            AnimalEventFactory.nascimento(
                uf="SP",
                cidade="Sao Paulo",
                nome="", especie="CAO", raca="Labrador",
                sexo="M", data_nascimento="15/03/2024",
                cor="Dourado", peso_kg=5.0,
                proprietario_cpf="12345678901",
                proprietario_nome="João",
            )

    def test_empty_especie_raises(self):
        with pytest.raises(ValueError, match="Espécie"):
            AnimalEventFactory.nascimento(
                uf="SP",
                cidade="Sao Paulo",
                nome="Rex", especie="", raca="Labrador",
                sexo="M", data_nascimento="15/03/2024",
                cor="Dourado", peso_kg=5.0,
                proprietario_cpf="12345678901",
                proprietario_nome="João",
            )

    def test_invalid_sexo_raises(self):
        with pytest.raises(ValueError, match="Sexo inválido"):
            AnimalEventFactory.nascimento(
                uf="SP",
                cidade="Sao Paulo",
                nome="Rex", especie="CAO", raca="Labrador",
                sexo="X", data_nascimento="15/03/2024",
                cor="Dourado", peso_kg=5.0,
                proprietario_cpf="12345678901",
                proprietario_nome="João",
            )

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="Data inválida"):
            AnimalEventFactory.nascimento(
                uf="SP",
                cidade="Sao Paulo",
                nome="Rex", especie="CAO", raca="Labrador",
                sexo="M", data_nascimento="15-03-2024",
                cor="Dourado", peso_kg=5.0,
                proprietario_cpf="12345678901",
                proprietario_nome="João",
            )

    def test_negative_peso_raises(self):
        with pytest.raises(ValueError, match="negativo"):
            AnimalEventFactory.nascimento(
                uf="SP",
                cidade="Sao Paulo",
                nome="Rex", especie="CAO", raca="Labrador",
                sexo="M", data_nascimento="15/03/2024",
                cor="Dourado", peso_kg=-1.0,
                proprietario_cpf="12345678901",
                proprietario_nome="João",
            )


# ── Compra/Venda ──────────────────────────────────────────────────────


class TestCompraVendaAnimal:
    def test_creates_valid(self):
        dados = AnimalEventFactory.compra_venda(
            nome="Rex",
            comprador_cpf="12345678901", comprador_nome="João",
            vendedor_cpf="98765432100", vendedor_nome="Maria",
            valor_transacao=2000.0,
            data_transacao="01/06/2024",
        )
        assert dados["evento_tipo"] == "COMPRA_VENDA"
        assert dados["valor_transacao"] == 2000.0

    def test_negative_valor_raises(self):
        with pytest.raises(ValueError, match="negativo"):
            AnimalEventFactory.compra_venda(
                nome="Rex",
                comprador_cpf="12345678901", comprador_nome="João",
                vendedor_cpf="98765432100", vendedor_nome="Maria",
                valor_transacao=-100.0, data_transacao="01/06/2024",
            )


# ── Doação ────────────────────────────────────────────────────────────


class TestDoacaoAnimal:
    def test_creates_valid(self):
        dados = AnimalEventFactory.doacao(
            donatario_cpf="12345678901", donatario_nome="João",
            doador_cpf="98765432100", doador_nome="Maria",
            data_doacao="01/06/2024",
            motivo="Mudança",
        )
        assert dados["evento_tipo"] == "DOACAO"


# ── Adoção ────────────────────────────────────────────────────────────


class TestAdocaoAnimal:
    def test_creates_valid(self):
        dados = AnimalEventFactory.adocao(
            adotante_cpf="12345678901", adotante_nome="João",
            data_adocao="01/06/2024",
            origem="ABRIGO",
        )
        assert dados["evento_tipo"] == "ADOCAO"
        assert dados["origem"] == "ABRIGO"


# ── Vacinação ─────────────────────────────────────────────────────────


class TestVacinacao:
    def test_creates_valid(self):
        dados = AnimalEventFactory.vacinacao(
            nome_vacina="Raiva",
            data_vacinacao="01/04/2024",
            lote="LOT-001",
            fabricante="Zoetis",
            dose="1a dose",
        )
        assert dados["evento_tipo"] == "VACINACAO"
        assert dados["nome_vacina"] == "Raiva"

    def test_empty_vacina_raises(self):
        with pytest.raises(ValueError, match="Nome da vacina"):
            AnimalEventFactory.vacinacao(
                nome_vacina="", data_vacinacao="01/04/2024",
            )


# ── Castração ─────────────────────────────────────────────────────────


class TestCastracao:
    def test_creates_valid(self):
        dados = AnimalEventFactory.castracao(
            data_castracao="01/06/2024",
            veterinario_cpf="12345678901",
            veterinario_nome="Dr. Silva",
            clinica="PetClinic",
            metodo="Cirúrgico",
        )
        assert dados["evento_tipo"] == "CASTRACAO"
        assert dados["metodo"] == "Cirúrgico"


# ── Tratamento ────────────────────────────────────────────────────────


class TestTratamento:
    def test_creates_valid(self):
        dados = AnimalEventFactory.tratamento(
            data_inicio="01/06/2024",
            data_fim="15/06/2024",
            diagnostico="Otite",
            veterinario_cpf="12345678901",
            veterinario_nome="Dr. Silva",
            clinica="PetClinic",
            medicamentos=["Antibiótico", "Anti-inflamatório"],
            valor=500.0,
        )
        assert dados["evento_tipo"] == "TRATAMENTO"
        assert dados["valor"] == 500.0
        assert len(dados["medicamentos"]) == 2


# ── Microchip ─────────────────────────────────────────────────────────


class TestMicrochip:
    def test_creates_valid(self):
        dados = AnimalEventFactory.microchip(
            numero_microchip="900123456789012",
            data_implantacao="01/06/2024",
            fabricante="HomeAgain",
        )
        assert dados["evento_tipo"] == "MICROCHIP"
        assert dados["numero_microchip"] == "900123456789012"

    def test_empty_microchip_raises(self):
        with pytest.raises(ValueError, match="microchip"):
            AnimalEventFactory.microchip(
                numero_microchip="", data_implantacao="01/06/2024",
            )


# ── Licença ───────────────────────────────────────────────────────────


class TestLicenca:
    def test_creates_valid(self):
        dados = AnimalEventFactory.licenca(
            numero_licenca="LIC-2024-001",
            data_emissao="01/01/2024",
            data_validade="01/01/2025",
            orgao_emissor="Prefeitura de SP",
        )
        assert dados["evento_tipo"] == "LICENCA"


# ── Mudança de Nome ───────────────────────────────────────────────────


class TestMudancaNomeAnimal:
    def test_creates_valid(self):
        dados = AnimalEventFactory.mudanca_nome(
            nome_anterior="Rex",
            nome_novo="Thor",
            data_mudanca="01/06/2024",
        )
        assert dados["nome_novo"] == "Thor"


# ── Óbito ─────────────────────────────────────────────────────────────


class TestObitoAnimal:
    def test_creates_valid(self):
        dados = AnimalEventFactory.obito(
            data_obito="01/06/2024",
            causa="Velhice",
            veterinario_cpf="12345678901",
            veterinario_nome="Dr. Silva",
        )
        assert dados["evento_tipo"] == "OBITO"


# ── Certidão ──────────────────────────────────────────────────────────


class TestCertidaoAnimal:
    def test_creates_valid(self):
        dados = AnimalEventFactory.certidao(
            tipo_certidao="NASCIMENTO",
            numero="CERT-2024-001",
            data_emissao="01/06/2024",
            orgao_emissor="CBKC",
        )
        assert dados["evento_tipo"] == "CERTIDAO"


# ── AnimalChain ───────────────────────────────────────────────────────


class TestAnimalChain:
    def _create_genesis_data(self):
        return AnimalEventFactory.nascimento(
            uf="SP",
            cidade="Sao Paulo",
            nome="Rex",
            especie="CAO",
            raca="Labrador",
            sexo="M",
            data_nascimento="15/03/2024",
            cor="Dourado",
            peso_kg=5.0,
            proprietario_cpf="12345678901",
            proprietario_nome="João Silva",
        )

    def test_create_genesis(self):
        chain = AnimalChain(difficulty=1)
        dados = self._create_genesis_data()
        genesis = chain.create_genesis(dados)
        assert genesis.index == 0
        assert genesis.data["evento_tipo"] == "NASCIMENTO"
        assert len(chain) == 1

    def test_get_nome(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        assert chain.get_nome() == "Rex"

    def test_get_especie(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        assert chain.get_especie() == "CAO"

    def test_add_vacinacao(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        block = chain.add_event(
            "VACINACAO",
            AnimalEventFactory.vacinacao(
                nome_vacina="Raiva", data_vacinacao="01/04/2024",
            ),
        )
        assert block.index == 1
        assert len(chain) == 2

    def test_get_estado_after_vacinacao(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "VACINACAO",
            AnimalEventFactory.vacinacao(
                nome_vacina="Raiva", data_vacinacao="01/04/2024",
                dose="1a dose",
            ),
        )
        estado = chain.get_estado_atual()
        assert len(estado["vacinas"]) == 1
        assert estado["vacinas"][0]["nome"] == "Raiva"

    def test_get_estado_after_compra(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "COMPRA_VENDA",
            AnimalEventFactory.compra_venda(
                nome="Rex",
                comprador_cpf="98765432100", comprador_nome="Maria",
                vendedor_cpf="12345678901", vendedor_nome="João",
                valor_transacao=2000.0, data_transacao="01/06/2024",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["proprietario"]["cpf"] == "98765432100"
        assert len(estado["historico_proprietarios"]) == 2

    def test_get_estado_after_adocao(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "ADOCAO",
            AnimalEventFactory.adocao(
                adotante_cpf="98765432100", adotante_nome="Maria",
                data_adocao="01/06/2024",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["proprietario"]["cpf"] == "98765432100"

    def test_get_estado_after_microchip(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "MICROCHIP",
            AnimalEventFactory.microchip(
                numero_microchip="900123456789012",
                data_implantacao="01/06/2024",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["microchip"] == "900123456789012"

    def test_get_estado_after_mudanca_nome(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "MUDANCA_NOME",
            AnimalEventFactory.mudanca_nome(
                nome_anterior="Rex", nome_novo="Thor",
                data_mudanca="01/06/2024",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["nome"] == "Thor"

    def test_get_estado_after_obito(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "OBITO",
            AnimalEventFactory.obito(
                data_obito="01/06/2024", causa="Velhice",
            ),
        )
        estado = chain.get_estado_atual()
        assert estado["situacao"] == "OBITO"

    def test_validate_valid(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        ok, msg = chain.validate()
        assert ok
        assert "válida" in msg

    def test_validate_empty(self):
        chain = AnimalChain(difficulty=1)
        ok, msg = chain.validate()
        assert not ok

    def test_add_evento_sem_genesis(self):
        chain = AnimalChain(difficulty=1)
        with pytest.raises(ValueError, match="Cadeia vazia"):
            chain.add_event("VACINACAO", {})

    def test_historico_completo(self):
        chain = AnimalChain(difficulty=1)
        chain.create_genesis(self._create_genesis_data())
        chain.add_event(
            "VACINACAO",
            AnimalEventFactory.vacinacao(
                nome_vacina="Raiva", data_vacinacao="01/04/2024",
            ),
        )
        historico = chain.get_historico_completo()
        assert len(historico) == 2
        assert historico[0]["tipo"] == "NASCIMENTO"
        assert historico[1]["tipo"] == "VACINACAO"


# ── AnimalChainProtector ──────────────────────────────────────────────


class TestAnimalChainProtector:
    def test_allows_when_vivo(self):
        assert AnimalChainProtector.pode_adicionar("VACINACAO", "VIVO")

    def test_blocks_when_obito(self):
        assert not AnimalChainProtector.pode_adicionar("VACINACAO", "OBITO")

    def test_allows_certidao_when_obito(self):
        assert AnimalChainProtector.pode_adicionar("CERTIDAO", "OBITO")

    def test_allows_obito_when_perda_total(self):
        assert AnimalChainProtector.pode_adicionar("OBITO", "PERDA_TOTAL")

    def test_blocks_compra_when_obito(self):
        assert not AnimalChainProtector.pode_adicionar("COMPRA_VENDA", "OBITO")


# ── CrossChainAN ──────────────────────────────────────────────────────


class TestCrossChainAN:
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

    def _create_an(self):
        chain = AnimalChain(difficulty=1)
        dados = AnimalEventFactory.nascimento(
            uf="SP",
            cidade="Sao Paulo",
            nome="Rex", especie="CAO", raca="Labrador", sexo="M",
            data_nascimento="15/03/2024", cor="Dourado", peso_kg=5.0,
            proprietario_cpf="12345678901", proprietario_nome="João Silva",
        )
        chain.create_genesis(dados)
        return chain

    def test_create_reference(self):
        manager = CrossChainAN()
        pf = self._create_pf()
        an = self._create_an()
        manager.register_pf("12345678901", pf)
        manager.register_an("rex-001", an)

        ref = manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="AN", destino_id="rex-001",
            tipo_vinculo="PROPRIETARIO",
        )
        assert ref.entidade_origem_id == "12345678901"
        assert ref.entidade_destino_id == "rex-001"
        assert ref.ativo

    def test_get_animais_da_pessoa(self):
        manager = CrossChainAN()
        pf = self._create_pf()
        an = self._create_an()
        manager.register_pf("12345678901", pf)
        manager.register_an("rex-001", an)
        manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="AN", destino_id="rex-001",
            tipo_vinculo="PROPRIETARIO",
        )
        result = manager.get_animais_da_pessoa("12345678901")
        assert len(result) == 1
        assert result[0]["nome"] == "Rex"

    def test_get_pessoas_do_animal(self):
        manager = CrossChainAN()
        pf = self._create_pf()
        an = self._create_an()
        manager.register_pf("12345678901", pf)
        manager.register_an("rex-001", an)
        manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="AN", destino_id="rex-001",
            tipo_vinculo="PROPRIETARIO",
        )
        result = manager.get_pessoas_do_animal("rex-001")
        assert len(result) == 1
        assert result[0]["cpf"] == "12345678901"

    def test_stats(self):
        manager = CrossChainAN()
        pf = self._create_pf()
        an = self._create_an()
        manager.register_pf("12345678901", pf)
        manager.register_an("rex-001", an)
        manager.create_reference(
            origem_tipo="PF", origem_id="12345678901",
            destino_tipo="AN", destino_id="rex-001",
            tipo_vinculo="PROPRIETARIO",
        )
        stats = manager.stats()
        assert stats["total_cadeias_pf"] == 1
        assert stats["total_cadeias_an"] == 1
        assert stats["referencias_ativas"] == 1
