"""
blockchain_ac/events.py
Definições e validadores para eventos de aeronaves.
Cada evento representa uma mudança na situação jurídica,
técnica ou operacional de uma aeronave desde sua fabricação.
"""

import re
import time
from enum import Enum
from typing import Any, Optional
from blockchain_pf.geografia_br import validar_cidade, validar_uf


# ── Enum de tipos de evento ────────────────────────────────────────────


class AircraftEventType(str, Enum):
    """Todos os tipos de evento de aeronave suportados."""

    # ── Gênesis ──────────────────────────────────────────────────────
    FABRICACAO = "FABRICACAO"  # Fabricação/cadastro (gênesis)

    # ── Transferência ────────────────────────────────────────────────
    COMPRA_VENDA = "COMPRA_VENDA"  # Transferência com pagamento
    DOACAO = "DOACAO"  # Transferência sem pagamento
    LEILAO = "LEILAO"  # Venda em leilão
    CONFISCO = "CONFISCO"  # Apreensão judicial

    # ── Manutenção ───────────────────────────────────────────────────
    REVISAO = "REVISAO"  # Revisão/manutenção programada
    REPARO = "REPARO"  # Reparo não programado
    INSPECAO = "INSPECAO"  # Inspeção técnica
    MODIFICACAO = "MODIFICACAO"  # Modificação STC

    # ── Administrativo ───────────────────────────────────────────────
    REGISTRO = "REGISTRO"  # Registro em nova autoridade
    MUDANCA_NOME = "MUDANCA_NOME"  # Mudança de nome/identificação
    BAIXA = "BAIXA"  # Baixa definitiva
    CERTIDAO = "CERTIDAO"  # Certidão emitida
    AIRWORTHINESS = "AIRWORTHINESS"  # Certificado de aeronavegabilidade
    LICENCA_VOO = "LICENCA_VOO"  # Licença de voo

    # ── Seguro ───────────────────────────────────────────────────────
    SEGURO = "SEGURO"  # Contratação de seguro
    SINISTRO = "SINISTRO"  # Registro de sinistro


# ── Validadores ────────────────────────────────────────────────────────


def _valida_cpf(cpf: str) -> bool:
    cpf_clean = re.sub(r"\D", "", cpf)
    return len(cpf_clean) == 11


def _valida_data(data: str) -> bool:
    return bool(re.match(r"^\d{2}/\d{2}/\d{4}$", data))


def _valida_matricula_aeronave(c: str) -> bool:
    """Validação básica de matrícula de aeronave."""
    n_clean = re.sub(r"[-\s]", "", c.upper())
    return bool(re.match(r"^[A-Z][A-Z0-9]{1,5}$", n_clean))


# ── Fábricas de eventos ───────────────────────────────────────────────


class AircraftEventFactory:
    """
    Fábrica para criar eventos validados de aeronaves.
    Cada método retorna um dict pronto para ir ao bloco.
    """

    @staticmethod
    def fabricacao(
        matricula: str,
        nome_aeronave: str,
        fabricante: str,
        modelo: str,
        tipo_aeronave: str,
        ano_fabricacao: int,
        peso_max_decolagem_kg: float,
        motorizacao: str,
        num_motores: int,
        motor_tipo: str = "",
        motor_potencia_cv: float = 0.0,
        envergadura_m: float = 0.0,
        comprimento_m: float = 0.0,
        autonomia_km: float = 0.0,
        velocidade_max_kmh: float = 0.0,
        capacidade_pilotos: int = 1,
        capacidade_passageiros: int = 0,
        pais_fabricacao: str = "BR",
        numero_serie: str = "",
        certificado_tipo: str = "",
        uf: str = "",
        cidade: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de FABRICAÇÃO (bloco gênesis).

        Args:
            matricula:              Matrícula da aeronave (N-number, PT-XXX, etc).
            nome_aeronave:          Nome da aeronave.
            fabricante:             Nome do fabricante.
            modelo:                 Modelo da aeronave.
            tipo_aeronave:          AVIAO, HELICOPTERO, PLANADOR, BALAO, DRONE.
            ano_fabricacao:         Ano de fabricação.
            peso_max_decolagem_kg:  Peso máximo de decolagem em kg.
            motorizacao:            PISTAO, TURBOEIXO, TURBOHELICE, JATO, etc.
            num_motores:            Número de motores.
            motor_tipo:             Tipo do motor.
            motor_potencia_cv:      Potência em CV.
            envergadura_m:          Envergadura em metros.
            comprimento_m:          Comprimento em metros.
            autonomia_km:           Autonomia em km.
            velocidade_max_kmh:     Velocidade máxima em km/h.
            capacidade_pilotos:     Capacidade de pilotos.
            capacidade_passageiros: Capacidade de passageiros.
            pais_fabricacao:        País de fabricação.
            numero_serie:           Número de série.
            certificado_tipo:       Tipo de certificado.
        """
        dados = {
            "evento_tipo": AircraftEventType.FABRICACAO.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "nome_aeronave": nome_aeronave.strip(),
            "fabricante": fabricante.strip(),
            "modelo": modelo.strip(),
            "tipo_aeronave": tipo_aeronave.upper().strip(),
            "ano_fabricacao": ano_fabricacao,
            "peso_max_decolagem_kg": peso_max_decolagem_kg,
            "motorizacao": motorizacao.upper().strip(),
            "num_motores": num_motores,
            "motor": {
                "tipo": motor_tipo.strip(),
                "potencia_cv": motor_potencia_cv,
            },
            "dimensoes": {
                "envergadura_m": envergadura_m,
                "comprimento_m": comprimento_m,
            },
            "desempenho": {
                "autonomia_km": autonomia_km,
                "velocidade_max_kmh": velocidade_max_kmh,
            },
            "capacidade": {
                "pilotos": capacidade_pilotos,
                "passageiros": capacidade_passageiros,
            },
            "pais_fabricacao": pais_fabricacao.upper().strip(),
            "uf": uf.upper().strip(),
            "cidade": cidade.strip(),
            "numero_serie": numero_serie.strip(),
            "certificado_tipo": certificado_tipo.strip(),
            "situacao": "REGULAR",
            "proprietarios": [],
            "seguros": [],
            "certidoes": [],
            "airworthiness": [],
            "historico_manutencao": [],
        }
        if not matricula.strip():
            raise ValueError("Matrícula é obrigatória.")
        if not nome_aeronave.strip():
            raise ValueError("Nome da aeronave é obrigatório.")
        if not fabricante.strip():
            raise ValueError("Fabricante é obrigatório.")
        if peso_max_decolagem_kg <= 0:
            raise ValueError(f"Peso máximo deve ser positivo: {peso_max_decolagem_kg}")
        if not validar_cidade(uf, cidade):
            raise ValueError(f"Local inválido: {cidade}/{uf}. Cidade deve existir na tabela oficial (IBGE).")
        return dados

    @staticmethod
    def compra_venda(
        matricula: str,
        comprador_cpf: str,
        comprador_nome: str,
        vendedor_cpf: str,
        vendedor_nome: str,
        valor_transacao: float,
        data_transacao: str,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de COMPRA/VENDA."""
        dados = {
            "evento_tipo": AircraftEventType.COMPRA_VENDA.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "comprador": {"cpf": re.sub(r"\D", "", comprador_cpf), "nome": comprador_nome.strip()},
            "vendedor": {"cpf": re.sub(r"\D", "", vendedor_cpf), "nome": vendedor_nome.strip()},
            "valor_transacao": valor_transacao,
            "data_transacao": data_transacao,
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_transacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_transacao}")
        return dados

    @staticmethod
    def doacao(
        matricula: str,
        donatario_cpf: str, donatario_nome: str,
        doador_cpf: str, doador_nome: str,
        data_doacao: str, motivo: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de DOAÇÃO."""
        dados = {
            "evento_tipo": AircraftEventType.DOACAO.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "donatario": {"cpf": re.sub(r"\D", "", donatario_cpf), "nome": donatario_nome.strip()},
            "doador": {"cpf": re.sub(r"\D", "", doador_cpf), "nome": doador_nome.strip()},
            "data_doacao": data_doacao, "motivo": motivo.strip(),
        }
        if not _valida_data(data_doacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_doacao}")
        return dados

    @staticmethod
    def revisao(
        matricula: str, data_revisao: str,
        oficina: str = "", tipo_revisao: str = "ANUAL",
        itens_revisados: Optional[list[str]] = None,
        proxima_revisao: str = "", valor_total: float = 0.0,
        descricao: str = "", **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de REVISÃO."""
        dados = {
            "evento_tipo": AircraftEventType.REVISAO.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "data_revisao": data_revisao, "oficina": oficina.strip(),
            "tipo_revisao": tipo_revisao.upper().strip(),
            "itens_revisados": itens_revisados or [],
            "proxima_revisao": proxima_revisao,
            "valor_total": valor_total, "descricao": descricao.strip(),
        }
        if not _valida_data(data_revisao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_revisao}")
        return dados

    @staticmethod
    def inspecao(
        matricula: str, data_inspecao: str, orgao_inspecao: str,
        resultado: str, certificado_numero: str = "",
        validade_certificado: str = "", descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de INSPEÇÃO."""
        dados = {
            "evento_tipo": AircraftEventType.INSPECAO.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "data_inspecao": data_inspecao,
            "orgao_inspecao": orgao_inspecao.strip(),
            "resultado": resultado.upper().strip(),
            "certificado_numero": certificado_numero.strip(),
            "validade_certificado": validade_certificado,
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_inspecao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_inspecao}")
        return dados

    @staticmethod
    def airworthiness(
        matricula: str, data_emissao: str, data_validade: str,
        numero_certificado: str, orgao_emissor: str = "ANAC",
        restricoes: Optional[list[str]] = None,
        descricao: str = "", **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de AIRWORTHINESS — certificado de aeronavegabilidade."""
        dados = {
            "evento_tipo": AircraftEventType.AIRWORTHINESS.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "data_emissao": data_emissao, "data_validade": data_validade,
            "numero_certificado": numero_certificado.strip(),
            "orgao_emissor": orgao_emissor.strip(),
            "restricoes": restricoes or [], "descricao": descricao.strip(),
            "status": "ATIVA",
        }
        if not _valida_data(data_emissao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_emissao}")
        return dados

    @staticmethod
    def baixa(
        matricula: str, data_baixa: str, motivo: str,
        destino: str = "", descricao: str = "", **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de BAIXA."""
        dados = {
            "evento_tipo": AircraftEventType.BAIXA.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "data_baixa": data_baixa, "motivo": motivo.strip(),
            "destino": destino.strip(), "descricao": descricao.strip(),
        }
        if not _valida_data(data_baixa):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_baixa}")
        return dados

    @staticmethod
    def registro(
        matricula: str, nova_matricula: str,
        data_registro: str, orgao: str = "ANAC",
        descricao: str = "", **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de REGISTRO — registro em nova autoridade."""
        dados = {
            "evento_tipo": AircraftEventType.REGISTRO.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "nova_matricula": re.sub(r"[-\s]", "", nova_matricula.upper()),
            "data_registro": data_registro, "orgao": orgao.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_registro):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_registro}")
        return dados

    @staticmethod
    def mudanca_nome(
        matricula: str, nome_anterior: str, nome_novo: str,
        data_mudanca: str, **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de MUDANÇA DE NOME."""
        dados = {
            "evento_tipo": AircraftEventType.MUDANCA_NOME.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "nome_anterior": nome_anterior.strip(), "nome_novo": nome_novo.strip(),
            "data_mudanca": data_mudanca,
        }
        if not _valida_data(data_mudanca):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_mudanca}")
        return dados

    @staticmethod
    def seguro(
        matricula: str, seguradora_nome: str, seguradora_cnpj: str,
        apolice_numero: str, data_inicio: str, data_fim: str,
        valor_segurado: float, tipo_seguro: str = "TOTAL",
        descricao: str = "", **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de SEGURO."""
        dados = {
            "evento_tipo": AircraftEventType.SEGURO.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "seguradora": {"nome": seguradora_nome.strip(), "cnpj": re.sub(r"\D", "", seguradora_cnpj)},
            "apolice_numero": apolice_numero.strip(),
            "data_inicio": data_inicio, "data_fim": data_fim,
            "valor_segurado": valor_segurado,
            "tipo_seguro": tipo_seguro.upper().strip(),
            "descricao": descricao.strip(), "status": "ATIVA",
        }
        if not _valida_data(data_inicio):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_inicio}")
        return dados

    @staticmethod
    def sinistro(
        matricula: str, data_sinistro: str, tipo: str,
        descricao: str = "", valor_dano: float = 0.0,
        bo_numero: str = "", **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de SINISTRO."""
        dados = {
            "evento_tipo": AircraftEventType.SINISTRO.value,
            "matricula": re.sub(r"[-\s]", "", matricula.upper()),
            "data_sinistro": data_sinistro, "tipo": tipo.upper().strip(),
            "descricao": descricao.strip(), "valor_dano": valor_dano,
            "bo_numero": bo_numero.strip(),
        }
        if not _valida_data(data_sinistro):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_sinistro}")
        return dados


class AircraftChainProtector:
    """Impede adição de eventos bloqueados."""

    BLOQUEADOS_APOS_BAIXA = {
        AircraftEventType.COMPRA_VENDA,
        AircraftEventType.DOACAO,
        AircraftEventType.LEILAO,
        AircraftEventType.REVISAO,
        AircraftEventType.INSPECAO,
        AircraftEventType.MODIFICACAO,
        AircraftEventType.AIRWORTHINESS,
        AircraftEventType.LICENCA_VOO,
    }

    @staticmethod
    def pode_adicionar(tipo_evento: str, situacao: str) -> bool:
        if situacao == "BAIXADA":
            try:
                tipo = AircraftEventType(tipo_evento)
                return tipo not in AircraftChainProtector.BLOQUEADOS_APOS_BAIXA
            except ValueError:
                return True
        return True
