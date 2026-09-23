"""
blockchain_pf/geografia_br.py
Base de consulta de UFs e municipios brasileiros.

Fonte: tabela oficial IBGE (database/ibge_municipios.json), gerada a partir de
https://servicodados.ibge.gov.br/api/v1/localidades/municipios

Usada pelos blocos dos 7 dominios para validar cidade/UF de forma estrita e
pelos endpoints de consulta GET /api/geografia/*.
"""

import json
import os
import unicodedata
from typing import Optional

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MUNICIPIOS_PATH = os.path.join(_PROJECT_ROOT, "database", "ibge_municipios.json")

# 27 UFs: (sigla, nome, regiao)
UFS = [
    ("AC", "Acre", "Norte"),
    ("AL", "Alagoas", "Nordeste"),
    ("AP", "Amapa", "Norte"),
    ("AM", "Amazonas", "Norte"),
    ("BA", "Bahia", "Nordeste"),
    ("CE", "Ceara", "Nordeste"),
    ("DF", "Distrito Federal", "Centro-Oeste"),
    ("ES", "Espirito Santo", "Sudeste"),
    ("GO", "Goias", "Centro-Oeste"),
    ("MA", "Maranhao", "Nordeste"),
    ("MT", "Mato Grosso", "Centro-Oeste"),
    ("MS", "Mato Grosso do Sul", "Centro-Oeste"),
    ("MG", "Minas Gerais", "Sudeste"),
    ("PA", "Para", "Norte"),
    ("PB", "Paraiba", "Nordeste"),
    ("PR", "Parana", "Sul"),
    ("PE", "Pernambuco", "Nordeste"),
    ("PI", "Piaui", "Nordeste"),
    ("RJ", "Rio de Janeiro", "Sudeste"),
    ("RN", "Rio Grande do Norte", "Nordeste"),
    ("RS", "Rio Grande do Sul", "Sul"),
    ("RO", "Rondonia", "Norte"),
    ("RR", "Roraima", "Norte"),
    ("SC", "Santa Catarina", "Sul"),
    ("SP", "Sao Paulo", "Sudeste"),
    ("SE", "Sergipe", "Nordeste"),
    ("TO", "Tocantins", "Norte"),
]

UFS_SIGLAS = {sigla for sigla, _nome, _regiao in UFS}
UF_NOMES = {sigla: nome for sigla, nome, _regiao in UFS}

CAPITAIS = {
    "AC": "Rio Branco", "AL": "Maceio", "AP": "Macapa", "AM": "Manaus",
    "BA": "Salvador", "CE": "Fortaleza", "DF": "Brasilia", "ES": "Vitoria",
    "GO": "Goiania", "MA": "Sao Luis", "MT": "Cuiaba", "MS": "Campo Grande",
    "MG": "Belo Horizonte", "PA": "Belem", "PB": "Joao Pessoa", "PR": "Curitiba",
    "PE": "Recife", "PI": "Teresina", "RJ": "Rio de Janeiro", "RN": "Natal",
    "RS": "Porto Alegre", "RO": "Porto Velho", "RR": "Boa Vista",
    "SC": "Florianopolis", "SP": "Sao Paulo", "SE": "Aracaju", "TO": "Palmas",
}


def _norm(s: str) -> str:
    """Normaliza string: sem acentos, sem espacos extras, maiuscula."""
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.split()).upper()


def _load_municipios() -> list[dict]:
    try:
        with open(_MUNICIPIOS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return [{"id": int(m["id"]), "nome": m["nome"], "uf": m["uf"],
             "capital": int(m.get("capital", 0))} for m in data]


MUNICIPIOS = _load_municipios()

# Cache de busca normalizada: (uf_norm, cidade_norm) -> entrada
_MUNICIPIO_INDEX: dict[tuple[str, str], dict] = {}
for _m in MUNICIPIOS:
    _MUNICIPIO_INDEX.setdefault((_m["uf"], _norm(_m["nome"])), _m)


def validar_uf(uf: Optional[str]) -> bool:
    """True se UF for uma das 27 siglas oficiais (case-insensitive)."""
    return uf is not None and str(uf).strip().upper() in UFS_SIGLAS


def municipios_da_uf(uf: Optional[str]) -> list[dict]:
    """Lista de municipios de uma UF (id, nome, capital), em ordem alfabetica."""
    if not validar_uf(uf):
        return []
    lista = [dict(m) for m in MUNICIPIOS if m["uf"] == uf.strip().upper()]
    lista.sort(key=lambda m: (not m["capital"], _norm(m["nome"])))
    return lista


def validar_cidade(uf: Optional[str], cidade: Optional[str]) -> bool:
    """
    Validacao estrita: a cidade precisa existir na tabela oficial da UF.
    Case/accent-insensitive. Lista oficial: 5.571 municipios IBGE.
    """
    if not validar_uf(uf) or not cidade or not str(cidade).strip():
        return False
    return (uf.strip().upper(), _norm(str(cidade))) in _MUNICIPIO_INDEX


def capital_da_uf(uf: Optional[str]) -> str:
    """Nome da capital de uma UF (sem acento)."""
    if not validar_uf(uf):
        return ""
    return CAPITAIS.get(uf.strip().upper(), "")


def total_municipios() -> int:
    return len(MUNICIPIOS)