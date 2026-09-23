"""
blockchain_co/cross_chain.py
Gerencia referências cruzadas entre blockchain_co (empresas)
e outras blockchains (PF, IM, MO).
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class CompanyCrossReference:
    """
    Referência cruzada envolvendo empresas.

    Pode conectar:
    - Pessoa ↔ Empresa (sócio, responsável, etc.)
    - Empresa ↔ Imóvel (sede, filial)
    - Empresa ↔ Veículo (frota)
    - Empresa ↔ Empresa (consórcio, coligação)

    Attributes:
        entidade_origem_tipo:   Tipo da entidade de origem (PF, IM, MO, CO).
        entidade_origem_id:     ID da entidade de origem.
        entidade_destino_tipo:  Tipo da entidade de destino.
        entidade_destino_id:    ID da entidade de destino.
        tipo_vinculo:           Tipo de vínculo.
        hash_cadeia_origem:     Hash da cadeia de origem.
        hash_cadeia_destino:    Hash da cadeia de destino.
        bloco_origem:           Índice do bloco na cadeia de origem.
        bloco_destino:          Índice do bloco na cadeia de destino.
        timestamp:              Quando o vínculo foi criado.
        dados:                  Dados extras do vínculo.
        ativo:                  Se o vínculo está vigente.
    """
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


class CrossChainCO:
    """
    Gerencia referências entre blockchain_co e outras blockchains.

    Funcionalidades:
    1. Valida que entidades referenciadas existem
    2. Registra vínculos bidirecionais
    3. Permite consultas cruzadas
    4. Suporta assinatura conjunta
    """

    def __init__(self) -> None:
        self._pf_chains: dict[str, Any] = {}
        self._im_chains: dict[str, Any] = {}
        self._mo_chains: dict[str, Any] = {}
        self._co_chains: dict[str, Any] = {}
        self._references: list[CompanyCrossReference] = []

    # ── Registro de cadeias ───────────────────────────────────────────

    def register_pf(self, cpf: str, chain: Any) -> None:
        cpf_clean = cpf.replace(".", "").replace("-", "")
        self._pf_chains[cpf_clean] = chain

    def register_im(self, matricula: str, chain: Any) -> None:
        self._im_chains[matricula.strip()] = chain

    def register_mo(self, placa: str, chain: Any) -> None:
        placa_clean = placa.replace("-", "").replace(" ", "").upper()
        self._mo_chains[placa_clean] = chain

    def register_co(self, cnpj: str, chain: Any) -> None:
        cnpj_clean = re.sub(r"\D", "", cnpj) if 're' in dir() else cnpj.replace(".", "").replace("/", "").replace("-", "")
        self._co_chains[cnpj_clean] = chain

    def unregister_pf(self, cpf: str) -> bool:
        cpf_clean = cpf.replace(".", "").replace("-", "")
        if cpf_clean in self._pf_chains:
            del self._pf_chains[cpf_clean]
            return True
        return False

    def unregister_im(self, matricula: str) -> bool:
        if matricula in self._im_chains:
            del self._im_chains[matricula]
            return True
        return False

    def unregister_mo(self, placa: str) -> bool:
        placa_clean = placa.replace("-", "").replace(" ", "").upper()
        if placa_clean in self._mo_chains:
            del self._mo_chains[placa_clean]
            return True
        return False

    def unregister_co(self, cnpj: str) -> bool:
        import re
        cnpj_clean = re.sub(r"\D", "", cnpj)
        if cnpj_clean in self._co_chains:
            del self._co_chains[cnpj_clean]
            return True
        return False

    # ── Validação de referências ──────────────────────────────────────

    def validate_pf_exists(self, cpf: str) -> tuple[bool, str]:
        cpf_clean = cpf.replace(".", "").replace("-", "")
        if cpf_clean in self._pf_chains:
            chain = self._pf_chains[cpf_clean]
            birth = chain.get_birth_block()
            nome = birth.data.get("payload", {}).get("nome_completo", "") if birth else ""
            return True, f"PF encontrada: {nome} (CPF: {cpf_clean})"
        return False, f"CPF {cpf_clean} não registrado no sistema."

    def validate_co_exists(self, cnpj: str) -> tuple[bool, str]:
        import re
        cnpj_clean = re.sub(r"\D", "", cnpj)
        if cnpj_clean in self._co_chains:
            chain = self._co_chains[cnpj_clean]
            estado = chain.get_estado_atual()
            return True, f"Empresa encontrada: {estado.get('razao_social', '')} (CNPJ: {cnpj_clean})"
        return False, f"CNPJ {cnpj_clean} não registrado no sistema."

    def validate_im_exists(self, matricula: str) -> tuple[bool, str]:
        if matricula in self._im_chains:
            chain = self._im_chains[matricula]
            estado = chain.get_estado_atual()
            return True, f"Imóvel encontrado: {estado.get('endereco', {}).get('logradouro', '')} (Mat: {matricula})"
        return False, f"Matrícula {matricula} não registrada no sistema."

    def validate_mo_exists(self, placa: str) -> tuple[bool, str]:
        placa_clean = placa.replace("-", "").replace(" ", "").upper()
        if placa_clean in self._mo_chains:
            chain = self._mo_chains[placa_clean]
            estado = chain.get_estado_atual()
            return True, f"Veículo encontrado: {estado.get('marca', '')} {estado.get('modelo', '')} (Placa: {placa_clean})"
        return False, f"Placa {placa_clean} não registrada no sistema."

    # ── Criação de referências ────────────────────────────────────────

    def create_reference(
        self,
        origem_tipo: str,
        origem_id: str,
        destino_tipo: str,
        destino_id: str,
        tipo_vinculo: str,
        bloco_origem: Optional[int] = None,
        bloco_destino: Optional[int] = None,
        dados: Optional[dict] = None,
    ) -> CompanyCrossReference:
        """Cria uma referência cruzada entre duas entidades."""
        # Normaliza IDs
        if origem_tipo == "PF":
            origem_id = origem_id.replace(".", "").replace("-", "")
        elif origem_tipo == "MO":
            origem_id = origem_id.replace("-", "").replace(" ", "").upper()
        elif origem_tipo == "CO":
            import re
            origem_id = re.sub(r"\D", "", origem_id)

        if destino_tipo == "PF":
            destino_id = destino_id.replace(".", "").replace("-", "")
        elif destino_tipo == "MO":
            destino_id = destino_id.replace("-", "").replace(" ", "").upper()
        elif destino_tipo == "CO":
            import re
            destino_id = re.sub(r"\D", "", destino_id)

        hash_origem = self._get_chain_hash(origem_tipo, origem_id)
        hash_destino = self._get_chain_hash(destino_tipo, destino_id)

        ref = CompanyCrossReference(
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
        self,
        origem_tipo: str,
        origem_id: str,
        destino_tipo: str,
        destino_id: str,
        tipo_vinculo: str = "",
    ) -> int:
        """Desativa referências entre duas entidades."""
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

    # ── Consultas ─────────────────────────────────────────────────────

    def get_socios_da_empresa(self, cnpj: str) -> list[dict[str, Any]]:
        """Lista todos os sócios vinculados a uma empresa."""
        import re
        cnpj_clean = re.sub(r"\D", "", cnpj)
        result = []
        for ref in self._references:
            if (ref.entidade_origem_tipo == "PF" and
                    ref.entidade_destino_tipo == "CO" and
                    ref.entidade_destino_id == cnpj_clean and
                    ref.ativo):
                socio_info = {
                    "cpf": ref.entidade_origem_id,
                    "vinculo": ref.tipo_vinculo,
                }
                if ref.entidade_origem_id in self._pf_chains:
                    chain = self._pf_chains[ref.entidade_origem_id]
                    birth = chain.get_birth_block()
                    if birth:
                        payload = birth.data.get("payload", {})
                        socio_info["nome"] = payload.get("nome_completo", "")
                result.append(socio_info)
        return result

    def get_empresas_da_pessoa(self, cpf: str) -> list[dict[str, Any]]:
        """Lista todas as empresas vinculadas a uma pessoa."""
        cpf_clean = cpf.replace(".", "").replace("-", "")
        result = []
        for ref in self._references:
            if (ref.entidade_origem_tipo == "PF" and
                    ref.entidade_origem_id == cpf_clean and
                    ref.entidade_destino_tipo == "CO" and
                    ref.ativo):
                empresa_info = {
                    "cnpj": ref.entidade_destino_id,
                    "vinculo": ref.tipo_vinculo,
                }
                if ref.entidade_destino_id in self._co_chains:
                    chain = self._co_chains[ref.entidade_destino_id]
                    estado = chain.get_estado_atual()
                    empresa_info["razao_social"] = estado.get("razao_social", "")
                    empresa_info["situacao"] = estado.get("situacao_cadastral", "")
                result.append(empresa_info)
        return result

    def get_vinculos_ativos(
        self,
        origem_tipo: str = "",
        origem_id: str = "",
        destino_tipo: str = "",
        destino_id: str = "",
    ) -> list[dict]:
        """Retorna todos os vínculos ativos, filtrando opcionalmente."""
        result = []
        for ref in self._references:
            if not ref.ativo:
                continue
            if origem_tipo and ref.entidade_origem_tipo != origem_tipo:
                continue
            if origem_id and ref.entidade_origem_id != origem_id:
                continue
            if destino_tipo and ref.entidade_destino_tipo != destino_tipo:
                continue
            if destino_id and ref.entidade_destino_id != destino_id:
                continue
            result.append(ref.to_dict())
        return result

    def _get_chain_hash(self, entity_type: str, entity_id: str) -> str:
        """Obtém o hash atual da cadeia de uma entidade."""
        chains = {
            "PF": self._pf_chains,
            "IM": self._im_chains,
            "MO": self._mo_chains,
            "CO": self._co_chains,
        }
        chain_dict = chains.get(entity_type, {})
        if entity_id in chain_dict:
            chain = chain_dict[entity_id]
            if chain.chain:
                return chain.chain[-1].hash
        return ""

    # ── Estatísticas ─────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Retorna estatísticas do sistema cross-chain."""
        ativos = sum(1 for r in self._references if r.ativo)
        return {
            "total_cadeias_pf": len(self._pf_chains),
            "total_cadeias_im": len(self._im_chains),
            "total_cadeias_mo": len(self._mo_chains),
            "total_cadeias_co": len(self._co_chains),
            "total_referencias": len(self._references),
            "referencias_ativas": ativos,
            "referencias_inativas": len(self._references) - ativos,
        }

    # ── Serialização ─────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serializa o estado do cross-chain manager."""
        return {
            "referencias": [r.to_dict() for r in self._references],
            "stats": self.stats(),
        }

    def save_to_file(self, filepath: str) -> None:
        """Salva as referências em JSON."""
        import json
        import os
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load_from_file(cls, filepath: str) -> "CrossChainCO":
        """Carrega referências de JSON."""
        import json
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        manager = cls()
        for ref_data in data.get("referencias", []):
            ref = CompanyCrossReference(**ref_data)
            manager._references.append(ref)
        return manager

    def __repr__(self) -> str:
        return (
            f"CrossChainCO("
            f"pf={len(self._pf_chains)}, "
            f"im={len(self._im_chains)}, "
            f"mo={len(self._mo_chains)}, "
            f"co={len(self._co_chains)}, "
            f"refs={len(self._references)})"
        )
