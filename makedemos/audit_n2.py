# -*- coding: utf-8 -*-
"""Auditoria N2 - payloads dos admin_*.html vs contratos get_estado_atual.

Testa: CO (10 eventos), IM (CONFISCO generico + 7 rotas especializadas),
MO (re-teste do fix GARANTIA_EMPRESTIMO). Cleanup com DELETE antes/depois.
"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
TOKEN = None
FALHAS = []


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if TOKEN:
        r.add_header("Authorization", "Bearer " + TOKEN)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode() or "{}")
            detail = detail.get("detail", detail)
        except Exception:
            detail = "?"
        return e.code, detail


def check(ctx, event, code, detail):
    if code in (200, 201):
        print(f"  OK   {ctx:<26} {event:<24} {code}")
    else:
        d = str(detail)[:110]
        print(f"  FALHA {ctx:<25} {event:<24} {code} {d}")
        FALHAS.append((ctx, event, code, d))


# ── Login ────────────────────────────────────────────────────────────
st, resp = req("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
assert st == 200, f"login falhou: {st} {resp}"
TOKEN = resp["data"]["token"]
print("Login admin OK\n")


def delete(path):
    req("DELETE", path)


# ══ CO: 10 eventos (payloads exatos de blockchain_co/admin.html) ═════
print("== CO ==")
CNPJ = "12345678000195"
delete(f"/api/co/{CNPJ}")
st, resp = req("POST", "/api/co", {
    "cnpj": CNPJ, "razao_social": "Auditoria N2 LTDA",
    "nome_fantasia": "N2 Audit", "data_constituicao": "01/02/2020",
    "tipo_empresa": "LTDA", "porte": "PEQUENO", "capital_social": 50000.0,
    "uf": "SP", "cidade": "Sao Paulo", "natureza_juridica": "Sociedade Empresaria Limitada",
    "atividade_principal": "Desenvolvimento de software",
})
assert st == 201, f"criar empresa falhou: {st} {resp}"
print(f"  empresa {CNPJ} criada (201)")

co_events = [
    ("ADICAO_SOCIO", {"socio": {"cpf": "52998224725", "nome": "Socio Um"},
                      "participacao": 50.0, "data_entrada": "10/03/2021", "tipo_socio": "PF"}),
    ("REMOCAO_SOCIO", {"socio": {"cpf": "52998224725", "nome": "Socio Um"},
                       "data_saida": "15/04/2022", "motivo": "Saida amigavel"}),
    ("MUDANCA_QUOTA", {"socio": {"cpf": "52998224725", "nome": "Socio Um"},
                       "participacao_anterior": 50.0, "participacao_nova": 60.0,
                       "data_mudanca": "01/05/2022"}),
    ("MUDANCA_CAPITAL", {"capital_anterior": 50000.0, "capital_novo": 75000.0,
                         "data_mudanca": "01/06/2022", "descricao": "Aumento de capital"}),
    ("ALTERACAO_CONTRATUAL", {"data_alteracao": "01/07/2022",
                              "descricao": "Alteracao do objeto social",
                              "tipo_alteracao": "OBJETO"}),
    ("MUDANCA_ENDERECO", {"novo_endereco": {"logradouro": "Av Paulista 1000",
                                            "cidade": "Sao Paulo", "uf": "SP", "cep": "01310200"},
                          "data_mudanca": "01/08/2022"}),
    ("SUSPENSAO", {"data_suspensao": "01/09/2022", "motivo": "Teste suspensao"}),
    ("REABERTURA", {"data_reabertura": "01/10/2022", "descricao": "Reativacao"}),
    ("CERTIDAO", {"tipo_certidao": "NEGATIVA", "numero": "CERT-001",
                  "data_emissao": "01/11/2022", "orgao_emissor": "JUCESP"}),
    ("BAIXA", {"data_baixa": "01/12/2022", "motivo": "Encerramento teste"}),
]
for evt, payload in co_events:
    st, resp = req("POST", f"/api/co/{CNPJ}/event", {"event_type": evt, "payload": payload})
    check("CO", evt, st, resp if st != 201 else "")
delete(f"/api/co/{CNPJ}")
print()# ══ IM: CONFISCO generico + 7 rotas especializadas ═══════════════════
# Cada rota usa um imovel proprio: eventos de negocio (ex: CONFISCO) mudam
# o estado e bloqueariam os eventos seguintes (maquina de estados, nao
# divergencia de payload).
print("== IM ==")

def cria_imovel(mat):
    delete(f"/api/im/{mat}")
    st, resp = req("POST", "/api/im", {
        "matricula": mat, "endereco_logradouro": "Rua Teste 123",
        "endereco_bairro": "Centro", "endereco_cidade": "Sao Paulo",
        "endereco_uf": "SP", "endereco_cep": "01001000",
        "area_terreno_m2": 500.0, "lat": -23.5505, "lon": -46.6333,
        "proprietario_cpf": "52998224725",
        "proprietario_nome": "Prop Teste",
    })
    assert st == 201, f"criar imovel {mat} falhou: {st} {resp}"

im_testes = [
    ("IM/generico", "CONFISCO", "event",
     {"event_type": "CONFISCO",
      "payload": {"matricula": "N2IM0001", "autoridade": "Receita Federal",
                  "processo_numero": "PROC-2026-001",
                  "data_confisco": "01/09/2026", "motivo": "Auditoria N2"}}),
    ("IM/rota", "construcao", "event/construcao",
     {"matricula": "N2IM0002", "descricao": "Casa sede",
      "area_construida_m2": 180.5, "tipo_construcao": "RESIDENCIAL",
      "pavimentos": 2, "data_inicio": "01/03/2023",
      "data_fim": "01/12/2023", "responsavel_tecnico": "Eng. Teste CREA-123"}),
    ("IM/rota", "compra_venda", "event/compra_venda",
     {"matricula": "N2IM0003", "comprador_cpf": "15350946056",
      "comprador_nome": "Comprador Teste", "vendedor_cpf": "52998224725",
      "vendedor_nome": "Prop Teste", "valor_transacao": 350000.0,
      "data_transacao": "15/01/2024", "escritura_numero": "ESC-777",
      "cartorio": "1 CRI Sao Paulo"}),
    ("IM/rota", "doacao", "event/doacao",
     {"matricula": "N2IM0004", "donatario_cpf": "39053344705",
      "donatario_nome": "Donatario Teste", "doador_cpf": "15350946056",
      "doador_nome": "Comprador Teste", "data_doacao": "01/02/2025",
      "motivo": "Doacao entre parentes"}),
    ("IM/rota", "heranca", "event/heranca",
     {"matricula": "N2IM0005", "inventariado_cpf": "39053344705",
      "inventariado_nome": "Donatario Teste",
      "herdeiros": [{"cpf": "12345678909", "nome": "Herdeiro Um", "participacao": 60.0},
                    {"cpf": "98765432100", "nome": "Herdeira Dois", "participacao": 40.0}],
      "data_obito": "01/03/2025", "inventario_tipo": "JUDICIAL"}),
    ("IM/rota", "garantia", "event/garantia",
     {"matricula": "N2IM0006", "credor_nome": "Banco Teste",
      "credor_cnpj": "12345678000195", "valor_garantia": 200000.0,
      "data_garantia": "01/04/2025", "data_vencimento": "01/04/2035",
      "tipo_garantia": "HIPOTECARIA", "taxa_juros": 9.5, "prazo_meses": 120}),
    ("IM/rota", "leilao", "event/leilao",
     {"matricula": "N2IM0007", "data_leilao": "01/05/2025", "valor_minimo": 400000.0,
      "lance_vencedor": 450000.0, "vencedor_cpf": "12345678909",
      "vencedor_nome": "Arrematante Teste", "leiloeiro": "Leiloeiro Oficial SA",
      "tipo": "JUDICIAL"}),
    ("IM/rota", "reforma", "event/reforma",
     {"matricula": "N2IM0008", "descricao": "Ampliacao quintal",
      "tipo": "AMPLIACAO", "area_anterior_m2": 180.5, "area_nova_m2": 220.0,
      "data_inicio": "01/06/2025", "data_fim": "01/08/2025"}),
]
for ctx, nome, rota, body in im_testes:
    mat = body.get("matricula") or body["payload"]["matricula"]
    cria_imovel(mat)
    st, resp = req("POST", f"/api/im/{mat}/{rota}", body)
    check(ctx, nome, st, resp if st != 201 else "")
    delete(f"/api/im/{mat}")
print()

# ══ MO: re-teste do fix GARANTIA_EMPRESTIMO (payload corrigido) ══════
print("== MO (re-teste fix) ==")
PLACA = "BDX8F45"
delete(f"/api/mo/{PLACA}")
st, resp = req("POST", "/api/mo", {
    "placa": PLACA, "renavan": "00987654321", "chassis": "9BWZZZ377VT004251",
    "marca": "VW", "modelo": "Gol", "ano_fabricacao": 2020, "ano_modelo": 2021,
    "cor": "PRATA", "combustivel": "FLEX",
    "uf": "SP", "cidade": "Sao Paulo", "cilindradas": 1000, "potencia_cv": 80,
})
assert st == 201, f"criar veiculo falhou: {st} {resp}"
print(f"  veiculo {PLACA} criado (201)")

st, resp = req("POST", f"/api/mo/{PLACA}/event", {
    "event_type": "GARANTIA_EMPRESTIMO",
    "payload": {"placa": PLACA,
                "credor": {"nome": "Banco Fix", "cnpj": "12345678000195"},
                "valor_emprestimo": 40000.0, "data_garantia": "10/09/2026",
                "data_vencimento": "10/09/2031", "taxa_juros": 12.5,
                "parcelas": 60, "tipo_garantia": "ALIENACAO_FIDUCIARIA"},
})
check("MO/fix", "GARANTIA_EMPRESTIMO", st, resp if st != 201 else "")
delete(f"/api/mo/{PLACA}")
print()

# ══ AU: rotas dedicadas (bodies exatos de blockchain_au/admin.html) ═══
print("== AU ==")
# O ator precisa ser autoridade ativa no livro-razao AU: login como N0.
st, resp = req("POST", "/api/auth/login", {"username": "admin01", "password": "@dmin01BR"})
assert st == 200, f"login N0 admin01 falhou: {st} {resp}"
TOKEN = resp["data"]["token"]

st, resp = req("POST", "/api/au", {
    "nome": "Autoridade N1 Auditoria", "nivel": 1, "escopo": "mo",
    "uf": "SP", "cidade": "", "senha": "@ud1tN1BR", "motivo": "Auditoria N2",
})
check("AU", "POST /api/au (nomear N1)", st, resp if st != 201 else "")
if st == 201:
    a1 = resp["data"]["id"]
    st, resp = req("POST", "/api/auth/login", {"username": a1, "password": "@ud1tN1BR"})
    assert st == 200, f"login autoridade N1 falhou: {st} {resp}"
    TOKEN_A1 = resp["data"]["token"]

    # N1 nomeia N2 do mesmo escopo+UF (modal 'Nomear Subordinado')
    TOKEN = TOKEN_A1  # requisicao feita pela N1
    st, resp = req("POST", "/api/au", {
        "nome": "Autoridade N2 Auditoria", "nivel": 2, "escopo": "mo",
        "uf": "SP", "cidade": "Sao Paulo", "senha": "@ud1tN2BR", "motivo": "Auditoria N2",
    })
    check("AU", f"{a1} nomeia N2", st, resp if st != 201 else "")

    if st == 201:
        a2 = resp["data"]["id"]
        st, resp = req("POST", f"/api/au/{a2}/alterar",
                       {"nome": "Autoridade N2 Renomeada", "motivo": "Auditoria N2"})
        check("AU", "alterar (pendentes)", st, resp if st not in (200, 201) else "")
        st, resp = req("POST", f"/api/au/{a2}/confirmar", {"motivo": "Auditoria N2"})
        check("AU", "confirmar alteracao", st, resp if st not in (200, 201) else "")
        st, resp = req("POST", f"/api/au/{a2}/alterar",
                       {"cidade": "Campinas", "motivo": "Auditoria N2"})
        if st in (200, 201):
            st, resp = req("POST", f"/api/au/{a2}/recusar", {"motivo": "Auditoria N2"})
        check("AU", "recusar alteracao", st, resp if st not in (200, 201) else "")
        st, resp = req("POST", f"/api/au/{a2}/revogar", {"motivo": "Fim da auditoria N2"})
        check("AU", "revogar", st, resp if st not in (200, 201) else "")
        # Cleanup como N0: apaga contas e revoga a N1
        st, resp = req("POST", "/api/auth/login", {"username": "admin01", "password": "@dmin01BR"})
        assert st == 200, f"re-login N0 falhou: {st} {resp}"
        TOKEN = resp["data"]["token"]
        req("DELETE", f"/api/auth/users/{a2}")
        st, resp = req("POST", f"/api/au/{a1}/revogar", {"motivo": "Fim da auditoria N2"})
        check("AU", "revogar N1 (cleanup)", st, resp if st not in (200, 201) else "")
        req("DELETE", f"/api/auth/users/{a1}")
print()

# ── Resumo ───────────────────────────────────────────────────────────
print("=" * 60)
if FALHAS:
    print(f"RESULTADO: {len(FALHAS)} FALHA(S)")
    for ctx, evt, code, d in FALHAS:
        print(f"  - [{ctx}] {evt}: {code} {d}")
    raise SystemExit(1)
print("RESULTADO: TODOS OK")
