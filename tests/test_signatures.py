"""Testes unitarios para blockchain_pf/signatures.py"""

import os
import tempfile
import time
import pytest
from blockchain_pf.signatures import (
    KeyPair, Signer, BlockSignature, SignatureVerifier,
    generate_authority_keypair,
)
from blockchain_pf.block import Block


@pytest.fixture
def keypair():
    """Par de chaves para testes."""
    return KeyPair.generate("Teste Auth")


@pytest.fixture
def signer(keypair):
    """Assinador para testes."""
    return Signer(keypair)


@pytest.fixture
def sample_block():
    """Bloco de exemplo para testes."""
    return Block(index=0, timestamp=time.time(), data={"a": 1}, previous_hash="0" * 64)


# ── KeyPair ────────────────────────────────────────────────────────────

class TestKeyPair:
    def test_generates_unique_keys(self):
        kp1 = KeyPair.generate("A")
        kp2 = KeyPair.generate("B")
        assert kp1.public_key_hex() != kp2.public_key_hex()

    def test_public_key_hex_length(self, keypair):
        hex_key = keypair.public_key_hex()
        # P-256 compressed point: 33 bytes = 66 hex chars
        assert len(hex_key) == 66

    def test_fingerprint_length(self, keypair):
        fp = keypair.fingerprint()
        assert len(fp) == 16

    def test_label(self, keypair):
        assert keypair.label == "Teste Auth"

    def test_public_key_pem(self, keypair):
        pem = keypair.public_key_pem()
        assert "BEGIN PUBLIC KEY" in pem

    def test_save_and_load_private_key(self, keypair):
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            filepath = f.name

        try:
            keypair.save_private_key(filepath)
            loaded = KeyPair.load_private_key(filepath, label="Loaded")
            assert loaded.label == "Loaded"
            assert loaded.public_key_hex() == keypair.public_key_hex()
        finally:
            os.unlink(filepath)

    def test_generate_helper(self):
        kp = generate_authority_keypair("Helper")
        assert kp.label == "Helper"
        assert len(kp.public_key_hex()) == 66


# ── Signer ─────────────────────────────────────────────────────────────

class TestSigner:
    def test_sign_block_produces_signature(self, signer, sample_block):
        sig = signer.sign_block(sample_block)
        assert isinstance(sig, BlockSignature)
        assert sig.signer_label == "Teste Auth"
        assert sig.block_hash == sample_block.hash

    def test_signature_contains_pubkey(self, signer, sample_block, keypair):
        sig = signer.sign_block(sample_block)
        assert sig.signer_pubkey == keypair.public_key_hex()

    def test_signature_verifies(self, signer, keypair, sample_block):
        """Assinatura ECDSA usa nonce aleatorio, entao verificamos validade."""
        sig = signer.sign_block(sample_block)
        ok, msg = SignatureVerifier.verify_block_signature(
            sample_block, sig, keypair.public_key
        )
        assert ok

    def test_different_blocks_different_signatures(self, signer):
        block1 = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        block2 = Block(index=1, timestamp=2.0, data={"b": 2}, previous_hash="abc")
        sig1 = signer.sign_block(block1)
        sig2 = signer.sign_block(block2)
        assert sig1.signature_b64 != sig2.signature_b64


# ── BlockSignature ─────────────────────────────────────────────────────

class TestBlockSignature:
    def test_to_dict_and_from_dict(self, signer, sample_block):
        sig = signer.sign_block(sample_block)
        d = sig.to_dict()
        restored = BlockSignature.from_dict(d)
        assert restored.signer_label == sig.signer_label
        assert restored.signature_b64 == sig.signature_b64
        assert restored.block_hash == sig.block_hash

    def test_repr(self, signer, sample_block):
        sig = signer.sign_block(sample_block)
        r = repr(sig)
        assert "Teste Auth" in r
        assert "BlockSignature" in r


# ── SignatureVerifier ──────────────────────────────────────────────────

class TestSignatureVerifier:
    def test_valid_signature(self, signer, keypair, sample_block):
        sig = signer.sign_block(sample_block)
        ok, msg = SignatureVerifier.verify_block_signature(
            sample_block, sig, keypair.public_key
        )
        assert ok
        assert "válida" in msg.lower()

    def test_tampered_block_fails(self, signer, keypair):
        # Cria dois blocos diferentes
        block1 = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        block2 = Block(index=0, timestamp=1.0, data={"a": 2}, previous_hash="0" * 64)
        sig = signer.sign_block(block1)
        # Verifica com bloco adulterado (hash diferente)
        ok, msg = SignatureVerifier.verify_block_signature(
            block2, sig, keypair.public_key
        )
        assert not ok

    def test_wrong_key_fails(self, signer, sample_block):
        sig = signer.sign_block(sample_block)
        wrong_kp = KeyPair.generate("Errado")
        ok, msg = SignatureVerifier.verify_block_signature(
            sample_block, sig, wrong_kp.public_key
        )
        assert not ok

    def test_reconstruct_pubkey(self, signer, keypair, sample_block):
        sig = signer.sign_block(sample_block)
        pubkey = SignatureVerifier._reconstruct_pubkey(sig.signer_pubkey)
        ok, msg = SignatureVerifier.verify_block_signature(
            sample_block, sig, pubkey
        )
        assert ok

    def test_invalid_pubkey_hex_fails(self, signer, sample_block):
        sig = signer.sign_block(sample_block)
        sig.signer_pubkey = "000000000000000000000000000000000000000000000000000000000000000000"
        ok, msg = SignatureVerifier.verify_block_signature(
            sample_block, sig, None
        )
        assert not ok

    def test_hash_mismatch_detected(self, signer, keypair, sample_block):
        sig = signer.sign_block(sample_block)
        # Cria bloco com hash diferente
        other_block = Block(index=99, timestamp=99.0, data={"x": 99}, previous_hash="zzz")
        ok, msg = SignatureVerifier.verify_block_signature(
            other_block, sig, keypair.public_key
        )
        assert not ok
        assert "hash" in msg.lower()


# ── Integration with Block ─────────────────────────────────────────────

class TestBlockIntegration:
    def test_block_set_signature_and_verify(self, keypair, signer, sample_block):
        sig = signer.sign_block(sample_block)
        sample_block.set_signature(
            signer_label=sig.signer_label,
            signer_pubkey=sig.signer_pubkey,
            signature_b64=sig.signature_b64,
            signed_at=sig.signed_at,
        )
        assert sample_block.has_signature()

        # Verifica
        sig_dict = sample_block.signature
        block_sig = BlockSignature.from_dict(sig_dict)
        ok, msg = SignatureVerifier.verify_block_signature(
            sample_block, block_sig, keypair.public_key
        )
        assert ok
