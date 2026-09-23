#!/usr/bin/env python3
"""
generate_300_new.py — Gera 300 registros em cada blockchain nova:
  CO (Empresas), EM (Embarcacoes), AC (Aeronaves), AN (Animais)

Uso:  PYTHONIOENCODING=utf-8 python generate_300_new.py
"""

import sys
import os
import random
import time
import json
import string
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blockchain_pf import generate_authority_keypair
from blockchain_pf.database import Database
from blockchain_pf.geografia_br import capital_da_uf
from blockchain_co import CompanyChain, CompanyEventFactory, CompanyEventType
from blockchain_em import VesselChain, VesselEventFactory, VesselEventType
from blockchain_ac import AircraftChain, AircraftEventFactory, AircraftEventType
from blockchain_an import AnimalChain, AnimalEventFactory, AnimalEventType

# ── Configuracoes ─────────────────────────────────────────────────────

NUM = 300
DIFFICULTY = 1
random.seed(42)

# ── Helpers ───────────────────────────────────────────────────────────

_NOMES_M = [
    "Joao", "Pedro", "Lucas", "Matheus", "Gabriel", "Rafael", "Bruno", "Felipe",
    "Gustavo", "Leonardo", "Tiago", "Andre", "Carlos", "Antonio", "Paulo",
    "Marcos", "Roberto", "Fernando", "Sergio", "Eduardo", "Ricardo", "Diego",
    "Vitor", "Thiago", "Daniel", "Marcelo", "Henrique", "Renato", "Rodrigo", "Caio",
]
_NOMES_F = [
    "Maria", "Ana", "Juliana", "Fernanda", "Patricia", "Camila", "Amanda",
    "Bruna", "Letícia", "Carla", "Vanessa", "Renata", "Adriana", "Claudia",
    "Daniela", "Luciana", "Mariana", "Priscila", "Raquel", "Tatiana",
    "Isabela", "Larissa", "Natalia", "Paula", "Simone", "Sonia", "Valeria",
    "Viviane", "Bianca", "Cristiane", "Debora", "Eliane", "Fernanda", "Helena",
]
_SOBRANOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves",
    "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho",
    "Almeida", "Lopes", "Soares", "Fernandes", "Vieira", "Barbosa",
    "Rocha", "Dias", "Nascimento", "Andrade", "Moreira", "Nunes", "Marques",
]
_UFS = ["SP", "RJ", "MG", "BA", "RS", "PR", "SC", "PE", "CE", "GO", "DF", "ES"]
_CIDES = ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Porto Alegre",
          "Salvador", "Recife", "Fortaleza", "Brasilia", "Manaus", "Goiania", "Vitoria"]
_RUAS = ["Rua das Flores", "Av. Brasil", "Rua Augusta", "Av. Paulista", "Rua Oscar Freire",
         "Av. Reboucas", "Rua Haddock Lobo", "Av. Faria Lima", "Rua da Consolacao"]
_BAIRROS = ["Centro", "Jardins", "Vila Mariana", "Moema", "Pinheiros", "Itaim Bibi"]

_EMPRESAS_TIPOS = ["TECNOLOGIA", "COMERCIO", "SERVICOS", "INDUSTRIA", "ALIMENTACAO",
                   "SAUDE", "EDUCACAO", "CONSTRUCAO", "TRANSPORTE", "AGRICULTURA"]
_RAZAO_SUFIXOS = ["LTDA", "EIRELI", "ME", "EPP", "SA", "SLU"]
_ATIVIDADES = ["6201501", "4711301", "5611203", "8630501", "8219102",
               "4120400", "4924101", "1011201", "8599699", "6190602"]

_TIPOS_EMBARCACAO = ["Lancha", "Veleiro", "Iate", "Barco", "Catamara", "Speedboat"]
_PORTE_EMB = ["PEQUENO", "MEDIO", "GRANDE"]
_MATERIAL_CASCO = ["Fibra", "Madeira", "Aluminio", "Aco"]
_MOTOR_EMB = ["Fora-de-borda", "Inboard", "Semirrigido", "Inboard/Fora-de-borda"]
_TIPOS_MOTOR = ["Gasolina", "Diesel", "Etanol", "Eletrico"]

_TIPOS_AERONAVE = ["AVIAO", "HELICOPTERO", "PLANADOR", "DRONE"]
_FABRICANTES_AC = ["Cessna", "Piper", "Embraer", "Boeing", "Airbus",
                   "Bell", "Robinson", "Beechcraft", "Bombardier", "Daher"]
_MODELOS_AC = {"Cessna": ["172S", "182T", "208B", "CJ4"], "Piper": ["PA-28", "PA-44", "M500"],
               "Embraer": ["Phenom 100", "Phenom 300", "ERJ-145"], "Bell": ["407", "505", "429"],
               "Robinson": ["R44", "R66"], "Boeing": ["737", "747", "777"],
               "Airbus": ["A320", "A350"], "Beechcraft": ["King Air 350"],
               "Bombardier": ["Global 6000"], "Daher": ["TBM 940"]}
_MOTOR_ACAO = ["PISTAO", "TURBOEIXO", "TURBOHELICE", "JATO", "FAN"]

_ESPECIES = ["CAO", "GATO", "CAVALO", "BOVINO", "OUTRO"]
_RACAS_CAO = ["Labrador", "Pastor Alemao", "Bulldog", "Poodle", "Shih Tzu",
              "Husky", "Boxer", "Golden", "Rottweiler", "Dalmata"]
_RACAS_GATO = ["Persa", "Siames", "Maine Coon", "Sphynx", "Bengal",
               "Ragdoll", "British Shorthair", "Angora"]
_RACAS_CAVALO = ["Mangalarga", "Quarto de Milha", "Crioulo", "Appaloosa"]
_RACAS_BOVINO = ["Nelore", "Angus", "Jersey", "Girolando"]
_CORRESP_RACA = {"CAO": _RACAS_CAO, "GATO": _RACAS_GATO, "CAVALO": _RACAS_CAO, "BOVINO": _RACAS_BOVINO}
_VACINAS_AN = ["Raiva", "Polivalente", "Gripe Canina", "Leptospirose",
               "FeLV", "FIV", "Giardia", "Verminose"]
_FABRICANTES_VAC = ["Zoetis", "Vetnil", "Ourofino", "Biovet", "Agener Uniao"]
_CLINICAS = ["PetClinic SP", "VetCare", "Animal Hospital", "PetSaude", "VetPrime"]
_FABRICANTES_EMB = ["Yamaha", "Mercury", "Suzuki", "Honda", "Yanmar", "Volvo Penta"]
_FABRICANTES_ANIM = ["PetAge", "HomeAgain", "AVID", "Bayer", "MSD Animal Health"]

_NOMES_EMB = ["Estrela do Mar", "Vento Leste", "Sol Nascente", "Ondas Azuis",
              "Paz do Oceano", "Aurora", "Trovao", "Libertade", "Aventura",
              "Tridente", "Navegador", "Coragem", "Fenix", "Esperanca", "Tranquilidade"]
_NOMES_ANIM = ["Rex", "Luna", "Max", "Bella", "Thor", "Mel", "Nike", "Caramelo",
               "Tobby", "Lady", "Bob", "Mia", "Rocky", "Amora", "Nina"]


def _cpf():
    return "".join(random.choices(string.digits, k=11))

def _cnpj():
    return "".join(random.choices(string.digits, k=14))

def _nome(sexo=None):
    if sexo is None:
        sexo = random.choice(["M", "F"])
    return f"{random.choice(_NOMES_M if sexo == 'M' else _NOMES_F)} {random.choice(_SOBRANOMES)}"

def _data(ano_inicio, ano_fim):
    d = datetime(ano_inicio, 1, 1) + timedelta(days=random.randint(0, max(1, (ano_fim - ano_inicio) * 365)))
    return d.strftime("%d/%m/%Y")

def _uf():
    return random.choice(_UFS)

def _cidade():
    return capital_da_uf(_uf())
def _regiao():
    uf = _uf()
    return uf, capital_da_uf(uf)


def _rua():
    return f"{random.choice(_RUAS)}, {random.randint(1, 2000)}"

def _bairro():
    return random.choice(_BAIRROS)

def _placa():
    return f"{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}{random.choice(string.digits)}{random.choice(string.ascii_uppercase+string.digits)}{random.choice(string.ascii_uppercase+string.digits)}{random.choice(string.ascii_uppercase+string.digits)}"

def _renavan():
    return "".join(random.choices(string.digits, k=11))

def _chassis():
    chars = [c for c in string.ascii_uppercase + string.digits if c not in "IOQ"]
    return "".join(random.choices(chars, k=17))

def _matricula_ac():
    return f"PT{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}"

def _registro_nr():
    return f"NR-{random.randint(2020,2026)}-{random.randint(1,999):03d}"

def _unique(items_set, generator):
    while True:
        item = generator()
        if item not in items_set:
            items_set.add(item)
            return item


# ═══════════════════════════════════════════════════════════════════════
#  FASE 1: CO — Empresas (300)
# ═══════════════════════════════════════════════════════════════════════

def gerar_co():
    print(f"\n{'='*60}")
    print(f"  FASE 1: Gerando {NUM} cadastros de EMPRESAS (CO)")
    print(f"{'='*60}")

    chains = {}
    cpjs = set()
    cpfs = set()
    signer = generate_authority_keypair("JUCESP - Junta Comercial de SP")
    stats = {}

    for i in range(NUM):
        cnpj = _unique(cpjs, _cnpj)
        tipo = random.choice(_EMPRESAS_TIPOS)
        razao = f"{tipo} {_nome('M').split()[0]} {random.choice(_RAZAO_SUFIXOS)}"

        chain = CompanyChain(difficulty=DIFFICULTY)
        chain.set_signer(signer)

        # Genesis: Constituicao
        _reg_uf, _reg_cidade = _regiao()
        dados = CompanyEventFactory.constituicao(
            cnpj=cnpj,
            razao_social=razao,
            nome_fantasia=tipo[:10],
            data_constituicao=_data(2015, 2024),
            tipo_empresa=random.choice(["LTDA", "SA", "MEI", "SLU"]),
            porte=random.choice(["ME", "EPP", "MEDIO", "GRANDE"]),
            capital_social=round(random.uniform(5000, 500000), 2),
            natureza_juridica="2062",
            atividade_principal=random.choice(_ATIVIDADES),
            endereco_sede={"logradouro": _rua(), "bairro": _bairro(), "cidade": _cidade(), "uf": _uf()},
            responsavel_cpf=_cpf(),
            responsavel_nome=_nome(),
            uf=_reg_uf,
            cidade=_reg_cidade,
        )
        chain.create_genesis(dados)
        stats["constituicao"] = stats.get("constituicao", 0) + 1

        num_eventos = random.randint(1, 5)
        for _ in range(num_eventos):
            evt = random.choice(["adicao_socio", "mudanca_capital", "certidao", "garantia", "suspensao", "reabertura"])
            try:
                if evt == "adicao_socio":
                    socio_cpf = _unique(cpfs, _cpf)
                    chain.add_event("ADICAO_SOCIO", CompanyEventFactory.adicao_socio(
                        cnpj=cnpj, socio_cpf=socio_cpf, socio_nome=_nome(),
                        participacao=round(random.uniform(5, 50), 1),
                        data_entrada=_data(2020, 2025),
                    ))
                elif evt == "mudanca_capital":
                    chain.add_event("MUDANCA_CAPITAL", CompanyEventFactory.mudanca_capital(
                        cnpj=cnpj, capital_anterior=random.uniform(5000, 100000),
                        capital_novo=random.uniform(50000, 500000),
                        data_mudanca=_data(2022, 2025),
                    ))
                elif evt == "certidao":
                    chain.add_event("CERTIDAO", CompanyEventFactory.certidao(
                        cnpj=cnpj, tipo_certidao=random.choice(["NEGATIVA", "POSITIVA", "REGULARIDADE"]),
                        numero=f"CND-{random.randint(2020,2026)}-{random.randint(1,9999)}",
                        data_emissao=_data(2023, 2025), orgao_emissor="Receita Federal",
                    ))
                elif evt == "garantia":
                    chain.add_event("GARANTIA", CompanyEventFactory.garantia(
                        cnpj=cnpj, credor_nome=random.choice(["Banco do Brasil", "Itau", "Bradesco"]),
                        credor_cnpj=_cnpj(), valor_garantia=round(random.uniform(10000, 500000), 2),
                        data_garantia=_data(2023, 2025), data_vencimento=_data(2028, 2035),
                    ))
                elif evt == "suspensao":
                    chain.add_event("SUSPENSAO", CompanyEventFactory.suspensao(
                        cnpj=cnpj, data_suspensao=_data(2024, 2025), motivo="Inatividade",
                    ))
                elif evt == "reabertura":
                    chain.add_event("REABERTURA", CompanyEventFactory.reabertura(
                        cnpj=cnpj, data_reabertura=_data(2024, 2025),
                    ))
                stats[evt] = stats.get(evt, 0) + 1
            except ValueError:
                pass

        chains[cnpj] = chain

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{NUM}] empresas geradas...")

    print(f"\n  Total: {len(chains)} empresas | Eventos: {stats}")
    return chains


# ═══════════════════════════════════════════════════════════════════════
#  FASE 2: EM — Embarcacoes (300)
# ═══════════════════════════════════════════════════════════════════════

def gerar_em():
    print(f"\n{'='*60}")
    print(f"  FASE 2: Gerando {NUM} cadastros de EMBARCACOES (EM)")
    print(f"{'='*60}")

    chains = {}
    registros = set()
    cpfs = set()
    signer = generate_authority_keypair("Capitania dos Portos - SP")
    stats = {}

    for i in range(NUM):
        reg = _unique(registros, _registro_nr)
        tipo_emb = random.choice(_TIPOS_EMBARCACAO)

        chain = VesselChain(difficulty=DIFFICULTY)
        chain.set_signer(signer)

        # Genesis: Construcao
        _reg_uf, _reg_cidade = _regiao()
        dados = VesselEventFactory.construcao(
            registro_nr=reg,
            nome_embarcacao=random.choice(_NOMES_EMB),
            tipo_embarcacao=tipo_emb,
            porte=random.choice(_PORTE_EMB),
            comprimento_m=round(random.uniform(5, 25), 1),
            beam_m=round(random.uniform(2, 8), 1),
            pontal_m=round(random.uniform(1, 4), 1),
            calado_m=round(random.uniform(0.5, 3), 1),
            deslocamento_ton=round(random.uniform(1, 30), 1),
            casco_material=random.choice(_MATERIAL_CASCO),
            motorizacao=random.choice(_MOTOR_EMB),
            motor_potencia_cv=round(random.uniform(50, 800), 0),
            motor_tipo=random.choice(_TIPOS_MOTOR),
            motor_fabricante=random.choice(_FABRICANTES_EMB),
            ano_construcao=random.randint(2000, 2024),
            estaleiro=f"Estaleiro {_nome('M').split()[0]}",
            porto_registro=random.choice(["Santos", "Rio de Janeiro", "Paranagua", "Itajai"]),
            uf=_reg_uf,
            cidade=_reg_cidade,
        )
        chain.create_genesis(dados)
        stats["construcao"] = stats.get("construcao", 0) + 1

        num_eventos = random.randint(1, 4)
        for _ in range(num_eventos):
            evt = random.choice(["compra_venda", "revisao", "inspecao", "licenciamento", "seguro"])
            try:
                if evt == "compra_venda":
                    chain.add_event("COMPRA_VENDA", VesselEventFactory.compra_venda(
                        registro_nr=reg, comprador_cpf=_cpf(), comprador_nome=_nome(),
                        vendedor_cpf=_cpf(), vendedor_nome=_nome(),
                        valor_transacao=round(random.uniform(20000, 500000), 2),
                        data_transacao=_data(2020, 2025),
                    ))
                elif evt == "revisao":
                    chain.add_event("REVISAO", VesselEventFactory.revisao(
                        registro_nr=reg, data_revisao=_data(2023, 2025),
                        oficina=random.choice(["Marina Santos", "Nautica SP", "Porto Seguro"]),
                        tipo_revisao=random.choice(["PREVENTIVA", "CORRETIVA"]),
                        itens_revisados=random.sample(["Motor", "Casco", "Eletrica", "Sonar", "Vela"], k=random.randint(2, 4)),
                        valor_total=round(random.uniform(1000, 20000), 2),
                    ))
                elif evt == "inspecao":
                    chain.add_event("INSPECAO", VesselEventFactory.inspecao(
                        registro_nr=reg, data_inspecao=_data(2023, 2025),
                        orgao_inspecao="Capitania dos Portos",
                        resultado=random.choice(["APROVADA", "REPROVADA"]),
                    ))
                elif evt == "licenciamento":
                    chain.add_event("LICENCIAMENTO", VesselEventFactory.licenciamento(
                        registro_nr=reg, ano_licenciamento=random.randint(2023, 2025),
                        data_licenciamento=_data(2023, 2025),
                    ))
                elif evt == "seguro":
                    chain.add_event("SEGURO", VesselEventFactory.seguro(
                        registro_nr=reg, seguradora_nome=random.choice(["Porto Seguro", "Tokio Marine"]),
                        seguradora_cnpj=_cnpj(), apolice_numero=f"AP-{random.randint(2020,2026)}-{random.randint(1,9999)}",
                        data_inicio=_data(2024, 2025), data_fim=_data(2025, 2026),
                        valor_segurado=round(random.uniform(50000, 500000), 2),
                    ))
                stats[evt] = stats.get(evt, 0) + 1
            except ValueError:
                pass

        chains[reg] = chain

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{NUM}] embarcacoes geradas...")

    print(f"\n  Total: {len(chains)} embarcacoes | Eventos: {stats}")
    return chains


# ═══════════════════════════════════════════════════════════════════════
#  FASE 3: AC — Aeronaves (300)
# ═══════════════════════════════════════════════════════════════════════

def gerar_ac():
    print(f"\n{'='*60}")
    print(f"  FASE 3: Gerando {NUM} cadastros de AERONAVES (AC)")
    print(f"{'='*60}")

    chains = {}
    matriculas = set()
    signer = generate_authority_keypair("ANAC - Agencia Nacional de Aviacao Civil")
    stats = {}

    for i in range(NUM):
        mat = _unique(matriculas, _matricula_ac)
        fab = random.choice(_FABRICANTES_AC)
        modelo = random.choice(_MODELOS_AC.get(fab, ["Default"]))

        chain = AircraftChain(difficulty=DIFFICULTY)
        chain.set_signer(signer)

        # Genesis: Fabricacao
        _reg_uf, _reg_cidade = _regiao()
        dados = AircraftEventFactory.fabricacao(
            matricula=mat,
            nome_aeronave=f"{fab} {modelo}",
            fabricante=fab,
            modelo=modelo,
            tipo_aeronave=random.choice(_TIPOS_AERONAVE),
            ano_fabricacao=random.randint(1990, 2024),
            peso_max_decolagem_kg=round(random.uniform(500, 80000), 0),
            motorizacao=random.choice(_MOTOR_ACAO),
            num_motores=random.choice([1, 2, 4]),
            motor_potencia_cv=round(random.uniform(100, 5000), 0),
            envergadura_m=round(random.uniform(8, 60), 1),
            comprimento_m=round(random.uniform(6, 70), 1),
            autonomia_km=round(random.uniform(500, 10000), 0),
            velocidade_max_kmh=round(random.uniform(150, 900), 0),
            capacidade_pilotos=1,
            capacidade_passageiros=random.randint(0, 180),
            numero_serie=f"SN-{random.randint(10000, 99999)}",
            uf=_reg_uf,
            cidade=_reg_cidade,
        )
        chain.create_genesis(dados)
        stats["fabricacao"] = stats.get("fabricacao", 0) + 1

        num_eventos = random.randint(1, 4)
        for _ in range(num_eventos):
            evt = random.choice(["airworthiness", "revisao", "compra_venda", "seguro", "inspecao"])
            try:
                if evt == "airworthiness":
                    chain.add_event("AIRWORTHINESS", AircraftEventFactory.airworthiness(
                        matricula=mat, data_emissao=_data(2023, 2025),
                        data_validade=_data(2025, 2027),
                        numero_certificado=f"CVA-{random.randint(2020,2026)}-{random.randint(1,9999)}",
                    ))
                elif evt == "revisao":
                    chain.add_event("REVISAO", AircraftEventFactory.revisao(
                        matricula=mat, data_revisao=_data(2023, 2025),
                        oficina=random.choice(["Aero Maintenance", "AeroTech", "Aviação Service"]),
                        tipo_revisao=random.choice(["ANUAL", "SEMESTRAL", "CAPITAL"]),
                        itens_revisados=random.sample(["Motor", "Asas", "Sistema eletrico", "Instrumentos", "Trem de pouso"], k=random.randint(2, 4)),
                        valor_total=round(random.uniform(5000, 100000), 2),
                    ))
                elif evt == "compra_venda":
                    chain.add_event("COMPRA_VENDA", AircraftEventFactory.compra_venda(
                        matricula=mat, comprador_cpf=_cpf(), comprador_nome=_nome(),
                        vendedor_cpf=_cpf(), vendedor_nome=_nome(),
                        valor_transacao=round(random.uniform(100000, 5000000), 2),
                        data_transacao=_data(2020, 2025),
                    ))
                elif evt == "seguro":
                    chain.add_event("SEGURO", AircraftEventFactory.seguro(
                        matricula=mat, seguradora_nome=random.choice(["Tokio Marine", "Liberty", "Azul Seguros"]),
                        seguradora_cnpj=_cnpj(),
                        apolice_numero=f"AC-{random.randint(2020,2026)}-{random.randint(1,9999)}",
                        data_inicio=_data(2024, 2025), data_fim=_data(2025, 2026),
                        valor_segurado=round(random.uniform(200000, 5000000), 2),
                    ))
                elif evt == "inspecao":
                    chain.add_event("INSPECAO", AircraftEventFactory.inspecao(
                        matricula=mat, data_inspecao=_data(2023, 2025),
                        orgao_inspecao="ANAC",
                        resultado=random.choice(["APROVADA", "REPROVADA"]),
                    ))
                stats[evt] = stats.get(evt, 0) + 1
            except ValueError:
                pass

        chains[mat] = chain

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{NUM}] aeronaves geradas...")

    print(f"\n  Total: {len(chains)} aeronaves | Eventos: {stats}")
    return chains


# ═══════════════════════════════════════════════════════════════════════
#  FASE 4: AN — Animais (300)
# ═══════════════════════════════════════════════════════════════════════

def gerar_an():
    print(f"\n{'='*60}")
    print(f"  FASE 4: Gerando {NUM} cadastros de ANIMAIS (AN)")
    print(f"{'='*60}")

    chains = {}
    ids = set()
    signer = generate_authority_keypair("CRMV-SP - Conselho Regional de Veterinarios")
    stats = {}

    for i in range(NUM):
        import hashlib
        nome = random.choice(_NOMES_ANIM)
        cpf_prop = _cpf()
        esp = random.choice(_ESPECIES)
        racas = _CORRESP_RACA.get(esp, _RACAS_CAO)
        aid = hashlib.sha256(f"{nome}{cpf_prop}{i}".encode()).hexdigest()[:12]

        chain = AnimalChain(difficulty=DIFFICULTY)
        chain.set_signer(signer)

        # Genesis: Nascimento
        _reg_uf, _reg_cidade = _regiao()
        dados = AnimalEventFactory.nascimento(
            nome=nome,
            especie=esp,
            raca=random.choice(racas),
            sexo=random.choice(["M", "F"]),
            data_nascimento=_data(2018, 2024),
            cor=random.choice(["Preto", "Branco", "Caramelo", "Dourado", "Cinza", "Malhado"]),
            peso_kg=round(random.uniform(0.5, 60), 1),
            proprietario_cpf=cpf_prop,
            proprietario_nome=_nome(),
            uf=_reg_uf,
            cidade=_reg_cidade,
        )
        chain.create_genesis(dados)
        stats["nascimento"] = stats.get("nascimento", 0) + 1

        num_eventos = random.randint(1, 5)
        for _ in range(num_eventos):
            evt = random.choice(["vacinacao", "castracao", "tratamento", "compra_venda", "microchip", "licenca"])
            try:
                if evt == "vacinacao":
                    chain.add_event("VACINACAO", AnimalEventFactory.vacinacao(
                        nome_vacina=random.choice(_VACINAS_AN),
                        data_vacinacao=_data(2023, 2025),
                        lote=f"LOT-{random.randint(1000,9999)}",
                        fabricante=random.choice(_FABRICANTES_VAC),
                        dose=random.choice(["1a dose", "2a dose", "Reforco"]),
                    ))
                elif evt == "castracao":
                    chain.add_event("CASTRACAO", AnimalEventFactory.castracao(
                        data_castracao=_data(2023, 2025),
                        veterinario_cpf=_cpf(), veterinario_nome=_nome(),
                        clinica=random.choice(_CLINICAS),
                        metodo=random.choice(["Cirurgico", "Laparoscopico"]),
                    ))
                elif evt == "tratamento":
                    chain.add_event("TRATAMENTO", AnimalEventFactory.tratamento(
                        data_inicio=_data(2023, 2025),
                        data_fim=_data(2024, 2025),
                        diagnostico=random.choice(["Otite", "Dermatite", "Gastroenterite", "Fratura", "Conjuntivite"]),
                        veterinario_cpf=_cpf(), veterinario_nome=_nome(),
                        clinica=random.choice(_CLINICAS),
                        medicamentos=random.sample(["Antibiotico", "Anti-inflamatorio", "Antifungico", "Vitaminico"], k=random.randint(1, 3)),
                        valor_total=round(random.uniform(100, 3000), 2),
                    ))
                elif evt == "compra_venda":
                    chain.add_event("COMPRA_VENDA", AnimalEventFactory.compra_venda(
                        nome=nome, comprador_cpf=_cpf(), comprador_nome=_nome(),
                        vendedor_cpf=_cpf(), vendedor_nome=_nome(),
                        valor_transacao=round(random.uniform(200, 10000), 2),
                        data_transacao=_data(2023, 2025),
                    ))
                elif evt == "microchip":
                    chain.add_event("MICROCHIP", AnimalEventFactory.microchip(
                        numero_microchip=f"900{random.randint(100000000, 999999999)}",
                        data_implantacao=_data(2023, 2025),
                        fabricante=random.choice(_FABRICANTES_ANIM),
                    ))
                elif evt == "licenca":
                    chain.add_event("LICENCA", AnimalEventFactory.licenca(
                        numero_licenca=f"LIC-{_uf()}-{random.randint(2020,2026)}-{random.randint(1,9999)}",
                        data_emissao=_data(2023, 2025),
                        data_validade=_data(2024, 2026),
                        orgao_emissor="Prefeitura Municipal",
                    ))
                stats[evt] = stats.get(evt, 0) + 1
            except ValueError:
                pass

        chains[aid] = chain

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{NUM}] animais gerados...")

    print(f"\n  Total: {len(chains)} animais | Eventos: {stats}")
    return chains


# ═══════════════════════════════════════════════════════════════════════
#  FASE 5: Salvar e Validar
# ═══════════════════════════════════════════════════════════════════════

def salvar_e_validar(chains_co, chains_em, chains_ac, chains_an, db=None):
    print(f"\n{'='*60}")
    print(f"  FASE 5: Validacao e Persistencia")
    print(f"{'='*60}")

    os.makedirs("demo_output", exist_ok=True)

    for name, chains in [("co", chains_co), ("em", chains_em), ("ac", chains_ac), ("an", chains_an)]:
        total_blocos = 0
        total_assinados = 0
        validas = 0
        invalidas = 0

        for key, chain in chains.items():
            ok, msg = chain.validate(require_signatures=True)
            total_blocos += len(chain)
            total_assinados += sum(1 for b in chain.chain if b.has_signature())
            if ok:
                validas += 1
            else:
                invalidas += 1

            # Persiste todas as cadeias no SQLite centralizado
            if db:
                chain_data = {
                    "difficulty": chain.difficulty,
                    "chain": [b.to_dict() for b in chain.chain],
                }
                db.save_domain_chain(name, key, chain.difficulty, chain_data)

            # Salva apenas primeiros 100 por blockchain (para nao encher disco)
            if list(chains.keys()).index(key) < 100:
                filepath = f"demo_output/{name}_{key}.json"
                chain.save_to_file(filepath)

        print(f"\n  {name.upper()}:")
        print(f"    Cadeias:        {len(chains)}")
        print(f"    Total blocos:   {total_blocos}")
        print(f"    Total assinados:{total_assinados}")
        print(f"    Validas:        {validas}")
        print(f"    Invalidas:      {invalidas}")


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 60)
    print("  GERACAO DE 300 REGISTROS — 4 NOVAS BLOCKCHAINS")
    print("  CO (Empresas) | EM (Embarcacoes) | AC (Aeronaves) | AN (Animais)")
    print("=" * 60)

    t0 = time.time()

    db = Database()

    chains_co = gerar_co()
    chains_em = gerar_em()
    chains_ac = gerar_ac()
    chains_an = gerar_an()

    salvar_e_validar(chains_co, chains_em, chains_ac, chains_an, db)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  CONCLUIDO em {elapsed:.1f}s")
    print(f"  Arquivos salvos em demo_output/")
    print(f"  Cadeias persistidas no SQLite centralizado: {db.db_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
