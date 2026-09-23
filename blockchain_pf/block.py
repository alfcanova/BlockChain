"""
blockchain_pf/block.py
Bloco base da Blockchain de Eventos Vitais PF.
Cada bloco encapsula um evento, mantém integridade via SHA-256,
referencia o bloco anterior pelo seu hash, e pode ser assinado
digitalmente com ECDSA para autenticação.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Block:
    """
    Bloco genérico da cadeia.
    
    Attributes:
        index:          Posição do bloco na cadeia (0 = gênesis).
        timestamp:      Unix timestamp do momento da criação.
        data:           Payload do evento (dict serializável).
        previous_hash:  Hash do bloco anterior (string hex).
        nonce:          Nonce para Proof-of-Work.
        hash:           Hash próprio do bloco (calculado automaticamente).
        difficulty:     Número de zeros iniciais exigidos no hash.
        signature:      Assinatura ECDSA (dict ou None).
    """
    index: int
    timestamp: float
    data: dict
    previous_hash: str
    nonce: int = 0
    hash: str = ""
    difficulty: int = 2  # 2 zeros iniciais (moderado para demo)
    signature: Optional[dict] = None  # BlockSignature.to_dict() ou None

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = self.compute_hash()

    # ── Hash ──────────────────────────────────────────────────────────

    def compute_hash(self) -> str:
        """
        Calcula SHA-256 sobre (index + previous_hash + data + nonce).
        O campo 'hash' e 'signature' são excluídos do cálculo
        para evitar circularidade.
        """
        block_string = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "data": self.data,
            "nonce": self.nonce,
        }, sort_keys=True, default=str)
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    # ── Proof-of-Work ─────────────────────────────────────────────────

    def mine_block(self) -> None:
        """Minera o bloco incrementando nonce até atingir a dificuldade."""
        target = "0" * self.difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()

    # ── Assinatura ────────────────────────────────────────────────────

    def set_signature(self, signer_label: str, signer_pubkey: str,
                      signature_b64: str, signed_at: float) -> None:
        """
        Define a assinatura ECDSA do bloco.
        
        Args:
            signer_label:  Nome do emissor (ex: "Cartório SP").
            signer_pubkey: Chave pública em hex comprimido.
            signature_b64: Assinatura em Base64.
            signed_at:     Timestamp da assinatura.
        """
        self.signature = {
            "signer_label": signer_label,
            "signer_pubkey": signer_pubkey,
            "signature_b64": signature_b64,
            "signed_at": signed_at,
            "block_hash": self.hash,
        }

    def has_signature(self) -> bool:
        """Verifica se o bloco possui assinatura."""
        return self.signature is not None

    # ── Serialização ──────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serializa o bloco para dict."""
        return asdict(self)

    def to_json(self) -> str:
        """Serializa o bloco para JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Block":
        """Desserializa um bloco a partir de um dict."""
        return cls(**d)

    # ── Validação ─────────────────────────────────────────────────────

    def is_valid(self) -> bool:
        """Verifica se o hash e a mineração estão corretos."""
        if self.hash != self.compute_hash():
            return False
        target = "0" * self.difficulty
        return self.hash.startswith(target)

    def __repr__(self) -> str:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))
        data_summary = str(self.data)[:60]
        sig_status = "signed" if self.signature else "unsigned"
        return (
            f"Block(index={self.index}, time={ts}, "
            f"hash={self.hash[:12]}..., {sig_status}, "
            f"data={data_summary}...)"
        )
