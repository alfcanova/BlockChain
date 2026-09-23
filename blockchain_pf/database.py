"""
blockchain_pf/database.py
Persistencia SQLite para chains (7 dominios), referencias cruzadas,
usuarios, grafo de relacionamentos e settings.

Banco centralizado: `database/blockchain.db` (projeto).

Garante que dados sobrevivem a reinicios do servidor.
Todas as operacoes sao atomicas (commit apos cada operacao).
"""

import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Optional

# Caminho padrao: <projeto>/database/blockchain.db
# Override via env BLOCKCHAIN_DB (ex.: testes com banco temporario).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.environ.get("BLOCKCHAIN_DB", os.path.join(_PROJECT_ROOT, "database", "blockchain.db"))

DOMAINS = ("pf", "im", "mo", "co", "em", "ac", "an")

_MUNICIPIOS_PATH = os.path.join(_PROJECT_ROOT, "database", "ibge_municipios.json")


def _carregar_municipios_json() -> list[dict]:
    """Carrega a tabela IBGE (id, uf, nome, capital) do arquivo JSON do projeto."""
    try:
        with open(_MUNICIPIOS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return [{"id": int(m["id"]), "uf": m["uf"], "nome": m["nome"],
             "capital": int(m.get("capital", 0))} for m in data]


class Database:
    """
    Camada de persistencia SQLite.

    Tabelas:
      - chains:            (domain, id) → JSON da cadeia completa
      - cross_references:  vinculos cross-chain (fonte da verdade em ref_data JSON)
      - users:             username → password_hash, role
      - graph_nodes:       cpf → nome, ativo
      - graph_edges:       from_cpf, to_cpf, tipo, ativo, block_index, dados
      - settings:          key → value (meta-dados do servidor)
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._local = threading.local()
        self._all_conns: list[sqlite3.Connection] = []
        self._init_schema()

    def __del__(self) -> None:
        """Fecha todas as conexoes ao ser destruido."""
        self.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ── Conexao ────────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Retorna conexao SQLite (uma por thread)."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._all_conns.append(self._local.conn)
        return self._local.conn

    @contextmanager
    def _transaction(self):
        """Context manager para transacao atomicas."""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # ── Schema ─────────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        """Cria tabelas se nao existirem."""
        with self._transaction() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS chains (
                    domain TEXT NOT NULL,
                    id TEXT NOT NULL,
                    difficulty INTEGER NOT NULL DEFAULT 2,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (domain, id)
                );

                CREATE TABLE IF NOT EXISTS cross_references (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    origem_tipo TEXT NOT NULL DEFAULT '',
                    origem_id TEXT NOT NULL DEFAULT '',
                    destino_tipo TEXT NOT NULL DEFAULT '',
                    destino_id TEXT NOT NULL DEFAULT '',
                    tipo_vinculo TEXT NOT NULL DEFAULT '',
                    timestamp REAL NOT NULL DEFAULT 0,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    ref_data TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'admin',
                    ativo INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS graph_nodes (
                    cpf TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    chain_index INTEGER
                );

                CREATE TABLE IF NOT EXISTS graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_cpf TEXT NOT NULL,
                    to_cpf TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    block_index INTEGER,
                    timestamp REAL NOT NULL,
                    dados TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS municipios (
                    codigo_ibge INTEGER PRIMARY KEY,
                    uf TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    capital INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_chains_domain ON chains(domain);
                CREATE INDEX IF NOT EXISTS idx_edges_from ON graph_edges(from_cpf);
                CREATE INDEX IF NOT EXISTS idx_edges_to ON graph_edges(to_cpf);
                CREATE INDEX IF NOT EXISTS idx_edges_tipo ON graph_edges(tipo);
                CREATE INDEX IF NOT EXISTS idx_xrefs_domain ON cross_references(domain);
                CREATE INDEX IF NOT EXISTS idx_xrefs_origem ON cross_references(origem_id);
                CREATE INDEX IF NOT EXISTS idx_xrefs_destino ON cross_references(destino_id);
                CREATE INDEX IF NOT EXISTS idx_municipios_uf ON municipios(uf);
            """)
            self._migrate_users_table(conn)
            self._seed_municipios()

    def _migrate_users_table(self, conn) -> None:
        """Adiciona colunas de autoridade (nivel/escopo/uf/cidade) em DBs antigos."""
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        for col, ddl in [
            ("nivel", "ALTER TABLE users ADD COLUMN nivel INTEGER NOT NULL DEFAULT 0"),
            ("escopo", "ALTER TABLE users ADD COLUMN escopo TEXT NOT NULL DEFAULT ''"),
            ("uf", "ALTER TABLE users ADD COLUMN uf TEXT NOT NULL DEFAULT ''"),
            ("cidade", "ALTER TABLE users ADD COLUMN cidade TEXT NOT NULL DEFAULT ''"),
        ]:
            if col not in cols:
                conn.execute(ddl)

    # ── Municipios (base geografica IBGE) ──────────────────────────────

    def _seed_municipios(self) -> None:
        """Preenche a tabela municipios a partir do JSON do IBGE (uma unica vez)."""
        if self.count_municipios() > 0:
            return
        dados = _carregar_municipios_json()
        if not dados:
            return
        with self._transaction() as conn:
            conn.executemany(
                "INSERT INTO municipios (codigo_ibge, uf, nome, capital) VALUES (?, ?, ?, ?)",
                [(d["id"], d["uf"], d["nome"], int(d.get("capital", 0))) for d in dados],
            )

    def count_municipios(self) -> int:
        """Total de municipios na tabela."""
        conn = self._get_conn()
        return conn.execute("SELECT COUNT(*) as c FROM municipios").fetchone()["c"]

    def municipios_da_uf(self, uf: str) -> list[dict]:
        """Municipios de uma UF (id, nome, capital), ordem alfabetica (capital 1a)."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT codigo_ibge, uf, nome, capital FROM municipios WHERE uf = ?",
            (uf.strip().upper(),),
        ).fetchall()
        m = [dict(r) for r in rows]
        m.sort(key=lambda r: (not r["capital"], r["nome"]))
        return m

    def lista_ufs(self) -> list[dict]:
        """Lista das UFs presentes na tabela (distinct)."""
        conn = self._get_conn()
        rows = conn.execute("SELECT DISTINCT uf FROM municipios ORDER BY uf").fetchall()
        return [dict(r) for r in rows]

    def validar_cidade(self, uf: str, cidade: str) -> bool:
        """Validacao estrita de cidade contra a tabela (case/accent-insensitive)."""
        from .geografia_br import validar_cidade as _val
        return _val(uf, cidade)

    # ── Chains (generico, por dominio) ────────────────────────────────

    # ── Chains (generico, por dominio) ────────────────────────────────

    def save_domain_chain(self, domain: str, cid: str, difficulty: int, chain_data: dict) -> None:
        """Salva ou atualiza uma cadeia de qualquer dominio."""
        now = time.time()
        data_json = json.dumps(chain_data, default=str)
        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO chains (domain, id, difficulty, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain, id) DO UPDATE SET
                    difficulty=excluded.difficulty,
                    data=excluded.data,
                    updated_at=excluded.updated_at
            """, (domain, cid, difficulty, data_json, now, now))

    def load_domain_chain(self, domain: str, cid: str) -> Optional[dict]:
        """Carrega uma cadeia de um dominio pela chave."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM chains WHERE domain = ? AND id = ?", (domain, cid)
        ).fetchone()
        if row:
            return json.loads(row["data"])
        return None

    def load_all_domain_chains(self, domain: str) -> dict[str, dict]:
        """Carrega todas as cadeias de um dominio. Retorna {id: data}."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, data FROM chains WHERE domain = ?", (domain,)
        ).fetchall()
        return {row["id"]: json.loads(row["data"]) for row in rows}

    def delete_domain_chain(self, domain: str, cid: str) -> bool:
        """Remove uma cadeia de um dominio."""
        with self._transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM chains WHERE domain = ? AND id = ?", (domain, cid)
            )
            return cursor.rowcount > 0

    def domain_chain_exists(self, domain: str, cid: str) -> bool:
        """Verifica se uma cadeia existe."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT 1 FROM chains WHERE domain = ? AND id = ?", (domain, cid)
        ).fetchone()
        return row is not None

    def list_domain_chains(self, domain: str) -> list[dict]:
        """Lista metadados de todas as cadeias de um dominio."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, domain, difficulty, created_at, updated_at FROM chains WHERE domain = ?",
            (domain,),
        ).fetchall()
        return [dict(row) for row in rows]

    # ── Chains PF (legado) ────────────────────────────────────────────

    def save_chain(self, cpf: str, difficulty: int, chain_data: dict) -> None:
        """Salva ou atualiza uma cadeia PF."""
        self.save_domain_chain("pf", cpf, difficulty, chain_data)

    def load_chain(self, cpf: str) -> Optional[dict]:
        """Carrega uma cadeia PF pelo CPF."""
        return self.load_domain_chain("pf", cpf)

    def load_all_chains(self) -> dict[str, dict]:
        """Carrega todas as cadeias PF."""
        return self.load_all_domain_chains("pf")

    def delete_chain(self, cpf: str) -> bool:
        """Remove uma cadeia PF."""
        return self.delete_domain_chain("pf", cpf)

    def chain_exists(self, cpf: str) -> bool:
        """Verifica se uma cadeia PF existe."""
        return self.domain_chain_exists("pf", cpf)

    def list_chains(self) -> list[dict]:
        """Lista metadados de todas as cadeias PF."""
        rows = self.list_domain_chains("pf")
        return [
            {
                "cpf": r["id"], "domain": r["domain"], "difficulty": r["difficulty"],
                "created_at": r["created_at"], "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    # ── Chains IM (legado) ────────────────────────────────────────────

    def save_imovel(self, matricula: str, difficulty: int, chain_data: dict) -> None:
        """Salva ou atualiza uma cadeia de imovel."""
        self.save_domain_chain("im", matricula, difficulty, chain_data)

    def load_imovel(self, matricula: str) -> Optional[dict]:
        """Carrega uma cadeia de imovel pela matricula."""
        return self.load_domain_chain("im", matricula)

    def load_all_imoveis(self) -> dict[str, dict]:
        """Carrega todas as cadeias de imoveis."""
        return self.load_all_domain_chains("im")

    def delete_imovel(self, matricula: str) -> bool:
        """Remove uma cadeia de imovel."""
        return self.delete_domain_chain("im", matricula)

    # ── Chains MO (legado) ────────────────────────────────────────────

    def save_veiculo(self, placa: str, difficulty: int, chain_data: dict) -> None:
        """Salva ou atualiza uma cadeia de veiculo."""
        self.save_domain_chain("mo", placa, difficulty, chain_data)

    def load_veiculo(self, placa: str) -> Optional[dict]:
        """Carrega uma cadeia de veiculo pela placa."""
        return self.load_domain_chain("mo", placa)

    def load_all_veiculos(self) -> dict[str, dict]:
        """Carrega todas as cadeias de veiculos."""
        return self.load_all_domain_chains("mo")

    def delete_veiculo(self, placa: str) -> bool:
        """Remove uma cadeia de veiculo."""
        return self.delete_domain_chain("mo", placa)

    # ── Referencias cruzadas ─────────────────────────────────────────

    def save_reference(self, domain: str, ref: dict) -> None:
        """
        Salva uma referencia cruzada.

        `ref` e o dict completo (dataclass.to_dict()) de um vinculo.
        As colunas genericas de busca sao derivadas dos campos:
          - estilo generico (entidade_origem_tipo / entidade_destino_tipo)
          - estilo IM legado (cpf / matricula)
        """
        data = dict(ref)
        if "entidade_origem_tipo" in data:
            origem_tipo = data.get("entidade_origem_tipo", "")
            origem_id = str(data.get("entidade_origem_id", ""))
            destino_tipo = data.get("entidade_destino_tipo", "")
            destino_id = str(data.get("entidade_destino_id", ""))
        else:
            origem_tipo = "PF"
            origem_id = str(data.get("cpf", ""))
            destino_tipo = "IM"
            destino_id = str(data.get("matricula", ""))
        tipo = data.get("tipo_vinculo", "")
        ts = data.get("timestamp", 0)
        ativo = int(bool(data.get("ativo", True)))
        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO cross_references
                (domain, origem_tipo, origem_id, destino_tipo, destino_id,
                 tipo_vinculo, timestamp, ativo, ref_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (domain, origem_tipo, origem_id, destino_tipo, destino_id,
                  tipo, ts, ativo, json.dumps(data, default=str)))

    def load_all_references(self, domain: Optional[str] = None) -> list[dict]:
        """Carrega referencias cruzadas (todas ou de um dominio)."""
        conn = self._get_conn()
        if domain:
            rows = conn.execute(
                "SELECT * FROM cross_references WHERE domain = ?", (domain,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM cross_references").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["ref_data"] = json.loads(d["ref_data"])
            d["ativo"] = bool(d["ativo"])
            result.append(d)
        return result

    def clear_references(self, domain: Optional[str] = None) -> int:
        """Remove referencias (todas ou de um dominio). Retorna qtd removida."""
        with self._transaction() as conn:
            if domain:
                cursor = conn.execute(
                    "DELETE FROM cross_references WHERE domain = ?", (domain,)
                )
            else:
                cursor = conn.execute("DELETE FROM cross_references")
            return cursor.rowcount

    # ── Users ──────────────────────────────────────────────────────────

    def save_user(
        self,
        username: str,
        password_hash: str,
        role: str,
        ativo: bool = True,
        nivel: int = 0,
        escopo: str = "",
        uf: str = "",
        cidade: str = "",
    ) -> None:
        """Salva ou atualiza um usuario."""
        now = time.time()
        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO users (username, password_hash, role, ativo, nivel, escopo, uf, cidade, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password_hash=excluded.password_hash,
                    role=excluded.role,
                    ativo=excluded.ativo,
                    nivel=excluded.nivel,
                    escopo=excluded.escopo,
                    uf=excluded.uf,
                    cidade=excluded.cidade
            """, (username, password_hash, role, int(ativo),
                  int(nivel), escopo, uf, cidade, now))

    def update_user(
        self,
        username: str,
        ativo: Optional[bool] = None,
        nivel: Optional[int] = None,
        escopo: Optional[str] = None,
        uf: Optional[str] = None,
        cidade: Optional[str] = None,
    ) -> bool:
        """Atualiza metadados de um usuario existente."""
        sets, args = [], []
        if ativo is not None:
            sets.append("ativo=?")
            args.append(int(ativo))
        if nivel is not None:
            sets.append("nivel=?")
            args.append(int(nivel))
        if escopo is not None:
            sets.append("escopo=?")
            args.append(escopo)
        if uf is not None:
            sets.append("uf=?")
            args.append(uf)
        if cidade is not None:
            sets.append("cidade=?")
            args.append(cidade)
        if not sets:
            return False
        args.append(username)
        with self._transaction() as conn:
            cursor = conn.execute(
                f"UPDATE users SET {', '.join(sets)} WHERE username = ?", args
            )
            return cursor.rowcount > 0

    def load_user(self, username: str) -> Optional[dict]:
        """Carrega um usuario."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row:
            d = dict(row)
            d["ativo"] = bool(d["ativo"])
            return d
        return None

    def load_all_users(self) -> list[dict]:
        """Carrega todos os usuarios."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM users").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["ativo"] = bool(d["ativo"])
            result.append(d)
        return result

    def delete_user(self, username: str) -> bool:
        """Remove um usuario."""
        with self._transaction() as conn:
            cursor = conn.execute("DELETE FROM users WHERE username = ?", (username,))
            return cursor.rowcount > 0

    # ── Graph Nodes ────────────────────────────────────────────────────

    def save_graph_node(self, cpf: str, nome: str, ativo: bool = True, chain_index: Optional[int] = None) -> None:
        """Salva ou atualiza um no do grafo."""
        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO graph_nodes (cpf, nome, ativo, chain_index)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cpf) DO UPDATE SET
                    nome=excluded.nome,
                    ativo=excluded.ativo,
                    chain_index=excluded.chain_index
            """, (cpf, nome, int(ativo), chain_index))

    def load_all_graph_nodes(self) -> list[dict]:
        """Carrega todos os nos do grafo."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM graph_nodes").fetchall()
        return [{**dict(row), "ativo": bool(row["ativo"])} for row in rows]

    def clear_graph(self) -> None:
        """Remove todos os nos e arestas do grafo."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM graph_nodes")
            conn.execute("DELETE FROM graph_edges")

    # ── Graph Edges ────────────────────────────────────────────────────

    def save_graph_edge(self, from_cpf: str, to_cpf: str, tipo: str,
                        ativo: bool = True, block_index: Optional[int] = None,
                        timestamp: float = 0, dados: Optional[dict] = None) -> int:
        """Salva uma aresta do grafo. Retorna o ID."""
        dados_json = json.dumps(dados or {}, default=str)
        with self._transaction() as conn:
            cursor = conn.execute("""
                INSERT INTO graph_edges (from_cpf, to_cpf, tipo, ativo, block_index, timestamp, dados)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (from_cpf, to_cpf, tipo, int(ativo), block_index, timestamp, dados_json))
            return cursor.lastrowid

    def deactivate_graph_edges(self, cpf_a: str, cpf_b: str, tipo: str) -> int:
        """Desativa arestas entre duas PFs de um tipo."""
        with self._transaction() as conn:
            cursor = conn.execute("""
                UPDATE graph_edges SET ativo = 0
                WHERE ((from_cpf = ? AND to_cpf = ?) OR (from_cpf = ? AND to_cpf = ?))
                AND tipo = ? AND ativo = 1
            """, (cpf_a, cpf_b, cpf_b, cpf_a, tipo))
            return cursor.rowcount

    def deactivate_graph_edge_by_id(self, edge_id: int) -> None:
        """Desativa uma aresta pelo ID."""
        with self._transaction() as conn:
            conn.execute("UPDATE graph_edges SET ativo = 0 WHERE id = ?", (edge_id,))

    def load_all_graph_edges(self) -> list[dict]:
        """Carrega todas as arestas do grafo."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM graph_edges").fetchall()
        return [{**dict(row), "ativo": bool(row["ativo"]),
                 "dados": json.loads(row["dados"])} for row in rows]

    def delete_all_graph_edges(self, cpf: str) -> int:
        """Remove todas as arestas de uma PF."""
        with self._transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM graph_edges WHERE from_cpf = ? OR to_cpf = ?",
                (cpf, cpf),
            )
            return cursor.rowcount

    # ── Settings ───────────────────────────────────────────────────────

    def set_setting(self, key: str, value: str) -> None:
        """Salva uma configuracao."""
        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, value))

    def get_setting(self, key: str, default: str = "") -> str:
        """Retorna uma configuracao."""
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    # ── Utilidades ─────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Retorna estatisticas do banco."""
        conn = self._get_conn()
        pf = conn.execute("SELECT COUNT(*) as c FROM chains WHERE domain = 'pf'").fetchone()["c"]
        im = conn.execute("SELECT COUNT(*) as c FROM chains WHERE domain = 'im'").fetchone()["c"]
        mo = conn.execute("SELECT COUNT(*) as c FROM chains WHERE domain = 'mo'").fetchone()["c"]
        co = conn.execute("SELECT COUNT(*) as c FROM chains WHERE domain = 'co'").fetchone()["c"]
        em = conn.execute("SELECT COUNT(*) as c FROM chains WHERE domain = 'em'").fetchone()["c"]
        ac = conn.execute("SELECT COUNT(*) as c FROM chains WHERE domain = 'ac'").fetchone()["c"]
        an = conn.execute("SELECT COUNT(*) as c FROM chains WHERE domain = 'an'").fetchone()["c"]
        users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        nodes = conn.execute("SELECT COUNT(*) as c FROM graph_nodes").fetchone()["c"]
        edges = conn.execute("SELECT COUNT(*) as c FROM graph_edges").fetchone()["c"]
        xrefs = conn.execute("SELECT COUNT(*) as c FROM cross_references").fetchone()["c"]
        xrefs_ativos = conn.execute(
            "SELECT COUNT(*) as c FROM cross_references WHERE ativo = 1"
        ).fetchone()["c"]
        return {
            "chains": pf,
            "chains_por_dominio": {"pf": pf, "im": im, "mo": mo,
                                   "co": co, "em": em, "ac": ac, "an": an},
            "users": users,
            "graph_nodes": nodes,
            "graph_edges": edges,
            "cross_references": xrefs,
            "cross_references_ativos": xrefs_ativos,
            "db_path": self.db_path,
            "db_size_kb": os.path.getsize(self.db_path) // 1024 if os.path.exists(self.db_path) else 0,
        }

    def close(self) -> None:
        """Fecha todas as conexoes abertas (todas as threads)."""
        for conn in self._all_conns:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
        self._all_conns.clear()
        self._local.conn = None

    def __repr__(self) -> str:
        return f"Database(path={self.db_path})"