"""Testes de validação de CPF/CNPJ — dígitos verificadores (H7, Fase 5.4).

A função _valida_cpf está duplicada em 4 módulos (PF, IM, MO, CO) e
_valida_cnpj em 2 (MO, CO). Todos devem ter comportamento idêntico:
  - 11/14 dígitos após limpeza de máscara
  - rejeita sequências de dígitos iguais (000..., 111...)
  - valida os 2 dígitos verificadores pelo algoritmo oficial
  - aceita CPF/CNPJ com máscara (pontos, hífen, barra)
"""

import pytest

from blockchain_pf.events import _valida_cpf as cpf_pf
from blockchain_im.events import _valida_cpf as cpf_im
from blockchain_mo.events import _valida_cpf as cpf_mo
from blockchain_co.events import _valida_cpf as cpf_co
from blockchain_co.events import _valida_cnpj as cnpj_co
from blockchain_mo.events import _valida_cnpj as cnpj_mo

CPFS = (cpf_pf, cpf_im, cpf_mo, cpf_co)
CNPJS = (cnpj_co, cnpj_mo)


# ── CPFs válidos ──────────────────────────────────────────────────────

CPFS_VALIDOS = [
    "12345678909",      # usado em toda a suite
    "11122233396",      # usado no E2E da API
    "52998224725",      # exemplo clássico da Receita
    "11144477735",
    "16899535009",
    "98765432100",
]

# ── CPFs inválidos ────────────────────────────────────────────────────

CPFS_INVALIDOS = [
    "12345678900",      # último dígito errado
    "12345678901",
    "52998224724",      # dígito verificador trocado
    "00000000000",      # sequência de iguais
    "11111111111",
    "99999999999",
    "1234567890",       # 10 dígitos
    "123456789098",     # 12 dígitos
    "",                 # vazio
    "abcdefghijk",      # não numérico
    "123.456",          # máscara incompleta
]


class TestCpfValidos:
    @pytest.mark.parametrize("cpf", CPFS_VALIDOS)
    def test_todas_implementacoes_aceitam(self, cpf):
        for fn in CPFS:
            assert fn(cpf) is True, f"{fn.__module__} rejeitou CPF {cpf}"

    def test_mascara_aceita(self):
        for fn in CPFS:
            assert fn("123.456.789-09") is True
            assert fn("111.222.333-96") is True

    def test_espacos_aceitos(self):
        for fn in CPFS:
            assert fn(" 12345678909 ") is True


class TestCpfInvalidos:
    @pytest.mark.parametrize("cpf", CPFS_INVALIDOS)
    def test_todas_implementacoes_rejeitam(self, cpf):
        for fn in CPFS:
            assert fn(cpf) is False, f"{fn.__module__} aceitou CPF {cpf}"

    def test_none_ou_numerico(self):
        """_valida_cpf espera str; re.sub em não-string levanta TypeError."""
        for fn in CPFS:
            with pytest.raises(TypeError):
                fn(None)  # type: ignore[arg-type]

    def test_digito_verificador_isolado(self):
        """Perturbar 1 dígito verificador de um CPF válido o invalida."""
        base = "12345678909"
        perturbados = {base[:9] + d + base[10] for d in "0123456789"}
        perturbados.discard(base)
        for p in perturbados:
            assert cpf_pf(p) is False, f"1º dígito {p[-2]} aceito incorretamente"


class TestConsistenciaEntreModulos:
    def test_implementacoes_cpf_identicas(self):
        candidatos = CPFS_VALIDOS + CPFS_INVALIDOS
        for cpf in candidatos:
            resultados = {fn(cpf) for fn in CPFS}
            assert len(resultados) == 1, f"divergência para CPF {cpf}: {resultados}"


# ── CNPJ ──────────────────────────────────────────────────────────────

CNPJS_VALIDOS = [
    "12345678000195",   # usado em toda a suite
    "11222333000181",   # dígito 11 é válido (resto < 2 → 0)
    "61198164000160",   # Porto Seguro (testes EM)
]

CNPJS_INVALIDOS = [
    "12345678000100",   # dígitos verificadores errados
    "12345678000196",
    "00000000000000",   # sequência de iguais
    "11111111111111",
    "1234567800019",    # 13 dígitos
    "123456780001950",  # 15 dígitos
    "",                 # vazio
    "12.345.678",       # máscara incompleta
]


class TestCnpjValidos:
    @pytest.mark.parametrize("cnpj", CNPJS_VALIDOS)
    def test_todas_implementacoes_aceitam(self, cnpj):
        for fn in CNPJS:
            assert fn(cnpj) is True, f"{fn.__module__} rejeitou CNPJ {cnpj}"

    def test_mascara_aceita(self):
        for fn in CNPJS:
            assert fn("12.345.678/0001-95") is True


class TestCnpjInvalidos:
    @pytest.mark.parametrize("cnpj", CNPJS_INVALIDOS)
    def test_todas_implementacoes_rejeitam(self, cnpj):
        for fn in CNPJS:
            assert fn(cnpj) is False, f"{fn.__module__} aceitou CNPJ {cnpj}"

    def test_none(self):
        for fn in CNPJS:
            with pytest.raises(TypeError):
                fn(None)  # type: ignore[arg-type]


class TestConsistenciaCnpj:
    def test_implementacoes_cnpj_identicas(self):
        candidatos = CNPJS_VALIDOS + CNPJS_INVALIDOS
        for cnpj in candidatos:
            resultados = {fn(cnpj) for fn in CNPJS}
            assert len(resultados) == 1, f"divergência para CNPJ {cnpj}: {resultados}"


# ── Integração com factories ──────────────────────────────────────────


class TestIntegracaoFactories:
    """Factories que usam os validadores devem propagar a rejeição."""

    def test_pf_nascimento_rejeita_cpf_invalido(self):
        from blockchain_pf import EventFactory

        with pytest.raises(ValueError, match="CPF"):
            EventFactory.nascimento(
                cpf="11111111111", nome_completo="Falso",
                data_nascimento="15/03/2000", sexo="F",
                cidade_nascimento="Sao Paulo", uf_nascimento="SP",
                nome_mae="Mae",
            )

    def test_co_constituicao_rejeita_cnpj_invalido(self):
        from blockchain_co import CompanyEventFactory

        with pytest.raises(ValueError, match="CNPJ"):
            CompanyEventFactory.constituicao(
                cnpj="11111111111111", razao_social="Fantasma LTDA",
                nome_fantasia="Fantasma",
                data_constituicao="01/01/2024", tipo_empresa="LTDA",
                porte="ME", capital_social=1000,
                natureza_juridica="2062", atividade_principal="6201501",
            )
