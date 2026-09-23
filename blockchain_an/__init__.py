"""
blockchain_an — Blockchain de Animais.

Uma cadeia de blocos imutável que registra toda a vida de um animal,
desde o nascimento/cadastro (gênesis) até o óbito, incluindo
transferências, vacinação, castração e registros veterinários.

Cada bloco pode ser assinado digitalmente com ECDSA (P-256)
para autenticação e não-repúdio.

Suporta referências cruzadas com blockchain_pf (pessoas físicas)
e blockchain_im (imóveis).
"""

from .events import AnimalEventType, AnimalEventFactory, AnimalChainProtector
from .chain import AnimalChain
from .cross_chain import CrossChainAN, AnimalCrossReference

__version__ = "1.0.0"
__all__ = [
    "AnimalEventType",
    "AnimalEventFactory",
    "AnimalChainProtector",
    "AnimalChain",
    "CrossChainAN",
    "AnimalCrossReference",
]
