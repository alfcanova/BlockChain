"""Testes completos para os 3 novos eventos de PF: CNH, Titulo do Eleitor, Escolaridade.

Cobre: EventFactory (criacao + validacao), Predictor, e endpoints da API.
"""
import pytest
from blockchain_pf.events import EventFactory, EventType
from blockchain_pf.chain import Blockchain
from blockchain_pf.predictor import LifeEventPredictor
from blockchain_pf.signatures import generate_authority_keypair


# ── Helpers ──────────────────────────────────────────────────────────

def _birth_data(**overrides):
    defaults = dict(
        cpf="12345678901",
        nome_completo="Maria Clara",
        data_nascimento="15/03/2000",
        sexo="F",
        cidade_nascimento="Sao Paulo",
        uf_nascimento="SP",
        nome_mae="Ana Paula",
    )
    defaults.update(overrides)
    return defaults


def _make_chain(**overrides):
    c = Blockchain(difficulty=1)
    c.create_genesis(_birth_data(**overrides))
    return c


# ══════════════════════════════════════════════════════════════════════
#  CNH — EventFactory
# ══════════════════════════════════════════════════════════════════════

class TestCNHFactory:
    def test_cria_cnh_valida(self):
        dados = EventFactory.cnh(
            cpf="12345678901",
            numero_cnh="12345678901",
            categoria="B",
            data_emissao="15/03/2020",
            data_validade="15/03/2030",
            orgao_emissor="DETRAN-SP",
            uf_emissao="SP",
            situacao="VALIDA",
            pontos=0,
        )
        assert dados["evento_tipo"] == "CNH"
        assert dados["cpf"] == "12345678901"
        assert dados["numero_cnh"] == "12345678901"
        assert dados["categoria"] == "B"
        assert dados["situacao"] == "VALIDA"
        assert dados["pontos"] == 0

    def test_cnh_com_exame_medico(self):
        dados = EventFactory.cnh(
            cpf="12345678901",
            numero_cnh="99988877766",
            categoria="AB",
            data_emissao="01/01/2024",
            data_validade="01/01/2034",
            exame_medico="APTO",
            data_exame_medico="15/12/2023",
        )
        assert dados["exame_medico"] == "APTO"
        assert dados["categoria"] == "AB"

    def test_cnh_pontos_limites(self):
        dados = EventFactory.cnh(
            cpf="12345678901",
            numero_cnh="11122233344",
            categoria="B",
            data_emissao="01/01/2024",
            data_validade="01/01/2034",
            pontos=50,  # > 40, deve ser limitado a 40
        )
        assert dados["pontos"] == 40

    def test_cnh_pontos_negativos(self):
        dados = EventFactory.cnh(
            cpf="12345678901",
            numero_cnh="11122233344",
            categoria="B",
            data_emissao="01/01/2024",
            data_validade="01/01/2034",
            pontos=-5,  # < 0, deve ser limitado a 0
        )
        assert dados["pontos"] == 0

    def test_cnh_cpf_invalido(self):
        with pytest.raises(ValueError, match="CPF"):
            EventFactory.cnh(
                cpf="123",
                numero_cnh="12345678901",
                categoria="B",
                data_emissao="01/01/2024",
                data_validade="01/01/2034",
            )

    def test_cnh_numero_obrigatorio(self):
        with pytest.raises(ValueError, match="Número"):
            EventFactory.cnh(
                cpf="12345678901",
                numero_cnh="",
                categoria="B",
                data_emissao="01/01/2024",
                data_validade="01/01/2034",
            )

    def test_cnh_data_emissao_invalida(self):
        with pytest.raises(ValueError, match="emissão"):
            EventFactory.cnh(
                cpf="12345678901",
                numero_cnh="12345678901",
                categoria="B",
                data_emissao="2024/01/01",
                data_validade="01/01/2034",
            )

    def test_cnh_data_validade_invalida(self):
        with pytest.raises(ValueError, match="validade"):
            EventFactory.cnh(
                cpf="12345678901",
                numero_cnh="12345678901",
                categoria="B",
                data_emissao="01/01/2024",
                data_validade="2034/01/01",
            )

    def test_cnh_categorias_variadas(self):
        for cat in ["A", "B", "C", "D", "E", "AB", "AC", "AD", "AE"]:
            dados = EventFactory.cnh(
                cpf="12345678901",
                numero_cnh="12345678901",
                categoria=cat,
                data_emissao="01/01/2024",
                data_validade="01/01/2034",
            )
            assert dados["categoria"] == cat


# ══════════════════════════════════════════════════════════════════════
#  TITULO ELEITOR — EventFactory
# ══════════════════════════════════════════════════════════════════════

class TestTituloEleitorFactory:
    def test_cria_titulo_valido(self):
        dados = EventFactory.titulo_eleitor(
            cpf="12345678901",
            numero_titulo="123456789012",
            zona_eleitoral="0123",
            secao_eleitoral="0045",
            municipio="Sao Paulo",
            uf="SP",
            data_emissao="10/06/2018",
            situacao="REGULAR",
        )
        assert dados["evento_tipo"] == "TITULO_ELEITOR"
        assert dados["cpf"] == "12345678901"
        assert dados["numero_titulo"] == "123456789012"
        assert dados["zona_eleitoral"] == "0123"
        assert dados["secao_eleitoral"] == "0045"
        assert dados["municipio"] == "Sao Paulo"
        assert dados["uf"] == "SP"
        assert dados["situacao"] == "REGULAR"

    def test_titulo_com_transferencia(self):
        dados = EventFactory.titulo_eleitor(
            cpf="12345678901",
            numero_titulo="999888777666",
            zona_eleitoral="0050",
            secao_eleitoral="0100",
            municipio="Rio de Janeiro",
            uf="RJ",
            data_emissao="01/01/2024",
            titulo_anterior="123456789012",
        )
        assert dados["titulo_anterior"] == "123456789012"

    def test_titulo_cpf_invalido(self):
        with pytest.raises(ValueError, match="CPF"):
            EventFactory.titulo_eleitor(
                cpf="123",
                numero_titulo="123456789012",
                zona_eleitoral="0123",
                secao_eleitoral="0045",
                municipio="SP",
                uf="SP",
                data_emissao="01/01/2024",
            )

    def test_titulo_numero_invalido(self):
        with pytest.raises(ValueError, match="título"):
            EventFactory.titulo_eleitor(
                cpf="12345678901",
                numero_titulo="12345",  # < 12 digitos
                zona_eleitoral="0123",
                secao_eleitoral="0045",
                municipio="SP",
                uf="SP",
                data_emissao="01/01/2024",
            )

    def test_titulo_zona_obrigatoria(self):
        with pytest.raises(ValueError, match="Zona"):
            EventFactory.titulo_eleitor(
                cpf="12345678901",
                numero_titulo="123456789012",
                zona_eleitoral="",
                secao_eleitoral="0045",
                municipio="SP",
                uf="SP",
                data_emissao="01/01/2024",
            )

    def test_titulo_secao_obrigatoria(self):
        with pytest.raises(ValueError, match="Seção"):
            EventFactory.titulo_eleitor(
                cpf="12345678901",
                numero_titulo="123456789012",
                zona_eleitoral="0123",
                secao_eleitoral="",
                municipio="SP",
                uf="SP",
                data_emissao="01/01/2024",
            )

    def test_titulo_data_invalida(self):
        with pytest.raises(ValueError, match="emissão"):
            EventFactory.titulo_eleitor(
                cpf="12345678901",
                numero_titulo="123456789012",
                zona_eleitoral="0123",
                secao_eleitoral="0045",
                municipio="SP",
                uf="SP",
                data_emissao="2024/01/01",
            )


# ══════════════════════════════════════════════════════════════════════
#  ESCOLARIDADE — EventFactory
# ══════════════════════════════════════════════════════════════════════

class TestEscolaridadeFactory:
    def test_cria_escolaridade_fundamental(self):
        dados = EventFactory.escolaridade(
            cpf="12345678901",
            nivel="Fundamental",
            instituicao="EMEF Maria Clara",
            data_inicio="01/02/2006",
            data_conclusao="15/12/2017",
            serie_ano="9 ano",
            situacao="CONCLUIDO",
        )
        assert dados["evento_tipo"] == "ESCOLARIDADE"
        assert dados["nivel"] == "Fundamental"
        assert dados["instituicao"] == "EMEF Maria Clara"
        assert dados["situacao"] == "CONCLUIDO"

    def test_cria_escolaridade_superior(self):
        dados = EventFactory.escolaridade(
            cpf="12345678901",
            nivel="Superior",
            instituicao="USP",
            data_inicio="01/03/2018",
            data_conclusao="15/12/2022",
            curso="Ciencia da Computacao",
            registro="DIPLOMA-2022-001",
            tipo_registro="DIPLOMA",
        )
        assert dados["curso"] == "Ciencia da Computacao"
        assert dados["registro"] == "DIPLOMA-2022-001"
        assert dados["tipo_registro"] == "DIPLOMA"

    def test_cria_escolaridade_em_andamento(self):
        dados = EventFactory.escolaridade(
            cpf="12345678901",
            nivel="Medio",
            instituicao="EEEFM Teste",
            data_inicio="01/02/2023",
            serie_ano="2 serie",
            situacao="EM_ANDAMENTO",
        )
        assert dados["situacao"] == "EM_ANDAMENTO"

    def test_cria_escolaridade_pos(self):
        dados = EventFactory.escolaridade(
            cpf="12345678901",
            nivel="Pos",
            instituicao="UNESP",
            curso="MBA Gestao de Projetos",
            data_inicio="01/03/2024",
            situacao="EM_ANDAMENTO",
        )
        assert dados["nivel"] == "Pos"

    def test_escolaridade_cpf_invalido(self):
        with pytest.raises(ValueError, match="CPF"):
            EventFactory.escolaridade(
                cpf="123",
                nivel="Superior",
                instituicao="USP",
            )

    def test_escolaridade_nivel_obrigatorio(self):
        with pytest.raises(ValueError, match="Nível"):
            EventFactory.escolaridade(
                cpf="12345678901",
                nivel="",
                instituicao="USP",
            )

    def test_escolaridade_instituicao_obrigatoria(self):
        with pytest.raises(ValueError, match="Instituição"):
            EventFactory.escolaridade(
                cpf="12345678901",
                nivel="Superior",
                instituicao="",
            )

    def test_escolaridade_data_inicio_invalida(self):
        with pytest.raises(ValueError, match="início"):
            EventFactory.escolaridade(
                cpf="12345678901",
                nivel="Superior",
                instituicao="USP",
                data_inicio="2024/01/01",
            )

    def test_escolaridade_data_conclusao_invalida(self):
        with pytest.raises(ValueError, match="conclusão"):
            EventFactory.escolaridade(
                cpf="12345678901",
                nivel="Superior",
                instituicao="USP",
                data_conclusao="2022/12/15",
            )

    def test_escolaridade_niveis_variados(self):
        for nivel in ["Fundamental", "Medio", "Tecnico", "Superior", "Pos", "Mestrado", "Doutorado"]:
            dados = EventFactory.escolaridade(
                cpf="12345678901",
                nivel=nivel,
                instituicao="Universidade",
            )
            assert dados["nivel"] == nivel


# ══════════════════════════════════════════════════════════════════════
#  CHAIN — Integração com os 3 novos eventos
# ══════════════════════════════════════════════════════════════════════

class TestChainIntegration:
    def test_add_cnh_event(self):
        chain = _make_chain()
        block = chain.add_event("CNH", EventFactory.cnh(
            cpf="12345678901",
            numero_cnh="12345678901",
            categoria="B",
            data_emissao="15/03/2020",
            data_validade="15/03/2030",
        ))
        assert block.index == 1
        assert chain.get_events_by_type("CNH")

    def test_add_titulo_event(self):
        chain = _make_chain()
        block = chain.add_event("TITULO_ELEITOR", EventFactory.titulo_eleitor(
            cpf="12345678901",
            numero_titulo="123456789012",
            zona_eleitoral="0123",
            secao_eleitoral="0045",
            municipio="SP",
            uf="SP",
            data_emissao="10/06/2018",
        ))
        assert block.index == 1
        assert chain.get_events_by_type("TITULO_ELEITOR")

    def test_add_escolaridade_event(self):
        chain = _make_chain()
        block = chain.add_event("ESCOLARIDADE", EventFactory.escolaridade(
            cpf="12345678901",
            nivel="Superior",
            instituicao="USP",
        ))
        assert block.index == 1
        assert chain.get_events_by_type("ESCOLARIDADE")

    def test_all_3_events_in_timeline(self):
        chain = _make_chain()
        chain.add_event("CNH", EventFactory.cnh(
            cpf="12345678901", numero_cnh="111", categoria="B",
            data_emissao="01/01/2024", data_validade="01/01/2034",
        ))
        chain.add_event("TITULO_ELEITOR", EventFactory.titulo_eleitor(
            cpf="12345678901", numero_titulo="123456789012",
            zona_eleitoral="0123", secao_eleitoral="0045",
            municipio="SP", uf="SP", data_emissao="01/01/2024",
        ))
        chain.add_event("ESCOLARIDADE", EventFactory.escolaridade(
            cpf="12345678901", nivel="Superior", instituicao="USP",
        ))
        tl = chain.get_timeline()
        tipos = [t["tipo"] for t in tl]
        assert "CNH" in tipos
        assert "TITULO_ELEITOR" in tipos
        assert "ESCOLARIDADE" in tipos
        assert len(tl) == 4  # genesis + 3

    def test_signed_events(self):
        chain = _make_chain()
        block = chain.add_event("CNH", EventFactory.cnh(
            cpf="12345678901", numero_cnh="111", categoria="B",
            data_emissao="01/01/2024", data_validade="01/01/2034",
        ))
        assert block.has_signature()

    def test_validate_with_new_events(self):
        chain = _make_chain()
        chain.add_event("CNH", EventFactory.cnh(
            cpf="12345678901", numero_cnh="111", categoria="B",
            data_emissao="01/01/2024", data_validade="01/01/2034",
        ))
        chain.add_event("TITULO_ELEITOR", EventFactory.titulo_eleitor(
            cpf="12345678901", numero_titulo="123456789012",
            zona_eleitoral="0123", secao_eleitoral="0045",
            municipio="SP", uf="SP", data_emissao="01/01/2024",
        ))
        ok, msg = chain.validate()
        assert ok


# ══════════════════════════════════════════════════════════════════════
#  PREDICTOR — CNH, Titulo, Escolaridade
# ══════════════════════════════════════════════════════════════════════

class TestPredictorCNH:
    def test_menor_18_sem_cnh(self):
        chain = _make_chain(data_nascimento="15/03/2015")  # 11 anos
        pred = LifeEventPredictor(chain).predizer_cnh()
        assert pred is not None
        assert pred.probabilidade == 0.0
        assert "anos" in pred.timeframe

    def test_20_anos_sem_cnh(self):
        chain = _make_chain(data_nascimento="15/03/2006")  # 20 anos
        pred = LifeEventPredictor(chain).predizer_cnh()
        assert pred is not None
        assert pred.probabilidade > 0.5

    def test_com_cnh_valida(self):
        chain = _make_chain()
        chain.add_event("CNH", EventFactory.cnh(
            cpf="12345678901", numero_cnh="111", categoria="B",
            data_emissao="01/01/2024", data_validade="01/01/2034",
        ))
        pred = LifeEventPredictor(chain).predizer_cnh()
        assert pred is not None
        assert "renovação" in pred.evento.lower()

    def test_cnh_vencida(self):
        chain = _make_chain()
        chain.add_event("CNH", EventFactory.cnh(
            cpf="12345678901", numero_cnh="111", categoria="B",
            data_emissao="01/01/2010", data_validade="01/01/2020",
        ))
        pred = LifeEventPredictor(chain).predizer_cnh()
        assert pred is not None
        assert pred.probabilidade >= 0.9

    def test_cnh_suspensa(self):
        chain = _make_chain()
        chain.add_event("CNH", EventFactory.cnh(
            cpf="12345678901", numero_cnh="111", categoria="B",
            data_emissao="01/01/2024", data_validade="01/01/2034",
            situacao="SUSPENSA",
        ))
        pred = LifeEventPredictor(chain).predizer_cnh()
        assert pred is not None
        assert "reativação" in pred.evento.lower()

    def test_com_obito_nao_prediz(self):
        chain = _make_chain()
        chain.add_event("OBITO", EventFactory.obito(
            cpf="12345678901", data_obito="01/01/2050",
            cidade_obito="SP", uf_obito="SP",
        ))
        assert LifeEventPredictor(chain).predizer_cnh() is None


class TestPredictorTituloEleitor:
    def test_menor_16_sem_titulo(self):
        chain = _make_chain(data_nascimento="15/03/2015")  # 11 anos
        pred = LifeEventPredictor(chain).predizer_titulo_eleitor()
        assert pred is not None
        assert pred.probabilidade == 0.0

    def test_20_anos_sem_titulo(self):
        chain = _make_chain(data_nascimento="15/03/2006")  # 20 anos
        pred = LifeEventPredictor(chain).predizer_titulo_eleitor()
        assert pred is not None
        assert pred.probabilidade == 0.95

    def test_com_titulo_regular(self):
        chain = _make_chain()
        chain.add_event("TITULO_ELEITOR", EventFactory.titulo_eleitor(
            cpf="12345678901", numero_titulo="123456789012",
            zona_eleitoral="0123", secao_eleitoral="0045",
            municipio="SP", uf="SP", data_emissao="01/01/2024",
        ))
        pred = LifeEventPredictor(chain).predizer_titulo_eleitor()
        assert pred is not None
        assert "atualização" in pred.evento.lower()

    def test_titulo_suspenso(self):
        chain = _make_chain()
        chain.add_event("TITULO_ELEITOR", EventFactory.titulo_eleitor(
            cpf="12345678901", numero_titulo="123456789012",
            zona_eleitoral="0123", secao_eleitoral="0045",
            municipio="SP", uf="SP", data_emissao="01/01/2024",
            situacao="SUSPENSO",
        ))
        pred = LifeEventPredictor(chain).predizer_titulo_eleitor()
        assert pred is not None
        assert "reativação" in pred.evento.lower()

    def test_com_obito_nao_prediz(self):
        chain = _make_chain()
        chain.add_event("OBITO", EventFactory.obito(
            cpf="12345678901", data_obito="01/01/2050",
            cidade_obito="SP", uf_obito="SP",
        ))
        assert LifeEventPredictor(chain).predizer_titulo_eleitor() is None


class TestPredictorEscolaridade:
    def test_crianca_sem_fundamental(self):
        chain = _make_chain(data_nascimento="15/03/2015")  # 11 anos
        pred = LifeEventPredictor(chain).predizer_escolaridade()
        assert pred is not None
        assert "fundamental" in pred.evento.lower()
        assert pred.probabilidade == 0.95

    def test_adolescente_sem_fundamental(self):
        chain = _make_chain(data_nascimento="15/03/2010")  # 16 anos
        pred = LifeEventPredictor(chain).predizer_escolaridade()
        assert pred is not None
        # Sem eventos de escolaridade, o proximo nivel e fundamental
        assert "fundamental" in pred.evento.lower()

    def test_adolescente_com_fundamental_sem_medio(self):
        chain = _make_chain(data_nascimento="15/03/2010")  # 16 anos
        chain.add_event("ESCOLARIDADE", EventFactory.escolaridade(
            cpf="12345678901", nivel="Fundamental", instituicao="EMEF",
            situacao="CONCLUIDO",
        ))
        pred = LifeEventPredictor(chain).predizer_escolaridade()
        assert pred is not None
        assert "medio" in pred.evento.lower()

    def test_adulto_com_fundamental_medio_sem_superior(self):
        chain = _make_chain(data_nascimento="15/03/2000")  # 26 anos
        chain.add_event("ESCOLARIDADE", EventFactory.escolaridade(
            cpf="12345678901", nivel="Fundamental", instituicao="EMEF",
            situacao="CONCLUIDO",
        ))
        chain.add_event("ESCOLARIDADE", EventFactory.escolaridade(
            cpf="12345678901", nivel="Medio", instituicao="EEEFM",
            situacao="CONCLUIDO",
        ))
        chain.add_event("ESCOLARIDADE", EventFactory.escolaridade(
            cpf="12345678901", nivel="Tecnico", instituicao="ETEC",
            situacao="CONCLUIDO",
        ))
        pred = LifeEventPredictor(chain).predizer_escolaridade()
        assert pred is not None
        assert "superior" in pred.evento.lower()
        assert pred.probabilidade == 0.30  # 25-35 anos

    def test_com_fundamental_vai_para_medio(self):
        chain = _make_chain(data_nascimento="15/03/2008")  # 18 anos
        chain.add_event("ESCOLARIDADE", EventFactory.escolaridade(
            cpf="12345678901", nivel="Fundamental", instituicao="EMEF",
            situacao="CONCLUIDO",
        ))
        pred = LifeEventPredictor(chain).predizer_escolaridade()
        assert pred is not None
        assert "medio" in pred.evento.lower()

    def test_todos_niveis_completos(self):
        chain = _make_chain()
        for nivel in ["Fundamental", "Medio", "Tecnico", "Superior", "Pos", "Mestrado", "Doutorado"]:
            chain.add_event("ESCOLARIDADE", EventFactory.escolaridade(
                cpf="12345678901", nivel=nivel, instituicao="Uni",
            ))
        pred = LifeEventPredictor(chain).predizer_escolaridade()
        assert pred is not None
        assert "completa" in pred.evento.lower()

    def test_com_obito_nao_prediz(self):
        chain = _make_chain()
        chain.add_event("OBITO", EventFactory.obito(
            cpf="12345678901", data_obito="01/01/2050",
            cidade_obito="SP", uf_obito="SP",
        ))
        assert LifeEventPredictor(chain).predizer_escolaridade() is None


class TestPredictorRelatorio:
    def test_relatorio_inclui_novos_eventos(self):
        chain = _make_chain()
        report = LifeEventPredictor(chain).gerar_relatorio()
        eventos = [p.evento for p in report.predicoes]
        # Deve ter predicoes de CNH, titulo e escolaridade
        assert any("CNH" in e for e in eventos)
        assert any("TÍTULO" in e for e in eventos)
        assert any("ESCOLARIDADE" in e for e in eventos)


# ══════════════════════════════════════════════════════════════════════
#  API — Endpoints
# ══════════════════════════════════════════════════════════════════════

class TestAPIEndpoints:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from web_app import app, chains
        from blockchain_pf.auth import init_default_users, _users_db
        chains.clear()
        _users_db.clear()
        init_default_users()
        return TestClient(app)

    def _login(self, client):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        return r.json()["data"]["token"]

    def _create_chain(self, client):
        token = self._login(client)
        h = {"Authorization": f"Bearer {token}"}
        client.post(f"/api/chain?cpf=12345678901", json={"difficulty": 2}, headers=h)
        client.post("/api/chain/12345678901/event/nascimento", json={
            "cpf": "12345678901", "nome_completo": "Maria Clara",
            "data_nascimento": "15/03/2000", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP", "nome_mae": "Ana Paula",
        }, headers=h)
        return token, h

    def test_add_cnh_endpoint(self, client):
        token, h = self._create_chain(client)
        r = client.post("/api/chain/12345678901/event/cnh", json={
            "cpf": "12345678901",
            "numero_cnh": "12345678901",
            "categoria": "B",
            "data_emissao": "15/03/2020",
            "data_validade": "15/03/2030",
        }, headers=h)
        assert r.status_code == 201
        assert r.json()["data"]["assinado"]

    def test_add_titulo_endpoint(self, client):
        token, h = self._create_chain(client)
        r = client.post("/api/chain/12345678901/event/titulo_eleitor", json={
            "cpf": "12345678901",
            "numero_titulo": "123456789012",
            "zona_eleitoral": "0123",
            "secao_eleitoral": "0045",
            "municipio": "Sao Paulo",
            "uf": "SP",
            "data_emissao": "10/06/2018",
        }, headers=h)
        assert r.status_code == 201
        assert r.json()["data"]["assinado"]

    def test_add_escolaridade_endpoint(self, client):
        token, h = self._create_chain(client)
        r = client.post("/api/chain/12345678901/event/escolaridade", json={
            "cpf": "12345678901",
            "nivel": "Superior",
            "instituicao": "USP",
        }, headers=h)
        assert r.status_code == 201
        assert r.json()["data"]["assinado"]

    def test_cnh_endpoint_no_auth(self, client):
        self._create_chain(client)
        r = client.post("/api/chain/12345678901/event/cnh", json={
            "cpf": "12345678901", "numero_cnh": "111", "categoria": "B",
            "data_emissao": "01/01/2024", "data_validade": "01/01/2034",
        })
        assert r.status_code == 401

    def test_titulo_endpoint_no_auth(self, client):
        self._create_chain(client)
        r = client.post("/api/chain/12345678901/event/titulo_eleitor", json={
            "cpf": "12345678901", "numero_titulo": "123456789012",
            "zona_eleitoral": "0123", "secao_eleitoral": "0045",
            "municipio": "SP", "uf": "SP", "data_emissao": "01/01/2024",
        })
        assert r.status_code == 401

    def test_escolaridade_endpoint_no_auth(self, client):
        self._create_chain(client)
        r = client.post("/api/chain/12345678901/event/escolaridade", json={
            "cpf": "12345678901", "nivel": "Superior", "instituicao": "USP",
        })
        assert r.status_code == 401

    def test_cnh_endpoint_validation_error(self, client):
        token, h = self._create_chain(client)
        r = client.post("/api/chain/12345678901/event/cnh", json={
            "cpf": "123",  # invalido
            "numero_cnh": "111", "categoria": "B",
            "data_emissao": "01/01/2024", "data_validade": "01/01/2034",
        }, headers=h)
        assert r.status_code == 400
