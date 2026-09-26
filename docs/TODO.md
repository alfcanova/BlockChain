# Blockchain Brasil — Analise de Codigo & TODO

> Gerado em 2026-09-22 | ~18.300 linhas Python
> **Pendente em 2026-09-26** — apenas itens ainda nao resolvidos.
> O que foi concluido (Fases 1-4, M9/M10/H7, Fase 5, M2/M3/M5,
> bugs N1-N6, auditoria N2 dos admins e features F2/F3/F4/F6/F8/
> F9/F10/F11/F12) foi removido deste arquivo; historico em `git log`.

---

## BAIXOS (1)

| # | Tipo | Problema |
|---|------|----------|
| L2 | Anti-padrao | ~2.900 linhas de web_app.py em arquivo unico — deveria ser modulos (routers FastAPI por dominio) |

---

## SUGESTOES DE NOVAS FUNCIONALIDADES

| # | Funcionalidade | Descricao |
|---|----------------|-----------|
| F1 | Docker/docker-compose | Containerizar app + SQLite para deploy rapido |
| F7 | Graph rebuild endpoint | `POST /api/pf/graph/rebuild` para reconstruir grafo a partir da cadeia |

---

## ORDEM RECOMENDADA RESTANTE

1. **L2** — Extrair rotas de `web_app.py` para routers FastAPI por dominio
2. **F7** — Graph rebuild endpoint

---

## Resumo atual

| Grupo | Qtd pendente |
|-------|--------------|
| Baixos de arquitetura | 1 (L2) |
| Features novas | 2 (F1, F7) |

Suite: **1166 passed** (~2min30s). Cobertura total: **75%** —
menores: `blockchain_co/chain.py` (60%), `web_app.py` (56%).
