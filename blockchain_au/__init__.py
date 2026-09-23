"""
blockchain_au
Cadeias de Autoridade (AU): hierarquia nacional de emissores.

Nivel 0: Brasil (admin01-03, seeds) — nomeia/gerencia qualquer N1/N2.
Nivel 1: UF  (escopo + UF)  — cria N2 no mesmo escopo+UF; gerencia dados na UF.
Nivel 2: Cidade (escopo + UF + cidade IBGE) — gerencia dados no municipio.

Livro-razao imutavel: geneses NOMEACAO, blocos ALTERACAO/REVOGACAO em cadeia
Hashchain assinada ECDSA (blockchain_pf.Blockchain).
"""

from .events import AuthorityEventType, AuthorityEventFactory, DOMINIOS
from .chain import AuthorityChain
from .registry import AuthorityRegistry

__all__ = [
    "AuthorityEventType",
    "AuthorityEventFactory",
    "AuthorityChain",
    "AuthorityRegistry",
    "DOMINIOS",
]