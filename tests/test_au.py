"""Testes do subsystema AU (Autoridades).

Cobre: events, chain, registry, rotas web.
"""
import pytest
from blockchain_au import (
    AuthorityEventType,
    AuthorityEventFactory,
    AuthorityChain,
    AuthorityRegistry,
    DOMINIOS,
)


# ── Events ───────────────────────────────────────────────────────────

class TestAuthorityEventType:
    def test_enum_values(self):
        assert AuthorityEventType.NOMEACAO.value == "NOMEACAO"
        assert AuthorityEventType.ALTERACAO.value == "ALTERACAO"
        assert AuthorityEventType.REVOGACAO.value == "REVOGACAO"
        assert AuthorityEventType.CONFIRMACAO.value == "CONFIRMACAO"
        assert AuthorityEventType.RECUSA.value == "RECUSA"

    def test_enum_count(self):
        assert len(AuthorityEventType) == 5

    def test_string_enum(self):
        assert isinstance(AuthorityEventType.NOMEACAO, str)


class TestAuthorityEventFactory:
    def test_nomeacao_valid(self):
        payload = AuthorityEventFactory.nomeacao(
            nome="Delegacia SP", nivel=1, escopo="pf", uf="SP",
            nomeado_por="admin01",
        )
        assert payload["nome"] == "Delegacia SP"
        assert payload["nivel"] == 1
        assert payload["escopo"] == "pf"
        assert payload["uf"] == "SP"
        assert payload["cidade"] == ""
        assert payload["nomeado_por"] == "admin01"
        assert payload["username"] == ""

    def test_nomeacao_n2_valid(self):
        payload = AuthorityEventFactory.nomeacao(
            nome="Cartorio BH", nivel=2, escopo="co", uf="MG",
            cidade="Belo Horizonte", nomeado_por="n1.co.MG",
        )
        assert payload["nivel"] == 2
        assert payload["cidade"] == "BELO HORIZONTE"

    def test_nomeacao_invalid_nivel(self):
        with pytest.raises(ValueError, match="Nivel"):
            AuthorityEventFactory.nomeacao(nome="X", nivel=0, escopo="pf", uf="SP")

    def test_nomeacao_invalid_escopo(self):
        with pytest.raises(ValueError, match="Escopo"):
            AuthorityEventFactory.nomeacao(nome="X", nivel=1, escopo="XX", uf="SP")

    def test_nomeacao_invalid_uf(self):
        with pytest.raises(ValueError, match="UF"):
            AuthorityEventFactory.nomeacao(nome="X", nivel=1, escopo="pf", uf="XX")

    def test_nomeacao_n1_with_cidade_fails(self):
        with pytest.raises(ValueError, match="cidade"):
            AuthorityEventFactory.nomeacao(
                nome="X", nivel=1, escopo="pf", uf="SP", cidade="Sao Paulo",
            )

    def test_nomeacao_n2_invalid_cidade(self):
        with pytest.raises(ValueError, match="Cidade"):
            AuthorityEventFactory.nomeacao(
                nome="X", nivel=2, escopo="pf", uf="SP", cidade="CidadeInexistente123",
            )

    def test_nomeacao_empty_name_fails(self):
        with pytest.raises(ValueError, match="obrigatorio"):
            AuthorityEventFactory.nomeacao(nome="", nivel=1, escopo="pf", uf="SP")

    def test_alteracao(self):
        payload = AuthorityEventFactory.alteracao(nome="Novo Nome", escopo="pf")
        assert payload["nome"] == "Novo Nome"
        assert payload["escopo"] == "pf"
        assert payload["status"] == "PENDENTE"

    def test_confirmacao(self):
        payload = AuthorityEventFactory.confirmacao(
            username="n1.pf.SP", nome="Delegacia", nivel=1,
            escopo="pf", uf="SP", confirmado_por="admin01",
        )
        assert payload["status"] == "CONFIRMADA"
        assert payload["confirmado_por"] == "admin01"
        assert payload["username"] == "n1.pf.SP"

    def test_recusa(self):
        payload = AuthorityEventFactory.recusa(
            username="n1.pf.SP", nome="Delegacia", nivel=1,
            escopo="pf", uf="SP", recusado_por="admin01",
        )
        assert payload["status"] == "RECUSADA"
        assert payload["recusado_por"] == "admin01"

    def test_revogacao(self):
        payload = AuthorityEventFactory.revogacao(motivo="Teste")
        assert payload["motivo"] == "Teste"
        assert "data" in payload


class TestDOMINIOS:
    def test_seven_domains(self):
        assert len(DOMINIOS) == 7
        assert set(DOMINIOS) == {"pf", "im", "mo", "co", "em", "ac", "an"}


# ── Chain ────────────────────────────────────────────────────────────

class TestAuthorityChain:
    def _make_chain(self):
        chain = AuthorityChain(difficulty=1)
        chain.set_signer(AuthorityChain._signer_class("test_signer") if hasattr(AuthorityChain, '_signer_class') else None)
        return chain

    def test_create_genesis(self):
        chain = AuthorityChain(difficulty=1)
        dados = AuthorityEventFactory.nomeacao(
            nome="Admin SP", nivel=1, escopo="pf", uf="SP",
            nomeado_por="admin01",
        )
        dados["username"] = "n1.pf.SP"
        genesis = chain.create_genesis(dados)
        assert genesis.index == 0
        assert genesis.hash is not None

    def test_get_estado_after_genesis(self):
        chain = AuthorityChain(difficulty=1)
        dados = AuthorityEventFactory.nomeacao(
            nome="Admin SP", nivel=1, escopo="pf", uf="SP",
            nomeado_por="admin01",
        )
        dados["username"] = "n1.pf.SP"
        chain.create_genesis(dados)
        estado = chain.get_estado_atual()
        assert estado["nome"] == "Admin SP"
        assert estado["nivel"] == 1
        assert estado["escopo"] == "pf"
        assert estado["uf"] == "SP"
        assert estado["revogado"] is False

    def test_add_alteracao(self):
        chain = AuthorityChain(difficulty=1)
        dados = AuthorityEventFactory.nomeacao(
            nome="Admin SP", nivel=1, escopo="pf", uf="SP",
            nomeado_por="admin01",
        )
        dados["username"] = "n1.pf.SP"
        chain.create_genesis(dados)
        alteracao = AuthorityEventFactory.alteracao(nome="Admin SP Updated")
        chain.add_event(AuthorityEventType.ALTERACAO.value, alteracao)
        estado = chain.get_estado_atual()
        assert estado["nome"] == "Admin SP Updated"
        assert estado["status"] == "PENDENTE"

    def test_add_confirmacao(self):
        chain = AuthorityChain(difficulty=1)
        dados = AuthorityEventFactory.nomeacao(
            nome="Admin SP", nivel=1, escopo="pf", uf="SP",
            nomeado_por="admin01",
        )
        dados["username"] = "n1.pf.SP"
        chain.create_genesis(dados)
        confirmacao = AuthorityEventFactory.confirmacao(
            username="n1.pf.SP", nome="Admin SP Final", nivel=1,
            escopo="pf", uf="SP", confirmado_por="admin01",
        )
        chain.add_event(AuthorityEventType.CONFIRMACAO.value, confirmacao)
        estado = chain.get_estado_atual()
        assert estado["nome"] == "Admin SP Final"
        assert estado["status"] == "CONFIRMADA"

    def test_add_recusa(self):
        chain = AuthorityChain(difficulty=1)
        dados = AuthorityEventFactory.nomeacao(
            nome="Admin SP", nivel=1, escopo="pf", uf="SP",
            nomeado_por="admin01",
        )
        dados["username"] = "n1.pf.SP"
        chain.create_genesis(dados)
        recusa = AuthorityEventFactory.recusa(
            username="n1.pf.SP", nome="Admin SP Rejected", nivel=1,
            escopo="pf", uf="SP", recusado_por="admin01",
        )
        chain.add_event(AuthorityEventType.RECUSA.value, recusa)
        estado = chain.get_estado_atual()
        assert estado["nome"] == "Admin SP Rejected"
        assert estado["status"] == "RECUSADA"

    def test_revogacao_marks_revoked(self):
        chain = AuthorityChain(difficulty=1)
        dados = AuthorityEventFactory.nomeacao(
            nome="Admin SP", nivel=1, escopo="pf", uf="SP",
            nomeado_por="admin01",
        )
        dados["username"] = "n1.pf.SP"
        chain.create_genesis(dados)
        revogacao = AuthorityEventFactory.revogacao(motivo="Teste")
        chain.add_event(AuthorityEventType.REVOGACAO.value, revogacao)
        estado = chain.get_estado_atual()
        assert estado["revogado"] is True

    def test_chain_length(self):
        chain = AuthorityChain(difficulty=1)
        dados = AuthorityEventFactory.nomeacao(
            nome="Admin SP", nivel=1, escopo="pf", uf="SP",
            nomeado_por="admin01",
        )
        dados["username"] = "n1.pf.SP"
        chain.create_genesis(dados)
        assert len(chain) == 1
        chain.add_event(AuthorityEventType.ALTERACAO.value,
                        AuthorityEventFactory.alteracao(nome="X"))
        assert len(chain) == 2


# ── Registry ─────────────────────────────────────────────────────────

def _build_registry_with_n0():
    """Cria registry com 3 N0 para testes (N0 bypasses _validar_base)."""
    chains = {}
    for uid in ["admin01", "admin02", "admin03"]:
        chain = AuthorityChain(difficulty=1)
        dados = {
            "username": uid,
            "nome": f"Admin {uid[-2:]}",
            "nivel": 0,
            "escopo": "",
            "uf": "",
            "cidade": "",
            "nomeado_por": "",
            "data": "01/01/2026",
            "motivo": "Seed N0",
        }
        chain.create_genesis(dados)
        chains[uid] = chain
    return AuthorityRegistry(chains)


def _add_n1(registry, uid, escopo, uf, nomeado_por):
    """Adiciona N1 ao registry."""
    chain = AuthorityChain(difficulty=1)
    dados = AuthorityEventFactory.nomeacao(
        nome=f"Auth {uf}", nivel=1, escopo=escopo, uf=uf,
        nomeado_por=nomeado_por,
    )
    dados["username"] = uid
    chain.create_genesis(dados)
    registry._au_chains[uid] = chain
    return chain


def _add_n2(registry, uid, escopo, uf, cidade, nomeado_por):
    """Adiciona N2 ao registry."""
    chain = AuthorityChain(difficulty=1)
    dados = AuthorityEventFactory.nomeacao(
        nome=f"Auth {cidade}", nivel=2, escopo=escopo, uf=uf,
        cidade=cidade, nomeado_por=nomeado_por,
    )
    dados["username"] = uid
    chain.create_genesis(dados)
    registry._au_chains[uid] = chain
    return chain


class TestAuthorityRegistry:
    def test_estado(self):
        reg = _build_registry_with_n0()
        st = reg.estado("admin01")
        assert st["nome"] == "Admin 01"
        assert st["nivel"] == 0

    def test_estado_inexistente(self):
        reg = _build_registry_with_n0()
        assert reg.estado("nao_existe") == {}

    def test_existe(self):
        reg = _build_registry_with_n0()
        assert reg.existe("admin01") is True
        assert reg.existe("nao_existe") is False

    def test_ativa(self):
        reg = _build_registry_with_n0()
        assert reg.ativa("admin01") is True

    def test_ativa_revogada(self):
        reg = _build_registry_with_n0()
        chain = reg._au_chains["admin01"]
        chain.add_event(AuthorityEventType.REVOGACAO.value,
                        AuthorityEventFactory.revogacao())
        assert reg.ativa("admin01") is False


class TestCanManageAuthority:
    def test_n0_manages_n1(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        target = reg.estado("n1.pf.SP")
        assert reg.can_manage_authority("admin01", target) is True

    def test_n0_manages_n2(self):
        reg = _build_registry_with_n0()
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "admin01")
        target = reg.estado("n2.pf.SP.sao-paulo")
        assert reg.can_manage_authority("admin01", target) is True

    def test_n1_manages_n2_same_scope_uf(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "n1.pf.SP")
        target = reg.estado("n2.pf.SP.sao-paulo")
        assert reg.can_manage_authority("n1.pf.SP", target) is True

    def test_n1_cannot_manage_n2_different_uf(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        _add_n2(reg, "n2.pf.RJ.rio", "pf", "RJ", "Rio de Janeiro", "admin01")
        target = reg.estado("n2.pf.RJ.rio")
        assert reg.can_manage_authority("n1.pf.SP", target) is False

    def test_n2_cannot_manage任何人(self):
        reg = _build_registry_with_n0()
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "admin01")
        _add_n1(reg, "n1.pf.RJ", "pf", "RJ", "admin01")
        target = reg.estado("n1.pf.RJ")
        assert reg.can_manage_authority("n2.pf.SP.sao-paulo", target) is False

    def test_n1_self_alteration(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        target = reg.estado("n1.pf.SP")
        assert reg.can_manage_authority("n1.pf.SP", target) is True

    def test_n2_self_alteration(self):
        reg = _build_registry_with_n0()
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "admin01")
        target = reg.estado("n2.pf.SP.sao-paulo")
        assert reg.can_manage_authority("n2.pf.SP.sao-paulo", target) is True

    def test_revoked_cannot_manage(self):
        reg = _build_registry_with_n0()
        chain = reg._au_chains["admin01"]
        chain.add_event(AuthorityEventType.REVOGACAO.value,
                        AuthorityEventFactory.revogacao())
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        target = reg.estado("n1.pf.SP")
        assert reg.can_manage_authority("admin01", target) is False


class TestCanConfirmarAlteracao:
    def test_n1_confirms_n2_they_nominated(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "n1.pf.SP")
        target = reg.estado("n2.pf.SP.sao-paulo")
        assert reg.can_confirmar_alteracao("n1.pf.SP", target) is True

    def test_n1_cannot_confirm_n2_they_didnt_nominate(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "admin01")
        target = reg.estado("n2.pf.SP.sao-paulo")
        assert reg.can_confirmar_alteracao("n1.pf.SP", target) is False

    def test_n0_cannot_confirm_own_changes(self):
        reg = _build_registry_with_n0()
        target = reg.estado("admin01")
        assert reg.can_confirmar_alteracao("admin01", target) is False

    def test_n0_can_confirm_other_n0(self):
        reg = _build_registry_with_n0()
        target = reg.estado("admin01")
        assert reg.can_confirmar_alteracao("admin02", target) is True
        assert reg.can_confirmar_alteracao("admin03", target) is True

    def test_n2_cannot_confirm任何人(self):
        reg = _build_registry_with_n0()
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "admin01")
        _add_n1(reg, "n1.pf.RJ", "pf", "RJ", "admin01")
        target = reg.estado("n1.pf.RJ")
        assert reg.can_confirmar_alteracao("n2.pf.SP.sao-paulo", target) is False

    def test_revoked_cannot_confirm(self):
        reg = _build_registry_with_n0()
        chain = reg._au_chains["admin02"]
        chain.add_event(AuthorityEventType.REVOGACAO.value,
                        AuthorityEventFactory.revogacao())
        target = reg.estado("admin01")
        assert reg.can_confirmar_alteracao("admin02", target) is False


class TestCanManageData:
    def test_n0_manages_any_data(self):
        reg = _build_registry_with_n0()
        assert reg.can_manage_data("admin01", "pf", "SP", "Sao Paulo") is True

    def test_n1_manages_data_same_scope_uf(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        assert reg.can_manage_data("n1.pf.SP", "pf", "SP") is True

    def test_n1_cannot_manage_data_different_uf(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        assert reg.can_manage_data("n1.pf.SP", "pf", "RJ") is False

    def test_n1_cannot_manage_data_different_scope(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        assert reg.can_manage_data("n1.pf.SP", "mo", "SP") is False

    def test_n2_manages_data_same_city(self):
        reg = _build_registry_with_n0()
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "admin01")
        assert reg.can_manage_data("n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo") is True

    def test_n2_cannot_manage_data_different_city(self):
        reg = _build_registry_with_n0()
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "admin01")
        assert reg.can_manage_data("n2.pf.SP.sao-paulo", "pf", "SP", "Campinas") is False


class TestArvore:
    def test_arvore_empty(self):
        reg = AuthorityRegistry({})
        assert reg.arvore() == []

    def test_arvore_with_n0(self):
        reg = _build_registry_with_n0()
        tree = reg.arvore()
        assert len(tree) == 3
        ids = {n["id"] for n in tree}
        assert "admin01" in ids

    def test_arvore_with_hierarchy(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "n1.pf.SP")
        tree = reg.arvore()
        n0_node = next(n for n in tree if n["id"] == "admin01")
        assert len(n0_node["filhos"]) == 1
        n1_node = n0_node["filhos"][0]
        assert n1_node["id"] == "n1.pf.SP"
        assert len(n1_node["filhos"]) == 1
        assert n1_node["filhos"][0]["id"] == "n2.pf.SP.sao-paulo"

    def test_filhos_de(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        _add_n2(reg, "n2.pf.SP.sao-paulo", "pf", "SP", "Sao Paulo", "n1.pf.SP")
        filhos = reg.filhos_de("admin01")
        assert len(filhos) == 1
        assert filhos[0]["id"] == "n1.pf.SP"

    def test_nomeadas_por(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        _add_n1(reg, "n1.mo.RJ", "mo", "RJ", "admin01")
        nomeadas = reg.nomeadas_por("admin01")
        assert len(nomeadas) == 2


class TestPorRegiao:
    def test_por_uf(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        _add_n1(reg, "n1.pf.RJ", "pf", "RJ", "admin01")
        sp = reg.por_regiao(uf="SP")
        assert len(sp) == 1
        assert sp[0]["id"] == "n1.pf.SP"

    def test_por_escopo(self):
        reg = _build_registry_with_n0()
        _add_n1(reg, "n1.pf.SP", "pf", "SP", "admin01")
        _add_n1(reg, "n1.mo.SP", "mo", "SP", "admin01")
        pf = reg.por_escopo("pf")
        assert len(pf) == 1
