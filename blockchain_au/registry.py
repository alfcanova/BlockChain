"""
blockchain_au/registry.py
Registro de autoridades: permissoes e resolucao de regiao por dominio.

Regras:
  - N0 (Brasil, seeds) gerencia qualquer N1/N2 de qualquer escopo/UF.
  - N1 (UF) cria/altera/revoga N2 do MESMO escopo+UF.
  - N1/N2 gerenciam dados do dominio apenas na propria regiao
    (N1: toda a UF; N2: o municipio). N2 nao gerencia autoridades.
  - Autoridade revogada perde todas as permissoes.
"""

import unicodedata
from typing import Any, Optional

from .events import DOMINIOS
from .chain import AuthorityChain


def _norm(s: Any) -> str:
    """Normaliza texto (acentos/maiusculas) para comparacoes de regiao."""
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = unicodedata.normalize("NFKD", s)
    return " ".join(
        "".join(c for c in s if not unicodedata.combining(c)).split()
    ).upper()


class AuthorityRegistry:
    """
    Consultas de permissao e hierarquia sobre as cadeias AU.
    A fonte da verdade e o livro-razao (blocos assinados).
    """

    # Chaves canonicas de regiao no genesis de cada dominio de dados
    REGION_KEYS: dict[str, tuple[str, str]] = {
        "pf": ("uf_nascimento", "cidade_nascimento"),
        "im": ("endereco_uf", "endereco_cidade"),
        "mo": ("uf", "cidade"),
        "co": ("uf", "cidade"),
        "em": ("uf", "cidade"),
        "ac": ("uf", "cidade"),
        "an": ("uf", "cidade"),
    }

    def __init__(self, au_chains: dict[str, AuthorityChain]) -> None:
        self._au_chains = au_chains

    # ── Estado ─────────────────────────────────────────────────────

    def estado(self, username: str) -> dict[str, Any]:
        """Estado vigente de uma autoridade (ou dict vazio se inexistente)."""
        chain = self._au_chains.get(username)
        return chain.get_estado_atual() if chain else {}

    def existe(self, username: str) -> bool:
        return username in self._au_chains

    def ativa(self, username: str) -> bool:
        st = self.estado(username)
        return bool(st) and not st.get("revogado", False)

    # ── Permissoes sobre autoridades ───────────────────────────────

    def can_manage_authority(self, actor: str, target_estado: dict[str, Any]) -> bool:
        """Pode o ator criar/alterar/revogar a autoridade alvo?"""
        actor_estado = self.estado(actor)
        if not actor_estado or actor_estado.get("revogado", False):
            return False
        actor_nivel = actor_estado.get("nivel", 0)
        target_nivel = target_estado.get("nivel", 2)
        actor_username = str(actor_estado.get("username") or actor).strip()

        # Auto-alteracao: N1/N2 alteram as proprias informacoes
        # (fase 1 -> status PENDENTE; a confirmacao vem do superior).
        if str(target_estado.get("username") or "").strip() == actor_username:
            if actor_nivel in (1, 2):
                return True
            return target_nivel in (1, 2)

        if actor_nivel == 0:
            return target_nivel in (1, 2)
        if actor_nivel != 1:
            return False  # N2 nao gerencia outras autoridades
        if target_nivel != 2:
            return False
        same_escopo = _norm(actor_estado.get("escopo")) == _norm(target_estado.get("escopo"))
        same_uf = _norm(actor_estado.get("uf")) == _norm(target_estado.get("uf"))
        return same_escopo and same_uf

    def can_confirmar_alteracao(self, actor: str, target_estado: dict[str, Any]) -> bool:
        """
        Pode o ator CONFIRMAR uma alteracao PENDENTE da autoridade alvo?
        Regras:
          - N1 confirma N2 que nomeou (nomeado_por == actor).
          - N0 confirma N0 (qualquer outro N0 ativo pode confirmar).
          - N2 nao confirma ninguem.
        """
        actor_estado = self.estado(actor)
        if not actor_estado or actor_estado.get("revogado", False):
            return False
        actor_nivel = actor_estado.get("nivel", 0)
        actor_uid = str(actor_estado.get("username") or actor).strip()
        target_uid = str(target_estado.get("username") or "").strip()
        target_nivel = target_estado.get("nivel", 0)
        nomeado_por = str(target_estado.get("nomeado_por") or "").strip()

        # N0: qualquer N0 ativo confirma alteracao de QUALQUER outro N0
        if actor_nivel == 0 and target_nivel == 0 and target_uid != actor_uid:
            return True
        # N1: confirma N2 que ele nomeou
        if actor_nivel == 1:
            return nomeado_por == actor_uid
        return False

    # ── Permissoes sobre dados ─────────────────────────────────────

    def can_manage_domain(self, actor: str) -> bool:
        st = self.estado(actor)
        return bool(st) and not st.get("revogado", False)

    def can_manage_data(
        self, actor: str, domain: str, uf: str, cidade: str = ""
    ) -> bool:
        """Pode o ator registrar/alterar dados do dominio nessa regiao?"""
        st = self.estado(actor)
        if not st or st.get("revogado", False):
            return False
        nivel = st.get("nivel", 0)
        if nivel == 0:
            return True
        if st.get("escopo") != domain:
            return False
        if _norm(st.get("uf")) != _norm(uf):
            return False
        if nivel == 2 and _norm(st.get("cidade")) != _norm(cidade):
            return False
        return nivel in (1, 2)

    # ── Regiao de uma cadeia de dados ──────────────────────────────

    def regiao_da_cadeia(self, domain: str, estado: dict[str, Any]) -> tuple[str, str]:
        """Retorna (uf, cidade) canonicos a partir do estado do registro."""
        k_uf, k_cid = self.REGION_KEYS.get(domain, ("uf", "cidade"))
        return estado.get(k_uf, ""), estado.get(k_cid, "")

    # ── Hierarquia ─────────────────────────────────────────────────

    def nomeadas_por(self, username: str) -> list[dict[str, Any]]:
        """Autoridades nomeadas diretamente pelo ator (para a arvore)."""
        return [
            {"id": cid, **self.estado(cid)}
            for cid, _chain in self._au_chains.items()
            if self.estado(cid).get("nomeado_por") == username
        ]

    def por_escopo(self, escopo: str) -> list[dict[str, Any]]:
        return [
            {"id": cid, **self.estado(cid)}
            for cid, _chain in self._au_chains.items()
            if self.estado(cid).get("escopo") == escopo
        ]

    def por_regiao(self, uf: str = "", cidade: str = "") -> list[dict[str, Any]]:
        out = []
        for cid, _chain in self._au_chains.items():
            st = self.estado(cid)
            if uf and _norm(st.get("uf")) != _norm(uf):
                continue
            if cidade and _norm(st.get("cidade")) != _norm(cidade):
                continue
            out.append({"id": cid, **st})
        return out

    def arvore(self, raiz: str = "") -> list[dict[str, Any]]:
        """
        Arvore hierarquica a partir de um no raiz (recursiva).

        - raiz = autoridade (ex.: N0 'admin01') -> N1 nomeados -> N2 nomeados.
        - raiz vazia: considera todos os N0 como raizes do Brasil.
        """
        if raiz:
            st = self.estado(raiz)
            if not st:
                return []
            return [self._no(raiz, st)]
        raizes = [cid for cid, _c in self._au_chains.items() if self.estado(cid).get("nivel") == 0]
        return [self._no(cid, self.estado(cid)) for cid in sorted(raizes)]

    def _no(self, cid: str, st: dict[str, Any]) -> dict[str, Any]:
        """No da arvore com filhos nomeados pelo proprio."""
        filhos = []
        for child, _c in sorted(self._au_chains.items()):
            child_st = self.estado(child)
            if child_st.get("nomeado_por") == cid:
                filhos.append(self._no(child, child_st))
        return {
            "id": cid,
            "nome": st.get("nome", ""),
            "nivel": st.get("nivel", 0),
            "escopo": st.get("escopo", ""),
            "uf": st.get("uf", ""),
            "cidade": st.get("cidade", ""),
            "revogado": st.get("revogado", False),
            "filhos": filhos,
        }

    def filhos_de(self, username: str, uf: str = "", cidade: str = "") -> list[dict[str, Any]]:
        """
        Filhos diretos do ator (N1 -> N2 no mesmo escopo+UF),
        respeitando o regime de visibilidade da propria regiao.
        """
        out = []
        for cid, _chain in self._au_chains.items():
            st = self.estado(cid)
            if st.get("nomeado_por") != username:
                continue
            if uf and _norm(st.get("uf")) != _norm(uf):
                continue
            if cidade and _norm(st.get("cidade")) != _norm(cidade):
                continue
            out.append({"id": cid, **st})
        return out