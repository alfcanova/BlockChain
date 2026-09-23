"""
blockchain_pf/chain.py
Cadeia de blocos para eventos vitais de PF.
Validação integral (hash + PoW + assinaturas ECDSA),
persistência em JSON e operações de busca.
"""

import json
import os
import time
from typing import Any, Optional, Iterator

from .block import Block
from .signatures import (
    KeyPair,
    Signer,
    BlockSignature,
    SignatureVerifier,
    generate_authority_keypair,
)
from .graph import RelationshipGraph, RelationType


class Blockchain:
    """
    Cadeia de blocos para uma pessoa física.

    A cadeia começa com um bloco gênesis que representa o nascimento.
    Cada bloco pode ser assinado digitalmente com ECDSA.
    Opcionalmente, mantém um grafo de relacionamentos cross-chain.
    """

    def __init__(self, difficulty: int = 2, graph: Optional[RelationshipGraph] = None) -> None:
        self.difficulty = difficulty
        self.chain: list[Block] = []
        self._event_index: dict[str, list[int]] = {}  # tipo_evento → [indices]
        self._signer: Optional[Signer] = None
        self._graph = graph  # Grafo de relacionamentos (opcional)
        # Gerador de assinador padrao para garantir que toda operacao seja assinada
        self._default_keypair = generate_authority_keypair("autoridade")
        self._signer = Signer(self._default_keypair)

    # ── Configuração de assinatura ─────────────────────────────────────

    def set_signer(self, keypair: KeyPair) -> None:
        """
        Configura o assinador da cadeia.
        
        Uma vez configurado, todos os novos blocos serão assinados.
        
        Args:
            keypair: Par de chaves ECDSA do emissor.
        """
        self._signer = Signer(keypair)

    @property
    def signer(self) -> Optional[Signer]:
        """Retorna o assinador atual (se configurado)."""
        return self._signer

    # ── Inicialização ─────────────────────────────────────────────────

    def create_genesis(self, birth_data: dict[str, Any]) -> Block:
        """
        Cria o bloco gênesis com dados de nascimento.
        O bloco é obrigatoriamente assinado com ECDSA.
        
        Args:
            birth_data: Dicionário com dados do nascimento.
        
        Raises:
            ValueError: Se nenhum signer estiver configurado.
        
        Returns:
            O bloco gênesis criado e assinado.
        """
        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")
        genesis = Block(
            index=0,
            timestamp=time.time(),
            data={
                "evento_tipo": "NASCIMENTO",
                "payload": birth_data,
                "hash_cadeia": "GENESIS",
            },
            previous_hash="0" * 64,
            difficulty=self.difficulty,
        )
        genesis.mine_block()

        # Assina obrigatoriamente
        sig = self._signer.sign_block(genesis)
        genesis.set_signature(
            signer_label=sig.signer_label,
            signer_pubkey=sig.signer_pubkey,
            signature_b64=sig.signature_b64,
            signed_at=sig.signed_at,
        )

        self.chain.append(genesis)
        self._index_event("NASCIMENTO", 0)

        # Atualiza grafo de relacionamentos
        if self._graph:
            cpf = birth_data.get("cpf", "")
            nome = birth_data.get("nome_completo", "")
            self._graph.add_node(cpf, nome, chain_index=0)
            # Adiciona arestas de parentela
            mae = birth_data.get("nome_mae", "")
            pai = birth_data.get("nome_pai", "")
            if mae:
                mae_cpf = birth_data.get("cpf_mae", "")
                if mae_cpf:
                    self._graph.add_node(mae_cpf, mae)
                    self._graph.add_edge(mae_cpf, cpf, RelationType.MAE, 0)
            if pai:
                pai_cpf = birth_data.get("cpf_pai", "")
                if pai_cpf:
                    self._graph.add_node(pai_cpf, pai)
                    self._graph.add_edge(pai_cpf, cpf, RelationType.PAI, 0)

        return genesis

    # ── Adição de blocos ──────────────────────────────────────────────

    def add_event(self, event_type: str, payload: dict[str, Any]) -> Block:
        """
        Adiciona um novo evento à cadeia.

        Se um signer estiver configurado, o bloco será assinado.

        Args:
            event_type: Tipo do evento (ex: "CASAMENTO", "DIVÓRCIO").
            payload:    Dados do evento.

        Returns:
            O bloco adicionado.

        Raises:
            ValueError: Se a cadeia estiver vazia ou inválida.
        """
        if not self.chain:
            raise ValueError("Cadeia vazia — crie o bloco gênesis primeiro.")

        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")

        last_block = self.chain[-1]
        new_block = Block(
            index=last_block.index + 1,
            timestamp=time.time(),
            data={
                "evento_tipo": event_type,
                "payload": payload,
                "hash_cadeia": last_block.hash,
            },
            previous_hash=last_block.hash,
            difficulty=self.difficulty,
        )
        new_block.mine_block()

        # Assina obrigatoriamente
        sig = self._signer.sign_block(new_block)
        new_block.set_signature(
            signer_label=sig.signer_label,
            signer_pubkey=sig.signer_pubkey,
            signature_b64=sig.signature_b64,
            signed_at=sig.signed_at,
        )

        self.chain.append(new_block)
        self._index_event(event_type, new_block.index)

        # Atualiza grafo de relacionamentos
        if self._graph:
            self._update_graph_on_event(event_type, payload, new_block.index)

        return new_block

    # ── Atualização do Grafo ─────────────────────────────────────────

    def _update_graph_on_event(self, event_type: str, payload: dict, block_index: int) -> None:
        """Atualiza o grafo de relacionamentos baseado no evento."""
        cpf = payload.get("cpf", "")
        if not cpf:
            return

        # Busca CPF da PF atual (do genesis)
        birth = self.get_birth_block()
        if not birth:
            return
        meu_cpf = birth.data.get("payload", {}).get("cpf", "")

        if event_type == "CASAMENTO":
            cpf_conjuge = payload.get("cpf_conjuge", "")
            nome_conjuge = payload.get("nome_conjuge", "")
            if cpf_conjuge:
                self._graph.add_node(cpf_conjuge, nome_conjuge)
                self._graph.add_edge(
                    meu_cpf, cpf_conjuge,
                    RelationType.CONJUGE, block_index,
                    dados={"regime_bens": payload.get("regime_bens", "")},
                )

        elif event_type == "DIVORCIO":
            # Desativa arestas de casamento ativas
            conjuges = self._graph.get_conjuges(meu_cpf)
            for c in conjuges:
                self._graph.deactivate_edges(meu_cpf, c.cpf, RelationType.CONJUGE)
                self._graph.add_edge(
                    meu_cpf, c.cpf,
                    RelationType.EX_CONJUGE, block_index,
                    dados={"tipo": payload.get("tipo", "")},
                )

        elif event_type == "ADOCAO":
            # ADOCAO: a PF (mae/pai adotivo) adota uma crianca
            # O payload contem o CPF da PF atual como adotante
            # A crianca ja deve existir no grafo ou ser criada
            mae_adotiva = payload.get("nome_mae_adotiva", "")
            pai_adotivo = payload.get("nome_pai_adotivo", "")
            # Nota: para adocao completa, precisaríamos do CPF da crianca
            # Por agora, registra a intenção

        elif event_type == "OBITO":
            self._graph.mark_deceased(meu_cpf)

        elif event_type == "DISVINC_MATERNA":
            # Remove aresta de mae
            pais = self._graph.get_pais(meu_cpf)
            for p in pais:
                edges = self._graph._get_active_edges(meu_cpf)
                for e in edges:
                    if e.tipo == RelationType.MAE and (
                        e.from_cpf == p.cpf or e.to_cpf == p.cpf
                    ):
                        e.ativo = False
                        break

        elif event_type == "DISVINC_PATerna":
            # Remove aresta de pai
            pais = self._graph.get_pais(meu_cpf)
            for p in pais:
                edges = self._graph._get_active_edges(meu_cpf)
                for e in edges:
                    if e.tipo == RelationType.PAI and (
                        e.from_cpf == p.cpf or e.to_cpf == p.cpf
                    ):
                        e.ativo = False
                        break

    # ── Propriedades ──────────────────────────────────────────────────

    @property
    def graph(self) -> Optional[RelationshipGraph]:
        """Retorna o grafo de relacionamentos (se configurado)."""
        return self._graph

    # ── Validação ─────────────────────────────────────────────────────

    def validate(self, require_signatures: bool = True) -> tuple[bool, str]:
        """
        Valida toda a cadeia.
        
        Args:
            require_signatures: Se True (padrão), exige que todos os blocos
                               tenham assinatura ECDSA válida.
        
        Returns:
            Tuple (é_válida, mensagem).
        """
        if not self.chain:
            return False, "Cadeia vazia."

        genesis = self.chain[0]
        if genesis.previous_hash != "0" * 64:
            return False, "Hash do gênesis inválido."

        if not genesis.is_valid():
            return False, f"Bloco gênesis (#{genesis.index}) corrompido."

        # Valida assinatura do gênesis se exigido
        if require_signatures and not genesis.has_signature():
            return False, f"Bloco gênesis (#{genesis.index}) sem assinatura."

        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # 1) Link hash anterior
            if current.previous_hash != previous.hash:
                return (
                    False,
                    f"Bloco #{current.index}: previous_hash não confere "
                    f"(esperado {previous.hash[:16]}..., "
                    f"obtido {current.previous_hash[:16]}...).",
                )

            # 2) Hash próprio
            if current.hash != current.compute_hash():
                return (
                    False,
                    f"Bloco #{current.index}: hash próprio não confere.",
                )

            # 3) Proof-of-Work
            if not current.is_valid():
                return (
                    False,
                    f"Bloco #{current.index}: proof-of-work inválido.",
                )

            # 4) Índice sequencial
            if current.index != i:
                return (
                    False,
                    f"Bloco #{current.index}: índice fora de sequência (esperado {i}).",
                )

            # 5) Assinatura ECDSA (se exigida)
            if require_signatures:
                if not current.has_signature():
                    return (
                        False,
                        f"Bloco #{current.index}: sem assinatura ECDSA.",
                    )
                sig = BlockSignature.from_dict(current.signature)
                ok, msg = self._verify_signature(current, sig)
                if not ok:
                    return (
                        False,
                        f"Bloco #{current.index}: assinatura inválida — {msg}",
                    )

        sig_count = sum(1 for b in self.chain if b.has_signature())
        suffix = f" | {sig_count}/{len(self.chain)} assinado(s)" if sig_count else ""
        return True, f"Cadeia válida — {len(self.chain)} bloco(s).{suffix}"

    def verify_all_signatures(self) -> tuple[bool, str]:
        """
        Verifica todas as assinaturas da cadeia.
        
        Returns:
            Tuple (todas_válidas, mensagem_detalhada).
        """
        unsigned = []
        invalid = []

        for block in self.chain:
            if not block.has_signature():
                unsigned.append(block.index)
                continue

            sig = BlockSignature.from_dict(block.signature)
            ok, msg = self._verify_signature(block, sig)
            if not ok:
                invalid.append((block.index, msg))

        lines = []
        if unsigned:
            lines.append(f"Sem assinatura: blocos {unsigned}")
        if invalid:
            for idx, msg in invalid:
                lines.append(f"Bloco #{idx}: {msg}")
        if not unsigned and not invalid:
            lines.append(f"Todas as {len(self.chain)} assinaturas ECDSA são válidas.")

        all_valid = not unsigned and not invalid
        return all_valid, " | ".join(lines)

    def _verify_signature(self, block: Block, sig: BlockSignature) -> tuple[bool, str]:
        """Verifica a assinatura de um bloco individual."""
        try:
            pubkey = SignatureVerifier._reconstruct_pubkey(sig.signer_pubkey)
            return SignatureVerifier.verify_block_signature(block, sig, pubkey)
        except Exception as e:
            return False, f"Erro na verificação: {e}"

    # ── Busca ─────────────────────────────────────────────────────────

    def get_event(self, index: int) -> Optional[Block]:
        """Retorna o bloco pelo índice."""
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None

    def get_events_by_type(self, event_type: str) -> list[Block]:
        """Retorna todos os blocos de um tipo de evento."""
        indices = self._event_index.get(event_type, [])
        return [self.chain[i] for i in indices if i < len(self.chain)]

    def get_last_event(self) -> Optional[Block]:
        """Retorna o último bloco da cadeia."""
        return self.chain[-1] if self.chain else None

    def get_birth_block(self) -> Optional[Block]:
        """Retorna o bloco de nascimento (gênesis)."""
        return self.chain[0] if self.chain else None

    def get_timeline(self) -> list[dict[str, Any]]:
        """
        Retorna uma timeline ordenada de todos os eventos.
        Útil para exibição e análise.
        """
        import time as _time
        timeline = []
        for block in self.chain:
            evento = block.data.get("evento_tipo", "DESCONHECIDO")
            payload = block.data.get("payload", {})
            ts = _time.strftime(
                "%Y-%m-%d %H:%M:%S", _time.localtime(block.timestamp)
            )
            signed = block.has_signature()
            signer = block.signature.get("signer_label", "") if signed else ""
            timeline.append({
                "indice": block.index,
                "tipo": evento,
                "data_registro": ts,
                "hash": block.hash[:16],
                "assinado": signed,
                "emissor": signer,
                "dados": payload,
            })
        return timeline

    # ── Persistência ──────────────────────────────────────────────────

    def save_to_file(self, filepath: str) -> None:
        """Serializa a cadeia para JSON e salva em disco."""
        data = {
            "difficulty": self.difficulty,
            "chain": [b.to_dict() for b in self.chain],
        }
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    @classmethod
    def load_from_file(cls, filepath: str) -> "Blockchain":
        """Carrega uma cadeia de um arquivo JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        chain = cls(difficulty=data["difficulty"])
        chain.chain = [Block.from_dict(b) for b in data["chain"]]
        # Reconstrói o índice
        for i, block in enumerate(chain.chain):
            evento = block.data.get("evento_tipo", "DESCONHECIDO")
            chain._index_event(evento, i)
        return chain

    # ── Privados ──────────────────────────────────────────────────────

    def _index_event(self, event_type: str, index: int) -> None:
        """Indexa um evento para busca rápida."""
        if event_type not in self._event_index:
            self._event_index[event_type] = []
        self._event_index[event_type].append(index)

    # ── Representação ─────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.chain)

    def __repr__(self) -> str:
        signer_info = f", signer={self._signer.keypair.label}" if self._signer else ""
        return f"Blockchain(blocks={len(self.chain)}, difficulty={self.difficulty}{signer_info})"
