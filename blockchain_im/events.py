"""
blockchain_im/events.py
Definições e validadores para eventos de imóveis.
Cada evento representa uma mudança na situação jurídica,
física ou financeira de um imóvel no espaço geográfico real.
"""

import re
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional
from blockchain_pf.geografia_br import validar_cidade


# ── Enum de tipos de evento ────────────────────────────────────────────

class PropertyEventType(str, Enum):
    """Todos os tipos de evento de imóvel suportados."""

    # ── Gênesis ──────────────────────────────────────────────────────
    TERRENO          = "TERRENO"              # Cadastro do terreno bruto

    # ── Estruturais ──────────────────────────────────────────────────
    CONSTRUCAO       = "CONSTRUCAO"           # Nova construção
    DEMOLICAO        = "DEMOLICAO"            # Demolição de construção
    REFORMA          = "REFORMA"              # Reforma (ampliação/redução)
    LOTEAMENTO       = "LOTEAMENTO"           # Subdivisão em lotes
    DESMEMBRAMENTO   = "DESMEMBRAMENTO"       # Divisão legal (novas matrículas)
    FUSAO            = "FUSAO"                # União de imóveis

    # ── Transferência ────────────────────────────────────────────────
    COMPRA_VENDA     = "COMPRA_VENDA"         # Transferência com pagamento
    DOACAO           = "DOACAO"               # Transferência sem pagamento
    HERANCA          = "HERANCA"              # Transferência por inventário
    PERMUTA          = "PERMUTA"              # Troca de imóveis
    CONFISCO         = "CONFISCO"             # Apreensão judicial

    # ── Financeiro ───────────────────────────────────────────────────
    GARANTIA         = "GARANTIA"             # Hipoteca / garantia
    QUITACAO         = "QUITACAO"             # Baixa de garantia
    LEILAO           = "LEILAO"               # Leilão
    PENHORA          = "PENHORA"              # Penhora judicial

    # ── Administrativo ───────────────────────────────────────────────
    MATRICULA        = "MATRICULA"            # Atualização de matrícula
    CERTIDAO         = "CERTIDAO"             # Certidão emitida
    IPTU             = "IPTU"                 # Alteração de IPTU
    ZONEAMENTO       = "ZONEAMENTO"           # Mudança de zoneamento

    # ── Cross-chain ──────────────────────────────────────────────────
    PROPRIETARIO     = "PROPRIETARIO"         # Adição/remoção de proprietário
    GARANTIA_PESSOA  = "GARANTIA_PESSOA"      # Garantia vinculada a pessoa


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
        "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS",
        "MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC",
        "SP","SE","TO"
    }
    return uf.upper() in ufs

def _valida_matricula(matricula: str) -> bool:
    """Validação básica de matrícula (não vazia, alfanumérica)."""
    return bool(matricula and matricula.strip())

def _valida_coordenadas(lat: float, lon: float) -> bool:
    """Valida coordenadas geográficas."""
    return -90 <= lat <= 90 and -180 <= lon <= 180


# ── Fábricas de eventos ───────────────────────────────────────────────

class PropertyEventFactory:
    """
    Fábrica para criar eventos validados de imóveis.
    Cada método retorna um dict pronto para ir ao bloco.
    """

    @staticmethod
    def terreno(
        matricula: str,
        endereco_logradouro: str,
        endereco_bairro: str,
        endereco_cidade: str,
        endereco_uf: str,
        endereco_cep: str,
        lat: float,
        lon: float,
        area_terreno_m2: float,
        metragem_frente: float = 0.0,
        metragem_fundo: float = 0.0,
        metragem_lado_esq: float = 0.0,
        metragem_lado_dir: float = 0.0,
        zoneamento: str = "",
        uso_permitido: Optional[list[str]] = None,
        altura_maxima: float = 0.0,
        taxa_ocupacao: float = 0.0,
        cacau_permitido: float = 0.0,
        codigo_iptu: str = "",
        proprietarios: Optional[list[dict]] = None,
        datum: str = "SIRGAS 2000",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de TERRENO (bloco gênesis).
        Cadastra o terreno bruto no espaço geográfico real.

        Args:
            matricula:           Número da matrícula no cartório.
            endereco_logradouro: Rua, avenida, etc.
            endereco_bairro:     Bairro.
            endereco_cidade:     Cidade.
            endereco_uf:         UF.
            endereco_cep:        CEP.
            lat:                 Latitude.
            lon:                 Longitude.
            area_terreno_m2:     Área total do terreno em m².
            metragem_frente:     Metragem da frente.
            metragem_fundo:      Metragem do fundo.
            metragem_lado_esq:   Metragem do lado esquerdo.
            metragem_lado_dir:   Metrigem do lado direito.
            zoneamento:          Código de zoneamento (ex: "ZER-2").
            uso_permitido:       Lista de usos permitidos.
            altura_maxima:       Altura máxima permitida (metros).
            taxa_ocupacao:       Taxa de ocupação (0.0 a 1.0).
            cacau_permitido:     Coeficiente de Aproveitamento Total.
            codigo_iptu:         Código IPTU.
            proprietarios:       Lista de proprietários iniciais.
            datum:               Datum geodésico (padrão SIRGAS 2000).
        """
        dados = {
            "evento_tipo": PropertyEventType.TERRENO.value,
            "matricula": matricula.strip(),
            "endereco": {
                "logradouro": endereco_logradouro.strip(),
                "bairro": endereco_bairro.strip(),
                "cidade": endereco_cidade.strip(),
                "uf": endereco_uf.upper(),
                "cep": endereco_cep.strip(),
            },
            "coordenadas": {
                "lat": lat,
                "lon": lon,
                "datum": datum,
            },
            "area_terreno_m2": area_terreno_m2,
            "area_construida_m2": 0.0,
            "metragem_frente": metragem_frente,
            "metragem_fundo": metragem_fundo,
            "metragem_lado_esq": metragem_lado_esq,
            "metragem_lado_dir": metragem_lado_dir,
            "zoneamento": zoneamento.strip(),
            "uso_permitido": uso_permitido or [],
            "altura_maxima": altura_maxima,
            "taxa_ocupacao": taxa_ocupacao,
            "cacau_permitido": cacau_permitido,
            "codigo_iptu": codigo_iptu.strip(),
            "situacao": "LIVRE",
            "proprietarios": proprietarios or [],
            "onus_reais": [],
            "certidoes": [],
        }
        # Validações
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not endereco_logradouro.strip():
            raise ValueError("Logradouro é obrigatório.")
        if not _valida_uf(endereco_uf):
            raise ValueError(f"UF inválida: {endereco_uf}")
        if not _valida_coordenadas(lat, lon):
            raise ValueError(f"Coordenadas inválidas: lat={lat}, lon={lon}")
        if area_terreno_m2 <= 0:
            raise ValueError(f"Área do terreno deve ser positiva: {area_terreno_m2}")
        if not validar_cidade(endereco_uf, endereco_cidade):
            raise ValueError(f"Local inválido: {endereco_cidade}/{endereco_uf}. Cidade deve existir na tabela oficial (IBGE).")
        return dados

    @staticmethod
    def construcao(
        matricula: str,
        descricao: str,
        area_construida_m2: float,
        tipo_construcao: str = "RESIDENCIAL",
        pavimentos: int = 1,
        data_inicio: str = "",
        data_fim: str = "",
        responsavel_tecnico: str = "",
       CRECI: str = "",
        alvara_numero: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de CONSTRUÇÃO — nova edificação no terreno.

        Args:
            matricula:              Matrícula do imóvel.
            descricao:              Descrição da construção.
            area_construida_m2:     Área construída em m².
            tipo_construcao:        RESIDENCIAL, COMERCIAL, MISTO, INDUSTRIAL.
            pavimentos:             Número de pavimentos.
            data_inicio:            Data de início (DD/MM/AAAA).
            data_fim:               Data de conclusão (DD/MM/AAAA).
            responsavel_tecnico:    Engenheiro/arquiteto responsável.
            CRECI:                  Registro profissional.
            alvara_numero:          Número do alvará de construção.
        """
        dados = {
            "evento_tipo": PropertyEventType.CONSTRUCAO.value,
            "matricula": matricula.strip(),
            "descricao": descricao.strip(),
            "area_construida_m2": area_construida_m2,
            "tipo_construcao": tipo_construcao.upper(),
            "pavimentos": pavimentos,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "responsavel_tecnico": responsavel_tecnico.strip(),
            "CRECI": CRECI.strip(),
            "alvara_numero": alvara_numero.strip(),
            "situacao_obra": "CONCLUIDA" if data_fim else "EM_OBRA",
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not descricao.strip():
            raise ValueError("Descrição da construção é obrigatória.")
        if area_construida_m2 <= 0:
            raise ValueError(f"Área construída deve ser positiva: {area_construida_m2}")
        if data_inicio and not _valida_data(data_inicio):
            raise ValueError(f"Data de início inválida (DD/MM/AAAA): {data_inicio}")
        if data_fim and not _valida_data(data_fim):
            raise ValueError(f"Data de conclusão inválida (DD/MM/AAAA): {data_fim}")
        return dados

    @staticmethod
    def demolicao(
        matricula: str,
        descricao: str,
        area_demolida_m2: float,
        motivo: str = "",
        data_demolicao: str = "",
        responsavel_tecnico: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de DEMOLIÇÃO — remoção de construção existente.

        Args:
            matricula:              Matrícula do imóvel.
            descricao:              O que foi demolido.
            area_demolida_m2:       Área demolida em m².
            motivo:                 Motivo da demolição.
            data_demolicao:         Data (DD/MM/AAAA).
            responsavel_tecnico:    Engenheiro responsável.
        """
        dados = {
            "evento_tipo": PropertyEventType.DEMOLICAO.value,
            "matricula": matricula.strip(),
            "descricao": descricao.strip(),
            "area_demolida_m2": area_demolida_m2,
            "motivo": motivo.strip(),
            "data_demolicao": data_demolicao,
            "responsavel_tecnico": responsavel_tecnico.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not descricao.strip():
            raise ValueError("Descrição da demolição é obrigatória.")
        if area_demolida_m2 <= 0:
            raise ValueError(f"Área demolida deve ser positiva: {area_demolida_m2}")
        if data_demolicao and not _valida_data(data_demolicao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_demolicao}")
        return dados

    @staticmethod
    def reforma(
        matricula: str,
        descricao: str,
        tipo: str,
        area_anterior_m2: float,
        area_nova_m2: float,
        data_inicio: str = "",
        data_fim: str = "",
        responsavel_tecnico: str = "",
        alvara_numero: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de REFORMA — ampliação ou redução de área construída.

        Args:
            matricula:              Matrícula do imóvel.
            descricao:              Descrição da reforma.
            tipo:                   AMPLIACAO ou REDUCAO.
            area_anterior_m2:       Área antes da reforma.
            area_nova_m2:           Área após a reforma.
            data_inicio:            Data de início (DD/MM/AAAA).
            data_fim:               Data de conclusão (DD/MM/AAAA).
            responsavel_tecnico:    Engenheiro/arquiteto.
            alvara_numero:          Número do alvará.
        """
        if tipo.upper() not in ("AMPLIACAO", "REDUCAO"):
            raise ValueError(f"Tipo de reforma inválido: {tipo}. Use AMPLIACAO ou REDUCAO.")
        dados = {
            "evento_tipo": PropertyEventType.REFORMA.value,
            "matricula": matricula.strip(),
            "descricao": descricao.strip(),
            "tipo": tipo.upper(),
            "area_anterior_m2": area_anterior_m2,
            "area_nova_m2": area_nova_m2,
            "delta_area_m2": area_nova_m2 - area_anterior_m2,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "responsavel_tecnico": responsavel_tecnico.strip(),
            "alvara_numero": alvara_numero.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not descricao.strip():
            raise ValueError("Descrição da reforma é obrigatória.")
        if area_anterior_m2 < 0:
            raise ValueError(f"Área anterior não pode ser negativa: {area_anterior_m2}")
        if area_nova_m2 < 0:
            raise ValueError(f"Área nova não pode ser negativa: {area_nova_m2}")
        if data_inicio and not _valida_data(data_inicio):
            raise ValueError(f"Data de início inválida (DD/MM/AAAA): {data_inicio}")
        if data_fim and not _valida_data(data_fim):
            raise ValueError(f"Data de conclusão inválida (DD/MM/AAAA): {data_fim}")
        return dados

    @staticmethod
    def desmembramento(
        matricula_origem: str,
        novas_matriculas: list[dict],
        area_total_anterior: float,
        descricao: str = "",
        data: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de DESMEMBRAMENTO — divisão legal do imóvel.

        Cria novas matrículas a partir de uma existente.

        Args:
            matricula_origem:       Matrícula original.
            novas_matriculas:       Lista de novas matrículas criadas.
                                    Cada uma: {"matricula": "...", "area_m2": ..., "endereco": ...}
            area_total_anterior:    Área total antes do desmembramento.
            descricao:              Descrição do desmembramento.
            data:                   Data do ato (DD/MM/AAAA).
        """
        dados = {
            "evento_tipo": PropertyEventType.DESMEMBRAMENTO.value,
            "matricula_origem": matricula_origem.strip(),
            "novas_matriculas": novas_matriculas,
            "quantidade_lotes": len(novas_matriculas),
            "area_total_anterior_m2": area_total_anterior,
            "area_total_nova_m2": sum(m.get("area_m2", 0) for m in novas_matriculas),
            "descricao": descricao.strip(),
            "data": data,
        }
        if not _valida_matricula(matricula_origem):
            raise ValueError("Matrícula de origem é obrigatória.")
        if not novas_matriculas:
            raise ValueError("Pelo menos uma nova matrícula deve ser criada.")
        if data and not _valida_data(data):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data}")
        return dados

    @staticmethod
    def fusao(
        matriculas_origem: list[str],
        nova_matricula: str,
        area_total_m2: float,
        endereco: str = "",
        descricao: str = "",
        data: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de FUSÃO — união de dois ou mais imóveis em um.

        Args:
            matriculas_origem:  Lista de matrículas que serão fundidas.
            nova_matricula:     Nova matrícula resultante.
            area_total_m2:      Área total resultante.
            endereco:           Novo endereço (se aplicável).
            descricao:          Descrição da fusão.
            data:               Data do ato (DD/MM/AAAA).
        """
        dados = {
            "evento_tipo": PropertyEventType.FUSAO.value,
            "matriculas_origem": matriculas_origem,
            "nova_matricula": nova_matricula.strip(),
            "quantidade_imoveis": len(matriculas_origem),
            "area_total_m2": area_total_m2,
            "endereco": endereco.strip(),
            "descricao": descricao.strip(),
            "data": data,
        }
        if len(matriculas_origem) < 2:
            raise ValueError("Fusão requer pelo menos 2 imóveis.")
        if not _valida_matricula(nova_matricula):
            raise ValueError("Nova matrícula é obrigatória.")
        if data and not _valida_data(data):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data}")
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
        escritura_numero: str = "",
        cartorio: str = "",
        regime_bens: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de COMPRA/VENDA — transferência com pagamento.

        Args:
            matricula:          Matrícula do imóvel.
            comprador_cpf:      CPF do comprador.
            comprador_nome:     Nome do comprador.
            vendedor_cpf:       CPF do vendedor.
            vendedor_nome:      Nome do vendedor.
            valor_transacao:    Valor da transação (R$).
            data_transacao:     Data (DD/MM/AAAA).
            escritura_numero:   Número da escritura.
            cartorio:           Cartório onde foi lavrada.
            regime_bens:        Regime de bens (se casado).
        """
        dados = {
            "evento_tipo": PropertyEventType.COMPRA_VENDA.value,
            "matricula": matricula.strip(),
            "comprador": {
                "cpf": re.sub(r"\D", "", comprador_cpf),
                "nome": comprador_nome.strip(),
                "hash_cadeia_pessoa": "",  # Preenchido pelo CrossChainManager
            },
            "vendedor": {
                "cpf": re.sub(r"\D", "", vendedor_cpf),
                "nome": vendedor_nome.strip(),
                "hash_cadeia_pessoa": "",  # Preenchido pelo CrossChainManager
            },
            "valor_transacao": valor_transacao,
            "data_transacao": data_transacao,
            "escritura_numero": escritura_numero.strip(),
            "cartorio": cartorio.strip(),
            "regime_bens": regime_bens.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
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
        matricula: str,
        donatario_cpf: str,
        donatario_nome: str,
        doador_cpf: str,
        doador_nome: str,
        data_doacao: str,
        motivo: str = "",
        escritura_numero: str = "",
        cartorio: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de DOAÇÃO — transferência sem pagamento.

        Args:
            matricula:          Matrícula do imóvel.
            donatario_cpf:      CPF do donatário (quem recebe).
            donatario_nome:     Nome do donatário.
            doador_cpf:         CPF do doador (quem doa).
            doador_nome:        Nome do doador.
            data_doacao:        Data (DD/MM/AAAA).
            motivo:             Motivo da doação.
            escritura_numero:   Número da escritura.
            cartorio:           Cartório.
        """
        dados = {
            "evento_tipo": PropertyEventType.DOACAO.value,
            "matricula": matricula.strip(),
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
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_cpf(donatario_cpf):
            raise ValueError(f"CPF do donatário inválido: {donatario_cpf}")
        if not _valida_cpf(doador_cpf):
            raise ValueError(f"CPF do doador inválido: {doador_cpf}")
        if not _valida_data(data_doacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_doacao}")
        return dados

    @staticmethod
    def heranca(
        matricula: str,
        inventariado_cpf: str,
        inventariado_nome: str,
        herdeiros: list[dict],
        data_obito: str,
        data_inventario: str = "",
        inventario_tipo: str = "JUDICIAL",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de HERANÇA — transferência por inventário.

        Args:
            matricula:          Matrícula do imóvel.
            inventariado_cpf:   CPF do falecido.
            inventariado_nome:  Nome do falecido.
            herdeiros:          Lista de herdeiros: [{"cpf": ..., "nome": ..., "participacao": ...}]
            data_obito:         Data do óbito (DD/MM/AAAA).
            data_inventario:    Data do inventário (DD/MM/AAAA).
            inventario_tipo:    JUDICIAL ou EXTRAJUDICIAL.
            descricao:          Descrição complementar.
        """
        dados = {
            "evento_tipo": PropertyEventType.HERANCA.value,
            "matricula": matricula.strip(),
            "inventariado": {
                "cpf": re.sub(r"\D", "", inventariado_cpf),
                "nome": inventariado_nome.strip(),
            },
            "herdeiros": herdeiros,
            "data_obito": data_obito,
            "data_inventario": data_inventario,
            "inventario_tipo": inventario_tipo.upper(),
            "descricao": descricao.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_cpf(inventariado_cpf):
            raise ValueError(f"CPF do inventariado inválido: {inventariado_cpf}")
        if not herdeiros:
            raise ValueError("Pelo menos um herdeiro deve ser informado.")
        if not _valida_data(data_obito):
            raise ValueError(f"Data de óbito inválida (DD/MM/AAAA): {data_obito}")
        if data_inventario and not _valida_data(data_inventario):
            raise ValueError(f"Data de inventário inválida (DD/MM/AAAA): {data_inventario}")
        return dados

    @staticmethod
    def permuta(
        matricula_imovel_a: str,
        matricula_imovel_b: str,
        proprietario_a_cpf: str,
        proprietario_a_nome: str,
        proprietario_b_cpf: str,
        proprietario_b_nome: str,
        data_permuta: str,
        valor_troco_a: float = 0.0,
        valor_troco_b: float = 0.0,
        escritura_numero: str = "",
        cartorio: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de PERMUTA — troca de imóveis entre duas partes.

        Args:
            matricula_imovel_a: Matrícula do imóvel A.
            matricula_imovel_b: Matrícula do imóvel B.
            proprietario_a_cpf: CPF do proprietário do imóvel A.
            proprietario_a_nome: Nome do proprietário A.
            proprietario_b_cpf: CPF do proprietário do imóvel B.
            proprietario_b_nome: Nome do proprietário B.
            data_permuta:       Data (DD/MM/AAAA).
            valor_troco_a:      Valor de troco dado pelo proprietário A.
            valor_troco_b:      Valor de troco dado pelo proprietário B.
            escritura_numero:   Número da escritura.
            cartorio:           Cartório.
        """
        dados = {
            "evento_tipo": PropertyEventType.PERMUTA.value,
            "matricula_imovel_a": matricula_imovel_a.strip(),
            "matricula_imovel_b": matricula_imovel_b.strip(),
            "proprietario_a": {
                "cpf": re.sub(r"\D", "", proprietario_a_cpf),
                "nome": proprietario_a_nome.strip(),
            },
            "proprietario_b": {
                "cpf": re.sub(r"\D", "", proprietario_b_cpf),
                "nome": proprietario_b_nome.strip(),
            },
            "data_permuta": data_permuta,
            "valor_troco_a": valor_troco_a,
            "valor_troco_b": valor_troco_b,
            "escritura_numero": escritura_numero.strip(),
            "cartorio": cartorio.strip(),
        }
        if not _valida_matricula(matricula_imovel_a):
            raise ValueError("Matrícula do imóvel A é obrigatória.")
        if not _valida_matricula(matricula_imovel_b):
            raise ValueError("Matrícula do imóvel B é obrigatória.")
        if not _valida_cpf(proprietario_a_cpf):
            raise ValueError(f"CPF do proprietário A inválido: {proprietario_a_cpf}")
        if not _valida_cpf(proprietario_b_cpf):
            raise ValueError(f"CPF do proprietário B inválido: {proprietario_b_cpf}")
        if not _valida_data(data_permuta):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_permuta}")
        return dados

    @staticmethod
    def confisco(
        matricula: str,
        autoridade: str,
        processo_numero: str,
        data_confisco: str,
        motivo: str = "",
        destino: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de CONFISCO — apreensão judicial do imóvel.

        Args:
            matricula:          Matrícula do imóvel.
            autoridade:         Autoridade que decretou.
            processo_numero:    Número do processo.
            data_confisco:      Data (DD/MM/AAAA).
            motivo:             Motivo do confisco.
            destino:            Destino do imóvel confiscado.
        """
        dados = {
            "evento_tipo": PropertyEventType.CONFISCO.value,
            "matricula": matricula.strip(),
            "autoridade": autoridade.strip(),
            "processo_numero": processo_numero.strip(),
            "data_confisco": data_confisco,
            "motivo": motivo.strip(),
            "destino": destino.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_data(data_confisco):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_confisco}")
        return dados

    @staticmethod
    def garantia(
        matricula: str,
        credor_nome: str,
        credor_cnpj: str,
        valor_garantia: float,
        data_garantia: str,
        data_vencimento: str,
        tipo_garantia: str = "HIPOTECARIA",
        taxa_juros: float = 0.0,
        prazo_meses: int = 0,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de GARANTIA — hipoteca ou garantia real sobre o imóvel.

        Args:
            matricula:          Matrícula do imóvel.
            credor_nome:        Nome do credor (banco, financeira).
            credor_cnpj:        CNPJ do credor.
            valor_garantia:     Valor da garantia (R$).
            data_garantia:      Data da garantia (DD/MM/AAAA).
            data_vencimento:    Data de vencimento (DD/MM/AAAA).
            tipo_garantia:      HIPOTECARIA, ALIENACAO_FIDUCIARIA, PENHOR.
            taxa_juros:         Taxa de juros anual (%).
            prazo_meses:        Prazo em meses.
            descricao:          Descrição do empréstimo.
        """
        dados = {
            "evento_tipo": PropertyEventType.GARANTIA.value,
            "matricula": matricula.strip(),
            "credor": {
                "nome": credor_nome.strip(),
                "cnpj": credor_cnpj.strip(),
            },
            "valor_garantia": valor_garantia,
            "data_garantia": data_garantia,
            "data_vencimento": data_vencimento,
            "tipo_garantia": tipo_garantia.upper(),
            "taxa_juros": taxa_juros,
            "prazo_meses": prazo_meses,
            "descricao": descricao.strip(),
            "status": "ATIVA",
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not credor_nome.strip():
            raise ValueError("Nome do credor é obrigatório.")
        if valor_garantia <= 0:
            raise ValueError(f"Valor da garantia deve ser positivo: {valor_garantia}")
        if not _valida_data(data_garantia):
            raise ValueError(f"Data de garantia inválida (DD/MM/AAAA): {data_garantia}")
        if not _valida_data(data_vencimento):
            raise ValueError(f"Data de vencimento inválida (DD/MM/AAAA): {data_vencimento}")
        return dados

    @staticmethod
    def quitacao(
        matricula: str,
        garantia_index: int,
        data_quitacao: str,
        valor_pago: float = 0.0,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de QUITAÇÃO — baixa de garantia/hipoteca.

        Args:
            matricula:          Matrícula do imóvel.
            garantia_index:     Índice da garantia a quitar (no onus_reais).
            data_quitacao:      Data (DD/MM/AAAA).
            valor_pago:         Valor total pago.
            descricao:          Descrição.
        """
        dados = {
            "evento_tipo": PropertyEventType.QUITACAO.value,
            "matricula": matricula.strip(),
            "garantia_index": garantia_index,
            "data_quitacao": data_quitacao,
            "valor_pago": valor_pago,
            "descricao": descricao.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_data(data_quitacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_quitacao}")
        return dados

    @staticmethod
    def leilao(
        matricula: str,
        data_leilao: str,
        valor_minimo: float,
        lance_vencedor: float = 0.0,
        vencedor_cpf: str = "",
        vencedor_nome: str = "",
        leiloeiro: str = "",
        processo_numero: str = "",
        tipo: str = "JUDICIAL",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de LEILÃO — venda judicial ou extrajudicial.

        Args:
            matricula:          Matrícula do imóvel.
            data_leilao:        Data do leilão (DD/MM/AAAA).
            valor_minimo:       Valor mínimo (R$).
            lance_vencedor:     Lance vencedor (R$).
            vencedor_cpf:       CPF do vencedor.
            vencedor_nome:      Nome do vencedor.
            leiloeiro:          Nome do leiloeiro.
            processo_numero:    Número do processo (se judicial).
            tipo:               JUDICIAL ou EXTRAJUDICIAL.
            descricao:          Descrição.
        """
        dados = {
            "evento_tipo": PropertyEventType.LEILAO.value,
            "matricula": matricula.strip(),
            "data_leilao": data_leilao,
            "valor_minimo": valor_minimo,
            "lance_vencedor": lance_vencedor,
            "vencedor": {
                "cpf": re.sub(r"\D", "", vencedor_cpf) if vencedor_cpf else "",
                "nome": vencedor_nome.strip(),
            },
            "leiloeiro": leiloeiro.strip(),
            "processo_numero": processo_numero.strip(),
            "tipo": tipo.upper(),
            "descricao": descricao.strip(),
            "status": "CONCLUIDO" if lance_vencedor > 0 else "AGUARDANDO",
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_data(data_leilao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_leilao}")
        if valor_minimo <= 0:
            raise ValueError(f"Valor mínimo deve ser positivo: {valor_minimo}")
        return dados

    @staticmethod
    def penhora(
        matricula: str,
        autoridade: str,
        processo_numero: str,
        data_penhora: str,
        valor_penhorado: float,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de PENHORA — penhora judicial do imóvel.

        Args:
            matricula:          Matrícula do imóvel.
            autoridade:         Autoridade judicial.
            processo_numero:    Número do processo.
            data_penhora:       Data (DD/MM/AAAA).
            valor_penhorado:    Valor penhorado (R$).
            descricao:          Descrição.
        """
        dados = {
            "evento_tipo": PropertyEventType.PENHORA.value,
            "matricula": matricula.strip(),
            "autoridade": autoridade.strip(),
            "processo_numero": processo_numero.strip(),
            "data_penhora": data_penhora,
            "valor_penhorado": valor_penhorado,
            "descricao": descricao.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_data(data_penhora):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_penhora}")
        return dados

    @staticmethod
    def matricula(
        matricula: str,
        nova_matricula: str,
        data: str,
        motivo: str = "",
        cartorio: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de MATRÍCULA — atualização de registro imobiliário.

        Args:
            matricula:      Matrícula atual.
            nova_matricula: Nova matrícula.
            data:           Data (DD/MM/AAAA).
            motivo:         Motivo da atualização.
            cartorio:       Cartório responsável.
        """
        dados = {
            "evento_tipo": PropertyEventType.MATRICULA.value,
            "matricula": matricula.strip(),
            "nova_matricula": nova_matricula.strip(),
            "data": data,
            "motivo": motivo.strip(),
            "cartorio": cartorio.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula atual é obrigatória.")
        if not _valida_matricula(nova_matricula):
            raise ValueError("Nova matrícula é obrigatória.")
        if not _valida_data(data):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data}")
        return dados

    @staticmethod
    def certidao(
        matricula: str,
        tipo_certidao: str,
        data_emissao: str,
        numero: str = "",
        orgao_emissor: str = "",
        validade: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de CERTIDÃO — emissão de certidão sobre o imóvel.

        Args:
            matricula:      Matrícula do imóvel.
            tipo_certidao:  NEGATIVA, POSITIVA, SITUACAO_FISCAL, etc.
            data_emissao:   Data de emissão (DD/MM/AAAA).
            numero:         Número da certidão.
            orgao_emissor:  Órgão emissor.
            validade:       Data de validade (DD/MM/AAAA).
            descricao:      Descrição.
        """
        dados = {
            "evento_tipo": PropertyEventType.CERTIDAO.value,
            "matricula": matricula.strip(),
            "tipo_certidao": tipo_certidao.upper().strip(),
            "data_emissao": data_emissao,
            "numero": numero.strip(),
            "orgao_emissor": orgao_emissor.strip(),
            "validade": validade,
            "descricao": descricao.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_data(data_emissao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_emissao}")
        return dados

    @staticmethod
    def iptu(
        matricula: str,
        codigo_iptu: str,
        data_atualizacao: str,
        valor_anterior: float = 0.0,
        valor_novo: float = 0.0,
        area_tributavel: float = 0.0,
        motivo: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de IPTU — alteração de avaliação fiscal.

        Args:
            matricula:          Matrícula do imóvel.
            codigo_iptu:        Código IPTU.
            data_atualizacao:   Data (DD/MM/AAAA).
            valor_anterior:     Valor anterior do IPTU.
            valor_novo:         Novo valor do IPTU.
            area_tributavel:    Área tributável (m²).
            motivo:             Motivo da alteração.
        """
        dados = {
            "evento_tipo": PropertyEventType.IPTU.value,
            "matricula": matricula.strip(),
            "codigo_iptu": codigo_iptu.strip(),
            "data_atualizacao": data_atualizacao,
            "valor_anterior": valor_anterior,
            "valor_novo": valor_novo,
            "area_tributavel": area_tributavel,
            "motivo": motivo.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_data(data_atualizacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_atualizacao}")
        return dados

    @staticmethod
    def zoneamento(
        matricula: str,
        zoneamento_anterior: str,
        zoneamento_novo: str,
        data: str,
        processo_numero: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de ZONEAMENTO — alteração de uso do solo.

        Args:
            matricula:              Matrícula do imóvel.
            zoneamento_anterior:    Código anterior.
            zoneamento_novo:        Código novo.
            data:                   Data (DD/MM/AAAA).
            processo_numero:        Número do processo.
            descricao:              Descrição.
        """
        dados = {
            "evento_tipo": PropertyEventType.ZONEAMENTO.value,
            "matricula": matricula.strip(),
            "zoneamento_anterior": zoneamento_anterior.strip(),
            "zoneamento_novo": zoneamento_novo.strip(),
            "data": data,
            "processo_numero": processo_numero.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_data(data):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data}")
        return dados

    @staticmethod
    def proprietario(
        matricula: str,
        cpf: str,
        nome: str,
        participacao: float,
        origem: str = "",
        data: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de PROPRIETÁRIO — adição/remoção de proprietário.

        Args:
            matricula:      Matrícula do imóvel.
            cpf:            CPF do proprietário.
            nome:           Nome do proprietário.
            participacao:   Percentual de participação (0-100).
            origem:         Origem: COMPRA, HERANCA, DOACAO, LEILAO.
            data:           Data (DD/MM/AAAA).
            descricao:      Descrição.
        """
        dados = {
            "evento_tipo": PropertyEventType.PROPRIETARIO.value,
            "matricula": matricula.strip(),
            "proprietario": {
                "cpf": re.sub(r"\D", "", cpf),
                "nome": nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "participacao": participacao,
            "origem": origem.upper().strip(),
            "data": data,
            "descricao": descricao.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_cpf(cpf):
            raise ValueError(f"CPF inválido: {cpf}")
        if not (0 < participacao <= 100):
            raise ValueError(f"Participação inválida: {participacao}. Use 0-100.")
        if data and not _valida_data(data):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data}")
        return dados

    @staticmethod
    def garantia_pessoa(
        matricula: str,
        garantidor_cpf: str,
        garantidor_nome: str,
        credor_nome: str,
        valor: float,
        data: str,
        tipo: str = "FIADOR",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de GARANTIA PESSOA — pessoa como garantidora do imóvel.

        Args:
            matricula:          Matrícula do imóvel.
            garantidor_cpf:     CPF do garantidor (fiador).
            garantidor_nome:    Nome do garantidor.
            credor_nome:        Nome do credor.
            valor:              Valor garantido (R$).
            data:               Data (DD/MM/AAAA).
            tipo:               FIADOR, AVALISTA, OUTRO.
            descricao:          Descrição.
        """
        dados = {
            "evento_tipo": PropertyEventType.GARANTIA_PESSOA.value,
            "matricula": matricula.strip(),
            "garantidor": {
                "cpf": re.sub(r"\D", "", garantidor_cpf),
                "nome": garantidor_nome.strip(),
                "hash_cadeia_pessoa": "",
            },
            "credor_nome": credor_nome.strip(),
            "valor": valor,
            "data": data,
            "tipo": tipo.upper().strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_matricula(matricula):
            raise ValueError("Matrícula é obrigatória.")
        if not _valida_cpf(garantidor_cpf):
            raise ValueError(f"CPF do garantidor inválido: {garantidor_cpf}")
        if not _valida_data(data):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data}")
        if valor <= 0:
            raise ValueError(f"Valor deve ser positivo: {valor}")
        return dados


# ── Protetor de Cadeia ────────────────────────────────────────────────

class PropertyChainProtector:
    """
    Impede adição de eventos que não fazem sentido
    em certos estados do imóvel.
    """

    @staticmethod
    def pode_adicionar(event_type: str, estado_atual: str) -> bool:
        """
        Verifica se um evento pode ser adicionado ao imóvel.

        Args:
            event_type:     Tipo do evento.
            estado_atual:   Estado atual do imóvel (LIVRE, CONSTRUIDO, etc).

        Returns:
            True se o evento pode ser adicionado.
        """
        # Em imóvel confiscado, só permitir certidões e zoneamento
        if estado_atual == "CONFISCADO":
            return event_type in {
                PropertyEventType.CERTIDAO.value,
                PropertyEventType.ZONEAMENTO.value,
                PropertyEventType.MATRICULA.value,
            }

        return True
