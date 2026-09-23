"""Testes completos para blockchain_pf/database.py.

Cobre: Chains, Imoveis, Veiculos, Users, Graph Nodes/Edges, Settings, Stats,
       Context Manager, close, __del__, __repr__.
"""
import json
import os
import tempfile
import threading
import time

import pytest

from blockchain_pf.database import Database


@pytest.fixture
def db():
    """Cria um Database temporario para cada teste."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def db_with_data(db):
    """Database com dados de exemplo pre-populados."""
    db.save_chain("11122233344", 2, {"chain": [{"index": 0}]})
    db.save_chain("55566677788", 3, {"chain": [{"index": 0}, {"index": 1}]})
    db.save_user("admin", "hash_abc", "admin")
    db.save_user("operador", "hash_def", "user")
    db.save_graph_node("11122233344", "Joao Silva", True, 0)
    db.save_graph_node("55566677788", "Maria Santos", True, 1)
    db.save_graph_edge("11122233344", "55566677788", "CONJUGE", True, 1, time.time(), {"regime": "parcial"})
    db.save_graph_edge("11122233344", "99988877766", "PAI", True, 0, time.time(), {})
    db.set_setting("versao", "2.0")
    return db


# ══════════════════════════════════════════════════════════════════════
#  CHAINS
# ══════════════════════════════════════════════════════════════════════

class TestChains:
    def test_save_and_load_chain(self, db):
        data = {"chain": [{"index": 0, "hash": "abc"}]}
        db.save_chain("12345678901", 2, data)
        loaded = db.load_chain("12345678901")
        assert loaded is not None
        assert loaded == data

    def test_load_chain_not_found(self, db):
        assert db.load_chain("00000000000") is None

    def test_load_all_chains_empty(self, db):
        assert db.load_all_chains() == {}

    def test_load_all_chains_multiple(self, db_with_data):
        all_chains = db_with_data.load_all_chains()
        assert len(all_chains) == 2
        assert "11122233344" in all_chains
        assert "55566677788" in all_chains

    def test_chain_exists(self, db):
        assert not db.chain_exists("12345678901")
        db.save_chain("12345678901", 2, {"chain": []})
        assert db.chain_exists("12345678901")

    def test_delete_chain(self, db):
        db.save_chain("12345678901", 2, {"chain": []})
        assert db.delete_chain("12345678901")
        assert db.load_chain("12345678901") is None

    def test_delete_chain_not_found(self, db):
        assert not db.delete_chain("00000000000")

    def test_list_chains_empty(self, db):
        assert db.list_chains() == []

    def test_list_chains(self, db_with_data):
        result = db_with_data.list_chains()
        assert len(result) == 2
        cpfs = {r["cpf"] for r in result}
        assert "11122233344" in cpfs
        assert "55566677788" in cpfs

    def test_upsert_chain(self, db):
        """ON CONFLICT atualiza existente."""
        data_v1 = {"chain": [{"index": 0}]}
        data_v2 = {"chain": [{"index": 0}, {"index": 1}]}
        db.save_chain("123", 2, data_v1)
        db.save_chain("123", 3, data_v2)
        loaded = db.load_chain("123")
        assert loaded == data_v2


# ══════════════════════════════════════════════════════════════════════
#  IMOVEIS
# ══════════════════════════════════════════════════════════════════════

class TestImoveis:
    def test_save_and_load_imovel(self, db):
        data = {"endereco": {"logradouro": "Rua A"}}
        db.save_imovel("MAT-001", 2, data)
        loaded = db.load_imovel("MAT-001")
        assert loaded == data

    def test_load_imovel_not_found(self, db):
        assert db.load_imovel("MAT-999") is None

    def test_load_all_imoveis_empty(self, db):
        assert db.load_all_imoveis() == {}

    def test_load_all_imoveis(self, db):
        db.save_imovel("MAT-001", 2, {"a": 1})
        db.save_imovel("MAT-002", 2, {"b": 2})
        result = db.load_all_imoveis()
        assert len(result) == 2
        assert "MAT-001" in result
        assert "MAT-002" in result

    def test_delete_imovel(self, db):
        db.save_imovel("MAT-001", 2, {"a": 1})
        assert db.delete_imovel("MAT-001")
        assert db.load_imovel("MAT-001") is None

    def test_delete_imovel_not_found(self, db):
        assert not db.delete_imovel("MAT-999")

    def test_upsert_imovel(self, db):
        db.save_imovel("MAT-001", 2, {"v": 1})
        db.save_imovel("MAT-001", 3, {"v": 2})
        assert db.load_imovel("MAT-001") == {"v": 2}


# ══════════════════════════════════════════════════════════════════════
#  VEICULOS
# ══════════════════════════════════════════════════════════════════════

class TestVeiculos:
    def test_save_and_load_veiculo(self, db):
        data = {"marca": "Fiat", "modelo": "Argo"}
        db.save_veiculo("ABC1D23", 2, data)
        loaded = db.load_veiculo("ABC1D23")
        assert loaded == data

    def test_load_veiculo_not_found(self, db):
        assert db.load_veiculo("XYZ9999") is None

    def test_load_all_veiculos_empty(self, db):
        assert db.load_all_veiculos() == {}

    def test_load_all_veiculos(self, db):
        db.save_veiculo("ABC1D23", 2, {"marca": "Fiat"})
        db.save_veiculo("DEF4E56", 2, {"marca": "VW"})
        result = db.load_all_veiculos()
        assert len(result) == 2

    def test_delete_veiculo(self, db):
        db.save_veiculo("ABC1D23", 2, {"marca": "Fiat"})
        assert db.delete_veiculo("ABC1D23")
        assert db.load_veiculo("ABC1D23") is None

    def test_delete_veiculo_not_found(self, db):
        assert not db.delete_veiculo("XYZ9999")

    def test_upsert_veiculo(self, db):
        db.save_veiculo("ABC1D23", 2, {"v": 1})
        db.save_veiculo("ABC1D23", 3, {"v": 2})
        assert db.load_veiculo("ABC1D23") == {"v": 2}


# ══════════════════════════════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════════════════════════════

class TestUsers:
    def test_save_and_load_user(self, db):
        db.save_user("joao", "hash123", "admin")
        user = db.load_user("joao")
        assert user is not None
        assert user["username"] == "joao"
        assert user["password_hash"] == "hash123"
        assert user["role"] == "admin"
        assert user["ativo"] is True

    def test_load_user_not_found(self, db):
        assert db.load_user("ghost") is None

    def test_load_all_users_empty(self, db):
        assert db.load_all_users() == []

    def test_load_all_users(self, db_with_data):
        users = db_with_data.load_all_users()
        assert len(users) == 2
        usernames = {u["username"] for u in users}
        assert "admin" in usernames
        assert "operador" in usernames

    def test_delete_user(self, db):
        db.save_user("joao", "hash123", "user")
        assert db.delete_user("joao")
        assert db.load_user("joao") is None

    def test_delete_user_not_found(self, db):
        assert not db.delete_user("ghost")

    def test_upsert_user(self, db):
        db.save_user("joao", "hash1", "user")
        db.save_user("joao", "hash2", "admin")
        user = db.load_user("joao")
        assert user["password_hash"] == "hash2"
        assert user["role"] == "admin"

    def test_user_inativo(self, db):
        db.save_user("joao", "hash1", "user", ativo=False)
        user = db.load_user("joao")
        assert user["ativo"] is False


# ══════════════════════════════════════════════════════════════════════
#  GRAPH NODES
# ══════════════════════════════════════════════════════════════════════

class TestGraphNodes:
    def test_save_and_load_nodes(self, db):
        db.save_graph_node("11111111111", "Ana", True, 0)
        db.save_graph_node("22222222222", "Bruno", False, 1)
        nodes = db.load_all_graph_nodes()
        assert len(nodes) == 2
        by_cpf = {n["cpf"]: n for n in nodes}
        assert by_cpf["11111111111"]["nome"] == "Ana"
        assert by_cpf["11111111111"]["ativo"] is True
        assert by_cpf["22222222222"]["ativo"] is False

    def test_upsert_node(self, db):
        db.save_graph_node("11111111111", "Ana", True, 0)
        db.save_graph_node("11111111111", "Ana Maria", False, 2)
        nodes = db.load_all_graph_nodes()
        assert len(nodes) == 1
        assert nodes[0]["nome"] == "Ana Maria"
        assert nodes[0]["chain_index"] == 2

    def test_load_all_nodes_empty(self, db):
        assert db.load_all_graph_nodes() == []


# ══════════════════════════════════════════════════════════════════════
#  GRAPH EDGES
# ══════════════════════════════════════════════════════════════════════

class TestGraphEdges:
    def test_save_and_load_edges(self, db):
        edge_id = db.save_graph_edge("CPF_A", "CPF_B", "CONJUGE", True, 1, 100.0, {"regime": "parcial"})
        assert edge_id > 0
        edges = db.load_all_graph_edges()
        assert len(edges) == 1
        assert edges[0]["from_cpf"] == "CPF_A"
        assert edges[0]["to_cpf"] == "CPF_B"
        assert edges[0]["tipo"] == "CONJUGE"
        assert edges[0]["ativo"] is True
        assert edges[0]["block_index"] == 1
        assert edges[0]["dados"]["regime"] == "parcial"

    def test_deactivate_edges(self, db):
        db.save_graph_edge("A", "B", "CONJUGE", True, 1, 0, {})
        db.save_graph_edge("A", "B", "CONJUGE", True, 2, 0, {})
        count = db.deactivate_graph_edges("A", "B", "CONJUGE")
        assert count == 2
        edges = db.load_all_graph_edges()
        assert all(not e["ativo"] for e in edges)

    def test_deactivate_edges_reverse_direction(self, db):
        db.save_graph_edge("B", "A", "CONJUGE", True, 1, 0, {})
        count = db.deactivate_graph_edges("A", "B", "CONJUGE")
        assert count == 1

    def test_deactivate_by_id(self, db):
        eid = db.save_graph_edge("A", "B", "PAI", True, 0, 0, {})
        db.deactivate_graph_edge_by_id(eid)
        edges = db.load_all_graph_edges()
        assert edges[0]["ativo"] is False

    def test_delete_all_edges_for_cpf(self, db):
        db.save_graph_edge("A", "B", "CONJUGE", True, 1, 0, {})
        db.save_graph_edge("A", "C", "PAI", True, 2, 0, {})
        db.save_graph_edge("B", "D", "FILHO", True, 3, 0, {})
        count = db.delete_all_graph_edges("A")
        assert count == 2  # A->B e A->C removidas, B->D nao
        edges = db.load_all_graph_edges()
        assert len(edges) == 1

    def test_load_all_edges_empty(self, db):
        assert db.load_all_graph_edges() == []


# ══════════════════════════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════════════════════════

class TestSettings:
    def test_set_and_get(self, db):
        db.set_setting("chave", "valor")
        assert db.get_setting("chave") == "valor"

    def test_get_default(self, db):
        assert db.get_setting("inexistente", "padrao") == "padrao"

    def test_get_default_empty(self, db):
        assert db.get_setting("inexistente") == ""

    def test_upsert_setting(self, db):
        db.set_setting("chave", "v1")
        db.set_setting("chave", "v2")
        assert db.get_setting("chave") == "v2"

    def test_multiple_settings(self, db):
        db.set_setting("a", "1")
        db.set_setting("b", "2")
        assert db.get_setting("a") == "1"
        assert db.get_setting("b") == "2"


# ══════════════════════════════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════════════════════════════

class TestStats:
    def test_stats_empty(self, db):
        s = db.stats()
        assert s["chains"] == 0
        assert s["users"] == 0
        assert s["graph_nodes"] == 0
        assert s["graph_edges"] == 0
        assert s["db_path"] == db.db_path
        assert isinstance(s["db_size_kb"], int)

    def test_stats_populated(self, db_with_data):
        s = db_with_data.stats()
        assert s["chains"] == 2
        assert s["users"] == 2
        assert s["graph_nodes"] == 2
        assert s["graph_edges"] == 2

    def test_stats_db_size(self, db):
        db.save_chain("123", 2, {"data": "x" * 2048})
        s = db.stats()
        assert s["db_size_kb"] >= 0


# ══════════════════════════════════════════════════════════════════════
#  CONTEXT MANAGER / CLOSE / REPR
# ══════════════════════════════════════════════════════════════════════

class TestLifecycle:
    def test_context_manager(self, tmp_path):
        path = str(tmp_path / "ctx.db")
        with Database(path) as database:
            database.save_chain("123", 2, {"x": 1})
            assert database.load_chain("123") == {"x": 1}

    def test_close(self, tmp_path):
        path = str(tmp_path / "close.db")
        database = Database(path)
        # Force a connection to be created
        database._get_conn()
        assert len(database._all_conns) == 1
        database.close()
        assert len(database._all_conns) == 0

    def test_close_multiple_threads(self, tmp_path):
        """Close deve fechar conexoes de todas as threads."""
        path = str(tmp_path / "multi.db")
        database = Database(path)
        # _init_schema() ja criou 1 conexao no __init__
        initial = len(database._all_conns)
        errors = []

        def worker():
            try:
                database._get_conn()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(database._all_conns) == initial + 3
        database.close()
        assert len(database._all_conns) == 0

    def test_repr(self, db):
        r = repr(db)
        assert "Database" in r
        assert db.db_path in r


# ══════════════════════════════════════════════════════════════════════
#  INTEGRITY / ATOMICITY
# ══════════════════════════════════════════════════════════════════════

class TestIntegrity:
    def test_transaction_rollback_on_error(self, db):
        """Se uma operacao dentro de _transaction falha, deve fazer rollback."""
        db.save_chain("123", 2, {"v": 1})
        with pytest.raises(ValueError):
            with db._transaction() as conn:
                conn.execute("INSERT INTO chains (domain, id, difficulty, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                             ("pf", "456", 2, "bad", 0, 0))
                raise ValueError("simulated error")
        # A cadeia original nao deve ter sido afetada
        assert db.load_chain("123") == {"v": 1}

    def test_concurrent_writes(self, tmp_path):
        """Varias threads escrevendo nao devem corromper o banco."""
        path = str(tmp_path / "concurrent.db")
        database = Database(path)
        errors = []

        def writer(i):
            try:
                database.save_chain(f"{i:011d}", 2, {"thread": i})
                database.save_user(f"user{i}", f"hash{i}", "user")
                database.save_graph_node(f"{i:011d}", f"Pessoa {i}", True, i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(database.load_all_chains()) == 10
        assert len(database.load_all_users()) == 10
        assert len(database.load_all_graph_nodes()) == 10
        database.close()


# ══════════════════════════════════════════════════════════════════════
#  F3/F4: DOMAIN GENERICO + REFERENCIAS + REOPEN ROUND-TRIP
# ══════════════════════════════════════════════════════════════════════

class TestGenericDomainChains:
    def test_save_load_delete_domain(self, db):
        db.save_domain_chain("an", "anim-001", 2, {"chain": [{"index": 0}]})
        assert db.load_domain_chain("an", "anim-001") == {"chain": [{"index": 0}]}
        assert db.domain_chain_exists("an", "anim-001")
        assert db.domain_chain_exists("pf", "anim-001") is False
        assert db.delete_domain_chain("an", "anim-001")
        assert not db.domain_chain_exists("an", "anim-001")

    def test_load_all_domains_isolated_by_domain(self, db):
        db.save_domain_chain("co", "10000000000001", 2, {"c": 1})
        db.save_domain_chain("an", "x1", 2, {"c": 2})
        db.save_domain_chain("an", "x2", 2, {"c": 3})
        assert set(db.load_all_domain_chains("an")) == {"x1", "x2"}
        assert set(db.load_all_domain_chains("co")) == {"10000000000001"}
        assert len(db.list_domain_chains("an")) == 2


REF_GENERICO = {
    "entidade_origem_tipo": "PF", "entidade_origem_id": "11122233344",
    "entidade_destino_tipo": "MO", "entidade_destino_id": "ABC1D23",
    "tipo_vinculo": "PROPRIETARIO", "timestamp": 1234.5, "ativo": True,
    "hash_cadeia_origem": "h1", "hash_cadeia_destino": "h2",
    "dados": {"extra": 1},
}
REF_LEGADO = {
    "cpf": "11122233344", "matricula": "M-001",
    "tipo_vinculo": "PROPRIETARIO", "timestamp": 999.0, "ativo": True,
    "dados": {},
}


class TestReferences:
    def test_save_reference_generico_roundtrip(self, db):
        db.save_reference("PF", REF_GENERICO)
        refs = db.load_all_references("PF")
        assert len(refs) == 1
        row = refs[0]
        assert row["origem_tipo"] == "PF" and row["origem_id"] == "11122233344"
        assert row["destino_tipo"] == "MO" and row["destino_id"] == "ABC1D23"
        assert row["ativo"] is True
        assert row["ref_data"]["tipo_vinculo"] == "PROPRIETARIO"

    def test_save_reference_legado_vira_pf_im(self, db):
        db.save_reference("IM", REF_LEGADO)
        row = db.load_all_references("IM")[0]
        assert row["origem_tipo"] == "PF" and row["origem_id"] == "11122233344"
        assert row["destino_tipo"] == "IM" and row["destino_id"] == "M-001"

    def test_load_all_references_filter_domain(self, db):
        db.save_reference("PF", REF_GENERICO)
        db.save_reference("IM", REF_LEGADO)
        assert len(db.load_all_references("PF")) == 1
        assert len(db.load_all_references()) == 2

    def test_clear_references_by_domain(self, db):
        db.save_reference("PF", REF_GENERICO)
        db.save_reference("IM", REF_LEGADO)
        removed = db.clear_references("PF")
        assert removed == 1
        assert len(db.load_all_references()) == 1

    def test_reopen_roundtrip(self, tmp_path):
        path = str(tmp_path / "reopen.db")
        db1 = Database(path)
        db1.save_domain_chain("im", "M-001", 2, {"chain": [{"index": 0}]})
        db1.save_user("operador", "hash", "user")
        db1.save_reference("IM", REF_LEGADO)
        db1.save_graph_node("11122233344", "Maria", True, 0)
        db1.close()

        db2 = Database(path)
        assert db2.load_domain_chain("im", "M-001") == {"chain": [{"index": 0}]}
        assert db2.load_user("operador") is not None
        assert len(db2.load_all_references()) == 1
        assert len(db2.load_all_graph_nodes()) == 1
        db2.close()
