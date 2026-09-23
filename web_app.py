#!/usr/bin/env python3
"""
web_app.py — Interface Web para a Blockchain de Eventos Vitais PF.

Roda com: PYTHONIOENCODING=utf-8 python web_app.py
Acesse em: http://localhost:8000

Endpoints:
  GET  /                         → Interface web (HTML)
  GET  /api/health               → Status do servidor
  POST /api/chain                → Criar nova cadeia para uma PF
  GET  /api/chain/{cpf}          → Obter dados da cadeia
  GET  /api/chain/{cpf}/timeline → Timeline completa
  POST /api/chain/{cpf}/event    → Registrar novo evento
  GET  /api/chain/{cpf}/validate → Validar cadeia
  POST /api/chain/{cpf}/sign     → Configurar assinador ECDSA
  GET  /api/chain/{cpf}/signatures → Verificar assinaturas
  GET  /api/chain/{cpf}/predictions → Gerar predicoes
  GET  /api/chain/{cpf}/export   → Exportar cadeia JSON
  DELETE /api/chain/{cpf}        → Remover cadeia
  GET  /api/chains               → Listar todas as cadeias
"""

import json
import re
import time
import os
import secrets
import sys
import unicodedata
from typing import Any, Optional, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from blockchain_pf import (
    Blockchain, EventFactory, EventType, ChainProtector,
    KeyPair, Signer, generate_authority_keypair,
    BlockSignature, SignatureVerifier,
)
from blockchain_pf.predictor import LifeEventPredictor
from blockchain_im import (
    PropertyChain,
    PropertyEventFactory,
    PropertyEventType,
    CrossChainManager,
    CrossReference,
)
from blockchain_au import (
    AuthorityChain,
    AuthorityEventFactory,
    AuthorityEventType,
    AuthorityRegistry,
)
from blockchain_mo import (
    VehicleChain,
    VehicleEventFactory,
    VehicleEventType,
    CrossChainMO,
    VehicleCrossReference,
)
from blockchain_co import (
    CompanyChain,
    CompanyEventFactory,
    CompanyEventType,
    CrossChainCO,
    CompanyCrossReference,
)
from blockchain_em import (
    VesselChain,
    VesselEventFactory,
    VesselEventType,
    CrossChainEM,
    VesselCrossReference,
)
from blockchain_ac import (
    AircraftChain,
    AircraftEventFactory,
    AircraftEventType,
    CrossChainAC,
    AircraftCrossReference,
)
from blockchain_an import (
    AnimalChain,
    AnimalEventFactory,
    AnimalEventType,
    CrossChainAN,
    AnimalCrossReference,
)
from blockchain_pf.graph import RelationshipGraph, Node, Edge, RelationType
from blockchain_pf.auth import (
    create_access_token, authenticate_user, get_user,
    create_user, list_users, delete_user, init_default_users,
    init_default_authorities, update_user_metadata,
    get_current_user, require_write_access, require_admin,
    require_nivel_atual,
    set_database as set_auth_database,
)
from blockchain_pf.database import Database
from blockchain_pf import geografia_br as geografia


# ── App ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Blockchain PF — Eventos Vitais",
    description="API REST para cadeia de blocos de eventos vitais de Pessoa Fisica.",
    version="2.0.0",
)

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins_env.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Armazenamento em memoria ──────────────────────────────────────────

chains: Dict[str, Blockchain] = {}
im_chains: Dict[str, PropertyChain] = {}
mo_chains: Dict[str, VehicleChain] = {}
co_chains: Dict[str, CompanyChain] = {}
em_chains: Dict[str, VesselChain] = {}
ac_chains: Dict[str, AircraftChain] = {}
an_chains: Dict[str, AnimalChain] = {}
au_chains: Dict[str, AuthorityChain] = {}
cross_manager = CrossChainManager()
cross_mo = CrossChainMO()
cross_co = CrossChainCO()
cross_em = CrossChainEM()
cross_ac = CrossChainAC()
cross_an = CrossChainAN()
pf_graph = RelationshipGraph()


# ── Models Pydantic ────────────────────────────────────────────────────

class NascimentoRequest(BaseModel):
    cpf: str = Field(..., description="CPF (11 digitos)")
    nome_completo: str
    data_nascimento: str = Field(..., description="DD/MM/AAAA")
    sexo: str = Field(..., description="M ou F")
    cidade_nascimento: str
    uf_nascimento: str
    nome_mae: str
    nome_pai: Optional[str] = None

class EventoRequest(BaseModel):
    event_type: str = Field(..., description="Tipo do evento")
    payload: dict = Field(..., description="Dados do evento")

class CasamentoRequest(BaseModel):
    cpf: str
    nome_conjuge: str
    cpf_conjuge: str
    data_casamento: str
    regime_bens: str = "COMUNHAO_PARCIAL"
    cidade: str = ""
    uf: str = ""

class DivorcioRequest(BaseModel):
    cpf: str
    data_divorcio: str
    tipo: str = "CONSENSUAL"
    guarda_filhos: Optional[str] = None
    pensao_alimenticia: bool = False

class AdocaoRequest(BaseModel):
    cpf: str
    nome_adotivo: Optional[str] = None
    data_adocao: str
    nome_mae_adotiva: str
    nome_pai_adotivo: Optional[str] = None
    mantem_nome_biologico: bool = False

class ObitoRequest(BaseModel):
    cpf: str
    data_obito: str
    cidade_obito: str
    uf_obito: str
    causa_morte: Optional[str] = None

class AlteracaoNomeRequest(BaseModel):
    cpf: str
    nome_anterior: str
    nome_novo: str
    data_alteracao: str
    motivo: str = ""

class DisvinculacaoRequest(BaseModel):
    cpf: str
    data_disvinculacao: str
    motivo: str
    tipo: str = Field("M", description="M=materna, P=paterna")

class VacinaRequest(BaseModel):
    cpf: str
    nome_vacina: str = Field(..., description="Nome da vacina")
    data_vacinacao: str = Field(..., description="DD/MM/AAAA")
    lote: str = ""
    fabricante: str = ""
    dose: str = Field("", description="Ex: 1a dose, 2a dose, Reforco")
    unidade_saude: str = ""
    cidade: str = ""
    uf: str = ""

class ProteseRequest(BaseModel):
    cpf: str
    nome_protese: str = Field(..., description="Nome da protese")
    data_implantacao: str = Field(..., description="DD/MM/AAAA")
    tipo: str = Field("", description="Ortopedica, Cardiaca, Dental, etc")
    marca_modelo: str = ""
    medico_responsavel: str = ""
    hospital_clinica: str = ""
    cidade: str = ""
    uf: str = ""
    data_remocao: Optional[str] = None
    motivo_remocao: str = ""

class CNHRequest(BaseModel):
    cpf: str
    numero_cnh: str = Field(..., description="Numero da CNH")
    categoria: str = Field(..., description="A, B, C, D, E, AB, etc")
    data_emissao: str = Field(..., description="DD/MM/AAAA")
    data_validade: str = Field(..., description="DD/MM/AAAA")
    orgao_emissor: str = ""
    uf_emissao: str = ""
    situacao: str = "VALIDA"
    pontos: int = 0
    exame_medico: str = ""
    data_exame_medico: str = ""

class TituloEleitorRequest(BaseModel):
    cpf: str
    numero_titulo: str = Field(..., description="12 digitos")
    zona_eleitoral: str = Field(..., description="Zona eleitoral")
    secao_eleitoral: str = Field(..., description="Secao eleitoral")
    municipio: str = Field(..., description="Municipio de registro")
    uf: str = Field(..., description="UF de registro")
    data_emissao: str = Field(..., description="DD/MM/AAAA")
    situacao: str = "REGULAR"
    titulo_anterior: str = ""

class EscolaridadeRequest(BaseModel):
    cpf: str
    nivel: str = Field(..., description="Fundamental, Medio, Tecnico, Superior, Pos, Mestrado, Doutorado")
    instituicao: str = Field(..., description="Nome da instituicao de ensino")
    data_inicio: str = ""
    data_conclusao: str = ""
    curso: str = ""
    serie_ano: str = ""
    situacao: str = "EM_ANDAMENTO"
    registro: str = ""
    tipo_registro: str = ""

class SignerRequest(BaseModel):
    label: str = Field("autoridade", description="Nome da autoridade")

class ChainCreateRequest(BaseModel):
    difficulty: int = Field(2, ge=1, le=5)
    signer_label: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str = Field("admin", description="admin | user | readonly")

# ── Models para Imóveis ─────────────────────────────────────────────

class TerrenoRequest(BaseModel):
    matricula: str
    endereco_logradouro: str
    endereco_bairro: str
    endereco_cidade: str
    endereco_uf: str
    endereco_cep: str
    lat: float
    lon: float
    area_terreno_m2: float
    metragem_frente: float = 0.0
    metragem_fundo: float = 0.0
    metragem_lado_esq: float = 0.0
    metragem_lado_dir: float = 0.0
    zoneamento: str = ""
    uso_permitido: list = []
    altura_maxima: float = 0.0
    taxa_ocupacao: float = 0.0
    cacau_permitido: float = 0.0
    codigo_iptu: str = ""
    proprietarios: list = []

class ConstrucaoRequest(BaseModel):
    matricula: str
    descricao: str
    area_construida_m2: float
    tipo_construcao: str = "RESIDENCIAL"
    pavimentos: int = 1
    data_inicio: str = ""
    data_fim: str = ""
    responsavel_tecnico: str = ""
    CRECI: str = ""
    alvara_numero: str = ""

class DemolicaoRequest(BaseModel):
    matricula: str
    descricao: str
    area_demolida_m2: float
    motivo: str = ""
    data_demolicao: str = ""
    responsavel_tecnico: str = ""

class ReformaRequest(BaseModel):
    matricula: str
    descricao: str
    tipo: str = Field(..., description="AMPLIACAO ou REDUCAO")
    area_anterior_m2: float
    area_nova_m2: float
    data_inicio: str = ""
    data_fim: str = ""
    responsavel_tecnico: str = ""
    alvara_numero: str = ""

class CompraVendaRequest(BaseModel):
    matricula: str
    comprador_cpf: str
    comprador_nome: str
    vendedor_cpf: str
    vendedor_nome: str
    valor_transacao: float
    data_transacao: str
    escritura_numero: str = ""
    cartorio: str = ""

class DoacaoRequest(BaseModel):
    matricula: str
    donatario_cpf: str
    donatario_nome: str
    doador_cpf: str
    doador_nome: str
    data_doacao: str
    motivo: str = ""

class HerancaRequest(BaseModel):
    matricula: str
    inventariado_cpf: str
    inventariado_nome: str
    herdeiros: list
    data_obito: str
    data_inventario: str = ""
    inventario_tipo: str = "JUDICIAL"

class GarantiaRequest(BaseModel):
    matricula: str
    credor_nome: str
    credor_cnpj: str
    valor_garantia: float
    data_garantia: str
    data_vencimento: str
    tipo_garantia: str = "HIPOTECARIA"
    taxa_juros: float = 0.0
    prazo_meses: int = 0

class LeilaoRequest(BaseModel):
    matricula: str
    data_leilao: str
    valor_minimo: float
    lance_vencedor: float = 0.0
    vencedor_cpf: str = ""
    vencedor_nome: str = ""
    leiloeiro: str = ""
    tipo: str = "JUDICIAL"

class ImovelGenericoRequest(BaseModel):
    event_type: str
    payload: dict


# ── Models Criação: MO / CO / EM / AC / AN ─────────────────────────────
# Campos obrigatorios das factories de genesis; extras ignorados para
# nao quebrar clientes existentes.

class VehicleCreateRequest(BaseModel):
    model_config = {"extra": "ignore"}
    placa: str
    renavan: str
    chassis: str
    marca: str
    modelo: str
    ano_fabricacao: int = Field(ge=1900)
    ano_modelo: int = Field(ge=1900)
    cor: str
    combustivel: str
    uf: str
    cidade: str
    cilindradas: int = Field(ge=0)
    potencia_cv: float = Field(ge=0)

class CompanyCreateRequest(BaseModel):
    model_config = {"extra": "ignore"}
    cnpj: str
    razao_social: str
    nome_fantasia: str
    data_constituicao: str
    tipo_empresa: str
    porte: str
    capital_social: float = Field(ge=0)
    uf: str
    cidade: str
    natureza_juridica: str
    atividade_principal: str

class VesselCreateRequest(BaseModel):
    model_config = {"extra": "ignore"}
    registro_nr: str
    nome_embarcacao: str
    tipo_embarcacao: str
    porte: str
    comprimento_m: float = Field(ge=0)
    beam_m: float = Field(ge=0)
    pontal_m: float = Field(ge=0)
    calado_m: float = Field(ge=0)
    deslocamento_ton: float = Field(ge=0)
    casco_material: str
    uf: str
    cidade: str
    motorizacao: str
    motor_potencia_cv: float = Field(ge=0)

class AircraftCreateRequest(BaseModel):
    model_config = {"extra": "ignore"}
    matricula: str
    nome_aeronave: str
    fabricante: str
    modelo: str
    tipo_aeronave: str
    ano_fabricacao: int = Field(ge=1900)
    peso_max_decolagem_kg: float = Field(ge=0)
    uf: str
    cidade: str
    motorizacao: str
    num_motores: int = Field(ge=0)

class AnimalCreateRequest(BaseModel):
    model_config = {"extra": "ignore"}
    nome: str
    especie: str
    raca: str
    sexo: str
    data_nascimento: str
    cor: str
    peso_kg: float = Field(ge=0)
    uf: str
    cidade: str
    proprietario_cpf: str
    proprietario_nome: str

class CrossVinculoRequest(BaseModel):
    origem_tipo: str
    origem_id: str
    destino_tipo: str
    destino_id: str
    tipo_vinculo: str
    bloco_origem: Optional[int] = None
    bloco_destino: Optional[int] = None
    dados: Dict = {}


# ── Helpers ────────────────────────────────────────────────────────────

def get_chain(cpf: str) -> Blockchain:
    cpf_clean = cpf.replace(".", "").replace("-", "").replace("/", "")
    if cpf_clean not in chains:
        raise HTTPException(status_code=404, detail=f"Cadeia nao encontrada para CPF: {cpf}")
    return chains[cpf_clean]


def ok(data: Any = None, message: str = "OK") -> dict:
    return {"status": "ok", "message": message, "data": data}


def _validate_event_type(enum_cls, event_type: str) -> str:
    """Valida que event_type pertence ao enum do dominio. Retorna o evento validado."""
    allowed = {e.value for e in enum_cls}
    if event_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de evento invalido: {event_type}. Permitidos: {sorted(allowed)}",
        )
    return event_type


# ── Landing Pages ─────────────────────────────────────────────────────

def _read_html(filename: str) -> str:
    """Lê um arquivo HTML da pasta do projeto."""
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/", response_class=HTMLResponse)
def landing_home():
    """Landing page principal com links para cada blockchain."""
    html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blockchain Brasil — Sistema de Registro</title>
<style>
  :root {
    --bg: #0a0e17; --surface: #111827; --surface2: #1e293b;
    --border: #334155; --text: #e2e8f0; --text2: #94a3b8;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

  .hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border-bottom: 1px solid var(--border); padding: 80px 32px; text-align: center;
  }
  .hero h1 { font-size: 3rem; font-weight: 800; margin-bottom: 16px; }
  .hero h1 span { color: #8b5cf6; }
  .hero p { font-size: 1.2rem; color: var(--text2); max-width: 700px; margin: 0 auto; }

  .container { max-width: 1000px; margin: 0 auto; padding: 48px 24px; }

  .blockchains {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 32px;
  }
  @media (max-width: 768px) { .blockchains { grid-template-columns: 1fr; } }

  .bc-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 16px;
    padding: 32px 24px; text-align: center; transition: all 0.3s; text-decoration: none; color: inherit;
  }
  .bc-card:hover { transform: translateY(-4px); box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
  .bc-card.pf { border-color: #3b82f6; }
  .bc-card.pf:hover { border-color: #60a5fa; box-shadow: 0 8px 32px rgba(59,130,246,0.2); }
  .bc-card.im { border-color: #22c55e; }
  .bc-card.im:hover { border-color: #4ade80; box-shadow: 0 8px 32px rgba(34,197,94,0.2); }
  .bc-card.mo { border-color: #f59e0b; }
  .bc-card.mo:hover { border-color: #fbbf24; box-shadow: 0 8px 32px rgba(245,158,11,0.2); }
  .bc-card.co { border-color: #8b5cf6; }
  .bc-card.co:hover { border-color: #a78bfa; box-shadow: 0 8px 32px rgba(139,92,246,0.2); }
  .bc-card.em { border-color: #06b6d4; }
  .bc-card.em:hover { border-color: #22d3ee; box-shadow: 0 8px 32px rgba(6,182,212,0.2); }
  .bc-card.ac { border-color: #ec4899; }
  .bc-card.ac:hover { border-color: #f472b6; box-shadow: 0 8px 32px rgba(236,72,153,0.2); }
  .bc-card.an { border-color: #10b981; }
  .bc-card.an:hover { border-color: #34d399; box-shadow: 0 8px 32px rgba(16,185,129,0.2); }
  .bc-card.au { border-color: #f43f5e; }
  .bc-card.au:hover { border-color: #fb7185; box-shadow: 0 8px 32px rgba(244,63,94,0.2); }

  .bc-card .icon { font-size: 3rem; margin-bottom: 16px; }
  .bc-card h2 { font-size: 1.4rem; font-weight: 700; margin-bottom: 8px; }
  .bc-card .subtitle { color: var(--text2); font-size: 0.9rem; margin-bottom: 16px; }
  .bc-card .desc { color: var(--text2); font-size: 0.85rem; line-height: 1.6; margin-bottom: 20px; }
  .bc-card .btn {
    display: inline-block; padding: 10px 24px; border-radius: 8px; font-weight: 700;
    font-size: 0.9rem; transition: all 0.2s;
  }
  .bc-card.pf .btn { background: #3b82f6; color: white; }
  .bc-card.im .btn { background: #22c55e; color: #000; }
  .bc-card.mo .btn { background: #f59e0b; color: #000; }
  .bc-card.co .btn { background: #8b5cf6; color: white; }
  .bc-card.em .btn { background: #06b6d4; color: white; }
  .bc-card.ac .btn { background: #ec4899; color: white; }
  .bc-card.an .btn { background: #10b981; color: white; }
  .bc-card.au .btn { background: #f43f5e; color: white; }
  .bc-card .btn:hover { opacity: 0.9; }

  .section-title {
    font-size: 1.5rem; font-weight: 700; margin-top: 48px; margin-bottom: 24px;
    color: var(--text); text-align: center;
  }

  .api-links {
    display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; margin-top: 16px;
  }
  .api-links a {
    background: var(--surface2); border: 1px solid var(--border); padding: 10px 20px;
    border-radius: 8px; color: var(--text2); text-decoration: none; font-size: 0.9rem;
    transition: all 0.2s;
  }
  .api-links a:hover { border-color: #8b5cf6; color: var(--text); }

  .footer { text-align: center; padding: 32px; color: var(--text2); font-size: 0.85rem; border-top: 1px solid var(--border); margin-top: 48px; }
</style>
</head>
<body>

<div class="hero">
  <h1>&#x1f517; Blockchain <span>Brasil</span></h1>
  <p>Sistema de registro imutável para Pessoas Físicas, Imóveis e Veículos — com assinaturas digitais ECDSA e integração cross-chain.</p>
</div>

<div class="container">
  <h2 class="section-title">Escolha um Blockchain</h2>
  <div class="blockchains">
    <a href="/pf" class="bc-card pf">
      <div class="icon">👤</div>
      <h2>Blockchain PF</h2>
      <div class="subtitle">Pessoas Físicas</div>
      <div class="desc">Registro de eventos vitais: nascimento, casamento, divórcio, vacinas, próteses e óbito.</div>
      <span class="btn">Acessar</span>
    </a>
    <a href="/im" class="bc-card im">
      <div class="icon">🏠</div>
      <h2>Blockchain IM</h2>
      <div class="subtitle">Imóveis</div>
      <div class="desc">Registro imobiliário: terreno, construção, compra/venda, hipoteca e leilão.</div>
      <span class="btn">Acessar</span>
    </a>
    <a href="/mo" class="bc-card mo">
      <div class="icon">🚗</div>
      <h2>Blockchain MO</h2>
      <div class="subtitle">Veículos (Móveis)</div>
      <div class="desc">Vida útil do veículo: fabricação, transferências, sinistros, multas e recalls.</div>
      <span class="btn">Acessar</span>
    </a>
    <a href="/co" class="bc-card co">
      <div class="icon">🏢</div>
      <h2>Blockchain CO</h2>
      <div class="subtitle">Empresas (CNPJ)</div>
      <div class="desc">Vida da empresa: constituição, sócios, fusões, cisões, dissolução e certidões.</div>
      <span class="btn">Acessar</span>
    </a>
    <a href="/em" class="bc-card em">
      <div class="icon">⛵</div>
      <h2>Blockchain EM</h2>
      <div class="subtitle">Embarcações</div>
      <div class="desc">Registro naval: construção, transferências, inspeções e licenciamento.</div>
      <span class="btn">Acessar</span>
    </a>
    <a href="/ac" class="bc-card ac">
      <div class="icon">✈️</div>
      <h2>Blockchain AC</h2>
      <div class="subtitle">Aeronaves</div>
      <div class="desc">Registro aeronáutico: fabricação, manutenção, airworthiness e transferências.</div>
      <span class="btn">Acessar</span>
    </a>
    <a href="/an" class="bc-card an">
      <div class="icon">🐾</div>
      <h2>Blockchain AN</h2>
      <div class="subtitle">Animais</div>
      <div class="desc">Registro animal: nascimento, vacinas, castração, tratamentos e transferências.</div>
      <span class="btn">Acessar</span>
    </a>
    <a href="/au" class="bc-card au">
      <div class="icon">🪪</div>
      <h2>Blockchain AU</h2>
      <div class="subtitle">Autoridades</div>
      <div class="desc">Hierarquia de emissores: Brasil → UF → cidade. Nomeação, alteração e revogação de autoridades por escopo/região.</div>
      <span class="btn">Acessar</span>
    </a>
  </div>

  <h2 class="section-title">APIs</h2>
  <div class="api-links">
    <a href="/api/docs">📄 Swagger (ReDoc)</a>
    <a href="/api/chains">🔗 Cadeias PF</a>
    <a href="/api/im">🏠 Imóveis</a>
    <a href="/api/co">🏢 Empresas</a>
    <a href="/api/em">⛵ Embarcações</a>
    <a href="/api/ac">✈️ Aeronaves</a>
    <a href="/api/an">🐾 Animais</a>
    <a href="/api/au">🪪 Autoridades</a>
    <a href="/api/health">💓 Health Check</a>
  </div>
</div>

<div class="footer">
  Blockchain Brasil v4.0 | ECDSA P-256 | SHA-256 | Proof of Work | FastAPI
</div>

</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/pf", response_class=HTMLResponse)
def landing_pf():
    """Landing page da Blockchain PF."""
    return HTMLResponse(content=_read_html("landing_pf.html"))


@app.get("/im", response_class=HTMLResponse)
def landing_im():
    """Landing page da Blockchain IM."""
    return HTMLResponse(content=_read_html("landing_im.html"))


@app.get("/mo", response_class=HTMLResponse)
def landing_mo():
    """Landing page da Blockchain MO."""
    return HTMLResponse(content=_read_html("landing_mo.html"))


@app.get("/co", response_class=HTMLResponse)
def landing_co():
    """Landing page da Blockchain CO (Empresas)."""
    return HTMLResponse(content=_read_html("landing_co.html"))


@app.get("/em", response_class=HTMLResponse)
def landing_em():
    """Landing page da Blockchain EM (Embarcacoes)."""
    return HTMLResponse(content=_read_html("landing_em.html"))


@app.get("/ac", response_class=HTMLResponse)
def landing_ac():
    """Landing page da Blockchain AC (Aeronaves)."""
    return HTMLResponse(content=_read_html("landing_ac.html"))


@app.get("/an", response_class=HTMLResponse)
def landing_an():
    """Landing page da Blockchain AN (Animais)."""
    return HTMLResponse(content=_read_html("landing_an.html"))


@app.get("/au", response_class=HTMLResponse)
def landing_au():
    """Landing page da Blockchain AU (Autoridades)."""
    return HTMLResponse(content=_read_html("landing_au.html"))


@app.get("/admin/pf", response_class=HTMLResponse)
def admin_pf():
    """Interface admin da Blockchain PF."""
    return HTMLResponse(content=_read_html("admin_pf.html"))


@app.get("/admin/im", response_class=HTMLResponse)
def admin_im():
    """Interface admin da Blockchain IM."""
    return HTMLResponse(content=_read_html("admin_im.html"))


@app.get("/admin/mo", response_class=HTMLResponse)
def admin_mo():
    """Interface admin da Blockchain MO."""
    return HTMLResponse(content=_read_html("admin_mo.html"))


@app.get("/admin/co", response_class=HTMLResponse)
def admin_co():
    """Interface admin da Blockchain CO (Empresas)."""
    return HTMLResponse(content=_read_html("admin_co.html"))


@app.get("/admin/em", response_class=HTMLResponse)
def admin_em():
    """Interface admin da Blockchain EM (Embarcacoes)."""
    return HTMLResponse(content=_read_html("admin_em.html"))


@app.get("/admin/ac", response_class=HTMLResponse)
def admin_ac():
    """Interface admin da Blockchain AC (Aeronaves)."""
    return HTMLResponse(content=_read_html("admin_ac.html"))


@app.get("/admin/an", response_class=HTMLResponse)
def admin_an():
    """Interface admin da Blockchain AN (Animais)."""
    return HTMLResponse(content=_read_html("admin_an.html"))


@app.get("/admin/au", response_class=HTMLResponse)
def admin_au():
    """Interface admin da Blockchain AU (Autoridades)."""
    return HTMLResponse(content=_read_html("admin_au.html"))


@app.get("/admin/cross", response_class=HTMLResponse)
def admin_cross():
    """Dashboard de cross-chain."""
    return HTMLResponse(content=_read_html("admin_cross.html"))


# ── Rotas: Cadeia ──────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return ok({
        "server": "Blockchain Brasil v4.0",
        "timestamp": time.time(),
        "blockchains": {
            "PF": {"count": len(chains), "label": "Pessoas Fisicas"},
            "IM": {"count": len(im_chains), "label": "Imoveis"},
            "MO": {"count": len(mo_chains), "label": "Veiculos"},
            "CO": {"count": len(co_chains), "label": "Empresas"},
            "EM": {"count": len(em_chains), "label": "Embarcacoes"},
            "AC": {"count": len(ac_chains), "label": "Aeronaves"},
            "AN": {"count": len(an_chains), "label": "Animais"},
        },
        "total_chains": len(chains) + len(im_chains) + len(mo_chains) + len(co_chains) + len(em_chains) + len(ac_chains) + len(an_chains),
    })


# ── Rotas: Geografia (base UF/Cidades IBGE) ─────────────────────────────

@app.get("/api/geografia/ufs")
def geografia_ufs():
    """Lista as 27 UFs."""
    return ok({"ufs": [{"sigla": s, "nome": n, "regiao": r} for s, n, r in geografia.UFS]})


@app.get("/api/geografia/municipios")
def geografia_municipios(uf: str = Query(..., description="Sigla da UF (ex.: SP)")):
    """Municipios de uma UF (tabela oficial IBGE, capital em 1o)."""
    uf = uf.strip().upper()
    if not geografia.validar_uf(uf):
        raise HTTPException(status_code=400, detail=f"UF invalida: {uf}")
    municipios = db.municipios_da_uf(uf)
    return ok({"uf": uf, "total": len(municipios), "municipios": municipios})


@app.get("/api/geografia/validar")
def geografia_validar(uf: str = Query(...), cidade: str = Query(...)):
    """Valida estritamente se (uf, cidade) existe na tabela oficial."""
    return ok({
        "uf": uf.strip().upper(),
        "cidade": cidade,
        "valido": geografia.validar_cidade(uf, cidade),
    })


# ── Rotas: Autenticacao ───────────────────────────────────────────────

@app.post("/api/auth/login")
def login(req: LoginRequest):
    """Autentica usuario e retorna token JWT."""
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuario ou senha invalidos.",
        )
    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "nivel": user.nivel,
        "escopo": user.escopo,
        "uf": user.uf,
        "cidade": user.cidade,
    })
    return ok({
        "token": token,
        "token_type": "bearer",
        "expires_in": 86400,
        "user": user.to_dict(),
    }, "Login realizado com sucesso.")


@app.get("/api/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    """Retorna dados do usuario autenticado."""
    username = user.get("sub", "")
    u = get_user(username)
    return ok(u.to_dict() if u else {"username": username, "role": user.get("role")})


@app.get("/api/auth/users")
def list_all_users(admin: dict = Depends(require_admin)):
    """Lista todos os usuarios (admin only)."""
    return ok(list_users())


@app.post("/api/auth/users", status_code=201)
def create_new_user(req: UserCreateRequest, admin: dict = Depends(require_admin)):
    """Cria novo usuario (admin only)."""
    try:
        user = create_user(req.username, req.password, req.role)
        return ok(user.to_dict(), f"Usuario '{req.username}' criado.")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.delete("/api/auth/users/{username}")
def delete_existing_user(username: str, admin: dict = Depends(require_admin)):
    """Remove usuario (admin only)."""
    if username == "admin":
        raise HTTPException(status_code=400, detail="Nao e possivel remover o admin.")
    if delete_user(username):
        return ok(message=f"Usuario '{username}' removido.")
    raise HTTPException(status_code=404, detail="Usuario nao encontrado.")


@app.post("/api/chain", status_code=201)
def create_chain(req: ChainCreateRequest, cpf: str = Query(...),
                 user: dict = Depends(require_write_access)):
    cpf_clean = cpf.replace(".", "").replace("-", "").replace("/", "")
    if cpf_clean in chains:
        raise HTTPException(status_code=409, detail="Cadeia ja existe para este CPF.")

    chain = Blockchain(difficulty=req.difficulty)
    signer_label = req.signer_label or "autoridade"
    kp = generate_authority_keypair(signer_label)
    chain.set_signer(kp)

    chains[cpf_clean] = chain
    # Salva no SQLite
    chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
    db.save_chain(cpf_clean, chain.difficulty, chain_data)
    return ok({"cpf": cpf_clean, "difficulty": req.difficulty}, "Cadeia criada. Use POST /api/chain/{cpf}/event para registrar o nascimento.")


@app.get("/api/chains")
def list_chains():
    result = []
    for cpf, chain in chains.items():
        birth = chain.get_birth_block()
        nome = ""
        if birth:
            nome = birth.data.get("payload", {}).get("nome_completo", "")
        result.append({
            "cpf": cpf,
            "nome": nome,
            "blocos": len(chain),
            "assinado": sum(1 for b in chain.chain if b.has_signature()),
        })
    return ok(result)


@app.get("/api/chain/{cpf}")
def get_chain_info(cpf: str):
    chain = get_chain(cpf)
    birth = chain.get_birth_block()
    nome = ""
    if birth:
        nome = birth.data.get("payload", {}).get("nome_completo", "")
    return ok({
        "cpf": cpf,
        "nome": nome,
        "blocos": len(chain),
        "dificuldade": chain.difficulty,
        "assinado": sum(1 for b in chain.chain if b.has_signature()),
        "signer": chain.signer.keypair.label if chain.signer else None,
    })


@app.delete("/api/chain/{cpf}")
def delete_chain(cpf: str, user: dict = Depends(require_admin)):
    cpf_clean = cpf.replace(".", "").replace("-", "").replace("/", "")
    if cpf_clean not in chains:
        raise HTTPException(status_code=404, detail="Cadeia nao encontrada.")
    del chains[cpf_clean]
    db.delete_chain(cpf_clean)
    return ok(message="Cadeia removida.")


# ── Rotas: Eventos ─────────────────────────────────────────────────────

def _persist_chain(cpf: str) -> None:
    """Salva a cadeia no SQLite."""
    if cpf in chains and db:
        chain = chains[cpf]
        chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
        db.save_chain(cpf, chain.difficulty, chain_data)


@app.post("/api/chain/{cpf}/event", status_code=201)
def add_event(cpf: str, req: EventoRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    _validate_event_type(EventType, req.event_type)

    # Verifica se ha obito
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito and not ChainProtector.pode_adicionar(req.event_type, True):
        raise HTTPException(
            status_code=400,
            detail="Cadeia encerrada por OBITO. Evento bloqueado.",
        )

    # Se a cadeia esta vazia e o evento e NASCIMENTO, cria genesis
    if not chain.chain and req.event_type == "NASCIMENTO":
        block = chain.create_genesis(req.payload)
    else:
        try:
            block = chain.add_event(req.event_type, req.payload)
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index,
        "hash": block.hash,
        "assinado": block.has_signature(),
        "emissor": block.signature.get("signer_label") if block.has_signature() else None,
    }, f"Evento {req.event_type} registrado.")


@app.post("/api/chain/{cpf}/event/nascimento", status_code=201)
def add_nascimento(cpf: str, req: NascimentoRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    if chain.chain:
        raise HTTPException(status_code=400, detail="Cadeia ja possui dados. Use /event para outros eventos.")

    try:
        dados = EventFactory.nascimento(
            cpf=req.cpf, nome_completo=req.nome_completo,
            data_nascimento=req.data_nascimento, sexo=req.sexo,
            cidade_nascimento=req.cidade_nascimento, uf_nascimento=req.uf_nascimento,
            nome_mae=req.nome_mae, nome_pai=req.nome_pai,
        )
        block = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ok({
        "bloco_index": block.index,
        "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Nascimento registrado (bloco genesis).")


@app.post("/api/chain/{cpf}/event/casamento", status_code=201)
def add_casamento(cpf: str, req: CasamentoRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito:
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")

    try:
        dados = EventFactory.casamento(
            cpf=req.cpf, nome_conjuge=req.nome_conjuge,
            cpf_conjuge=req.cpf_conjuge, data_casamento=req.data_casamento,
            regime_bens=req.regime_bens, cidade=req.cidade, uf=req.uf,
        )
        block = chain.add_event(EventType.CASAMENTO.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Casamento registrado.")


@app.post("/api/chain/{cpf}/event/divorcio", status_code=201)
def add_divorcio(cpf: str, req: DivorcioRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito:
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")

    try:
        dados = EventFactory.divorcio(
            cpf=req.cpf, data_divorcio=req.data_divorcio,
            tipo=req.tipo, guarda_filhos=req.guarda_filhos,
            pensao_alimenticia=req.pensao_alimenticia,
        )
        block = chain.add_event(EventType.DIVORCIO.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Divorcio registrado.")


@app.post("/api/chain/{cpf}/event/adocao", status_code=201)
def add_adocao(cpf: str, req: AdocaoRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito:
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")

    try:
        dados = EventFactory.adocao(
            cpf=req.cpf, nome_adotivo=req.nome_adotivo,
            data_adocao=req.data_adocao, nome_mae_adotiva=req.nome_mae_adotiva,
            nome_pai_adotivo=req.nome_pai_adotivo,
            mantem_nome_biologico=req.mantem_nome_biologico,
        )
        block = chain.add_event(EventType.ADOCAO.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Adocao registrada.")


@app.post("/api/chain/{cpf}/event/obito", status_code=201)
def add_obito(cpf: str, req: ObitoRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    try:
        dados = EventFactory.obito(
            cpf=req.cpf, data_obito=req.data_obito,
            cidade_obito=req.cidade_obito, uf_obito=req.uf_obito,
            causa_morte=req.causa_morte,
        )
        block = chain.add_event(EventType.OBITO.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Obito registrado. Cadeia encerrada.")


@app.post("/api/chain/{cpf}/event/alteracao_nome", status_code=201)
def add_alteracao_nome(cpf: str, req: AlteracaoNomeRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    # ALTERACAO_NOME e permitida apos obito (correcao administrativa)
    # Nao bloqueia aqui — ChainProtector ja define essa regra

    try:
        dados = EventFactory.alteracao_nome(
            cpf=req.cpf, nome_anterior=req.nome_anterior,
            nome_novo=req.nome_novo, data_alteracao=req.data_alteracao,
            motivo=req.motivo,
        )
        block = chain.add_event(EventType.ALTERACAO_NOME.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Alteracao de nome registrada.")


@app.post("/api/chain/{cpf}/event/disvinculacao", status_code=201)
def add_disvinculacao(cpf: str, req: DisvinculacaoRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito:
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")

    try:
        if req.tipo.upper() == "P":
            dados = EventFactory.disvinculacao_paterna(
                cpf=req.cpf, data_disvinculacao=req.data_disvinculacao,
                motivo=req.motivo,
            )
            evt_type = EventType.DISVINC_PATerna.value
        else:
            dados = EventFactory.disvinculacao_materna(
                cpf=req.cpf, data_disvinculacao=req.data_disvinculacao,
                motivo=req.motivo,
            )
            evt_type = EventType.DISVINC_MATERNA.value
        block = chain.add_event(evt_type, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Disvinculacao registrada.")


@app.post("/api/chain/{cpf}/event/vacina", status_code=201)
def add_vacina(cpf: str, req: VacinaRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito:
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")

    try:
        dados = EventFactory.vacina(
            cpf=req.cpf, nome_vacina=req.nome_vacina,
            data_vacinacao=req.data_vacinacao, lote=req.lote,
            fabricante=req.fabricante, dose=req.dose,
            unidade_saude=req.unidade_saude, cidade=req.cidade, uf=req.uf,
        )
        block = chain.add_event(EventType.VACINACAO.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Vacinacao registrada.")


@app.post("/api/chain/{cpf}/event/protese", status_code=201)
def add_protese(cpf: str, req: ProteseRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito:
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")

    try:
        dados = EventFactory.protese(
            cpf=req.cpf, nome_protese=req.nome_protese,
            data_implantacao=req.data_implantacao, tipo=req.tipo,
            marca_modelo=req.marca_modelo, medico_responsavel=req.medico_responsavel,
            hospital_clinica=req.hospital_clinica, cidade=req.cidade, uf=req.uf,
            data_remocao=req.data_remocao, motivo_remocao=req.motivo_remocao,
        )
        block = chain.add_event(EventType.PROTESE.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Protese registrada.")


@app.post("/api/chain/{cpf}/event/cnh", status_code=201)
def add_cnh(cpf: str, req: CNHRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito:
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")

    try:
        dados = EventFactory.cnh(
            cpf=req.cpf, numero_cnh=req.numero_cnh, categoria=req.categoria,
            data_emissao=req.data_emissao, data_validade=req.data_validade,
            orgao_emissor=req.orgao_emissor, uf_emissao=req.uf_emissao,
            situacao=req.situacao, pontos=req.pontos,
            exame_medico=req.exame_medico, data_exame_medico=req.data_exame_medico,
        )
        block = chain.add_event(EventType.CNH.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "CNH registrada.")


@app.post("/api/chain/{cpf}/event/titulo_eleitor", status_code=201)
def add_titulo_eleitor(cpf: str, req: TituloEleitorRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito:
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")

    try:
        dados = EventFactory.titulo_eleitor(
            cpf=req.cpf, numero_titulo=req.numero_titulo,
            zona_eleitoral=req.zona_eleitoral, secao_eleitoral=req.secao_eleitoral,
            municipio=req.municipio, uf=req.uf,
            data_emissao=req.data_emissao, situacao=req.situacao,
            titulo_anterior=req.titulo_anterior,
        )
        block = chain.add_event(EventType.TITULO_ELEITOR.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Titulo de eleitor registrado.")


@app.post("/api/chain/{cpf}/event/escolaridade", status_code=201)
def add_escolaridade(cpf: str, req: EscolaridadeRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito:
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")

    try:
        dados = EventFactory.escolaridade(
            cpf=req.cpf, nivel=req.nivel, instituicao=req.instituicao,
            data_inicio=req.data_inicio, data_conclusao=req.data_conclusao,
            curso=req.curso, serie_ano=req.serie_ano,
            situacao=req.situacao, registro=req.registro,
            tipo_registro=req.tipo_registro,
        )
        block = chain.add_event(EventType.ESCOLARIDADE.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _persist_chain(cpf)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Escolaridade registrada.")


# ── Rotas: Validacao e Assinaturas ─────────────────────────────────────

@app.get("/api/chain/{cpf}/validate")
def validate_chain(cpf: str, require_signatures: bool = False):
    chain = get_chain(cpf)
    valida, msg = chain.validate(require_signatures=require_signatures)
    return ok({
        "valida": valida,
        "mensagem": msg,
        "blocos": len(chain),
        "assinados": sum(1 for b in chain.chain if b.has_signature()),
    })


@app.post("/api/chain/{cpf}/sign")
def configure_signer(cpf: str, req: SignerRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    kp = generate_authority_keypair(req.label)
    chain.set_signer(kp)
    return ok({
        "label": kp.label,
        "fingerprint": kp.fingerprint(),
        "public_key_hex": kp.public_key_hex()[:32] + "...",
    }, "Assinador ECDSA configurado. Novos blocos serao assinados.")


@app.get("/api/chain/{cpf}/signatures")
def verify_signatures(cpf: str):
    chain = get_chain(cpf)
    all_ok, all_msg = chain.verify_all_signatures()

    details = []
    for block in chain.chain:
        if block.has_signature():
            sig = BlockSignature.from_dict(block.signature)
            ok_s, msg_s = chain._verify_signature(block, sig)
            details.append({
                "bloco": block.index,
                "tipo": block.data.get("evento_tipo", "?"),
                "valida": ok_s,
                "emissor": sig.signer_label,
            })
        else:
            details.append({
                "bloco": block.index,
                "tipo": block.data.get("evento_tipo", "?"),
                "valida": None,
                "emissor": None,
            })

    return ok({
        "todas_validas": all_ok,
        "mensagem": all_msg,
        "detalhes": details,
    })


# ── Rotas: Timeline e Predicoes ───────────────────────────────────────

@app.get("/api/chain/{cpf}/timeline")
def get_timeline(cpf: str):
    chain = get_chain(cpf)
    return ok(chain.get_timeline())


@app.get("/api/chain/{cpf}/predictions")
def get_predictions(cpf: str):
    chain = get_chain(cpf)
    predictor = LifeEventPredictor(chain)
    report = predictor.gerar_relatorio()
    return ok(report.to_dict())


@app.get("/api/chain/{cpf}/export")
def export_chain(cpf: str):
    chain = get_chain(cpf)
    return ok({
        "difficulty": chain.difficulty,
        "chain": [b.to_dict() for b in chain.chain],
    })


# ── Rotas: Imóveis ────────────────────────────────────────────────────

@app.get("/api/im")
def list_imoveis():
    result = []
    for mat, chain in im_chains.items():
        estado = chain.get_estado_atual()
        result.append({
            "matricula": mat,
            "endereco": estado.get("endereco", {}),
            "situacao": estado.get("situacao", ""),
            "area_terreno": estado.get("area_terreno_m2", 0),
            "area_construida": estado.get("area_construida_m2", 0),
            "blocos": len(chain),
            "proprietarios": len(estado.get("proprietarios", [])),
        })
    return ok(result)


@app.post("/api/im", status_code=201)
def create_imovel(req: TerrenoRequest, user: dict = Depends(require_write_access)):
    matricula = req.matricula.strip()
    if matricula in im_chains:
        raise HTTPException(status_code=409, detail=f"Cadeia já existe para matrícula: {matricula}")

    chain = PropertyChain(difficulty=2)
    chain.set_signer(generate_authority_keypair("cartorio_imoveis"))
    try:
        dados = PropertyEventFactory.terreno(
            matricula=req.matricula,
            endereco_logradouro=req.endereco_logradouro,
            endereco_bairro=req.endereco_bairro,
            endereco_cidade=req.endereco_cidade,
            endereco_uf=req.endereco_uf,
            endereco_cep=req.endereco_cep,
            lat=req.lat, lon=req.lon,
            area_terreno_m2=req.area_terreno_m2,
            metragem_frente=req.metragem_frente,
            metragem_fundo=req.metragem_fundo,
            metragem_lado_esq=req.metragem_lado_esq,
            metragem_lado_dir=req.metragem_lado_dir,
            zoneamento=req.zoneamento,
            uso_permitido=req.uso_permitido,
            altura_maxima=req.altura_maxima,
            taxa_ocupacao=req.taxa_ocupacao,
            cacau_permitido=req.cacau_permitido,
            codigo_iptu=req.codigo_iptu,
            proprietarios=req.proprietarios,
        )
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    im_chains[matricula] = chain
    _persist_imovel(matricula)
    return ok({
        "matricula": matricula,
        "bloco_index": genesis.index,
        "hash": genesis.hash,
    }, "Imóvel criado (bloco gênesis).")


@app.get("/api/im/{matricula}")
def get_imovel_info(matricula: str):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    estado = chain.get_estado_atual()
    return ok({
        "matricula": matricula,
        "endereco": estado.get("endereco", {}),
        "coordenadas": estado.get("coordenadas", {}),
        "situacao": estado.get("situacao", ""),
        "area_terreno": estado.get("area_terreno_m2", 0),
        "area_construida": estado.get("area_construida_m2", 0),
        "proprietarios": estado.get("proprietarios", []),
        "onus_ativos": chain.get_onus_ativos(),
        "blocos": len(chain),
        "matricula_atual": chain.get_matricula(),
    })


@app.get("/api/im/{matricula}/estado")
def get_imovel_estado(matricula: str):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    return ok(chain.get_estado_atual())


@app.get("/api/im/{matricula}/timeline")
def get_imovel_timeline(matricula: str):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    return ok(chain.get_historico_completo())


@app.get("/api/im/{matricula}/validate")
def validate_imovel(matricula: str, require_signatures: bool = False):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    valida, msg = chain.validate(require_signatures=require_signatures)
    return ok({
        "valida": valida,
        "mensagem": msg,
        "blocos": len(chain),
    })


@app.get("/api/im/{matricula}/financeiro")
def get_fluxo_financeiro(matricula: str):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    return ok(chain.get_fluxo_financeiro())


@app.get("/api/im/{matricula}/pessoas")
def get_pessoas_do_imovel(matricula: str):
    pessoas = cross_manager.get_pessoas_do_imovel(matricula)
    return ok(pessoas)


@app.get("/api/pessoa/{cpf}/imoveis")
def get_imoveis_da_pessoa(cpf: str):
    imoveis = cross_manager.get_imoveis_da_pessoa(cpf)
    return ok(imoveis)


@app.post("/api/im/{matricula}/event", status_code=201)
def add_imovel_event(matricula: str, req: ImovelGenericoRequest, user: dict = Depends(require_write_access)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    _validate_event_type(PropertyEventType, req.event_type)
    try:
        block = chain.add_event(req.event_type, req.payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_imovel(matricula)
    return ok({
        "bloco_index": block.index,
        "hash": block.hash,
        "assinado": block.has_signature(),
    }, f"Evento {req.event_type} registrado.")


@app.post("/api/im/{matricula}/event/construcao", status_code=201)
def add_construcao(matricula: str, req: ConstrucaoRequest, user: dict = Depends(require_write_access)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    try:
        dados = PropertyEventFactory.construcao(**req.model_dump())
        block = chain.add_event(PropertyEventType.CONSTRUCAO.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_imovel(matricula)
    return ok({"bloco_index": block.index, "hash": block.hash}, "Construção registrada.")


@app.post("/api/im/{matricula}/event/demolicao", status_code=201)
def add_demolicao(matricula: str, req: DemolicaoRequest, user: dict = Depends(require_write_access)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    try:
        dados = PropertyEventFactory.demolicao(**req.model_dump())
        block = chain.add_event(PropertyEventType.DEMOLICAO.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_imovel(matricula)
    return ok({"bloco_index": block.index, "hash": block.hash}, "Demolição registrada.")


@app.post("/api/im/{matricula}/event/reforma", status_code=201)
def add_reforma(matricula: str, req: ReformaRequest, user: dict = Depends(require_write_access)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    try:
        dados = PropertyEventFactory.reforma(**req.model_dump())
        block = chain.add_event(PropertyEventType.REFORMA.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_imovel(matricula)
    return ok({"bloco_index": block.index, "hash": block.hash}, "Reforma registrada.")


@app.post("/api/im/{matricula}/event/compra_venda", status_code=201)
def add_compra_venda(matricula: str, req: CompraVendaRequest, user: dict = Depends(require_write_access)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    try:
        dados = PropertyEventFactory.compra_venda(**req.model_dump())
        block = chain.add_event(PropertyEventType.COMPRA_VENDA.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_imovel(matricula)
    return ok({"bloco_index": block.index, "hash": block.hash}, "Compra/venda registrada.")


@app.post("/api/im/{matricula}/event/doacao", status_code=201)
def add_doacao(matricula: str, req: DoacaoRequest, user: dict = Depends(require_write_access)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    try:
        dados = PropertyEventFactory.doacao(**req.model_dump())
        block = chain.add_event(PropertyEventType.DOACAO.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_imovel(matricula)
    return ok({"bloco_index": block.index, "hash": block.hash}, "Doação registrada.")


@app.post("/api/im/{matricula}/event/garantia", status_code=201)
def add_garantia(matricula: str, req: GarantiaRequest, user: dict = Depends(require_write_access)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    try:
        dados = PropertyEventFactory.garantia(**req.model_dump())
        block = chain.add_event(PropertyEventType.GARANTIA.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_imovel(matricula)
    return ok({"bloco_index": block.index, "hash": block.hash}, "Garantia registrada.")


@app.post("/api/im/{matricula}/event/leilao", status_code=201)
def add_leilao(matricula: str, req: LeilaoRequest, user: dict = Depends(require_write_access)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    try:
        dados = PropertyEventFactory.leilao(**req.model_dump())
        block = chain.add_event(PropertyEventType.LEILAO.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_imovel(matricula)
    return ok({"bloco_index": block.index, "hash": block.hash}, "Leilão registrado.")


@app.post("/api/im/{matricula}/event/heranca", status_code=201)
def add_heranca(matricula: str, req: HerancaRequest, user: dict = Depends(require_write_access)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail=f"Imóvel não encontrado: {matricula}")
    chain = im_chains[matricula]
    try:
        dados = PropertyEventFactory.heranca(**req.model_dump())
        block = chain.add_event(PropertyEventType.HERANCA.value, dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_imovel(matricula)
    return ok({"bloco_index": block.index, "hash": block.hash}, "Herança registrada.")


@app.delete("/api/im/{matricula}")
def delete_imovel(matricula: str, user: dict = Depends(require_admin)):
    if matricula not in im_chains:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado.")
    del im_chains[matricula]
    db.delete_imovel(matricula)
    return ok(message="Imóvel removido.")


# ── Helpers: Persistência ──────────────────────────────────────────────

def _persist_imovel(matricula: str) -> None:
    if matricula in im_chains and db:
        chain = im_chains[matricula]
        chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
        db.save_imovel(matricula, chain.difficulty, chain_data)


def _persist_veiculo(placa: str) -> None:
    if placa in mo_chains and db:
        chain = mo_chains[placa]
        chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
        db.save_veiculo(placa, chain.difficulty, chain_data)


# ── Rotas: Veículos (MO) ──────────────────────────────────────────────

@app.get("/api/mo")
def list_veiculos():
    result = []
    for placa, chain in mo_chains.items():
        estado = chain.get_estado_atual()
        result.append({
            "placa": placa,
            "marca": estado.get("marca", ""),
            "modelo": estado.get("modelo", ""),
            "cor": estado.get("cor", ""),
            "ano": estado.get("ano_fabricacao", 0),
            "situacao": estado.get("situacao", ""),
            "blocos": len(chain),
            "proprietarios": len(estado.get("proprietarios", [])),
            "odometro": estado.get("odometro_km", 0),
        })
    return ok(result)


@app.post("/api/mo", status_code=201)
def create_veiculo(req: VehicleCreateRequest, user: dict = Depends(require_write_access)):
    placa = req.placa.strip().upper()
    if placa in mo_chains:
        raise HTTPException(status_code=409, detail=f"Cadeia já existe para placa: {placa}")
    chain = VehicleChain(difficulty=2)
    chain.set_signer(generate_authority_keypair("detran"))
    try:
        dados = VehicleEventFactory.fabricacao(**req.model_dump(exclude={"placa"}), placa=placa)
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    mo_chains[placa] = chain
    _persist_veiculo(placa)
    return ok({"placa": placa, "bloco_index": genesis.index, "hash": genesis.hash}, "Veiculo criado.")


@app.get("/api/mo/{placa}")
def get_veiculo_info(placa: str):
    placa = placa.upper()
    if placa not in mo_chains:
        raise HTTPException(status_code=404, detail=f"Veiculo nao encontrado: {placa}")
    chain = mo_chains[placa]
    estado = chain.get_estado_atual()
    return ok({
        "placa": placa, "estado": estado,
        "blocos": len(chain),
        "valida": chain.validate()[0],
    })


@app.get("/api/mo/{placa}/timeline")
def get_veiculo_timeline(placa: str):
    placa = placa.upper()
    if placa not in mo_chains:
        raise HTTPException(status_code=404, detail=f"Veiculo nao encontrado: {placa}")
    return ok(mo_chains[placa].get_historico_completo())


@app.get("/api/mo/{placa}/validate")
def validate_veiculo(placa: str, require_signatures: bool = False):
    placa = placa.upper()
    if placa not in mo_chains:
        raise HTTPException(status_code=404, detail=f"Veiculo nao encontrado: {placa}")
    valida, msg = mo_chains[placa].validate(require_signatures=require_signatures)
    return ok({"valida": valida, "mensagem": msg, "blocos": len(mo_chains[placa])})


@app.post("/api/mo/{placa}/event", status_code=201)
def add_veiculo_event(placa: str, req: dict, user: dict = Depends(require_write_access)):
    placa = placa.upper()
    if placa not in mo_chains:
        raise HTTPException(status_code=404, detail=f"Veiculo nao encontrado: {placa}")
    event_type = _validate_event_type(VehicleEventType, req.get("event_type", ""))
    payload = req.get("payload", {})
    try:
        block = mo_chains[placa].add_event(event_type, payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_veiculo(placa)
    return ok({"bloco_index": block.index, "hash": block.hash}, f"Evento {event_type} registrado.")


@app.get("/api/mo/{placa}/financeiro")
def get_veiculo_financeiro(placa: str):
    placa = placa.upper()
    if placa not in mo_chains:
        raise HTTPException(status_code=404, detail=f"Veiculo nao encontrado: {placa}")
    return ok(mo_chains[placa].get_fluxo_financeiro())


@app.delete("/api/mo/{placa}")
def delete_veiculo(placa: str, user: dict = Depends(require_admin)):
    placa = placa.upper()
    if placa not in mo_chains:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado.")
    del mo_chains[placa]
    db.delete_veiculo(placa)
    return ok(message="Veiculo removido.")


# ── Rotas: Empresas (CO) ──────────────────────────────────────────────

@app.get("/api/co")
def list_empresas():
    result = []
    for cnpj, chain in co_chains.items():
        estado = chain.get_estado_atual()
        result.append({
            "cnpj": cnpj, "razao_social": estado.get("razao_social", ""),
            "situacao": estado.get("situacao_cadastral", ""),
            "blocos": len(chain), "socios": len(estado.get("socios", [])),
        })
    return ok(result)

@app.post("/api/co", status_code=201)
def create_empresa(req: CompanyCreateRequest, user: dict = Depends(require_write_access)):
    cnpj_clean = __import__("re").sub(r"\D", "", req.cnpj)
    if cnpj_clean in co_chains:
        raise HTTPException(status_code=409, detail=f"Cadeia ja existe para CNPJ: {cnpj_clean}")
    chain = CompanyChain(difficulty=2)
    chain.set_signer(generate_authority_keypair("junta_comercial"))
    try:
        dados = CompanyEventFactory.constituicao(
            **req.model_dump(exclude={"cnpj"}), cnpj=cnpj_clean
        )
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    co_chains[cnpj_clean] = chain
    _save_chain_to_db("co", cnpj_clean, chain)
    return ok({"cnpj": cnpj_clean, "bloco_index": genesis.index, "hash": genesis.hash}, "Empresa criada.")

@app.get("/api/co/{cnpj}")
def get_empresa_info(cnpj: str):
    cnpj_clean = __import__("re").sub(r"\D", "", cnpj)
    if cnpj_clean not in co_chains:
        raise HTTPException(status_code=404, detail=f"Empresa nao encontrada: {cnpj_clean}")
    chain = co_chains[cnpj_clean]
    estado = chain.get_estado_atual()
    return ok({"cnpj": cnpj_clean, "estado": estado, "blocos": len(chain)})

@app.get("/api/co/{cnpj}/timeline")
def get_empresa_timeline(cnpj: str):
    cnpj_clean = __import__("re").sub(r"\D", "", cnpj)
    if cnpj_clean not in co_chains:
        raise HTTPException(status_code=404, detail=f"Empresa nao encontrada: {cnpj_clean}")
    return ok(co_chains[cnpj_clean].get_historico_completo())

@app.post("/api/co/{cnpj}/event", status_code=201)
def add_empresa_event(cnpj: str, req: dict, user: dict = Depends(require_write_access)):
    cnpj_clean = __import__("re").sub(r"\D", "", cnpj)
    if cnpj_clean not in co_chains:
        raise HTTPException(status_code=404, detail=f"Empresa nao encontrada: {cnpj_clean}")
    event_type = _validate_event_type(CompanyEventType, req.get("event_type", ""))
    payload = req.get("payload", {})
    try:
        block = co_chains[cnpj_clean].add_event(event_type, payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    _save_chain_to_db("co", cnpj_clean, co_chains[cnpj_clean])
    return ok({"bloco_index": block.index, "hash": block.hash}, f"Evento {event_type} registrado.")

@app.delete("/api/co/{cnpj}")
def delete_empresa(cnpj: str, user: dict = Depends(require_admin)):
    cnpj_clean = __import__("re").sub(r"\D", "", cnpj)
    if cnpj_clean not in co_chains:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")
    del co_chains[cnpj_clean]
    db.delete_domain_chain("co", cnpj_clean)
    return ok(message="Empresa removida.")


# ── Rotas: Embarcacoes (EM) ──────────────────────────────────────────

@app.get("/api/em")
def list_embarcacoes():
    result = []
    for reg, chain in em_chains.items():
        estado = chain.get_estado_atual()
        result.append({
            "registro_nr": reg, "nome": estado.get("nome_embarcacao", ""),
            "tipo": estado.get("tipo_embarcacao", ""), "porte": estado.get("porte", ""),
            "situacao": estado.get("situacao", ""), "blocos": len(chain),
        })
    return ok(result)

@app.post("/api/em", status_code=201)
def create_embarcacao(req: VesselCreateRequest, user: dict = Depends(require_write_access)):
    reg = req.registro_nr.strip()
    if reg in em_chains:
        raise HTTPException(status_code=409, detail=f"Cadeia ja existe para registro: {reg}")
    chain = VesselChain(difficulty=2)
    chain.set_signer(generate_authority_keypair("capitania_portos"))
    try:
        dados = VesselEventFactory.construcao(
            **req.model_dump(exclude={"registro_nr"}), registro_nr=reg
        )
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    em_chains[reg] = chain
    _save_chain_to_db("em", reg, chain)
    return ok({"registro_nr": reg, "bloco_index": genesis.index, "hash": genesis.hash}, "Embarcacao criada.")

@app.get("/api/em/{registro}")
def get_embarcacao_info(registro: str):
    if registro not in em_chains:
        raise HTTPException(status_code=404, detail=f"Embarcacao nao encontrada: {registro}")
    chain = em_chains[registro]
    estado = chain.get_estado_atual()
    return ok({"registro_nr": registro, "estado": estado, "blocos": len(chain)})

@app.get("/api/em/{registro}/timeline")
def get_embarcacao_timeline(registro: str):
    if registro not in em_chains:
        raise HTTPException(status_code=404, detail=f"Embarcacao nao encontrada: {registro}")
    return ok(em_chains[registro].get_historico_completo())

@app.post("/api/em/{registro}/event", status_code=201)
def add_embarcacao_event(registro: str, req: dict, user: dict = Depends(require_write_access)):
    if registro not in em_chains:
        raise HTTPException(status_code=404, detail=f"Embarcacao nao encontrada: {registro}")
    event_type = _validate_event_type(VesselEventType, req.get("event_type", ""))
    payload = req.get("payload", {})
    try:
        block = em_chains[registro].add_event(event_type, payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    _save_chain_to_db("em", registro, em_chains[registro])
    return ok({"bloco_index": block.index, "hash": block.hash}, f"Evento {event_type} registrado.")

@app.delete("/api/em/{registro}")
def delete_embarcacao(registro: str, user: dict = Depends(require_admin)):
    if registro not in em_chains:
        raise HTTPException(status_code=404, detail="Embarcacao nao encontrada.")
    del em_chains[registro]
    db.delete_domain_chain("em", registro)
    return ok(message="Embarcacao removida.")


# ── Rotas: Aeronaves (AC) ────────────────────────────────────────────

@app.get("/api/ac")
def list_aeronaves():
    result = []
    for mat, chain in ac_chains.items():
        estado = chain.get_estado_atual()
        result.append({
            "matricula": mat, "nome": estado.get("nome_aeronave", ""),
            "modelo": estado.get("modelo", ""), "fabricante": estado.get("fabricante", ""),
            "situacao": estado.get("situacao", ""), "blocos": len(chain),
        })
    return ok(result)

@app.post("/api/ac", status_code=201)
def create_aeronave(req: AircraftCreateRequest, user: dict = Depends(require_write_access)):
    mat = req.matricula.strip().upper()
    if mat in ac_chains:
        raise HTTPException(status_code=409, detail=f"Cadeia ja existe para matricula: {mat}")
    chain = AircraftChain(difficulty=2)
    chain.set_signer(generate_authority_keypair("anac"))
    try:
        dados = AircraftEventFactory.fabricacao(
            **req.model_dump(exclude={"matricula"}), matricula=mat
        )
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ac_chains[mat] = chain
    _save_chain_to_db("ac", mat, chain)
    return ok({"matricula": mat, "bloco_index": genesis.index, "hash": genesis.hash}, "Aeronave criada.")

@app.get("/api/ac/{matricula}")
def get_aeronave_info(matricula: str):
    matricula = matricula.upper()
    if matricula not in ac_chains:
        raise HTTPException(status_code=404, detail=f"Aeronave nao encontrada: {matricula}")
    chain = ac_chains[matricula]
    estado = chain.get_estado_atual()
    return ok({"matricula": matricula, "estado": estado, "blocos": len(chain)})

@app.get("/api/ac/{matricula}/timeline")
def get_aeronave_timeline(matricula: str):
    matricula = matricula.upper()
    if matricula not in ac_chains:
        raise HTTPException(status_code=404, detail=f"Aeronave nao encontrada: {matricula}")
    return ok(ac_chains[matricula].get_historico_completo())

@app.post("/api/ac/{matricula}/event", status_code=201)
def add_aeronave_event(matricula: str, req: dict, user: dict = Depends(require_write_access)):
    matricula = matricula.upper()
    if matricula not in ac_chains:
        raise HTTPException(status_code=404, detail=f"Aeronave nao encontrada: {matricula}")
    event_type = _validate_event_type(AircraftEventType, req.get("event_type", ""))
    payload = req.get("payload", {})
    try:
        block = ac_chains[matricula].add_event(event_type, payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    _save_chain_to_db("ac", matricula, ac_chains[matricula])
    return ok({"bloco_index": block.index, "hash": block.hash}, f"Evento {event_type} registrado.")

@app.delete("/api/ac/{matricula}")
def delete_aeronave(matricula: str, user: dict = Depends(require_admin)):
    matricula = matricula.upper()
    if matricula not in ac_chains:
        raise HTTPException(status_code=404, detail="Aeronave nao encontrada.")
    del ac_chains[matricula]
    db.delete_domain_chain("ac", matricula)
    return ok(message="Aeronave removida.")


# ── Rotas: Animais (AN) ──────────────────────────────────────────────

@app.get("/api/an")
def list_animais():
    result = []
    for aid, chain in an_chains.items():
        estado = chain.get_estado_atual()
        result.append({
            "animal_id": aid, "nome": estado.get("nome", ""),
            "especie": estado.get("especie", ""), "raca": estado.get("raca", ""),
            "situacao": estado.get("situacao", ""), "blocos": len(chain),
        })
    return ok(result)

@app.post("/api/an", status_code=201)
def create_animal(req: AnimalCreateRequest, user: dict = Depends(require_write_access)):
    import hashlib
    nome = req.nome
    cpf = req.proprietario_cpf
    data = req.data_nascimento
    aid = hashlib.sha256(f"{nome}{cpf}{data}".encode()).hexdigest()[:12]
    if aid in an_chains:
        raise HTTPException(status_code=409, detail=f"Animal ja registrado: {aid}")
    chain = AnimalChain(difficulty=2)
    chain.set_signer(generate_authority_keypair("crm veterinario"))
    try:
        dados = AnimalEventFactory.nascimento(**req.model_dump())
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    an_chains[aid] = chain
    _save_chain_to_db("an", aid, chain)
    return ok({"animal_id": aid, "bloco_index": genesis.index, "hash": genesis.hash}, "Animal registrado.")

@app.get("/api/an/{animal_id}")
def get_animal_info(animal_id: str):
    if animal_id not in an_chains:
        raise HTTPException(status_code=404, detail=f"Animal nao encontrado: {animal_id}")
    chain = an_chains[animal_id]
    estado = chain.get_estado_atual()
    return ok({"animal_id": animal_id, "estado": estado, "blocos": len(chain)})

@app.get("/api/an/{animal_id}/timeline")
def get_animal_timeline(animal_id: str):
    if animal_id not in an_chains:
        raise HTTPException(status_code=404, detail=f"Animal nao encontrado: {animal_id}")
    return ok(an_chains[animal_id].get_historico_completo())

@app.post("/api/an/{animal_id}/event", status_code=201)
def add_animal_event(animal_id: str, req: dict, user: dict = Depends(require_write_access)):
    if animal_id not in an_chains:
        raise HTTPException(status_code=404, detail=f"Animal nao encontrado: {animal_id}")
    event_type = _validate_event_type(AnimalEventType, req.get("event_type", ""))
    payload = req.get("payload", {})
    try:
        block = an_chains[animal_id].add_event(event_type, payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    _save_chain_to_db("an", animal_id, an_chains[animal_id])
    return ok({"bloco_index": block.index, "hash": block.hash}, f"Evento {event_type} registrado.")

@app.delete("/api/an/{animal_id}")
def delete_animal(animal_id: str, user: dict = Depends(require_admin)):
    if animal_id not in an_chains:
        raise HTTPException(status_code=404, detail="Animal nao encontrado.")
    del an_chains[animal_id]
    db.delete_domain_chain("an", animal_id)
    return ok(message="Animal removido.")


# ── Rotas: Grafo PF ───────────────────────────────────────────────────

@app.get("/api/pf/graph")
def get_pf_graph():
    """Retorna o grafo completo de relacionamentos PF."""
    return ok(pf_graph.to_dict())


# ── Rotas: Autoridade (AU) ─────────────────────────────────────────────
# Hierarquia de emissores: N0 (Brasil) → N1 (UF) → N2 (cidade).
# Revogacao no livro-razao AU bloqueia a conta (sem delete fisico).

class AuthorityCreateRequest(BaseModel):
    nome: str = Field(..., description="Nome da autoridade")
    nivel: int = Field(..., description="1 (UF) ou 2 (cidade)")
    escopo: str = Field(..., description="Dominio governado: pf|im|mo|co|em|ac|an")
    uf: str = Field(..., description="Sigla da UF (27 oficiais)")
    cidade: str = Field("", description="Municipio IBGE da UF (obrigatorio p/ nivel 2)")
    senha: str = Field("", description="Senha da conta (opcional; gerada se vazia)")
    data: str = Field("", description="Data da nomeacao (DD/MM/AAAA; default hoje)")
    motivo: str = Field("", description="Motivo da nomeacao")


class AuthorityAlterRequest(BaseModel):
    nome: str = Field("", description="Novo nome")
    escopo: str = Field("", description="Novo escopo")
    uf: str = Field("", description="Nova UF")
    cidade: str = Field("", description="Nova cidade")
    data: str = Field("", description="Data da alteracao")
    motivo: str = Field("", description="Motivo da alteracao")


class AuthorityRevokeRequest(BaseModel):
    data: str = Field("", description="Data da revogacao")
    motivo: str = Field("Revogada pela autoridade superior.", description="Motivo")


class AuthorityEventConfirmRequest(BaseModel):
    data: str = Field("", description="Data da confirmacao/recusa")
    motivo: str = Field("", description="Motivo da decisao")


# Fabricas de accao por dominio (reuso integral das rotas de criacao)
_DOMAIN_ENUM = {
    "pf": EventType, "im": PropertyEventType, "mo": VehicleEventType,
    "co": CompanyEventType, "em": VesselEventType, "ac": AircraftEventType,
    "an": AnimalEventType,
}

# Baixa/encerramento definitivo por dominio (usado no DELETE de dados)
_BAIXA_TYPE = {
    "pf": "OBITO", "mo": "BAIXA", "co": "BAIXA", "em": "BAIXA",
    "ac": "BAIXA", "an": "OBITO",
}

def _today() -> str:
    return time.strftime("%d/%m/%Y")


def _estado_ou_genesis(chain) -> dict:
    """Estado da cadeia (get_estado_atual quando existe; genesis PF como fallback)."""
    if hasattr(chain, "get_estado_atual"):
        return chain.get_estado_atual()
    birth = chain.get_birth_block()
    return birth.data.get("payload", {}) if birth else {}


def _persist_autoridade(uid: str) -> None:
    chain = au_chains.get(uid)
    if chain and db:
        _save_chain_to_db("au", uid, chain)


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", "-", s.upper()).strip("-")


def _username_autoridade(nivel: int, escopo: str, uf: str, cidade: str) -> str:
    base = "n1.%s.%s" % (escopo, uf.strip().upper()) if nivel == 1 \
        else "n2.%s.%s.%s" % (escopo, uf.strip().upper(), _slug(cidade))
    uid, i = base, 1
    while uid in au_chains or get_user(uid) is not None:
        i += 1
        uid = "%s-%d" % (base, i)
    return uid


async def _depende_autoridade_ativa(uid: str,
                                    user: dict = Depends(get_current_user)) -> dict:
    """FastAPI injeta o path param `uid`; valida token + identidade + autoridade ativa."""
    if user.get("sub", "") != uid:
        raise HTTPException(status_code=403, detail="Identidade da autoridade nao confere com o token.")
    if not registry.ativa(uid):
        raise HTTPException(status_code=403, detail="Autoridade revogada ou inexistente.")
    return user


@app.get("/api/au")
def list_autoridades():
    """Lista das autoridades (id + estado vigente)."""
    reg = AuthorityRegistry(au_chains)
    out = []
    for uid in sorted(au_chains):
        st = reg.estado(uid)
        out.append({"id": uid, **st})
    return ok(out)


@app.get("/api/au/arvore")
def arvore_autoridades():
    """Arvore hierarquica completa Brasil → UF → cidade."""
    return ok(AuthorityRegistry(au_chains).arvore())


@app.get("/api/au/{uid}")
def get_autoridade(uid: str):
    """Dados e estado vigente de uma autoridade."""
    if uid not in au_chains:
        raise HTTPException(status_code=404, detail=f"Autoridade nao encontrada: {uid}")
    return ok({"id": uid, "estado": au_chains[uid].get_estado_atual(),
               "blocos": len(au_chains[uid])})


@app.get("/api/au/{uid}/timeline")
def autoridade_timeline(uid: str):
    if uid not in au_chains:
        raise HTTPException(status_code=404, detail=f"Autoridade nao encontrada: {uid}")
    chain = au_chains[uid]
    tl = chain.get_timeline() if hasattr(chain, "get_timeline") else []
    return ok(tl)


@app.get("/api/au/{uid}/filhos")
def autoridade_filhos(uid: str):
    """Autoridades nomeadas diretamente pelo ator."""
    if uid not in au_chains:
        raise HTTPException(status_code=404, detail=f"Autoridade nao encontrada: {uid}")
    return ok(AuthorityRegistry(au_chains).filhos_de(uid))


@app.post("/api/au", status_code=201)
def criar_autoridade(req: AuthorityCreateRequest, user: dict = Depends(get_current_user)):
    """N0 nomeia N1; N1 nomeia N2 (mesmo escopo+UF). Cria cadeia AU + conta."""
    actor = user.get("sub", "")
    factory = AuthorityEventFactory
    try:
        dados = factory.nomeacao(
            nome=req.nome, nivel=req.nivel, escopo=req.escopo,
            uf=req.uf, cidade=req.cidade,
            nomeado_por=actor, data=req.data, motivo=req.motivo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    target = {"nivel": req.nivel, "escopo": req.escopo, "uf": req.uf.strip().upper(),
              "cidade": (req.cidade or "").strip().upper()}
    if not registry.can_manage_authority(actor, target):
        raise HTTPException(status_code=403,
                            detail="Sem permissao para nomear esta autoridade "
                                   "(N0 nomeia N1/N2; N1 nomeia apenas N2 do mesmo escopo+UF).")

    uid = _username_autoridade(req.nivel, req.escopo, req.uf, req.cidade)
    chain = AuthorityChain(difficulty=2)
    chain.set_signer(generate_authority_keypair("autoridade"))
    dados["username"] = uid
    try:
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    au_chains[uid] = chain
    _persist_autoridade(uid)

    senha = req.senha or secrets.token_hex(12)
    create_user(uid, senha, role="user", nivel=req.nivel,
                escopo=req.escopo, uf=req.uf.strip().upper(),
                cidade=dados["cidade"])

    return ok({
        "id": uid,
        "password": senha,
        "nivel": req.nivel,
        "escopo": req.escopo,
        "uf": dados["uf"],
        "cidade": dados["cidade"],
        "bloco_index": genesis.index,
        "hash": genesis.hash,
    }, f"Autoridade {uid} nomeada.")


@app.post("/api/au/{uid}/alterar")
def alterar_autoridade(uid: str, req: AuthorityAlterRequest,
                       user: dict = Depends(get_current_user)):
    """Altera metadados da autoridade (apenas pelo superior hierarquico; nivel imutavel)."""
    actor = user.get("sub", "")
    if not registry.ativa(actor):
        raise HTTPException(status_code=403, detail="Autoridade atora revogada ou inexistente.")
    if uid not in au_chains:
        raise HTTPException(status_code=404, detail=f"Autoridade nao encontrada: {uid}")
    estado = au_chains[uid].get_estado_atual()
    if not registry.can_manage_authority(actor, estado):
        raise HTTPException(status_code=403, detail="Sem permissao para alterar esta autoridade.")

    factory = AuthorityEventFactory
    novo_escopo = req.escopo or estado.get("escopo", "")
    novo_uf = (req.uf or estado.get("uf", "")).strip().upper()
    nova_cidade = (req.cidade if req.cidade is not None else estado.get("cidade", "")).strip().upper()
    nivel = estado.get("nivel", 2)

    # Validacao estrita dos novos valores no mesmo regime de nivel
    try:
        factory.nomeacao(
            nome=req.nome or estado.get("nome", ""), nivel=nivel,
            escopo=novo_escopo, uf=novo_uf, cidade=nova_cidade,
            nomeado_por=estado.get("nomeado_por", ""),
            data=req.data or _today(), motivo=req.motivo or "Alteracao de registro",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    bloco = au_chains[uid].add_event(AuthorityEventType.ALTERACAO.value,
                                     factory.alteracao(
                                         nome=req.nome, escopo=novo_escopo,
                                         uf=novo_uf, cidade=nova_cidade,
                                         data=req.data, motivo=req.motivo,
                                     ))
    _persist_autoridade(uid)
    update_user_metadata(uid, escopo=novo_escopo, uf=novo_uf, cidade=nova_cidade)
    return ok({"id": uid, "bloco_index": bloco.index, "hash": bloco.hash,
               "estado": au_chains[uid].get_estado_atual()}, "Autoridade alterada.")


@app.post("/api/au/{uid}/revogar")
def revogar_autoridade(uid: str, req: AuthorityRevokeRequest,
                       user: dict = Depends(get_current_user)):
    """Revoga a autoridade no livro-razao e desativa a conta (sem delete fisico)."""
    actor = user.get("sub", "")
    if not registry.ativa(actor):
        raise HTTPException(status_code=403, detail="Autoridade atora revogada ou inexistente.")
    if uid not in au_chains:
        raise HTTPException(status_code=404, detail=f"Autoridade nao encontrada: {uid}")
    if not registry.can_manage_authority(actor, au_chains[uid].get_estado_atual()):
        raise HTTPException(status_code=403, detail="Sem permissao para revogar esta autoridade.")
    bloco = au_chains[uid].add_event(AuthorityEventType.REVOGACAO.value,
                                     AuthorityEventFactory.revogacao(req.data, req.motivo))
    _persist_autoridade(uid)
    update_user_metadata(uid, ativo=False)
    return ok({"id": uid, "bloco_index": bloco.index, "hash": bloco.hash,
               "estado": au_chains[uid].get_estado_atual()}, f"Autoridade {uid} revogada.")


@app.get("/api/au/pendentes")
def au_pendentes(user: dict = Depends(get_current_user)):
    """Alteracoes PENDENTES que o ator pode confirmar/recusar."""
    actor = user.get("sub", "")
    out = []
    for cid, chain in au_chains.items():
        estado = chain.get_estado_atual()
        if estado.get("status") != "PENDENTE":
            continue
        if registry.can_confirmar_alteracao(actor, estado):
            out.append({"id": cid, "estado": estado})
    return ok({"total": len(out), "pendentes": out})


@app.post("/api/au/{uid}/confirmar", status_code=201)
def confirmar_alteracao(uid: str, req: AuthorityEventConfirmRequest,
                        user: dict = Depends(get_current_user)):
    """Confirma alteracao PENDENTE da autoridade (aplica o novo snapshot)."""
    actor = user.get("sub", "")
    if uid not in au_chains:
        raise HTTPException(status_code=404, detail=f"Autoridade nao encontrada: {uid}")
    estado = au_chains[uid].get_estado_atual()
    if estado.get("status") != "PENDENTE":
        raise HTTPException(status_code=400, detail="Nao ha alteracao PENDENTE para confirmar.")
    if not registry.can_confirmar_alteracao(actor, estado):
        raise HTTPException(status_code=403,
                            detail="Sem permissao para confirmar esta alteracao.")
    bloco = au_chains[uid].add_event(AuthorityEventType.CONFIRMACAO.value,
                                     AuthorityEventFactory.confirmacao(
                                         username=uid, **estado,
                                         confirmado_por=actor, data=req.data, motivo=req.motivo,
                                     ))
    _persist_autoridade(uid)
    update_user_metadata(uid, nome=estado.get("nome", ""),
                         escopo=estado.get("escopo", ""),
                         uf=estado.get("uf", ""), cidade=estado.get("cidade", ""))
    return ok({"id": uid, "bloco_index": bloco.index, "hash": bloco.hash,
               "estado": au_chains[uid].get_estado_atual()}, "Alteracao confirmada.")


@app.post("/api/au/{uid}/recusar", status_code=201)
def recusar_alteracao(uid: str, req: AuthorityEventConfirmRequest,
                      user: dict = Depends(get_current_user)):
    """Recusa alteracao PENDENTE — mantem o snapshot vigente (nao aplica)."""
    actor = user.get("sub", "")
    if uid not in au_chains:
        raise HTTPException(status_code=404, detail=f"Autoridade nao encontrada: {uid}")
    estado = au_chains[uid].get_estado_atual()
    if estado.get("status") != "PENDENTE":
        raise HTTPException(status_code=400, detail="Nao ha alteracao PENDENTE para recusar.")
    if not registry.can_confirmar_alteracao(actor, estado):
        raise HTTPException(status_code=403,
                            detail="Sem permissao para recusar esta alteracao.")
    bloco = au_chains[uid].add_event(AuthorityEventType.RECUSA.value,
                                     AuthorityEventFactory.recusa(
                                         username=uid, **estado,
                                         recusado_por=actor, data=req.data, motivo=req.motivo,
                                     ))
    _persist_autoridade(uid)
    return ok({"id": uid, "bloco_index": bloco.index, "hash": bloco.hash,
               "estado": au_chains[uid].get_estado_atual()}, "Alteracao recusada.")


# ── Dados de dominio sob escopo de autoridade ──────────────────────────

@app.get("/api/au/{uid}/dados/{domain}")
def dados_no_escopo(uid: str, domain: str,
                    user: dict = Depends(_depende_autoridade_ativa)):
    """Lista registros do dominio dentro da regiao da autoridade."""
    if domain not in _DOMAIN_ENUM:
        raise HTTPException(status_code=400, detail=f"Dominio invalido: {domain}")
    store, _enum = _store_do_dominio(domain)
    if not registry.can_manage_domain(uid):
        raise HTTPException(status_code=403, detail="Autoridade revogada.")
    out = []
    for cid, chain in store.items():
        estado = _estado_ou_genesis(chain)
        uf, cidade = registry.regiao_da_cadeia(domain, estado)
        if not registry.can_manage_data(uid, domain, uf, cidade):
            continue
        out.append({"id": cid, **estado, "_uf": uf, "_cidade": cidade, "blocos": len(chain)})
    return ok({"domain": domain, "total": len(out), "registros": out})


@app.post("/api/au/{uid}/dados/{domain}", status_code=201)
def criar_dado_no_escopo(uid: str, domain: str, body: dict,
                         user: dict = Depends(_depende_autoridade_ativa)):
    """Cria registro no dominio: regiao do payload precisa caber no escopo do ator."""
    if domain not in _DOMAIN_ENUM:
        raise HTTPException(status_code=400, detail=f"Dominio invalido: {domain}")
    chain, cid, dado = _criar_registro_dominio(domain, body)
    uf, cidade = registry.regiao_da_cadeia(domain, dado)
    if not registry.can_manage_data(uid, domain, uf, cidade):
        raise HTTPException(status_code=403,
                            detail=f"Regiao fora do escopo: {uf}/{cidade}.")
    _guardar_registro_dominio(domain, cid, chain)
    return ok({"domain": domain, "id": cid, "blocos": len(chain)},
              f"Registro criado no escopo da autoridade {uid}.")


@app.post("/api/au/{uid}/dados/{domain}/{cid}/event", status_code=201)
def evento_no_escopo(uid: str, domain: str, cid: str, req: dict,
                     user: dict = Depends(_depende_autoridade_ativa)):
    """Registra evento em cadeia existente do dominio (dentro da regiao)."""
    if domain not in _DOMAIN_ENUM:
        raise HTTPException(status_code=400, detail=f"Dominio invalido: {domain}")
    store, enum = _store_do_dominio(domain)
    if cid not in store:
        raise HTTPException(status_code=404, detail=f"Registro nao encontrado: {cid}")
    chain = store[cid]
    estado = _estado_ou_genesis(chain)
    uf, cidade = registry.regiao_da_cadeia(domain, estado)
    if not registry.can_manage_data(uid, domain, uf, cidade):
        raise HTTPException(status_code=403, detail="Regiao fora do escopo da autoridade.")
    event_type = _validate_event_type(enum, req.get("event_type", ""))
    try:
        bloco = chain.add_event(event_type, req.get("payload", {}))
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    _save_chain_to_db(domain, cid, chain)
    return ok({"domain": domain, "id": cid, "bloco_index": bloco.index, "hash": bloco.hash},
              f"Evento {event_type} registrado.")


@app.delete("/api/au/{uid}/dados/{domain}/{cid}")
def baixa_no_escopo(uid: str, domain: str, cid: str,
                    user: dict = Depends(_depende_autoridade_ativa)):
    """Baixa/encerramento definitivo do registro (bloco terminal, sem delete)."""
    if domain not in _DOMAIN_ENUM or domain not in _BAIXA_TYPE:
        raise HTTPException(status_code=400,
                            detail=f"Baixa nao suportada para o dominio: {domain}")
    store, _enum = _store_do_dominio(domain)
    if cid not in store:
        raise HTTPException(status_code=404, detail=f"Registro nao encontrado: {cid}")
    chain = store[cid]
    estado = _estado_ou_genesis(chain)
    uf, cidade = registry.regiao_da_cadeia(domain, estado)
    if not registry.can_manage_data(uid, domain, uf, cidade):
        raise HTTPException(status_code=403, detail="Regiao fora do escopo da autoridade.")
    payload = _payload_baixa(domain, cid)
    try:
        bloco = chain.add_event(_BAIXA_TYPE[domain], payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    _save_chain_to_db(domain, cid, chain)
    return ok({"domain": domain, "id": cid, "bloco_index": bloco.index, "hash": bloco.hash},
              f"Registro {cid} encerrado (bloco {_BAIXA_TYPE[domain]}).")


def _store_do_dominio(domain: str):
    stores = {
        "pf": (chains, EventType), "im": (im_chains, PropertyEventType),
        "mo": (mo_chains, VehicleEventType), "co": (co_chains, CompanyEventType),
        "em": (em_chains, VesselEventType), "ac": (ac_chains, AircraftEventType),
        "an": (an_chains, AnimalEventType),
    }
    return stores[domain]


def _payload_baixa(domain: str, cid: str) -> dict:
    hoje = _today()
    if domain == "pf":
        return {"cpf": cid, "data_obito": hoje, "causa_morte": "Record encerrado por autoridade"}
    if domain == "mo":
        return {"placa": cid, "data_baixa": hoje, "motivo": "Encerrado por autoridade"}
    if domain == "co":
        return {"cnpj": cid, "data_baixa": hoje, "motivo": "Encerrado por autoridade"}
    if domain == "em":
        return {"registro_nr": cid, "data_baixa": hoje, "motivo": "Encerrado por autoridade"}
    if domain == "ac":
        return {"matricula": cid, "data_baixa": hoje, "motivo": "Encerrado por autoridade"}
    if domain == "an":
        return {"animal_id": cid, "data_obito": hoje, "causa": "Encerrado por autoridade"}
    return {}


def _criar_registro_dominio(domain: str, body: dict):
    """Cria a cadeia de dados como faria a rota oficial, retornando (chain, cid, payload)."""
    kp = generate_authority_keypair("autoridade")
    try:
        if domain == "pf":
            cid = (body.get("cpf") or "").replace(".", "").replace("-", "").replace("/", "")
            if cid in chains:
                raise ValueError(f"Cadeia ja existe para CPF: {cid}")
            chain, payload_pf = _chain_com_genesis(Blockchain, kp, EventFactory.nascimento, body)
            chains[cid] = chain
            return chain, cid, payload_pf
        if domain == "im":
            cid = (body.get("matricula") or "").strip()
            if cid in im_chains:
                raise ValueError(f"Cadeia ja existe para matricula: {cid}")
            chain, payload = _chain_com_genesis(PropertyChain, kp, PropertyEventFactory.terreno, body)
            im_chains[cid] = chain
            return chain, cid, payload
        if domain == "mo":
            cid = (body.get("placa") or "").strip().upper()
            if cid in mo_chains:
                raise ValueError(f"Cadeia ja existe para placa: {cid}")
            body2 = {**body, "placa": cid}
            chain, payload = _chain_com_genesis(VehicleChain, kp, VehicleEventFactory.fabricacao, body2)
            mo_chains[cid] = chain
            return chain, cid, payload
        if domain == "co":
            cid = re.sub(r"\D", "", body.get("cnpj") or "")
            if cid in co_chains:
                raise ValueError(f"Cadeia ja existe para CNPJ: {cid}")
            body2 = {**body, "cnpj": cid}
            chain, payload = _chain_com_genesis(CompanyChain, kp, CompanyEventFactory.constituicao, body2)
            co_chains[cid] = chain
            return chain, cid, payload
        if domain == "em":
            cid = (body.get("registro_nr") or body.get("registro_embarcacao") or "").strip()
            if cid in em_chains:
                raise ValueError(f"Cadeia ja existe para registro: {cid}")
            body2 = {**body, "registro_nr": cid}
            chain, payload = _chain_com_genesis(VesselChain, kp, VesselEventFactory.construcao, body2)
            em_chains[cid] = chain
            return chain, cid, payload
        if domain == "ac":
            cid = (body.get("matricula") or "").strip().upper()
            if cid in ac_chains:
                raise ValueError(f"Cadeia ja existe para matricula: {cid}")
            body2 = {**body, "matricula": cid}
            chain, payload = _chain_com_genesis(AircraftChain, kp, AircraftEventFactory.fabricacao, body2)
            ac_chains[cid] = chain
            return chain, cid, payload
        if domain == "an":
            import hashlib
            nome = body.get("nome", "")
            cpf = body.get("proprietario_cpf", "")
            data = body.get("data_nascimento", "")
            cid = hashlib.sha256(f"{nome}{cpf}{data}".encode()).hexdigest()[:12]
            if cid in an_chains:
                raise ValueError(f"Animal ja registrado: {cid}")
            chain, payload = _chain_com_genesis(AnimalChain, kp, AnimalEventFactory.nascimento, body)
            an_chains[cid] = chain
            return chain, cid, payload
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=400, detail=f"Dominio invalido: {domain}")


def _chain_com_genesis(cls, kp, factory, kwargs: dict):
    """Cria cadeia assinada com genesis produzido pela factory."""
    try:
        payload = factory(**kwargs)
    except TypeError as e:
        raise ValueError(f"Payload invalido para o dominio: {e}")
    chain = cls(difficulty=2)
    chain.set_signer(kp)
    chain.create_genesis(payload)
    return chain, payload


def _guardar_registro_dominio(domain: str, cid: str, chain) -> None:
    _save_chain_to_db(domain, cid, chain)


# ── Rotas: Grafo PF ───────────────────────────────────────────────────


@app.get("/api/pf/graph/stats")
def get_pf_graph_stats():
    return ok(pf_graph.stats())


@app.get("/api/pf/graph/{cpf}/rede")
def get_pf_rede(cpf: str, depth: int = 2):
    """Retorna a rede familiar de uma PF."""
    cpf_clean = cpf.replace(".", "").replace("-", "")
    result = pf_graph.get_family_network(cpf_clean, depth)
    return ok(result)


@app.get("/api/pf/graph/{cpf_a}/caminho/{cpf_b}")
def find_pf_path(cpf_a: str, cpf_b: str):
    """Encontra caminho entre duas PFs."""
    path = pf_graph.find_path(cpf_a, cpf_b)
    if path is None:
        return ok(None, "Caminho nao encontrado.")
    return ok(path)


@app.get("/api/pf/graph/{cpf}/conjuges")
def get_conjuges(cpf: str):
    result = pf_graph.get_conjuges(cpf)
    return ok([n.to_dict() for n in result])


@app.get("/api/pf/graph/{cpf}/filhos")
def get_filhos(cpf: str):
    result = pf_graph.get_filhos(cpf)
    return ok([n.to_dict() for n in result])


@app.get("/api/pf/graph/{cpf}/pais")
def get_pais(cpf: str):
    result = pf_graph.get_pais(cpf)
    return ok([n.to_dict() for n in result])


# ── Rotas: Cross-Chain ────────────────────────────────────────────────

@app.get("/api/cross")
def get_cross_chain_stats():
    """Estatisticas do sistema cross-chain."""
    stats_im = cross_manager.stats()
    stats_mo = cross_mo.stats()
    return ok({"pf_im": stats_im, "pf_mo": stats_mo})


@app.get("/api/cross/pf/{cpf}/imoveis")
def get_imoveis_da_pessoa_cross(cpf: str):
    return ok(cross_manager.get_imoveis_da_pessoa(cpf))


@app.get("/api/cross/pf/{cpf}/veiculos")
def get_veiculos_da_pessoa_cross(cpf: str):
    return ok(cross_mo.get_veiculos_da_pessoa(cpf))


@app.get("/api/cross/im/{matricula}/pessoas")
def get_pessoas_do_imovel_cross(matricula: str):
    return ok(cross_manager.get_pessoas_do_imovel(matricula))


@app.get("/api/cross/mo/{placa}/pessoas")
def get_pessoas_do_veiculo_cross(placa: str):
    return ok(cross_mo.get_pessoas_do_veiculo(placa))


@app.get("/api/cross/vinculos")
def get_all_vinculos(
    origem_tipo: str = "", origem_id: str = "",
    destino_tipo: str = "", destino_id: str = "",
    tipo_vinculo: str = "",
):
    """Lista vinculos ativos cross-chain."""
    refs = cross_mo.get_vinculos_ativos(
        origem_tipo=origem_tipo, origem_id=origem_id,
        destino_tipo=destino_tipo, destino_id=destino_id,
        tipo_vinculo=tipo_vinculo,
    )
    return ok(refs)


@app.post("/api/cross/vinculo", status_code=201)
def create_vinculo(req: CrossVinculoRequest, user: dict = Depends(require_write_access)):
    """Cria um vinculo cross-chain."""
    ref = cross_mo.create_reference(**req.model_dump())
    return ok(ref.to_dict(), "Vinculo criado.")


class CrossVinculoDeleteRequest(BaseModel):
    origem_tipo: str
    origem_id: str
    destino_tipo: str
    destino_id: str
    tipo_vinculo: str = ""


@app.delete("/api/cross/vinculo")
def delete_vinculo(req: CrossVinculoDeleteRequest, user: dict = Depends(require_write_access)):
    """Desativa um vinculo cross-chain."""
    count = cross_mo.deactivate_reference(**req.model_dump())
    return ok({"desativados": count}, f"{count} vinculo(s) desativado(s).")


# ── Interface Web ─────────────────────────────────────────────────────────────────
# Landing/admin pages: landing_home (raiz) + arquivos .html do disco.
# HTML_UI antigo e rota index() removidos (rota dobra "/").
# ── Database ──────────────────────────────────────────────────────────

db = Database()
set_auth_database(db)

# Registro de autoridades: resolve permissoes sobre cadeias AU
registry = AuthorityRegistry(au_chains)

# Especificacoes das 8 cadeias: (dominio, dict em memoria, classe da cadeia, rotulo signer)
_CHAIN_SPECS = [
    ("pf", chains, Blockchain, "autoridade"),
    ("im", im_chains, PropertyChain, "cartorio_imoveis"),
    ("mo", mo_chains, VehicleChain, "detran"),
    ("co", co_chains, CompanyChain, "junta_comercial"),
    ("em", em_chains, VesselChain, "capitania_portos"),
    ("ac", ac_chains, AircraftChain, "anac"),
    ("an", an_chains, AnimalChain, "crm veterinario"),
    ("au", au_chains, AuthorityChain, "autoridade"),
]

# Managers cross-chain: (dominio, manager, classe da referencia)
_CROSS_MANAGERS = [
    ("im", cross_manager, CrossReference),
    ("mo", cross_mo, VehicleCrossReference),
    ("co", cross_co, CompanyCrossReference),
    ("em", cross_em, VesselCrossReference),
    ("ac", cross_ac, AircraftCrossReference),
    ("an", cross_an, AnimalCrossReference),
]


def _chain_payload(chain) -> dict:
    """Serializa uma cadeia para persistencia."""
    return {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}


def _save_chain_to_db(domain: str, cid: str, chain) -> None:
    """Salva uma cadeia de qualquer dominio no SQLite."""
    if db:
        db.save_domain_chain(domain, cid, chain.difficulty, _chain_payload(chain))


def _rebuild_chain(cls, data, signer_label: str):
    """Reconstrói uma cadeia a partir do JSON salvo no SQLite."""
    from blockchain_pf.block import Block
    chain = cls(difficulty=data["difficulty"])
    chain.set_signer(generate_authority_keypair(signer_label))
    chain.chain = [Block.from_dict(b) for b in data["chain"]]
    for i, block in enumerate(chain.chain):
        evt = block.data.get("evento_tipo", "DESCONHECIDO")
        if evt not in chain._event_index:
            chain._event_index[evt] = []
        chain._event_index[evt].append(i)
    return chain


def _save_cross_references() -> None:
    """Persiste todos os vinculos cross-chain no SQLite."""
    for domain, manager, _ref_cls in _CROSS_MANAGERS:
        db.clear_references(domain)
        for ref in getattr(manager, "_references", []):
            db.save_reference(domain, ref.to_dict())


def _restore_cross_references() -> None:
    """Reconstroi os managers cross-chain a partir do SQLite."""
    for domain, manager, ref_cls in _CROSS_MANAGERS:
        rows = db.load_all_references(domain)
        manager._references = [ref_cls(**r["ref_data"]) for r in rows]


def _save_graph() -> None:
    """Persiste o grafo de relacionamentos PF no SQLite."""
    if not pf_graph.nodes and not pf_graph.edges:
        return
    db.clear_graph()
    for node in pf_graph.nodes.values():
        db.save_graph_node(node.cpf, node.nome, node.ativo, node.chain_index)
    for edge in pf_graph.edges:
        db.save_graph_edge(edge.from_cpf, edge.to_cpf, edge.tipo, edge.ativo,
                           edge.block_index, edge.timestamp, edge.dados)


def _restore_graph() -> None:
    """Reconstroi o grafo de relacionamentos PF a partir do SQLite."""
    for n in db.load_all_graph_nodes():
        pf_graph.nodes[n["cpf"]] = Node(
            cpf=n["cpf"], nome=n["nome"], ativo=n["ativo"], chain_index=n["chain_index"]
        )
    for e in db.load_all_graph_edges():
        edge = Edge(
            from_cpf=e["from_cpf"], to_cpf=e["to_cpf"], tipo=e["tipo"],
            ativo=e["ativo"], block_index=e["block_index"],
            timestamp=e["timestamp"], dados=e["dados"],
        )
        pf_graph.edges.append(edge)
        idx = len(pf_graph.edges) - 1
        pf_graph._edge_index.setdefault(edge.from_cpf, []).append(idx)
        pf_graph._edge_index.setdefault(edge.to_cpf, []).append(idx)


def _save_current_state() -> None:
    """Salva estado atual no SQLite (7 dominios + cross-chain + grafo)."""
    for domain, store, _cls, _label in _CHAIN_SPECS:
        for cid, chain in store.items():
            _save_chain_to_db(domain, cid, chain)
    _save_cross_references()
    _save_graph()


# ── Startup ──────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    # Carrega as 8 cadeias do SQLite
    for domain, store, cls, signer_label in _CHAIN_SPECS:
        saved = db.load_all_domain_chains(domain)
        for cid, data in saved.items():
            store[cid] = _rebuild_chain(cls, data, signer_label)

    _restore_cross_references()
    _restore_graph()

    # Carrega usuarios do SQLite
    init_default_users()
    init_default_authorities()
    _seed_autoridades_n0()

    counts = {d: len(store) for d, store, _c, _l in _CHAIN_SPECS}
    n_users = len(list_users())
    print(f"  SQLite: PF={counts['pf']} | IM={counts['im']} | MO={counts['mo']} "
          f"| CO={counts['co']} | EM={counts['em']} | AC={counts['ac']} | AN={counts['an']} "
          f"| AU={counts['au']} | Users={n_users} carregados")
    print("  Logins: admin (administrador), operador (operacao), consulta (somente leitura)")
    print("  Autoridades N0: admin01/@dmin01BR, admin02/@dmin02BR, admin03/@dmin03BR")


def _seed_autoridades_n0() -> None:
    """Cria as cadeias AU das 3 autoridades de nivel 0 (livro-razao)."""
    for uid in ("admin01", "admin02", "admin03"):
        if uid in au_chains or get_user(uid) is None:
            continue
        chain = AuthorityChain(difficulty=2)
        chain.set_signer(generate_authority_keypair("autoridade"))
        try:
            genesis = chain.create_genesis(AuthorityEventFactory.nomeacao(
                nome=f"Autoridade Nacional {uid}", nivel=0, escopo="",
                uf="", cidade="", nomeado_por="sistema",
                motivo="Seed de autoridade de nivel 0 (Brasil).",
            ))
            genesis.data["payload"]["username"] = uid
        except ValueError as e:
            print(f"  AU: seed {uid} ignorado — {e}")
            continue
        au_chains[uid] = chain
        _persist_autoridade(uid)
        print(f"  AU: autoridade nacional {uid} seedada (bloco {genesis.index}).")


@app.on_event("shutdown")
def shutdown():
    """Salva estado ao desligar."""
    _save_current_state()
    print("  Estado salvo no SQLite.")
    db.close()


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n  Blockchain Brasil — Servidor Web (SQLite + JWT Auth)")
    print("  Acesse: http://localhost:8000")
    print("  Docs:   http://localhost:8000/docs")
    print("  API:    http://localhost:8000/api/health")
    print("  Auth:   POST /api/auth/login {username, password}")
    print(f"  DB:     {db.db_path}\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
