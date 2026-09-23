"""
blockchain_pf/signatures.py
Assinaturas digitais ECDSA (P-256 / secp256r1) para autenticação de blocos.

Cada bloco é assinado pelo emissor (autoridade) após a mineração.
A assinatura cobre o hash do bloco, impedindo falsificação.

Esquema:
  1. Gera-se um par de chaves ECDSA (P-256) por autoridade.
  2. Após mineração, o emissor assina o hash do bloco.
  3. Qualquer um pode verificar a assinatura com a chave pública.
  4. Alteração do bloco invalida a assinatura.
"""

import hashlib
import json
import os
import time
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from typing import Any, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
    SECP256R1,
)
from cryptography.exceptions import InvalidSignature


# ── Par de Chaves ──────────────────────────────────────────────────────

@dataclass
class KeyPair:
    """
    Par de chaves ECDSA (P-256).
    
    Attributes:
        private_key: Chave privada ECDSA.
        public_key:  Chave pública ECDSA.
        label:       Identificador legível da chave (ex: "Cartório SP").
    """
    private_key: EllipticCurvePrivateKey
    public_key: EllipticCurvePublicKey
    label: str = "autoridade"

    @classmethod
    def generate(cls, label: str = "autoridade") -> "KeyPair":
        """Gera um novo par de chaves ECDSA P-256."""
        private_key = ec.generate_private_key(SECP256R1())
        public_key = private_key.public_key()
        return cls(private_key=private_key, public_key=public_key, label=label)

    # ── Serialização ──────────────────────────────────────────────────

    def public_key_pem(self) -> str:
        """Retorna a chave pública em PEM (Base64)."""
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode("utf-8")

    def public_key_hex(self) -> str:
        """Retorna a chave pública como hex (formato compacto para blocos)."""
        raw = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint,
        )
        return raw.hex()

    def fingerprint(self) -> str:
        """Fingerprint curto da chave pública (SHA-256, 16 hex)."""
        raw = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint,
        )
        return hashlib.sha256(raw).hexdigest()[:16]

    def save_private_key(self, filepath: str, password: Optional[bytes] = None) -> None:
        """Salva a chave privada em arquivo PEM."""
        encryption = (
            serialization.BestAvailableEncryption(password)
            if password
            else serialization.NoEncryption()
        )
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption,
        )
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(pem)

    @classmethod
    def load_private_key(
        cls, filepath: str, password: Optional[bytes] = None, label: str = "autoridade"
    ) -> "KeyPair":
        """Carrega uma chave privada de arquivo PEM e reconstrói o par."""
        with open(filepath, "rb") as f:
            pem = f.read()
        decryption = (
            serialization.BestAvailableEncryption(password)
            if password
            else serialization.NoEncryption()
        )
        private_key = serialization.load_pem_private_key(pem, password=password)
        if not isinstance(private_key, EllipticCurvePrivateKey):
            raise TypeError("Chave não é ECDSA privada.")
        return cls(
            private_key=private_key,
            public_key=private_key.public_key(),
            label=label,
        )


# ── Assinatura ─────────────────────────────────────────────────────────

@dataclass
class BlockSignature:
    """
    Assinatura ECDSA de um bloco.
    
    Attributes:
        signer_label:   Nome/identificador do emissor.
        signer_pubkey:  Chave pública do emissor (hex comprimido).
        signature_b64:  Assinatura em Base64.
        signed_at:      Timestamp da assinatura.
        block_hash:     Hash do bloco assinado.
    """
    signer_label: str
    signer_pubkey: str
    signature_b64: str
    signed_at: float
    block_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "signer_label": self.signer_label,
            "signer_pubkey": self.signer_pubkey,
            "signature_b64": self.signature_b64,
            "signed_at": self.signed_at,
            "block_hash": self.block_hash,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BlockSignature":
        return cls(**d)

    def __repr__(self) -> str:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.signed_at))
        return (
            f"BlockSignature(signer={self.signer_label}, "
            f"block={self.block_hash[:12]}..., at={ts})"
        )


# ── Assinador ──────────────────────────────────────────────────────────

class Signer:
    """
    Assinador de blocos usando ECDSA.
    
    Uso:
        keypair = KeyPair.generate("Cartório SP")
        signer = Signer(keypair)
        
        # Após minerar o bloco:
        block.signature = signer.sign_block(block)
    """

    def __init__(self, keypair: KeyPair) -> None:
        self.keypair = keypair

    def sign_block(self, block: Any) -> BlockSignature:
        """
        Assina um bloco após mineração.
        
        A assinatura cobre: block_hash + index + timestamp.
        Isso garante que a assinatura é única para cada bloco.
        
        Args:
            block: Objeto Block (ou dict com hash, index, timestamp).
        
        Returns:
            BlockSignature com a assinatura ECDSA.
        """
        # Dados a serem assinados (do bloco, não do hash como string)
        sign_data = self._block_sign_payload(block)

        # Assina com ECDSA + SHA-256
        signature = self.keypair.private_key.sign(
            sign_data,
            ec.ECDSA(hashes.SHA256()),
        )

        return BlockSignature(
            signer_label=self.keypair.label,
            signer_pubkey=self.keypair.public_key_hex(),
            signature_b64=b64encode(signature).decode("ascii"),
            signed_at=time.time(),
            block_hash=block.hash if hasattr(block, "hash") else block.get("hash", ""),
        )

    @staticmethod
    def _block_sign_payload(block: Any) -> bytes:
        """
        Gera os bytes a serem assinados a partir de um bloco.
        Inclui hash + index + timestamp para prevenir replay.
        """
        if hasattr(block, "hash"):
            block_hash = block.hash
            block_index = block.index
            block_ts = block.timestamp
        else:
            block_hash = block.get("hash", "")
            block_index = block.get("index", 0)
            block_ts = block.get("timestamp", 0)

        payload = json.dumps({
            "block_hash": block_hash,
            "block_index": block_index,
            "block_timestamp": block_ts,
        }, sort_keys=True).encode("utf-8")
        return payload


# ── Verificador ────────────────────────────────────────────────────────

class SignatureVerifier:
    """
    Verificador de assinaturas ECDSA.
    
    Pode verificar com chave pública fornecida ou reconstruída do hex.
    """

    @staticmethod
    def verify_block_signature(
        block: Any,
        signature: BlockSignature,
        public_key: Optional[EllipticCurvePublicKey] = None,
    ) -> tuple[bool, str]:
        """
        Verifica se a assinatura de um bloco é válida.
        
        Args:
            block:      Objeto Block ou dict.
            signature:  BlockSignature a verificar.
            public_key: Chave pública do emissor (opcional, reconstrói do hex se omitido).
        
        Returns:
            Tuple (é_válida, mensagem).
        """
        if public_key is None:
            try:
                public_key = SignatureVerifier._reconstruct_pubkey(signature.signer_pubkey)
            except Exception as e:
                return False, f"Erro ao reconstruir chave pública: {e}"

        # Verifica se o hash do bloco confere
        block_hash = block.hash if hasattr(block, "hash") else block.get("hash", "")
        if block_hash != signature.block_hash:
            return (
                False,
                f"Hash do bloco não confere: "
                f"bloco={block_hash[:12]}... vs assinatura={signature.block_hash[:12]}...",
            )

        # Verifica a assinatura ECDSA
        sign_data = Signer._block_sign_payload(block)
        sig_bytes = b64decode(signature.signature_b64)

        try:
            public_key.verify(sig_bytes, sign_data, ec.ECDSA(hashes.SHA256()))
            return True, "Assinatura ECDSA válida."
        except InvalidSignature:
            return False, "Assinatura ECDSA INVÁLIDA — bloco pode ter sido adulterado."

    @staticmethod
    def _reconstruct_pubkey(pubkey_hex: str) -> EllipticCurvePublicKey:
        """Reconstrói chave pública ECDSA a partir do hex comprimido."""
        raw = bytes.fromhex(pubkey_hex)
        return ec.EllipticCurvePublicKey.from_encoded_point(SECP256R1(), raw)


# ── Utilitários ────────────────────────────────────────────────────────

def generate_authority_keypair(label: str = "cartorio") -> KeyPair:
    """Gera um par de chaves de autoridade para assinatura de blocos."""
    return KeyPair.generate(label=label)


def demo_signature() -> None:
    """Demonstração rápida do sistema de assinatura."""
    # Gera chaves
    kp = KeyPair.generate("Cartório de Registro Civil")
    signer = Signer(kp)

    print(f"Chave pública (hex):  {kp.public_key_hex()}")
    print(f"Fingerprint:         {kp.fingerprint()}")
    print(f"Label:               {kp.label}")

    # Bloco fictício
    fake_block = {
        "index": 0,
        "hash": "001377580115c08f5c62a098f2ea909efdfeade7f0da8b32104d1c157a822e73",
        "timestamp": time.time(),
    }

    # Assina
    sig = signer.sign_block(fake_block)
    print(f"\nAssinatura: {sig}")

    # Verifica
    ok, msg = SignatureVerifier.verify_block_signature(fake_block, sig, kp.public_key)
    print(f"Verificação: {ok} — {msg}")

    # Teste com hash adulterado
    fake_block_bad = dict(fake_block, hash="0000000000000000000000000000000000000000000000000000000000000000")
    ok2, msg2 = SignatureVerifier.verify_block_signature(fake_block_bad, sig, kp.public_key)
    print(f"Verificação (adulterado): {ok2} — {msg2}")


if __name__ == "__main__":
    demo_signature()
