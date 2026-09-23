"""Testes unitarios para blockchain_pf/block.py"""

import json
import pytest
from blockchain_pf.block import Block


class TestBlockCreation:
    """Testes de criacao de bloco."""

    def test_creates_block_with_defaults(self):
        block = Block(index=0, timestamp=1.0, data={"evento": "TESTE"}, previous_hash="0" * 64)
        assert block.index == 0
        assert block.nonce == 0
        assert block.difficulty == 2
        assert block.signature is None

    def test_generates_hash_on_creation(self):
        block = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        assert block.hash != ""
        assert len(block.hash) == 64  # SHA-256 hex

    def test_hash_depends_on_data(self):
        block1 = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        block2 = Block(index=0, timestamp=1.0, data={"a": 2}, previous_hash="0" * 64)
        assert block1.hash != block2.hash

    def test_hash_depends_on_index(self):
        block1 = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        block2 = Block(index=1, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        assert block1.hash != block2.hash

    def test_hash_depends_on_previous_hash(self):
        block1 = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        block2 = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="1" * 64)
        assert block1.hash != block2.hash

    def test_hash_ignores_signature_field(self):
        """A assinatura nao deve afetar o hash do bloco."""
        block = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        hash_before = block.hash
        block.set_signature("test", "abc123", "sig_b64", 2.0)
        assert block.hash == hash_before


class TestBlockMining:
    """Testes de Proof-of-Work."""

    def test_mine_produces_valid_hash(self):
        block = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64, difficulty=2)
        block.mine_block()
        assert block.hash.startswith("00")
        assert block.is_valid()

    def test_mine_with_higher_difficulty(self):
        block = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64, difficulty=3)
        block.mine_block()
        assert block.hash.startswith("000")

    def test_mine_increments_nonce(self):
        block = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64, difficulty=2)
        initial_nonce = block.nonce
        block.mine_block()
        assert block.nonce > initial_nonce

    def test_is_valid_checks_pow(self):
        block = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64, difficulty=2)
        assert not block.is_valid()  # Nao minerado
        block.mine_block()
        assert block.is_valid()  # Minerado


class TestBlockSignature:
    """Testes de assinatura no bloco."""

    def test_no_signature_by_default(self):
        block = Block(index=0, timestamp=1.0, data={}, previous_hash="0" * 64)
        assert block.signature is None
        assert not block.has_signature()

    def test_set_signature(self):
        block = Block(index=0, timestamp=1.0, data={}, previous_hash="0" * 64)
        block.set_signature("Cartorio", "pubkey123", "sig456", 99.0)
        assert block.has_signature()
        assert block.signature["signer_label"] == "Cartorio"
        assert block.signature["signer_pubkey"] == "pubkey123"
        assert block.signature["signature_b64"] == "sig456"
        assert block.signature["block_hash"] == block.hash


class TestBlockSerialization:
    """Testes de serializacao/desserializacao."""

    def test_to_dict(self):
        block = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        d = block.to_dict()
        assert d["index"] == 0
        assert d["data"] == {"a": 1}
        assert "hash" in d
        assert "signature" in d

    def test_to_json(self):
        block = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        j = block.to_json()
        parsed = json.loads(j)
        assert parsed["index"] == 0

    def test_from_dict(self):
        original = Block(index=2, timestamp=5.0, data={"x": 10}, previous_hash="abc")
        d = original.to_dict()
        restored = Block.from_dict(d)
        assert restored.index == original.index
        assert restored.hash == original.hash
        assert restored.data == original.data

    def test_roundtrip_with_signature(self):
        block = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        block.set_signature("auth", "pk", "sig", 2.0)
        d = block.to_dict()
        restored = Block.from_dict(d)
        assert restored.has_signature()
        assert restored.signature["signer_label"] == "auth"


class TestBlockRepr:
    """Testes de representacao."""

    def test_repr_contains_key_info(self):
        block = Block(index=5, timestamp=1.0, data={}, previous_hash="0" * 64)
        r = repr(block)
        assert "index=5" in r
        assert "unsigned" in r

    def test_repr_signed(self):
        block = Block(index=0, timestamp=1.0, data={}, previous_hash="0" * 64)
        block.set_signature("auth", "pk", "sig", 1.0)
        r = repr(block)
        assert "signed" in r
