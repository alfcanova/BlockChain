"""
blockchain_pf/graph.py
Grafo de relacionamentos entre Pessoas Fisicas.

Conecta multiplas cadeias de blockchain via CPF, criando um grafo
onde nos sao PFs e arestas sao relacionamentos (casamento, parentela, adocao).

Estrutura:
  No:      CPF → {nome, chain_ref, blocos}
  Aresta:  (cpf_a, cpf_b) → {tipo, evento_block_index, dados}

Suporta:
  - CASAMENTO:       aresta bidirecional entre conjuges
  - DIVORCIO:        remove aresta de casamento
  - ADOCAO:          aresta de parentela (mae_adotiva/pai_adotivo → crianca)
  - NASCIMENTO:      aresta de parentela (mae/pai → crianca)
  - DISVINCULACAO:   remove aresta de parentela
  - OBITO:           marca no como inativo
"""

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class RelationType(str, Enum):
    """Tipos de aresta no grafo."""
    CONJUGE      = "CONJUGE"        # Casamento
    MAE          = "MAE"            # Mae biologica/adotiva
    PAI          = "PAI"            # Pai biologico/adotivo
    FILHO        = "FILHO"          # Filho(a)
    EX_CONJUGE   = "EX_CONJUGE"     # Divorcio
    DISVINC_MAE  = "DISVINC_MAE"    # Disvinculacao materna
    DISVINC_PAI  = "DISVINC_PAI"    # Disvinculacao paterna


@dataclass
class Node:
    """
    No do grafo — representa uma PF.
    
    Attributes:
        cpf:          CPF da PF (chave unica).
        nome:         Nome atual da PF.
        ativo:        Se a PF esta viva.
        chain_index:  Indice da cadeia no repositorio.
    """
    cpf: str
    nome: str
    ativo: bool = True
    chain_index: Optional[int] = None  # Index no dict de chains

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Edge:
    """
    Aresta do grafo — representa um relacionamento.
    
    Attributes:
        from_cpf:    CPF de origem.
        to_cpf:      CPF de destino.
        tipo:        Tipo do relacionamento.
        ativo:       Se o relacionamento esta vigente.
        block_index:  Indice do bloco que registrou o evento.
        timestamp:   Quando o relacionamento foi registrado.
        dados:       Dados extras (ex: regime de bens, motivo).
    """
    from_cpf: str
    to_cpf: str
    tipo: str
    ativo: bool = True
    block_index: Optional[int] = None
    timestamp: float = 0.0
    dados: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RelationshipGraph:
    """
    Grafo de relacionamentos entre PFs.
    
    Mantem um mapa de nos (PFs) e arestas (relacionamentos),
    permitindo consultas como:
      - Quem e o conjuge de X?
      - Quais filhos X tem?
      - Qual e a rede familiar completa de X?
      - Quem esta conectado a quem?
    """

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}   # cpf → Node
        self.edges: list[Edge] = []        # todas as arestas
        self._edge_index: dict[str, list[int]] = {}  # cpf → [indices das arestas]

    # ── Gerenciamento de Nos ──────────────────────────────────────────

    def add_node(self, cpf: str, nome: str, chain_index: Optional[int] = None) -> Node:
        """
        Adiciona uma PF ao grafo.
        
        Args:
            cpf:          CPF (11 digitos).
            nome:         Nome completo.
            chain_index:  Indice da cadeia no repositorio.
        
        Returns:
            O no criado.
        """
        cpf = cpf.replace(".", "").replace("-", "")
        if cpf in self.nodes:
            # Atualiza nome se mudou
            self.nodes[cpf].nome = nome
            if chain_index is not None:
                self.nodes[cpf].chain_index = chain_index
            return self.nodes[cpf]

        node = Node(cpf=cpf, nome=nome, chain_index=chain_index)
        self.nodes[cpf] = node
        return node

    def get_node(self, cpf: str) -> Optional[Node]:
        """Retorna o no pelo CPF."""
        cpf = cpf.replace(".", "").replace("-", "")
        return self.nodes.get(cpf)

    def mark_deceased(self, cpf: str) -> None:
        """Marca uma PF como falecida."""
        cpf = cpf.replace(".", "").replace("-", "")
        if cpf in self.nodes:
            self.nodes[cpf].ativo = False

    # ── Gerenciamento de Arestas ──────────────────────────────────────

    def add_edge(
        self,
        from_cpf: str,
        to_cpf: str,
        tipo: str,
        block_index: Optional[int] = None,
        dados: Optional[dict] = None,
    ) -> Edge:
        """
        Adiciona uma aresta (relacionamento) entre duas PFs.
        
        Args:
            from_cpf:    CPF de origem.
            to_cpf:      CPF de destino.
            tipo:        Tipo do relacionamento (RelationType).
            block_index:  Indice do bloco na cadeia.
            dados:       Dados extras.
        
        Returns:
            A aresta criada.
        """
        from_cpf = from_cpf.replace(".", "").replace("-", "")
        to_cpf = to_cpf.replace(".", "").replace("-", "")

        edge = Edge(
            from_cpf=from_cpf,
            to_cpf=to_cpf,
            tipo=tipo,
            block_index=block_index,
            timestamp=time.time(),
            dados=dados or {},
        )
        self.edges.append(edge)
        idx = len(self.edges) - 1

        # Indexa
        if from_cpf not in self._edge_index:
            self._edge_index[from_cpf] = []
        if to_cpf not in self._edge_index:
            self._edge_index[to_cpf] = []
        self._edge_index[from_cpf].append(idx)
        self._edge_index[to_cpf].append(idx)

        return edge

    def deactivate_edges(self, cpf_a: str, cpf_b: str, tipo: str) -> int:
        """
        Desativa arestas entre duas PFs de um tipo especifico.
        
        Returns:
            Numero de arestas desativadas.
        """
        cpf_a = cpf_a.replace(".", "").replace("-", "")
        cpf_b = cpf_b.replace(".", "").replace("-", "")
        count = 0
        for edge in self.edges:
            if (edge.from_cpf == cpf_a and edge.to_cpf == cpf_b or
                edge.from_cpf == cpf_b and edge.to_cpf == cpf_a):
                if edge.tipo == tipo and edge.ativo:
                    edge.ativo = False
                    count += 1
        return count

    # ── Consultas ─────────────────────────────────────────────────────

    def get_conjuges(self, cpf: str) -> list[Node]:
        """Retorna todos os conjuges atuais de uma PF."""
        cpf = cpf.replace(".", "").replace("-", "")
        result = []
        for edge in self._get_active_edges(cpf):
            if edge.tipo == RelationType.CONJUGE:
                other = edge.to_cpf if edge.from_cpf == cpf else edge.from_cpf
                node = self.nodes.get(other)
                if node:
                    result.append(node)
        return result

    def get_ex_conjuges(self, cpf: str) -> list[Node]:
        """Retorna todos os ex-conjuges de uma PF."""
        cpf = cpf.replace(".", "").replace("-", "")
        result = []
        for edge in self._get_all_edges(cpf):
            if edge.tipo == RelationType.EX_CONJUGE:
                other = edge.to_cpf if edge.from_cpf == cpf else edge.from_cpf
                node = self.nodes.get(other)
                if node and node not in result:
                    result.append(node)
        return result

    def get_filhos(self, cpf: str) -> list[Node]:
        """Retorna todos os filhos de uma PF."""
        cpf = cpf.replace(".", "").replace("-", "")
        result = []
        for edge in self._get_active_edges(cpf):
            if edge.tipo in (RelationType.MAE, RelationType.PAI):
                # A aresta vai de MAE/PAI → FILHO
                filho_cpf = edge.to_cpf if edge.from_cpf == cpf else edge.from_cpf
                node = self.nodes.get(filho_cpf)
                if node and node not in result:
                    result.append(node)
        return result

    def get_pais(self, cpf: str) -> list[Node]:
        """Retorna os pais (biologicos ou adotivos) de uma PF."""
        cpf = cpf.replace(".", "").replace("-", "")
        result = []
        for edge in self._get_active_edges(cpf):
            if edge.tipo in (RelationType.MAE, RelationType.PAI):
                # A aresta vai de MAE/PAI → FILHO, entao o outro lado e o pai/mae
                other = edge.from_cpf if edge.to_cpf == cpf else edge.to_cpf
                node = self.nodes.get(other)
                if node and node not in result:
                    result.append(node)
        return result

    def getirmaos(self, cpf: str) -> list[Node]:
        """Retorna os irmaos de uma PF (mesmos pais)."""
        cpf = cpf.replace(".", "").replace("-", "")
        pais = self.get_pais(cpf)
        irmaos = []
        for pai in pais:
            filhos = self.get_filhos(pai.cpf)
            for filho in filhos:
                if filho.cpf != cpf and filho not in irmaos:
                    irmaos.append(filho)
        return irmaos

    def get_family_network(self, cpf: str, depth: int = 2) -> dict[str, Any]:
        """
        Retorna a rede familiar completa de uma PF.
        
        Args:
            cpf:    CPF da PF.
            depth:  Profundidade de busca (1=pais, 2=avós, etc.).
        
        Returns:
            Dict com nos, arestas e estatisticas.
        """
        cpf = cpf.replace(".", "").replace("-", "")
        visited = set()
        nodes_found = []
        edges_found = []

        def _traverse(c: str, d: int):
            if d <= 0 or c in visited:
                return
            visited.add(c)
            node = self.nodes.get(c)
            if node:
                nodes_found.append(node.to_dict())
            for edge in self._get_active_edges(c):
                other = edge.to_cpf if edge.from_cpf == c else edge.from_cpf
                if other not in visited:
                    edges_found.append(edge.to_dict())
                    _traverse(other, d - 1)

        _traverse(cpf, depth)

        return {
            "origem": cpf,
            "nos": nodes_found,
            "arestas": edges_found,
            "estatisticas": {
                "total_pessoas": len(nodes_found),
                "total_relacionamentos": len(edges_found),
            },
        }

    def find_path(self, cpf_a: str, cpf_b: str) -> Optional[list[dict]]:
        """
        Encontra o caminho mais curto entre duas PFs.
        
        Returns:
            Lista de nos no caminho, ou None se nao encontrado.
        """
        cpf_a = cpf_a.replace(".", "").replace("-", "")
        cpf_b = cpf_b.replace(".", "").replace("-", "")

        if cpf_a == cpf_b:
            return [self.nodes[cpf_a].to_dict()] if cpf_a in self.nodes else None

        # BFS
        from collections import deque
        queue = deque([(cpf_a, [cpf_a])])
        visited = {cpf_a}

        while queue:
            current, path = queue.popleft()
            for edge in self._get_active_edges(current):
                other = edge.to_cpf if edge.from_cpf == current else edge.from_cpf
                if other == cpf_b:
                    full_path = path + [other]
                    return [self.nodes[c].to_dict() for c in full_path if c in self.nodes]
                if other not in visited:
                    visited.add(other)
                    queue.append((other, path + [other]))

        return None

    # ── Estatisticas ─────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Retorna estatisticas do grafo."""
        ativos = sum(1 for n in self.nodes.values() if n.ativo)
        inativos = len(self.nodes) - ativos
        ativos_edges = sum(1 for e in self.edges if e.ativo)

        return {
            "total_pessoas": len(self.nodes),
            "ativos": ativos,
            "falecidos": inativos,
            "total_relacionamentos": len(self.edges),
            "ativos_relacionamentos": ativos_edges,
            "ex_relacionamentos": len(self.edges) - ativos_edges,
        }

    # ── Serializacao ─────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {cpf: n.to_dict() for cpf, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
        }

    def save_to_file(self, filepath: str) -> None:
        """Salva o grafo em JSON."""
        import os
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load_from_file(cls, filepath: str) -> "RelationshipGraph":
        """Carrega o grafo de JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        graph = cls()
        for cpf, n in data.get("nodes", {}).items():
            graph.nodes[cpf] = Node(**n)
        for e in data.get("edges", []):
            edge = Edge(**e)
            graph.edges.append(edge)
            idx = len(graph.edges) - 1
            if edge.from_cpf not in graph._edge_index:
                graph._edge_index[edge.from_cpf] = []
            if edge.to_cpf not in graph._edge_index:
                graph._edge_index[edge.to_cpf] = []
            graph._edge_index[edge.from_cpf].append(idx)
            graph._edge_index[edge.to_cpf].append(idx)
        return graph

    # ── Privados ──────────────────────────────────────────────────────

    def _get_active_edges(self, cpf: str) -> list[Edge]:
        """Retorna arestas ativas de uma PF."""
        cpf = cpf.replace(".", "").replace("-", "")
        indices = self._edge_index.get(cpf, [])
        return [self.edges[i] for i in indices if self.edges[i].ativo]

    def _get_all_edges(self, cpf: str) -> list[Edge]:
        """Retorna todas as arestas (ativas e inativas) de uma PF."""
        cpf = cpf.replace(".", "").replace("-", "")
        indices = self._edge_index.get(cpf, [])
        return [self.edges[i] for i in indices]

    # ── Representacao ─────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"RelationshipGraph("
            f"nodes={len(self.nodes)}, "
            f"edges={len(self.edges)})"
        )
