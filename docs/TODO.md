# Blockchain Brasil — Analise de Codigo & TODO

> Gerado em 2026-09-22 | ~18.300 linhas Python
> **Pendente em 2026-09-26** — apenas itens ainda nao resolvidos.
> O que foi concluido (Fases 1-4, M9/M10/H7, Fase 5, bugs N1, M2/M3/M5)
> foi removido deste arquivo; historico em `git log`.

---

## BAIXOS (1)

| # | Tipo | Problema |
|---|------|----------|
| L2 | Anti-padrao | ~2.900 linhas de web_app.py em arquivo unico — deveria ser modulos (routers FastAPI por dominio) |

> M1-M5, M6-M8, M9-M12, L1, L3-L10 e C1-C6/H1-H8: resolvidos.
> M2/M3/M5 resolvidos em 2026-09-26: `_persist_domain` unificado (M5),
> escrita incremental por bloco na tabela `blocks` (M2) e `chains_lock`
> protegendo as 14 mutacoes dos dicts globais (M3).

---

## BUGS DESCOBERTOS DURANTE A CORRECAO

| # | Tipo | Local | Problema |
|---|------|-------|----------|
| N1 | Bug | `auth.py delete_user` | Sem DB, checava `username in _users_db` APÓS deletar — sempre retornava False. **Corrigido** (retorno unificado memória/DB), mantido aqui como registro do padrão: funções de auth com retorno dependente da ordem memória/DB precisam de revisão |
| N2 | Bug latente | `tests/test_fixes.py` | API aceitava `MUDANCA_COR` com campo `cor`, mas o estado consome `cor_nova` — evento nunca alterava a cor. Corrigido no teste. **Auditoria completa dos admins executada em 2026-09-26 (ver N3-N6)** |
| N3 | Bug front | `blockchain_mo/admin.html` | `GARANTIA_EMPRESTIMO` enviava `credor_nome`/`credor_cnpj` planos, mas o contrato exige dict `credor:{nome,cnpj}` — evento sempre rejeitado (400). **Corrigido** no admin; validado 13/13 eventos MO contra o servidor real |
| N4 | Bug seed | `blockchain_au/events.py` | Factory `nomeacao` rejeitava `nivel=0` — o seed das 3 autoridades N0 (`_seed_autoridades_n0`) nunca funcionou e todo o fluxo AU ficava barrado (403). **Corrigido**: N0 válido como autoridade nacional (sem escopo/UF/cidade) + teste novo |
| N5 | Bug M2 | `web_app.py _rebuild_chain` | `save_block_incremental` gravava snapshot `{"difficulty": n}` sem `"chain"` em `chains` — qualquer cadeia criada pós-M2 quebrava o restore do startup (KeyError). **Corrigido**: restore faz merge snapshot legado + tabela `blocks` (blocks prevalece por índice). Validado com restart real (300+ chains) |
| N6 | Bug AU | `web_app.py` rotas `/api/au` | (a) `alterar` não passava `nivel` para a factory — bloco PENDENTE rebaixava a autoridade a nivel 0 e quebrava permissões; (b) `confirmar` chamava `update_user_metadata(nome=...)` inexistente (500); (c) `confirmar/recusar` passavam `**estado` completo à factory (TypeError latente — rotas sem cobertura em testes); (d) `criar_autoridade` sobrescrevia cadeia existente silenciosamente → agora 409. **Todos corrigidos**; fluxo completo N0→N1→N2 (nomear/alterar/confirmar/recusar/revogar) validado via `makedemos/audit_n2.py` |

> Auditoria N2 (2026-09-26): payloads EXATOS de todos os admins testados
> contra o servidor real — EM 9/9, AC 9/9, AN 9/9, MO 13/13, CO 10/10,
> IM 8/8 (CONFISCO genérico + 7 rotas especializadas), AU 7/7 (rotas
> dedicadas). Script: `makedemos/audit_n2.py`.

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

1. **L2** — Extrair rotas de `web_app.py` para routers FastAPI por dominio
2. **F2/F3** — Rate limiting + refresh tokens (seguranca de autenticacao)

---

## Resumo atual

| Grupo | Qtd pendente |
|-------|--------------|
| Baixos de arquitetura | 1 (L2) |
| Bugs novos | N1-N6 todos corrigidos |
| Features novas | 11 (F1-F4, F6-F12) |

Suite: **1127 passed** (~2min15s). Cobertura total: **75%** —
menores: `blockchain_co/chain.py` (60%), `web_app.py` (56%).
