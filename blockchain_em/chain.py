"""
blockchain_em/chain.py
Cadeia de blocos para eventos de embarcações.
Gênesis = construção da embarcação.
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

from .events import VesselEventType, VesselChainProtector


class VesselChain:
    """
    Cadeia de blocos para uma embarcação.

    A cadeia começa com um bloco gênesis que representa a construção
    da embarcação (registro, especificações técnicas).
    Cada bloco pode ser assinado digitalmente com ECDSA.
    """

    def __init__(self, difficulty: int = 2) -> None:
        self.difficulty = difficulty
        self.chain: list[Block] = []
        self._event_index: dict[str, list[int]] = {}
        self._default_keypair = generate_authority_keypair("capitania_portos")
        self._signer = Signer(self._default_keypair)

    def set_signer(self, keypair: KeyPair) -> None:
        self._signer = Signer(keypair)

    @property
    def signer(self) -> Optional[Signer]:
        return self._signer

    def create_genesis(self, embarcacao_data: dict[str, Any]) -> Block:
        """
        Cria o bloco gênesis com dados da embarcação.
        O bloco é obrigatoriamente assinado com ECDSA.

        Raises:
            ValueError: Se nenhum signer estiver configurado.
        """
        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")
        genesis = Block(
            index=0,
            timestamp=time.time(),
            data={
                "evento_tipo": VesselEventType.CONSTRUCAO.value,
                "payload": embarcacao_data,
                "hash_cadeia": "GENESIS",
            },
            previous_hash="0" * 64,
            difficulty=self.difficulty,
        )
        genesis.mine_block()
        sig = self._signer.sign_block(genesis)
        genesis.set_signature(
            signer_label=sig.signer_label,
            signer_pubkey=sig.signer_pubkey,
            signature_b64=sig.signature_b64,
            signed_at=sig.signed_at,
        )
        self.chain.append(genesis)
        self._index_event(VesselEventType.CONSTRUCAO.value, 0)
        return genesis

    def add_event(self, event_type: str, payload: dict[str, Any]) -> Block:
        if not self.chain:
            raise ValueError("Cadeia vazia — crie o bloco gênesis primeiro.")
        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")
        estado = self.get_estado_atual()
        if not VesselChainProtector.pode_adicionar(
            event_type, estado.get("situacao", "REGULAR")
        ):
            raise ValueError(
                f"Evento '{event_type}' bloqueado para embarcação com estado "
                f"'{estado.get('situacao')}'."
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

    def get_estado_atual(self) -> dict[str, Any]:
        if not self.chain:
            return {}
        genesis = self.chain[0]
        payload_genesis = genesis.data.get("payload", {})
        estado = {
            "registro_nr": payload_genesis.get("registro_nr", ""),
            "nome_embarcacao": payload_genesis.get("nome_embarcacao", ""),
            "tipo_embarcacao": payload_genesis.get("tipo_embarcacao", ""),
            "porte": payload_genesis.get("porte", ""),
            "comprimento_m": payload_genesis.get("comprimento_m", 0),
            "beam_m": payload_genesis.get("beam_m", 0),
            "casco": payload_genesis.get("casco", {}),
            "motorizacao": payload_genesis.get("motorizacao", ""),
            "motor": payload_genesis.get("motor", {}),
            "ano_construcao": payload_genesis.get("ano_construcao", 0),
            "estaleiro": payload_genesis.get("estaleiro", {}),
            "bandeira": payload_genesis.get("bandeira", ""),
            "porto_registro": payload_genesis.get("porto_registro", ""),
            "situacao": payload_genesis.get("situacao", "REGULAR"),
            "proprietarios": list(payload_genesis.get("proprietarios", [])),
            "seguros": list(payload_genesis.get("seguros", [])),
            "certidoes": list(payload_genesis.get("certidoes", [])),
        }
        for block in self.chain[1:]:
            evento = block.data.get("evento_tipo", "")
            payload = block.data.get("payload", {})
            if evento == VesselEventType.COMPRA_VENDA.value:
                comprador = payload.get("comprador", {})
                vendedor = payload.get("vendedor", {})
                cpf_c = comprador.get("cpf", "")
                cpf_v = vendedor.get("cpf", "")
                estado["proprietarios"] = [
                    p for p in estado["proprietarios"]
                    if p.get("cpf") != cpf_v
                ]
                if cpf_c and not any(p.get("cpf") == cpf_c for p in estado["proprietarios"]):
                    estado["proprietarios"].append({
                        "cpf": cpf_c, "nome": comprador.get("nome", ""),
                        "participacao": 100.0, "origem": "COMPRA",
                    })
            elif evento == VesselEventType.DOACAO.value:
                donatario = payload.get("donatario", {})
                doador = payload.get("doador", {})
                cpf_d = donatario.get("cpf", "")
                cpf_do = doador.get("cpf", "")
                estado["proprietarios"] = [
                    p for p in estado["proprietarios"]
                    if p.get("cpf") != cpf_do
                ]
                if cpf_d and not any(p.get("cpf") == cpf_d for p in estado["proprietarios"]):
                    estado["proprietarios"].append({
                        "cpf": cpf_d, "nome": donatario.get("nome", ""),
                        "participacao": 100.0, "origem": "DOACAO",
                    })
            elif evento == VesselEventType.MUDANCA_NOME.value:
                estado["nome_embarcacao"] = payload.get("nome_novo", estado["nome_embarcacao"])
            elif evento == VesselEventType.BAIXA.value:
                estado["situacao"] = "BAIXADA"
            elif evento == VesselEventType.SEGURO.value:
                seguro = {
                    "seguradora": payload.get("seguradora", {}),
                    "apolice": payload.get("apolice_numero", ""),
                    "data_inicio": payload.get("data_inicio", ""),
                    "data_fim": payload.get("data_fim", ""),
                    "valor": payload.get("valor_segurado", 0),
                    "status": "ATIVA",
                    "bloco_index": block.index,
                }
                estado["seguros"].append(seguro)
            elif evento == VesselEventType.CERTIDAO.value:
                cert = {
                    "tipo": payload.get("tipo_certidao", ""),
                    "numero": payload.get("numero", ""),
                    "data": payload.get("data_emissao", ""),
                }
                estado["certidoes"].append(cert)
        return estado

    def get_event(self, index: int) -> Optional[Block]:
        return self.chain[index] if 0 <= index < len(self.chain) else None

    def get_events_by_type(self, event_type: str) -> list[Block]:
        indices = self._event_index.get(event_type, [])
        return [self.chain[i] for i in indices if i < len(self.chain)]

    def get_genesis_block(self) -> Optional[Block]:
        return self.chain[0] if self.chain else None

    def get_registro_nr(self) -> str:
        genesis = self.get_genesis_block()
        return genesis.data.get("payload", {}).get("registro_nr", "") if genesis else ""

    def get_historico_completo(self) -> list[dict[str, Any]]:
        timeline = []
        for block in self.chain:
            evento = block.data.get("evento_tipo", "DESCONHECIDO")
            payload = block.data.get("payload", {})
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp))
            signed = block.has_signature()
            signer = block.signature.get("signer_label", "") if signed else ""
            timeline.append({
                "indice": block.index, "tipo": evento,
                "data_registro": ts, "hash": block.hash[:16],
                "assinado": signed, "emissor": signer, "dados": payload,
            })
        return timeline

    def validate(self, require_signatures: bool = True) -> tuple[bool, str]:
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
                return False, f"Bloco #{current.index}: previous_hash não confere."
            if current.hash != current.compute_hash():
                return False, f"Bloco #{current.index}: hash próprio não confere."
            if not current.is_valid():
                return False, f"Bloco #{current.index}: proof-of-work inválido."
            if current.index != i:
                return False, f"Bloco #{current.index}: índice fora de sequência."
            if require_signatures:
                if not current.has_signature():
                    return False, f"Bloco #{current.index}: sem assinatura ECDSA."
                sig = BlockSignature.from_dict(current.signature)
                ok, msg = self._verify_signature(current, sig)
                if not ok:
                    return False, f"Bloco #{current.index}: assinatura inválida — {msg}"
        sig_count = sum(1 for b in self.chain if b.has_signature())
        suffix = f" | {sig_count}/{len(self.chain)} assinado(s)" if sig_count else ""
        return True, f"Cadeia válida — {len(self.chain)} bloco(s).{suffix}"

    def verify_all_signatures(self) -> tuple[bool, str]:
        unsigned, invalid = [], []
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
        return not unsigned and not invalid, " | ".join(lines)

    def _verify_signature(self, block: Block, sig: BlockSignature) -> tuple[bool, str]:
        try:
            pubkey = SignatureVerifier._reconstruct_pubkey(sig.signer_pubkey)
            return SignatureVerifier.verify_block_signature(block, sig, pubkey)
        except Exception as e:
            return False, f"Erro na verificação: {e}"

    def save_to_file(self, filepath: str) -> None:
        data = {"difficulty": self.difficulty, "chain": [b.to_dict() for b in self.chain]}
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    @classmethod
    def load_from_file(cls, filepath: str) -> "VesselChain":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        chain = cls(difficulty=data["difficulty"])
        chain.chain = [Block.from_dict(b) for b in data["chain"]]
        for i, block in enumerate(chain.chain):
            chain._index_event(block.data.get("evento_tipo", ""), i)
        return chain

    def _index_event(self, event_type: str, index: int) -> None:
        if event_type not in self._event_index:
            self._event_index[event_type] = []
        self._event_index[event_type].append(index)

    def __len__(self) -> int:
        return len(self.chain)

    def __repr__(self) -> str:
        reg = self.get_registro_nr()
        signer_info = f", signer={self._signer.keypair.label}" if self._signer else ""
        return f"VesselChain(registro={reg}, blocks={len(self.chain)}, difficulty={self.difficulty}{signer_info})"
