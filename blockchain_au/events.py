"""
blockchain_au/events.py
Tipos de evento e fabrica de payloads da cadeia de Autoridade.

Payloads sao snapshots completos do registro de autoridade
(NOMEACAO/ALTERACAO) ou marcadores de REVOGACAO.
Alteracoes de N1/N2 entram como PENDENTES (status=ALTERACAO)
e so sao aplicadas apos CONFIRMACAO da autoridade superior.
Validacao estrita de escopo/UF/cidade contra a base IBGE.
"""

import time
from enum import Enum
from typing import Any

from blockchain_pf.geografia_br import validar_cidade, validar_uf


class AuthorityEventType(str, Enum):
    """Tipos de bloco da cadeia de autoridade."""
    NOMEACAO = "NOMEACAO"
    ALTERACAO = "ALTERACAO"
    REVOGACAO = "REVOGACAO"
    CONFIRMACAO = "CONFIRMACAO"
    RECUSA = "RECUSA"


# 7 dominios de dados governados pelas autoridades
DOMINIOS = ["pf", "im", "mo", "co", "em", "ac", "an"]


class AuthorityEventFactory:
    """
    Fabrica de payloads de eventos de autoridade.
    N1: escopo + uf (cidade vazia).
    N2: escopo + uf + cidade (estritamente IBGE da UF).
    """

    @staticmethod
    def _validar_base(nivel: int, escopo: str, uf: str, cidade: str) -> None:
        if nivel not in (1, 2):
            raise ValueError(f"Nivel de autoridade invalido: {nivel}. Use 1 (UF) ou 2 (cidade).")
        if escopo not in DOMINIOS:
            raise ValueError(f"Escopo invalido: {escopo}. Escopos: {', '.join(DOMINIOS)}.")
        if not validar_uf(uf):
            raise ValueError(f"UF invalida: {uf!r}. Use uma das 27 siglas oficiais.")
        if nivel == 1:
            if cidade.strip():
                raise ValueError(f"Autoridade de nivel 1 nao possui cidade (recebido: {cidade!r}).")
        else:
            if not validar_cidade(uf, cidade):
                raise ValueError(
                    f"Cidade invalida para a UF {uf}: {cidade!r}. "
                    "Precisa existir na tabela oficial IBGE."
                )

    @staticmethod
    def nomeacao(
        nome: str,
        nivel: int,
        escopo: str,
        uf: str = "",
        cidade: str = "",
        nomeado_por: str = "",
        data: str = "",
        motivo: str = "",
    ) -> dict[str, Any]:
        """Genesis: criacao de autoridade N1 (UF) ou N2 (cidade)."""
        AuthorityEventFactory._validar_base(nivel, escopo, uf, cidade or "")
        if not nome or not str(nome).strip():
            raise ValueError("Nome da autoridade e obrigatorio.")
        return {
            "username": "",
            "nome": str(nome).strip(),
            "nivel": nivel,
            "escopo": escopo,
            "uf": uf.strip().upper(),
            "cidade": cidade.strip().upper(),
            "nomeado_por": nomeado_por,
            "data": data or time.strftime("%d/%m/%Y"),
            "motivo": motivo or "",
        }

    @staticmethod
    def alteracao(
        nome: str = "",
        nivel: int = 0,
        escopo: str = "",
        uf: str = "",
        cidade: str = "",
        data: str = "",
        motivo: str = "",
    ) -> dict[str, Any]:
        """Alteracao de autoridade — fica PENDENTE ate confirmacao do superior."""
        return {
            "username": "",
            "nome": str(nome).strip(),
            "nivel": nivel,
            "escopo": escopo,
            "uf": uf.strip().upper(),
            "cidade": cidade.strip().upper(),
            "data": data or time.strftime("%d/%m/%Y"),
            "motivo": motivo or "",
            "status": "PENDENTE",
        }

    @staticmethod
    def confirmacao(
        username: str = "",
        nome: str = "",
        nivel: int = 0,
        escopo: str = "",
        uf: str = "",
        cidade: str = "",
        confirmado_por: str = "",
        data: str = "",
        motivo: str = "",
    ) -> dict[str, Any]:
        """Confirmacao (1a fase aplicada) de alteracao PENDENTE da autoridade."""
        return {
            "username": username,
            "nome": str(nome).strip(),
            "nivel": nivel,
            "escopo": escopo,
            "uf": uf.strip().upper(),
            "cidade": cidade.strip().upper(),
            "confirmado_por": confirmado_por,
            "data": data or time.strftime("%d/%m/%Y"),
            "motivo": motivo or "",
            "status": "CONFIRMADA",
        }

    @staticmethod
    def recusa(
        username: str = "",
        nome: str = "",
        nivel: int = 0,
        escopo: str = "",
        uf: str = "",
        cidade: str = "",
        recusado_por: str = "",
        data: str = "",
        motivo: str = "",
    ) -> dict[str, Any]:
        """Recusa (fase terminal) de alteracao PENDENTE — nao aplica."""
        return {
            "username": username,
            "nome": str(nome).strip(),
            "nivel": nivel,
            "escopo": escopo,
            "uf": uf.strip().upper(),
            "cidade": cidade.strip().upper(),
            "recusado_por": recusado_por,
            "data": data or time.strftime("%d/%m/%Y"),
            "motivo": motivo or "",
            "status": "RECUSADA",
        }

    @staticmethod
    def revogacao(data: str = "", motivo: str = "") -> dict[str, Any]:
        """Revogacao da autoridade (bloco terminal)."""
        return {
            "data": data or time.strftime("%d/%m/%Y"),
            "motivo": motivo or "Revogada pela autoridade superior.",
        }
