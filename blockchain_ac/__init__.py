"""
blockchain_ac — Blockchain de Aeronaves.

Uma cadeia de blocos imutável que registra toda a vida útil de uma aeronave,
desde a fabricação (gênesis) até a baixa, incluindo transferências,
manutenção, inspeções e certidões.

Cada bloco pode ser assinado digitalmente com ECDSA (P-256)
para autenticação e não-repúdio.

Suporta referências cruzadas com blockchain_pf (pessoas físicas)
e blockchain_im (imóveis).
"""

from .events import AircraftEventType, AircraftEventFactory, AircraftChainProtector
from .chain import AircraftChain
from .cross_chain import CrossChainAC, AircraftCrossReference

__version__ = "1.0.0"
__all__ = [
    "AircraftEventType",
    "AircraftEventFactory",
    "AircraftChainProtector",
    "AircraftChain",
    "CrossChainAC",
    "AircraftCrossReference",
]
