#!/usr/bin/env python3
"""
demo_data.py — Gerador massivo de dados aleatórios para demonstração.

Gera 300 PF + 300 IM + 300 MO com perfis diversificados:
  PF: solteiros, casados, divorciados, viúvos, vacinados, com próteses, etc.
  IM: com construção, venda, doação, herança, garantia, leilão, desmembramento, etc.
  MO: com sinistro, perda total, multa, recall, troca de peça, garantia, etc.

Execute: PYTHONIOENCODING=utf-8 python demo_data.py
"""

import random
import string
import sys
import os
import io
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blockchain_pf import Blockchain, EventFactory, EventType, generate_authority_keypair
from blockchain_im import PropertyChain, PropertyEventFactory, PropertyEventType
from blockchain_mo import VehicleChain, VehicleEventFactory, VehicleEventType


# ═══════════════════════════════════════════════════════════════════════
#  BANCOS DE DADOS REALISTAS
# ═══════════════════════════════════════════════════════════════════════

NOMES_M = [
    "João", "Pedro", "Lucas", "Gabriel", "Matheus", "Rafael", "Gustavo",
    "Felipe", "Bruno", "Leonardo", "Thiago", "Diego", "Eduardo", "Marco",
    "Carlos", "Paulo", "André", "Fernando", "Roberto", "José", "Antônio",
    "Francisco", "Sérgio", "Luis", "Ricardo", "Alexandre", "Daniel",
    "Marcelo", "Marcos", "Rogério", "Sandro", "Tiago", "Vinícius",
    "Samuel", "Enzo", "Miguel", "Arthur", "Bernardo", "Heitor", "Valentim",
]

NOMES_F = [
    "Maria", "Ana", "Juliana", "Fernanda", "Patrícia", "Camila", "Amanda",
    "Bruna", "Carla", "Daniela", "Renata", "Adriana", "Vanessa", "Letícia",
    "Bianca", "Tatiana", "Priscila", "Luciana", "Mariana", "Isabela",
    "Cláudia", "Sandra", "Lúcia", "Cristina", "Beatriz", "Larissa", "Natália",
    "Raquel", "Viviane", "Simone", "Helena", "Alice", "Yasmin", "Cecília",
]

SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira",
    "Alves", "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins",
    "Carvalho", "Almeida", "Lopes", "Soares", "Fernandes", "Vieira",
    "Barbosa", "Rocha", "Dias", "Nascimento", "Andrade", "Moreira",
    "Nunes", "Marques", "Machado", "Mendes", "Freitas", "Cardoso",
    "Ramos", "Gonçalves", "Santana", "Teixeira", "Araújo", "Pinto",
    "Correia", "Campos", "Azevedo", "Castro", "Cavalcanti", "Ribeiro",
]

CIDADES = [
    ("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Brasília", "DF"),
    ("Salvador", "BA"), ("Fortaleza", "CE"), ("Belo Horizonte", "MG"),
    ("Manaus", "AM"), ("Curitiba", "PR"), ("Recife", "PE"), ("Porto Alegre", "RS"),
    ("Goiânia", "GO"), ("Belém", "PA"), ("Guarulhos", "SP"), ("Campinas", "SP"),
    ("São Luís", "MA"), ("Maceió", "AL"), ("Campo Grande", "MS"),
    ("Teresina", "PI"), ("João Pessoa", "PB"), ("Natal", "RN"),
    ("Cuiabá", "MT"), ("Aracaju", "SE"), ("Londrina", "PR"),
    ("Joinville", "SC"), ("Florianópolis", "SC"), ("Vitória", "ES"),
    ("Juiz de Fora", "MG"), ("Santos", "SP"), ("Ribeirão Preto", "SP"),
    ("Sorocaba", "SP"), ("Osasco", "SP"), ("São José dos Campos", "SP"),
]

BAIRROS = [
    "Centro", "Jardim América", "Vila Mariana", "Copacabana", "Boa Viagem",
    "Savassi", "Batel", "Moinhos de Vento", "Aldeota", "Meireles",
    "Piedade", "Jardim Paulista", "Moema", "Pinheiros", "Itaim Bibi",
    "Brooklin", "Vila Olímpia", "Tatuapé", "Mooca", "Santana",
    "Vila Nova Conceição", "Consolação", "República", "Liberdade", "Aclimação",
]

LOGRADOUROS = ["Rua", "Avenida", "Alameda", "Travessa", "Praça", "Rodovia"]

NOMES_RUA = [
    "das Flores", "da Paz", "Brasil", "São Paulo", "dos Andradas",
    "Paraná", "Bahia", "Minas Gerais", "Rio de Janeiro", "Atlântida",
    "Buenos Aires", "Lima", "Bolívar", "San Martín", "Machado de Assis",
    "Castelo Branco", "Getúlio Vargas", "Juscelino Kubitschek",
    "Tiradentes", "Dom Pedro II", "XV de Novembro", "Sete de Setembro",
    "Paulista", "Brigadeiro Faria Lima", "Aviação Brasileira",
]

MARCAS_VEICULOS = [
    ("Volkswagen", "Gol"), ("Volkswagen", "Polo"), ("Volkswagen", "Virtus"),
    ("Volkswagen", "T-Cross"), ("Volkswagen", "Taos"),
    ("Chevrolet", "Onix"), ("Chevrolet", "Tracker"), ("Chevrolet", "S10"),
    ("Chevrolet", "Equinox"),
    ("Fiat", "Argo"), ("Fiat", "Cronos"), ("Fiat", "Pulse"), ("Fiat", "Fastback"),
    ("Hyundai", "HB20"), ("Hyundai", "Creta"), ("Hyundai", "Tucson"),
    ("Toyota", "Corolla"), ("Toyota", "Hilux"), ("Toyota", "SW4"), ("Toyota", "Yaris"),
    ("Jeep", "Renegade"), ("Jeep", "Compass"), ("Jeep", "Commander"),
    ("Renault", "Kwid"), ("Renault", "Duster"), ("Renault", "Captur"),
    ("Honda", "Civic"), ("Honda", "HR-V"), ("Honda", "WR-V"),
    ("Nissan", "Kicks"), ("Nissan", "Versa"), ("Nissan", "Frontier"),
    ("Ford", "Bronco Sport"), ("Ford", "Ranger"),
    ("Citroën", "C3"), ("Peugeot", "208"), ("Peugeot", "2008"),
]

CORES_VEICULOS = [
    "Prata", "Branco", "Preto", "Vermelho", "Azul", "Cinza",
    "Vermelho Escuro", "Azul Escuro", "Branco Pérola", "Cinza Chumbo",
]

COMBUSTIVEIS = ["GASOLINA", "ETANOL", "FLEX", "DIESEL", "ELETRICO", "HIBRIDO"]

FABRICANTES = [
    ("Volkswagen do Brasil", "61198164000123"),
    ("General Motors do Brasil", "61439835000103"),
    ("FCA Fiat", "33000167000101"),
    ("Hyundai Motor Brasil", "02558157000162"),
    ("Toyota do Brasil", "51023583000110"),
    ("Stellantis Brasil", "33592510000154"),
]

TIPOS_SINISTRO = ["COLISAO", "ATROPELAMENTO", "INCENDIO", "ALAGAMENTO", "OUTRO"]
ORGAOS_TRANSITO = ["DETRAN/SP", "DETRAN/RJ", "DETRAN/MG", "DETRAN/PR", "DETRAN/BA"]
ENQUADRAMENTOS = [
    ("Art. 165 CTB", "Dirigir sob influencia de alcool", 7, 293.47),
    ("Art. 163 CTB", "Nao respeitar sinal vermelho", 5, 293.47),
    ("Art. 167 CTB", "Velocidade acima do permitido", 5, 293.47),
    ("Art. 175 CTB", "Nao usar cinto de seguranca", 5, 197.96),
    ("Art. 170 CTB", "Ultrapassar em local proibido", 5, 293.47),
    ("Art. 218 CTB", "Velocidade entre 20-50% acima", 3, 197.96),
    ("Art. 219 CTB", "Velocidade entre 50-100% acima", 5, 885.42),
    ("Art. 203 CTB", "Avancar sinal vermelho", 7, 1207.02),
]

OFICINAS = [
    "Oficina Mecanica Central", "Mecanica Geral Express",
    "Oficina do Carro", "AutoMecanica Brasil", "Servico Auto Rapido",
    "Oficina do Silva", "Mecanica Especializada XYZ",
]

NOMES_VACINAS = [
    "COVID-19 (Pfizer)", "COVID-19 (AstraZeneca)", "COVID-19 (CoronaVac)",
    "Febre Amarela", "Hepatite B", "Triplice Viral", "Pentavalente",
    "Gripe (Influenza)", "HPV", "Pneumococica", "Meningococica",
]

PROTESES = [
    "Protese de Joelho Direito", "Protese de Quadril Esquerdo",
    "Protese de Coluna Lombar", "Marca-passo Cardiaco",
    "Protese Dentaria", "Lente Intraocular Direita",
    "Protese de Ombro Direito", "Stent Coronario",
]

HOSPITAIS = [
    "Hospital Sao Paulo", "Hospital Albert Einstein",
    "Hospital Sirio-Libanes", "Hospital Albert Sabin",
    "Hospital Beneficencia Portuguesa", "Hospital Sao Camilo",
]

SECUNDARIOS_M = ["Carlos", "Eduardo", "Fernando", "Gustavo", "Henrique",
                  "Igor", "Julio", "Leonardo", "Marcos", "Nelson",
                  "Otavio", "Paulo", "Ricardo", "Sergio", "Thiago"]

SECUNDARIOS_F = ["Adriana", "Camila", "Daniela", "Elena", "Fernanda",
                  "Gabriela", "Helena", "Isabela", "Juliana", "Karen",
                  "Larissa", "Marina", "Natalia", "Olga", "Patricia"]


# ═══════════════════════════════════════════════════════════════════════
#  FUNCOES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════

_used_cpfs: set[str] = set()
_used_placas: set[str] = set()
_used_matriculas: set[str] = set()


def rand_cpf() -> str:
    while True:
        cpf = [random.randint(0, 9) for _ in range(9)]
        d1 = sum((10 - i) * cpf[i] for i in range(9)) % 11
        d1 = 0 if d1 < 2 else 11 - d1
        d2 = sum((11 - i) * cpf[i] for i in range(9)) % 11
        d2 = 0 if d2 < 2 else 11 - d2
        cpf.extend([d1, d2])
        s = "".join(str(d) for d in cpf)
        if len(set(cpf)) > 1 and s not in _used_cpfs:
            _used_cpfs.add(s)
            return s


def rand_cnpj() -> str:
    while True:
        c = [random.randint(0, 9) for _ in range(12)]
        p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        p2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        d1 = sum(x * y for x, y in zip(c, p1)) % 11
        d1 = 0 if d1 < 2 else 11 - d1
        c.append(d1)
        d2 = sum(x * y for x, y in zip(c, p2)) % 11
        d2 = 0 if d2 < 2 else 11 - d2
        c.append(d2)
        if len(set(c)) > 1:
            return "".join(str(d) for d in c)


def rand_data(min_ano: int = 1940, max_ano: int = 2024) -> str:
    if min_ano > max_ano:
        min_ano, max_ano = max_ano, min_ano
    min_ano = max(min_ano, 1940)
    max_ano = min(max_ano, 2024)
    if min_ano > max_ano:
        min_ano = max_ano
    ano = random.randint(min_ano, max_ano)
    mes = random.randint(1, 12)
    dia = random.randint(1, 28)
    return f"{dia:02d}/{mes:02d}/{ano}"


def rand_placa() -> str:
    while True:
        l = "".join(random.choices(string.ascii_uppercase, k=3))
        d = str(random.randint(0, 9))
        r = "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
        p = f"{l}{d}{r}"
        if p not in _used_placas:
            _used_placas.add(p)
            return p


def rand_renavan() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(11))


def rand_chassi() -> str:
    chars = string.ascii_uppercase.replace("I", "").replace("O", "").replace("Q", "") + string.digits
    return "".join(random.choices(chars, k=17))


def rand_nome(sexo: str = None) -> str:
    if sexo is None:
        sexo = random.choice(["M", "F"])
    p = random.choice(NOMES_M if sexo == "M" else NOMES_F)
    m = random.choice(SOBRENOMES)
    u = random.choice(SOBRENOMES)
    return f"{p} {m} {u}"


def rand_cidade() -> tuple[str, str]:
    return random.choice(CIDADES)


def rand_endereco() -> dict:
    cid, uf = rand_cidade()
    return {
        "logradouro": f"{random.choice(LOGRADOUROS)} {random.choice(NOMES_RUA)}, {random.randint(10, 5000)}",
        "bairro": random.choice(BAIRROS),
        "cidade": cid,
        "uf": uf,
        "cep": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
    }


def _safe_add(chain, event_type, data) -> bool:
    try:
        chain.add_event(event_type, data)
        return True
    except (ValueError, Exception):
        return False


# ═══════════════════════════════════════════════════════════════════════
#  GERADOR DE PF — 300 PESSOAS COM PERFIS DIVERSOS
# ═══════════════════════════════════════════════════════════════════════

def gerar_pf(num: int = 300) -> dict[str, Blockchain]:
    """Gera 300 PF com perfis diversificados."""
    chains: dict[str, Blockchain] = {}
    progresso = 0

    # Perfis com probabilidades ajustadas
    perfis = [
        ("casado", 0.25),
        ("divorciado", 0.12),
        ("viuvo", 0.06),
        ("solteiro_vacinado", 0.18),
        ("com_protese", 0.08),
        ("solteiro_eventos", 0.15),
        ("casado_filhos", 0.10),
        ("obito", 0.06),
    ]
    perfil_nomes = [p[0] for p in perfis]
    perfil_probs = [p[1] for p in perfis]
    # Normaliza
    total_p = sum(perfil_probs)
    perfil_probs = [p / total_p for p in perfil_probs]

    for i in range(num):
        cpf = rand_cpf()
        sexo = random.choice(["M", "F"])
        nome = rand_nome(sexo)
        cidade, uf = rand_cidade()
        nasc_ano = random.randint(1945, 2005)
        data_nasc = rand_data(nasc_ano, nasc_ano)

        perfil = random.choices(perfil_nomes, perfil_probs)[0]

        chain = Blockchain(difficulty=2)
        kp = generate_authority_keypair("Cartorio Registro Civil")
        chain.set_signer(kp)

        # GÊNESIS
        dados_nasc = EventFactory.nascimento(
            cpf=cpf, nome_completo=nome, data_nascimento=data_nasc,
            sexo=sexo, cidade_nascimento=cidade, uf_nascimento=uf,
            nome_mae=rand_nome("F"),
            nome_pai=rand_nome("M") if random.random() > 0.25 else None,
        )
        chain.create_genesis(dados_nasc)

        # ── VACINAÇÃO ──────────────────────────────────────────────
        if perfil in ("solteiro_vacinado", "casado", "casado_filhos", "solteiro_eventos", "viuvo"):
            nv = random.randint(1, 4)
            for _ in range(nv):
                _safe_add(chain, EventType.VACINACAO.value, EventFactory.vacina(
                    cpf=cpf, nome_vacina=random.choice(NOMES_VACINAS),
                    data_vacinacao=rand_data(max(nasc_ano + 1, 2020), 2024),
                    lote=f"LOTE-{random.randint(1000, 9999)}",
                    fabricante=random.choice(["Pfizer", "AstraZeneca", "CoronaVac", "Fiocruz"]),
                    dose=random.choice(["1a dose", "2a dose", "Reforco"]),
                    unidade_saude=random.choice(["UBS Central", "UBS Jardim", "Hospital Municipal"]),
                    cidade=cidade, uf=uf,
                ))

        # ── PRÓTESE ────────────────────────────────────────────────
        if perfil == "com_protese":
            np_ = random.randint(1, 3)
            for _ in range(np_):
                _safe_add(chain, EventType.PROTESE.value, EventFactory.protese(
                    cpf=cpf, nome_protese=random.choice(PROTESES),
                    data_implantacao=rand_data(max(nasc_ano + 25, 2010), 2024),
                    tipo=random.choice(["Ortopedica", "Cardiaca", "Dental"]),
                    marca_modelo=f"Mod-{random.randint(100, 999)}",
                    medico_responsavel=rand_nome("M"),
                    hospital_clinica=random.choice(HOSPITAIS),
                    cidade=cidade, uf=uf,
                ))

        # ── CASAMENTO ──────────────────────────────────────────────
        casado = False
        if perfil in ("casado", "divorciado", "viuvo", "casado_filhos") and nasc_ano < 2000:
            conjuge_sexo = "F" if sexo == "M" else "M"
            data_cas = rand_data(max(nasc_ano + 18, 2000), 2023)
            ok = _safe_add(chain, EventType.CASAMENTO.value, EventFactory.casamento(
                cpf=cpf, nome_conjuge=rand_nome(conjuge_sexo),
                cpf_conjuge=rand_cpf(), data_casamento=data_cas,
                regime_bens=random.choice(["COMUNHAO_PARCIAL", "SEPARACAO_TOTAL", "COMUNHAO_UNIVERSAL"]),
                cidade=cidade, uf=uf,
            ))
            casado = ok

        # ── DIVÓRCIO ───────────────────────────────────────────────
        if perfil == "divorciado" and casado:
            _safe_add(chain, EventType.DIVORCIO.value, EventFactory.divorcio(
                cpf=cpf, data_divorcio=rand_data(2020, 2024),
                tipo=random.choice(["CONSENSUAL", "JUDICIAL"]),
                guarda_filhos=random.choice([None, "COMPARTILHADA", "MATERNA", "PATerna"]),
                pensao_alimenticia=random.choice([True, False]),
            ))

        # ── ÓBITO ──────────────────────────────────────────────────
        if perfil in ("viuvo", "obito"):
            _safe_add(chain, EventType.OBITO.value, EventFactory.obito(
                cpf=cpf, data_obito=rand_data(2022, 2024),
                cidade_obito=cidade, uf_obito=uf,
                causa_morte=random.choice(["Causas naturais", "Doença cardíaca", "Acidente vascular", "Neoplasia", None]),
            ))

        # ── ALTERAÇÃO DE NOME ──────────────────────────────────────
        if perfil in ("solteiro_eventos", "casado_filhos") and random.random() < 0.3:
            _safe_add(chain, EventType.ALTERACAO_NOME.value, EventFactory.alteracao_nome(
                cpf=cpf, nome_anterior=nome,
                nome_novo=nome.split()[0] + " " + random.choice(SOBRENOMES),
                data_alteracao=rand_data(2020, 2024),
                motivo=random.choice(["Casamento", "Divorcio", "Retificacao judicial"]),
            ))

        # ── EVENTOS EXTRAS (permuta, adoção) ───────────────────────
        if perfil == "casado_filhos" and random.random() < 0.2:
            _safe_add(chain, EventType.ADOCAO.value, EventFactory.adocao(
                cpf=cpf, nome_adotivo=None,
                data_adocao=rand_data(2015, 2024),
                nome_mae_adotiva=rand_nome("F"),
                nome_pai_adotivo=rand_nome("M") if random.random() > 0.3 else None,
                mantem_nome_biologico=random.choice([True, False]),
            ))

        chains[cpf] = chain
        progresso += 1
        if progresso % 50 == 0:
            print(f"    PF: {progresso}/{num} geradas...")

    print(f"  [OK] {len(chains)} cadeias PF geradas.")
    return chains


# ═══════════════════════════════════════════════════════════════════════
#  GERADOR DE IM — 300 IMOVEIS COM SITUACOES DIVERSAS
# ═══════════════════════════════════════════════════════════════════════

def gerar_im(pf_cpfs: list[str], num: int = 300) -> dict[str, PropertyChain]:
    """Gera 300 IM com situações diversificadas."""
    chains: dict[str, PropertyChain] = {}
    progresso = 0

    perfis = [
        ("residencia_simples", 0.20),
        ("com_construcao", 0.15),
        ("compra_venda", 0.12),
        ("doacao", 0.06),
        ("heranca", 0.06),
        ("garantia_hipoteca", 0.10),
        ("leilao", 0.05),
        ("confisco", 0.03),
        ("penhora", 0.03),
        ("desmembramento", 0.04),
        ("reforma", 0.08),
        ("multas_iptu", 0.05),
        ("certidoes", 0.03),
    ]
    nomes_perfis = [p[0] for p in perfis]
    probs_perfis = [p[1] for p in perfis]
    total_p = sum(probs_perfis)
    probs_perfis = [p / total_p for p in probs_perfis]

    for i in range(num):
        while True:
            mat = f"{random.randint(100000, 999999)}-{random.randint(1, 9)}"
            if mat not in _used_matriculas:
                _used_matriculas.add(mat)
                break

        cid, uf = rand_cidade()
        bairro = random.choice(BAIRROS)
        tipo_log = random.choice(LOGRADOUROS)
        nome_rua = random.choice(NOMES_RUA)
        numero = random.randint(10, 5000)
        area_terreno = round(random.uniform(100, 2000), 2)
        cpf_prop = random.choice(pf_cpfs) if pf_cpfs else rand_cpf()
        nome_prop = rand_nome()

        perfil = random.choices(nomes_perfis, probs_perfis)[0]

        chain = PropertyChain(difficulty=2)
        kp = generate_authority_keypair("Cartorio de Imoveis")
        chain.set_signer(kp)

        # GÊNESIS — Terreno
        dados_terreno = PropertyEventFactory.terreno(
            matricula=mat,
            endereco_logradouro=f"{tipo_log} {nome_rua}, {numero}",
            endereco_bairro=bairro, endereco_cidade=cid, endereco_uf=uf,
            endereco_cep=f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
            lat=round(random.uniform(-33.0, 5.0), 6),
            lon=round(random.uniform(-74.0, -35.0), 6),
            area_terreno_m2=area_terreno,
            metragem_frente=round(random.uniform(5, 30), 2),
            metragem_fundo=round(random.uniform(5, 30), 2),
            metragem_lado_esq=round(random.uniform(5, 20), 2),
            metragem_lado_dir=round(random.uniform(5, 20), 2),
            zoneamento=random.choice(["ZER-1", "ZER-2", "ZER-3", "ZC-1", "ZI-1", "ZM-1"]),
            uso_permitido=random.choice([["RESIDENCIAL"], ["COMERCIAL"], ["MISTO"], ["INDUSTRIAL"]]),
            altura_maxima=random.choice([10, 15, 20, 25, 30]),
            taxa_ocupacao=round(random.uniform(0.3, 0.8), 2),
            cacau_permitido=round(random.uniform(1.0, 4.0), 2),
            codigo_iptu=f"IPTU-{random.randint(100000, 999999)}",
            proprietarios=[{
                "cpf": cpf_prop, "nome": nome_prop,
                "participacao": 100.0, "origem": "CADASTRO",
            }],
        )
        chain.create_genesis(dados_terreno)

        # ── CONSTRUÇÃO ─────────────────────────────────────────────
        if perfil in ("com_construcao", "reforma", "residencia_simples"):
            area_constr = round(random.uniform(40, min(area_terreno * 0.7, 500)), 2)
            _safe_add(chain, PropertyEventType.CONSTRUCAO.value, PropertyEventFactory.construcao(
                matricula=mat,
                descricao=f"Residencia de {area_constr:.0f}m2",
                area_construida_m2=area_constr,
                tipo_construcao=random.choice(["RESIDENCIAL", "COMERCIAL", "MISTO"]),
                pavimentos=random.choice([1, 2, 3]),
                data_inicio=rand_data(2015, 2022),
                data_fim=rand_data(2022, 2024),
                responsavel_tecnico=rand_nome("M"),
            ))

        # ── REFORMA ────────────────────────────────────────────────
        if perfil == "reforma" and random.random() < 0.6:
            _safe_add(chain, PropertyEventType.REFORMA.value, PropertyEventFactory.reforma(
                matricula=mat, descricao="Ampliacao da area construida",
                tipo="AMPLIACAO",
                area_anterior_m2=round(random.uniform(50, 200), 2),
                area_nova_m2=round(random.uniform(100, 350), 2),
                data_inicio=rand_data(2023, 2024),
                responsavel_tecnico=rand_nome("M"),
            ))

        # ── COMPRA/VENDA ───────────────────────────────────────────
        if perfil == "compra_venda":
            _safe_add(chain, PropertyEventType.COMPRA_VENDA.value, PropertyEventFactory.compra_venda(
                matricula=mat,
                comprador_cpf=rand_cpf(), comprador_nome=rand_nome(),
                vendedor_cpf=cpf_prop, vendedor_nome=nome_prop,
                valor_transacao=round(random.uniform(150000, 2000000), 2),
                data_transacao=rand_data(2020, 2024),
                escritura_numero=f"ESC-{random.randint(10000, 99999)}",
                cartorio=random.choice(["CRI Centro", "CRI Jardins", "CRI Vila Mariana"]),
            ))
        elif perfil == "residencia_simples" and random.random() < 0.2:
            _safe_add(chain, PropertyEventType.COMPRA_VENDA.value, PropertyEventFactory.compra_venda(
                matricula=mat,
                comprador_cpf=rand_cpf(), comprador_nome=rand_nome(),
                vendedor_cpf=cpf_prop, vendedor_nome=nome_prop,
                valor_transacao=round(random.uniform(200000, 1500000), 2),
                data_transacao=rand_data(2021, 2024),
            ))

        # ── DOAÇÃO ─────────────────────────────────────────────────
        if perfil == "doacao":
            _safe_add(chain, PropertyEventType.DOACAO.value, PropertyEventFactory.doacao(
                matricula=mat,
                donatario_cpf=rand_cpf(), donatario_nome=rand_nome(),
                doador_cpf=cpf_prop, doador_nome=nome_prop,
                data_doacao=rand_data(2022, 2024),
                motivo=random.choice(["Presente familiar", "Doacao filantropica", "_transferencia"]),
            ))

        # ── HERANÇA ────────────────────────────────────────────────
        if perfil == "heranca":
            nh = random.randint(2, 4)
            herdeiros = []
            for _ in range(nh):
                herdeiros.append({
                    "cpf": rand_cpf(), "nome": rand_nome(),
                    "participacao": round(100.0 / nh, 1),
                })
            _safe_add(chain, PropertyEventType.HERANCA.value, PropertyEventFactory.heranca(
                matricula=mat,
                inventariado_cpf=cpf_prop, inventariado_nome=nome_prop,
                herdeiros=herdeiros,
                data_obito=rand_data(2020, 2023),
                data_inventario=rand_data(2023, 2024),
                inventario_tipo=random.choice(["JUDICIAL", "EXTRAJUDICIAL"]),
            ))

        # ── GARANTIA / HIPOTECA ────────────────────────────────────
        if perfil in ("garantia_hipoteca", "leilao"):
            idx_gar = None
            dados_gar = PropertyEventFactory.garantia(
                matricula=mat,
                credor_nome=random.choice(["Banco do Brasil", "Itau", "Bradesco", "Caixa", "Santander"]),
                credor_cnpj=rand_cnpj(),
                valor_garantia=round(random.uniform(50000, 800000), 2),
                data_garantia=rand_data(2020, 2023),
                data_vencimento=rand_data(2025, 2035),
                tipo_garantia=random.choice(["HIPOTECARIA", "ALIENACAO_FIDUCIARIA", "PENHOR"]),
                taxa_juros=round(random.uniform(8, 15), 2),
                prazo_meses=random.choice([120, 180, 240, 360]),
            )
            _safe_add(chain, PropertyEventType.GARANTIA.value, dados_gar)

        # ── LEILÃO ─────────────────────────────────────────────────
        if perfil == "leilao":
            _safe_add(chain, PropertyEventType.LEILAO.value, PropertyEventFactory.leilao(
                matricula=mat,
                data_leilao=rand_data(2024, 2024),
                valor_minimo=round(random.uniform(100000, 500000), 2),
                lance_vencedor=round(random.uniform(120000, 600000), 2),
                vencedor_cpf=rand_cpf(), vencedor_nome=rand_nome(),
                leiloeiro=random.choice(["Leiloeira XYZ", "Leiloeira Brasil", "Leiloeira Oficial"]),
                tipo=random.choice(["JUDICIAL", "EXTRAJUDICIAL"]),
            ))

        # ── CONFISCO ───────────────────────────────────────────────
        if perfil == "confisco":
            _safe_add(chain, PropertyEventType.CONFISCO.value, PropertyEventFactory.confisco(
                matricula=mat,
                autoridade=random.choice(["Juiz Federal", "Juiz Estadual", "Ministerio Publico"]),
                processo_numero=f"000{random.randint(100000, 999999)}-00.2024.8.26.0100",
                data_confisco=rand_data(2023, 2024),
                motivo=random.choice(["Sonegacao fiscal", "Crimes financeiros", "Execucao fiscal"]),
            ))

        # ── PENHORA ────────────────────────────────────────────────
        if perfil == "penhora":
            _safe_add(chain, PropertyEventType.PENHORA.value, PropertyEventFactory.penhora(
                matricula=mat,
                autoridade=random.choice(["Justica Federal", "Justica Estadual"]),
                processo_numero=f"000{random.randint(100000, 999999)}-00.2024.8.26.0100",
                data_penhora=rand_data(2023, 2024),
                valor_penhorado=round(random.uniform(50000, 500000), 2),
            ))

        # ── DESMEMBRAMENTO ─────────────────────────────────────────
        if perfil == "desmembramento" and area_terreno > 500:
            nl = random.randint(2, 4)
            novas = []
            area_rest = area_terreno
            for j in range(nl - 1):
                a = round(random.uniform(area_terreno / nl * 0.5, area_terreno / nl * 1.5), 2)
                a = min(a, area_rest - (nl - j - 1) * 50)
                novas.append({"matricula": f"{random.randint(100000, 999999)}-{random.randint(1, 9)}", "area_m2": a})
                area_rest -= a
            novas.append({"matricula": f"{random.randint(100000, 999999)}-{random.randint(1, 9)}", "area_m2": round(area_rest, 2)})
            _safe_add(chain, PropertyEventType.DESMEMBRAMENTO.value, PropertyEventFactory.desmembramento(
                matricula_origem=mat, novas_matriculas=novas,
                area_total_anterior=area_terreno,
                descricao=f"Divisao em {nl} lotes",
            ))

        # ── CERTIDÕES ──────────────────────────────────────────────
        if perfil == "certidoes" or random.random() < 0.15:
            nc = random.randint(1, 3)
            for _ in range(nc):
                _safe_add(chain, PropertyEventType.CERTIDAO.value, PropertyEventFactory.certidao(
                    matricula=mat,
                    tipo_certidao=random.choice(["NEGATIVA", "POSITIVA", "SITUACAO_FISCAL", "ONUS_REAIS"]),
                    data_emissao=rand_data(2023, 2024),
                    numero=f"CERT-{random.randint(10000, 99999)}",
                    orgao_emissor=random.choice(["Cartorio", "Receita Federal", "Poder Judicial"]),
                ))

        # ── IPTU ───────────────────────────────────────────────────
        if perfil == "multas_iptu" or random.random() < 0.1:
            _safe_add(chain, PropertyEventType.IPTU.value, PropertyEventFactory.iptu(
                matricula=mat,
                codigo_iptu=f"IPTU-{random.randint(100000, 999999)}",
                data_atualizacao=rand_data(2024, 2024),
                valor_anterior=round(random.uniform(500, 3000), 2),
                valor_novo=round(random.uniform(600, 4000), 2),
            ))

        # ── ZONEAMENTO ─────────────────────────────────────────────
        if random.random() < 0.08:
            _safe_add(chain, PropertyEventType.ZONEAMENTO.value, PropertyEventFactory.zoneamento(
                matricula=mat,
                zoneamento_anterior=random.choice(["ZER-1", "ZER-2", "ZC-1"]),
                zoneamento_novo=random.choice(["ZER-2", "ZC-1", "ZM-1"]),
                data=rand_data(2024, 2024),
            ))

        chains[mat] = chain
        progresso += 1
        if progresso % 50 == 0:
            print(f"    IM: {progresso}/{num} gerados...")

    print(f"  [OK] {len(chains)} cadeias IM geradas.")
    return chains


# ═══════════════════════════════════════════════════════════════════════
#  GERADOR DE MO — 300 VEICULOS COM SITUACOES DIVERSAS
# ═══════════════════════════════════════════════════════════════════════

def gerar_mo(pf_cpfs: list[str], num: int = 300) -> dict[str, VehicleChain]:
    """Gera 300 MO com situações diversificadas."""
    chains: dict[str, VehicleChain] = {}
    progresso = 0

    perfis = [
        ("novo_sem_eventos", 0.10),
        ("com_venda", 0.15),
        ("com_multas", 0.10),
        ("com_sinistro", 0.10),
        ("sinistro_perda_total", 0.05),
        ("com_troca_peca", 0.10),
        ("com_garantia", 0.06),
        ("com_recall", 0.08),
        ("leilao", 0.04),
        ("confisco", 0.03),
        ("baixa", 0.03),
        ("revisao_frequente", 0.08),
        ("com_licenciamento", 0.05),
        ("mudanca_cor", 0.03),
    ]
    nomes_perfis = [p[0] for p in perfis]
    probs_perfis = [p[1] for p in perfis]
    total_p = sum(probs_perfis)
    probs_perfis = [p / total_p for p in probs_perfis]

    for i in range(num):
        placa = rand_placa()
        marca, modelo = random.choice(MARCAS_VEICULOS)
        cor = random.choice(CORES_VEICULOS)
        combustivel = random.choice(COMBUSTIVEIS)
        fab_nome, fab_cnpj = random.choice(FABRICANTES)
        ano = random.randint(2015, 2024)

        perfil = random.choices(nomes_perfis, probs_perfis)[0]
        cpf_prop = random.choice(pf_cpfs) if pf_cpfs else rand_cpf()

        chain = VehicleChain(difficulty=2)
        kp = generate_authority_keypair("DETRAN")
        chain.set_signer(kp)

        # GÊNESIS — Fabricação
        dados_fab = VehicleEventFactory.fabricacao(
            placa=placa, renavan=rand_renavan(), chassis=rand_chassi(),
            marca=marca, modelo=modelo,
            ano_fabricacao=ano, ano_modelo=ano + random.choice([0, 0, 0, 1]),
            cor=cor, combustivel=combustivel,
            cilindradas=random.choice([1000, 1000, 1600, 2000]),
            potencia_cv=round(random.uniform(75, 250), 0),
            tipo_veiculo="AUTOMOVEL", categoria="PARTICULAR",
            num_portas=random.choice([4, 4, 4, 2]),
            capacidade_passageiros=5,
            fabricante_cnpj=fab_cnpj, fabricante_nome=fab_nome,
            motor_tipo=f"{random.choice([1.0, 1.6, 2.0])} MPI",
            motor_numero=f"MOT-{random.randint(10000, 99999)}",
            freio_dianteiro=random.choice(["DISCO", "DISCO VENTILADO"]),
            freio_traseiro=random.choice(["TAMBOR", "DISCO"]),
            direcao=random.choice(["HIDRAULICA", "ELETROHIDRAULICA", "ELETRICA"]),
            transmissao=random.choice(["MANUAL 5 MARCHAS", "AUTOMATICO CVT", "AUTOMATICO 6 MARCHAS"]),
            lote_fabricacao=f"LOTE-{ano}-{random.randint(100, 999)}",
            data_fabricacao=rand_data(ano, ano + 1),
            crv=f"CRV-{ano}-{random.randint(10000, 99999)}",
            odometro_km=0.0,
        )
        chain.create_genesis(dados_fab)

        # ── COMPRA/VENDA ───────────────────────────────────────────
        if perfil in ("com_venda", "com_multas", "com_sinistro", "com_troca_peca",
                       "com_garantia", "com_recall", "revisao_frequente", "com_licenciamento",
                       "mudanca_cor", "leilao", "sinistro_perda_total"):
            _safe_add(chain, VehicleEventType.COMPRA_VENDA.value, VehicleEventFactory.compra_venda(
                placa=placa,
                comprador_cpf=cpf_prop, comprador_nome=rand_nome(),
                vendedor_cpf=rand_cpf(), vendedor_nome=f"Concessionaria {marca}",
                valor_transacao=round(random.uniform(40000, 200000), 2),
                data_transacao=rand_data(ano, ano + 1),
                odometro_km=round(random.uniform(0, 500), 0),
                notafiscal_numero=f"NF-{random.randint(100000, 999999)}",
            ))
        elif perfil == "novo_sem_eventos" and random.random() < 0.3:
            _safe_add(chain, VehicleEventType.COMPRA_VENDA.value, VehicleEventFactory.compra_venda(
                placa=placa,
                comprador_cpf=cpf_prop, comprador_nome=rand_nome(),
                vendedor_cpf=rand_cpf(), vendedor_nome=f"Concessionaria {marca}",
                valor_transacao=round(random.uniform(50000, 180000), 2),
                data_transacao=rand_data(ano, ano + 1),
                odometro_km=round(random.uniform(0, 100), 0),
            ))

        # ── MULTAS ─────────────────────────────────────────────────
        if perfil == "com_multas":
            nm = random.randint(2, 5)
            for _ in range(nm):
                enq = random.choice(ENQUADRAMENTOS)
                cid_uf = rand_cidade()
                _safe_add(chain, VehicleEventType.MULTA.value, VehicleEventFactory.multa(
                    placa=placa,
                    numero_auto=f"AUTO-{ano}-{random.randint(10000, 99999)}",
                    data_infracao=rand_data(max(ano, 2022), 2024),
                    local_logradouro=f"{random.choice(LOGRADOUROS)} {random.choice(NOMES_RUA)}",
                    local_cidade=cid_uf[0], local_uf=cid_uf[1],
                    enquadramento=enq[0], pontos=enq[2], valor_multa=enq[3],
                    orgao_autuador=random.choice(ORGAOS_TRANSITO),
                    condutor_cpf=cpf_prop, condutor_nome=rand_nome(),
                ))

        # ── SINISTRO ───────────────────────────────────────────────
        if perfil == "com_sinistro":
            _safe_add(chain, VehicleEventType.SINISTRO.value, VehicleEventFactory.sinistro(
                placa=placa,
                data_sinistro=rand_data(max(ano, 2022), 2024),
                tipo=random.choice(TIPOS_SINISTRO),
                bo_numero=f"BO-{ano}-{random.randint(10000, 99999)}",
                delegacia=random.choice(["1a DP Centro", "2a DP Jardins", "3a DP Vila Mariana"]),
                seguradora_nome=random.choice(["Porto Seguro", "Bradesco Seguros", "SulAmerica", "Allianz"]),
                seguradora_cnpj=rand_cnpj(),
                seguradora_apolice=f"AP-{random.randint(100000, 999999)}",
                valor_dano=round(random.uniform(2000, 35000), 2),
                pecas_danificadas=random.sample(
                    ["Para-choque", "Farol", "Capo", "Porta", "Para-lama", "Retrovisor", "Parabrisa"],
                    k=random.randint(1, 4),
                ),
            ))

        # ── SINISTRO PERDA TOTAL ───────────────────────────────────
        if perfil == "sinistro_perda_total":
            _safe_add(chain, VehicleEventType.SINISTRO_PERDA_TOTAL.value, VehicleEventFactory.sinistro_perda_total(
                placa=placa,
                data_sinistro=rand_data(max(ano, 2022), 2024),
                tipo=random.choice(["INCENDIO", "ALAGAMENTO", "COLISAO", "FURTO_ROUBO"]),
                bo_numero=f"BO-{ano}-{random.randint(10000, 99999)}",
                seguradora_nome=random.choice(["Porto Seguro", "Bradesco Seguros", "SulAmerica"]),
                valor_indenizacao=round(random.uniform(30000, 180000), 2),
                destino=random.choice(["DESLICHE", "FERRO_VELHO", "DESTRUIDO", "RECICLAGEM"]),
                data_baixa_detran=rand_data(2024, 2024),
            ))

        # ── TROCA DE PEÇA ──────────────────────────────────────────
        if perfil == "com_troca_peca":
            np_ = random.randint(1, 3)
            for _ in range(np_):
                _safe_add(chain, VehicleEventType.TROCA_PECA.value, VehicleEventFactory.troca_peca(
                    placa=placa,
                    peca_nome=random.choice(["Motor", "Cambio", "Alternador", "Compressor de Ar", "Direcao Eletrica", "Injetor", "Radiador"]),
                    peca_numero_serie=f"PS-{random.randint(100000, 999999)}",
                    peca_fabricante=marca,
                    peca_origem=random.choice(["ORIGINAL", "GENUINA", "REMANUFACTURADA"]),
                    data_troca=rand_data(max(ano, 2022), 2024),
                    oficina_responsavel=random.choice(OFICINAS),
                    mecanico_cpf=rand_cpf(),
                    motivo=random.choice(["Manutencao preventiva", "Avaria", "Desgaste", "Recall"]),
                    odometro_km=round(random.uniform(10000, 120000), 0),
                ))
            # Validação de peça
            if random.random() < 0.5:
                _safe_add(chain, VehicleEventType.VALIDACAO_PECA.value, VehicleEventFactory.validacao_peca(
                    placa=placa,
                    peca_nome=random.choice(["Motor", "Cambio"]),
                    peca_numero_serie=f"PS-{random.randint(100000, 999999)}",
                    validador_cpf=rand_cpf(), validador_nome=rand_nome(),
                    data_validacao=rand_data(2024, 2024),
                    resultado=random.choice(["AUTENTICADA", "FALSIFICADA"]),
                    metodo_validacao="Analise documental + fisica",
                ))

        # ── GARANTIA / EMPRÉSTIMO ──────────────────────────────────
        if perfil == "com_garantia":
            _safe_add(chain, VehicleEventType.GARANTIA_EMPRESTIMO.value, VehicleEventFactory.garantia_emprestimo(
                placa=placa,
                credor_nome=random.choice(["Banco do Brasil", "Itau", "Bradesco", "Caixa", "Santander"]),
                credor_cnpj=rand_cnpj(),
                valor_emprestimo=round(random.uniform(10000, 80000), 2),
                data_garantia=rand_data(2023, 2024),
                data_vencimento=rand_data(2025, 2028),
                taxa_juros=round(random.uniform(1.5, 4.0), 2),
                parcelas=random.choice([12, 24, 36, 48]),
                tipo_garantia=random.choice(["ALIENACAO_FIDUCIARIA", "PENHOR"]),
            ))
            # 40% quitam
            if random.random() < 0.4:
                _safe_add(chain, VehicleEventType.QUITACAO_GARANTIA.value, VehicleEventFactory.quitacao_garantia(
                    placa=placa, garantia_index=0,
                    data_quitacao=rand_data(2024, 2024),
                    valor_pago=round(random.uniform(10000, 80000), 2),
                ))

        # ── RECALL ─────────────────────────────────────────────────
        if perfil == "com_recall":
            nr = random.randint(1, 2)
            for _ in range(nr):
                _safe_add(chain, VehicleEventType.RECALL_DE_FABRICA.value, VehicleEventFactory.recall_fabrica(
                    placa=placa,
                    data_notificacao=rand_data(max(ano, 2023), 2024),
                    fabricante_nome=fab_nome, fabricante_cnpj=fab_cnpj,
                    numero_recall=f"RC-{ano}-{random.randint(100, 999)}",
                    peca_defeituosa=random.choice(["Airbag", "Cinto de seguranca", "Direcao", "Freios", "Motor", "Cambio"]),
                    descricao_defeito=random.choice([
                        "Possivel falha no mecanismo de acionamento",
                        "Desgaste prematuro do componente",
                        "Risco de curto-circuito no modulo eletronico",
                        "Vazamento de fluido hidraulico",
                        "Falha no sensor de colisao",
                    ]),
                    risco=random.choice(["BAIXO", "MEDIO", "ALTO", "CRITICO"]),
                    solucao=random.choice(["Reposicao da peca", "Atualizacao de software", "Reparo gratuito"]),
                    oficina_autorizada=f"Oficina Autorizada {marca}",
                    prazo_conclusao=rand_data(2024, 2025),
                    custo_para_proprietario=0.0,
                ))

        # ── LEILÃO ─────────────────────────────────────────────────
        if perfil == "leilao":
            _safe_add(chain, VehicleEventType.LEILAO.value, VehicleEventFactory.leilao(
                placa=placa,
                data_leilao=rand_data(2024, 2024),
                valor_minimo=round(random.uniform(15000, 80000), 2),
                lance_vencedor=round(random.uniform(18000, 90000), 2),
                vencedor_cpf=rand_cpf(), vencedor_nome=rand_nome(),
                leiloeiro=random.choice(["Leiloeira XYZ", "Leiloeira Brasil"]),
                tipo=random.choice(["JUDICIAL", "EXTRAJUDICIAL"]),
            ))

        # ── CONFISCO ───────────────────────────────────────────────
        if perfil == "confisco":
            _safe_add(chain, VehicleEventType.CONFISCO.value, VehicleEventFactory.confisco(
                placa=placa,
                autoridade=random.choice(["Juiz Federal", "Delegado de Policia"]),
                processo_numero=f"000{random.randint(100000, 999999)}-00.2024.8.26.0100",
                data_confisco=rand_data(2023, 2024),
                motivo=random.choice(["Trafico de drogas", "Sonegacao fiscal", "Furto"]),
            ))

        # ── BAIXA ──────────────────────────────────────────────────
        if perfil == "baixa":
            _safe_add(chain, VehicleEventType.BAIXA.value, VehicleEventFactory.baixa(
                placa=placa,
                data_baixa=rand_data(2024, 2024),
                motivo=random.choice(["PERDA_TOTAL", "FURTO_NAO_RECUPERADO", "DESMANCHE", "SUCATA"]),
            ))

        # ── REVISÃO ────────────────────────────────────────────────
        if perfil in ("revisao_frequente", "com_troca_peca"):
            nr = random.randint(2, 4)
            for j in range(nr):
                _safe_add(chain, VehicleEventType.REVISAO.value, VehicleEventFactory.revisao(
                    placa=placa,
                    data_revisao=rand_data(max(ano + j, 2022), 2024),
                    oficina_responsavel=random.choice(OFICINAS),
                    tipo_revisao=random.choice(["PREVENTIVA", "CORRETIVA"]),
                    itens_revisados=random.sample(
                        ["Oleo", "Filtros", "Freios", "Pneus", "Suspensao", "Eletrica", "Arrefecimento"],
                        k=random.randint(2, 5),
                    ),
                    pecas_substituidas=random.sample(
                        ["Oleo do motor", "Filtro de oleo", "Filtro de ar", "Pastilha de freio"],
                        k=random.randint(1, 3),
                    ),
                    odometro_km=round(random.uniform(5000 + j * 10000, 50000 + j * 10000), 0),
                    proxima_revisao_km=round(random.uniform(10000, 100000), 0),
                    valor_total=round(random.uniform(200, 3000), 2),
                ))

        # ── LICENCIAMENTO ──────────────────────────────────────────
        if perfil in ("com_licenciamento", "revisao_frequente") or random.random() < 0.15:
            _safe_add(chain, VehicleEventType.LICENCIAMENTO.value, VehicleEventFactory.licenciamento(
                placa=placa,
                ano_licenciamento=2024,
                data_licenciamento=rand_data(2024, 2024),
                ipva_pago=random.choice([True, True, True, False]),
                valor_ipva=round(random.uniform(500, 4000), 2),
            ))

        # ── MUDANÇA DE COR ─────────────────────────────────────────
        if perfil == "mudanca_cor":
            _safe_add(chain, VehicleEventType.MUDANCA_COR.value, VehicleEventFactory.mudanca_cor(
                placa=placa,
                cor_anterior=cor,
                cor_nova=random.choice([c for c in CORES_VEICULOS if c != cor]),
                data_mudanca=rand_data(2024, 2024),
            ))

        # ── TRANSFERÊNCIA DETRAN ───────────────────────────────────
        if random.random() < 0.08:
            _safe_add(chain, VehicleEventType.TRANSFERENCIA_PROPRIEDADE.value, VehicleEventFactory.transferencia_propriedade(
                placa=placa,
                novo_proprietario_cpf=rand_cpf(),
                novo_proprietario_nome=rand_nome(),
                data_transferencia=rand_data(2023, 2024),
            ))

        chains[placa] = chain
        progresso += 1
        if progresso % 50 == 0:
            print(f"    MO: {progresso}/{num} gerados...")

    print(f"  [OK] {len(chains)} cadeias MO geradas.")
    return chains


# ═══════════════════════════════════════════════════════════════════════
#  RELATÓRIO
# ═══════════════════════════════════════════════════════════════════════

def relatorio(pf: dict, im: dict, mo: dict) -> str:
    linhas = []
    linhas.append("=" * 70)
    linhas.append("  RELATORIO — GERACAO DE DADOS ALEATORIOS")
    linhas.append("=" * 70)

    # Contadores de eventos PF
    pf_eventos: dict[str, int] = {}
    for chain in pf.values():
        for b in chain.chain[1:]:
            evt = b.data.get("evento_tipo", "?")
            pf_eventos[evt] = pf_eventos.get(evt, 0) + 1

    linhas.append(f"\n  PESSOAS FISICAS: {len(pf)}")
    linhas.append(f"  {'─' * 60}")
    linhas.append(f"  Eventos gerados:")
    for evt, cnt in sorted(pf_eventos.items(), key=lambda x: -x[1]):
        linhas.append(f"    {evt:30s} {cnt:4d}")

    # Contadores de eventos IM
    im_eventos: dict[str, int] = {}
    for chain in im.values():
        for b in chain.chain[1:]:
            evt = b.data.get("evento_tipo", "?")
            im_eventos[evt] = im_eventos.get(evt, 0) + 1

    linhas.append(f"\n  IMOVEIS: {len(im)}")
    linhas.append(f"  {'─' * 60}")
    linhas.append(f"  Eventos gerados:")
    for evt, cnt in sorted(im_eventos.items(), key=lambda x: -x[1]):
        linhas.append(f"    {evt:30s} {cnt:4d}")

    # Contadores de eventos MO
    mo_eventos: dict[str, int] = {}
    for chain in mo.values():
        for b in chain.chain[1:]:
            evt = b.data.get("evento_tipo", "?")
            mo_eventos[evt] = mo_eventos.get(evt, 0) + 1

    linhas.append(f"\n  VEICULOS: {len(mo)}")
    linhas.append(f"  {'─' * 60}")
    linhas.append(f"  Eventos gerados:")
    for evt, cnt in sorted(mo_eventos.items(), key=lambda x: -x[1]):
        linhas.append(f"    {evt:30s} {cnt:4d}")

    # Totais
    total_blocos = sum(len(c) for c in pf.values()) + \
                   sum(len(c) for c in im.values()) + \
                   sum(len(c) for c in mo.values())
    linhas.append(f"\n  {'═' * 60}")
    linhas.append(f"  TOTAL: {len(pf)} PF + {len(im)} IM + {len(mo)} MO = {total_blocos} bloco(s)")
    linhas.append(f"  {'═' * 60}")

    return "\n".join(linhas)


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("\nGerando 300 PF + 300 IM + 300 MO com perfis diversificados...\n")

    t0 = time.time()

    pf = gerar_pf(300)
    pf_cpfs = list(pf.keys())

    im = gerar_im(pf_cpfs, 300)
    mo = gerar_mo(pf_cpfs, 300)

    elapsed = time.time() - t0
    print(f"\n  Tempo total: {elapsed:.1f}s\n")
    print(relatorio(pf, im, mo))

    # Salva
    os.makedirs("demo_output", exist_ok=True)

    print("\n  Salvando PF...")
    for cpf, chain in pf.items():
        chain.save_to_file(f"demo_output/pf_{cpf}.json")

    print("  Salvando IM...")
    for mat, chain in im.items():
        chain.save_to_file(f"demo_output/im_{mat.replace('/', '_')}.json")

    print("  Salvando MO...")
    for placa, chain in mo.items():
        chain.save_to_file(f"demo_output/mo_{placa}.json")

    print(f"\n  Arquivos salvos em demo_output/")
    print(f"  Total: {len(os.listdir('demo_output'))} arquivos JSON\n")


if __name__ == "__main__":
    main()
