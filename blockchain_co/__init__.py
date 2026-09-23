"""
blockchain_co — Blockchain de Empresas (CNPJ).

Uma cadeia de blocos imutável que registra toda a vida de uma empresa,
da constituição (gênesis) à baixa, incluindo alterações contratuais,
fusões, cisões, dissolução e certidões.

Cada bloco pode ser assinado digitalmente com ECDSA (P-256)
para autenticação e não-repúdio.

Suporta referências cruzadas com blockchain_pf (pessoas físicas),
blockchain_im (imóveis) e blockchain_mo (veículos).
"""

from .events import CompanyEventType, CompanyEventFactory, CompanyChainProtector
from .chain import CompanyChain
from .cross_chain import CrossChainCO, CompanyCrossReference

__version__ = "1.0.0"
__all__ = [
    "CompanyEventType",
    "CompanyEventFactory",
    "CompanyChainProtector",
    "CompanyChain",
    "CrossChainCO",
    "CompanyCrossReference",
]
