# Blockchain Brasil — Plano de Correcao

> Ordem de execucao com dependencias. Cada fase so comeca quando a anterior estiver 100%.
>
> **Status (2026-09-26):** Fases 1 a 5 e P1-P3 executados e validados (1126 testes).
> Este arquivo mantem apenas o que resta; o conteudo executado foi removido
> e o historico esta em `git log`.

---

## RESOLVIDO NESTA RODADA (P1-P3)

- **P1/M2** — Persistencia incremental: tabela `blocks` (domain, id,
  block_index, block_json) + `save_block_incremental()`; escrita O(1)
  por evento via `_persist_domain()`.
- **P2/M3** — `chains_lock` (threading.Lock) protegendo as 14 mutacoes
  dos dicts globais em `web_app.py`.
- **P3/M5** — Helper unico `_persist_domain(domain, cid, chain)`;
  `_persist_chain/_persist_imovel/_persist_veiculo/_persist_autoridade/
  _save_chain_to_db` viraram delegados de uma linha.

---

## PENDENTE: arquitetura

### P4. Extrair routers do monolito (L2)
**Arquivo:** `web_app.py` (~2.900 linhas, 136 rotas)
**Mudanca:** Separar em `routers/pf.py`, `routers/im.py`, `routers/mo.py`,
`routers/co.py`, `routers/em.py`, `routers/ac.py`, `routers/an.py`,
`routers/au.py`, `routers/auth.py` + `static/` para os HTMLs.
**Atencao:** `tests/test_api.py` e `test_fixes.py` importam `chains` e os
dicts de dominio diretamente de `web_app` — manter re-exports la ou
atualizar os imports junto.

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

## RESOLVIDO: revisao de contratos dos admins (R1/N2)

Auditoria executada em 2026-09-26 contra servidor real (script
`makedemos/audit_n2.py`): payloads EXATOS dos `admin_*.html` testados
contra os contratos das APIs. Resultado: EM 9/9 · AC 9/9 · AN 9/9 ·
MO 13/13 · CO 10/10 · IM 8/8 · AU 7/7. Bugs descobertos e corrigidos
no caminho: N3 (MO credor dict), N4 (seed N0), N5 (restore M2),
N6 (rotas AU alterar/confirmar/recusar) — detalhes no `docs/TODO.md`.

---

## PENDENTE: testes residuais

| Item | Alcance |
|------|---------|
| T1. API de MO e PF generica | As rotas `/api/mo/*` e PF estao cobertas via `test_fixes.py`; consolidar em `test_api.py` |
| T2. Concurrencia real | Teste com `ThreadPoolExecutor` disparando `add_event` paralelos nas 6 chains (valida C6/M3 em escala) |
| T3. Restart real da app | ~~Validar recarga pela tabela `blocks`~~ **Feito em 2026-09-26** (N5): restore com merge blocks+chains validado em restart real com 300+ chains. Falta apenas o teste automatizado com dois `lifespan` |

---

## Ordem de Execucao Restante

```
P4 (L2 routers)
   ↓
P5 → P6 → P7 (seguranca de auth)
   ↓
R1 (revisar admins) · T1 → T2 → T3 (testes residuais)
   ↓
Features F1/F6-F12 (backlog, sem ordem obrigatoria)
   ↓
pytest → commit → push
```

**Suite atual:** 1127 passed | Cobertura: 75% | Principais gaps:
`blockchain_co/chain.py` (60%), `web_app.py` (56%).
