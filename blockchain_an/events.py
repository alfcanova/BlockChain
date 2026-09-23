"""
blockchain_an/events.py
Definições e validadores para eventos de animais.
Cada evento representa uma mudança na situação clínica,
jurídica ou de posse de um animal desde seu nascimento/cadastro.
"""

import re
import time
from enum import Enum
from typing import Any, Optional
from blockchain_pf.geografia_br import validar_cidade, validar_uf


# ── Enum de tipos de evento ────────────────────────────────────────────


class AnimalEventType(str, Enum):
    """Todos os tipos de evento de animal suportados."""

    # ── Gênesis ──────────────────────────────────────────────────────
    NASCIMENTO = "NASCIMENTO"  # Nascimento/cadastro do animal (gênesis)

    # ── Transferência ────────────────────────────────────────────────
    COMPRA_VENDA = "COMPRA_VENDA"  # Transferência com pagamento
    DOACAO = "DOACAO"  # Transferência sem pagamento
    ADOCAO = "ADOCAO"  # Adoção de animal abandonado
    APREENSAO = "APREENSAO"  # Apreensão por autoridade

    # ── Saúde ────────────────────────────────────────────────────────
    VACINACAO = "VACINACAO"  # Aplicação de vacina
    CASTRACAO = "CASTRACAO"  # Castração/esterilização
    TRATAMENTO = "TRATAMENTO"  # Tratamento veterinário
    CIRURGIA = "CIRURGIA"  # Cirurgia veterinária
    EXAME = "EXAME"  # Exame clínico/laboratorial
    DOENCA = "DOENCA"  # Registro de doença
    DESDE = "DESDE"  # Registro de óbito do animal

    # ── Identificação ────────────────────────────────────────────────
    MICROCHIP = "MICROCHIP"  # Implantação de microchip
    TATUAGEM = "TATUAGEM"  # Tatuagem de identificação
    CERTIDAO = "CERTIDAO"  # Certidão de nascimento/raça

    # ── Administrativo ───────────────────────────────────────────────
    LICENCA = "LICENCA"  # Licença de posse
    REGISTRO_RACA = "REGISTRO_RACA"  # Registro em confederação
    MUDANCA_NOME = "MUDANCA_NOME"  # Mudança do nome do animal
    OBITO = "OBITO"  # Óbito do animal
    PERDA_TOTAL = "PERDA_TOTAL"  # Desaparecimento/roubo


# ── Validadores ────────────────────────────────────────────────────────


def _valida_cpf(cpf: str) -> bool:
    cpf_clean = re.sub(r"\D", "", cpf)
    return len(cpf_clean) == 11


def _valida_data(data: str) -> bool:
    return bool(re.match(r"^\d{2}/\d{2}/\d{4}$", data))


# ── Fábricas de eventos ───────────────────────────────────────────────


class AnimalEventFactory:
    """
    Fábrica para criar eventos validados de animais.
    Cada método retorna um dict pronto para ir ao bloco.
    """

    @staticmethod
    def nascimento(
        nome: str,
        especie: str,
        raca: str,
        sexo: str,
        data_nascimento: str,
        cor: str,
        peso_kg: float,
        proprietario_cpf: str,
        proprietario_nome: str,
        pai_nome: str = "",
        mae_nome: str = "",
        microchip: str = "",
        raca_registro: str = "",
        cidade: str = "",
        uf: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Evento de NASCIMENTO (bloco gênesis).

        Args:
            nome:               Nome do animal.
            especie:            CÃO, GATO, CAVALO, BOVINO, etc.
            raca:               Raça do animal.
            sexo:               M ou F.
            data_nascimento:    DD/MM/AAAA.
            cor:                Cor predominante.
            peso_kg:            Peso em kg.
            proprietario_cpf:   CPF do proprietário.
            proprietario_nome:  Nome do proprietário.
            pai_nome:           Nome do pai (reprodutor).
            mae_nome:           Nome da mãe.
            microchip:          Número do microchip.
            raca_registro:      Registro da raça (CBKC, etc).
            cidade:             Cidade de nascimento.
            uf:                 UF.
            descricao:          Descrição complementar.
        """
        dados = {
            "evento_tipo": AnimalEventType.NASCIMENTO.value,
            "nome": nome.strip(),
            "especie": especie.upper().strip(),
            "raca": raca.strip(),
            "sexo": sexo.upper().strip(),
            "data_nascimento": data_nascimento,
            "cor": cor.strip(),
            "peso_kg": peso_kg,
            "proprietario": {
                "cpf": re.sub(r"\D", "", proprietario_cpf),
                "nome": proprietario_nome.strip(),
            },
            "pai_nome": pai_nome.strip(),
            "mae_nome": mae_nome.strip(),
            "microchip": microchip.strip(),
            "raca_registro": raca_registro.strip(),
            "cidade": cidade.strip(),
            "uf": uf.upper().strip(),
            "descricao": descricao.strip(),
            "situacao": "VIVO",
            "vacinas": [],
            "tratamentos": [],
            "doencas": [],
            "historico_proprietarios": [{
                "cpf": re.sub(r"\D", "", proprietario_cpf),
                "nome": proprietario_nome.strip(),
                "data_inicio": data_nascimento,
                "origem": "NASCIMENTO",
            }],
        }
        if not nome.strip():
            raise ValueError("Nome do animal é obrigatório.")
        if not especie.strip():
            raise ValueError("Espécie é obrigatória.")
        if sexo.upper() not in ("M", "F"):
            raise ValueError(f"Sexo inválido: {sexo}. Use M ou F.")
        if not _valida_data(data_nascimento):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_nascimento}")
        if peso_kg < 0:
            raise ValueError(f"Peso não pode ser negativo: {peso_kg}")
        if not validar_cidade(uf, cidade):
            raise ValueError(f"Local inválido: {cidade}/{uf}. Cidade deve existir na tabela oficial (IBGE).")
        return dados

    @staticmethod
    def compra_venda(
        nome: str,
        comprador_cpf: str, comprador_nome: str,
        vendedor_cpf: str, vendedor_nome: str,
        valor_transacao: float,
        data_transacao: str,
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de COMPRA/VENDA."""
        dados = {
            "evento_tipo": AnimalEventType.COMPRA_VENDA.value,
            "comprador": {"cpf": re.sub(r"\D", "", comprador_cpf), "nome": comprador_nome.strip()},
            "vendedor": {"cpf": re.sub(r"\D", "", vendedor_cpf), "nome": vendedor_nome.strip()},
            "valor_transacao": valor_transacao,
            "data_transacao": data_transacao,
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_transacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_transacao}")
        if valor_transacao < 0:
            raise ValueError(f"Valor não pode ser negativo: {valor_transacao}")
        return dados

    @staticmethod
    def doacao(
        donatario_cpf: str, donatario_nome: str,
        doador_cpf: str, doador_nome: str,
        data_doacao: str, motivo: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de DOAÇÃO."""
        dados = {
            "evento_tipo": AnimalEventType.DOACAO.value,
            "donatario": {"cpf": re.sub(r"\D", "", donatario_cpf), "nome": donatario_nome.strip()},
            "doador": {"cpf": re.sub(r"\D", "", doador_cpf), "nome": doador_nome.strip()},
            "data_doacao": data_doacao, "motivo": motivo.strip(),
        }
        if not _valida_data(data_doacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_doacao}")
        return dados

    @staticmethod
    def adocao(
        adotante_cpf: str, adotante_nome: str,
        data_adocao: str,
        origem: str = "ABRIGO",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de ADOÇÃO."""
        dados = {
            "evento_tipo": AnimalEventType.ADOCAO.value,
            "adotante": {"cpf": re.sub(r"\D", "", adotante_cpf), "nome": adotante_nome.strip()},
            "data_adocao": data_adocao,
            "origem": origem.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_adocao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_adocao}")
        return dados

    @staticmethod
    def vacinacao(
        nome_vacina: str, data_vacinacao: str,
        lote: str = "", fabricante: str = "", dose: str = "",
        veterinario_cpf: str = "", veterinario_nome: str = "",
        clinica: str = "", descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de VACINAÇÃO."""
        dados = {
            "evento_tipo": AnimalEventType.VACINACAO.value,
            "nome_vacina": nome_vacina.strip(),
            "data_vacinacao": data_vacinacao,
            "lote": lote.strip(), "fabricante": fabricante.strip(),
            "dose": dose.strip(),
            "veterinario": {"cpf": re.sub(r"\D", "", veterinario_cpf), "nome": veterinario_nome.strip()},
            "clinica": clinica.strip(), "descricao": descricao.strip(),
        }
        if not nome_vacina.strip():
            raise ValueError("Nome da vacina é obrigatório.")
        if not _valida_data(data_vacinacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_vacinacao}")
        return dados

    @staticmethod
    def castracao(
        data_castracao: str,
        veterinario_cpf: str = "", veterinario_nome: str = "",
        clinica: str = "", metodo: str = "",
        descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de CASTRAÇÃO."""
        dados = {
            "evento_tipo": AnimalEventType.CASTRACAO.value,
            "data_castracao": data_castracao,
            "veterinario": {"cpf": re.sub(r"\D", "", veterinario_cpf), "nome": veterinario_nome.strip()},
            "clinica": clinica.strip(), "metodo": metodo.strip(),
            "descricao": descricao.strip(),
        }
        if not _valida_data(data_castracao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_castracao}")
        return dados

    @staticmethod
    def tratamento(
        data_inicio: str, data_fim: str,
        diagnostico: str,
        veterinario_cpf: str = "", veterinario_nome: str = "",
        clinica: str = "", medicamentos: Optional[list[str]] = None,
        valor: float = 0.0, descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de TRATAMENTO veterinário."""
        dados = {
            "evento_tipo": AnimalEventType.TRATAMENTO.value,
            "data_inicio": data_inicio, "data_fim": data_fim,
            "diagnostico": diagnostico.strip(),
            "veterinario": {"cpf": re.sub(r"\D", "", veterinario_cpf), "nome": veterinario_nome.strip()},
            "clinica": clinica.strip(),
            "medicamentos": medicamentos or [],
            "valor": valor, "descricao": descricao.strip(),
        }
        if not _valida_data(data_inicio):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_inicio}")
        return dados

    @staticmethod
    def microchip(
        numero_microchip: str, data_implantacao: str,
        fabricante: str = "", veterinario_cpf: str = "",
        veterinario_nome: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de MICROCHIP."""
        dados = {
            "evento_tipo": AnimalEventType.MICROCHIP.value,
            "numero_microchip": numero_microchip.strip(),
            "data_implantacao": data_implantacao,
            "fabricante": fabricante.strip(),
            "veterinario": {"cpf": re.sub(r"\D", "", veterinario_cpf), "nome": veterinario_nome.strip()},
        }
        if not numero_microchip.strip():
            raise ValueError("Número do microchip é obrigatório.")
        if not _valida_data(data_implantacao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_implantacao}")
        return dados

    @staticmethod
    def licenca(
        numero_licenca: str, data_emissao: str, data_validade: str,
        orgao_emissor: str = "", descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de LICENÇA de posse."""
        dados = {
            "evento_tipo": AnimalEventType.LICENCA.value,
            "numero_licenca": numero_licenca.strip(),
            "data_emissao": data_emissao, "data_validade": data_validade,
            "orgao_emissor": orgao_emissor.strip(), "descricao": descricao.strip(),
        }
        if not _valida_data(data_emissao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_emissao}")
        return dados

    @staticmethod
    def mudanca_nome(
        nome_anterior: str, nome_novo: str, data_mudanca: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de MUDANÇA DE NOME."""
        dados = {
            "evento_tipo": AnimalEventType.MUDANCA_NOME.value,
            "nome_anterior": nome_anterior.strip(), "nome_novo": nome_novo.strip(),
            "data_mudanca": data_mudanca,
        }
        if not _valida_data(data_mudanca):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_mudanca}")
        return dados

    @staticmethod
    def obito(
        data_obito: str, causa: str = "",
        veterinario_cpf: str = "", veterinario_nome: str = "",
        local: str = "", descricao: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de ÓBITO."""
        dados = {
            "evento_tipo": AnimalEventType.OBITO.value,
            "data_obito": data_obito, "causa": causa.strip(),
            "veterinario": {"cpf": re.sub(r"\D", "", veterinario_cpf), "nome": veterinario_nome.strip()},
            "local": local.strip(), "descricao": descricao.strip(),
        }
        if not _valida_data(data_obito):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_obito}")
        return dados

    @staticmethod
    def certidao(
        tipo_certidao: str, numero: str, data_emissao: str,
        orgao_emissor: str = "", conteudo: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Evento de CERTIDÃO."""
        dados = {
            "evento_tipo": AnimalEventType.CERTIDAO.value,
            "tipo_certidao": tipo_certidao.upper().strip(),
            "numero": numero.strip(), "data_emissao": data_emissao,
            "orgao_emissor": orgao_emissor.strip(), "conteudo": conteudo.strip(),
        }
        if not _valida_data(data_emissao):
            raise ValueError(f"Data inválida (DD/MM/AAAA): {data_emissao}")
        return dados


class AnimalChainProtector:
    """Impede adição de eventos bloqueados."""

    BLOQUEADOS_APOS_OBITO = {
        AnimalEventType.COMPRA_VENDA,
        AnimalEventType.DOACAO,
        AnimalEventType.ADOCAO,
        AnimalEventType.VACINACAO,
        AnimalEventType.CASTRACAO,
        AnimalEventType.TRATAMENTO,
        AnimalEventType.CIRURGIA,
        AnimalEventType.MICROCHIP,
        AnimalEventType.LICENCA,
    }

    @staticmethod
    def pode_adicionar(tipo_evento: str, situacao: str) -> bool:
        if situacao in ("OBITO", "PERDA_TOTAL"):
            try:
                tipo = AnimalEventType(tipo_evento)
                return tipo not in AnimalChainProtector.BLOQUEADOS_APOS_OBITO
            except ValueError:
                return True
        return True
