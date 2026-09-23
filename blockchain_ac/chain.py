"""
blockchain_ac/chain.py
Cadeia de blocos para eventos de aeronaves.
Gênesis = fabricação da aeronave.
Validação integral (hash + PoW + assinaturas ECDSA),
persistência em JSON e operações de busca.
"""

import json
import os
import time
from typing import Any, Optional

from blockchain_pf.block import Block
from blockchain_pf.signatures import (
    KeyPair, Signer, BlockSignature, SignatureVerifier,
    generate_authority_keypair,
)

from .events import AircraftEventType, AircraftChainProtector


class AircraftChain:
    """
    Cadeia de blocos para uma aeronave.
    Gênesis = fabricação (matrícula, modelo, especificações técnicas).
    """

    def __init__(self, difficulty: int = 2) -> None:
        self.difficulty = difficulty
        self.chain: list[Block] = []
        self._event_index: dict[str, list[int]] = {}
        self._default_keypair = generate_authority_keypair("anac")
        self._signer = Signer(self._default_keypair)

    def set_signer(self, keypair: KeyPair) -> None:
        self._signer = Signer(keypair)

    @property
    def signer(self) -> Optional[Signer]:
        return self._signer

    def create_genesis(self, data: dict[str, Any]) -> Block:
        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")
        genesis = Block(
            index=0, timestamp=time.time(),
            data={"evento_tipo": AircraftEventType.FABRICACAO.value, "payload": data, "hash_cadeia": "GENESIS"},
            previous_hash="0" * 64, difficulty=self.difficulty,
        )
        genesis.mine_block()
        sig = self._signer.sign_block(genesis)
        genesis.set_signature(signer_label=sig.signer_label, signer_pubkey=sig.signer_pubkey,
                              signature_b64=sig.signature_b64, signed_at=sig.signed_at)
        self.chain.append(genesis)
        self._index_event(AircraftEventType.FABRICACAO.value, 0)
        return genesis

    def add_event(self, event_type: str, payload: dict[str, Any]) -> Block:
        if not self.chain:
            raise ValueError("Cadeia vazia — crie o bloco gênesis primeiro.")
        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")
        estado = self.get_estado_atual()
        if not AircraftChainProtector.pode_adicionar(event_type, estado.get("situacao", "REGULAR")):
            raise ValueError(f"Evento '{event_type}' bloqueado.")
        last_block = self.chain[-1]
        new_block = Block(
            index=last_block.index + 1, timestamp=time.time(),
            data={"evento_tipo": event_type, "payload": payload, "hash_cadeia": last_block.hash},
            previous_hash=last_block.hash, difficulty=self.difficulty,
        )
        new_block.mine_block()
        sig = self._signer.sign_block(new_block)
        new_block.set_signature(signer_label=sig.signer_label, signer_pubkey=sig.signer_pubkey,
                                signature_b64=sig.signature_b64, signed_at=sig.signed_at)
        self.chain.append(new_block)
        self._index_event(event_type, new_block.index)
        return new_block

    def get_estado_atual(self) -> dict[str, Any]:
        if not self.chain:
            return {}
        genesis = self.chain[0]
        p = genesis.data.get("payload", {})
        estado = {
            "matricula": p.get("matricula", ""), "nome_aeronave": p.get("nome_aeronave", ""),
            "fabricante": p.get("fabricante", ""), "modelo": p.get("modelo", ""),
            "tipo_aeronave": p.get("tipo_aeronave", ""), "ano_fabricacao": p.get("ano_fabricacao", 0),
            "peso_max_decolagem_kg": p.get("peso_max_decolagem_kg", 0),
            "motorizacao": p.get("motorizacao", ""), "num_motores": p.get("num_motores", 0),
            "motor": p.get("motor", {}), "dimensoes": p.get("dimensoes", {}),
            "desempenho": p.get("desempenho", {}), "capacidade": p.get("capacidade", {}),
            "pais_fabricacao": p.get("pais_fabricacao", ""),
            "situacao": p.get("situacao", "REGULAR"),
            "proprietarios": list(p.get("proprietarios", [])),
            "seguros": list(p.get("seguros", [])),
            "certidoes": list(p.get("certidoes", [])),
            "airworthiness": list(p.get("airworthiness", [])),
            "historico_manutencao": list(p.get("historico_manutencao", [])),
        }
        for block in self.chain[1:]:
            evt = block.data.get("evento_tipo", "")
            pl = block.data.get("payload", {})
            if evt == AircraftEventType.COMPRA_VENDA.value:
                comp = pl.get("comprador", {})
                vend = pl.get("vendedor", {})
                cpf_c, cpf_v = comp.get("cpf", ""), vend.get("cpf", "")
                estado["proprietarios"] = [x for x in estado["proprietarios"] if x.get("cpf") != cpf_v]
                if cpf_c and not any(x.get("cpf") == cpf_c for x in estado["proprietarios"]):
                    estado["proprietarios"].append({"cpf": cpf_c, "nome": comp.get("nome", ""), "participacao": 100.0})
            elif evt == AircraftEventType.DOACAO.value:
                don = pl.get("donatario", {})
                cpf_d = don.get("cpf", "")
                if cpf_d and not any(x.get("cpf") == cpf_d for x in estado["proprietarios"]):
                    estado["proprietarios"].append({"cpf": cpf_d, "nome": don.get("nome", ""), "participacao": 100.0})
            elif evt == AircraftEventType.MUDANCA_NOME.value:
                estado["nome_aeronave"] = pl.get("nome_novo", estado["nome_aeronave"])
            elif evt == AircraftEventType.REGISTRO.value:
                estado["matricula"] = pl.get("nova_matricula", estado["matricula"])
            elif evt == AircraftEventType.BAIXA.value:
                estado["situacao"] = "BAIXADA"
            elif evt == AircraftEventType.SEGURO.value:
                estado["seguros"].append({"seguradora": pl.get("seguradora", {}), "apolice": pl.get("apolice_numero", ""), "status": "ATIVA"})
            elif evt == AircraftEventType.AIRWORTHINESS.value:
                estado["airworthiness"].append({"numero": pl.get("numero_certificado", ""), "validade": pl.get("data_validade", ""), "status": "ATIVA"})
        return estado

    def get_event(self, index: int) -> Optional[Block]:
        return self.chain[index] if 0 <= index < len(self.chain) else None

    def get_events_by_type(self, event_type: str) -> list[Block]:
        return [self.chain[i] for i in self._event_index.get(event_type, []) if i < len(self.chain)]

    def get_genesis_block(self) -> Optional[Block]:
        return self.chain[0] if self.chain else None

    def get_matricula(self) -> str:
        g = self.get_genesis_block()
        return g.data.get("payload", {}).get("matricula", "") if g else ""

    def get_historico_completo(self) -> list[dict[str, Any]]:
        timeline = []
        for block in self.chain:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp))
            signed = block.has_signature()
            timeline.append({
                "indice": block.index, "tipo": block.data.get("evento_tipo", ""),
                "data_registro": ts, "hash": block.hash[:16], "assinado": signed,
                "emissor": block.signature.get("signer_label", "") if signed else "",
                "dados": block.data.get("payload", {}),
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
            cur, prev = self.chain[i], self.chain[i - 1]
            if cur.previous_hash != prev.hash:
                return False, f"Bloco #{cur.index}: previous_hash não confere."
            if cur.hash != cur.compute_hash():
                return False, f"Bloco #{cur.index}: hash próprio não confere."
            if not cur.is_valid():
                return False, f"Bloco #{cur.index}: proof-of-work inválido."
            if require_signatures:
                if not cur.has_signature():
                    return False, f"Bloco #{cur.index}: sem assinatura ECDSA."
                sig = BlockSignature.from_dict(cur.signature)
                ok, msg = self._verify_signature(cur, sig)
                if not ok:
                    return False, f"Bloco #{cur.index}: assinatura inválida — {msg}"
        sc = sum(1 for b in self.chain if b.has_signature())
        sfx = f" | {sc}/{len(self.chain)} assinado(s)" if sc else ""
        return True, f"Cadeia válida — {len(self.chain)} bloco(s).{sfx}"

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
    def load_from_file(cls, filepath: str) -> "AircraftChain":
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
        m = self.get_matricula()
        si = f", signer={self._signer.keypair.label}" if self._signer else ""
        return f"AircraftChain(matricula={m}, blocks={len(self.chain)}, difficulty={self.difficulty}{si})"
