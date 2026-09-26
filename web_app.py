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

import asyncio
import hashlib
import json
import re
import threading
import time
import os
import secrets
import sys
import unicodedata
from contextlib import asynccontextmanager
from functools import partial
from typing import Any, Optional, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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
    revoke_user_tokens, decode_access_token,
    set_database as set_auth_database,
)
from blockchain_pf.database import Database
from blockchain_pf import geografia_br as geografia


# ── Configuracao via env (M12) ─────────────────────────────────────

PORT = int(os.environ.get("PORT", "8000"))
DEFAULT_DIFFICULTY = int(os.environ.get("DEFAULT_DIFFICULTY", "2"))
TOKEN_EXPIRY_HOURS = int(os.environ.get("TOKEN_EXPIRY_HOURS", "24"))

# F2: rate limiting (janela fixa por IP+rota)
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "1") == "1"
RATE_LIMIT_LOGIN = int(os.environ.get("RATE_LIMIT_LOGIN", "10"))   # req/min por IP
RATE_LIMIT_WRITE = int(os.environ.get("RATE_LIMIT_WRITE", "120"))  # req/min por IP+rota

# F9: contadores Prometheus (text/plain em /api/metrics)
_METRICS = {
    "http_requests_total": {},   # (method, path, status) → count
    "http_request_duration_seconds": {},  # (method, path) → [count, total_s]
    "auth_login_attempts_total": {},      # outcome → count
}
_metrics_lock = threading.Lock()


def _metrics_snapshot() -> str:
    """Renderiza as metricas em formato de exposicao Prometheus."""
    lines: list[str] = []
    req = _METRICS["http_requests_total"]
    lines.append("# HELP http_requests_total Total de requisicoes HTTP.")
    lines.append("# TYPE http_requests_total counter")
    for (method, path, status), count in sorted(req.items()):
        lines.append(
            f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
        )
    dur = _METRICS["http_request_duration_seconds"]
    lines.append("# HELP http_request_duration_seconds Duracao total das requisicoes (s).")
    lines.append("# TYPE http_request_duration_seconds counter")
    for (method, path), (count, total) in sorted(dur.items()):
        lines.append(
            f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total:.6f}'
        )
        lines.append(
            f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {count}'
        )
    logins = _METRICS["auth_login_attempts_total"]
    lines.append("# HELP auth_login_attempts_total Tentativas de login por resultado.")
    lines.append("# TYPE auth_login_attempts_total counter")
    for outcome, count in sorted(logins.items()):
        lines.append(f'auth_login_attempts_total{{outcome="{outcome}"}} {count}')
    return "\n".join(lines) + "\n"


# ── App ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown unificados (substitui @app.on_event deprecated — M8)."""
    startup()
    yield
    shutdown()

app = FastAPI(
    title="Blockchain PF — Eventos Vitais",
    description="API REST para cadeia de blocos de eventos vitais de Pessoa Fisica.",
    version="2.0.0",
    lifespan=lifespan,
)

# Relatorio de cobertura (htmlcov/) servido estaticamente — link no index.html
_HTMLCOV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "htmlcov")
if os.path.isdir(_HTMLCOV_DIR):
    app.mount("/htmlcov", StaticFiles(directory=_HTMLCOV_DIR), name="htmlcov")

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins_env.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── F9: Metricas + F11: Audit log (middlewares) ──────────────────────

_METRICS_EXCLUDED = {"/api/metrics"}
_AUDIT_EXCLUDED = {"/api/health", "/api/metrics"}


@app.middleware("http")
async def metrics_audit_middleware(request, call_next):
    """F9: conta requisicoes/latencia; F11: grava audit log por usuario."""
    import time as _time
    start = _time.time()
    response = await call_next(request)
    dur = _time.time() - start

    path = request.url.path
    method = request.method
    status = response.status_code
    client_ip = (request.client.host if request.client else "")

    if path not in _METRICS_EXCLUDED:
        with _metrics_lock:
            key = (method, path, str(status))
            _METRICS["http_requests_total"][key] = \
                _METRICS["http_requests_total"].get(key, 0) + 1
            dkey = (method, path)
            cur = _METRICS["http_request_duration_seconds"].setdefault(dkey, [0, 0.0])
            cur[0] += 1
            cur[1] += dur

    if (path not in _AUDIT_EXCLUDED and db is not None
            and not path.startswith("/htmlcov")):
        username = ""
        authz = request.headers.get("authorization", "")
        if authz.lower().startswith("bearer "):
            payload = decode_access_token(authz[7:].strip())
            if payload:
                username = str(payload.get("sub", ""))
        db.save_audit_entry(
            username=username, method=method, path=path,
            status=status, duration_ms=dur * 1000.0, client_ip=client_ip,
        )
    return response


# ── F2: Rate limiting (janela fixa, em memoria) ───────────────────────

_rate_lock = threading.Lock()
_rate_buckets: dict[str, list] = {}  # chave → [window_start, count]


def _rate_check(key: str, limit: int) -> bool:
    """True se dentro do limite; False se excedeu (janela de 60s)."""
    now = time.time()
    with _rate_lock:
        entry = _rate_buckets.get(key)
        if entry is None or now - entry[0] >= 60.0:
            _rate_buckets[key] = [now, 1]
            return True
        entry[1] += 1
        return entry[1] <= limit


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """F2: limita /api/auth/login (por IP) e rotas de escrita (por IP+rota)."""
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    path = request.url.path
    method = request.method
    client_ip = request.client.host if request.client else "?"

    if path == "/api/auth/login" and method == "POST":
        if not _rate_check(f"login:{client_ip}", RATE_LIMIT_LOGIN):
            return JSONResponse(status_code=429, content={
                "detail": "Muitas tentativas de login. Tente novamente em 1 minuto.",
            })
    elif method in ("POST", "PUT", "PATCH", "DELETE") and path.startswith("/api/"):
        if not _rate_check(f"write:{client_ip}:{method}:{path}", RATE_LIMIT_WRITE):
            return JSONResponse(status_code=429, content={
                "detail": "Taxa de requisicoes excedida para esta rota.",
            })
    return await call_next(request)

# ── Armazenamento em memoria ──────────────────────────────────────────

chains: Dict[str, Blockchain] = {}
im_chains: Dict[str, PropertyChain] = {}
mo_chains: Dict[str, VehicleChain] = {}
co_chains: Dict[str, CompanyChain] = {}
em_chains: Dict[str, VesselChain] = {}
ac_chains: Dict[str, AircraftChain] = {}
an_chains: Dict[str, AnimalChain] = {}
au_chains: Dict[str, AuthorityChain] = {}

# Lock global para mutacao dos dicts acima (M3): criações/deleções de
# cadeias via rotas FastAPI podem concorrer com a listagem/startup.
# As cadeias individuais já possuem lock próprio (C6); este serializa
# apenas as operações sobre os dicts (insert/clear/del).
chains_lock = threading.Lock()
cross_manager = CrossChainManager()
cross_mo = CrossChainMO()
cross_co = CrossChainCO()
cross_em = CrossChainEM()
cross_ac = CrossChainAC()
cross_an = CrossChainAN()
pf_graph = RelationshipGraph()


# ── Models Pydantic ────────────────────────────────────────────────────

class NascimentoRequest(BaseModel):
    cpf: str = Field(..., max_length=14, description="CPF (11 digitos)")
    nome_completo: str = Field(..., max_length=200)
    data_nascimento: str = Field(..., description="DD/MM/AAAA")
    sexo: str = Field(..., description="M ou F")
    cidade_nascimento: str = Field(..., max_length=120)
    uf_nascimento: str = Field(..., max_length=2)
    nome_mae: str = Field(..., max_length=200)
    nome_pai: Optional[str] = Field(None, max_length=200)

class EventoRequest(BaseModel):
    event_type: str = Field(..., description="Tipo do evento")
    payload: dict = Field(..., description="Dados do evento")

class DomainEventRequest(BaseModel):
    """Modelo generico para rotas de eventos das cadeias de dominio (H8)."""
    event_type: str = Field(..., min_length=1, max_length=64, description="Tipo do evento")
    payload: dict = Field(default_factory=dict, description="Dados do evento")

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
    difficulty: int = Field(DEFAULT_DIFFICULTY, ge=1, le=5)
    signer_label: Optional[str] = None

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)
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
    uso_permitido: list[str] = []
    altura_maxima: float = 0.0
    taxa_ocupacao: float = 0.0
    cacau_permitido: float = 0.0
    codigo_iptu: str = ""
    proprietarios: list[dict] = []

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
    valor_transacao: float = Field(..., ge=0)
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
    herdeiros: list[dict]
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
    from blockchain_pf.events import normalize_event_type
    event_type = normalize_event_type(event_type)
    allowed = {e.value for e in enum_cls}
    if event_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de evento invalido: {event_type}. Permitidos: {sorted(allowed)}",
        )
    return event_type


# ── Landing Pages ─────────────────────────────────────────────────────

def _read_html(filename: str) -> str:
    """Lê um HTML do projeto.

    Aceita caminho relativo à raiz OU nome simples resolvido para a
    pasta do pacote do domínio (HTMLs moram junto de sua blockchain):
      "admin_pf.html"     -> blockchain_pf/admin.html
      "landing_au.html"   -> blockchain_au/landing.html
      "admin_cross.html"  -> blockchain_au/admin_cross.html
    """
    root = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(root, filename)
    if not os.path.exists(filepath):
        base = filename[:-5] if filename.endswith(".html") else filename  # sem .html
        if base == "admin_cross":
            filepath = os.path.join(root, "blockchain_au", "admin_cross.html")
        elif base.startswith("admin_"):
            filepath = os.path.join(root, f"blockchain_{base[6:]}", "admin.html")
        elif base.startswith("landing_"):
            filepath = os.path.join(root, f"blockchain_{base[8:]}", "landing.html")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/", response_class=HTMLResponse)
def landing_home():
    """Portal: index.html com links para cada blockchain."""
    return HTMLResponse(content=_read_html("index.html"))


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
    """F8: status do servidor, DB e memoria + contagem de cadeias."""
    # DB: probe real (SELECT 1) + contagens
    db_status = "ok"
    db_detail = {}
    try:
        conn = db._get_conn()
        conn.execute("SELECT 1")
        db_detail = {
            "schema_version": db.schema_version(),
            "audit_entries": db.count_audit_entries(),
            "chains": db.count_all_chains(),
        }
    except Exception as e:
        db_status = f"erro: {e}"

    # Memoria do processo (F8); psutil e opcional
    memoria = None
    try:
        import psutil
        proc = psutil.Process()
        mem = proc.memory_info()
        memoria = {
            "rss_mb": round(mem.rss / 1024 / 1024, 1),
            "vms_mb": round(mem.vms / 1024 / 1024, 1),
            "percent": round(proc.memory_percent(), 1),
        }
    except Exception:
        pass

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
            "AU": {"count": len(au_chains), "label": "Autoridades"},
        },
        "total_chains": len(chains) + len(im_chains) + len(mo_chains) + len(co_chains) + len(em_chains) + len(ac_chains) + len(an_chains) + len(au_chains),
        "database": {"status": db_status, **db_detail},
        "memoria": memoria,
    })


@app.get("/api/metrics")
def metrics():
    """F9: metricas em formato de exposicao Prometheus (text/plain)."""
    from fastapi.responses import Response
    return Response(
        content=_metrics_snapshot(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/audit")
def get_audit(limit: int = 100, username: str = "", user: dict = Depends(require_admin)):
    """F11: ultimas chamadas de API registradas (admin only)."""
    limit = max(1, min(limit, 500))
    return ok(db.load_audit_entries(limit=limit, username=username))


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
        with _metrics_lock:
            k = _METRICS["auth_login_attempts_total"].setdefault("falha", 0)
            _METRICS["auth_login_attempts_total"]["falha"] = k + 1
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
    refresh = create_access_token(
        {"sub": user.username}, token_type="refresh"
    )
    with _metrics_lock:
        k = _METRICS["auth_login_attempts_total"].setdefault("ok", 0)
        _METRICS["auth_login_attempts_total"]["ok"] = k + 1
    return ok({
        "token": token,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": TOKEN_EXPIRY_HOURS * 3600,
        "user": user.to_dict(),
    }, "Login realizado com sucesso.")


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/api/auth/refresh")
def refresh_session(req: RefreshRequest):
    """F3: renova o access token a partir de um refresh token valido."""
    payload = decode_access_token(req.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Refresh token invalido ou expirado.")
    user = get_user(str(payload.get("sub", "")))
    if not user or not user.ativo:
        raise HTTPException(status_code=401, detail="Usuario invalido ou inativo.")
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
        "expires_in": TOKEN_EXPIRY_HOURS * 3600,
    }, "Sessao renovada.")


@app.post("/api/auth/logout")
def logout_session(user: dict = Depends(get_current_user)):
    """F3: revoga os tokens do usuario (novo login passa a ser obrigatorio)."""
    revoke_user_tokens(str(user.get("sub", "")))
    return ok(message="Logout realizado — tokens revogados.")


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
    """Cria novo usuario (admin only). Senha fraca retorna 400 (F4)."""
    try:
        user = create_user(req.username, req.password, req.role)
        return ok(user.to_dict(), f"Usuario '{req.username}' criado.")
    except ValueError as e:
        msg = str(e)
        status_code = 400 if "Senha" in msg else 409
        raise HTTPException(status_code=status_code, detail=msg)


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

    with chains_lock:
        chains[cpf_clean] = chain
    # Salva no SQLite (escrita incremental O(1) — M2)
    _persist_domain("pf", cpf_clean, chain)
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
    _desativa_vinculos_da_entidade("pf", cpf_clean)
    with chains_lock:
        del chains[cpf_clean]
    db.delete_chain(cpf_clean)
    return ok(message="Cadeia removida.")


# ── Rotas: Eventos ─────────────────────────────────────────────────────

def _persist_chain(cpf: str) -> None:
    """Salva a cadeia PF no SQLite (normaliza o CPF — C4; M5 delega)."""
    cpf_clean = re.sub(r"\D", "", cpf)
    if cpf_clean in chains:
        _persist_domain("pf", cpf_clean, chains[cpf_clean])


def _ja_obito(cpf: str) -> bool:
    """True se a cadeia PF ja foi encerrada por OBITO."""
    chain = get_chain(cpf)
    return len(chain.get_events_by_type(EventType.OBITO.value)) > 0


def _add_pf_event(
    cpf: str,
    event_type: str,
    payload: dict,
    strict_obito: bool = True,
):
    """
    Handler generico de eventos PF (M4): checa OBITO, adiciona o bloco
    e persiste a cadeia no SQLite.

    Args:
        strict_obito: se True, qualquer evento e bloqueado apos OBITO
                      (rotas especificas); se False, vale o ChainProtector
                      (permite ALTERACAO_NOME, etc).
    """
    chain = get_chain(cpf)
    if _ja_obito(cpf) and (strict_obito or not ChainProtector.pode_adicionar(event_type, True)):
        raise HTTPException(status_code=400, detail="Cadeia encerrada por OBITO.")
    try:
        block = chain.add_event(event_type, payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    _persist_chain(cpf)
    return block


@app.post("/api/chain/{cpf}/event", status_code=201)
async def add_event(cpf: str, req: EventoRequest, user: dict = Depends(require_write_access)):
    chain = get_chain(cpf)
    event_type = _validate_event_type(EventType, req.event_type)

    # Se a cadeia esta vazia e o evento e NASCIMENTO, cria genesis
    if not chain.chain and event_type == "NASCIMENTO":
        try:
            loop = asyncio.get_running_loop()
            block = await loop.run_in_executor(None, chain.create_genesis, req.payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        _persist_chain(cpf)
    else:
        # PoW roda fora do event loop (M1)
        loop = asyncio.get_running_loop()
        block = await loop.run_in_executor(
            None, partial(_add_pf_event, cpf, event_type, req.payload, False)
        )

    return ok({
        "bloco_index": block.index,
        "hash": block.hash,
        "assinado": block.has_signature(),
        "emissor": block.signature.get("signer_label") if block.has_signature() else None,
    }, f"Evento {event_type} registrado.")


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

    _persist_chain(cpf)  # Persiste o genesis no SQLite (H4)
    return ok({
        "bloco_index": block.index,
        "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Nascimento registrado (bloco genesis).")


@app.post("/api/chain/{cpf}/event/casamento", status_code=201)
def add_casamento(cpf: str, req: CasamentoRequest, user: dict = Depends(require_write_access)):
    try:
        dados = EventFactory.casamento(
            cpf=req.cpf, nome_conjuge=req.nome_conjuge,
            cpf_conjuge=req.cpf_conjuge, data_casamento=req.data_casamento,
            regime_bens=req.regime_bens, cidade=req.cidade, uf=req.uf,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.CASAMENTO.value, dados)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Casamento registrado.")


@app.post("/api/chain/{cpf}/event/divorcio", status_code=201)
def add_divorcio(cpf: str, req: DivorcioRequest, user: dict = Depends(require_write_access)):
    try:
        dados = EventFactory.divorcio(
            cpf=req.cpf, data_divorcio=req.data_divorcio,
            tipo=req.tipo, guarda_filhos=req.guarda_filhos,
            pensao_alimenticia=req.pensao_alimenticia,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.DIVORCIO.value, dados)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Divorcio registrado.")


@app.post("/api/chain/{cpf}/event/adocao", status_code=201)
def add_adocao(cpf: str, req: AdocaoRequest, user: dict = Depends(require_write_access)):
    try:
        dados = EventFactory.adocao(
            cpf=req.cpf, nome_adotivo=req.nome_adotivo,
            data_adocao=req.data_adocao, nome_mae_adotiva=req.nome_mae_adotiva,
            nome_pai_adotivo=req.nome_pai_adotivo,
            mantem_nome_biologico=req.mantem_nome_biologico,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.ADOCAO.value, dados)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Adocao registrada.")


@app.post("/api/chain/{cpf}/event/obito", status_code=201)
def add_obito(cpf: str, req: ObitoRequest, user: dict = Depends(require_write_access)):
    try:
        dados = EventFactory.obito(
            cpf=req.cpf, data_obito=req.data_obito,
            cidade_obito=req.cidade_obito, uf_obito=req.uf_obito,
            causa_morte=req.causa_morte,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.OBITO.value, dados, strict_obito=False)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Obito registrado. Cadeia encerrada.")


@app.post("/api/chain/{cpf}/event/alteracao_nome", status_code=201)
def add_alteracao_nome(cpf: str, req: AlteracaoNomeRequest, user: dict = Depends(require_write_access)):
    # ALTERACAO_NOME e permitida apos obito (correcao administrativa)
    try:
        dados = EventFactory.alteracao_nome(
            cpf=req.cpf, nome_anterior=req.nome_anterior,
            nome_novo=req.nome_novo, data_alteracao=req.data_alteracao,
            motivo=req.motivo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.ALTERACAO_NOME.value, dados, strict_obito=False)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Alteracao de nome registrada.")


@app.post("/api/chain/{cpf}/event/disvinculacao", status_code=201)
def add_disvinculacao(cpf: str, req: DisvinculacaoRequest, user: dict = Depends(require_write_access)):
    try:
        if req.tipo.upper() == "P":
            dados = EventFactory.disvinculacao_paterna(
                cpf=req.cpf, data_disvinculacao=req.data_disvinculacao,
                motivo=req.motivo,
            )
            evt_type = EventType.DISVINC_PATERNA.value
        else:
            dados = EventFactory.disvinculacao_materna(
                cpf=req.cpf, data_disvinculacao=req.data_disvinculacao,
                motivo=req.motivo,
            )
            evt_type = EventType.DISVINC_MATERNA.value
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, evt_type, dados)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Disvinculacao registrada.")


@app.post("/api/chain/{cpf}/event/vacina", status_code=201)
def add_vacina(cpf: str, req: VacinaRequest, user: dict = Depends(require_write_access)):
    try:
        dados = EventFactory.vacina(
            cpf=req.cpf, nome_vacina=req.nome_vacina,
            data_vacinacao=req.data_vacinacao, lote=req.lote,
            fabricante=req.fabricante, dose=req.dose,
            unidade_saude=req.unidade_saude, cidade=req.cidade, uf=req.uf,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.VACINACAO.value, dados)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Vacinacao registrada.")


@app.post("/api/chain/{cpf}/event/protese", status_code=201)
def add_protese(cpf: str, req: ProteseRequest, user: dict = Depends(require_write_access)):
    try:
        dados = EventFactory.protese(
            cpf=req.cpf, nome_protese=req.nome_protese,
            data_implantacao=req.data_implantacao, tipo=req.tipo,
            marca_modelo=req.marca_modelo, medico_responsavel=req.medico_responsavel,
            hospital_clinica=req.hospital_clinica, cidade=req.cidade, uf=req.uf,
            data_remocao=req.data_remocao, motivo_remocao=req.motivo_remocao,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.PROTESE.value, dados)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Protese registrada.")


@app.post("/api/chain/{cpf}/event/cnh", status_code=201)
def add_cnh(cpf: str, req: CNHRequest, user: dict = Depends(require_write_access)):
    try:
        dados = EventFactory.cnh(
            cpf=req.cpf, numero_cnh=req.numero_cnh, categoria=req.categoria,
            data_emissao=req.data_emissao, data_validade=req.data_validade,
            orgao_emissor=req.orgao_emissor, uf_emissao=req.uf_emissao,
            situacao=req.situacao, pontos=req.pontos,
            exame_medico=req.exame_medico, data_exame_medico=req.data_exame_medico,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.CNH.value, dados)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "CNH registrada.")


@app.post("/api/chain/{cpf}/event/titulo_eleitor", status_code=201)
def add_titulo_eleitor(cpf: str, req: TituloEleitorRequest, user: dict = Depends(require_write_access)):
    try:
        dados = EventFactory.titulo_eleitor(
            cpf=req.cpf, numero_titulo=req.numero_titulo,
            zona_eleitoral=req.zona_eleitoral, secao_eleitoral=req.secao_eleitoral,
            municipio=req.municipio, uf=req.uf,
            data_emissao=req.data_emissao, situacao=req.situacao,
            titulo_anterior=req.titulo_anterior,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.TITULO_ELEITOR.value, dados)
    return ok({
        "bloco_index": block.index, "hash": block.hash,
        "assinado": block.has_signature(),
    }, "Titulo de eleitor registrado.")


@app.post("/api/chain/{cpf}/event/escolaridade", status_code=201)
def add_escolaridade(cpf: str, req: EscolaridadeRequest, user: dict = Depends(require_write_access)):
    try:
        dados = EventFactory.escolaridade(
            cpf=req.cpf, nivel=req.nivel, instituicao=req.instituicao,
            data_inicio=req.data_inicio, data_conclusao=req.data_conclusao,
            curso=req.curso, serie_ano=req.serie_ano,
            situacao=req.situacao, registro=req.registro,
            tipo_registro=req.tipo_registro,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    block = _add_pf_event(cpf, EventType.ESCOLARIDADE.value, dados)
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
def export_chain(cpf: str, user: dict = Depends(get_current_user)):
    # Export completo exige autenticacao de leitura (H1 — unica rota GET protegida)
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

    chain = PropertyChain(difficulty=DEFAULT_DIFFICULTY)
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

    with chains_lock:
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
    _desativa_vinculos_da_entidade("im", matricula)
    with chains_lock:
        del im_chains[matricula]
    db.delete_imovel(matricula)
    return ok(message="Imóvel removido.")


# ── Helpers: Persistência (M5: helper unificado; M2: escrita O(1)) ─────

def _persist_domain(domain: str, cid: str, chain) -> None:
    """Persiste uma cadeia de QUALQUER dominio no SQLite.

    Substitui os 5 helpers antigos (_persist_chain, _persist_imovel,
    _persist_veiculo, _persist_autoridade, _save_chain_to_db).
    Escrita incremental (M2): grava apenas o bloco novo (O(1)) na
    tabela `blocks`; o snapshot consolidado em `chains` é atualizado
    para o caminho de leitura existente.
    """
    if not db or not chain or not len(chain):
        return
    last = chain.chain[-1]
    db.save_block_incremental(domain, cid, chain.difficulty, last.to_dict())


# ── F6: Integridade cross-chain ──────────────────────────────────────

# Campos de referencia por dominio: (campo_id_origem, campo_id_destino).
# Ex.: VehicleCrossReference.entidade_origem_tipo/entidade_origem_id.
_REF_KEYS = {
    "im": ("cpf", "matricula"),
    "mo": ("entidade_origem_id", "entidade_destino_id"),
    "co": ("entidade_origem_id", "entidade_destino_id"),
    "em": ("entidade_origem_id", "entidade_destino_id"),
    "ac": ("entidade_origem_id", "entidade_destino_id"),
    "an": ("entidade_origem_id", "entidade_destino_id"),
}


def _desativa_vinculos_da_entidade(domain: str, cid: str) -> int:
    """F6: desativa vinculos cross-chain ativos envolvendo a entidade.

    Chamado nas rotas de delete (antes de remover a cadeia): evita
    referencias orfas — um vinculo ativo apontando para entidade que
    nao existe mais. Retorna a quantidade desativada.
    """
    def _norm_id(s: str) -> str:
        """Normaliza id para comparacao (pontos/tracos/espacos/case)."""
        return re.sub(r"[\s.\-]", "", str(s)).upper()

    cid_norm = _norm_id(cid)
    desativados = 0
    for dom, manager, _ref_cls in _CROSS_MANAGERS:
        if not hasattr(manager, "deactivate_reference"):
            continue
        k_origem, k_destino = _REF_KEYS.get(
            dom, ("entidade_origem_id", "entidade_destino_id"))
        for ref in list(getattr(manager, "_references", [])):
            d = ref.to_dict() if hasattr(ref, "to_dict") else dict(ref)
            if not d.get("ativo", True):
                continue
            o_tipo = str(d.get("entidade_origem_tipo", d.get("origem_tipo", "")))
            d_tipo = str(d.get("entidade_destino_tipo", d.get("destino_tipo", "")))
            o_id = str(d.get(k_origem, ""))
            d_id = str(d.get(k_destino, ""))

            if dom == "im":
                # Ref legada IM: dict tem 'cpf' e 'matricula' (sem tipos)
                o_tipo, d_tipo = "PF", "IM"
                o_id = str(d.get("cpf", ""))
                d_id = str(d.get("matricula", ""))

            # A entidade removida pode estar na origem OU no destino da ref;
            # a chamada mantem a orientacao armazenada (deactivate compara
            # os quatro campos na direcao gravada).
            origem_envolve = o_tipo.lower() == domain and _norm_id(o_id) == cid_norm
            destino_envolve = d_tipo.lower() == domain and _norm_id(d_id) == cid_norm
            if not (origem_envolve or destino_envolve):
                continue

            if dom == "im":
                count = manager.deactivate_reference(cpf=o_id, matricula=d_id)
            else:
                count = manager.deactivate_reference(
                    origem_tipo=o_tipo, origem_id=o_id,
                    destino_tipo=d_tipo, destino_id=d_id)
            desativados += int(count)
    return desativados


def _persist_imovel(matricula: str) -> None:
    """Delegado mantido por compatibilidade com chamadas existentes."""
    if matricula in im_chains:
        _persist_domain("im", matricula, im_chains[matricula])


def _persist_veiculo(placa: str) -> None:
    """Delegado mantido por compatibilidade com chamadas existentes."""
    if placa in mo_chains:
        _persist_domain("mo", placa, mo_chains[placa])


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
    chain = VehicleChain(difficulty=DEFAULT_DIFFICULTY)
    chain.set_signer(generate_authority_keypair("detran"))
    try:
        dados = VehicleEventFactory.fabricacao(**req.model_dump(exclude={"placa"}), placa=placa)
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with chains_lock:
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
def add_veiculo_event(placa: str, req: DomainEventRequest, user: dict = Depends(require_write_access)):
    placa = placa.upper()
    if placa not in mo_chains:
        raise HTTPException(status_code=404, detail=f"Veiculo nao encontrado: {placa}")
    event_type = _validate_event_type(VehicleEventType, req.event_type)
    payload = req.payload
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
    _desativa_vinculos_da_entidade("mo", placa)
    with chains_lock:
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
    cnpj_clean = re.sub(r"\D", "", req.cnpj)
    if cnpj_clean in co_chains:
        raise HTTPException(status_code=409, detail=f"Cadeia ja existe para CNPJ: {cnpj_clean}")
    chain = CompanyChain(difficulty=DEFAULT_DIFFICULTY)
    chain.set_signer(generate_authority_keypair("junta_comercial"))
    try:
        dados = CompanyEventFactory.constituicao(
            **req.model_dump(exclude={"cnpj"}), cnpj=cnpj_clean
        )
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with chains_lock:
        co_chains[cnpj_clean] = chain
    _save_chain_to_db("co", cnpj_clean, chain)
    return ok({"cnpj": cnpj_clean, "bloco_index": genesis.index, "hash": genesis.hash}, "Empresa criada.")

@app.get("/api/co/{cnpj}")
def get_empresa_info(cnpj: str):
    cnpj_clean = re.sub(r"\D", "", cnpj)
    if cnpj_clean not in co_chains:
        raise HTTPException(status_code=404, detail=f"Empresa nao encontrada: {cnpj_clean}")
    chain = co_chains[cnpj_clean]
    estado = chain.get_estado_atual()
    return ok({"cnpj": cnpj_clean, "estado": estado, "blocos": len(chain)})

@app.get("/api/co/{cnpj}/timeline")
def get_empresa_timeline(cnpj: str):
    cnpj_clean = re.sub(r"\D", "", cnpj)
    if cnpj_clean not in co_chains:
        raise HTTPException(status_code=404, detail=f"Empresa nao encontrada: {cnpj_clean}")
    return ok(co_chains[cnpj_clean].get_historico_completo())

@app.get("/api/co/{cnpj}/validate")
def validate_empresa(cnpj: str, require_signatures: bool = False):
    cnpj_clean = re.sub(r"\D", "", cnpj)
    if cnpj_clean not in co_chains:
        raise HTTPException(status_code=404, detail=f"Empresa nao encontrada: {cnpj_clean}")
    valida, msg = co_chains[cnpj_clean].validate(require_signatures=require_signatures)
    return ok({"valida": valida, "mensagem": msg, "blocos": len(co_chains[cnpj_clean])})

@app.post("/api/co/{cnpj}/event", status_code=201)
def add_empresa_event(cnpj: str, req: DomainEventRequest, user: dict = Depends(require_write_access)):
    cnpj_clean = re.sub(r"\D", "", cnpj)
    if cnpj_clean not in co_chains:
        raise HTTPException(status_code=404, detail=f"Empresa nao encontrada: {cnpj_clean}")
    event_type = _validate_event_type(CompanyEventType, req.event_type)
    payload = req.payload
    try:
        block = co_chains[cnpj_clean].add_event(event_type, payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    _save_chain_to_db("co", cnpj_clean, co_chains[cnpj_clean])
    return ok({"bloco_index": block.index, "hash": block.hash}, f"Evento {event_type} registrado.")

@app.delete("/api/co/{cnpj}")
def delete_empresa(cnpj: str, user: dict = Depends(require_admin)):
    cnpj_clean = re.sub(r"\D", "", cnpj)
    if cnpj_clean not in co_chains:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")
    _desativa_vinculos_da_entidade("co", cnpj_clean)
    with chains_lock:
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
    chain = VesselChain(difficulty=DEFAULT_DIFFICULTY)
    chain.set_signer(generate_authority_keypair("capitania_portos"))
    try:
        dados = VesselEventFactory.construcao(
            **req.model_dump(exclude={"registro_nr"}), registro_nr=reg
        )
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with chains_lock:
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

@app.get("/api/em/{registro}/validate")
def validate_embarcacao(registro: str, require_signatures: bool = False):
    if registro not in em_chains:
        raise HTTPException(status_code=404, detail=f"Embarcacao nao encontrada: {registro}")
    valida, msg = em_chains[registro].validate(require_signatures=require_signatures)
    return ok({"valida": valida, "mensagem": msg, "blocos": len(em_chains[registro])})

@app.post("/api/em/{registro}/event", status_code=201)
def add_embarcacao_event(registro: str, req: DomainEventRequest, user: dict = Depends(require_write_access)):
    if registro not in em_chains:
        raise HTTPException(status_code=404, detail=f"Embarcacao nao encontrada: {registro}")
    event_type = _validate_event_type(VesselEventType, req.event_type)
    payload = req.payload
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
    _desativa_vinculos_da_entidade("em", registro)
    with chains_lock:
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
    chain = AircraftChain(difficulty=DEFAULT_DIFFICULTY)
    chain.set_signer(generate_authority_keypair("anac"))
    try:
        dados = AircraftEventFactory.fabricacao(
            **req.model_dump(exclude={"matricula"}), matricula=mat
        )
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with chains_lock:
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

@app.get("/api/ac/{matricula}/validate")
def validate_aeronave(matricula: str, require_signatures: bool = False):
    matricula = matricula.upper()
    if matricula not in ac_chains:
        raise HTTPException(status_code=404, detail=f"Aeronave nao encontrada: {matricula}")
    valida, msg = ac_chains[matricula].validate(require_signatures=require_signatures)
    return ok({"valida": valida, "mensagem": msg, "blocos": len(ac_chains[matricula])})

@app.post("/api/ac/{matricula}/event", status_code=201)
def add_aeronave_event(matricula: str, req: DomainEventRequest, user: dict = Depends(require_write_access)):
    matricula = matricula.upper()
    if matricula not in ac_chains:
        raise HTTPException(status_code=404, detail=f"Aeronave nao encontrada: {matricula}")
    event_type = _validate_event_type(AircraftEventType, req.event_type)
    payload = req.payload
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
    _desativa_vinculos_da_entidade("ac", matricula)
    with chains_lock:
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
    nome = req.nome
    cpf = req.proprietario_cpf
    data = req.data_nascimento
    aid = hashlib.sha256(f"{nome}{cpf}{data}".encode()).hexdigest()[:12]
    if aid in an_chains:
        raise HTTPException(status_code=409, detail=f"Animal ja registrado: {aid}")
    chain = AnimalChain(difficulty=DEFAULT_DIFFICULTY)
    chain.set_signer(generate_authority_keypair("crm veterinario"))
    try:
        dados = AnimalEventFactory.nascimento(**req.model_dump())
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with chains_lock:
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

@app.get("/api/an/{animal_id}/validate")
def validate_animal(animal_id: str, require_signatures: bool = False):
    if animal_id not in an_chains:
        raise HTTPException(status_code=404, detail=f"Animal nao encontrado: {animal_id}")
    valida, msg = an_chains[animal_id].validate(require_signatures=require_signatures)
    return ok({"valida": valida, "mensagem": msg, "blocos": len(an_chains[animal_id])})

@app.post("/api/an/{animal_id}/event", status_code=201)
def add_animal_event(animal_id: str, req: DomainEventRequest, user: dict = Depends(require_write_access)):
    if animal_id not in an_chains:
        raise HTTPException(status_code=404, detail=f"Animal nao encontrado: {animal_id}")
    event_type = _validate_event_type(AnimalEventType, req.event_type)
    payload = req.payload
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
    _desativa_vinculos_da_entidade("an", animal_id)
    with chains_lock:
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


def _estado_para_evento(estado: dict) -> dict:
    """Extrai de um estado AU os campos aceitos por confirmacao()/recusa().

    get_estado_atual() retorna o snapshot completo (status, nomeado_por,
    revogado etc.); passar **estado direto quebraria a factory (TypeError).
    """
    return {k: estado.get(k, "") for k in
            ("nome", "nivel", "escopo", "uf", "cidade")}


class AuthorityAlterRequest(BaseModel):
    nome: Optional[str] = Field(None, description="Novo nome (None = manter)")
    escopo: Optional[str] = Field(None, description="Novo escopo (None = manter)")
    uf: Optional[str] = Field(None, description="Nova UF (None = manter)")
    cidade: Optional[str] = Field(None, description="Nova cidade (None = manter)")
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
    if chain:
        _persist_domain("au", uid, chain)


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


@app.get("/api/au/{uid}/validate")
def autoridade_validate(uid: str, require_signatures: bool = False):
    if uid not in au_chains:
        raise HTTPException(status_code=404, detail=f"Autoridade nao encontrada: {uid}")
    valida, msg = au_chains[uid].validate(require_signatures=require_signatures)
    return ok({"valida": valida, "mensagem": msg, "blocos": len(au_chains[uid])})


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
    # Gate de seguranca (H2): apenas autoridades ativas do livro-razao AU
    # podem nomear — usuarios comuns (mesmo autenticados) sao barrados aqui,
    # antes de qualquer logica de dominio. O can_manage_authority abaixo
    # mantem as regras hierarquicas (N0->N1/N2; N1->N2 do mesmo escopo+UF).
    if not registry.ativa(actor):
        raise HTTPException(
            status_code=403,
            detail="Apenas autoridades ativas podem nomear autoridades.",
        )
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
    if uid in au_chains or get_user(uid) is not None:
        raise HTTPException(status_code=409, detail=f"Autoridade ja existe: {uid}")
    chain = AuthorityChain(difficulty=DEFAULT_DIFFICULTY)
    chain.set_signer(generate_authority_keypair("autoridade"))
    dados["username"] = uid
    try:
        genesis = chain.create_genesis(dados)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    au_chains[uid] = chain
    _persist_autoridade(uid)

    # F4: senha gerada satisfaz a politica (letra+num+especial); se o
    # admin informou uma senha fraca, rejeita com 400.
    senha = req.senha or (secrets.token_hex(6) + "Aa1!")
    try:
        create_user(uid, senha, role="user", nivel=req.nivel,
                    escopo=req.escopo, uf=req.uf.strip().upper(),
                    cidade=dados["cidade"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
                                         nome=req.nome, nivel=nivel,
                                         escopo=novo_escopo,
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
                                         username=uid, **_estado_para_evento(estado),
                                         confirmado_por=actor, data=req.data, motivo=req.motivo,
                                     ))
    _persist_autoridade(uid)
    update_user_metadata(uid,
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
                                         username=uid, **_estado_para_evento(estado),
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
    chain = cls(difficulty=DEFAULT_DIFFICULTY)
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


@app.get("/api/cross/orfaos")
def listar_vinculos_orfaos(user: dict = Depends(require_admin)):
    """F6: vinculos ativos apontando para entidades inexistentes (orfos)."""
    stores = {"pf": chains, "im": im_chains, "mo": mo_chains, "co": co_chains,
              "em": em_chains, "ac": ac_chains, "an": an_chains}
    orfaos = []
    for dom, manager, _ref_cls in _CROSS_MANAGERS:
        k_origem, k_destino = _REF_KEYS.get(
            dom, ("entidade_origem_id", "entidade_destino_id"))
        for ref in getattr(manager, "_references", []):
            d = ref.to_dict() if hasattr(ref, "to_dict") else dict(ref)
            if not d.get("ativo", True):
                continue
            o_tipo = str(d.get("entidade_origem_tipo", d.get("origem_tipo", ""))).lower()
            d_tipo = str(d.get("entidade_destino_tipo", d.get("destino_tipo", ""))).lower()
            o_id = str(d.get(k_origem, ""))
            d_id = str(d.get(k_destino, ""))
            lo, ld = stores.get(o_tipo), stores.get(d_tipo)
            if lo is not None and o_id and o_id not in lo:
                orfaos.append({"domain": dom, "lado": "origem", "tipo": o_tipo,
                               "id": o_id, "tipo_vinculo": d.get("tipo_vinculo", "")})
            if ld is not None and d_id and d_id not in ld:
                orfaos.append({"domain": dom, "lado": "destino", "tipo": d_tipo,
                               "id": d_id, "tipo_vinculo": d.get("tipo_vinculo", "")})
    return ok({"total": len(orfaos), "orfaos": orfaos})


# ── F12: Backup/restore (bundle JSON) ──────────────────────────────────

def _montar_bundle() -> dict:
    """Monta o bundle de backup: cadeias + grafo + cross-references.

    As cadeias sao serializadas no mesmo formato do snapshot legado
    ({"difficulty": n, "chain": [bloco_dict]}), restauravel via
    _rebuild_chain. Autoridades (AU) incluidas.
    """
    cadeias: dict[str, dict] = {}
    counts: dict[str, int] = {}
    for domain, store, _cls, _label in _CHAIN_SPECS:
        cadeias[domain] = {
            cid: _chain_payload(chain) for cid, chain in store.items()
        }
        counts[domain] = len(cadeias[domain])
    return {
        "meta": {
            "versao": 1,
            "gerado_em": time.time(),
            "app": "Blockchain Brasil v4.0",
            "counts": counts,
        },
        "chains": cadeias,
        "graph": pf_graph.to_dict(),
        "cross_references": {
            dom: [r.to_dict() for r in getattr(mgr, "_references", [])]
            for dom, mgr, _ref_cls in _CROSS_MANAGERS
        },
    }


@app.get("/api/admin/backup")
def exportar_backup(user: dict = Depends(require_admin)):
    """F12: exporta cadeias + grafo + cross-references (download JSON).

    Retorna o bundle puro (sem envelope ok()) para o arquivo servir
    direto como entrada do /api/admin/restore.
    """
    bundle = _montar_bundle()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return JSONResponse(
        content=bundle,
        media_type="application/json",
        headers={
            "Content-Disposition":
                f'attachment; filename="blockchain_backup_{stamp}.json"',
        },
    )


@app.post("/api/admin/restore")
def restaurar_backup(bundle: dict, user: dict = Depends(require_admin)):
    """F12: importa bundle gerado pelo backup (upsert por id).

    Cadeias presentes no bundle substituem as de mesmo id (e deixam as
    demais intactas); grafo e cross-references sao recarregados das
    listas do bundle e re-persistidos.
    """
    if not isinstance(bundle, dict) or "meta" not in bundle or "chains" not in bundle:
        raise HTTPException(
            status_code=400,
            detail="Bundle invalido: 'meta' e 'chains' sao obrigatorios.")
    chains_b = bundle.get("chains") or {}
    if not isinstance(chains_b, dict):
        raise HTTPException(status_code=400, detail="Bundle invalido: 'chains' deve ser um objeto.")

    restauradas: dict[str, int] = {}
    with chains_lock:
        for domain, store, cls, label in _CHAIN_SPECS:
            dominio_b = chains_b.get(domain) or {}
            if not isinstance(dominio_b, dict):
                raise HTTPException(
                    status_code=400,
                    detail=f"Bundle invalido: chains.{domain} deve ser um objeto.")
            n = 0
            for cid, data in dominio_b.items():
                if not isinstance(data, dict) or not isinstance(data.get("chain"), list):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Bundle invalido: chains.{domain}.{cid}")
                difficulty = int(data.get("difficulty", 2))
                # Persiste: limpa estado anterior do id e grava snapshot
                # completo + blocos incrementais (mesmo caminho de leitura
                # do startup).
                db.delete_domain_chain(domain, cid)
                db.save_domain_chain(domain, cid, difficulty, data)
                for b in data["chain"]:
                    db.save_block_incremental(domain, cid, difficulty, b)
                store[cid] = _rebuild_chain(cls, data, label,
                                            domain=domain, cid=cid)
                n += 1
            if n:
                restauradas[domain] = n

    # Grafo de relacionamentos PF
    graph_b = bundle.get("graph") or {}
    if graph_b:
        pf_graph.nodes.clear()
        pf_graph.edges.clear()
        pf_graph._edge_index.clear()
        for cpf, n in (graph_b.get("nodes") or {}).items():
            pf_graph.nodes[cpf] = Node(**n)
        for e in graph_b.get("edges") or []:
            edge = Edge(
                from_cpf=e["from_cpf"], to_cpf=e["to_cpf"], tipo=e["tipo"],
                ativo=e.get("ativo", True), block_index=e.get("block_index"),
                timestamp=e.get("timestamp", 0.0), dados=e.get("dados") or {},
            )
            pf_graph.edges.append(edge)
            idx = len(pf_graph.edges) - 1
            pf_graph._edge_index.setdefault(edge.from_cpf, []).append(idx)
            pf_graph._edge_index.setdefault(edge.to_cpf, []).append(idx)
        _save_graph()

    # Cross-references
    refs_b = bundle.get("cross_references") or {}
    for dom, mgr, ref_cls in _CROSS_MANAGERS:
        lista = refs_b.get(dom)
        if lista is None:
            continue
        mgr._references = [ref_cls(**d) for d in lista]
    _save_cross_references()

    return ok({
        "versao_bundle": bundle["meta"].get("versao", 0),
        "gerado_em": bundle["meta"].get("gerado_em", 0),
        "cadeias_restauradas": restauradas,
        "grafo": bool(graph_b),
        "cross_domains": sorted(refs_b.keys()),
    }, "Backup restaurado.")


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
    """Serializa uma cadeia para persistencia (usado no rebuild inicial)."""
    return {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}


def _save_chain_to_db(domain: str, cid: str, chain) -> None:
    """Alias legado de _persist_domain (M5)."""
    _persist_domain(domain, cid, chain)


def _rebuild_chain(cls, data, signer_label: str, domain: str = "", cid: str = ""):
    """Reconstrói uma cadeia a partir do JSON salvo no SQLite.

    Fonte primária: tabela `blocks` (M2, escrita incremental O(1)).
    Fallback: snapshot consolidado em `chains` (formato legado com
    "chain" embutido) — usado por bases anteriores ao M2.
    """
    from blockchain_pf.block import Block
    # Merge snapshot legado (chains.data["chain"]) + blocos incrementais
    # (tabela blocks, M2). O incremental prevalece por índice; cadeias
    # criadas 100% pós-M2 só existem em `blocks`.
    por_indice: dict[int, dict] = {}
    for b in data.get("chain", []):
        por_indice[int(b.get("index", 0))] = b
    for b in (db.load_blocks(domain, cid) if (db and domain and cid) else []):
        por_indice[int(b.get("index", 0))] = b
    blocos = [por_indice[i] for i in sorted(por_indice)]
    if not blocos:
        raise KeyError(f"Cadeia {domain}/{cid} sem blocos restauraveis")
    difficulty = data.get("difficulty", blocos[0].get("difficulty", 2))
    chain = cls(difficulty=difficulty)
    chain.set_signer(generate_authority_keypair(signer_label))
    chain.chain = [Block.from_dict(b) for b in blocos]
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

def startup():
    # Carrega as 8 cadeias do SQLite
    for domain, store, cls, signer_label in _CHAIN_SPECS:
        saved = db.load_all_domain_chains(domain)
        for cid, data in saved.items():
            store[cid] = _rebuild_chain(cls, data, signer_label,
                                        domain=domain, cid=cid)

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


def _seed_autoridades_n0() -> None:
    """Cria as cadeias AU das 3 autoridades de nivel 0 (livro-razao)."""
    init_default_authorities()  # garante as contas N0 (idempotente)
    for uid in ("admin01", "admin02", "admin03"):
        if uid in au_chains and get_user(uid) is not None:
            continue  # Ja seedada (cadeia + conta)
        if uid in au_chains:
            continue  # Cadeia existe, conta recriada acima
        chain = AuthorityChain(difficulty=DEFAULT_DIFFICULTY)
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
    uvicorn.run(app, host="0.0.0.0", port=PORT)
