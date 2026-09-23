"""
blockchain_em/events.py
Definições e validadores para eventos de embarcações.
Cada evento representa uma mudança na situação jurídica,
física ou operacional de uma embarcação desde sua construção.
"""

import re
import time
from enum import Enum
from typing import Any, Optional
from blockchain_pf.geografia_br import validar_cidade, validar_uf


# ── Enum de tipos de evento ────────────────────────────────────────────


class VesselEventType(str, Enum):
    """Todos os tipos de evento de embarcação suportados."""

    # ── Gênesis ──────────────────────────────────────────────────────
    CONSTRUCAO = "CONSTRUCAO"  # Construção/cadastro da embarcação (gênesis)

    # ── Transferência ────────────────────────────────────────────────
    COMPRA_VENDA = "COMPRA_VENDA"  # Transferência com pagamento
    DOACAO = "DOACAO"  # Transferência sem pagamento
    LEILAO = "LEILAO"  # Venda em leilão
    CONFISCO = "CONFISCO"  # Apreensão judicial

    # ── Manutenção / Inspeção ───────────────────────────────────────
    REVISAO = "REVISAO"  # Revisão/manutenção programada
    REPARO = "REPARO"  # Reparo não programado
    INSPECAO = "INSPECAO"  # Inspeção de segurança
    CONVERSao = "CONVERSao"  # Modificação/conversão da embarcação

    # ── Administrativo ───────────────────────────────────────────────
    LICENCIAMENTO = "LICENCIAMENTO"  # Renovação de licenciamento
    REGISTRO = "REGISTRO"  # Registro em novo porto
    MUDANCA_NOME = "MUDANCA_NOME"  # Mudança de nome da embarcação
    BAIXA = "BAIXA"  # Baixa definitiva
    CERTIDAO = "CERTIDAO"  # Certidão emitida

    # ── Seguro ───────────────────────────────────────────────────────
    SEGURO = "SEGURO"  # Contratação de seguro
    SINISTRO = "SINISTRO"  # Registro de sinistro


# ── Validadores ────────────────────────────────────────────────────────


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


class VesselEventFactory:
    """
    Fábrica para criar eventos validados de embarcações.
    Cada método retorna um dict pronto para ir ao bloco.
    """

    @staticmethod
    def construcao(
        registro_nr: str,
        nome_embarcacao: str,
        tipo_embarcacao: str,
        porte: str,
        comprimento_m: float,
        beam_m: float,
        pontal_m: float,
        calado_m: float,
        deslocamento_ton: float,
        casco_material: str,
        motorizacao: str,
        motor_potencia_cv: float,
        motor_tipo: str = "",
        motor_fabricante: str = "",
        motor_numero_serie: str = "",
        ano_construcao: int = 0,
        estaleiro: str = "",
        estaleiro_cnpj: str = "",
        bandeira: str = "BR",
        porto_registro: str = "",
        capacidade_tripulacao: int = 0,
        capacidade_passageiros: int = 0,
        autonomia_milhas: float = 0.0,
        velocidade_max_nos: float = 0.0,
        uf: str = "",
        cidade: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de CONSTRUÇÃO (bloco gênesis).

        Args:
            registro_nr:            Número de registro na autoridade marítima.
            nome_embarcacao:        Nome da embarcação.
            tipo_embarcacao:        Lancha, Veleiro, Iate, Barco, Catamarã, etc.
            porte:                  PEQUENO, MEDIO, GRANDE.
            comprimento_m:          Comprimento em metros.
            beam_m:                 Boca (beam) em metros.
            pontal_m:               Pontal em metros.
            calado_m:               Calado em metros.
            deslocamento_ton:       Deslocamento em toneladas.
            casco_material:         Fibra, Madeira, Alumínio, Aço, etc.
            motorizacao:            Inboard, Fora-de-borda, Semirrígido, etc.
            motor_potencia_cv:      Potência do motor em CV.
            motor_tipo:             Tipo do motor (gasolina, diesel, etc).
            motor_fabricante:       Fabricante do motor.
            motor_numero_serie:     Número de série do motor.
            ano_construcao:         Ano de construção.
            estaleiro:              Nome do estaleiro.
            estaleiro_cnpj:         CNPJ do estaleiro.
            bandeira:               País de registro (padrão BR).
            porto_registro:         Porto de registro.
            capacidade_tripulacao:  Capacidade de tripulantes.
            capacidade_passageiros: Capacidade de passageiros.
            autonomia_milhas:       Autonomia em milhas náuticas.
            velocidade_max_nos:     Velocidade máxima em nós.
        """
        dados = {
            "evento_tipo": VesselEventType.CONSTRUCAO.value,
            "registro_nr": registro_nr.strip(),
            "nome_embarcacao": nome_embarcacao.strip(),
            "tipo_embarcacao": tipo_embarcacao.strip(),
            "porte": porte.upper().strip(),
            "comprimento_m": comprimento_m,
            "beam_m": beam_m,
            "pontal_m": pontal_m,
            "calado_m": calado_m,
            "deslocamento_ton": deslocamento_ton,
            "casco": {
                "material": casco_material.strip(),
            },
            "motorizacao": motorizacao.strip(),
            "motor": {
                "tipo": motor_tipo.strip(),
                "potencia_cv": motor_potencia_cv,
                "fabricante": motor_fabricante.strip(),
                "numero_serie": motor_numero_serie.strip(),
            },
            "ano_construcao": ano_construcao,
            "estaleiro": {
                "nome": estaleiro.strip(),
                "cnpj": re.sub(r"\D", "", estaleiro_cnpj),
            },
            "bandeira": bandeira.upper().strip(),
            "porto_registro": porto_registro.strip(),
            "capacidade_tripulacao": capacidade_tripulacao,
            "capacidade_passageiros": capacidade_passageiros,
            "autonomia_milhas": autonomia_milhas,
            "velocidade_max_nos": velocidade_max_nos,
            "uf": uf.upper().strip(),
            "cidade": cidade.strip(),
            "situacao": "REGULAR",
            "proprietarios": [],
            "seguros": [],
            "certidoes": [],
        }
        # Validações
        if not registro_nr.strip():
            raise ValueError("Número de registro é obrigatório.")
        if not nome_embarcacao.strip():
            raise ValueError("Nome da embarcação é obrigatório.")
        if comprimento_m <= 0:
            raise ValueError(f"Comprimento deve ser positivo: {comprimento_m}")
        if not validar_cidade(uf, cidade):
            raise ValueError(f"Local inválido: {cidade}/{uf}. Cidade deve existir na tabela oficial (IBGE).")
        return dados

    @staticmethod
    def compra_venda(
        registro_nr: str,
        comprador_cpf: str,
        comprador_nome: str,
        vendedor_cpf: str,
        vendedor_nome: str,
        valor_transacao: float,
        data_transacao: str,
        cartorio: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de COMPRA/VENDA — transferência com pagamento."""
        dados = {
            "evento_tipo": VesselEventType.COMPRA_VENDA.value,
            "registro_nr": registro_nr.strip(),
            "comprador": {
                "cpf": re.sub(r"\D", "", comprador_cpf),
                "nome": comprador_nome.strip(),
            },
            "vendedor": {
                "cpf": re.sub(r"\D", "", vendedor_cpf),
                "nome": vendedor_nome.strip(),
            },
            "valor_transacao": valor_transacao,
            "data_transacao": data_transacao,
            "cartorio": cartorio.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_transacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_transacao}")
        if valor_transacao < 0:
            raise ValueError(f"Valor não pode ser negativo: {valor_transacao}")
        return dados

    @staticmethod
    def doacao(
        registro_nr: str,
        donatario_cpf: str,
        donatario_nome: str,
        doador_cpf: str,
        doador_nome: str,
        data_doacao: str,
        motivo: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de DOAÇÃO — transferência sem pagamento."""
        dados = {
            "evento_tipo": VesselEventType.DOACAO.value,
            "registro_nr": registro_nr.strip(),
            "donatario": {
                "cpf": re.sub(r"\D", "", donatario_cpf),
                "nome": donatario_nome.strip(),
            },
            "doador": {
                "cpf": re.sub(r"\D", "", doador_cpf),
                "nome": doador_nome.strip(),
            },
            "data_doacao": data_doacao,
            "motivo": motivo.strip(),
        }
        if not _valida_data(data_doacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_doacao}")
        return dados

    @staticmethod
    def leilao(
        registro_nr: str,
        data_leilao: str,
        valor_minimo: float,
        lance_vencedor: float = 0.0,
        vencedor_cpf: str = "",
        vencedor_nome: str = "",
        leiloeiro: str = "",
        tipo: str = "JUDICIAL",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de LEILÃO — venda em leilão."""
        dados = {
            "evento_tipo": VesselEventType.LEILAO.value,
            "registro_nr": registro_nr.strip(),
            "data_leilao": data_leilao,
            "valor_minimo": valor_minimo,
            "lance_vencedor": lance_vencedor,
            "vencedor": {
                "cpf": re.sub(r"\D", "", vencedor_cpf) if vencedor_cpf else "",
                "nome": vencedor_nome.strip(),
            },
            "leiloeiro": leiloeiro.strip(),
            "tipo": tipo.upper().strip(),
            "descricao": descricao.strip(),
            "status": "CONCLUIDO" if lance_vencedor > 0 else "AGUARDANDO",
        }
        if not _valida_data(data_leilao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_leilao}")
        return dados

    @staticmethod
    def revisao(
        registro_nr: str,
        data_revisao: str,
        oficina: str = "",
        tipo_revisao: str = "PREVENTIVA",
        itens_revisados: Optional[list[str]] = None,
        proxima_revisao: str = "",
        valor_total: float = 0.0,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de REVISÃO — manutenção programada."""
        dados = {
            "evento_tipo": VesselEventType.REVISAO.value,
            "registro_nr": registro_nr.strip(),
            "data_revisao": data_revisao,
            "oficina": oficina.strip(),
            "tipo_revisao": tipo_revisao.upper().strip(),
            "itens_revisados": itens_revisados or [],
            "proxima_revisao": proxima_revisao,
            "valor_total": valor_total,
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_revisao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_revisao}")
        return dados

    @staticmethod
    def inspecao(
        registro_nr: str,
        data_inspecao: str,
        orgao_inspecao: str,
        resultado: str,
        certificado_numero: str = "",
        validade_certificado: str = "",
        irregularidades: Optional[list[str]] = None,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de INSPEÇÃO — inspeção de segurança."""
        dados = {
            "evento_tipo": VesselEventType.INSPECAO.value,
            "registro_nr": registro_nr.strip(),
            "data_inspecao": data_inspecao,
            "orgao_inspecao": orgao_inspecao.strip(),
            "resultado": resultado.upper().strip(),
            "certificado_numero": certificado_numero.strip(),
            "validade_certificado": validade_certificado,
            "irregularidades": irregularidades or [],
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_inspecao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_inspecao}")
        return dados

    @staticmethod
    def licenciamento(
        registro_nr: str,
        ano_licenciamento: int,
        data_licenciamento: str,
        orgao_emissor: str = "",
        doc_numero: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de LICENCIAMENTO — renovação de licenciamento."""
        dados = {
            "evento_tipo": VesselEventType.LICENCIAMENTO.value,
            "registro_nr": registro_nr.strip(),
            "ano_licenciamento": ano_licenciamento,
            "data_licenciamento": data_licenciamento,
            "orgao_emissor": orgao_emissor.strip(),
            "doc_numero": doc_numero.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_licenciamento):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_licenciamento}")
        return dados

    @staticmethod
    def mudanca_nome(
        registro_nr: str,
        nome_anterior: str,
        nome_novo: str,
        data_mudanca: str,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de MUDANÇA DE NOME — alteração do nome da embarcação."""
        dados = {
            "evento_tipo": VesselEventType.MUDANCA_NOME.value,
            "registro_nr": registro_nr.strip(),
            "nome_anterior": nome_anterior.strip(),
            "nome_novo": nome_novo.strip(),
            "data_mudanca": data_mudanca,
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_mudanca):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_mudanca}")
        return dados

    @staticmethod
    def baixa(
        registro_nr: str,
        data_baixa: str,
        motivo: str,
        destino: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de BAIXA — baixa definitiva da embarcação."""
        dados = {
            "evento_tipo": VesselEventType.BAIXA.value,
            "registro_nr": registro_nr.strip(),
            "data_baixa": data_baixa,
            "motivo": motivo.strip(),
            "destino": destino.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_baixa):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_baixa}")
        return dados

    @staticmethod
    def seguro(
        registro_nr: str,
        seguradora_nome: str,
        seguradora_cnpj: str,
        apolice_numero: str,
        data_inicio: str,
        data_fim: str,
        valor_segurado: float,
        tipo_seguro: str = "CASCO",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de SEGURO — contratação de seguro."""
        dados = {
            "evento_tipo": VesselEventType.SEGURO.value,
            "registro_nr": registro_nr.strip(),
            "seguradora": {
                "nome": seguradora_nome.strip(),
                "cnpj": re.sub(r"\D", "", seguradora_cnpj),
            },
            "apolice_numero": apolice_numero.strip(),
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "valor_segurado": valor_segurado,
            "tipo_seguro": tipo_seguro.upper().strip(),
            "descricao": descricao.strip(),
            "status": "ATIVA",
        }
        if not _valida_data(data_inicio):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_inicio}")
        return dados

    @staticmethod
    def sinistro(
        registro_nr: str,
        data_sinistro: str,
        tipo: str,
        descricao: str = "",
        valor_dano: float = 0.0,
        seguradora_nome: str = "",
        apolice_numero: str = "",
        bo_numero: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de SINISTRO — registro de sinistro."""
        dados = {
            "evento_tipo": VesselEventType.SINISTRO.value,
            "registro_nr": registro_nr.strip(),
            "data_sinistro": data_sinistro,
            "tipo": tipo.upper().strip(),
            "descricao": descricao.strip(),
            "valor_dano": valor_dano,
            "seguradora_nome": seguradora_nome.strip(),
            "apolice_numero": apolice_numero.strip(),
            "bo_numero": bo_numero.strip(),
        }
        if not _valida_data(data_sinistro):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_sinistro}")
        return dados


# ── Protetor de Cadeia ────────────────────────────────────────────────


class VesselChainProtector:
    """Impede adição de eventos que não fazem sentido em certos estados."""

    BLOQUEADOS_APOS_BAIXA = {
        VesselEventType.COMPRA_VENDA,
        VesselEventType.DOACAO,
        VesselEventType.LEILAO,
        VesselEventType.REVISAO,
        VesselEventType.INSPECAO,
        VesselEventType.LICENCIAMENTO,
        VesselEventType.CONVERSao,
    }

    @staticmethod
    def pode_adicionar(tipo_evento: str, situacao: str) -> bool:
        """Verifica se um evento pode ser adicionado à cadeia."""
        if situacao == "BAIXADA":
            try:
                tipo = VesselEventType(tipo_evento)
                return tipo not in VesselChainProtector.BLOQUEADOS_APOS_BAIXA
            except ValueError:
                return True
        return True
