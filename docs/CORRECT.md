# Blockchain Brasil — Plano de Correcao

> Ordem de execucao com dependencias. Cada fase so comeca quando a anterior estiver 100%.
>
> **Status (2026-09-26):** Fases 1 a 5 executadas e validadas (1126 testes).
> Este arquivo mantem apenas o que resta; o conteudo executado foi removido
> e o historico esta em `git log` (commits `c872d5b`, `d2e7e46` e seguintes).

---

## PENDENTE: itens fora do plano original

Estes itens existiam no TODO.md original mas nao tinham entrada no plano;
continuam em aberto:

### P1. Serializacao O(n) a cada evento (M2)
**Arquivos:** `web_app.py` (`_save_chain_to_db` / `_persist_*`)
**Mudanca:** Persistencia incremental — salvar apenas o bloco novo (tabela
`blocks` por cadeia) em vez de serializar a cadeia inteira a cada evento.

### P2. Locks nos dicts globais (M3)
**Arquivo:** `web_app.py`
**Mudanca:** `chains`, `im_chains`, `mo_chains`, `co_chains`, `em_chains`,
`ac_chains`, `an_chains` e cross-managers sao mutados por rotas FastAPI
(threads do event loop) sem lock — usar `threading.Lock()` por dict ou um
`RWLock` unico, cobrindo create/delete e os loops de listagem.

### P3. Unificar padroes de persistencia (M5)
**Arquivo:** `web_app.py`
**Mudanca:** Hoje coexistem 5 helpers (`_persist_chain`, `_persist_imovel`,
`_persist_veiculo`, `_persist_autoridade`, `_save_chain_to_db`). Extrair um
unico `persist(domain, cid, chain)` e migrar as chamadas.

### P4. Extrair routers do monolito (L2)
**Arquivo:** `web_app.py`
**Mudanca:** Separar em `routers/pf.py`, `routers/im.py`, `routers/mo.py`,
`routers/co.py`, `routers/em.py`, `routers/ac.py`, `routers/an.py`,
`routers/au.py`, `routers/auth.py` + `static/` para os HTMLs.

---

## PENDENTE: seguranca de autenticacao

### P5. Rate limiting (F2)
**Alvo:** `/api/auth/login`, rotas de escrita.
**Mudanca:** Middleware/slowapi com janela por IP e backoff por usuario.

### P6. Refresh tokens (F3)
**Arquivo:** `blockchain_pf/auth.py` + rotas `/api/auth/*`.
**Mudanca:** Par access (curto) + refresh (longo, revogavel), endpoint
`POST /api/auth/refresh` e revogacao no logout.

### P7. Password complexity (F4)
**Arquivo:** `blockchain_pf/auth.py create_user` / `UserCreateRequest`.
**Mudanca:** Minimo 8 chars com maiuscula, numero e especial; rejeitar
senhas fracas no cadastro e na troca de senha.

---

## PENDENTE: features (resumo)

F1 Docker/compose · F6 integridade cross-chain (orfos) · F7 graph rebuild ·
F8 health check enriquecido · F9 Prometheus · F10 Alembic · F11 audit log ·
F12 export/import bundle.

Detalhes de cada feature no `docs/TODO.md`.

---

## PENDENTE: testes residuais

| Item | Alcance |
|------|---------|
| T1. API de MO e PF generica | As rotas `/api/mo/*` e PF estao cobertas via `test_fixes.py`; consolidar em `test_api.py` |
| T2. Concurrencia real | Teste com `ThreadPoolExecutor` disparando `add_event` paralelos nas 6 chains (valida C6 em escala) |
| T3. Restart real da app | Subir `TestClient` duas vezes (dois `lifespan`) e verificar recarga de cadeias do SQLite |

---

## Ordem de Execucao Restante

```
P2 (M3 locks) → P3 (M5 persist) → P1 (M2 incremental) → P4 (L2 routers)
   ↓
P5 → P6 → P7 (seguranca de auth)
   ↓
T1 → T2 → T3 (testes residuais)
   ↓
Features F1/F6-F12 (backlog, sem ordem obrigatoria)
   ↓
pytest → commit → push
```

**Suite atual:** 1126 passed | Cobertura: 75% | Principais gaps:
`blockchain_co/chain.py` (60%), `web_app.py` (56%).
