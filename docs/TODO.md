# Blockchain Brasil — Analise de Codigo & TODO

> Gerado em 2026-09-22 | ~18.300 linhas Python
> **Pendente em 2026-09-26** — apenas itens ainda nao resolvidos.
> O que foi concluido (Fases 1-4, M9/M10/H7, Fase 5, M2/M3/M5,
> bugs N1-N6, auditoria N2 dos admins e features F2/F3/F4/F8/F9/F10/F11)
> foi removido deste arquivo; historico em `git log`.

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
| F6 | Cross-chain integrity | Validar que referencias cruzadas nao ficam orfas ao deletar entidade |
| F7 | Graph rebuild endpoint | `POST /api/pf/graph/rebuild` para reconstruir grafo a partir da cadeia |
| F12 | Export/import backup | Exportar todas cadeias + grafo + cross-references em bundle |

---

## ORDEM RECOMENDADA RESTANTE

1. **L2** — Extrair rotas de `web_app.py` para routers FastAPI por dominio
2. **F6/F7/F12** — Integridade cross-chain, graph rebuild, backup bundle

---

## Resumo atual

| Grupo | Qtd pendente |
|-------|--------------|
| Baixos de arquitetura | 1 (L2) |
| Features novas | 4 (F1, F6, F7, F12) |

Suite: **1152 passed** (~2min30s). Cobertura total: **75%** —
menores: `blockchain_co/chain.py` (60%), `web_app.py` (56%).
