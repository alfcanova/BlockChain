"""
blockchain_pf/events.py
Definições e validadores para eventos vitais de PF.
Cada evento é representado como um dicionário estruturado
que será serializado no payload do bloco.
"""

import re
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional, ClassVar
from blockchain_pf.geografia_br import validar_cidade


# ── Enum de tipos de evento ────────────────────────────────────────────

class EventType(str, Enum):
    """Todos os tipos de evento vital suportados."""
    NASCIMENTO     = "NASCIMENTO"
    ADOCAO         = "ADOCAO"
    CASAMENTO      = "CASAMENTO"
    DIVORCIO       = "DIVORCIO"
    OBITO          = "OBITO"
    ALTERACAO_NOME = "ALTERACAO_NOME"
    DISVINC_MATERNA = "DISVINC_MATERNA"
    DISVINC_PATerna = "DISVINC_PATerna"
    VACINACAO      = "VACINACAO"
    PROTESE        = "PROTESE"
    # Documentos pessoais
    CNH            = "CNH"
    TITULO_ELEITOR  = "TITULO_ELEITOR"
    ESCOLARIDADE    = "ESCOLARIDADE"

    # Alias para manter compatibilidade
    DISVINCULACAO_MATERNA = "DISVINC_MATERNA"
    DISVINCULACAO_PATerna = "DISVINC_PATerna"


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

def _valida_nomes_obrigatorios(campos: list[str], dados: dict) -> list[str]:
    """Retorna lista de campos obrigatórios ausentes."""
    return [c for c in campos if not dados.get(c)]


# ── Fábricas de eventos ───────────────────────────────────────────────

class EventFactory:
    """
    Fábrica para criar eventos validados.
    Cada método retorna um dict pronto para ir ao bloco.
    """

    @staticmethod
    def nascimento(
        cpf: str,
        nome_completo: str,
        data_nascimento: str,
        sexo: str,
        cidade_nascimento: str,
        uf_nascimento: str,
        nome_mae: str,
        nome_pai: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de NASCIMENTO (bloco gênesis).
        
        Args:
            cpf:               CPF do recém-nascido (11 dígitos).
            nome_completo:     Nome completo ao nascer.
            data_nascimento:   DD/MM/AAAA.
            sexo:              'M' ou 'F'.
            cidade_nascimento: Cidade de nascimento.
            uf_nascimento:     UF de nascimento.
            nome_mae:          Nome completo da mãe.
            nome_pai:          Nome completo do pai (opcional).
        """
        dados = {
            "evento_tipo": EventType.NASCIMENTO.value,
            "cpf": re.sub(r"\D", "", cpf),
            "nome_completo": nome_completo.strip(),
            "nome_social": nome_completo.strip(),
            "data_nascimento": data_nascimento,
            "sexo": sexo.upper(),
            "cidade_nascimento": cidade_nascimento,
            "uf_nascimento": uf_nascimento.upper(),
            "nome_mae": nome_mae.strip(),
            "nome_pai": (nome_pai or "").strip(),
            "nome_conjuge": None,
            "status_vivo": True,
            "historico_nomes": [nome_completo.strip()],
            "parentela": {
                "mae": {"nome": nome_mae.strip(), "ativo": True},
                "pai": {"nome": (nome_pai or "").strip(), "ativo": True},
            },
        }
        # Validações
        if not _valida_cpf(cpf):
            raise ValueError(f"CPF inválido: {cpf}")
        if not _valida_data(data_nascimento):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_nascimento}")
        if not _valida_uf(uf_nascimento):
            raise ValueError(f"UF inválida: {uf_nascimento}")
        if sexo.upper() not in ("M", "F"):
            raise ValueError(f"Sexo inválido: {sexo}")
        if not validar_cidade(uf_nascimento, cidade_nascimento):
            raise ValueError(f"Local de nascimento inválido: {cidade_nascimento}/{uf_nascimento}. Cidade deve existir na tabela oficial (IBGE).")
        return dados

    @staticmethod
    def adocao(
        cpf: str,
        nome_adotivo: Optional[str],
        data_adocao: str,
        nome_mae_adotiva: str,
        nome_pai_adotivo: Optional[str] = None,
        mantem_nome_biologico: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de ADOÇÃO — altera parentela e opcionalmente o nome."""
        dados = {
            "evento_tipo": EventType.ADOCAO.value,
            "cpf": re.sub(r"\D", "", cpf),
            "data_adocao": data_adocao,
            "nome_mae_adotiva": nome_mae_adotiva.strip(),
            "nome_pai_adotivo": (nome_pai_adotivo or "").strip(),
            "nome_adotivo": (nome_adotivo or "").strip(),
            "mantem_nome_biologico": mantem_nome_biologico,
        }
        if not _valida_data(data_adocao):
            raise ValueError(f"Data inválida: {data_adocao}")
        return dados

    @staticmethod
    def casamento(
        cpf: str,
        nome_conjuge: str,
        cpf_conjuge: str,
        data_casamento: str,
        regime_bens: str = "COMUNHAO_PARCIAL",
        cidade: str = "",
        uf: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de CASAMENTO.
        
        Args:
            regime_bens: COMUNHAO_PARCIAL, COMUNHAO_UNIVERSAL,
                         SEPARACAO_TOTAL, PARTICIPACAO_FINAL_AQUESTOS.
        """
        dados = {
            "evento_tipo": EventType.CASAMENTO.value,
            "cpf": re.sub(r"\D", "", cpf),
            "nome_conjuge": nome_conjuge.strip(),
            "cpf_conjuge": re.sub(r"\D", "", cpf_conjuge),
            "data_casamento": data_casamento,
            "regime_bens": regime_bens.upper(),
            "cidade": cidade.strip(),
            "uf": uf.upper(),
        }
        if not _valida_data(data_casamento):
            raise ValueError(f"Data inválida: {data_casamento}")
        return dados

    @staticmethod
    def divorcio(
        cpf: str,
        data_divorcio: str,
        tipo: str = "CONSENSUAL",
        guarda_filhos: Optional[str] = None,
        pensao_alimenticia: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de DIVÓRCIO.
        
        Args:
            tipo:           CONSENSUAL ou JUDICIAL.
            guarda_filhos:  'MATERNA', 'PATerna', 'COMPARTILHADA' ou None.
            pensao_alimenticia: Se há pensão.
        """
        dados = {
            "evento_tipo": EventType.DIVORCIO.value,
            "cpf": re.sub(r"\D", "", cpf),
            "data_divorcio": data_divorcio,
            "tipo": tipo.upper(),
            "guarda_filhos": guarda_filhos,
            "pensao_alimenticia": pensao_alimenticia,
        }
        if not _valida_data(data_divorcio):
            raise ValueError(f"Data inválida: {data_divorcio}")
        return dados

    @staticmethod
    def obito(
        cpf: str,
        data_obito: str,
        cidade_obito: str,
        uf_obito: str,
        causa_morte: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de ÓBITO — encerra a cadeia ( eventos extras bloqueados)."""
        dados = {
            "evento_tipo": EventType.OBITO.value,
            "cpf": re.sub(r"\D", "", cpf),
            "data_obito": data_obito,
            "cidade_obito": cidade_obito,
            "uf_obito": uf_obito.upper(),
            "causa_morte": causa_morte or "Não informada",
        }
        if not _valida_data(data_obito):
            raise ValueError(f"Data inválida: {data_obito}")
        return dados

    @staticmethod
    def alteracao_nome(
        cpf: str,
        nome_anterior: str,
        nome_novo: str,
        data_alteracao: str,
        motivo: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de ALTERAÇÃO DE NOME."""
        dados = {
            "evento_tipo": EventType.ALTERACAO_NOME.value,
            "cpf": re.sub(r"\D", "", cpf),
            "nome_anterior": nome_anterior.strip(),
            "nome_novo": nome_novo.strip(),
            "data_alteracao": data_alteracao,
            "motivo": motivo.strip(),
        }
        if not _valida_data(data_alteracao):
            raise ValueError(f"Data inválida: {data_alteracao}")
        return dados

    @staticmethod
    def disvinculacao_materna(
        cpf: str,
        data_disvinculacao: str,
        motivo: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de DESLIGAMENTO DE VÍNCULO MATerno."""
        dados = {
            "evento_tipo": EventType.DISVINC_MATERNA.value,
            "cpf": re.sub(r"\D", "", cpf),
            "data_disvinculacao": data_disvinculacao,
            "motivo": motivo.strip(),
            "vinculo_afetado": "MAE",
        }
        if not _valida_data(data_disvinculacao):
            raise ValueError(f"Data inválida: {data_disvinculacao}")
        return dados

    @staticmethod
    def disvinculacao_paterna(
        cpf: str,
        data_disvinculacao: str,
        motivo: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de DESLIGAMENTO DE VÍNCULO PATerno."""
        dados = {
            "evento_tipo": EventType.DISVINC_PATerna.value,
            "cpf": re.sub(r"\D", "", cpf),
            "data_disvinculacao": data_disvinculacao,
            "motivo": motivo.strip(),
            "vinculo_afetado": "PAI",
        }
        if not _valida_data(data_disvinculacao):
            raise ValueError(f"Data inválida: {data_disvinculacao}")
        return dados

    @staticmethod
    def vacina(
        cpf: str,
        nome_vacina: str,
        data_vacinacao: str,
        lote: str = "",
        fabricante: str = "",
        dose: str = "",
        unidade_saude: str = "",
        cidade: str = "",
        uf: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de VACINAÇÃO.

        Registra a aplicação de uma vacina na cartilha de vacinação.

        Args:
            cpf:              CPF da pessoa vacinada (11 dígitos).
            nome_vacina:      Nome da vacina (ex: "COVID-19", "Febre Amarela").
            data_vacinacao:   DD/MM/AAAA.
            lote:             Número do lote da vacina (opcional).
            fabricante:       Fabricante da vacina (opcional).
            dose:             Dose aplicada (ex: "1ª dose", "2ª dose", "Reforço").
            unidade_saude:    UBS ou clínica onde foi aplicada (opcional).
            cidade:           Cidade da aplicação (opcional).
            uf:               UF da aplicação (opcional).
        """
        dados = {
            "evento_tipo": EventType.VACINACAO.value,
            "cpf": re.sub(r"\D", "", cpf),
            "nome_vacina": nome_vacina.strip(),
            "data_vacinacao": data_vacinacao,
            "lote": lote.strip(),
            "fabricante": fabricante.strip(),
            "dose": dose.strip(),
            "unidade_saude": unidade_saude.strip(),
            "cidade": cidade.strip(),
            "uf": uf.upper() if uf else "",
        }
        if not _valida_cpf(cpf):
            raise ValueError(f"CPF inválido: {cpf}")
        if not _valida_data(data_vacinacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_vacinacao}")
        if not nome_vacina.strip():
            raise ValueError("Nome da vacina é obrigatório.")
        return dados

    @staticmethod
    def protese(
        cpf: str,
        nome_protese: str,
        data_implantacao: str,
        tipo: str = "",
        marca_modelo: str = "",
        medico_responsavel: str = "",
        hospital_clinica: str = "",
        cidade: str = "",
        uf: str = "",
        data_remocao: Optional[str] = None,
        motivo_remocao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de PRÓTESE / IMPLANTE.

        Registra a colocação ou remoção de prótese/implante.

        Args:
            cpf:                  CPF da pessoa (11 dígitos).
            nome_protese:         Nome da prótese (ex: "Prótese de Joelho Direito").
            data_implantacao:     DD/MM/AAAA da implantação.
            tipo:                 Tipo da prótese (ex: "Ortopédica", "Cardíaca", "Dental").
            marca_modelo:         Marca e modelo (opcional).
            medico_responsavel:   Nome do cirurgião (opcional).
            hospital_clinica:     Local da cirurgia (opcional).
            cidade:               Cidade (opcional).
            uf:                   UF (opcional).
            data_remocao:         DD/MM/AAAA se removida (opcional).
            motivo_remocao:       Motivo da remoção (opcional).
        """
        dados = {
            "evento_tipo": EventType.PROTESE.value,
            "cpf": re.sub(r"\D", "", cpf),
            "nome_protese": nome_protese.strip(),
            "data_implantacao": data_implantacao,
            "tipo": tipo.strip(),
            "marca_modelo": marca_modelo.strip(),
            "medico_responsavel": medico_responsavel.strip(),
            "hospital_clinica": hospital_clinica.strip(),
            "cidade": cidade.strip(),
            "uf": uf.upper() if uf else "",
            "data_remocao": data_remocao,
            "motivo_remocao": motivo_remocao.strip() if motivo_remocao else "",
            "ativa": data_remocao is None,
        }
        if not _valida_cpf(cpf):
            raise ValueError(f"CPF inválido: {cpf}")
        if not _valida_data(data_implantacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_implantacao}")
        if not nome_protese.strip():
            raise ValueError("Nome da prótese é obrigatório.")
        if data_remocao and not _valida_data(data_remocao):
            raise ValueError(f"Data de remoção inválida (DD/MM/AAAA): {data_remocao}")
        return dados

    # ── CNH ───────────────────────────────────────────────────────────

    @staticmethod
    def cnh(
        cpf: str,
        numero_cnh: str,
        categoria: str,
        data_emissao: str,
        data_validade: str,
        orgao_emissor: str = "",
        uf_emissao: str = "",
        situacao: str = "VALIDA",
        pontos: int = 0,
        exame_medico: str = "",
        data_exame_medico: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de CNH (Carteira Nacional de Habilitação).

        Registra obtenção, renovação ou alteração da CNH.

        Args:
            cpf:                CPF do titular (11 dígitos).
            numero_cnh:         Número da CNH.
            categoria:          Categoria (A, B, C, D, E, AB, AC, AD, AE).
            data_emissao:       DD/MM/AAAA da emissão.
            data_validade:      DD/MM/AAAA da validade.
            orgao_emissor:      Órgão emissor (ex: "DETRAN-SP").
            uf_emissao:         UF de emissão.
            situacao:           VALIDA, SUSPENSA, CASSADA, CANCELADA, RENOVADA.
            pontos:             Pontuação na carteira (0-40).
            exame_medico:       Resultado do exame médico (APTO / INAPTO).
            data_exame_medico:  Data do exame médico.
        """
        dados = {
            "evento_tipo": EventType.CNH.value,
            "cpf": re.sub(r"\D", "", cpf),
            "numero_cnh": numero_cnh.strip(),
            "categoria": categoria.upper().strip(),
            "data_emissao": data_emissao,
            "data_validade": data_validade,
            "orgao_emissor": orgao_emissor.strip(),
            "uf_emissao": uf_emissao.upper() if uf_emissao else "",
            "situacao": situacao.upper().strip(),
            "pontos": max(0, min(40, pontos)),
            "exame_medico": exame_medico.strip(),
            "data_exame_medico": data_exame_medico,
        }
        if not _valida_cpf(cpf):
            raise ValueError(f"CPF inválido: {cpf}")
        if not numero_cnh.strip():
            raise ValueError("Número da CNH é obrigatório.")
        if not _valida_data(data_emissao):
            raise ValueError(f"Data de emissão inválida (DD/MM/AAAA): {data_emissao}")
        if not _valida_data(data_validade):
            raise ValueError(f"Data de validade inválida (DD/MM/AAAA): {data_validade}")
        return dados

    # ── Título de Eleitor ──────────────────────────────────────────────

    @staticmethod
    def titulo_eleitor(
        cpf: str,
        numero_titulo: str,
        zona_eleitoral: str,
        secao_eleitoral: str,
        municipio: str,
        uf: str,
        data_emissao: str,
        situacao: str = "REGULAR",
        titulo_anterior: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de Título de Eleitor.

        Registra obtenção, transferência ou atualização do título.

        Args:
            cpf:                CPF do titular (11 dígitos).
            numero_titulo:      Número do título de eleitor (12 dígitos).
            zona_eleitoral:     Número da zona eleitoral.
            secao_eleitoral:    Número da seção eleitoral.
            municipio:          Município de registro.
            uf:                 UF de registro.
            data_emissao:       DD/MM/AAAA da emissão.
            situacao:           REGULAR, SUSPENSO, CANCELADO,segunda_via.
            titulo_anterior:    Número do título anterior (se transferência/2ª via).
        """
        dados = {
            "evento_tipo": EventType.TITULO_ELEITOR.value,
            "cpf": re.sub(r"\D", "", cpf),
            "numero_titulo": numero_titulo.strip(),
            "zona_eleitoral": zona_eleitoral.strip(),
            "secao_eleitoral": secao_eleitoral.strip(),
            "municipio": municipio.strip(),
            "uf": uf.upper().strip(),
            "data_emissao": data_emissao,
            "situacao": situacao.upper().strip(),
            "titulo_anterior": titulo_anterior.strip(),
        }
        if not _valida_cpf(cpf):
            raise ValueError(f"CPF inválido: {cpf}")
        titulo_clean = re.sub(r"\D", "", numero_titulo)
        if len(titulo_clean) != 12:
            raise ValueError(f"Número de título inválido (12 dígitos): {numero_titulo}")
        if not _valida_data(data_emissao):
            raise ValueError(f"Data de emissão inválida (DD/MM/AAAA): {data_emissao}")
        if not zona_eleitoral.strip():
            raise ValueError("Zona eleitoral é obrigatória.")
        if not secao_eleitoral.strip():
            raise ValueError("Seção eleitoral é obrigatória.")
        return dados

    # ── Escolaridade ───────────────────────────────────────────────────

    @staticmethod
    def escolaridade(
        cpf: str,
        nivel: str,
        instituicao: str,
        data_inicio: str = "",
        data_conclusao: str = "",
        curso: str = "",
        serie_ano: str = "",
        situacao: str = "EM_ANDAMENTO",
        registro: str = "",
        tipo_registro: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de ESCOLARIDADE.

        Registra ciclo escolar, graduação, pós-graduação, etc.

        Args:
            cpf:            CPF do titular (11 dígitos).
            nivel:          Fundamental, Medio, Tecnico, Superior, Pos, Mestrado, Doutorado.
            instituicao:    Nome da instituição de ensino.
            data_inicio:    DD/MM/AAAA do início (opcional).
            data_conclusao: DD/MM/AAAA da conclusão (opcional).
            curso:          Nome do curso (para nível superior+).
            serie_ano:      Série ou ano escolar (para fundamental/médio).
            situacao:       EM_ANDAMENTO, CONCLUIDO, TRANCADO, DESISTENTE, ABANDONO.
            registro:       Número de registro do diploma/certificado.
            tipo_registro:  Tipo: DIPLOMA, CERTIFICADO, HISTORICO, ATESTADO.
        """
        dados = {
            "evento_tipo": EventType.ESCOLARIDADE.value,
            "cpf": re.sub(r"\D", "", cpf),
            "nivel": nivel.strip(),
            "instituicao": instituicao.strip(),
            "data_inicio": data_inicio,
            "data_conclusao": data_conclusao,
            "curso": curso.strip(),
            "serie_ano": serie_ano.strip(),
            "situacao": situacao.upper().strip(),
            "registro": registro.strip(),
            "tipo_registro": tipo_registro.strip(),
        }
        if not _valida_cpf(cpf):
            raise ValueError(f"CPF inválido: {cpf}")
        if not nivel.strip():
            raise ValueError("Nível de escolaridade é obrigatório.")
        if not instituicao.strip():
            raise ValueError("Instituição de ensino é obrigatória.")
        if data_inicio and not _valida_data(data_inicio):
            raise ValueError(f"Data de início inválida (DD/MM/AAAA): {data_inicio}")
        if data_conclusao and not _valida_data(data_conclusao):
            raise ValueError(f"Data de conclusão inválida (DD/MM/AAAA): {data_conclusao}")
        return dados


# ── Protetor de Cadeia (após óbito) ───────────────────────────────────

class ChainProtector:
    """
    Impede adição de novos eventos após ÓBITO,
    exceto ALTERACAO_NOME (correção administrativa).
    """

    BLOQUEADOS_APOS_OBITO = {
        EventType.CASAMENTO,
        EventType.DIVORCIO,
        EventType.ADOCAO,
        EventType.DISVINC_MATERNA,
        EventType.DISVINC_PATerna,
    }

    @staticmethod
    def pode_adicionar(tipo_evento: str, ja_tem_obito: bool) -> bool:
        """Verifica se um evento pode ser adicionado à cadeia."""
        if not ja_tem_obito:
            return True
        try:
            tipo = EventType(tipo_evento)
            return tipo not in ChainProtector.BLOQUEADOS_APOS_OBITO
        except ValueError:
            return True  # Tipo desconhecido — permite
