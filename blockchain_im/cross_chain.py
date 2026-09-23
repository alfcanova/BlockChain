"""
blockchain_im/cross_chain.py
Gerencia referências cruzadas entre blockchain_pf (pessoas) e blockchain_im (imóveis).

Permite:
- Vincular pessoas a imóveis (propriedade, garantia)
- Validar referências cruzadas
- Consultar imóveis de uma pessoa e pessoas de um imóvel
- Assinatura conjunta (pessoa + cartório)
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class CrossReference:
    """
    Referência cruzada entre uma pessoa e um imóvel.

    Attributes:
        cpf:                CPF da pessoa.
        matricula:          Matrícula do imóvel.
        tipo_vinculo:       Tipo de vínculo (PROPRIETARIO, GARANTIDOR, COMPRADOR, etc).
        hash_cadeia_pessoa: Hash da cadeia de blocos da pessoa.
        hash_cadeia_imovel: Hash da cadeia de blocos do imóvel.
        bloco_pessoa:       Índice do bloco na cadeia da pessoa.
        bloco_imovel:       Índice do bloco na cadeia do imóvel.
        timestamp:          Quando o vínculo foi criado.
        dados:              Dados extras do vínculo.
        ativo:              Se o vínculo está vigente.
    """
    cpf: str
    matricula: str
    tipo_vinculo: str
    hash_cadeia_pessoa: str = ""
    hash_cadeia_imovel: str = ""
    bloco_pessoa: Optional[int] = None
    bloco_imovel: Optional[int] = None
    timestamp: float = 0.0
    dados: dict = field(default_factory=dict)
    ativo: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CrossChainManager:
    """
    Gerencia referências entre blockchain_pf e blockchain_im.

    Funcionalidades:
    1. Valida que CPFs referenciados existem no blockchain_pf
    2. Registra vínculos bidirecionais
    3. Permite consultas cruzadas
    4. Assinatura conjunta (pessoa + cartório)
    """

    def __init__(self) -> None:
        self._pf_chains: dict[str, Any] = {}   # cpf → Blockchain (PF)
        self._im_chains: dict[str, Any] = {}   # matrícula → PropertyChain (IM)
        self._references: list[CrossReference] = []

    # ── Registro de cadeias ───────────────────────────────────────────

    def register_pf(self, cpf: str, chain: Any) -> None:
        """Registra uma cadeia de PF para referência."""
        cpf_clean = cpf.replace(".", "").replace("-", "")
        self._pf_chains[cpf_clean] = chain

    def register_im(self, matricula: str, chain: Any) -> None:
        """Registra uma cadeia de IM para referência."""
        self._im_chains[matricula.strip()] = chain

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

    def validate_cross_reference(self, cpf: str, matricula: str) -> tuple[bool, str]:
        """
        Valida se a referência cruzada é consistente.
        Verifica se tanto a PF quanto o IM existem.
        """
        ok_pf, msg_pf = self.validate_pf_exists(cpf)
        if not ok_pf:
            return False, f"Referência PF: {msg_pf}"

        ok_im, msg_im = self.validate_im_exists(matricula)
        if not ok_im:
            return False, f"Referência IM: {msg_im}"

        return True, f"Referência válida — PF: {msg_pf} | IM: {msg_im}"

    # ── Criação de referências ────────────────────────────────────────

    def create_reference(
        self,
        cpf: str,
        matricula: str,
        tipo_vinculo: str,
        bloco_pessoa: Optional[int] = None,
        bloco_imovel: Optional[int] = None,
        dados: Optional[dict] = None,
    ) -> CrossReference:
        """
        Cria uma referência cruzada entre pessoa e imóvel.

        Args:
            cpf:                CPF da pessoa.
            matricula:          Matrícula do imóvel.
            tipo_vinculo:       Tipo: PROPRIETARIO, GARANTIDOR, COMPRADOR, etc.
            bloco_pessoa:       Índice do bloco na cadeia da pessoa.
            bloco_imovel:       Índice do bloco na cadeia do imóvel.
            dados:              Dados extras.

        Returns:
            A referência criada.
        """
        cpf_clean = cpf.replace(".", "").replace("-", "")
        matricula_clean = matricula.strip()

        # Obtém hashes das cadeias
        hash_pessoa = ""
        if cpf_clean in self._pf_chains:
            chain_pf = self._pf_chains[cpf_clean]
            if chain_pf.chain:
                last_block = chain_pf.chain[-1]
                hash_pessoa = last_block.hash

        hash_imovel = ""
        if matricula_clean in self._im_chains:
            chain_im = self._im_chains[matricula_clean]
            if chain_im.chain:
                last_block = chain_im.chain[-1]
                hash_imovel = last_block.hash

        ref = CrossReference(
            cpf=cpf_clean,
            matricula=matricula_clean,
            tipo_vinculo=tipo_vinculo,
            hash_cadeia_pessoa=hash_pessoa,
            hash_cadeia_imovel=hash_imovel,
            bloco_pessoa=bloco_pessoa,
            bloco_imovel=bloco_imovel,
            timestamp=time.time(),
            dados=dados or {},
        )
        self._references.append(ref)
        return ref

    def deactivate_reference(self, cpf: str, matricula: str, tipo_vinculo: str = "") -> int:
        """
        Desativa referências entre pessoa e imóvel.

        Returns:
            Número de referências desativadas.
        """
        cpf_clean = cpf.replace(".", "").replace("-", "")
        matricula_clean = matricula.strip()
        count = 0
        for ref in self._references:
            if ref.cpf == cpf_clean and ref.matricula == matricula_clean:
                if not tipo_vinculo or ref.tipo_vinculo == tipo_vinculo:
                    if ref.ativo:
                        ref.ativo = False
                        count += 1
        return count

    # ── Consultas ─────────────────────────────────────────────────────

    def get_imoveis_da_pessoa(self, cpf: str) -> list[dict[str, Any]]:
        """Lista todos os imóveis vinculados a uma pessoa."""
        cpf_clean = cpf.replace(".", "").replace("-", "")
        result = []
        for ref in self._references:
            if ref.cpf == cpf_clean and ref.ativo:
                imovel_info = {"matricula": ref.matricula, "vinculo": ref.tipo_vinculo}
                # Enriquece com dados do imóvel
                if ref.matricula in self._im_chains:
                    chain = self._im_chains[ref.matricula]
                    estado = chain.get_estado_atual()
                    imovel_info["endereco"] = estado.get("endereco", {})
                    imovel_info["situacao"] = estado.get("situacao", "")
                    imovel_info["area_terreno"] = estado.get("area_terreno_m2", 0)
                    imovel_info["area_construida"] = estado.get("area_construida_m2", 0)
                result.append(imovel_info)
        return result

    def get_pessoas_do_imovel(self, matricula: str) -> list[dict[str, Any]]:
        """Lista todas as pessoas vinculadas a um imóvel."""
        matricula_clean = matricula.strip()
        result = []
        for ref in self._references:
            if ref.matricula == matricula_clean and ref.ativo:
                pessoa_info = {"cpf": ref.cpf, "vinculo": ref.tipo_vinculo}
                # Enriquece com dados da pessoa
                if ref.cpf in self._pf_chains:
                    chain = self._pf_chains[ref.cpf]
                    birth = chain.get_birth_block()
                    if birth:
                        payload = birth.data.get("payload", {})
                        pessoa_info["nome"] = payload.get("nome_completo", "")
                        pessoa_info["data_nascimento"] = payload.get("data_nascimento", "")
                result.append(pessoa_info)
        return result

    def get_vinculos_ativos(self, cpf: str = "", matricula: str = "") -> list[dict]:
        """Retorna todos os vínculos ativos, filtrando opcionalmente."""
        result = []
        for ref in self._references:
            if not ref.ativo:
                continue
            if cpf and ref.cpf != cpf.replace(".", "").replace("-", ""):
                continue
            if matricula and ref.matricula != matricula.strip():
                continue
            result.append(ref.to_dict())
        return result

    # ── Estatísticas ─────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Retorna estatísticas do sistema cross-chain."""
        ativos = sum(1 for r in self._references if r.ativo)
        return {
            "total_cadeias_pf": len(self._pf_chains),
            "total_cadeias_im": len(self._im_chains),
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
    def load_from_file(cls, filepath: str) -> "CrossChainManager":
        """Carrega referências de JSON."""
        import json
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        manager = cls()
        for ref_data in data.get("referencias", []):
            ref = CrossReference(**ref_data)
            manager._references.append(ref)
        return manager

    # ── Representação ─────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"CrossChainManager("
            f"pf={len(self._pf_chains)}, "
            f"im={len(self._im_chains)}, "
            f"refs={len(self._references)})"
        )
