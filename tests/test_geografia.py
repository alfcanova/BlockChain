"""Testes para blockchain_pf/geografia_br — Validação geográfica IBGE.

Cobertura (gap crítico do TODO.md — módulo importado por todas as factories):
  - validar_uf: 27 UFs oficiais, case/whitespace-insensitive, inválidos
  - validar_cidade: tabela oficial IBGE (5.571 municípios), acentos, case
  - municipios_da_uf: ordenação (capital primeiro, depois alfabética)
  - capital_da_uf: 27 capitais, consistência com validar_cidade
  - total_municipios: total oficial IBGE
  - _norm: normalização (None, não-string, acentos, espaços)
"""

from blockchain_pf.geografia_br import (
    CAPITAIS,
    MUNICIPIOS,
    UFS,
    UFS_SIGLAS,
    _norm,
    capital_da_uf,
    municipios_da_uf,
    total_municipios,
    validar_cidade,
    validar_uf,
)


# ── Dados de base ─────────────────────────────────────────────────────


class TestDadosBase:
    def test_27_ufs_oficiais(self):
        assert len(UFS) == 27
        assert len(UFS_SIGLAS) == 27

    def test_uf_tem_sigla_nome_regiao(self):
        for sigla, nome, regiao in UFS:
            assert len(sigla) == 2
            assert sigla == sigla.upper()
            assert nome and regiao

    def test_27_capitais(self):
        assert len(CAPITAIS) == 27
        for sigla in UFS_SIGLAS:
            assert sigla in CAPITAIS

    def test_tabela_municipios_carregada(self):
        """A tabela IBGE deve carregar do JSON (5.571 municípios)."""
        assert total_municipios() == 5571
        assert len(MUNICIPIOS) == 5571


# ── validar_uf ────────────────────────────────────────────────────────


class TestValidarUf:
    def test_todas_siglas_validas(self):
        for sigla in UFS_SIGLAS:
            assert validar_uf(sigla) is True

    def test_case_insensitive(self):
        assert validar_uf("sp") is True
        assert validar_uf("Sp") is True

    def test_espacos_ao_redor(self):
        assert validar_uf(" SP ") is True

    def test_none_invalido(self):
        assert validar_uf(None) is False

    def test_vazio_invalido(self):
        assert validar_uf("") is False
        assert validar_uf("   ") is False

    def test_sigla_inexistente(self):
        assert validar_uf("XX") is False
        assert validar_uf("ZZ") is False

    def test_nao_string(self):
        assert validar_uf(42) is False


# ── validar_cidade ────────────────────────────────────────────────────


class TestValidarCidade:
    def test_capitais_validam_na_propria_uf(self):
        """Todas as 27 capitais devem existir na tabela da própria UF."""
        for uf, capital in CAPITAIS.items():
            assert validar_cidade(uf, capital), f"{capital}/{uf} deveria validar"

    def test_capital_uf_errada_invalida(self):
        """Capital não pode validar em UF errada (ex: capital do SP no RJ)."""
        assert validar_cidade("RJ", "Sao Paulo") is False

    def test_acentos_ignorados(self):
        assert validar_cidade("SP", "São Paulo") is True
        assert validar_cidade("CE", "Fortaleza") is True

    def test_case_insensitive(self):
        assert validar_cidade("SP", "sao paulo") is True
        assert validar_cidade("SP", "SAO PAULO") is True

    def test_espacos_extras_normalizados(self):
        assert validar_cidade("SP", "  sao   paulo  ") is True

    def test_cidade_inexistente(self):
        assert validar_cidade("SP", "Cidade Inexistente XYZ") is False

    def test_uf_invalida(self):
        assert validar_cidade("XX", "Sao Paulo") is False

    def test_entradas_vazias_ou_none(self):
        assert validar_cidade(None, "Sao Paulo") is False
        assert validar_cidade("SP", None) is False
        assert validar_cidade("SP", "") is False
        assert validar_cidade("SP", "   ") is False


# ── municipios_da_uf ──────────────────────────────────────────────────


class TestMunicipiosDaUf:
    def test_lista_nao_vazia_para_todas_ufs(self):
        for sigla in UFS_SIGLAS:
            lista = municipios_da_uf(sigla)
            assert len(lista) > 0, f"{sigla} sem municípios"

    def test_capital_primeiro(self):
        sp = municipios_da_uf("SP")
        assert sp[0]["capital"] == 1
        assert _norm(sp[0]["nome"]) == "SAO PAULO"

    def test_ordenacao_alfabetica_apos_capital(self):
        sp = municipios_da_uf("SP")
        nomes = [_norm(m["nome"]) for m in sp[1:]]
        assert nomes == sorted(nomes)

    def test_demais_municipios_nao_sao_capital(self):
        sp = municipios_da_uf("SP")
        assert all(m["capital"] == 0 for m in sp[1:])

    def test_municipio_tem_campos(self):
        m = municipios_da_uf("SP")[0]
        assert set(m.keys()) == {"id", "nome", "uf", "capital"}
        assert m["uf"] == "SP"

    def test_uf_invalida_retorna_vazia(self):
        assert municipios_da_uf("XX") == []
        assert municipios_da_uf(None) == []
        assert municipios_da_uf("") == []


# ── capital_da_uf ─────────────────────────────────────────────────────


class TestCapitalDaUf:
    def test_capitais_conhecidas(self):
        assert capital_da_uf("SP") == "Sao Paulo"
        assert capital_da_uf("RJ") == "Rio de Janeiro"
        assert capital_da_uf("DF") == "Brasilia"

    def test_case_insensitive(self):
        assert capital_da_uf("df") == "Brasilia"

    def test_capitais_sem_acento(self):
        """CAPITAIS já armazena nomes sem acento (escolha de design do módulo)."""
        import unicodedata

        def _sem_acento(s: str) -> str:
            nfkd = unicodedata.normalize("NFKD", s)
            return "".join(c for c in nfkd if not unicodedata.combining(c))

        for capital in CAPITAIS.values():
            assert capital == _sem_acento(capital)

    def test_uf_invalida_retorna_vazia(self):
        assert capital_da_uf("XX") == ""
        assert capital_da_uf(None) == ""
        assert capital_da_uf("") == ""


# ── _norm ─────────────────────────────────────────────────────────────


class TestNorm:
    def test_none_para_vazio(self):
        assert _norm(None) == ""

    def test_nao_string_convertida(self):
        assert _norm(123) == "123"

    def test_remove_acentos(self):
        assert _norm("São Paulo") == "SAO PAULO"
        assert _norm("Vitória") == "VITORIA"

    def test_colausa_espacos(self):
        assert _norm("  sao   paulo  ") == "SAO PAULO"

    def test_maiusculas(self):
        assert _norm("abc") == "ABC"
