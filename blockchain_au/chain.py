"""
blockchain_au/chain.py
Cadeia de autoridade: NOMEACAO (genesis) + ALTERACAO/REVOGACAO.

Reutiliza blockchain_pf.Blockchain (hashchain + PoW + assinaturas ECDSA)
e ajusta o genesis para o tipo NOMEACAO com estado derivado dos blocos.
"""

import time
from typing import Any, Optional

from blockchain_pf.block import Block
from blockchain_pf.chain import Blockchain

from .events import AuthorityEventType


class AuthorityChain(Blockchain):
    """
    Cadeia bloqueada e assinada de uma autoridade (N1 UF / N2 cidade).

    O estado vigente e a fusao dos snapshots NOMEACAO/ALTERACAO;
    um bloco REVOGACAO marca 'revogado=True' e encerra o ciclo de vida.
    """

    def create_genesis(self, authority_data: dict[str, Any]) -> Block:
        """Genesis: bloco assinado com o snapshot inicial da autoridade."""
        if not self._signer:
            raise ValueError(
                "Cadeia requer assinador configurado (set_signer) para registrar operacoes."
            )
        genesis = Block(
            index=0,
            timestamp=time.time(),
            data={
                "evento_tipo": AuthorityEventType.NOMEACAO.value,
                "payload": authority_data,
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
        self._index_event(AuthorityEventType.NOMEACAO.value, 0)
        return genesis

    def get_estado_atual(self) -> dict[str, Any]:
        """
        Estado vigente da autoridade (dados mergeados dos blocos).

        Inclui: username, nome, nivel, escopo, uf, cidade, nomeado_por,
                revogado, revogado_data, motivo_revogacao.
        """
        estado: dict[str, Any] = {
            "revogado": False,
            "revogado_data": "",
            "motivo_revogacao": "",
        }
        for block in self.chain:
            evento = block.data.get("evento_tipo", "")
            payload = block.data.get("payload", {})
            if evento == AuthorityEventType.REVOGACAO.value:
                estado["revogado"] = True
                estado["revogado_data"] = payload.get("data", "")
                estado["motivo_revogacao"] = payload.get("motivo", "")
            else:
                estado.update({k: v for k, v in payload.items() if k not in ("revogado",)})
                estado["revogado"] = False
        return estado