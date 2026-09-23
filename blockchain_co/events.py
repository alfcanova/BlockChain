"""
blockchain_co/events.py
Definições e validadores para eventos de empresas (CNPJ).
Cada evento representa uma mudança na situação jurídica,
administrativa ou societária de uma empresa desde sua constituição.
"""

import re
import time
from enum import Enum
from typing import Any, Optional
from blockchain_pf.geografia_br import validar_cidade, validar_uf


# ── Enum de tipos de evento ────────────────────────────────────────────


class CompanyEventType(str, Enum):
    """Todos os tipos de evento de empresa suportados."""

    # ── Gênesis ──────────────────────────────────────────────────────
    CONSTITUICAO = "CONSTITUICAO"  # Abertura da empresa (gênesis)

    # ── Alterações Contratuais ───────────────────────────────────────
    ALTERACAO_CONTRATUAL = "ALTERACAO_CONTRATUAL"  # Mudança de capital, objeto, endereço
    MUDANCA_ENDERECO = "MUDANCA_ENDERECO"  # Mudança de sede
    MUDANCA_CAPITAL = "MUDANCA_CAPITAL"  # Alteração de capital social
    MUDANCA_OBJETO = "MUDANCA_OBJETO"  # Alteração do objeto social
    MUDANCA_NOME = "MUDANCA_NOME"  # Mudança de razão social/nome fantasia

    # ── Societário ───────────────────────────────────────────────────
    ADICAO_SOCIO = "ADICAO_SOCIO"  # Entrada de novo sócio
    REMOCAO_SOCIO = "REMOCAO_SOCIO"  # Saída de sócio
    MUDANCA_QUOTA = "MUDANCA_QUOTA"  # Alteração de participação societária

    # ── Reestruturação ──────────────────────────────────────────────
    FUSAO = "FUSAO"  # União com outra empresa
    CISAO = "CISAO"  # Divisão em empresas menores
    INCORPORACAO = "INCORPORACAO"  # Absorção por outra empresa
    COLIGACAO = "COLIGACAO"  # Vínculo com outra empresa (consórcio)

    # ── Situação ─────────────────────────────────────────────────────
    SUSPENSAO = "SUSPENSAO"  # Suspensão de atividades
    REABERTURA = "REABERTURA"  # Retorno de atividades
    LIQUIDACAO = "LIQUIDACAO"  # Início da liquidação
    BAIXA = "BAIXA"  # Encerramento definitivo

    # ── Certidões / Documentos ───────────────────────────────────────
    CERTIDAO = "CERTIDAO"  # Certidão emitida (negativa, positiva)
    ALVARA = "ALVARA"  # Alvará de funcionamento
    INSCRICAO_ESTADUAL = "INSCRICAO_ESTADUAL"  # Inscrição estadual
    INSCRICAO_MUNICIPAL = "INSCRICAO_MUNICIPAL"  # Inscrição municipal

    # ── Financeiro ───────────────────────────────────────────────────
    GARANTIA = "GARANTIA"  # Garantia/fiança oferecida
    QUITACAO = "QUITACAO"  # Baixa de garantia


# ── Validadores ────────────────────────────────────────────────────────


def _valida_cnpj(cnpj: str) -> bool:
    """Validação básica de CNPJ (14 dígitos)."""
    cnpj_clean = re.sub(r"\D", "", cnpj)
    return len(cnpj_clean) == 14


def _valida_cpf(cpf: str) -> bool:
    """Validação básica de CPF (11 dígitos)."""
    cpf_clean = re.sub(r"\D", "", cpf)
    return len(cpf_clean) == 11


def _valida_data(data: str) -> bool:
    """Valida formato DD/MM/AAAA."""
    return bool(re.match(r"^\d{2}/\d{2}/\d{4}$", data))


def _valida_uf(uf: str) -> bool:
    """Valida UF brasileira (2 letras maiúsculas)."""
    ufs = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
        "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
        "SP", "SE", "TO",
    }
    return uf.upper() in ufs


# ── Fábricas de eventos ───────────────────────────────────────────────


class CompanyEventFactory:
    """
    Fábrica para criar eventos validados de empresas.
    Cada método retorna um dict pronto para ir ao bloco.
    """

    @staticmethod
    def constituicao(
        cnpj: str,
        razao_social: str,
        nome_fantasia: str,
        data_constituicao: str,
        tipo_empresa: str,
        porte: str,
        capital_social: float,
        natureza_juridica: str,
        atividade_principal: str,
        atividades_secundarias: Optional[list[str]] = None,
        endereco_sede: Optional[dict] = None,
        responsavel_cpf: str = "",
        responsavel_nome: str = "",
        contabilista_cpf: str = "",
        contabilista_nome: str = "",
        jucesp_numero: str = "",
        data_reg_jucesp: str = "",
        uf: str = "",
        cidade: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de CONSTITUIÇÃO (bloco gênesis).

        Args:
            cnpj:                   CNPJ da empresa (14 dígitos).
            razao_social:           Razão social.
            nome_fantasia:          Nome fantasia.
            data_constituicao:      Data de constituição (DD/MM/AAAA).
            tipo_empresa:           LTDA, SA, EIRELI, MEI, SLU, S/A, etc.
            porte:                  ME, EPP, MEI, MEDIO, GRANDE.
            capital_social:         Capital social em R$.
            natureza_juridica:      Código da natureza jurídica.
            atividade_principal:    CNAE principal.
            atividades_secundarias: Lista de CNAEs secundários.
            endereco_sede:          Dict com endereço da sede.
            responsavel_cpf:        CPF do responsável legal.
            responsavel_nome:       Nome do responsável legal.
            contabilista_cpf:       CPF do contador.
            contabilista_nome:      Nome do contador.
            jucesp_numero:          Número de registro na JUCESP.
            data_reg_jucesp:        Data do registro na JUCESP.
        """
        dados = {
            "evento_tipo": CompanyEventType.CONSTITUICAO.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "razao_social": razao_social.strip(),
            "nome_fantasia": nome_fantasia.strip(),
            "data_constituicao": data_constituicao,
            "tipo_empresa": tipo_empresa.upper().strip(),
            "porte": porte.upper().strip(),
            "capital_social": capital_social,
            "natureza_juridica": natureza_juridica.strip(),
            "atividade_principal": atividade_principal.strip(),
            "atividades_secundarias": atividades_secundarias or [],
            "endereco_sede": endereco_sede or {},
            "uf": uf.upper().strip(),
            "cidade": cidade.strip(),
            "responsavel": {
                "cpf": re.sub(r"\D", "", responsavel_cpf),
                "nome": responsavel_nome.strip(),
            },
            "contabilista": {
                "cpf": re.sub(r"\D", "", contabilista_cpf),
                "nome": contabilista_nome.strip(),
            },
            "registro": {
                "jucesp_numero": jucesp_numero.strip(),
                "data_reg_jucesp": data_reg_jucesp,
            },
            "situacao_cadastral": "ATIVA",
            "socios": [],
            "certidoes": [],
            "garantias": [],
            "enderecos_historico": [endereco_sede] if endereco_sede else [],
        }
        # Validações
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not razao_social.strip():
            raise ValueError("Razão social é obrigatória.")
        if not _valida_data(data_constituicao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_constituicao}")
        if capital_social < 0:
            raise ValueError(f"Capital social não pode ser negativo: {capital_social}")
        if not validar_cidade(uf, cidade):
            raise ValueError(f"Local inválido: {cidade}/{uf}. Cidade deve existir na tabela oficial (IBGE).")
        return dados

    @staticmethod
    def adicao_socio(
        cnpj: str,
        socio_cpf: str,
        socio_nome: str,
        participacao: float,
        data_entrada: str,
        tipo_socio: str = "QUOTISTA",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de ADIÇÃO DE SÓCIO — entrada de novo sócio.

        Args:
            cnpj:           CNPJ da empresa.
            socio_cpf:      CPF do sócio.
            socio_nome:     Nome do sócio.
            participacao:   Percentual de participação (0-100).
            data_entrada:   Data de entrada (DD/MM/AAAA).
            tipo_socio:     QUOTISTA, ACIONISTA, ADMINISTRADOR.
            descricao:      Descrição complementar.
        """
        dados = {
            "evento_tipo": CompanyEventType.ADICAO_SOCIO.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "socio": {
                "cpf": re.sub(r"\D", "", socio_cpf),
                "nome": socio_nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "participacao": participacao,
            "data_entrada": data_entrada,
            "tipo_socio": tipo_socio.upper().strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_cpf(socio_cpf):
            raise ValueError(f"CPF do sócio inválido: {socio_cpf}")
        if not socio_nome.strip():
            raise ValueError("Nome do sócio é obrigatório.")
        if not (0 < participacao <= 100):
            raise ValueError(f"Participação inválida: {participacao}. Deve ser entre 0 e 100.")
        if not _valida_data(data_entrada):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_entrada}")
        return dados

    @staticmethod
    def remocao_socio(
        cnpj: str,
        socio_cpf: str,
        socio_nome: str,
        data_saida: str,
        motivo: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de REMOÇÃO DE SÓCIO — saída de sócio.

        Args:
            cnpj:           CNPJ da empresa.
            socio_cpf:      CPF do sócio.
            socio_nome:     Nome do sócio.
            data_saida:     Data de saída (DD/MM/AAAA).
            motivo:         Motivo da saída.
        """
        dados = {
            "evento_tipo": CompanyEventType.REMOCAO_SOCIO.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "socio": {
                "cpf": re.sub(r"\D", "", socio_cpf),
                "nome": socio_nome.strip(),
            },
            "data_saida": data_saida,
            "motivo": motivo.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_cpf(socio_cpf):
            raise ValueError(f"CPF do sócio inválido: {socio_cpf}")
        if not _valida_data(data_saida):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_saida}")
        return dados

    @staticmethod
    def mudanca_quota(
        cnpj: str,
        socio_cpf: str,
        socio_nome: str,
        participacao_anterior: float,
        participacao_nova: float,
        data_mudanca: str,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de MUDANÇA DE QUOTA — alteração de participação societária."""
        dados = {
            "evento_tipo": CompanyEventType.MUDANCA_QUOTA.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "socio": {
                "cpf": re.sub(r"\D", "", socio_cpf),
                "nome": socio_nome.strip(),
            },
            "participacao_anterior": participacao_anterior,
            "participacao_nova": participacao_nova,
            "data_mudanca": data_mudanca,
            "descricao": descricao.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_cpf(socio_cpf):
            raise ValueError(f"CPF do sócio inválido: {socio_cpf}")
        if not _valida_data(data_mudanca):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_mudanca}")
        return dados

    @staticmethod
    def alteracao_contratual(
        cnpj: str,
        data_alteracao: str,
        descricao: str,
        tipo_alteracao: str = "GERAL",
        documento_numero: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de ALTERAÇÃO CONTRATUAL — mudança geral no contrato social."""
        dados = {
            "evento_tipo": CompanyEventType.ALTERACAO_CONTRATUAL.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "data_alteracao": data_alteracao,
            "descricao": descricao.strip(),
            "tipo_alteracao": tipo_alteracao.upper().strip(),
            "documento_numero": documento_numero.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_alteracao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_alteracao}")
        return dados

    @staticmethod
    def mudanca_endereco(
        cnpj: str,
        novo_endereco: dict,
        data_mudanca: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de MUDANÇA DE ENDEREÇO — nova sede."""
        dados = {
            "evento_tipo": CompanyEventType.MUDANCA_ENDERECO.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "novo_endereco": novo_endereco,
            "data_mudanca": data_mudanca,
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_mudanca):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_mudanca}")
        return dados

    @staticmethod
    def mudanca_capital(
        cnpj: str,
        capital_anterior: float,
        capital_novo: float,
        data_mudanca: str,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de MUDANÇA DE CAPITAL — alteração do capital social."""
        dados = {
            "evento_tipo": CompanyEventType.MUDANCA_CAPITAL.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "capital_anterior": capital_anterior,
            "capital_novo": capital_novo,
            "data_mudanca": data_mudanca,
            "descricao": descricao.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_mudanca):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_mudanca}")
        return dados

    @staticmethod
    def fusao(
        cnpj_origem: str,
        cnpj_destino: str,
        razao_social_nova: str,
        cnpj_novo: str,
        data_fusao: str,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de FUSÃO — união com outra empresa."""
        dados = {
            "evento_tipo": CompanyEventType.FUSAO.value,
            "cnpj_origem": re.sub(r"\D", "", cnpj_origem),
            "cnpj_destino": re.sub(r"\D", "", cnpj_destino),
            "razao_social_nova": razao_social_nova.strip(),
            "cnpj_novo": re.sub(r"\D", "", cnpj_novo),
            "data_fusao": data_fusao,
            "descricao": descricao.strip(),
        }
        if not _valida_cnpj(cnpj_origem):
            raise ValueError(f"CNPJ de origem inválido: {cnpj_origem}")
        if not _valida_data(data_fusao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_fusao}")
        return dados

    @staticmethod
    def cisao(
        cnpj_origem: str,
        empresas_novas: list[dict],
        data_cisao: str,
        tipo: str = "PARCIAL",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de CISÃO — divisão em empresas menores."""
        dados = {
            "evento_tipo": CompanyEventType.CISAO.value,
            "cnpj_origem": re.sub(r"\D", "", cnpj_origem),
            "empresas_novas": empresas_novas,
            "data_cisao": data_cisao,
            "tipo": tipo.upper().strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_cnpj(cnpj_origem):
            raise ValueError(f"CNPJ de origem inválido: {cnpj_origem}")
        if not _valida_data(data_cisao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_cisao}")
        return dados

    @staticmethod
    def incorporacao(
        cnpj_incorporadora: str,
        cnpj_incorporada: str,
        data_incorporacao: str,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de INCORPORACAO — absorção por outra empresa."""
        dados = {
            "evento_tipo": CompanyEventType.INCORPORACAO.value,
            "cnpj_incorporadora": re.sub(r"\D", "", cnpj_incorporadora),
            "cnpj_incorporada": re.sub(r"\D", "", cnpj_incorporada),
            "data_incorporacao": data_incorporacao,
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_incorporacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_incorporacao}")
        return dados

    @staticmethod
    def suspensao(
        cnpj: str,
        data_suspensao: str,
        motivo: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de SUSPENSÃO — suspensão de atividades."""
        dados = {
            "evento_tipo": CompanyEventType.SUSPENSAO.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "data_suspensao": data_suspensao,
            "motivo": motivo.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_suspensao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_suspensao}")
        return dados

    @staticmethod
    def reabertura(
        cnpj: str,
        data_reabertura: str,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de REABERTURA — retorno de atividades."""
        dados = {
            "evento_tipo": CompanyEventType.REABERTURA.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "data_reabertura": data_reabertura,
            "descricao": descricao.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_reabertura):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_reabertura}")
        return dados

    @staticmethod
    def liquidacao(
        cnpj: str,
        data_liquidacao: str,
        motivo: str,
        liquidante_cpf: str = "",
        liquidante_nome: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de LIQUIDAÇÃO — início da liquidação."""
        dados = {
            "evento_tipo": CompanyEventType.LIQUIDACAO.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "data_liquidacao": data_liquidacao,
            "motivo": motivo.strip(),
            "liquidante": {
                "cpf": re.sub(r"\D", "", liquidante_cpf),
                "nome": liquidante_nome.strip(),
            },
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_liquidacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_liquidacao}")
        return dados

    @staticmethod
    def baixa(
        cnpj: str,
        data_baixa: str,
        motivo: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de BAIXA — encerramento definitivo da empresa."""
        dados = {
            "evento_tipo": CompanyEventType.BAIXA.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "data_baixa": data_baixa,
            "motivo": motivo.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_baixa):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_baixa}")
        return dados

    @staticmethod
    def certidao(
        cnpj: str,
        tipo_certidao: str,
        numero: str,
        data_emissao: str,
        orgao_emissor: str,
        conteudo: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de CERTIDÃO — emissão de certidão."""
        dados = {
            "evento_tipo": CompanyEventType.CERTIDAO.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "tipo_certidao": tipo_certidao.upper().strip(),
            "numero": numero.strip(),
            "data_emissao": data_emissao,
            "orgao_emissor": orgao_emissor.strip(),
            "conteudo": conteudo.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_emissao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_emissao}")
        return dados

    @staticmethod
    def alvara(
        cnpj: str,
        numero: str,
        data_emissao: str,
        data_validade: str,
        orgao_emissor: str,
        atividades_permitidas: Optional[list[str]] = None,
        endereco: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de ALVARÁ — alvará de funcionamento."""
        dados = {
            "evento_tipo": CompanyEventType.ALVARA.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "numero": numero.strip(),
            "data_emissao": data_emissao,
            "data_validade": data_validade,
            "orgao_emissor": orgao_emissor.strip(),
            "atividades_permitidas": atividades_permitidas or [],
            "endereco": endereco.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_emissao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_emissao}")
        return dados

    @staticmethod
    def garantia(
        cnpj: str,
        credor_nome: str,
        credor_cnpj: str,
        valor_garantia: float,
        data_garantia: str,
        data_vencimento: str,
        tipo_garantia: str = "FIANCA",
        taxa_juros: float = 0.0,
        prazo_meses: int = 0,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de GARANTIA — garantia/fiança oferecida pela empresa."""
        dados = {
            "evento_tipo": CompanyEventType.GARANTIA.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "credor": {
                "nome": credor_nome.strip(),
                "cnpj": re.sub(r"\D", "", credor_cnpj),
            },
            "valor_garantia": valor_garantia,
            "data_garantia": data_garantia,
            "data_vencimento": data_vencimento,
            "tipo_garantia": tipo_garantia.upper().strip(),
            "taxa_juros": taxa_juros,
            "prazo_meses": prazo_meses,
            "descricao": descricao.strip(),
            "status": "ATIVA",
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_garantia):
            raise ValueError(f"Data de garantia inválida (DD/MM/AAAA): {data_garantia}")
        if valor_garantia <= 0:
            raise ValueError(f"Valor da garantia deve ser positivo: {valor_garantia}")
        return dados

    @staticmethod
    def quitacao(
        cnpj: str,
        garantia_index: int,
        data_quitacao: str,
        valor_pago: float = 0.0,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de QUITAÇÃO — baixa de garantia."""
        dados = {
            "evento_tipo": CompanyEventType.QUITACAO.value,
            "cnpj": re.sub(r"\D", "", cnpj),
            "garantia_index": garantia_index,
            "data_quitacao": data_quitacao,
            "valor_pago": valor_pago,
            "descricao": descricao.strip(),
        }
        if not _valida_cnpj(cnpj):
            raise ValueError(f"CNPJ inválido: {cnpj}")
        if not _valida_data(data_quitacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_quitacao}")
        return dados


# ── Protetor de Cadeia ────────────────────────────────────────────────


class CompanyChainProtector:
    """
    Impede adição de eventos que não fazem sentido
    em certos estados da empresa.
    """

    BLOQUEADOS_APOS_BAIXA = {
        CompanyEventType.ADICAO_SOCIO,
        CompanyEventType.REMOCAO_SOCIO,
        CompanyEventType.MUDANCA_QUOTA,
        CompanyEventType.ALTERACAO_CONTRATUAL,
        CompanyEventType.MUDANCA_ENDERECO,
        CompanyEventType.MUDANCA_CAPITAL,
        CompanyEventType.MUDANCA_OBJETO,
        CompanyEventType.MUDANCA_NOME,
        CompanyEventType.FUSAO,
        CompanyEventType.CISAO,
        CompanyEventType.INCORPORACAO,
        CompanyEventType.SUSPENSAO,
    }

    @staticmethod
    def pode_adicionar(tipo_evento: str, situacao: str) -> bool:
        """Verifica se um evento pode ser adicionado à cadeia."""
        if situacao not in ("BAIXADA", "LIQUIDACAO_ENCERRADA"):
            return True
        try:
            tipo = CompanyEventType(tipo_evento)
            return tipo not in CompanyChainProtector.BLOQUEADOS_APOS_BAIXA
        except ValueError:
            return True  # Tipo desconhecido — permite
