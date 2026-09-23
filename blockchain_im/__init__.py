"""
blockchain_im — Blockchain de Imóveis.

Uma cadeia de blocos imutável que registra toda a vida de um imóvel,
do cadastro do terreno (gênesis no espaço geográfico real) ao
desmembramento, fusão, transferências, garantias e leilões.

Cada bloco pode ser assinado digitalmente com ECDSA (P-256)
para autenticação e não-repúdio.

Suporta referências cruzadas com blockchain_pf (pessoas físicas).
"""

from .events import PropertyEventType, PropertyEventFactory, PropertyChainProtector
from .chain import PropertyChain
from .cross_chain import CrossChainManager, CrossReference

__version__ = "1.0.0"
__all__ = [
    "PropertyEventType",
    "PropertyEventFactory",
    "PropertyChainProtector",
    "PropertyChain",
    "CrossChainManager",
    "CrossReference",
]
