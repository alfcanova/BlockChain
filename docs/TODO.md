# Blockchain Brasil — Analise de Codigo & TODO

> Gerado em 2026-09-22 | ~18.300 linhas Python
> **Pendente em 2026-09-26** — apenas itens ainda nao resolvidos.
> O que foi concluido (Fases 1-4, M9/M10/H7, Fase 5, correcao do bug
> `delete_user`) foi removido deste arquivo; historico em `git log`.

---

## MEDIOS (4)

| # | Tipo | Problema |
|---|------|----------|
| M2 | Performance | Serializa cadeia inteira (O(n)) a cada evento persistido |
| M3 | Performance | Nenhum lock nos dicts globais (chains, im_chains, cross-managers) |
| M5 | Codigo duplicado | 5 padroes de persistencia diferentes (_persist_chain, _persist_imovel, _persist_veiculo, _persist_autoridade, _save_chain_to_db) |
| L2 | Anti-padrao | ~2.900 linhas de web_app.py em arquivo unico — deveria ser modulos |

> M1, M4, M6-M8, M9-M12, L1, L3-L10 e C1-C6/H1-H8: resolvidos.

---

## BUGS DESCOBERTOS DURANTE A CORRECAO

| # | Tipo | Local | Problema |
|---|------|-------|----------|
| N1 | Bug | `auth.py delete_user` | Sem DB, checava `username in _users_db` APÓS deletar — sempre retornava False. **Corrigido** (retorno unificado memória/DB), mantido aqui como registro do padrão: funções de auth com retorno dependente da ordem memória/DB precisam de revisão |
| N2 | Bug latente | `tests/test_fixes.py` | API aceitava `MUDANCA_COR` com campo `cor`, mas o estado consome `cor_nova` — evento nunca alterava a cor. Corrigido no teste; revisar outros payloads de admin contra os contratos de `get_estado_atual` |

---

## SUGESTOES DE NOVAS FUNCIONALIDADES

| # | Funcionalidade | Descricao |
|---|----------------|-----------|
| F1 | Docker/docker-compose | Containerizar app + SQLite para deploy rapido |
| F2 | Rate limiting | Proteger `/api/auth/login` e endpoints de escrita |
| F3 | Refresh tokens | Substituir token unico de 24h por access+refresh token |
| F4 | Password complexity | Exigir min 8 chars, maiuscula, numero, especial |
| F5 | CPF/CNPJ checksum | ~~Validacao completa (digitos verificadores)~~ **FEITO (H7)** |
| F6 | Cross-chain integrity | Validar que referencias cruzadas nao ficam orfas ao deletar entidade |
| F7 | Graph rebuild endpoint | `POST /api/pf/graph/rebuild` para reconstruir grafo a partir da cadeia |
| F8 | Health check | `GET /health` com status de DB, cadeias, memoria |
| F9 | Metrics/observability | Prometheus metrics (request count, latencia, erros) |
| F10 | Migracao de schema | Alembic para evolucao controlada do SQLite |
| F11 | Audit log | Registrar quem criou/modificou cada evento (rastreabilidade) |
| F12 | Export/import backup | Exportar todas cadeias + grafo + cross-references em bundle |

---

## ORDEM RECOMENDADA RESTANTE

1. **M3** — Locks nos dicts globais de `web_app.py` (escritas concorrentes via API)
2. **M5** — Unificar `_persist_*` / `_save_chain_to_db` em um helper por dominio
3. **M2** — Persistencia incremental (evitar serializar a cadeia inteira por evento)
4. **L2** — Extrair rotas de `web_app.py` para routers FastAPI por dominio
5. **F2/F3** — Rate limiting + refresh tokens (seguranca de autenticacao)

---

## Resumo atual

| Grupo | Qtd pendente |
|-------|--------------|
| Medios/baixos de performance e arquitetura | 4 (M2, M3, M5, L2) |
| Bugs novos registrados (ja corrigidos, a documentar) | 2 (N1, N2) |
| Features novas | 11 (F1-F4, F6-F12) |

Suite: **1126 passed** (~2min20s). Cobertura total: **75%** —
menores: `blockchain_co/chain.py` (60%), `web_app.py` (56%).
