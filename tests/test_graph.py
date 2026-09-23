"""Testes unitarios para blockchain_pf/graph.py"""

import pytest
from blockchain_pf.graph import RelationshipGraph, Node, Edge, RelationType
from blockchain_pf.chain import Blockchain


@pytest.fixture
def graph():
    return RelationshipGraph()


@pytest.fixture
def graph_with_family():
    """Grafo com familia de exemplo."""
    g = RelationshipGraph()
    # Pais
    g.add_node("11111111111", "Joao Silva")
    g.add_node("22222222222", "Ana Santos")
    # Filho
    g.add_node("33333333333", "Pedro Silva")
    # Arestas de parentela
    g.add_edge("11111111111", "33333333333", RelationType.PAI)
    g.add_edge("22222222222", "33333333333", RelationType.MAE)
    return g


# ── Nodes ──────────────────────────────────────────────────────────────

class TestNodes:
    def test_add_node(self, graph):
        node = graph.add_node("12345678901", "Maria")
        assert node.cpf == "12345678901"
        assert node.nome == "Maria"
        assert node.ativo is True

    def test_add_node_strips_cpf(self, graph):
        node = graph.add_node("123.456.789-01", "Maria")
        assert node.cpf == "12345678901"

    def test_add_node_updates_name(self, graph):
        graph.add_node("12345678901", "Maria")
        node = graph.add_node("12345678901", "Maria Santos")
        assert node.nome == "Maria Santos"

    def test_get_node(self, graph):
        graph.add_node("12345678901", "Maria")
        assert graph.get_node("12345678901") is not None
        assert graph.get_node("00000000000") is None

    def test_mark_deceased(self, graph):
        graph.add_node("12345678901", "Maria")
        graph.mark_deceased("12345678901")
        assert graph.nodes["12345678901"].ativo is False

    def test_node_to_dict(self, graph):
        node = graph.add_node("12345678901", "Maria")
        d = node.to_dict()
        assert d["cpf"] == "12345678901"
        assert d["nome"] == "Maria"


# ── Edges ──────────────────────────────────────────────────────────────

class TestEdges:
    def test_add_edge(self, graph):
        graph.add_node("11111111111", "A")
        graph.add_node("22222222222", "B")
        edge = graph.add_edge("11111111111", "22222222222", RelationType.CONJUGE)
        assert edge.tipo == RelationType.CONJUGE
        assert edge.ativo is True

    def test_add_edge_strips_cpfs(self, graph):
        graph.add_node("11111111111", "A")
        graph.add_node("22222222222", "B")
        edge = graph.add_edge("111.111.111-11", "222.222.222-22", RelationType.CONJUGE)
        assert edge.from_cpf == "11111111111"
        assert edge.to_cpf == "22222222222"

    def test_deactivate_edges(self, graph_with_family):
        g = graph_with_family
        g.add_node("44444444444", "Esposa")
        g.add_edge("33333333333", "44444444444", RelationType.CONJUGE)
        count = g.deactivate_edges("33333333333", "44444444444", RelationType.CONJUGE)
        assert count == 1
        conjuges = g.get_conjuges("33333333333")
        assert len(conjuges) == 0

    def test_edge_to_dict(self, graph):
        graph.add_node("11111111111", "A")
        graph.add_node("22222222222", "B")
        edge = graph.add_edge("11111111111", "22222222222", RelationType.CONJUGE)
        d = edge.to_dict()
        assert d["tipo"] == "CONJUGE"


# ── Queries ────────────────────────────────────────────────────────────

class TestQueries:
    def test_get_conjuges(self, graph):
        graph.add_node("11111111111", "Maria")
        graph.add_node("22222222222", "Pedro")
        graph.add_edge("11111111111", "22222222222", RelationType.CONJUGE)
        conjuges = graph.get_conjuges("11111111111")
        assert len(conjuges) == 1
        assert conjuges[0].cpf == "22222222222"

    def test_get_conjuges_bidirectional(self, graph):
        graph.add_node("11111111111", "Maria")
        graph.add_node("22222222222", "Pedro")
        graph.add_edge("11111111111", "22222222222", RelationType.CONJUGE)
        conjuges_a = graph.get_conjuges("11111111111")
        conjuges_b = graph.get_conjuges("22222222222")
        assert len(conjuges_a) == 1
        assert len(conjuges_b) == 1

    def test_get_ex_conjuges(self, graph):
        graph.add_node("11111111111", "Maria")
        graph.add_node("22222222222", "Pedro")
        e = graph.add_edge("11111111111", "22222222222", RelationType.CONJUGE)
        e.ativo = False
        graph.add_edge("11111111111", "22222222222", RelationType.EX_CONJUGE)
        ex = graph.get_ex_conjuges("11111111111")
        assert len(ex) == 1
        assert ex[0].cpf == "22222222222"

    def test_get_filhos(self, graph_with_family):
        filhos = graph_with_family.get_filhos("11111111111")
        assert len(filhos) == 1
        assert filhos[0].cpf == "33333333333"

    def test_get_pais(self, graph_with_family):
        pais = graph_with_family.get_pais("33333333333")
        assert len(pais) == 2
        cpfs = {p.cpf for p in pais}
        assert "11111111111" in cpfs
        assert "22222222222" in cpfs

    def test_getirmaos(self):
        g = RelationshipGraph()
        g.add_node("11111111111", "Pai")
        g.add_node("22222222222", "Mae")
        g.add_node("33333333333", "Filho1")
        g.add_node("44444444444", "Filho2")
        g.add_edge("11111111111", "33333333333", RelationType.PAI)
        g.add_edge("22222222222", "33333333333", RelationType.MAE)
        g.add_edge("11111111111", "44444444444", RelationType.PAI)
        g.add_edge("22222222222", "44444444444", RelationType.MAE)
        irmaos = g.getirmaos("33333333333")
        assert len(irmaos) == 1
        assert irmaos[0].cpf == "44444444444"

    def test_get_family_network(self, graph_with_family):
        net = graph_with_family.get_family_network("33333333333", depth=2)
        assert net["estatisticas"]["total_pessoas"] == 3

    def test_find_path(self, graph):
        graph.add_node("11111111111", "A")
        graph.add_node("22222222222", "B")
        graph.add_node("33333333333", "C")
        graph.add_edge("11111111111", "22222222222", RelationType.CONJUGE)
        graph.add_edge("22222222222", "33333333333", RelationType.FILHO)
        path = graph.find_path("11111111111", "33333333333")
        assert path is not None
        assert len(path) == 3

    def test_find_path_same_node(self, graph):
        graph.add_node("11111111111", "A")
        path = graph.find_path("11111111111", "11111111111")
        assert path is not None
        assert len(path) == 1

    def test_find_path_no_connection(self, graph):
        graph.add_node("11111111111", "A")
        graph.add_node("22222222222", "B")
        path = graph.find_path("11111111111", "22222222222")
        assert path is None


# ── Stats ──────────────────────────────────────────────────────────────

class TestStats:
    def test_stats(self, graph):
        graph.add_node("11111111111", "A")
        graph.add_node("22222222222", "B")
        graph.add_edge("11111111111", "22222222222", RelationType.CONJUGE)
        s = graph.stats()
        assert s["total_pessoas"] == 2
        assert s["ativos"] == 2
        assert s["total_relacionamentos"] == 1

    def test_stats_after_death(self, graph):
        graph.add_node("11111111111", "A")
        graph.mark_deceased("11111111111")
        s = graph.stats()
        assert s["falecidos"] == 1


# ── Serialization ──────────────────────────────────────────────────────

class TestSerialization:
    def test_to_dict(self, graph_with_family):
        d = graph_with_family.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert len(d["nodes"]) == 3

    def test_repr(self, graph):
        r = repr(graph)
        assert "RelationshipGraph" in r


# ── Integration with Blockchain ────────────────────────────────────────

class TestBlockchainIntegration:
    def test_genesis_adds_node(self):
        g = RelationshipGraph()
        chain = Blockchain(difficulty=1, graph=g)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Maria Clara",
            "data_nascimento": "01/01/2000", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Ana Paula",
        })
        assert "12345678901" in g.nodes
        assert g.nodes["12345678901"].nome == "Maria Clara"

    def test_casamento_adds_conjuge(self):
        g = RelationshipGraph()
        chain = Blockchain(difficulty=1, graph=g)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Maria",
            "data_nascimento": "01/01/2000", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Ana",
        })
        chain.add_event("CASAMENTO", {
            "evento_tipo": "CASAMENTO", "cpf": "12345678901",
            "nome_conjuge": "Pedro", "cpf_conjuge": "98765432100",
            "data_casamento": "01/01/2022", "regime_bens": "COMUNHAO_PARCIAL",
        })
        conjuges = g.get_conjuges("12345678901")
        assert len(conjuges) == 1
        assert conjuges[0].cpf == "98765432100"

    def test_divorcio_remove_conjuge(self):
        g = RelationshipGraph()
        chain = Blockchain(difficulty=1, graph=g)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Maria",
            "data_nascimento": "01/01/2000", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Ana",
        })
        chain.add_event("CASAMENTO", {
            "evento_tipo": "CASAMENTO", "cpf": "12345678901",
            "nome_conjuge": "Pedro", "cpf_conjuge": "98765432100",
            "data_casamento": "01/01/2022",
        })
        chain.add_event("DIVORCIO", {
            "evento_tipo": "DIVORCIO", "cpf": "12345678901",
            "data_divorcio": "01/01/2025",
        })
        conjuges = g.get_conjuges("12345678901")
        assert len(conjuges) == 0
        ex = g.get_ex_conjuges("12345678901")
        assert len(ex) == 1

    def test_obito_marca_falecido(self):
        g = RelationshipGraph()
        chain = Blockchain(difficulty=1, graph=g)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Maria",
            "data_nascimento": "01/01/2000", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Ana",
        })
        chain.add_event("OBITO", {
            "evento_tipo": "OBITO", "cpf": "12345678901",
            "data_obito": "01/01/2050",
            "cidade_obito": "SP", "uf_obito": "SP",
        })
        assert g.nodes["12345678901"].ativo is False

    def test_disvinculacao_paterna(self):
        g = RelationshipGraph()
        # Adiciona pais manualmente
        g.add_node("11111111111", "Pai")
        g.add_node("22222222222", "Mae")
        g.add_node("33333333333", "Filho")
        g.add_edge("11111111111", "33333333333", RelationType.PAI)
        g.add_edge("22222222222", "33333333333", RelationType.MAE)
        # Simula disvinculacao
        chain = Blockchain(difficulty=1, graph=g)
        chain.chain = [type("FakeBlock", (), {"index": 0, "data": {"payload": {"cpf": "33333333333"}}})()]
        chain._update_graph_on_event("DISVINC_PATerna", {"cpf": "33333333333"}, 0)
        # Pai ativo deve ser desativado
        active_edges = g._get_active_edges("33333333333")
        pai_edges = [e for e in active_edges if e.tipo == RelationType.PAI]
        assert len(pai_edges) == 0

    def test_graph_property(self):
        g = RelationshipGraph()
        chain = Blockchain(difficulty=1, graph=g)
        assert chain.graph is g

    def test_no_graph_by_default(self):
        chain = Blockchain(difficulty=1)
        assert chain.graph is None

    def test_multiplos_casamentos_e_divorcios(self):
        g = RelationshipGraph()
        chain = Blockchain(difficulty=1, graph=g)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Maria",
            "data_nascimento": "01/01/2000", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Ana",
        })
        # 1o casamento
        chain.add_event("CASAMENTO", {
            "evento_tipo": "CASAMENTO", "cpf": "12345678901",
            "nome_conjuge": "Pedro", "cpf_conjuge": "98765432100",
            "data_casamento": "01/01/2022",
        })
        # 1o divorcio
        chain.add_event("DIVORCIO", {
            "evento_tipo": "DIVORCIO", "cpf": "12345678901",
            "data_divorcio": "01/01/2024",
        })
        # 2o casamento
        chain.add_event("CASAMENTO", {
            "evento_tipo": "CASAMENTO", "cpf": "12345678901",
            "nome_conjuge": "Lucas", "cpf_conjuge": "77777777777",
            "data_casamento": "01/06/2024",
        })
        # Verifica
        conjuges = g.get_conjuges("12345678901")
        assert len(conjuges) == 1
        assert conjuges[0].cpf == "77777777777"
        ex = g.get_ex_conjuges("12345678901")
        assert len(ex) == 1
