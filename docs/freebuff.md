# Freebuff

Projeto desenvolvido com o auxílio do **[Freebuff](https://freebuff.com)** —
agente de codificação por IA (Buffy) usado para análise de código, correção de
bugs, refatoração e ampliação da suíte de testes.

## Como o agente foi usado neste repositório

- **Análise e plano** — `docs/TODO.md` (auditoria de 36 problemas) e
  `docs/CORRECT.md` (plano de correção em 5 fases)
- **Execução** — correções de segurança e integridade (Fases 1–4), validação
  de payload por contrato nas chains de domínio (M9/M10) e testes da Fase 5
- **Verificação** — suíte completa via `python -m pytest tests/`
  (1089 testes) e relatório de cobertura em `htmlcov/index.html`

## Fluxo de trabalho

1. Alterações são validadas pela suíte antes de cada commit
2. Commits temáticos (`fix:`, `docs:`, `chore:`, `test:`)
3. Relatório de cobertura versionado em `htmlcov/`

> Arquivo de notas do mantenedor — sinta-se livre para editar.
