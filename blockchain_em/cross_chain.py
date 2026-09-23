"""
blockchain_em/cross_chain.py
Gerencia referências cruzadas entre blockchain_em (embarcações)
e outras blockchains (PF, IM, MO, CO).
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class VesselCrossReference:
    """Referência cruzada envolvendo embarcações."""
    entidade_origem_tipo: str
    entidade_origem_id: str
    entidade_destino_tipo: str
    entidade_destino_id: str
    tipo_vinculo: str
    hash_cadeia_origem: str = ""
    hash_cadeia_destino: str = ""
    bloco_origem: Optional[int] = None
    bloco_destino: Optional[int] = None
    timestamp: float = 0.0
    dados: dict = field(default_factory=dict)
    ativo: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CrossChainEM:
    """Gerencia referências entre blockchain_em e outras blockchains."""

    def __init__(self) -> None:
        self._pf_chains: dict[str, Any] = {}
        self._im_chains: dict[str, Any] = {}
        self._mo_chains: dict[str, Any] = {}
        self._co_chains: dict[str, Any] = {}
        self._em_chains: dict[str, Any] = {}
        self._references: list[VesselCrossReference] = []

    def register_pf(self, cpf: str, chain: Any) -> None:
        self._pf_chains[cpf.replace(".", "").replace("-", "")] = chain

    def register_im(self, matricula: str, chain: Any) -> None:
        self._im_chains[matricula.strip()] = chain

    def register_mo(self, placa: str, chain: Any) -> None:
        self._mo_chains[placa.replace("-", "").replace(" ", "").upper()] = chain

    def register_co(self, cnpj: str, chain: Any) -> None:
        import re
        self._co_chains[re.sub(r"\D", "", cnpj)] = chain

    def register_em(self, registro: str, chain: Any) -> None:
        self._em_chains[registro.strip()] = chain

    def unregister_em(self, registro: str) -> bool:
        if registro in self._em_chains:
            del self._em_chains[registro]
            return True
        return False

    def create_reference(
        self,
        origem_tipo: str, origem_id: str,
        destino_tipo: str, destino_id: str,
        tipo_vinculo: str,
        bloco_origem: Optional[int] = None,
        bloco_destino: Optional[int] = None,
        dados: Optional[dict] = None,
    ) -> VesselCrossReference:
        import re
        # Normaliza IDs
        if origem_tipo == "PF":
            origem_id = origem_id.replace(".", "").replace("-", "")
        elif origem_tipo == "MO":
            origem_id = origem_id.replace("-", "").replace(" ", "").upper()
        elif origem_tipo in ("CO",):
            origem_id = re.sub(r"\D", "", origem_id)

        if destino_tipo == "PF":
            destino_id = destino_id.replace(".", "").replace("-", "")
        elif destino_tipo == "MO":
            destino_id = destino_id.replace("-", "").replace(" ", "").upper()
        elif destino_tipo in ("CO",):
            destino_id = re.sub(r"\D", "", destino_id)

        hash_origem = self._get_chain_hash(origem_tipo, origem_id)
        hash_destino = self._get_chain_hash(destino_tipo, destino_id)

        ref = VesselCrossReference(
            entidade_origem_tipo=origem_tipo,
            entidade_origem_id=origem_id,
            entidade_destino_tipo=destino_tipo,
            entidade_destino_id=destino_id,
            tipo_vinculo=tipo_vinculo,
            hash_cadeia_origem=hash_origem,
            hash_cadeia_destino=hash_destino,
            bloco_origem=bloco_origem,
            bloco_destino=bloco_destino,
            timestamp=time.time(),
            dados=dados or {},
        )
        self._references.append(ref)
        return ref

    def deactivate_reference(
        self, origem_tipo: str, origem_id: str,
        destino_tipo: str, destino_id: str,
        tipo_vinculo: str = "",
    ) -> int:
        count = 0
        for ref in self._references:
            if (ref.entidade_origem_tipo == origem_tipo and
                    ref.entidade_origem_id == origem_id and
                    ref.entidade_destino_tipo == destino_tipo and
                    ref.entidade_destino_id == destino_id):
                if not tipo_vinculo or ref.tipo_vinculo == tipo_vinculo:
                    if ref.ativo:
                        ref.ativo = False
                        count += 1
        return count

    def get_embarcacoes_da_pessoa(self, cpf: str) -> list[dict[str, Any]]:
        cpf_clean = cpf.replace(".", "").replace("-", "")
        result = []
        for ref in self._references:
            if (ref.entidade_origem_tipo == "PF" and
                    ref.entidade_origem_id == cpf_clean and
                    ref.entidade_destino_tipo == "EM" and
                    ref.ativo):
                info = {"registro_nr": ref.entidade_destino_id, "vinculo": ref.tipo_vinculo}
                if ref.entidade_destino_id in self._em_chains:
                    estado = self._em_chains[ref.entidade_destino_id].get_estado_atual()
                    info["nome"] = estado.get("nome_embarcacao", "")
                    info["tipo"] = estado.get("tipo_embarcacao", "")
                result.append(info)
        return result

    def get_vinculos_ativos(self, **kwargs) -> list[dict]:
        result = []
        for ref in self._references:
            if not ref.ativo:
                continue
            match = True
            for k, v in kwargs.items():
                attr = f"entidade_{k}" if "tipo" in k or "id" in k else k
                if hasattr(ref, attr) and getattr(ref, attr) != v:
                    match = False
                    break
            if match:
                result.append(ref.to_dict())
        return result

    def _get_chain_hash(self, entity_type: str, entity_id: str) -> str:
        chains = {
            "PF": self._pf_chains, "IM": self._im_chains,
            "MO": self._mo_chains, "CO": self._co_chains,
            "EM": self._em_chains,
        }
        chain_dict = chains.get(entity_type, {})
        if entity_id in chain_dict and chain_dict[entity_id].chain:
            return chain_dict[entity_id].chain[-1].hash
        return ""

    def stats(self) -> dict[str, Any]:
        ativos = sum(1 for r in self._references if r.ativo)
        return {
            "total_cadeias_pf": len(self._pf_chains),
            "total_cadeias_im": len(self._im_chains),
            "total_cadeias_mo": len(self._mo_chains),
            "total_cadeias_co": len(self._co_chains),
            "total_cadeias_em": len(self._em_chains),
            "total_referencias": len(self._references),
            "referencias_ativas": ativos,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "referencias": [r.to_dict() for r in self._references],
            "stats": self.stats(),
        }

    def save_to_file(self, filepath: str) -> None:
        import json, os
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load_from_file(cls, filepath: str) -> "CrossChainEM":
        import json
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        manager = cls()
        for ref_data in data.get("referencias", []):
            manager._references.append(VesselCrossReference(**ref_data))
        return manager

    def __repr__(self) -> str:
        return (
            f"CrossChainEM(pf={len(self._pf_chains)}, im={len(self._im_chains)}, "
            f"mo={len(self._mo_chains)}, co={len(self._co_chains)}, "
            f"em={len(self._em_chains)}, refs={len(self._references)})"
        )
