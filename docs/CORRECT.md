# Blockchain Brasil — Plano de Correcao

> Ordem de execucao com dependencias. Cada fase so comeca quando a anterior estiver 100%.
>
> **Status (2026-09-26):** Fases 1 a 5, P1-P3, R1/N2 (auditoria dos
> admins, bugs N3-N6) e P5-P7 (rate limiting, refresh tokens, senha
> forte) executados e validados (1152 testes).
> Este arquivo mantem apenas o que resta; o conteudo executado foi removido
> e o historico esta em `git log`.

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

## PENDENTE: features (resumo)

F1 Docker/compose · F6 integridade cross-chain (orfos) ·
F7 graph rebuild · F12 export/import bundle.

Detalhes de cada feature no `docs/TODO.md`.

---

## PENDENTE: testes residuais

| Item | Alcance |
|------|---------|
| T1. API de MO e PF generica | As rotas `/api/mo/*` e PF estao cobertas via `test_fixes.py`; consolidar em `test_api.py` |
| T2. Concurrencia real | Teste com `ThreadPoolExecutor` disparando `add_event` paralelos nas 6 chains (valida C6/M3 em escala) |
| T3. Restart real da app | Restore pela tabela `blocks` já validado manualmente (restart real, 300+ chains); falta o teste automatizado com dois `lifespan` |

---

## Ordem de Execucao Restante

```
P4 (L2 routers)
   ↓
T1 → T2 → T3 (testes residuais)
   ↓
Features F1/F6/F7/F12 (backlog, sem ordem obrigatoria)
   ↓
pytest → commit → push
```

**Suite atual:** 1152 passed | Cobertura: 75% | Principais gaps:
`blockchain_co/chain.py` (60%), `web_app.py` (56%).
