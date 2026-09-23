"""
blockchain_em — Blockchain de Embarcações.

Uma cadeia de blocos imutável que registra toda a vida útil de uma embarcação,
desde a construção (gênesis) até a baixa, incluindo transferências,
inspeções, manutenção e licenciamento.

Cada bloco pode ser assinado digitalmente com ECDSA (P-256)
para autenticação e não-repúdio.

Suporta referências cruzadas com blockchain_pf (pessoas físicas)
e blockchain_im (imóveis).
"""

from .events import VesselEventType, VesselEventFactory, VesselChainProtector
from .chain import VesselChain
from .cross_chain import CrossChainEM, VesselCrossReference

__version__ = "1.0.0"
__all__ = [
    "VesselEventType",
    "VesselEventFactory",
    "VesselChainProtector",
    "VesselChain",
    "CrossChainEM",
    "VesselCrossReference",
]
