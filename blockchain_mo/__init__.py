"""
blockchain_mo — Blockchain de Móveis (Veículos).

Uma cadeia de blocos imutável que registra toda a vida útil de um veículo,
desde a fabricação (gênesis) até a baixa, incluindo transferências,
sinistros, multas, garantias, leilões, troca de peças e validação.

Cada bloco pode ser assinado digitalmente com ECDSA (P-256)
para autenticação e não-repúdio.

Suporta referências cruzadas com blockchain_pf (pessoas físicas)
e blockchain_im (imóveis).
"""

from .events import VehicleEventType, VehicleEventFactory, VehicleChainProtector
from .chain import VehicleChain
from .cross_chain import CrossChainMO, VehicleCrossReference

__version__ = "1.0.0"
__all__ = [
    "VehicleEventType",
    "VehicleEventFactory",
    "VehicleChainProtector",
    "VehicleChain",
    "CrossChainMO",
    "VehicleCrossReference",
]
