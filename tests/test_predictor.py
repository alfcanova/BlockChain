"""Testes unitarios para blockchain_pf/predictor.py"""

import pytest
from blockchain_pf.chain import Blockchain
from blockchain_pf.predictor import LifeEventPredictor, Prediction, PredictionReport
from blockchain_pf.events import EventType


@pytest.fixture
def young_female_chain():
    """Cadeia de uma jovem de 26 anos, solteira."""
    chain = Blockchain(difficulty=1)
    dados = {
        "cpf": "12345678901",
        "nome_completo": "Maria Clara",
        "data_nascimento": "15/03/2000",
        "sexo": "F",
        "cidade_nascimento": "Sao Paulo",
        "uf_nascimento": "SP",
        "nome_mae": "Ana Paula",
    }
    chain.create_genesis(dados)
    return chain


@pytest.fixture
def married_male_chain():
    """Cadeia de um homem casado de 35 anos."""
    chain = Blockchain(difficulty=1)
    dados = {
        "cpf": "98765432100",
        "nome_completo": "Pedro Henrique",
        "data_nascimento": "10/06/1991",
        "sexo": "M",
        "cidade_nascimento": "Rio de Janeiro",
        "uf_nascimento": "RJ",
        "nome_mae": "Clara",
    }
    chain.create_genesis(dados)
    chain.add_event(EventType.CASAMENTO.value, {
        "evento_tipo": "CASAMENTO",
        "cpf": "98765432100",
        "nome_conjuge": "Maria",
        "data_casamento": "20/06/2022",
    })
    return chain


@pytest.fixture
def divorced_chain():
    """Cadeia de uma mulher divorciada de 40 anos."""
    chain = Blockchain(difficulty=1)
    dados = {
        "cpf": "11122233344",
        "nome_completo": "Ana Souza",
        "data_nascimento": "01/01/1986",
        "sexo": "F",
        "cidade_nascimento": "Belo Horizonte",
        "uf_nascimento": "MG",
        "nome_mae": "Rosa",
    }
    chain.create_genesis(dados)
    chain.add_event(EventType.CASAMENTO.value, {
        "evento_tipo": "CASAMENTO",
        "cpf": "11122233344",
        "nome_conjuge": "Carlos",
        "data_casamento": "15/12/2010",
    })
    chain.add_event(EventType.DIVORCIO.value, {
        "evento_tipo": "DIVORCIO",
        "cpf": "11122233344",
        "data_divorcio": "01/06/2020",
    })
    return chain


@pytest.fixture
def deceased_chain():
    """Cadeia de uma pessoa falecida."""
    chain = Blockchain(difficulty=1)
    dados = {
        "cpf": "55566677788",
        "nome_completo": "Jose Silva",
        "data_nascimento": "01/01/1950",
        "sexo": "M",
        "cidade_nascimento": "Salvador",
        "uf_nascimento": "BA",
        "nome_mae": "Maria",
    }
    chain.create_genesis(dados)
    chain.add_event(EventType.OBITO.value, {
        "evento_tipo": "OBITO",
        "cpf": "55566677788",
        "data_obito": "01/01/2024",
        "cidade_obito": "Salvador",
        "uf_obito": "BA",
    })
    return chain


# ── LifeEventPredictor ────────────────────────────────────────────────

class TestPredictorCreation:
    def test_creates_predictor(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        assert predictor.chain is young_female_chain

    def test_idade_atual(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        idade = predictor._idade_atual()
        assert 25 <= idade <= 27  # Nasceu em 2000

    def test_sexo(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        assert predictor._sexo() == "F"

    def test_ja_casou_false(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        assert not predictor._ja_casou()

    def test_ja_casou_true(self, married_male_chain):
        predictor = LifeEventPredictor(married_male_chain)
        assert predictor._ja_casou()

    def test_esta_casado_true(self, married_male_chain):
        predictor = LifeEventPredictor(married_male_chain)
        assert predictor._esta_casado()

    def test_esta_casado_false_after_divorce(self, divorced_chain):
        predictor = LifeEventPredictor(divorced_chain)
        assert not predictor._esta_casado()

    def test_ja_teve_obito_false(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        assert not predictor._ja_teve_obito()

    def test_ja_teve_obito_true(self, deceased_chain):
        predictor = LifeEventPredictor(deceased_chain)
        assert predictor._ja_teve_obito()


# ── Prediction: Casamento ──────────────────────────────────────────────

class TestPredizerCasamento:
    def test_solteira_young(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        pred = predictor.predizer_casamento()
        assert pred is not None
        assert pred.evento == "CASAMENTO"
        assert 0.0 < pred.probabilidade <= 1.0

    def test_casado_nao_prediz(self, married_male_chain):
        predictor = LifeEventPredictor(married_male_chain)
        pred = predictor.predizer_casamento()
        assert pred is None  # Ja casado e nao divorciado

    def test_divorciada_prediz(self, divorced_chain):
        predictor = LifeEventPredictor(divorced_chain)
        pred = predictor.predizer_casamento()
        assert pred is not None
        assert pred.probabilidade > 0  # Re-casamento possivel

    def test_falecido_nao_prediz(self, deceased_chain):
        predictor = LifeEventPredictor(deceased_chain)
        pred = predictor.predizer_casamento()
        assert pred is None


# ── Prediction: Divorcio ───────────────────────────────────────────────

class TestPredizerDivorcio:
    def test_solteira_nao_prediz(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        pred = predictor.predizer_divorcio()
        assert pred is None

    def test_casado_prediz(self, married_male_chain):
        predictor = LifeEventPredictor(married_male_chain)
        pred = predictor.predizer_divorcio()
        assert pred is not None
        assert pred.evento and pred.probabilidade > 0
        assert 0.0 < pred.probabilidade <= 1.0

    def test_divorciada_nao_prediz(self, divorced_chain):
        predictor = LifeEventPredictor(divorced_chain)
        pred = predictor.predizer_divorcio()
        assert pred is None

    def test_falecido_nao_prediz(self, deceased_chain):
        predictor = LifeEventPredictor(deceased_chain)
        pred = predictor.predizer_divorcio()
        assert pred is None


# ── Prediction: Obito ──────────────────────────────────────────────────

class TestPredizerObito:
    def test_vivo_prediz(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        pred = predictor.predizer_obito()
        assert pred is not None
        assert pred.probabilidade > 0
        assert pred.probabilidade < 1.0

    def test_falecido_nao_prediz(self, deceased_chain):
        predictor = LifeEventPredictor(deceased_chain)
        pred = predictor.predizer_obito()
        assert pred is None

    def test_idoso_maior_probabilidade(self):
        """Pessoa mais velha deve ter maior probabilidade de obito."""
        chain_old = Blockchain(difficulty=1)
        chain_old.create_genesis({
            "cpf": "11111111111", "nome_completo": "Velho",
            "data_nascimento": "01/01/1940", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        chain_young = Blockchain(difficulty=1)
        chain_young.create_genesis({
            "cpf": "22222222222", "nome_completo": "Jovem",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        pred_old = LifeEventPredictor(chain_old).predizer_obito()
        pred_young = LifeEventPredictor(chain_young).predizer_obito()
        assert pred_old.probabilidade > pred_young.probabilidade


# ── Prediction: Adocao ─────────────────────────────────────────────────

class TestPredizerAdocao:
    def test_adulto_prediz(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        pred = predictor.predizer_adocao()
        assert pred is not None
        assert pred is not None and pred.probabilidade > 0

    def test_falecido_nao_prediz(self, deceased_chain):
        predictor = LifeEventPredictor(deceased_chain)
        pred = predictor.predizer_adocao()
        assert pred is None


# ── Prediction: Disvinculacao ──────────────────────────────────────────

class TestPredizerDisvinculacao:
    def test_vivo_prediz(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        pred = predictor.predizer_disvinculacao()
        assert pred is not None
        assert pred.probabilidade < 0.01  # Evento raro

    def test_falecido_nao_prediz(self, deceased_chain):
        predictor = LifeEventPredictor(deceased_chain)
        pred = predictor.predizer_disvinculacao()
        assert pred is None


# ── Prediction: Alteracao Nome ─────────────────────────────────────────

class TestPredizerAlteracaoNome:
    def test_vivo_prediz(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        pred = predictor.predizer_alteracao_nome()
        assert pred is not None
        assert pred.probabilidade > 0

    def test_falecido_nao_prediz(self, deceased_chain):
        predictor = LifeEventPredictor(deceased_chain)
        pred = predictor.predizer_alteracao_nome()
        assert pred is None


# ── Report ─────────────────────────────────────────────────────────────

class TestReport:
    def test_gera_relatorio(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        report = predictor.gerar_relatorio()
        assert isinstance(report, PredictionReport)
        assert report.nome == "Maria Clara"
        assert len(report.predicoes) > 0

    def test_report_to_dict(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        report = predictor.gerar_relatorio()
        d = report.to_dict()
        assert "cpf" in d
        assert "predicoes" in d
        assert len(d["predicoes"]) > 0

    def test_report_resumo(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        report = predictor.gerar_relatorio()
        resumo = report.resumo()
        assert "Maria Clara" in resumo
        assert "CASAMENTO" in resumo or "OBITO" in resumo

    def test_report_has_situacao(self, young_female_chain):
        predictor = LifeEventPredictor(young_female_chain)
        report = predictor.gerar_relatorio()
        assert len(report.situacao_atual) > 0

    def test_falecido_report(self, deceased_chain):
        predictor = LifeEventPredictor(deceased_chain)
        report = predictor.gerar_relatorio()
        # Falecido: menos predicoes
        assert len(report.predicoes) < 5


# ── Prediction dataclass ───────────────────────────────────────────────

class TestPredictionDataclass:
    def test_to_dict(self):
        p = Prediction(
            evento="TESTE", probabilidade=0.5,
            timeframe="5-10 anos", fundamento="Teste",
            confianca="MEDIA",
        )
        d = p.to_dict()
        assert d["evento"] == "TESTE"
        assert d["probabilidade"] == 0.5
        assert d["confianca"] == "MEDIA"


# ── Helpers ────────────────────────────────────────────────────────────

class TestHelpers:
    def test_faixa_mortalidade(self):
        assert LifeEventPredictor._faixa_mortalidade(5) == "0-9"
        assert LifeEventPredictor._faixa_mortalidade(15) == "10-19"
        assert LifeEventPredictor._faixa_mortalidade(25) == "20-29"
        assert LifeEventPredictor._faixa_mortalidade(35) == "30-39"
        assert LifeEventPredictor._faixa_mortalidade(45) == "40-49"
        assert LifeEventPredictor._faixa_mortalidade(55) == "50-59"
        assert LifeEventPredictor._faixa_mortalidade(65) == "60-69"
        assert LifeEventPredictor._faixa_mortalidade(75) == "70-79"
        assert LifeEventPredictor._faixa_mortalidade(85) == "80-89"
        assert LifeEventPredictor._faixa_mortalidade(95) == "90+"
