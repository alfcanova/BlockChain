"""
blockchain_pf — Blockchain de Eventos Vitais de Pessoas Físicas.

Uma cadeia de blocos imutável que registra toda a vida de uma pessoa,
do nascimento ao óbito, incluindo adoções, casamentos, divórcios,
alterações de nome e disvinculações parentais.

Cada bloco pode ser assinado digitalmente com ECDSA (P-256)
para autenticação e não-repúdio.
"""

from .block import Block
from .chain import Blockchain
from .events import EventFactory, EventType, ChainProtector
from .signatures import (
    KeyPair,
    Signer,
    BlockSignature,
    SignatureVerifier,
    generate_authority_keypair,
)
from .graph import RelationshipGraph, Node, Edge, RelationType

__version__ = "3.0.0"
__all__ = [
    "Block",
    "Blockchain",
    "EventFactory",
    "EventType",
    "ChainProtector",
    "KeyPair",
    "Signer",
    "BlockSignature",
    "SignatureVerifier",
    "generate_authority_keypair",
    "RelationshipGraph",
    "Node",
    "Edge",
    "RelationType",
]
