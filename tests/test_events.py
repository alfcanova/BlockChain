"""Testes unitarios para blockchain_pf/events.py"""

import pytest
from blockchain_pf.events import EventFactory, EventType, ChainProtector


# ── Nascimento ─────────────────────────────────────────────────────────

class TestNascimento:
    def test_creates_valid_nascimento(self):
        dados = EventFactory.nascimento(
            cpf="12345678901",
            nome_completo="Maria Clara",
            data_nascimento="15/03/2000",
            sexo="F",
            cidade_nascimento="Sao Paulo",
            uf_nascimento="SP",
            nome_mae="Ana Paula",
        )
        assert dados["evento_tipo"] == "NASCIMENTO"
        assert dados["cpf"] == "12345678901"
        assert dados["nome_completo"] == "Maria Clara"
        assert dados["sexo"] == "F"
        assert dados["status_vivo"] is True

    def test_strips_whitespace(self):
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="  Maria Clara  ",
            data_nascimento="15/03/2000", sexo="f",
            cidade_nascimento="sao paulo", uf_nascimento="sp",
            nome_mae="ana paula",
        )
        assert dados["nome_completo"] == "Maria Clara"
        assert dados["sexo"] == "F"
        assert dados["uf_nascimento"] == "SP"

    def test_invalid_cpf_raises(self):
        with pytest.raises(ValueError, match="CPF"):
            EventFactory.nascimento(
                cpf="123", nome_completo="Maria",
                data_nascimento="15/03/2000", sexo="F",
                cidade_nascimento="Sao Paulo", uf_nascimento="SP",
                nome_mae="Ana",
            )

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="Data"):
            EventFactory.nascimento(
                cpf="12345678901", nome_completo="Maria",
                data_nascimento="2000-03-15", sexo="F",
                cidade_nascimento="Sao Paulo", uf_nascimento="SP",
                nome_mae="Ana",
            )

    def test_invalid_uf_raises(self):
        with pytest.raises(ValueError, match="UF"):
            EventFactory.nascimento(
                cpf="12345678901", nome_completo="Maria",
                data_nascimento="15/03/2000", sexo="F",
                cidade_nascimento="Sao Paulo", uf_nascimento="XX",
                nome_mae="Ana",
            )

    def test_invalid_sexo_raises(self):
        with pytest.raises(ValueError, match="Sexo"):
            EventFactory.nascimento(
                cpf="12345678901", nome_completo="Maria",
                data_nascimento="15/03/2000", sexo="X",
                cidade_nascimento="Sao Paulo", uf_nascimento="SP",
                nome_mae="Ana",
            )

    def test_with_pai(self):
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="Maria",
            data_nascimento="15/03/2000", sexo="F",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Ana", nome_pai="Joao",
        )
        assert dados["nome_pai"] == "Joao"
        assert dados["parentela"]["pai"]["nome"] == "Joao"

    def test_without_pai(self):
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="Maria",
            data_nascimento="15/03/2000", sexo="F",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Ana",
        )
        assert dados["nome_pai"] == ""
        assert dados["parentela"]["pai"]["ativo"] is True


# ── Casamento ──────────────────────────────────────────────────────────

class TestCasamento:
    def test_creates_valid_casamento(self):
        dados = EventFactory.casamento(
            cpf="12345678901",
            nome_conjuge="Pedro",
            cpf_conjuge="98765432100",
            data_casamento="20/06/2022",
        )
        assert dados["evento_tipo"] == "CASAMENTO"
        assert dados["nome_conjuge"] == "Pedro"
        assert dados["regime_bens"] == "COMUNHAO_PARCIAL"

    def test_custom_regime(self):
        dados = EventFactory.casamento(
            cpf="12345678901", nome_conjuge="Pedro",
            cpf_conjuge="98765432100", data_casamento="20/06/2022",
            regime_bens="SEPARACAO_TOTAL",
        )
        assert dados["regime_bens"] == "SEPARACAO_TOTAL"

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError):
            EventFactory.casamento(
                cpf="12345678901", nome_conjuge="Pedro",
                cpf_conjuge="98765432100", data_casamento="2022-06-20",
            )


# ── Divorcio ───────────────────────────────────────────────────────────

class TestDivorcio:
    def test_creates_valid_divorcio(self):
        dados = EventFactory.divorcio(
            cpf="12345678901",
            data_divorcio="05/01/2025",
        )
        assert dados["evento_tipo"] == "DIVORCIO"
        assert dados["tipo"] == "CONSENSUAL"

    def test_judicial(self):
        dados = EventFactory.divorcio(
            cpf="12345678901", data_divorcio="05/01/2025",
            tipo="JUDICIAL", guarda_filhos="MATERNA",
            pensao_alimenticia=True,
        )
        assert dados["tipo"] == "JUDICIAL"
        assert dados["guarda_filhos"] == "MATERNA"
        assert dados["pensao_alimenticia"] is True


# ── Obito ──────────────────────────────────────────────────────────────

class TestObito:
    def test_creates_valid_obito(self):
        dados = EventFactory.obito(
            cpf="12345678901",
            data_obito="01/01/2050",
            cidade_obito="SP",
            uf_obito="SP",
        )
        assert dados["evento_tipo"] == "OBITO"
        assert dados["causa_morte"] == "Não informada"

    def test_with_causa(self):
        dados = EventFactory.obito(
            cpf="12345678901", data_obito="01/01/2050",
            cidade_obito="SP", uf_obito="SP",
            causa_morte="Causa natural",
        )
        assert dados["causa_morte"] == "Causa natural"


# ── Alteracao de Nome ──────────────────────────────────────────────────

class TestAlteracaoNome:
    def test_creates_valid(self):
        dados = EventFactory.alteracao_nome(
            cpf="12345678901",
            nome_anterior="Maria Clara",
            nome_novo="Maria Clara Santos",
            data_alteracao="15/03/2018",
            motivo="Casamento",
        )
        assert dados["evento_tipo"] == "ALTERACAO_NOME"
        assert dados["nome_anterior"] == "Maria Clara"
        assert dados["nome_novo"] == "Maria Clara Santos"


# ── Adocao ─────────────────────────────────────────────────────────────

class TestAdocao:
    def test_creates_valid(self):
        dados = EventFactory.adocao(
            cpf="12345678901",
            nome_adotivo=None,
            data_adocao="10/11/2023",
            nome_mae_adotiva="Maria Clara",
        )
        assert dados["evento_tipo"] == "ADOCAO"
        assert dados["mantem_nome_biologico"] is False

    def test_with_nome_adotivo(self):
        dados = EventFactory.adocao(
            cpf="12345678901",
            nome_adotivo="Novo Nome",
            data_adocao="10/11/2023",
            nome_mae_adotiva="Maria",
            mantem_nome_biologico=True,
        )
        assert dados["nome_adotivo"] == "Novo Nome"
        assert dados["mantem_nome_biologico"] is True


# ── Disvinculacao ──────────────────────────────────────────────────────

class TestDisvinculacao:
    def test_materna(self):
        dados = EventFactory.disvinculacao_materna(
            cpf="12345678901",
            data_disvinculacao="15/03/2026",
            motivo="Ausencia",
        )
        assert dados["evento_tipo"] == "DISVINC_MATERNA"
        assert dados["vinculo_afetado"] == "MAE"

    def test_paterna(self):
        dados = EventFactory.disvinculacao_paterna(
            cpf="12345678901",
            data_disvinculacao="15/03/2026",
            motivo="Abandono",
        )
        assert dados["evento_tipo"] == "DISVINC_PATerna"
        assert dados["vinculo_afetado"] == "PAI"


# ── Vacinação ──────────────────────────────────────────────────────────

class TestVacina:
    def test_creates_valid_vacina(self):
        dados = EventFactory.vacina(
            cpf="12345678901",
            nome_vacina="COVID-19",
            data_vacinacao="10/05/2024",
        )
        assert dados["evento_tipo"] == "VACINACAO"
        assert dados["cpf"] == "12345678901"
        assert dados["nome_vacina"] == "COVID-19"
        assert dados["data_vacinacao"] == "10/05/2024"

    def test_with_all_fields(self):
        dados = EventFactory.vacina(
            cpf="12345678901",
            nome_vacina="Febre Amarela",
            data_vacinacao="15/01/2023",
            lote="FA2023-01",
            fabricante="Bio-Manguinhos",
            dose="Dose única",
            unidade_saude="UBS Vila Mariana",
            cidade="São Paulo",
            uf="SP",
        )
        assert dados["lote"] == "FA2023-01"
        assert dados["fabricante"] == "Bio-Manguinhos"
        assert dados["dose"] == "Dose única"
        assert dados["uf"] == "SP"

    def test_invalid_cpf_raises(self):
        with pytest.raises(ValueError, match="CPF"):
            EventFactory.vacina(
                cpf="123", nome_vacina="COVID-19",
                data_vacinacao="10/05/2024",
            )

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="Data"):
            EventFactory.vacina(
                cpf="12345678901", nome_vacina="COVID-19",
                data_vacinacao="2024-05-10",
            )

    def test_empty_vacina_name_raises(self):
        with pytest.raises(ValueError, match="vacina"):
            EventFactory.vacina(
                cpf="12345678901", nome_vacina="",
                data_vacinacao="10/05/2024",
            )


# ── Prótese ─────────────────────────────────────────────────────────────

class TestProtese:
    def test_creates_valid_protese(self):
        dados = EventFactory.protese(
            cpf="12345678901",
            nome_protese="Prótese de Joelho Direito",
            data_implantacao="15/03/2023",
        )
        assert dados["evento_tipo"] == "PROTESE"
        assert dados["cpf"] == "12345678901"
        assert dados["nome_protese"] == "Prótese de Joelho Direito"
        assert dados["ativa"] is True

    def test_with_all_fields(self):
        dados = EventFactory.protese(
            cpf="12345678901",
            nome_protese="Stent Coronário",
            data_implantacao="20/07/2022",
            tipo="Cardíaca",
            marca_modelo="Medtronic Xience",
            medico_responsavel="Dr. Silva",
            hospital_clinica="Hospital Sírio-Libanês",
            cidade="São Paulo",
            uf="SP",
        )
        assert dados["tipo"] == "Cardíaca"
        assert dados["ativa"] is True
        assert dados["uf"] == "SP"

    def test_with_remoção(self):
        dados = EventFactory.protese(
            cpf="12345678901",
            nome_protese="Prótese de Quadril",
            data_implantacao="10/01/2020",
            data_remocao="15/06/2024",
            motivo_remocao="Desgaste",
        )
        assert dados["ativa"] is False
        assert dados["data_remocao"] == "15/06/2024"
        assert dados["motivo_remocao"] == "Desgaste"

    def test_invalid_cpf_raises(self):
        with pytest.raises(ValueError, match="CPF"):
            EventFactory.protese(
                cpf="123", nome_protese="Joelho",
                data_implantacao="15/03/2023",
            )

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError, match="Data"):
            EventFactory.protese(
                cpf="12345678901", nome_protese="Joelho",
                data_implantacao="2023-03-15",
            )

    def test_invalid_remoção_date_raises(self):
        with pytest.raises(ValueError, match="remo"):
            EventFactory.protese(
                cpf="12345678901", nome_protese="Joelho",
                data_implantacao="15/03/2023",
                data_remocao="2024-06-15",
            )

    def test_empty_protese_name_raises(self):
        with pytest.raises(ValueError):
            EventFactory.protese(
                cpf="12345678901", nome_protese="",
                data_implantacao="15/03/2023",
            )


# ── EventType Enum ─────────────────────────────────────────────────────

class TestEventType:
    def test_all_types_exist(self):
        assert EventType.NASCIMENTO.value == "NASCIMENTO"
        assert EventType.ADOCAO.value == "ADOCAO"
        assert EventType.CASAMENTO.value == "CASAMENTO"
        assert EventType.DIVORCIO.value == "DIVORCIO"
        assert EventType.OBITO.value == "OBITO"
        assert EventType.ALTERACAO_NOME.value == "ALTERACAO_NOME"
        assert EventType.DISVINC_MATERNA.value == "DISVINC_MATERNA"
        assert EventType.DISVINC_PATerna.value == "DISVINC_PATerna"
        assert EventType.VACINACAO.value == "VACINACAO"
        assert EventType.PROTESE.value == "PROTESE"


# ── ChainProtector ─────────────────────────────────────────────────────

class TestChainProtector:
    def test_allows_events_before_obito(self):
        assert ChainProtector.pode_adicionar("CASAMENTO", False)
        assert ChainProtector.pode_adicionar("DIVORCIO", False)

    def test_blocks_events_after_obito(self):
        assert not ChainProtector.pode_adicionar("CASAMENTO", True)
        assert not ChainProtector.pode_adicionar("DIVORCIO", True)
        assert not ChainProtector.pode_adicionar("ADOCAO", True)
        assert not ChainProtector.pode_adicionar("DISVINC_MATERNA", True)
        assert not ChainProtector.pode_adicionar("DISVINC_PATerna", True)

    def test_allows_alteracao_nome_after_obito(self):
        assert ChainProtector.pode_adicionar("ALTERACAO_NOME", True)
