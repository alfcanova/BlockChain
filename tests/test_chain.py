"""Testes unitarios para blockchain_pf/chain.py"""

import os
import json
import tempfile
import pytest
from blockchain_pf.chain import Blockchain
from blockchain_pf.events import EventType
from blockchain_pf.signatures import generate_authority_keypair


@pytest.fixture
def chain():
    """Cadeia vazia para testes."""
    return Blockchain(difficulty=2)


@pytest.fixture
def signed_chain():
    """Cadeia com assinador para testes."""
    c = Blockchain(difficulty=2)
    kp = generate_authority_keypair("Teste")
    c.set_signer(kp)
    return c


@pytest.fixture
def birth_data():
    """Dados de nascimento para testes."""
    return {
        "cpf": "12345678901",
        "nome_completo": "Maria Clara",
        "data_nascimento": "15/03/2000",
        "sexo": "F",
        "cidade_nascimento": "Sao Paulo",
        "uf_nascimento": "SP",
        "nome_mae": "Ana Paula",
    }


# ── Genesis ────────────────────────────────────────────────────────────

class TestGenesis:
    def test_creates_genesis_block(self, chain, birth_data):
        genesis = chain.create_genesis(birth_data)
        assert genesis.index == 0
        assert genesis.data["evento_tipo"] == "NASCIMENTO"
        assert genesis.previous_hash == "0" * 64

    def test_genesis_is_valid(self, chain, birth_data):
        chain.create_genesis(birth_data)
        assert chain.chain[0].is_valid()

    def test_genesis_has_correct_payload(self, chain, birth_data):
        chain.create_genesis(birth_data)
        payload = chain.chain[0].data["payload"]
        assert payload["cpf"] == "12345678901"
        assert payload["nome_completo"] == "Maria Clara"

    def test_genesis_signed_when_signer_configured(self, signed_chain, birth_data):
        signed_chain.create_genesis(birth_data)
        assert signed_chain.chain[0].has_signature()

    def test_genesis_signed_by_default(self, chain, birth_data):
        """Todos os blocos sao obrigatoriamente assinados."""
        chain.create_genesis(birth_data)
        assert chain.chain[0].has_signature()


# ── Add Event ──────────────────────────────────────────────────────────

class TestAddEvent:
    def test_add_event_increases_chain_length(self, chain, birth_data):
        chain.create_genesis(birth_data)
        chain.add_event("CASAMENTO", {"cpf": "12345678901"})
        assert len(chain) == 2

    def test_add_event_links_to_previous(self, chain, birth_data):
        chain.create_genesis(birth_data)
        block = chain.add_event("CASAMENTO", {"cpf": "12345678901"})
        assert block.previous_hash == chain.chain[0].hash

    def test_add_event_sequential_index(self, chain, birth_data):
        chain.create_genesis(birth_data)
        block = chain.add_event("CASAMENTO", {})
        assert block.index == 1

    def test_add_event_raises_on_empty_chain(self):
        chain = Blockchain()
        with pytest.raises(ValueError, match="Cadeia vazia"):
            chain.add_event("CASAMENTO", {})

    def test_add_multiple_events(self, chain, birth_data):
        chain.create_genesis(birth_data)
        chain.add_event("CASAMENTO", {})
        chain.add_event("DIVORCIO", {})
        chain.add_event("ALTERACAO_NOME", {})
        assert len(chain) == 4

    def test_signed_chain_signs_new_events(self, signed_chain, birth_data):
        signed_chain.create_genesis(birth_data)
        block = signed_chain.add_event("CASAMENTO", {})
        assert block.has_signature()


# ── Validation ─────────────────────────────────────────────────────────

class TestValidation:
    def test_empty_chain_invalid(self):
        chain = Blockchain()
        valid, msg = chain.validate()
        assert not valid
        assert "vazia" in msg

    def test_single_genesis_valid(self, chain, birth_data):
        chain.create_genesis(birth_data)
        valid, msg = chain.validate()
        assert valid
        assert "1 bloco" in msg

    def test_multi_block_chain_valid(self, chain, birth_data):
        chain.create_genesis(birth_data)
        chain.add_event("CASAMENTO", {})
        chain.add_event("DIVORCIO", {})
        valid, msg = chain.validate()
        assert valid
        assert "3 bloco" in msg

    def test_tampered_hash_detected(self, chain, birth_data):
        chain.create_genesis(birth_data)
        chain.add_event("CASAMENTO", {})
        # Adultera o hash
        chain.chain[1].hash = "0" * 64
        valid, msg = chain.validate()
        assert not valid
        assert "hash" in msg.lower() or "corrompido" in msg.lower()

    def test_validate_with_signatures(self, signed_chain, birth_data):
        signed_chain.create_genesis(birth_data)
        signed_chain.add_event("CASAMENTO", {})
        valid, msg = signed_chain.validate(require_signatures=True)
        assert valid
        assert "assinado" in msg

    def test_validate_without_signatures(self, signed_chain, birth_data):
        signed_chain.create_genesis(birth_data)
        valid, msg = signed_chain.validate(require_signatures=False)
        assert valid

    def test_signed_block_passes_signature_validation(self, chain, birth_data):
        """Todos os blocos sao assinados, validacao passa."""
        chain.create_genesis(birth_data)
        valid, msg = chain.validate(require_signatures=True)
        assert valid
        assert "assinado" in msg


# ── Signatures ─────────────────────────────────────────────────────────

class TestSignatureVerification:
    def test_all_signatures_valid(self, signed_chain, birth_data):
        signed_chain.create_genesis(birth_data)
        signed_chain.add_event("CASAMENTO", {})
        ok, msg = signed_chain.verify_all_signatures()
        assert ok
        assert "válidas" in msg.lower()

    def test_tampered_block_invalidates_signature(self, signed_chain, birth_data):
        signed_chain.create_genesis(birth_data)
        signed_chain.add_event("CASAMENTO", {})
        # Adultera dados
        signed_chain.chain[1].data["payload"]["cpf"] = "FAKE"
        signed_chain.chain[1].hash = signed_chain.chain[1].compute_hash()
        ok, msg = signed_chain.verify_all_signatures()
        assert not ok

    def test_all_blocks_signed_detected(self, chain, birth_data):
        """Todos os blocos sao assinados, verificacao passa."""
        chain.create_genesis(birth_data)
        ok, msg = chain.verify_all_signatures()
        assert ok
        assert "válidas" in msg.lower()


# ── Search ─────────────────────────────────────────────────────────────

class TestSearch:
    def test_get_event(self, chain, birth_data):
        chain.create_genesis(birth_data)
        chain.add_event("CASAMENTO", {})
        assert chain.get_event(0) is not None
        assert chain.get_event(1) is not None
        assert chain.get_event(2) is None

    def test_get_events_by_type(self, chain, birth_data):
        chain.create_genesis(birth_data)
        chain.add_event("CASAMENTO", {})
        chain.add_event("DIVORCIO", {})
        chain.add_event("CASAMENTO", {})
        casamentos = chain.get_events_by_type("CASAMENTO")
        assert len(casamentos) == 2
        divorcios = chain.get_events_by_type("DIVORCIO")
        assert len(divorcios) == 1

    def test_get_last_event(self, chain, birth_data):
        chain.create_genesis(birth_data)
        assert chain.get_last_event().index == 0
        chain.add_event("CASAMENTO", {})
        assert chain.get_last_event().index == 1

    def test_get_birth_block(self, chain, birth_data):
        chain.create_genesis(birth_data)
        chain.add_event("CASAMENTO", {})
        birth = chain.get_birth_block()
        assert birth.index == 0
        assert birth.data["evento_tipo"] == "NASCIMENTO"

    def test_get_timeline(self, chain, birth_data):
        chain.create_genesis(birth_data)
        chain.add_event("CASAMENTO", {})
        tl = chain.get_timeline()
        assert len(tl) == 2
        assert tl[0]["tipo"] == "NASCIMENTO"
        assert tl[1]["tipo"] == "CASAMENTO"
        assert "assinado" in tl[0]


# ── Persistence ────────────────────────────────────────────────────────

class TestPersistence:
    def test_save_and_load(self, chain, birth_data):
        chain.create_genesis(birth_data)
        chain.add_event("CASAMENTO", {})

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            chain.save_to_file(filepath)
            loaded = Blockchain.load_from_file(filepath)
            assert len(loaded) == 2
            assert loaded.chain[0].data["evento_tipo"] == "NASCIMENTO"
            valid, _ = loaded.validate()
            assert valid
        finally:
            os.unlink(filepath)

    def test_save_with_signatures(self, signed_chain, birth_data):
        signed_chain.create_genesis(birth_data)
        signed_chain.add_event("CASAMENTO", {})

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            signed_chain.save_to_file(filepath)
            loaded = Blockchain.load_from_file(filepath)
            assert loaded.chain[0].has_signature()
            valid, _ = loaded.validate(require_signatures=True)
            assert valid
        finally:
            os.unlink(filepath)


# ── Repr ───────────────────────────────────────────────────────────────

class TestRepr:
    def test_repr(self, chain):
        r = repr(chain)
        assert "Blockchain" in r
        assert "blocks=0" in r

    def test_len(self, chain, birth_data):
        assert len(chain) == 0
        chain.create_genesis(birth_data)
        assert len(chain) == 1
