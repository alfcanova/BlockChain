"""
blockchain_co/chain.py
Cadeia de blocos para eventos de empresas (CNPJ).
Gênesis = constituição da empresa.
Validação integral (hash + PoW + assinaturas ECDSA),
persistência em JSON e operações de busca.
"""

import json
import os
import time
from typing import Any, Optional

from blockchain_pf.block import Block
from blockchain_pf.signatures import (
    KeyPair,
    Signer,
    BlockSignature,
    SignatureVerifier,
    generate_authority_keypair,
)

from .events import CompanyEventType, CompanyChainProtector


class CompanyChain:
    """
    Cadeia de blocos para uma empresa.

    A cadeia começa com um bloco gênesis que representa a constituição
    da empresa (CNPJ, razão social, capital social, sócios).
    Cada bloco pode ser assinado digitalmente com ECDSA.
    """

    def __init__(self, difficulty: int = 2) -> None:
        self.difficulty = difficulty
        self.chain: list[Block] = []
        self._event_index: dict[str, list[int]] = {}
        self._default_keypair = generate_authority_keypair("junta_comercial")
        self._signer = Signer(self._default_keypair)

    # ── Configuração de assinatura ─────────────────────────────────────

    def set_signer(self, keypair: KeyPair) -> None:
        """Configura o assinador da cadeia."""
        self._signer = Signer(keypair)

    @property
    def signer(self) -> Optional[Signer]:
        """Retorna o assinador atual."""
        return self._signer

    # ── Inicialização ─────────────────────────────────────────────────

    def create_genesis(self, empresa_data: dict[str, Any]) -> Block:
        """
        Cria o bloco gênesis com dados de constituição da empresa.
        O bloco é obrigatoriamente assinado com ECDSA.

        Raises:
            ValueError: Se nenhum signer estiver configurado.

        Args:
            empresa_data: Dicionário com dados da empresa (CNPJ, razão social, etc).

        Returns:
            O bloco gênesis criado.
        """
        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")

        genesis = Block(
            index=0,
            timestamp=time.time(),
            data={
                "evento_tipo": CompanyEventType.CONSTITUICAO.value,
                "payload": empresa_data,
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
        self._index_event(CompanyEventType.CONSTITUICAO.value, 0)
        return genesis

    # ── Adição de blocos ──────────────────────────────────────────────

    def add_event(self, event_type: str, payload: dict[str, Any]) -> Block:
        """
        Adiciona um novo evento à cadeia.

        Args:
            event_type: Tipo do evento (ex: "ADICAO_SOCIO", "FUSAO").
            payload:    Dados do evento.

        Returns:
            O bloco adicionado.

        Raises:
            ValueError: Se a cadeia estiver vazia ou o evento for bloqueado.
        """
        if not self.chain:
            raise ValueError("Cadeia vazia — crie o bloco gênesis primeiro.")

        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")

        # Verifica se o evento pode ser adicionado
        estado = self.get_estado_atual()
        if not CompanyChainProtector.pode_adicionar(
            event_type, estado.get("situacao_cadastral", "ATIVA")
        ):
            raise ValueError(
                f"Evento '{event_type}' bloqueado para empresa com estado "
                f"'{estado.get('situacao_cadastral')}'."
            )

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
        return new_block

    # ── Estado acumulado ──────────────────────────────────────────────

    def get_estado_atual(self) -> dict[str, Any]:
        """
        Retorna o estado consolidado da empresa.
        Calcula a partir de todos os blocos da cadeia.
        """
        if not self.chain:
            return {}

        genesis = self.chain[0]
        payload_genesis = genesis.data.get("payload", {})

        estado = {
            "cnpj": payload_genesis.get("cnpj", ""),
            "razao_social": payload_genesis.get("razao_social", ""),
            "nome_fantasia": payload_genesis.get("nome_fantasia", ""),
            "data_constituicao": payload_genesis.get("data_constituicao", ""),
            "tipo_empresa": payload_genesis.get("tipo_empresa", ""),
            "porte": payload_genesis.get("porte", ""),
            "capital_social": payload_genesis.get("capital_social", 0.0),
            "natureza_juridica": payload_genesis.get("natureza_juridica", ""),
            "atividade_principal": payload_genesis.get("atividade_principal", ""),
            "atividades_secundarias": list(
                payload_genesis.get("atividades_secundarias", [])
            ),
            "endereco_sede": payload_genesis.get("endereco_sede", {}),
            "responsavel": payload_genesis.get("responsavel", {}),
            "contabilista": payload_genesis.get("contabilista", {}),
            "registro": payload_genesis.get("registro", {}),
            "situacao_cadastral": payload_genesis.get(
                "situacao_cadastral", "ATIVA"
            ),
            "socios": list(payload_genesis.get("socios", [])),
            "certidoes": list(payload_genesis.get("certidoes", [])),
            "garantias": list(payload_genesis.get("garantias", [])),
            "enderecos_historico": list(
                payload_genesis.get("enderecos_historico", [])
            ),
        }

        # Processa cada evento subsequente
        for block in self.chain[1:]:
            evento = block.data.get("evento_tipo", "")
            payload = block.data.get("payload", {})

            if evento == CompanyEventType.ADICAO_SOCIO.value:
                socio = payload.get("socio", {})
                cpf = socio.get("cpf", "")
                participacao = payload.get("participacao", 0)
                if cpf:
                    existe = any(
                        s.get("cpf") == cpf for s in estado["socios"]
                    )
                    if not existe:
                        estado["socios"].append({
                            "cpf": cpf,
                            "nome": socio.get("nome", ""),
                            "participacao": participacao,
                            "tipo": payload.get("tipo_socio", ""),
                            "data_entrada": payload.get("data_entrada", ""),
                        })

            elif evento == CompanyEventType.REMOCAO_SOCIO.value:
                socio = payload.get("socio", {})
                cpf = socio.get("cpf", "")
                if cpf:
                    estado["socios"] = [
                        s for s in estado["socios"]
                        if s.get("cpf") != cpf
                    ]

            elif evento == CompanyEventType.MUDANCA_QUOTA.value:
                socio = payload.get("socio", {})
                cpf = socio.get("cpf", "")
                nova_part = payload.get("participacao_nova", 0)
                for s in estado["socios"]:
                    if s.get("cpf") == cpf:
                        s["participacao"] = nova_part
                        break

            elif evento == CompanyEventType.MUDANCA_CAPITAL.value:
                estado["capital_social"] = payload.get(
                    "capital_novo", estado["capital_social"]
                )

            elif evento == CompanyEventType.MUDANCA_ENDERECO.value:
                novo_end = payload.get("novo_endereco", {})
                if novo_end:
                    estado["endereco_sede"] = novo_end
                    estado["enderecos_historico"].append(novo_end)

            elif evento == CompanyEventType.MUDANCA_NOME.value:
                estado["razao_social"] = payload.get(
                    "razao_nova", estado["razao_social"]
                )
                if payload.get("nome_fantasia_novo"):
                    estado["nome_fantasia"] = payload["nome_fantasia_novo"]

            elif evento == CompanyEventType.SUSPENSAO.value:
                estado["situacao_cadastral"] = "SUSPENSA"

            elif evento == CompanyEventType.REABERTURA.value:
                estado["situacao_cadastral"] = "ATIVA"

            elif evento == CompanyEventType.LIQUIDACAO.value:
                estado["situacao_cadastral"] = "EM_LIQUIDACAO"

            elif evento == CompanyEventType.BAIXA.value:
                estado["situacao_cadastral"] = "BAIXADA"

            elif evento == CompanyEventType.CERTIDAO.value:
                cert = {
                    "tipo": payload.get("tipo_certidao", ""),
                    "numero": payload.get("numero", ""),
                    "data": payload.get("data_emissao", ""),
                    "orgao": payload.get("orgao_emissor", ""),
                }
                estado["certidoes"].append(cert)

            elif evento == CompanyEventType.GARANTIA.value:
                garantia = {
                    "credor": payload.get("credor", {}),
                    "valor": payload.get("valor_garantia", 0),
                    "data": payload.get("data_garantia", ""),
                    "vencimento": payload.get("data_vencimento", ""),
                    "tipo": payload.get("tipo_garantia", ""),
                    "status": "ATIVA",
                    "bloco_index": block.index,
                }
                estado["garantias"].append(garantia)

            elif evento == CompanyEventType.QUITACAO.value:
                idx = payload.get("garantia_index", -1)
                if 0 <= idx < len(estado["garantias"]):
                    estado["garantias"][idx]["status"] = "QUITADA"

            elif evento == CompanyEventType.ALTERACAO_CONTRATUAL.value:
                pass  # Apenas registra

        return estado

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

    def get_genesis_block(self) -> Optional[Block]:
        """Retorna o bloco gênesis (constituição)."""
        return self.chain[0] if self.chain else None

    def get_cnpj(self) -> str:
        """Retorna o CNPJ da empresa."""
        genesis = self.get_genesis_block()
        if not genesis:
            return ""
        return genesis.data.get("payload", {}).get("cnpj", "")

    def get_historico_completo(self) -> list[dict[str, Any]]:
        """Retorna timeline de todos os eventos da empresa."""
        timeline = []
        for block in self.chain:
            evento = block.data.get("evento_tipo", "DESCONHECIDO")
            payload = block.data.get("payload", {})
            ts = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp)
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

    def get_garantias_ativas(self) -> list[dict[str, Any]]:
        """Retorna garantias vigentes."""
        estado = self.get_estado_atual()
        return [g for g in estado.get("garantias", []) if g.get("status") == "ATIVA"]

    # ── Validação ─────────────────────────────────────────────────────

    def validate(self, require_signatures: bool = True) -> tuple[bool, str]:
        """
        Valida toda a cadeia.

        Args:
            require_signatures: Se True, exige assinatura ECDSA em todos os blocos.

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

        if require_signatures and not genesis.has_signature():
            return False, f"Bloco gênesis (#{genesis.index}) sem assinatura."

        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.previous_hash != previous.hash:
                return (
                    False,
                    f"Bloco #{current.index}: previous_hash não confere.",
                )

            if current.hash != current.compute_hash():
                return (
                    False,
                    f"Bloco #{current.index}: hash próprio não confere.",
                )

            if not current.is_valid():
                return (
                    False,
                    f"Bloco #{current.index}: proof-of-work inválido.",
                )

            if current.index != i:
                return (
                    False,
                    f"Bloco #{current.index}: índice fora de sequência (esperado {i}).",
                )

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
        """Verifica todas as assinaturas da cadeia."""
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
    def load_from_file(cls, filepath: str) -> "CompanyChain":
        """Carrega uma cadeia de um arquivo JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        chain = cls(difficulty=data["difficulty"])
        chain.chain = [Block.from_dict(b) for b in data["chain"]]
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
        cnpj = self.get_cnpj()
        signer_info = f", signer={self._signer.keypair.label}" if self._signer else ""
        return f"CompanyChain(cnpj={cnpj}, blocks={len(self.chain)}, difficulty={self.difficulty}{signer_info})"
