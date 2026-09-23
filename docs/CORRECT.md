# Blockchain Brasil — Plano de Correcao

> Ordem de execucao com dependencias. Cada fase so comeca quando a anterior estiver 100%.

---

## FASE 1: Seguranca & Perda de Dados (CRITICO)

### 1.1 SHA-256 → bcrypt (C1)
**Arquivo:** `blockchain_pf/auth.py`
**Mudanca:**
- Instalar `bcrypt` no `requirements.txt`
- Substituir `_hash_password` para usar `bcrypt.hashpw()` + `bcrypt.checkpw()`
- Manter compatibilidade: se hash antigo (sem `$` no formato), aceitar como legacy e re-hashear no proximo login
- Atualizar `authenticate_user` para chamar `bcrypt.checkpw()`

```python
# Novo:
import bcrypt

def _hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    h = bcrypt.hashpw(f"{salt}:{password}".encode(), bcrypt.gensalt()).decode()
    return f"{salt}${h}"

def _verify_password(password: str, stored: str) -> bool:
    salt, h = stored.split("$", 1)
    if len(h) == 64:  # legacy SHA-256
        return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest() == h
    return bcrypt.checkpw(f"{salt}:{password}".encode(), h.encode())
```

**Testes:** Adicionar `test_auth.py` — testar hash, verify, legado SHA-256.

---

### 1.2 JWT Secret Fixo (C2)
**Arquivo:** `blockchain_pf/auth.py`
**Mudanca:**
- Gerar `SECRET_KEY` uma vez e persistir em arquivo `.jwt_secret` na primeira execução
- Se `JWT_SECRET_KEY` env var existe, usar ela; senao, carregar de `.jwt_secret`
- Se `.jwt_secret` nao existe, gerar e salvar
- Adicionar `.jwt_secret` ao `.gitignore`

```python
_SECRET_FILE = os.path.join(os.path.dirname(__file__), "..", ".jwt_secret")

def _load_or_create_secret() -> str:
    if os.environ.get("JWT_SECRET_KEY"):
        return os.environ["JWT_SECRET_KEY"]
    if os.path.exists(_SECRET_FILE):
        return open(_SECRET_FILE).read().strip()
    key = secrets.token_hex(32)
    with open(_SECRET_FILE, "w") as f:
        f.write(key)
    return key

SECRET_KEY = _load_or_create_secret()
```

---

### 1.3 Senhas N0 no Console (C3)
**Arquivo:** `web_app.py:2816`
**Mudanca:** Remover linha `print("  Autoridades N0: admin01/@dmin01BR...")`. Nao expor senhas em logs.

---

### 1.4 `_persist_chain` Nunca Funciona (C4) — PF Nao Salva
**Arquivo:** `web_app.py:968-973`
**Mudanca:**
- `_persist_chain(cpf)` recebe CPF cru (ex: `"123.456.789-00"`) mas chains tem key limpa (`"12345678900"`)
- Fix: limpar CPF dentro de `_persist_chain` antes de buscar no dict

```python
def _persist_chain(cpf: str) -> None:
    cpf_clean = re.sub(r"\D", "", cpf)
    if cpf_clean in chains and db:
        chain = chains[cpf_clean]
        chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
        db.save_chain(cpf_clean, chain.difficulty, chain_data)
```

**Testes:** Testar que chain criada via API aparece no SQLite.

---

### 1.5 `load_from_file` Perde Signer (C5)
**Arquivos:** `blockchain_pf/chain.py`, `blockchain_im/chain.py`, `blockchain_mo/chain.py`, `blockchain_co/chain.py`, `blockchain_em/chain.py`, `blockchain_ac/chain.py`, `blockchain_an/chain.py`, `blockchain_au/chain.py`
**Mudanca:**
- `save_to_file`: incluir `signer_public_key` (PEM) nos dados serializados
- `load_from_file`: restaurar signer a partir da chave publica salva
- Se chave publica nao existe no arquivo (legado), gerar nova e logar warning

```python
# save_to_file:
data = {
    "difficulty": self.difficulty,
    "signer_public_key": self._signer.get_public_key_pem() if self._signer else None,
    "chain": [b.to_dict() for b in self.chain],
}

# load_from_file:
chain = cls(difficulty=data["difficulty"])
pub_pem = data.get("signer_public_key")
if pub_pem:
    chain._signer = Signer(KeyPair(private_key=None, public_key=pub_pem))
```

**Testes:** Testar round-trip save/load mantendo assinaturas validas.

---

### 1.6 Race Condition em `add_event` (C6)
**Arquivos:** `blockchain_pf/chain.py` + todos `blockchain_*/chain.py`
**Mudanca:**
- Adicionar `threading.Lock()` em cada classe de chain
- `add_event()` e `create_genesis()` adquirem lock antes de modificar `self.chain`

```python
import threading

class Blockchain:
    def __init__(self, ...):
        self._lock = threading.Lock()
        ...

    def add_event(self, event_type, payload):
        with self._lock:
            # logica existente
```

**Testes:** Testar concorrencia com `threading` + `pytest-xdist` ou `concurrent.futures`.

---

## FASE 2: Bugs Altos

### 2.1 `_seed_autoridades_n0` Logica Invertida (H5)
**Arquivo:** `web_app.py:2822`
**Mudanca:** Corrigir condicao de skip:

```python
# Antes (bug):
if uid in au_chains or get_user(uid) is None:
    continue

# Depois:
if uid in au_chains and get_user(uid) is not None:
    continue
```

---

### 2.2 `add_nascimento` Nao Persiste (H4)
**Arquivo:** `web_app.py:1007-1028`
**Mudanca:** Adicionar `_persist_chain(cpf)` apos `create_genesis`:

```python
block = chain.create_genesis(dados)
_persist_chain(cpf)  # <-- adicionar
return ok({...}, "Nascimento registrado (bloco genesis).")
```

---

### 2.3 Enum `DISVINC_PATerna` (H6)
**Arquivo:** `blockchain_pf/events.py:26-27`
**Mudanca:** Renomear para `DISVINC_PATERNA` (ALL_UPPER). Adicionar alias retrocompativel:

```python
DISVINC_PATERNA = "DISVINC_PATERNA"
# Alias para retrocompatibilidade
DISVINC_PATerna = DISVINC_PATERNA
```
- Atualizar `ChainProtector` e `_update_graph_on_event` para usar `DISVINC_PATERNA`
- Repassar em `blockchain_pf/chain.py:241`

---

### 2.4 Privilege Escalation em `criar_autoridade` (H2)
**Arquivo:** `web_app.py:2202`
**Mudanca:** Trocar `get_current_user` por `require_admin`:

```python
@app.post("/api/au", status_code=201)
def criar_autoridade(req: AuthorityCreateRequest, user: dict = Depends(require_admin)):
    ...
```

---

### 2.5 `_users_db` Sem Thread Safety (H3)
**Arquivo:** `blockchain_pf/auth.py:84`
**Mudanca:** Adicionar `threading.Lock()` para operacoes de escrita:

```python
import threading
_user_lock = threading.Lock()

def create_user(username, password, ...):
    with _user_lock:
        if username in _users_db:
            raise ValueError(f"Usuario ja existe: {username}")
        ...
```

---

### 2.6 CPF/CNPJ Checksum (H7)
**Arquivo:** `blockchain_pf/events.py`
**Mudanca:** Implementar validacao completa de CPF e CNPJ:

```python
def _valida_cpf(cpf: str) -> bool:
    cpf_clean = re.sub(r"\D", "", cpf)
    if len(cpf_clean) != 11:
        return False
    if cpf_clean == cpf_clean[0] * 11:  # todos iguais
        return False
    # Digitos verificadores
    sum1 = sum(int(cpf_clean[i]) * (10 - i) for i in range(9))
    d1 = (sum1 * 10 % 11) % 10
    if int(cpf_clean[9]) != d1:
        return False
    sum2 = sum(int(cpf_clean[i]) * (11 - i) for i in range(10))
    d2 = (sum2 * 10 % 11) % 10
    return int(cpf_clean[10]) == d2

def _valida_cnpj(cnpj: str) -> bool:
    cnpj_clean = re.sub(r"\D", "", cnpj)
    if len(cnpj_clean) != 14:
        return False
    if cnpj_clean == cnpj_clean[0] * 14:
        return False
    weights1 = [5,4,3,2,9,8,7,6,5,4,3,2]
    weights2 = [6,5,4,3,2,9,8,7,6,5,4,3,2]
    sum1 = sum(int(cnpj_clean[i]) * weights1[i] for i in range(12))
    d1 = (sum1 % 11 < 2) and 0 or 11 - (sum1 % 11)
    if int(cnpj_clean[12]) != d1:
        return False
    sum2 = sum(int(cnpj_clean[i]) * weights2[i] for i in range(13))
    d2 = (sum2 % 11 < 2) and 0 or 11 - (sum2 % 11)
    return int(cnpj_clean[13]) == d2
```
- Aplicar tambem em `blockchain_im/events.py`, `blockchain_mo/events.py`, `blockchain_co/events.py`

**Testes:** CPF validos/invalidos, CNPJ validos/invalidos, todos zeros, sequenciais.

---

### 2.7 Pydantic Validation em Rotas `req: dict` (H8)
**Arquivo:** `web_app.py`
**Mudanca:** Criar modelo generico e aplicar em 5 rotas:

```python
class DomainEventRequest(BaseModel):
    event_type: str
    payload: dict = {}

# Aplicar em:
# POST /api/mo/{placa}/event
# POST /api/co/{cnpj}/event
# POST /api/em/{registro}/event
# POST /api/ac/{matricula}/event
# POST /api/an/{animal_id}/event
```

---

### 2.8 Autenticacao em Rotas GET (H1)
**Arquivo:** `web_app.py`
**Mudanca:** Nao aplicavel a todas (~50 rotas). Estrategia:
- Rotas de **listagem** (`GET /api/chains`, `GET /api/im`, etc.) ficam publicas ( dados publicos em blockchain)
- Rotas de **detalhe** (`GET /api/chain/{cpf}`, `GET /api/im/{matricula}`, etc.) continuam publicas (verificabilidade)
- **Apenas** rotas de **export completo** (`GET /api/chain/{cpf}/export`) exigem auth de leitura
- **Decisao:** Manter GETs publicos (blockchain = dados publicos por design). Proteger apenas `/export` e rotas de admin.

---

## FASE 3: Medios

### 3.1 PoW Assincrono (M1)
**Arquivo:** `blockchain_pf/chain.py` + todos `blockchain_*/chain.py`
**Mudanca:** Envolver `add_event()` em `run_in_executor` no web_app:

```python
import asyncio
from functools import partial

@app.post("/api/chain/{cpf}/event", status_code=201)
async def add_event(cpf: str, req: EventoRequest, user: dict = Depends(require_write_access)):
    ...
    loop = asyncio.get_event_loop()
    block = await loop.run_in_executor(None, partial(chain.add_event, req.event_type, req.payload))
    ...
```

---

### 3.2 Remover `__import__("re")` (M6)
**Arquivo:** `web_app.py` (5 ocorrências: L1793, L1811, L1820, L1827, L1841)
**Mudanca:** `re` ja importado no topo. Substituir `__import__("re").sub(...)` por `re.sub(...)`.

---

### 3.3 `import hashlib` no Topo (M7)
**Arquivo:** `web_app.py:2005, 2538`
**Mudanca:** Mover `import hashlib` para o topo do arquivo (junto com outros imports).

---

### 3.4 `lifespan` em vez de `on_event` (M8)
**Arquivo:** `web_app.py:2794, 2841`
**Mudanca:** Substituir `@app.on_event("startup")` e `@app.on_event("shutdown")` por `lifespan` context manager:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    _load_all()
    yield
    # shutdown
    _save_current_state()
    db.close()

app = FastAPI(lifespan=lifespan)
```

---

### 3.5 Validacao de UF em Todas Factories (M11)
**Arquivo:** `blockchain_pf/events.py`
**Mudanca:** Adicionar `_valida_uf()` em `casamento()`, `divorcio()`, `obito()`, `adocao()`, `alteracao_nome()`, `disvinculacao_materna()`, `disvinculacao_paterna()` — validar `uf` quando presente.

---

### 3.6 Validacao de Datas (M10)
**Arquivo:** `blockchain_pf/events.py`
**Mudanca:** Chamar `_valida_data()` em todas factories que tem campo de data (ja existe, so nao esta sendo chamado em todas).

---

### 3.7 Configurabilidade via Env (M12)
**Arquivo:** `web_app.py`
**Mudanca:** Extrair hardcoded values para env vars:

```python
PORT = int(os.environ.get("PORT", "8000"))
DEFAULT_DIFFICULTY = int(os.environ.get("DEFAULT_DIFFICULTY", "2"))
TOKEN_EXPIRY_HOURS = int(os.environ.get("TOKEN_EXPIRY_HOURS", "24"))
```

---

### 3.8 Refatorar Duplicacao de Handlers PF (M4)
**Arquivo:** `web_app.py`
**Mudanca:** Criar handler generico para eventos PF:

```python
def _add_pf_event(cpf: str, event_type: str, payload: dict, user: dict):
    chain = get_chain(cpf)
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito and not ChainProtector.pode_adicionar(event_type, True):
        raise HTTPException(400, "Cadeia encerrada por OBITO")
    try:
        block = chain.add_event(event_type, payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))
    _persist_chain(cpf)
    return block

# Cada handler de evento PF chama _add_pf_event
```

---

## FASE 4: Baixos

### 4.1 Naming `getirmaos` → `get_irmaos` (L3)
**Arquivo:** `blockchain_pf/graph.py:256`
**Mudanca:** Renomear metodo. Manter alias `getirmaos = get_irmaos` para retrocompatibilidade.

---

### 4.2 `CONVERSao` → `CONVERSAO` (L4)
**Arquivo:** `blockchain_em/events.py:34`
**Mudanca:** Renomear. Adicionar alias.

---

### 4.3 `DESDE` (L5)
**Arquivo:** `blockchain_an/events.py:37`
**Mudanca:** Verificar se `DESDE` e utilizado em algum lugar. Se sim, renomear para algo claro (ex: `REGISTRO_OBITO`). Se nao, remover.

---

### 4.4 Cross-chain Naming (L6)
**Arquivo:** `blockchain_im/cross_chain.py`
**Mudanca:** Renomear `CrossChainManager` para `CrossChainIM` e `CrossReference` para `IMCrossReference`. Manter aliases.

---

### 4.5 Pydantic Models (L7)
**Arquivo:** `web_app.py`
**Mudanca:**
- `uso_permitido: list = []` → `list[str] = []`
- `proprietarios: list = []` → `list[dict] = []`
- `herdeiros: list` → `list[dict]`
- `valor_transacao: float` → `float = Field(ge=0)`
- Adicionar `max_length` em campos de string criticos

---

### 4.6 Rotas `/validate` Faltantes (L8)
**Arquivo:** `web_app.py`
**Mudanca:** Adicionar `GET /api/co/{cnpj}/validate`, `GET /api/em/{registro}/validate`, `GET /api/ac/{matricula}/validate`, `GET /api/an/{animal_id}/validate`, `GET /api/au/{uid}/validate` — chamar `chain.validate()`.

---

### 4.7 Link `/api/mo` na Landing (L9)
**Arquivo:** `web_app.py:673`
**Mudanca:** Adicionar link para `/api/mo` na secao de links da landing page.

---

## FASE 5: Testes

### 5.1 Tests para CrossChainEM
**Arquivo:** `tests/test_em.py` (adicionar)
**Cobertura:** `create_reference`, `deactivate_reference`, `get_embarcacoes_da_pessoa`, `get_vinculos_ativos`, `stats`, `save/load` round-trip.

### 5.2 Tests para CrossChainAC
**Arquivo:** `tests/test_ac.py` (adicionar)
**Cobertura:** Mesmo que 5.1 para aeronaves.

### 5.3 Tests para `geografia_br.py`
**Arquivo:** `tests/test_geografia.py` (novo)
**Cobertura:** `validar_uf`, `validar_cidade`, `municipios_da_uf`, `capital_da_uf`, `total_municipios`, edge cases (None, empty, acentos).

### 5.4 Tests para CPF/CNPJ Checksum
**Arquivo:** `tests/test_validacao.py` (novo)
**Cobertura:** CPF validos, invalidos, todos iguais, digitos verificadores. CNPJ idem.

### 5.5 Tests para save/load round-trip
**Arquivo:** Adicionar em cada `test_*.py`
**Cobertura:** Criar chain → add events → save → load → validate → verificar assinaturas.

### 5.6 Tests para API endpoints domain chains
**Arquivo:** `tests/test_api.py` (expandir)
**Cobertura:** Criar IM/MO/CO/EM/AC/AN via API → add evento via API → validar via API.

### 5.7 Tests para JWT secret persistido
**Arquivo:** `tests/test_auth.py` (expandir)
**Cobertura:** Login → restart (simular) → login novamente com mesmo token.

---

## Ordem de Execucao

```
FASE 1 (1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6)
   ↓
FASE 2 (2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.7 → 2.8)
   ↓
FASE 3 (3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 3.6 → 3.7 → 3.8)
   ↓
FASE 4 (4.1 → 4.2 → 4.3 → 4.4 → 4.5 → 4.6 → 4.7)
   ↓
FASE 5 (5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.7)
   ↓
pytest → commit → push
```

**Total de arquivos alterados:** ~30
**Total de testes novos estimados:** ~80-100
**Tempo estimado:** 4-6h de implementacao
