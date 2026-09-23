# Blockchain Brasil — Analise de Codigo & TODO

> Gerado em 2026-09-22 | 959 testes passando | 8 cadeias | ~18.300 linhas Python

---

## CRITICOS (6)

| # | Tipo | Local | Problema |
|---|------|-------|----------|
| C1 | Seguranca | `auth.py:94` | Senhas com SHA-256 (brute-force em GPUs). Usar bcrypt/argon2 |
| C2 | Seguranca | `auth.py:34-37` | JWT secret muda a cada restart — tokens de sessoes anteriores invalidados |
| C3 | Seguranca | `web_app.py:2816` | Senhas N0 (`@dmin01BR`) impressas em plaintext no console |
| C4 | Bug | `web_app.py:973` | `_persist_chain(cpf)` nunca funciona — cpf vem cru do path param mas chains usa cpf_clean como key. **Cadeias PF nunca persistem no SQLite** |
| C5 | Bug | `chain.py:439` | `load_from_file` gera novo signer — todas assinaturas ECDSA quebram ao recarregar |
| C6 | Race | `chain.py` (todas) | `add_event()` sem lock — duas threads concorrentes criam fork (dois blocos com mesmo previous_hash) |

---

## ALTOS (8)

| # | Tipo | Local | Problema |
|---|------|-------|----------|
| H1 | Seguranca | `web_app.py` rotas GET | ~50 rotas GET sem autenticacao — expoem CPFs, nomes, propriedades |
| H2 | Seguranca | `web_app.py:2202` | `criar_autoridade` so checa `get_current_user`, nao `require_admin` — privilege escalation |
| H3 | Seguranca | `auth.py:84` | `_users_db` dict global sem thread safety — race condition em `create_user` |
| H4 | Bug | `web_app.py:1007` | `add_nascimento` NAO chama `_persist_chain` — genesis nunca salva no SQLite |
| H5 | Bug | `web_app.py:2822` | `_seed_autoridades_n0` logica invertida — `if uid in au_chains or get_user(uid) is None: continue` |
| H6 | Bug | `events.py:26-27` | Enum `DISVINC_PATerna` com case misto vs `DISVINC_MATERNA` — propaga bugs |
| H7 | Inconsistencia | `events.py:42-45` | `_valida_cpf` so checa len=11 — aceita `"00000000000"`, `"11111111111"` |
| H8 | Seguranca | `web_app.py:1745+` | 7 rotas recebem `req: dict` sem validacao Pydantic — injection surface |

---

## MEDIOS (12)

| # | Tipo | Problema |
|---|------|----------|
| M1 | Performance | PoW em `add_event()` bloqueia event loop do asyncio (usar `run_in_executor`) |
| M2 | Performance | Serializa cadeia inteira (O(n)) a cada evento persistido |
| M3 | Performance | Nenhum lock nos dicts globais (chains, im_chains, cross-managers) |
| M4 | Codigo duplicado | Check obito copy-paste 10x nos handlers PF |
| M5 | Codigo duplicado | 4 padroes de persistencia diferentes (_persist_chain, _persist_imovel, _persist_veiculo, _save_chain_to_db) |
| M6 | Anti-padrao | `__import__("re")` usado 5x — `re` ja importado no topo |
| M7 | Anti-padrao | `import hashlib` dentro de corpo de funcao (2x) |
| M8 | Anti-padrao | `@app.on_event("startup")` deprecated — usar `lifespan` |
| M9 | Validacao | Nascimento valida UF+cidade, mas casamento/divorcio/obito nao validam |
| M10 | Validacao | Nenhuma validacao de formato em datas (DD/MM/AAAA) |
| M11 | Validacao | Nenhuma validacao de UF (27 valores oficiais) em campos de UF |
| M12 | Hardcoded | Porta 8000, token expiry 24h, difficulty 2, labels de signer — nada configuravel via env |

---

## BAIXOS (10)

| # | Tipo | Problema |
|---|------|----------|
| L1 | Anti-padrao | `sys.path.insert(0, ...)` no web_app.py |
| L2 | Anti-padrao | 2859 linhas em arquivo unico — deveria ser modulos |
| L3 | Naming | `getirmaos` (camelCase) vs `get_filhos`, `get_pais` (snake_case) |
| L4 | Naming | `CONVERSao` em vez de `CONVERSAO` nos eventos EM |
| L5 | Naming | `DESDE` em vez de `OBITO` duplicado nos eventos AN |
| L6 | Naming | Cross-chain: `CrossChainManager` (IM) vs `CrossChainXX` (outros) |
| L7 | Pydantic | `list` sem tipo, `dict` sem tipo, sem `gt=0` em valores monetarios |
| L8 | Rota | Falta `/validate` para CO, EM, AC, AN, AU |
| L9 | Rota | Falta link `/api/mo` na landing page |
| L10 | Anti-padrao | `model_config` com `extra="ignore"` so em alguns modulos (inconsistente) |

---

## TESTES — Gaps

| Prioridade | Gap |
|------------|-----|
| **Critica** | `CrossChainEM` e `CrossChainAC` — zero cobertura |
| **Critica** | `geografia_br.py` — importado por todas factories, zero testes |
| **Alta** | Nenhum teste de API para rotas IM, CO, EM, AC, AN (eventos) |
| **Alta** | Nenhum teste `save/load` round-trip para VesselChain, AircraftChain, AnimalChain |
| **Alta** | Nenhum teste de integracao cross-domain (PF+MO linkado, autoridade gateando criacao) |
| **Media** | Falta `validate()` e `verify_all_signatures()` nos testes de domain chains |
| **Media** | `test_api.py` so testa happy paths — nenhum payload invalido, CPF malformado |
| **Media** | Sem `@pytest.mark.parametrize` para padroes de validacao repetitivos |

---

## SUGESTOES DE NOVAS FUNCIONALIDADES

| # | Funcionalidade | Descricao |
|---|----------------|-----------|
| F1 | Docker/docker-compose | Containerizar app + SQLite para deploy rapido |
| F2 | Rate limiting | Proteger `/api/auth/login` e endpoints de escrita |
| F3 | Refresh tokens | Substituir token unico de 24h por access+refresh token |
| F4 | Password complexity | Exigir min 8 chars, maiuscula, numero, especial |
| F5 | CPF/CNPJ checksum | Validacao completa (digitos verificadores) |
| F6 | Cross-chain integrity | Validar que referencias cruzadas nao ficam orfas ao deletar entidade |
| F7 | Graph rebuild endpoint | `POST /api/pf/graph/rebuild` para reconstruir grafo a partir da cadeia |
| F8 | Health check | `GET /health` com status de DB, cadeias, memoria |
| F9 | Metrics/observability | Prometheus metrics (request count, latencia, erros) |
| F10 | Migracao de schema | Alembic para evolucao controlada do SQLite |
| F11 | Audit log | Registrar quem criou/modificou cada evento (rastreabilidade) |
| F12 | Export/import backup | Exportar todas cadeias + grafo + cross-references em bundle |

---

## Resumo

| Severidade | Qtd |
|-----------|-----|
| Criticos | 6 |
| Altos | 8 |
| Medios | 12 |
| Baixos | 10 |
| **Total bugs/problemas** | **36** |
| Gaps de teste | 8 |
| Sugestoes novas | 12 |

---

## Ordem de Correcao Recomendada

1. **C4** — PF chains nao persistem no SQLite (perda de dados)
2. **C6** — Race condition em `add_event()` (fork de cadeia)
3. **C1** — SHA-256 → bcrypt/argon2 (vulnerabilidade de senhas)
4. **H4** — Genesis nao salva no SQLite
5. **C2** — JWT secret fixo (nao muda por restart)
6. **H2** — Privilege escalation em criar autoridade
7. **H7** — Validacao completa de CPF/CNPJ
8. **H8** — Pydantic validation em rotas de escrita
9. **M1** — PoW assincrono (run_in_executor)
10. **M4-M5** — Refatorar duplicacao de codigo
