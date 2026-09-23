"""
blockchain_mo/cross_chain.py
Gerencia referências cruzadas entre blockchain_pf (pessoas),
blockchain_im (imóveis) e blockchain_mo (veículos).

Permite:
- Vincular pessoas a veículos (propriedade, garantia, etc.)
- Vincular imóveis a veículos (garagem, estacionamento)
- Vincular veículos a veículos (troca de peças entre veículos)
- Validar referências cruzadas
- Consultas cruzadas
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class VehicleCrossReference:
    """
    Referência cruzada envolvendo veículos.

    Pode conectar:
    - Pessoa ↔ Veículo (propriedade, garantia, etc.)
    - Imóvel ↔ Veículo (garagem, estacionamento)
    - Veículo ↔ Veículo (troca de peças)

    Attributes:
        entidade_origem_tipo:   Tipo da entidade de origem (PF, IM, MO).
        entidade_origem_id:     ID da entidade de origem (CPF, matrícula, placa).
        entidade_destino_tipo:  Tipo da entidade de destino (PF, IM, MO).
        entidade_destino_id:    ID da entidade de destino.
        tipo_vinculo:           Tipo de vínculo (PROPRIETARIO, GARANTIDOR, etc).
        hash_cadeia_origem:     Hash da cadeia de origem.
        hash_cadeia_destino:    Hash da cadeia de destino.
        bloco_origem:           Índice do bloco na cadeia de origem.
        bloco_destino:          Índice do bloco na cadeia de destino.
        timestamp:              Quando o vínculo foi criado.
        dados:                  Dados extras do vínculo.
        ativo:                  Se o vínculo está vigente.
    """
    entidade_origem_tipo: str   # PF, IM, MO
    entidade_origem_id: str     # CPF, matrícula, placa
    entidade_destino_tipo: str  # PF, IM, MO
    entidade_destino_id: str    # CPF, matrícula, placa
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


class CrossChainMO:
    """
    Gerencia referências entre blockchain_pf, blockchain_im e blockchain_mo.

    Funcionalidades:
    1. Valida que entidades referenciadas existem
    2. Registra vínculos bidirecionais
    3. Permite consultas cruzadas
    4. Suporta assinatura conjunta
    """

    def __init__(self) -> None:
        self._pf_chains: dict[str, Any] = {}   # cpf → Blockchain (PF)
        self._im_chains: dict[str, Any] = {}   # matrícula → PropertyChain (IM)
        self._mo_chains: dict[str, Any] = {}   # placa → VehicleChain (MO)
        self._references: list[VehicleCrossReference] = []

    # ── Registro de cadeias ───────────────────────────────────────────

    def register_pf(self, cpf: str, chain: Any) -> None:
        """Registra uma cadeia de PF para referência."""
        cpf_clean = cpf.replace(".", "").replace("-", "")
        self._pf_chains[cpf_clean] = chain

    def register_im(self, matricula: str, chain: Any) -> None:
        """Registra uma cadeia de IM para referência."""
        self._im_chains[matricula.strip()] = chain

    def register_mo(self, placa: str, chain: Any) -> None:
        """Registra uma cadeia de MO para referência."""
        placa_clean = placa.replace("-", "").replace(" ", "").upper()
        self._mo_chains[placa_clean] = chain

    def unregister_pf(self, cpf: str) -> bool:
        """Remove uma cadeia de PF do registro."""
        cpf_clean = cpf.replace(".", "").replace("-", "")
        if cpf_clean in self._pf_chains:
            del self._pf_chains[cpf_clean]
            return True
        return False

    def unregister_im(self, matricula: str) -> bool:
        """Remove uma cadeia de IM do registro."""
        if matricula in self._im_chains:
            del self._im_chains[matricula]
            return True
        return False

    def unregister_mo(self, placa: str) -> bool:
        """Remove uma cadeia de MO do registro."""
        placa_clean = placa.replace("-", "").replace(" ", "").upper()
        if placa_clean in self._mo_chains:
            del self._mo_chains[placa_clean]
            return True
        return False

    # ── Validação de referências ──────────────────────────────────────

    def validate_pf_exists(self, cpf: str) -> tuple[bool, str]:
        """Valida se existe uma cadeia de PF para o CPF informado."""
        cpf_clean = cpf.replace(".", "").replace("-", "")
        if cpf_clean in self._pf_chains:
            chain = self._pf_chains[cpf_clean]
            birth = chain.get_birth_block()
            nome = birth.data.get("payload", {}).get("nome_completo", "") if birth else ""
            return True, f"PF encontrada: {nome} (CPF: {cpf_clean})"
        return False, f"CPF {cpf_clean} não registrado no sistema."

    def validate_im_exists(self, matricula: str) -> tuple[bool, str]:
        """Valida se existe uma cadeia de IM para a matrícula informada."""
        if matricula in self._im_chains:
            chain = self._im_chains[matricula]
            estado = chain.get_estado_atual()
            return True, f"Imóvel encontrado: {estado.get('endereco', {}).get('logradouro', '')} (Mat: {matricula})"
        return False, f"Matrícula {matricula} não registrada no sistema."

    def validate_mo_exists(self, placa: str) -> tuple[bool, str]:
        """Valida se existe uma cadeia de MO para a placa informada."""
        placa_clean = placa.replace("-", "").replace(" ", "").upper()
        if placa_clean in self._mo_chains:
            chain = self._mo_chains[placa_clean]
            estado = chain.get_estado_atual()
            return True, f"Veículo encontrado: {estado.get('marca', '')} {estado.get('modelo', '')} (Placa: {placa_clean})"
        return False, f"Placa {placa_clean} não registrada no sistema."

    def validate_cross_reference(
        self, origem_tipo: str, origem_id: str,
        destino_tipo: str, destino_id: str,
    ) -> tuple[bool, str]:
        """
        Valida se a referência cruzada é consistente.
        Verifica se ambas as entidades existem.
        """
        validators = {
            "PF": self.validate_pf_exists,
            "IM": self.validate_im_exists,
            "MO": self.validate_mo_exists,
        }

        val_origem = validators.get(origem_tipo)
        if not val_origem:
            return False, f"Tipo de entidade inválido: {origem_tipo}"

        val_destino = validators.get(destino_tipo)
        if not val_destino:
            return False, f"Tipo de entidade inválido: {destino_tipo}"

        ok_origem, msg_origem = val_origem(origem_id)
        if not ok_origem:
            return False, f"Referência origem: {msg_origem}"

        ok_destino, msg_destino = val_destino(destino_id)
        if not ok_destino:
            return False, f"Referência destino: {msg_destino}"

        return True, f"Referência válida — Origem: {msg_origem} | Destino: {msg_destino}"

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
    ) -> VehicleCrossReference:
        """
        Cria uma referência cruzada entre duas entidades.

        Args:
            origem_tipo:        Tipo da entidade de origem (PF, IM, MO).
            origem_id:          ID da entidade de origem (CPF, matrícula, placa).
            destino_tipo:       Tipo da entidade de destino (PF, IM, MO).
            destino_id:         ID da entidade de destino.
            tipo_vinculo:       Tipo de vínculo (PROPRIETARIO, GARANTIDOR, etc).
            bloco_origem:       Índice do bloco na cadeia de origem.
            bloco_destino:      Índice do bloco na cadeia de destino.
            dados:              Dados extras.

        Returns:
            A referência criada.
        """
        # Normaliza IDs
        if origem_tipo == "PF":
            origem_id = origem_id.replace(".", "").replace("-", "")
        elif origem_tipo == "MO":
            origem_id = origem_id.replace("-", "").replace(" ", "").upper()

        if destino_tipo == "PF":
            destino_id = destino_id.replace(".", "").replace("-", "")
        elif destino_tipo == "MO":
            destino_id = destino_id.replace("-", "").replace(" ", "").upper()

        # Obtém hashes das cadeias
        hash_origem = self._get_chain_hash(origem_tipo, origem_id)
        hash_destino = self._get_chain_hash(destino_tipo, destino_id)

        ref = VehicleCrossReference(
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
        """
        Desativa referências entre duas entidades.

        Returns:
            Número de referências desativadas.
        """
        if origem_tipo == "PF":
            origem_id = origem_id.replace(".", "").replace("-", "")
        elif origem_tipo == "MO":
            origem_id = origem_id.replace("-", "").replace(" ", "").upper()

        if destino_tipo == "PF":
            destino_id = destino_id.replace(".", "").replace("-", "")
        elif destino_tipo == "MO":
            destino_id = destino_id.replace("-", "").replace(" ", "").upper()

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

    def get_veiculos_da_pessoa(self, cpf: str) -> list[dict[str, Any]]:
        """Lista todos os veículos vinculados a uma pessoa."""
        cpf_clean = cpf.replace(".", "").replace("-", "")
        result = []
        for ref in self._references:
            if (ref.entidade_origem_tipo == "PF" and
                    ref.entidade_origem_id == cpf_clean and
                    ref.entidade_destino_tipo == "MO" and
                    ref.ativo):
                veiculo_info = {
                    "placa": ref.entidade_destino_id,
                    "vinculo": ref.tipo_vinculo,
                }
                # Enriquece com dados do veículo
                if ref.entidade_destino_id in self._mo_chains:
                    chain = self._mo_chains[ref.entidade_destino_id]
                    estado = chain.get_estado_atual()
                    veiculo_info["marca"] = estado.get("marca", "")
                    veiculo_info["modelo"] = estado.get("modelo", "")
                    veiculo_info["cor"] = estado.get("cor", "")
                    veiculo_info["situacao"] = estado.get("situacao", "")
                result.append(veiculo_info)
            elif (ref.entidade_destino_tipo == "PF" and
                    ref.entidade_destino_id == cpf_clean and
                    ref.entidade_origem_tipo == "MO" and
                    ref.ativo):
                veiculo_info = {
                    "placa": ref.entidade_origem_id,
                    "vinculo": ref.tipo_vinculo,
                }
                if ref.entidade_origem_id in self._mo_chains:
                    chain = self._mo_chains[ref.entidade_origem_id]
                    estado = chain.get_estado_atual()
                    veiculo_info["marca"] = estado.get("marca", "")
                    veiculo_info["modelo"] = estado.get("modelo", "")
                    veiculo_info["cor"] = estado.get("cor", "")
                    veiculo_info["situacao"] = estado.get("situacao", "")
                result.append(veiculo_info)
        return result

    def get_pessoas_do_veiculo(self, placa: str) -> list[dict[str, Any]]:
        """Lista todas as pessoas vinculadas a um veículo."""
        placa_clean = placa.replace("-", "").replace(" ", "").upper()
        result = []
        for ref in self._references:
            if not ref.ativo:
                continue
            if (ref.entidade_destino_tipo == "MO" and
                    ref.entidade_destino_id == placa_clean and
                    ref.entidade_origem_tipo == "PF"):
                pessoa_info = {
                    "cpf": ref.entidade_origem_id,
                    "vinculo": ref.tipo_vinculo,
                }
                if ref.entidade_origem_id in self._pf_chains:
                    chain = self._pf_chains[ref.entidade_origem_id]
                    birth = chain.get_birth_block()
                    if birth:
                        payload = birth.data.get("payload", {})
                        pessoa_info["nome"] = payload.get("nome_completo", "")
                result.append(pessoa_info)
            elif (ref.entidade_origem_tipo == "MO" and
                    ref.entidade_origem_id == placa_clean and
                    ref.entidade_destino_tipo == "PF"):
                pessoa_info = {
                    "cpf": ref.entidade_destino_id,
                    "vinculo": ref.tipo_vinculo,
                }
                if ref.entidade_destino_id in self._pf_chains:
                    chain = self._pf_chains[ref.entidade_destino_id]
                    birth = chain.get_birth_block()
                    if birth:
                        payload = birth.data.get("payload", {})
                        pessoa_info["nome"] = payload.get("nome_completo", "")
                result.append(pessoa_info)
        return result

    def get_veiculos_no_imovel(self, matricula: str) -> list[dict[str, Any]]:
        """Lista todos os veículos vinculados a um imóvel (garagem, estacionamento)."""
        result = []
        for ref in self._references:
            if not ref.ativo:
                continue
            if (ref.entidade_origem_tipo == "IM" and
                    ref.entidade_origem_id == matricula and
                    ref.entidade_destino_tipo == "MO"):
                veiculo_info = {
                    "placa": ref.entidade_destino_id,
                    "vinculo": ref.tipo_vinculo,
                }
                if ref.entidade_destino_id in self._mo_chains:
                    chain = self._mo_chains[ref.entidade_destino_id]
                    estado = chain.get_estado_atual()
                    veiculo_info["marca"] = estado.get("marca", "")
                    veiculo_info["modelo"] = estado.get("modelo", "")
                    veiculo_info["cor"] = estado.get("cor", "")
                result.append(veiculo_info)
            elif (ref.entidade_destino_tipo == "IM" and
                    ref.entidade_destino_id == matricula and
                    ref.entidade_origem_tipo == "MO"):
                veiculo_info = {
                    "placa": ref.entidade_origem_id,
                    "vinculo": ref.tipo_vinculo,
                }
                if ref.entidade_origem_id in self._mo_chains:
                    chain = self._mo_chains[ref.entidade_origem_id]
                    estado = chain.get_estado_atual()
                    veiculo_info["marca"] = estado.get("marca", "")
                    veiculo_info["modelo"] = estado.get("modelo", "")
                    veiculo_info["cor"] = estado.get("cor", "")
                result.append(veiculo_info)
        return result

    def get_pecas_de_veiculo(self, placa: str) -> list[dict[str, Any]]:
        """Lista veículos que doaram peças para este veículo (MO↔MO)."""
        placa_clean = placa.replace("-", "").replace(" ", "").upper()
        result = []
        for ref in self._references:
            if not ref.ativo:
                continue
            if (ref.entidade_origem_tipo == "MO" and
                    ref.entidade_destino_tipo == "MO" and
                    ref.entidade_destino_id == placa_clean and
                    ref.tipo_vinculo == "PECA_ORIGEM"):
                peca_info = {
                    "veiculo_origem": ref.entidade_origem_id,
                    "dados": ref.dados,
                }
                if ref.entidade_origem_id in self._mo_chains:
                    chain = self._mo_chains[ref.entidade_origem_id]
                    estado = chain.get_estado_atual()
                    peca_info["marca_origem"] = estado.get("marca", "")
                    peca_info["modelo_origem"] = estado.get("modelo", "")
                result.append(peca_info)
        return result

    def get_vinculos_ativos(
        self,
        origem_tipo: str = "",
        origem_id: str = "",
        destino_tipo: str = "",
        destino_id: str = "",
        tipo_vinculo: str = "",
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
            if tipo_vinculo and ref.tipo_vinculo != tipo_vinculo:
                continue
            result.append(ref.to_dict())
        return result

    # ── Atualização de hashes ────────────────────────────────────────

    def _get_chain_hash(self, entity_type: str, entity_id: str) -> str:
        """Obtém o hash atual da cadeia de uma entidade."""
        if entity_type == "PF" and entity_id in self._pf_chains:
            chain = self._pf_chains[entity_id]
            if chain.chain:
                return chain.chain[-1].hash
        elif entity_type == "IM" and entity_id in self._im_chains:
            chain = self._im_chains[entity_id]
            if chain.chain:
                return chain.chain[-1].hash
        elif entity_type == "MO" and entity_id in self._mo_chains:
            chain = self._mo_chains[entity_id]
            if chain.chain:
                return chain.chain[-1].hash
        return ""

    # ── Estatísticas ─────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Retorna estatísticas do sistema cross-chain."""
        ativos = sum(1 for r in self._references if r.ativo)
        por_tipo_vinculo: dict[str, int] = {}
        for r in self._references:
            if r.ativo:
                por_tipo_vinculo[r.tipo_vinculo] = por_tipo_vinculo.get(r.tipo_vinculo, 0) + 1

        return {
            "total_cadeias_pf": len(self._pf_chains),
            "total_cadeias_im": len(self._im_chains),
            "total_cadeias_mo": len(self._mo_chains),
            "total_referencias": len(self._references),
            "referencias_ativas": ativos,
            "referencias_inativas": len(self._references) - ativos,
            "por_tipo_vinculo": por_tipo_vinculo,
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
    def load_from_file(cls, filepath: str) -> "CrossChainMO":
        """Carrega referências de JSON."""
        import json
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        manager = cls()
        for ref_data in data.get("referencias", []):
            ref = VehicleCrossReference(**ref_data)
            manager._references.append(ref)
        return manager

    # ── Representação ─────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"CrossChainMO("
            f"pf={len(self._pf_chains)}, "
            f"im={len(self._im_chains)}, "
            f"mo={len(self._mo_chains)}, "
            f"refs={len(self._references)})"
        )
