"""
blockchain_mo/events.py
Definições e validadores para eventos de veículos (móveis).
Cada evento representa uma mudança na situação jurídica,
física ou financeira de um veículo desde sua fabricação.
"""

import re
import time
from enum import Enum
from typing import Any, Optional
from blockchain_pf.geografia_br import validar_cidade, validar_uf


# ── Enum de tipos de evento ────────────────────────────────────────────


class VehicleEventType(str, Enum):
    """Todos os tipos de evento de veículo suportados."""

    # ── Gênesis ──────────────────────────────────────────────────────
    FABRICACAO = "FABRICACAO"  # Cadastro do veículo na fábrica (gênesis)

    # ── Transferência ────────────────────────────────────────────────
    COMPRA_VENDA = "COMPRA_VENDA"  # Transferência com pagamento
    DOACAO = "DOACAO"  # Transferência sem pagamento
    LEILAO = "LEILAO"  # Venda em leilão (judicial/extrajudicial)
    CONFISCO = "CONFISCO"  # Apreensão judicial

    # ── Garantia / Empréstimo ────────────────────────────────────────
    GARANTIA_EMPRESTIMO = "GARANTIA_EMPRESTIMO"  # Veículo como garantia
    QUITACAO_GARANTIA = "QUITACAO_GARANTIA"  # Baixa de garantia

    # ── Infrações / Sinistros ────────────────────────────────────────
    MULTA = "MULTA"  # Infração de trânsito
    SINISTRO = "SINISTRO"  # Acidente com avaria parcial
    SINISTRO_PERDA_TOTAL = "SINISTRO_PERDA_TOTAL"  # Destruição total

    # ── Manutenção / Peças ───────────────────────────────────────────
    TROCA_PECA = "TROCA_PECA"  # Substituição de componente
    VALIDACAO_PECA = "VALIDACAO_PECA"  # Validação/autenticação de peça
    REVISAO = "REVISAO"  # Revisão/manutenção programada

    # ── Administrativo ───────────────────────────────────────────────
    TRANSFERENCIA_PROPRIEDADE = "TRANSFERENCIA_PROPRIEDADE"  # Mudança DETRAN
    LICENCIAMENTO = "LICENCIAMENTO"  # Renovação de licenciamento
    MUDANCA_COR = "MUDANCA_COR"  # Alteração de cor (DETRAN)
    BAIXA = "BAIXA"  # Baixa definitiva do veículo
    RECALL_DE_FABRICA = "RECALL_DE_FABRICA"  # Recall de fábrica


# ── Validadores ────────────────────────────────────────────────────────


def _valida_cpf(cpf: str) -> bool:
    """Validação básica de CPF (11 dígitos)."""
    cpf_clean = re.sub(r"\D", "", cpf)
    return len(cpf_clean) == 11


def _valida_cnpj(cnpj: str) -> bool:
    """Validação básica de CNPJ (14 dígitos)."""
    cnpj_clean = re.sub(r"\D", "", cnpj)
    return len(cnpj_clean) == 14


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


def _valida_placa(placa: str) -> bool:
    """Valida placa brasileira (Mercosul: ABC1D23 ou antiga: ABC-1234)."""
    placa_clean = re.sub(r"[-\s]", "", placa.upper())
    # Mercosul: 3 letras + 1 digito + 3 alfanuméricos
    mercosul = bool(re.match(r"^[A-Z]{3}[0-9][A-Z0-9]{3}$", placa_clean))
    # Antiga: 3 letras + 4 digitos
    antiga = bool(re.match(r"^[A-Z]{3}[0-9]{4}$", placa_clean))
    return mercosul or antiga


def _valida_renavam(renavan: str) -> bool:
    """Validação básica de RENAVAN (11 dígitos)."""
    ren_clean = re.sub(r"\D", "", renavan)
    return len(ren_clean) == 11


def _valida_chassis(chassis: str) -> bool:
    """Validação básica de chassi (17 caracteres alfanuméricos, excluindo I, O, Q)."""
    ch = re.sub(r"[-\s]", "", chassis.upper())
    if len(ch) != 17:
        return False
    # VIN não pode ter I, O, Q
    invalidos = set("IOQ")
    return all(c not in invalidos for c in ch)


# ── Fábricas de eventos ───────────────────────────────────────────────


class VehicleEventFactory:
    """
    Fábrica para criar eventos validados de veículos.
    Cada método retorna um dict pronto para ir ao bloco.
    """

    @staticmethod
    def fabricacao(
        placa: str,
        renavan: str,
        chassis: str,
        marca: str,
        modelo: str,
        ano_fabricacao: int,
        ano_modelo: int,
        cor: str,
        combustivel: str,
        cilindradas: int,
        potencia_cv: float,
        tipo_veiculo: str = "AUTOMOVEL",
        categoria: str = "PARTICULAR",
        num_portas: int = 4,
        capacidade_passageiros: int = 5,
        fabricante_cnpj: str = "",
        fabricante_nome: str = "",
        fabricante_pais: str = "BR",
        motor_tipo: str = "",
        motor_numero: str = "",
        carroceria_tipo: str = "",
        carroceria_material: str = "",
        eixo_dianteiro: Optional[dict] = None,
        eixo_traseiro: Optional[dict] = None,
        freio_dianteiro: str = "",
        freio_traseiro: str = "",
        suspensao_dianteira: str = "",
        suspensao_traseira: str = "",
        direcao: str = "",
        transmissao: str = "",
        lote_fabricacao: str = "",
        data_fabricacao: str = "",
        certificado_homologacao: str = "",
        crv: str = "",
        odometro_km: float = 0.0,
        uf: str = "",
        cidade: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de FABRICAÇÃO (bloco gênesis).

        Cadastra o veículo no momento de sua fabricação.

        Args:
            placa:                    Placa do veículo (Mercosul ou antiga).
            renavan:                  RENAVAN (11 dígitos).
            chassis:                  Número do chassi (VIN, 17 chars).
            marca:                    Marca (ex: "Volkswagen").
            modelo:                   Modelo (ex: "Gol").
            ano_fabricacao:           Ano de fabricação.
            ano_modelo:               Ano do modelo.
            cor:                      Cor do veículo.
            combustivel:              Tipo de combustível (GASOLINA, ETANOL, FLEX, DIESEL, ELETRICO).
            cilindradas:              Cilindradas do motor.
            potencia_cv:              Potência em cavalos.
            tipo_veiculo:             AUTOMOVEL, CAMINHAO, MOTOCICLETA, ONIBUS, UTILITARIO.
            categoria:                PARTICULAR, Oficial, ALUGUEL, Locacao.
            num_portas:               Número de portas.
            capacidade_passageiros:   Capacidade de passageiros.
            fabricante_cnpj:          CNPJ do fabricante.
            fabricante_nome:          Nome do fabricante.
            fabricante_pais:          País do fabricante.
            motor_tipo:               Tipo do motor.
            motor_numero:             Número de série do motor.
            carroceria_tipo:          Tipo da carroceria.
            carroceria_material:      Material da carroceria.
            eixo_dianteiro:           Dados do eixo dianteiro.
            eixo_traseiro:            Dados do eixo traseiro.
            freio_dianteiro:          Tipo do freio dianteiro.
            freio_traseiro:           Tipo do freio traseiro.
            suspensao_dianteira:      Tipo da suspensão dianteira.
            suspensao_traseira:       Tipo da suspensão traseira.
            direcao:                  Tipo da direção.
            transmissao:              Tipo da transmissão.
            lote_fabricacao:          Número do lote de fabricação.
            data_fabricacao:          Data de fabricação (DD/MM/AAAA).
            certificado_homologacao:  Certificado de homologação.
            crv:                      CRV (Certificado de Registro de Veículo).
            odometro_km:              Quilometragem inicial.
        """
        dados = {
            "evento_tipo": VehicleEventType.FABRICACAO.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "renavan": re.sub(r"\D", "", renavan),
            "chassis": re.sub(r"[-\s]", "", chassis.upper()),
            "marca": marca.strip(),
            "modelo": modelo.strip(),
            "ano_fabricacao": ano_fabricacao,
            "ano_modelo": ano_modelo,
            "cor": cor.strip(),
            "combustivel": combustivel.upper().strip(),
            "cilindradas": cilindradas,
            "potencia_cv": potencia_cv,
            "uf": uf.upper().strip(),
            "cidade": cidade.strip(),
            "tipo_veiculo": tipo_veiculo.upper().strip(),
            "categoria": categoria.upper().strip(),
            "num_portas": num_portas,
            "capacidade_passageiros": capacidade_passageiros,
            "fabricante": {
                "cnpj": re.sub(r"\D", "", fabricante_cnpj),
                "nome": fabricante_nome.strip(),
                "pais": fabricante_pais.upper().strip(),
            },
            "motor": {
                "tipo": motor_tipo.strip(),
                "numero": motor_numero.strip(),
            },
            "carroceria": {
                "tipo": carroceria_tipo.strip(),
                "material": carroceria_material.strip(),
            },
            "eixo_dianteiro": eixo_dianteiro or {},
            "eixo_traseiro": eixo_traseiro or {},
            "freio_dianteiro": freio_dianteiro.strip(),
            "freio_traseiro": freio_traseiro.strip(),
            "suspensao_dianteira": suspensao_dianteira.strip(),
            "suspensao_traseira": suspensao_traseira.strip(),
            "direcao": direcao.strip(),
            "transmissao": transmissao.strip(),
            "lote_fabricacao": lote_fabricacao.strip(),
            "data_fabricacao": data_fabricacao,
            "certificado_homologacao": certificado_homologacao.strip(),
            "crv": crv.strip(),
            "situacao": "REGULAR",
            "proprietarios": [],
            "pecas_homologadas": [],
            "historico_veiculo": [],
            "odometro_km": odometro_km,
        }
        # Validações
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_renavam(renavan):
            raise ValueError(f"RENAVAN inválido: {renavan}")
        if not _valida_chassis(chassis):
            raise ValueError(f"Chassi inválido: {chassis}")
        if not marca.strip():
            raise ValueError("Marca é obrigatória.")
        if not modelo.strip():
            raise ValueError("Modelo é obrigatório.")
        if ano_fabricacao < 1900 or ano_fabricacao > 2100:
            raise ValueError(f"Ano de fabricação inválido: {ano_fabricacao}")
        if data_fabricacao and not _valida_data(data_fabricacao):
            raise ValueError(f"Data de fabricação inválida (DD/MM/AAAA): {data_fabricacao}")
        if not validar_cidade(uf, cidade):
            raise ValueError(f"Local inválido: {cidade}/{uf}. Cidade deve existir na tabela oficial (IBGE).")
        return dados

    @staticmethod
    def compra_venda(
        placa: str,
        comprador_cpf: str,
        comprador_nome: str,
        vendedor_cpf: str,
        vendedor_nome: str,
        valor_transacao: float,
        data_transacao: str,
        odometro_km: float = 0.0,
        notafiscal_numero: str = "",
        cartorio: str = "",
        dot_number: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de COMPRA/VENDA — transferência com pagamento.

        Args:
            placa:              Placa do veículo.
            comprador_cpf:      CPF do comprador.
            comprador_nome:     Nome do comprador.
            vendedor_cpf:       CPF do vendedor.
            vendedor_nome:      Nome do vendedor.
            valor_transacao:    Valor da transação (R$).
            data_transacao:     Data (DD/MM/AAAA).
            odometro_km:        Quilometragem na data da transação.
            notafiscal_numero:  Número da nota fiscal.
            cartorio:           Cartório onde foi lavrada.
            dot_number:         DOT number (se aplicável).
        """
        dados = {
            "evento_tipo": VehicleEventType.COMPRA_VENDA.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "comprador": {
                "cpf": re.sub(r"\D", "", comprador_cpf),
                "nome": comprador_nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "vendedor": {
                "cpf": re.sub(r"\D", "", vendedor_cpf),
                "nome": vendedor_nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "valor_transacao": valor_transacao,
            "data_transacao": data_transacao,
            "odometro_km": odometro_km,
            "notafiscal_numero": notafiscal_numero.strip(),
            "cartorio": cartorio.strip(),
            "dot_number": dot_number.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_cpf(comprador_cpf):
            raise ValueError(f"CPF do comprador inválido: {comprador_cpf}")
        if not _valida_cpf(vendedor_cpf):
            raise ValueError(f"CPF do vendedor inválido: {vendedor_cpf}")
        if not _valida_data(data_transacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_transacao}")
        if valor_transacao < 0:
            raise ValueError(f"Valor da transação não pode ser negativo: {valor_transacao}")
        return dados

    @staticmethod
    def doacao(
        placa: str,
        donatario_cpf: str,
        donatario_nome: str,
        doador_cpf: str,
        doador_nome: str,
        data_doacao: str,
        motivo: str = "",
        escritura_numero: str = "",
        cartorio: str = "",
        odometro_km: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de DOAÇÃO — transferência sem pagamento.

        Args:
            placa:              Placa do veículo.
            donatario_cpf:      CPF do donatário (quem recebe).
            donatario_nome:     Nome do donatário.
            doador_cpf:         CPF do doador (quem doa).
            doador_nome:        Nome do doador.
            data_doacao:        Data (DD/MM/AAAA).
            motivo:             Motivo da doação.
            escritura_numero:   Número da escritura.
            cartorio:           Cartório.
            odometro_km:        Quilometragem na data da doação.
        """
        dados = {
            "evento_tipo": VehicleEventType.DOACAO.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "donatario": {
                "cpf": re.sub(r"\D", "", donatario_cpf),
                "nome": donatario_nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "doador": {
                "cpf": re.sub(r"\D", "", doador_cpf),
                "nome": doador_nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "data_doacao": data_doacao,
            "motivo": motivo.strip(),
            "escritura_numero": escritura_numero.strip(),
            "cartorio": cartorio.strip(),
            "odometro_km": odometro_km,
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_cpf(donatario_cpf):
            raise ValueError(f"CPF do donatário inválido: {donatario_cpf}")
        if not _valida_cpf(doador_cpf):
            raise ValueError(f"CPF do doador inválido: {doador_cpf}")
        if not _valida_data(data_doacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_doacao}")
        return dados

    @staticmethod
    def garantia_emprestimo(
        placa: str,
        credor_nome: str,
        credor_cnpj: str,
        valor_emprestimo: float,
        data_garantia: str,
        data_vencimento: str,
        taxa_juros: float = 0.0,
        parcelas: int = 0,
        tipo_garantia: str = "ALIENACAO_FIDUCIARIA",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de GARANTIA DE EMPRÉSTIMO — veículo dado como garantia.

        Args:
            placa:              Placa do veículo.
            credor_nome:        Nome do credor (banco, financeira).
            credor_cnpj:        CNPJ do credor.
            valor_emprestimo:   Valor do empréstimo (R$).
            data_garantia:      Data da garantia (DD/MM/AAAA).
            data_vencimento:    Data de vencimento (DD/MM/AAAA).
            taxa_juros:         Taxa de juros anual (%).
            parcelas:           Número de parcelas.
            tipo_garantia:      ALIENACAO_FIDUCIARIA, PENHOR, HIPOTECARIA.
            descricao:          Descrição do empréstimo.
        """
        dados = {
            "evento_tipo": VehicleEventType.GARANTIA_EMPRESTIMO.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "credor": {
                "nome": credor_nome.strip(),
                "cnpj": re.sub(r"\D", "", credor_cnpj),
            },
            "valor_emprestimo": valor_emprestimo,
            "data_garantia": data_garantia,
            "data_vencimento": data_vencimento,
            "taxa_juros": taxa_juros,
            "parcelas": parcelas,
            "tipo_garantia": tipo_garantia.upper().strip(),
            "descricao": descricao.strip(),
            "status": "ATIVA",
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not credor_nome.strip():
            raise ValueError("Nome do credor é obrigatório.")
        if not _valida_cnpj(credor_cnpj):
            raise ValueError(f"CNPJ do credor inválido: {credor_cnpj}")
        if valor_emprestimo <= 0:
            raise ValueError(f"Valor do empréstimo deve ser positivo: {valor_emprestimo}")
        if not _valida_data(data_garantia):
            raise ValueError(f"Data de garantia inválida (DD/MM/AAAA): {data_garantia}")
        if not _valida_data(data_vencimento):
            raise ValueError(f"Data de vencimento inválida (DD/MM/AAAA): {data_vencimento}")
        return dados

    @staticmethod
    def quitacao_garantia(
        placa: str,
        garantia_index: int,
        data_quitacao: str,
        valor_pago: float = 0.0,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de QUITAÇÃO DE GARANTIA — baixa de empréstimo garantido.

        Args:
            placa:              Placa do veículo.
            garantia_index:     Índice da garantia a quitar.
            data_quitacao:      Data (DD/MM/AAAA).
            valor_pago:         Valor total pago.
            descricao:          Descrição.
        """
        dados = {
            "evento_tipo": VehicleEventType.QUITACAO_GARANTIA.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "garantia_index": garantia_index,
            "data_quitacao": data_quitacao,
            "valor_pago": valor_pago,
            "descricao": descricao.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_data(data_quitacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_quitacao}")
        return dados

    @staticmethod
    def leilao(
        placa: str,
        data_leilao: str,
        valor_minimo: float,
        lance_vencedor: float = 0.0,
        vencedor_cpf: str = "",
        vencedor_nome: str = "",
        leiloeiro: str = "",
        processo_numero: str = "",
        tipo: str = "JUDICIAL",
        descricao: str = "",
        odometro_km: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de LEILÃO — venda em leilão judicial ou extrajudicial.

        Args:
            placa:              Placa do veículo.
            data_leilao:        Data do leilão (DD/MM/AAAA).
            valor_minimo:       Valor mínimo (R$).
            lance_vencedor:     Lance vencedor (R$).
            vencedor_cpf:       CPF do vencedor.
            vencedor_nome:      Nome do vencedor.
            leiloeiro:          Nome do leiloeiro.
            processo_numero:    Número do processo (se judicial).
            tipo:               JUDICIAL ou EXTRAJUDICIAL.
            descricao:          Descrição.
            odometro_km:        Quilometragem no leilão.
        """
        dados = {
            "evento_tipo": VehicleEventType.LEILAO.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "data_leilao": data_leilao,
            "valor_minimo": valor_minimo,
            "lance_vencedor": lance_vencedor,
            "vencedor": {
                "cpf": re.sub(r"\D", "", vencedor_cpf) if vencedor_cpf else "",
                "nome": vencedor_nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "leiloeiro": leiloeiro.strip(),
            "processo_numero": processo_numero.strip(),
            "tipo": tipo.upper().strip(),
            "descricao": descricao.strip(),
            "odometro_km": odometro_km,
            "status": "CONCLUIDO" if lance_vencedor > 0 else "AGUARDANDO",
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_data(data_leilao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_leilao}")
        if valor_minimo <= 0:
            raise ValueError(f"Valor mínimo deve ser positivo: {valor_minimo}")
        return dados

    @staticmethod
    def confisco(
        placa: str,
        autoridade: str,
        processo_numero: str,
        data_confisco: str,
        motivo: str = "",
        destino: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de CONFISCO — apreensão judicial do veículo.

        Args:
            placa:              Placa do veículo.
            autoridade:         Autoridade que decretou.
            processo_numero:    Número do processo.
            data_confisco:      Data (DD/MM/AAAA).
            motivo:             Motivo do confisco.
            destino:            Destino do veículo confiscado.
        """
        dados = {
            "evento_tipo": VehicleEventType.CONFISCO.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "autoridade": autoridade.strip(),
            "processo_numero": processo_numero.strip(),
            "data_confisco": data_confisco,
            "motivo": motivo.strip(),
            "destino": destino.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_data(data_confisco):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_confisco}")
        return dados

    @staticmethod
    def multa(
        placa: str,
        numero_auto: str,
        data_infracao: str,
        local_logradouro: str,
        local_cidade: str,
        local_uf: str,
        enquadramento: str,
        pontos: int,
        valor_multa: float,
        orgao_autuador: str,
        condutor_cpf: str = "",
        condutor_nome: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de MULTA — infração de trânsito.

        Args:
            placa:              Placa do veículo.
            numero_auto:        Número do auto de infração.
            data_infracao:      Data da infração (DD/MM/AAAA).
            local_logradouro:   Local da infração.
            local_cidade:       Cidade.
            local_uf:           UF.
            enquadramento:      Código do CTB.
            pontos:             Pontos na CNH.
            valor_multa:        Valor da multa (R$).
            orgao_autuador:     Órgão que autuou.
            condutor_cpf:       CPF do condutor (se diferente do proprietário).
            condutor_nome:      Nome do condutor.
            descricao:          Descrição complementar.
        """
        dados = {
            "evento_tipo": VehicleEventType.MULTA.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "numero_auto": numero_auto.strip(),
            "data_infracao": data_infracao,
            "local": {
                "logradouro": local_logradouro.strip(),
                "cidade": local_cidade.strip(),
                "uf": local_uf.upper().strip(),
            },
            "enquadramento": enquadramento.strip(),
            "pontos": pontos,
            "valor_multa": valor_multa,
            "orgao_autuador": orgao_autuador.strip(),
            "condutor": {
                "cpf": re.sub(r"\D", "", condutor_cpf) if condutor_cpf else "",
                "nome": condutor_nome.strip(),
            },
            "descricao": descricao.strip(),
            "status": "PENDENTE",
            "data_pagamento": "",
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not numero_auto.strip():
            raise ValueError("Número do auto de infração é obrigatório.")
        if not _valida_data(data_infracao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_infracao}")
        if not local_uf.strip() or not _valida_uf(local_uf):
            raise ValueError(f"UF inválida: {local_uf}")
        if pontos < 0 or pontos > 7:
            raise ValueError(f"Pontos inválidos: {pontos}. Máximo 7.")
        if valor_multa <= 0:
            raise ValueError(f"Valor da multa deve ser positivo: {valor_multa}")
        return dados

    @staticmethod
    def sinistro(
        placa: str,
        data_sinistro: str,
        tipo: str,
        bo_numero: str,
        delegacia: str = "",
        seguradora_nome: str = "",
        seguradora_cnpj: str = "",
        seguradora_apolice: str = "",
        valor_dano: float = 0.0,
        laudo_perito: str = "",
        oficina_responsavel: str = "",
        pecas_danificadas: Optional[list[str]] = None,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de SINISTRO — acidente com avaria parcial.

        Args:
            placa:                  Placa do veículo.
            data_sinistro:          Data do sinistro (DD/MM/AAAA).
            tipo:                   COLISAO, ATROPELAMENTO, INCENDIO, ALAGAMENTO, OUTRO.
            bo_numero:              Número do boletim de ocorrência.
            delegacia:              Delegacia registradora.
            seguradora_nome:        Nome da seguradora.
            seguradora_cnpj:        CNPJ da seguradora.
            seguradora_apolice:     Número da apólice.
            valor_dano:             Valor estimado do dano (R$).
            laudo_perito:           Laudo do perito.
            oficina_responsavel:    Oficina que realizou o reparo.
            pecas_danificadas:      Lista de peças danificadas.
            descricao:              Descrição do sinistro.
        """
        dados = {
            "evento_tipo": VehicleEventType.SINISTRO.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "data_sinistro": data_sinistro,
            "tipo": tipo.upper().strip(),
            "perda_total": False,
            "bo_numero": bo_numero.strip(),
            "delegacia": delegacia.strip(),
            "seguradora": {
                "nome": seguradora_nome.strip(),
                "cnpj": re.sub(r"\D", "", seguradora_cnpj),
                "apolice": seguradora_apolice.strip(),
            },
            "valor_dano": valor_dano,
            "laudo_perito": laudo_perito.strip(),
            "oficina_responsavel": oficina_responsavel.strip(),
            "pecas_danificadas": pecas_danificadas or [],
            "reparado": False,
            "data_conclusao_reparo": "",
            "descricao": descricao.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_data(data_sinistro):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_sinistro}")
        if not bo_numero.strip():
            raise ValueError("Número do BO é obrigatório.")
        tipos_validos = {"COLISAO", "ATROPELAMENTO", "INCENDIO", "ALAGAMENTO", "OUTRO"}
        if tipo.upper().strip() not in tipos_validos:
            raise ValueError(f"Tipo de sinistro inválido: {tipo}. Use: {tipos_validos}")
        return dados

    @staticmethod
    def sinistro_perda_total(
        placa: str,
        data_sinistro: str,
        tipo: str,
        bo_numero: str,
        seguradora_nome: str = "",
        seguradora_cnpj: str = "",
        seguradora_apolice: str = "",
        valor_indenizacao: float = 0.0,
        destino: str = "DESTRUIDO",
        data_baixa_detran: str = "",
        laudo_perito: str = "",
        delegacia: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de SINISTRO COM PERDA TOTAL — destruição total do veículo.

        Args:
            placa:                  Placa do veículo.
            data_sinistro:          Data do sinistro (DD/MM/AAAA).
            tipo:                   COLISAO, INCENDIO, ALAGAMENTO, FURTO_ROUBO, OUTRO.
            bo_numero:              Número do BO.
            seguradora_nome:        Nome da seguradora.
            seguradora_cnpj:        CNPJ da seguradora.
            seguradora_apolice:     Número da apólice.
            valor_indenizacao:      Valor da indenização paga (R$).
            destino:                DESLICHE, FERRO_VELHO, DESTRUIDO, RECICLAGEM.
            data_baixa_detran:      Data da baixa no DETRAN (DD/MM/AAAA).
            laudo_perito:           Laudo do perito.
            delegacia:              Delegacia registradora.
            descricao:              Descrição do sinistro.
        """
        dados = {
            "evento_tipo": VehicleEventType.SINISTRO_PERDA_TOTAL.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "data_sinistro": data_sinistro,
            "tipo": tipo.upper().strip(),
            "perda_total": True,
            "bo_numero": bo_numero.strip(),
            "delegacia": delegacia.strip(),
            "seguradora": {
                "nome": seguradora_nome.strip(),
                "cnpj": re.sub(r"\D", "", seguradora_cnpj),
                "apolice": seguradora_apolice.strip(),
            },
            "valor_indenizacao": valor_indenizacao,
            "destino": destino.upper().strip(),
            "data_baixa_detran": data_baixa_detran,
            "laudo_perito": laudo_perito.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_data(data_sinistro):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_sinistro}")
        if not bo_numero.strip():
            raise ValueError("Número do BO é obrigatório.")
        if data_baixa_detran and not _valida_data(data_baixa_detran):
            raise ValueError(f"Data de baixa DETRAN inválida (DD/MM/AAAA): {data_baixa_detran}")
        destinos_validos = {"DESLICHE", "FERRO_VELHO", "DESTRUIDO", "RECICLAGEM"}
        if destino.upper().strip() not in destinos_validos:
            raise ValueError(f"Destino inválido: {destino}. Use: {destinos_validos}")
        return dados

    @staticmethod
    def troca_peca(
        placa: str,
        peca_nome: str,
        peca_numero_serie: str,
        peca_fabricante: str,
        peca_origem: str,
        data_troca: str,
        oficina_responsavel: str = "",
        mecanico_cpf: str = "",
        motivo: str = "",
        odometro_km: float = 0.0,
        peca_certificado: str = "",
        peca_descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de TROCA DE PEÇA — substituição de componente.

        Args:
            placa:                  Placa do veículo.
            peca_nome:              Nome da peça (ex: "Motor", "Câmbio").
            peca_numero_serie:      Número de série da peça.
            peca_fabricante:        Fabricante da peça.
            peca_origem:            ORIGINAL, GENUINA, REMANUFACTURADA, PARALELA.
            data_troca:             Data da troca (DD/MM/AAAA).
            oficina_responsavel:    Oficina que realizou a troca.
            mecanico_cpf:           CPF do mecânico responsável.
            motivo:                 Motivo da troca.
            odometro_km:            Quilometragem na data da troca.
            peca_certificado:       Certificado de autenticidade.
            peca_descricao:         Descrição complementar da peça.
        """
        dados = {
            "evento_tipo": VehicleEventType.TROCA_PECA.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "peca": {
                "nome": peca_nome.strip(),
                "numero_serie": peca_numero_serie.strip(),
                "fabricante": peca_fabricante.strip(),
                "origem": peca_origem.upper().strip(),
                "certificado": peca_certificado.strip(),
                "descricao": peca_descricao.strip(),
            },
            "data_troca": data_troca,
            "oficina_responsavel": oficina_responsavel.strip(),
            "mecanico_cpf": re.sub(r"\D", "", mecanico_cpf) if mecanico_cpf else "",
            "motivo": motivo.strip(),
            "odometro_km": odometro_km,
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not peca_nome.strip():
            raise ValueError("Nome da peça é obrigatório.")
        if not _valida_data(data_troca):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_troca}")
        origens_validas = {"ORIGINAL", "GENUINA", "REMANUFACTURADA", "PARALELA"}
        if peca_origem.upper().strip() not in origens_validas:
            raise ValueError(f"Origem da peça inválida: {peca_origem}. Use: {origens_validas}")
        return dados

    @staticmethod
    def validacao_peca(
        placa: str,
        peca_nome: str,
        peca_numero_serie: str,
        validador_cpf: str,
        validador_nome: str,
        data_validacao: str,
        resultado: str,
        metodo_validacao: str = "",
        certificado_validacao: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de VALIDAÇÃO DE PEÇA — autenticação de componente.

        Args:
            placa:                      Placa do veículo.
            peca_nome:                  Nome da peça.
            peca_numero_serie:          Número de série da peça.
            validador_cpf:              CPF do validador.
            validador_nome:             Nome do validador.
            data_validacao:             Data da validação (DD/MM/AAAA).
            resultado:                  AUTENTICADA, FALSIFICADA, INCONCLUSIVA.
            metodo_validacao:           Método utilizado na validação.
            certificado_validacao:      Certificado emitido.
            descricao:                  Descrição complementar.
        """
        dados = {
            "evento_tipo": VehicleEventType.VALIDACAO_PECA.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "peca": {
                "nome": peca_nome.strip(),
                "numero_serie": peca_numero_serie.strip(),
            },
            "validador": {
                "cpf": re.sub(r"\D", "", validador_cpf),
                "nome": validador_nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "data_validacao": data_validacao,
            "resultado": resultado.upper().strip(),
            "metodo_validacao": metodo_validacao.strip(),
            "certificado_validacao": certificado_validacao.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not peca_nome.strip():
            raise ValueError("Nome da peça é obrigatório.")
        if not _valida_cpf(validador_cpf):
            raise ValueError(f"CPF do validador inválido: {validador_cpf}")
        if not _valida_data(data_validacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_validacao}")
        resultados_validos = {"AUTENTICADA", "FALSIFICADA", "INCONCLUSIVA"}
        if resultado.upper().strip() not in resultados_validos:
            raise ValueError(f"Resultado inválido: {resultado}. Use: {resultados_validos}")
        return dados

    @staticmethod
    def transferencia_propriedade(
        placa: str,
        novo_proprietario_cpf: str,
        novo_proprietario_nome: str,
        data_transferencia: str,
        documento_tipo: str = "CRV",
        documento_numero: str = "",
        orgao_emissor: str = "DETRAN",
        descricao: str = "",
        odometro_km: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de TRANSFERÊNCIA DE PROPRIEDADE — mudança de titularidade no DETRAN.

        Args:
            placa:                      Placa do veículo.
            novo_proprietario_cpf:      CPF do novo proprietário.
            novo_proprietario_nome:     Nome do novo proprietário.
            data_transferencia:         Data (DD/MM/AAAA).
            documento_tipo:             CRV, RECIBO, ALVARA.
            documento_numero:           Número do documento.
            orgao_emissor:              Órgão emissor.
            descricao:                  Descrição.
            odometro_km:                Quilometragem.
        """
        dados = {
            "evento_tipo": VehicleEventType.TRANSFERENCIA_PROPRIEDADE.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "novo_proprietario": {
                "cpf": re.sub(r"\D", "", novo_proprietario_cpf),
                "nome": novo_proprietario_nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "data_transferencia": data_transferencia,
            "documento_tipo": documento_tipo.upper().strip(),
            "documento_numero": documento_numero.strip(),
            "orgao_emissor": orgao_emissor.strip(),
            "descricao": descricao.strip(),
            "odometro_km": odometro_km,
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_cpf(novo_proprietario_cpf):
            raise ValueError(f"CPF do novo proprietário inválido: {novo_proprietario_cpf}")
        if not _valida_data(data_transferencia):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_transferencia}")
        return dados

    @staticmethod
    def revisao(
        placa: str,
        data_revisao: str,
        oficina_responsavel: str = "",
        mecanico_cpf: str = "",
        tipo_revisao: str = "PREVENTIVA",
        itens_revisados: Optional[list[str]] = None,
        pecas_substituidas: Optional[list[str]] = None,
        odometro_km: float = 0.0,
        proxima_revisao_km: float = 0.0,
        proxima_revisao_data: str = "",
        valor_total: float = 0.0,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de REVISÃO — manutenção programada.

        Args:
            placa:                  Placa do veículo.
            data_revisao:           Data da revisão (DD/MM/AAAA).
            oficina_responsavel:    Oficina.
            mecanico_cpf:           CPF do mecânico.
            tipo_revisao:           PREVENTIVA, CORRETIVA, PREDITIVA.
            itens_revisados:        Lista de itens revisados.
            pecas_substituidas:     Lista de peças substituídas.
            odometro_km:            Quilometragem na revisão.
            proxima_revisao_km:     Próxima revisão por km.
            proxima_revisao_data:   Próxima revisão por data.
            valor_total:            Valor total da revisão.
            descricao:              Descrição.
        """
        dados = {
            "evento_tipo": VehicleEventType.REVISAO.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "data_revisao": data_revisao,
            "oficina_responsavel": oficina_responsavel.strip(),
            "mecanico_cpf": re.sub(r"\D", "", mecanico_cpf) if mecanico_cpf else "",
            "tipo_revisao": tipo_revisao.upper().strip(),
            "itens_revisados": itens_revisados or [],
            "pecas_substituidas": pecas_substituidas or [],
            "odometro_km": odometro_km,
            "proxima_revisao_km": proxima_revisao_km,
            "proxima_revisao_data": proxima_revisao_data,
            "valor_total": valor_total,
            "descricao": descricao.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_data(data_revisao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_revisao}")
        return dados

    @staticmethod
    def licenciamento(
        placa: str,
        ano_licenciamento: int,
        data_licenciamento: str,
        orgao_emissor: str = "DETRAN",
        doc_numero: str = "",
        ipva_pago: bool = True,
        valor_ipva: float = 0.0,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de LICENCIAMENTO — renovação anual.

        Args:
            placa:                  Placa do veículo.
            ano_licenciamento:      Ano do licenciamento.
            data_licenciamento:     Data (DD/MM/AAAA).
            orgao_emissor:          Órgão emissor (DETRAN).
            doc_numero:             Número do documento.
            ipva_pago:              Se o IPVA foi pago.
            valor_ipva:             Valor do IPVA.
            descricao:              Descrição.
        """
        dados = {
            "evento_tipo": VehicleEventType.LICENCIAMENTO.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "ano_licenciamento": ano_licenciamento,
            "data_licenciamento": data_licenciamento,
            "orgao_emissor": orgao_emissor.strip(),
            "doc_numero": doc_numero.strip(),
            "ipva_pago": ipva_pago,
            "valor_ipva": valor_ipva,
            "descricao": descricao.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_data(data_licenciamento):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_licenciamento}")
        return dados

    @staticmethod
    def mudanca_cor(
        placa: str,
        cor_anterior: str,
        cor_nova: str,
        data_mudanca: str,
        doc_numero: str = "",
        orgao_emissor: str = "DETRAN",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de MUDANÇA DE COR — alteração de cor registrada no DETRAN.

        Args:
            placa:              Placa do veículo.
            cor_anterior:       Cor anterior.
            cor_nova:           Nova cor.
            data_mudanca:       Data (DD/MM/AAAA).
            doc_numero:         Número do documento.
            orgao_emissor:      Órgão emissor.
            descricao:          Descrição.
        """
        dados = {
            "evento_tipo": VehicleEventType.MUDANCA_COR.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "cor_anterior": cor_anterior.strip(),
            "cor_nova": cor_nova.strip(),
            "data_mudanca": data_mudanca,
            "doc_numero": doc_numero.strip(),
            "orgao_emissor": orgao_emissor.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not cor_nova.strip():
            raise ValueError("Nova cor é obrigatória.")
        if not _valida_data(data_mudanca):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_mudanca}")
        return dados

    @staticmethod
    def baixa(
        placa: str,
        data_baixa: str,
        motivo: str,
        orgao_emissor: str = "DETRAN",
        doc_numero: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de BAIXA — baixa definitiva do veículo.

        Args:
            placa:              Placa do veículo.
            data_baixa:         Data (DD/MM/AAAA).
            motivo:             Motivo: PERDA_TOTAL, FURTO_NAO_RECUPERADO, DESMANCHE, SUCATA, OUTRO.
            orgao_emissor:      Órgão emissor.
            doc_numero:         Número do documento.
            descricao:          Descrição.
        """
        dados = {
            "evento_tipo": VehicleEventType.BAIXA.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "data_baixa": data_baixa,
            "motivo": motivo.upper().strip(),
            "orgao_emissor": orgao_emissor.strip(),
            "doc_numero": doc_numero.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_data(data_baixa):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_baixa}")
        if not motivo.strip():
            raise ValueError("Motivo da baixa é obrigatório.")
        return dados

    @staticmethod
    def recall_fabrica(
        placa: str,
        data_notificacao: str,
        fabricante_nome: str,
        fabricante_cnpj: str,
        numero_recall: str,
        peca_defeituosa: str,
        descricao_defeito: str,
        risco: str = "MEDIO",
        lote_inicio: str = "",
        lote_fim: str = "",
        ano_fabricacao_inicio: int = 0,
        ano_fabricacao_fim: int = 0,
        solucao: str = "",
        oficina_autorizada: str = "",
        prazo_conclusao: str = "",
        custo_para_proprietario: float = 0.0,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de RECALL DE FÁBRICA — chamada de volta por defeito de fabricação.

        Args:
                    placa:                  Placa do veículo.
                    data_notificacao:       Data de notificação do recall (DD/MM/AAAA).
                    fabricante_nome:        Nome do fabricante.
                    fabricante_cnpj:        CNPJ do fabricante.
                    numero_recall:          Número do recall (ex: "RC-2024-001").
                    peca_defeituosa:        Peça componente com defeito.
                    descricao_defeito:      Descrição do defeito.
                    risco:                  BAIXO, MEDIO, ALTO, CRITICO.
                    lote_inicio:            Lote inicial afetado.
                    lote_fim:               Lote final afetado.
                    ano_fabricacao_inicio:   Ano inicial da faixa afetada.
                    ano_fabricacao_fim:      Ano final da faixa afetada.
                    solucao:                Solução oferecida (reposição, reparo, atualização).
                    oficina_autorizada:     Oficina autorizada pelo fabricante.
                    prazo_conclusao:        Prazo para conclusão do recall (DD/MM/AAAA).
                    custo_para_proprietario: Custo para o proprietário (0 = gratuito).
                    descricao:              Descrição complementar.
        """
        dados = {
            "evento_tipo": VehicleEventType.RECALL_DE_FABRICA.value,
            "placa": re.sub(r"[-\s]", "", placa.upper()),
            "data_notificacao": data_notificacao,
            "fabricante": {
                "nome": fabricante_nome.strip(),
                "cnpj": re.sub(r"\D", "", fabricante_cnpj),
            },
            "numero_recall": numero_recall.strip(),
            "peca_defeituosa": peca_defeituosa.strip(),
            "descricao_defeito": descricao_defeito.strip(),
            "risco": risco.upper().strip(),
            "lote_inicio": lote_inicio.strip(),
            "lote_fim": lote_fim.strip(),
            "ano_fabricacao_inicio": ano_fabricacao_inicio,
            "ano_fabricacao_fim": ano_fabricacao_fim,
            "solucao": solucao.strip(),
            "oficina_autorizada": oficina_autorizada.strip(),
            "prazo_conclusao": prazo_conclusao,
            "custo_para_proprietario": custo_para_proprietario,
            "descricao": descricao.strip(),
            "status": "PENDENTE",  # PENDENTE, EM_EXECUCAO, CONCLUIDO, REJEITADO
            "data_conclusao": "",
        }
        # Validações
        if not _valida_placa(placa):
            raise ValueError(f"Placa inválida: {placa}")
        if not _valida_data(data_notificacao):
            raise ValueError(f"Data de notificação inválida (DD/MM/AAAA): {data_notificacao}")
        if not fabricante_nome.strip():
            raise ValueError("Nome do fabricante é obrigatório.")
        if not _valida_cnpj(fabricante_cnpj):
            raise ValueError(f"CNPJ do fabricante inválido: {fabricante_cnpj}")
        if not numero_recall.strip():
            raise ValueError("Número do recall é obrigatório.")
        if not peca_defeituosa.strip():
            raise ValueError("Peça defeituosa é obrigatória.")
        if not descricao_defeito.strip():
            raise ValueError("Descrição do defeito é obrigatória.")
        riscos_validos = {"BAIXO", "MEDIO", "ALTO", "CRITICO"}
        if risco.upper().strip() not in riscos_validos:
            raise ValueError(f"Nível de risco inválido: {risco}. Use: {riscos_validos}")
        if prazo_conclusao and not _valida_data(prazo_conclusao):
            raise ValueError(f"Prazo de conclusão inválido (DD/MM/AAAA): {prazo_conclusao}")
        if custo_para_proprietario < 0:
            raise ValueError(f"Custo para o proprietário não pode ser negativo: {custo_para_proprietario}")
        return dados


# ── Protetor de Cadeia ────────────────────────────────────────────────


class VehicleChainProtector:
    """
    Impede adição de eventos que não fazem sentido
    em certos estados do veículo.
    """

    # Estado → Eventos bloqueados
    BLOQUEADOS: dict[str, set[str]] = {
        "EM_LEILAO": {
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventType.DOACAO.value,
            VehicleEventType.GARANTIA_EMPRESTIMO.value,
        },
        "GARANTIDO": {
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventType.DOACAO.value,
            VehicleEventType.LEILAO.value,
        },
        "CONFISCADO": {
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventType.DOACAO.value,
            VehicleEventType.LEILAO.value,
            VehicleEventType.GARANTIA_EMPRESTIMO.value,
        },
        "PERDA_TOTAL": {
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventType.DOACAO.value,
            VehicleEventType.GARANTIA_EMPRESTIMO.value,
            VehicleEventType.TROCA_PECA.value,
            VehicleEventType.REVISAO.value,
        },
        "BAIXADO": set(VehicleEventType),  # Tudo bloqueado
    }

    @staticmethod
    def pode_adicionar(event_type: str, estado_atual: str) -> bool:
        """
        Verifica se um evento pode ser adicionado ao veículo.

        Args:
            event_type:     Tipo do evento.
            estado_atual:   Estado atual do veículo.

        Returns:
            True se o evento pode ser adicionado.
        """
        bloqueados = VehicleChainProtector.BLOQUEADOS.get(estado_atual, set())
        return event_type not in bloqueados
