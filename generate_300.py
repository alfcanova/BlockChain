#!/usr/bin/env python3
"""
generate_300.py — Gera 300 registros em cada blockchain (PF, IM, MO)
com cross-chain e cobertura de todos os tipos de evento.

Uso:  PYTHONIOENCODING=utf-8 python generate_300.py
"""

import sys
import os
import random
import time
import json
import string
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blockchain_pf import (
    Blockchain, EventFactory, EventType,
    generate_authority_keypair,
)
from blockchain_pf.database import Database
from blockchain_pf.geografia_br import capital_da_uf
from blockchain_im import (
    PropertyChain, PropertyEventFactory, PropertyEventType,
    CrossChainManager,
)
from blockchain_mo import (
    VehicleChain, VehicleEventFactory, VehicleEventType,
    CrossChainMO,
)

# ── Configurações ──────────────────────────────────────────────────────

NUM_PF = 300
NUM_IM = 300
NUM_MO = 300
DIFFICULTY = 1  # Baixa para ser rápido

random.seed(42)  # Reprodutível

# ── Helpers ────────────────────────────────────────────────────────────

_UFS = ["SP", "RJ", "MG", "BA", "RS", "PR", "SC", "PE", "CE", "GO", "DF", "ES", "PA", "MA", "MT"]
_CIDES_SP = ["São Paulo", "Campinas", "Santos", "Sorocaba", "Ribeirão Preto", "São José dos Campos",
             "Osasco", "Jundiaí", "Piracicaba", "Bauru", "São Bernardo", "Guarulhos", "Mogi das Cruzes"]
_CIDES_RJ = ["Rio de Janeiro", "Niterói", "Petrópolis", "Volta Redonda", "Campos dos Goytacazes"]
_CIDES_Gerais = ["Brasília", "Curitiba", "Porto Alegre", "Salvador", "Recife", "Fortaleza",
                 "Belém", "Manaus", "Goiânia", "Vitória", "Belo Horizonte", "Belém", "São Luís"]

_NOMES_M = [
    "João", "Pedro", "Lucas", "Matheus", "Gabriel", "Rafael", "Bruno", "Felipe",
    "Gustavo", "Feliciano", "Leonardo", "Tiago", "André", "Carlos", "Antônio",
    "Francisco", "Paulo", "Marcos", "Luis", "Roberto", "Fernando", "Sérgio",
    "Eduardo", "Ricardo", "Alexandre", "Diego", "Vitor", "Thiago", "Daniel",
    "Marcelo", "Henrique", "Renato", "Rodrigo", "Sandro", "Caio", "Murilo",
]
_NOMES_F = [
    "Maria", "Ana", "Juliana", "Fernanda", "Patrícia", "Camila", "Amanda",
    "Bruna", "Letícia", "Carla", "Vanessa", "Renata", "Adriana", "Cláudia",
    "Daniela", "Luciana", "Mariana", "Priscila", "Raquel", "Tatiana",
    "Isabela", "Larissa", "Natália", "Paula", "Renata", "Simone", "Sônia",
    "Teresa", "Valéria", "Viviane", "Bianca", "Cristiane", "Débora", "Eliane",
]
_SOBRANOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves",
    "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho",
    "Almeida", "Lopes", "Soares", "Fernandes", "Vieira", "Barbosa",
    "Rocha", "Dias", "Nascimento", "Andrade", "Moreira", "Nunes", "Marques",
    "Machado", "Mendes", "Freitas", "Cardoso", "Ramos", "Gonçalves", "Santana",
]

_RUAS = [
    "Rua das Flores", "Av. Brasil", "Rua Augusta", "Av. Paulista", "Rua Oscar Freire",
    "Av. Rebouças", "Rua Haddock Lobo", "Av. Faria Lima", "Rua Bela Cintra",
    "Rua da Consolação", "Av. Ipiranga", "Rua Liberdade", "Av. Sumaré",
    "Rua Cardeal Arcoverde", "Rua dos Pinheiros", "Av. Brigadeiro Faria Lima",
    "Rua Artur de Azevedo", "Rua Wisard", "Rua Gomes de Carvalho", "Av. Eng. Luis Carlos Berrini",
]
_BAIRROS = ["Centro", "Jardins", "Vila Mariana", "Moema", "Pinheiros", "Itaim Bibi",
            "Brooklin", "Campo Belo", "Vila Olímpia", "Perdizes", "Lapa", "Consolação"]
_MARCAS_CAR = ["Volkswagen", "Chevrolet", "Fiat", "Toyota", "Honda", "Hyundai",
               "Ford", "Jeep", "Nissan", "Renault", "Citroën", "Peugeot", "BMW",
               "Mercedes-Benz", "Audi"]
_MODELOS = {
    "Volkswagen": ["Gol", "Polo", "T-Cross", "Taos", "Virtus", "Saveiro"],
    "Chevrolet": ["Onix", "Tracker", "S10", "Cruze", "Spin"],
    "Fiat": ["Argo", "Cronos", "Pulse", "Fastback", "Strada"],
    "Toyota": ["Corolla", "Yaris", "Hilux", "RAV4", "SW4"],
    "Honda": ["Civic", "City", "HR-V", "WR-V"],
    "Hyundai": ["HB20", "Creta", "Tucson", "Santa Fe"],
    "Ford": ["Bronco", "Territory", "Ranger"],
    "Jeep": ["Renegade", "Compass", "Commander"],
    "Nissan": ["Kicks", "Frontier", "Versa"],
    "Renault": ["Kwid", "Duster", "Captur"],
    "Citroën": ["C3", "C4 Cactus"],
    "Peugeot": ["208", "2008", "308"],
    "BMW": ["Série 3", "X1", "X3"],
    "Mercedes-Benz": ["Classe A", "GLA", "GLC"],
    "Audi": ["A3", "Q3", "Q5"],
}
_CORES = ["Branco", "Prata", "Preto", "Vermelho", "Azul", "Cinza", "Verde", "Bege", "Marrom"]
_COMBUSTIVEIS = ["GASOLINA", "ETANOL", "FLEX", "DIESEL", "ELETRICO"]

_VACINAS = ["COVID-19", "Febre Amarela", "Gripe", "Hepatite B", "HPV",
            "Tripla Viral", "Poliomielite", "DPT", "BCG", "Rotavírus"]
_PROTESES = ["Prótese de Joelho", "Prótese de Quadril", "Marca-Passo",
             "Stent Coronário", "Prótese Dentária", "Prótese Ocular",
             "Implante Coclear", "Prótese de Ombro"]
_FABRICANTES_VAC = ["Pfizer", "AstraZeneca", "Sinovac", "Janssen", "Butantan", "Fiocruz"]
_HOSPITAIS = ["Hospital Albert Einstein", "Hospital Sírio-Libanês", "Hospital Beneficência",
              "Hospital Oswaldo Cruz", "Hospital das Clínicas", "Hospital São Paulo"]
_OFICINAS = ["Oficina Mecânica Silva", "AutoCenter Brasil", "Mecânica Express",
             "Oficina do Zé", "CarService Premium"]
_BANCOS = ["Banco do Brasil", "Itaú Unibanco", "Bradesco", "Caixa Econômica Federal",
           "Santander", "Banco Inter", "Nubank", "BTG Pactual"]
_ORGAOS = ["DETRAN-SP", "DETRAN-RJ", "DETRAN-MG", "CET", "Polícia Rodoviária",
           "Polícia Civil", "Ministério Público"]

# ── Geradores ──────────────────────────────────────────────────────────

def _cpf_aleatorio() -> str:
    """Gera CPF com 11 dígitos."""
    return "".join(random.choices(string.digits, k=11))

def _nome_completo(sexo: str = None) -> str:
    if sexo is None:
        sexo = random.choice(["M", "F"])
    primeiro = random.choice(_NOMES_M if sexo == "M" else _NOMES_F)
    meio = random.choice(_NOMES_M + _NOMES_F)
    sobrenome = random.choice(_SOBRANOMES)
    return f"{primeiro} {meio} {sobrenome}"

def _data_aleatoria(ano_inicio: int, ano_fim: int) -> str:
    if ano_inicio > ano_fim:
        ano_inicio, ano_fim = ano_fim, ano_inicio
    if ano_inicio == ano_fim:
        d = datetime(ano_inicio, 1, 1) + timedelta(days=random.randint(0, 364))
    else:
        d = datetime(ano_inicio, 1, 1) + timedelta(days=random.randint(0, (ano_fim - ano_inicio) * 365))
    return d.strftime("%d/%m/%Y")

def _data_nascimento(idade: int) -> str:
    ano = datetime.now().year - idade
    return _data_aleatoria(ano - 1, ano)

def _uf() -> str:
    return random.choice(_UFS)

def _cidade(uf: str = None) -> str:
    if uf is None:
        uf = _uf()
    return capital_da_uf(uf)

def _rua() -> str:
    return f"{random.choice(_RUAS)}, {random.randint(1, 2000)}"

def _bairro() -> str:
    return random.choice(_BAIRROS)

def _cep() -> str:
    return f"{random.randint(10000, 99999)}-{random.randint(100, 999)}"

def _placa() -> str:
    """Gera placa Mercosul."""
    l1 = random.choice(string.ascii_uppercase)
    l2 = random.choice(string.ascii_uppercase)
    l3 = random.choice(string.ascii_uppercase)
    n1 = random.choice(string.digits)
    a4 = random.choice(string.ascii_uppercase + string.digits)
    a5 = random.choice(string.ascii_uppercase + string.digits)
    a6 = random.choice(string.ascii_uppercase + string.digits)
    return f"{l1}{l2}{l3}{n1}{a4}{a5}{a6}"

def _renavan() -> str:
    return "".join(random.choices(string.digits, k=11))

def _chassis() -> str:
    """Gera chassi VIN (17 chars, sem I/O/Q)."""
    chars = [c for c in string.ascii_uppercase + string.digits if c not in "IOQ"]
    return "".join(random.choices(chars, k=17))

def _placa_existe(placas: set) -> str:
    while True:
        p = _placa()
        if p not in placas:
            placas.add(p)
            return p

def _cpf_existe(cpfs: set) -> str:
    while True:
        c = _cpf_aleatorio()
        if c not in cpfs:
            cpfs.add(c)
            return c


# ═══════════════════════════════════════════════════════════════════════
#  FASE 1: CRIAR BLOCKCHAINS PF (300 pessoas)
# ═══════════════════════════════════════════════════════════════════════

def gerar_pf(db: Database) -> tuple[dict, list]:
    """Gera 300 cadeias de PF com eventos variados."""
    print(f"\n{'='*60}")
    print(f"  FASE 1: Gerando {NUM_PF} cadastros de PESSOAS FÍSICAS")
    print(f"{'='*60}")

    chains = {}
    cpfs_usados = set()
    signer = generate_authority_keypair("Cartório Central de Registro Civil")
    pf_chains_info = []  # Para cross-chain

    stats = {"nascimento": 0, "casamento": 0, "divorcio": 0, "adocao": 0,
             "alteracao_nome": 0, "disvinculacao": 0, "vacina": 0,
             "protese": 0, "obito": 0}

    # Pré-definir casais para divórcio posterior
    casais = []  # (cpf1, cpf2, data_casamento)

    for i in range(NUM_PF):
        cpf = _cpf_existe(cpfs_usados)
        sexo = random.choice(["M", "F"])
        nome = _nome_completo(sexo)
        idade = random.randint(0, 85)
        uf_nasc = _uf()
        cidade_nasc = _cidade(uf_nasc)
        nome_mae = _nome_completo("F")

        chain = Blockchain(difficulty=DIFFICULTY)
        chain.set_signer(signer)

        # ── NASCIMENTO (genesis) ──────────────────────────────────────
        dados = EventFactory.nascimento(
            cpf=cpf,
            nome_completo=nome,
            data_nascimento=_data_nascimento(idade),
            sexo=sexo,
            cidade_nascimento=cidade_nasc,
            uf_nascimento=uf_nasc,
            nome_mae=nome_mae,
            nome_pai=_nome_completo("M") if random.random() > 0.15 else None,
        )
        genesis = chain.create_genesis(dados)
        stats["nascimento"] += 1

        # ── VACINAÇÃO (antes dos 30 anos, ~40% chance) ────────────────
        if idade < 30 and random.random() < 0.4:
            for _ in range(random.randint(1, 4)):
                vacina = random.choice(_VACINAS)
                dose_num = random.randint(1, 3)
                chain.add_event(EventType.VACINACAO.value, EventFactory.vacina(
                    cpf=cpf,
                    nome_vacina=vacina,
                    data_vacinacao=_data_aleatoria(2015, 2025),
                    lote=f"LOTE-{random.randint(1000,9999)}",
                    fabricante=random.choice(_FABRICANTES_VAC),
                    dose=f"{dose_num}ª dose",
                    unidade_saude=f"UBS {_bairro()}",
                    cidade=cidade_nasc,
                    uf=uf_nasc,
                ))
                stats["vacina"] += 1

        # ── PRÓTESE (~10% dos adultos, idade > 25) ───────────────────
        if idade > 25 and random.random() < 0.1:
            protese = random.choice(_PROTESES)
            dados_p = EventFactory.protese(
                cpf=cpf,
                nome_protese=protese,
                data_implantacao=_data_aleatoria(2015, 2025),
                tipo=random.choice(["Ortopédica", "Cardíaca", "Dental", "Neurológica"]),
                marca_modelo=f"Modelo-{random.randint(100,999)}",
                medico_responsavel=f"Dr(a). {_nome_completo()}",
                hospital_clinica=random.choice(_HOSPITAIS),
                cidade=cidade_nasc,
                uf=uf_nasc,
                data_remocao=_data_aleatoria(2020, 2025) if random.random() < 0.15 else None,
                motivo_remocao="Desgaste" if random.random() < 0.15 else "",
            )
            chain.add_event(EventType.PROTESE.value, dados_p)
            stats["protese"] += 1

        # ── ADOÇÃO (~5% dos menores de 18) ───────────────────────────
        if idade < 18 and random.random() < 0.05:
            chain.add_event(EventType.ADOCAO.value, EventFactory.adocao(
                cpf=cpf,
                nome_adotivo=_nome_completo(sexo) if random.random() < 0.5 else None,
                data_adocao=_data_aleatoria(2000, 2023),
                nome_mae_adotiva=_nome_completo("F"),
                nome_pai_adotivo=_nome_completo("M") if random.random() > 0.3 else None,
                mantem_nome_biologico=random.choice([True, False]),
            ))
            stats["adocao"] += 1

        # ── ALTERAÇÃO DE NOME (~10%) ──────────────────────────────────
        if idade > 18 and random.random() < 0.1:
            nome_novo = _nome_completo(sexo)
            chain.add_event(EventType.ALTERACAO_NOME.value, EventFactory.alteracao_nome(
                cpf=cpf,
                nome_anterior=nome,
                nome_novo=nome_novo,
                data_alteracao=_data_aleatoria(2010, 2024),
                motivo=random.choice(["Casamento", "Pedido próprio", "Correção", "Adoção"]),
            ))
            stats["alteracao_nome"] += 1

        # ── DESVINCULAÇÃO (~3% dos adultos) ───────────────────────────
        if idade > 18 and random.random() < 0.03:
            tipo_vinc = random.choice(["MATERNA", "PATerna"])
            if tipo_vinc == "MATERNA":
                chain.add_event(EventType.DISVINC_MATERNA.value, EventFactory.disvinculacao_materna(
                    cpf=cpf,
                    data_disvinculacao=_data_aleatoria(2010, 2024),
                    motivo=random.choice(["Abandono", "Violência", "Irreconhecimento", "Reconhecimento tardio"]),
                ))
            else:
                chain.add_event(EventType.DISVINC_PATerna.value, EventFactory.disvinculacao_paterna(
                    cpf=cpf,
                    data_disvinculacao=_data_aleatoria(2010, 2024),
                    motivo=random.choice(["Abandono", "Negativa de paternidade", "Reconhecimento tardio"]),
                ))
            stats["disvinculacao"] += 1

        # ── CASAMENTO (idade > 18, ~60%) ─────────────────────────────
        if idade > 18 and random.random() < 0.6:
            conjuge_sexo = "F" if sexo == "M" else "M"
            cpf_conjuge = _cpf_existe(cpfs_usados)
            nome_conjuge = _nome_completo(conjuge_sexo)
            data_casamento = _data_aleatoria(2000, 2024)

            chain.add_event(EventType.CASAMENTO.value, EventFactory.casamento(
                cpf=cpf,
                nome_conjuge=nome_conjuge,
                cpf_conjuge=cpf_conjuge,
                data_casamento=data_casamento,
                regime_bens=random.choice(["COMUNHAO_PARCIAL", "COMUNHAO_UNIVERSAL",
                                           "SEPARACAO_TOTAL", "PARTICIPACAO_FINAL_AQUESTOS"]),
                cidade=_cidade(),
                uf=_uf(),
            ))
            stats["casamento"] += 1
            casais.append((cpf, cpf_conjuge, nome, nome_conjuge, data_casamento))

        # ── DIVÓRCIO (~20% dos casados) ──────────────────────────────
        # (será processado depois, pois precisa de dados do casal)

        # ── ÓBITO (~15% dos idosos > 60) ─────────────────────────────
        if idade > 60 and random.random() < 0.15:
            chain.add_event(EventType.OBITO.value, EventFactory.obito(
                cpf=cpf,
                data_obito=_data_aleatoria(2018, 2025),
                cidade_obito=_cidade(),
                uf_obito=_uf(),
                causa_morte=random.choice([
                    "Parada cardíaca", "Câncer", "AVC", "Insuficiência respiratória",
                    "COVID-19", "Causas naturais", "Não informada",
                ]),
            ))
            stats["obito"] += 1

        chains[cpf] = chain
        pf_chains_info.append({
            "cpf": cpf,
            "nome": nome,
            "sexo": sexo,
            "idade": idade,
            "uf": uf_nasc,
            "cidade": cidade_nasc,
        })

    # ── Processar divórcios ────────────────────────────────────────────
    for cpf1, cpf2, nome1, nome2, data_cas in casais:
        if random.random() < 0.2:  # 20% dos casais se divorciam
            # Divórcio em pelo menos um dos cônjuges
            for cpf in [cpf1, cpf2]:
                if cpf in chains:
                    chain = chains[cpf]
                    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
                    if not ja_obito:
                        try:
                            # Data de divórcio deve ser posterior ao casamento
                            ano_cas = int(data_cas.split("/")[2])
                            chain.add_event(EventType.DIVORCIO.value, EventFactory.divorcio(
                                cpf=cpf,
                                data_divorcio=_data_aleatoria(ano_cas + 1, 2025),
                                tipo=random.choice(["CONSENSUAL", "JUDICIAL"]),
                                guarda_filhos=random.choice([None, "MATERNA", "PATerna", "COMPARTILHADA"]),
                                pensao_alimenticia=random.choice([True, False]),
                            ))
                            stats["divorcio"] += 1
                        except (ValueError, Exception):
                            pass  # Ignorar se bloqueado por óbito

    # ── Salvar no banco ────────────────────────────────────────────────
    for cpf, chain in chains.items():
        chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
        db.save_chain(cpf, chain.difficulty, chain_data)

    print(f"\n  ✅ {len(chains)} cadeias PF criadas.")
    for evt, count in sorted(stats.items()):
        print(f"     {evt}: {count}")

    return chains, pf_chains_info


# ═══════════════════════════════════════════════════════════════════════
#  FASE 2: CRIAR BLOCKCHAINS IM (300 imóveis)
# ═══════════════════════════════════════════════════════════════════════

def gerar_im(db: Database, pf_chains: dict, pf_info: list) -> tuple[dict, list]:
    """Gera 300 cadeias de IM com eventos variados."""
    print(f"\n{'='*60}")
    print(f"  FASE 2: Gerando {NUM_IM} cadastros de IMÓVEIS")
    print(f"{'='*60}")

    im_chains = {}
    matriculas_usadas = set()
    cross_im = CrossChainManager()
    im_info = []  # Para cross-chain

    stats = {"terreno": 0, "construcao": 0, "demolicao": 0, "reforma": 0,
             "compra_venda": 0, "doacao": 0, "heranca": 0, "garantia": 0,
             "leilao": 0, "certidao": 0, "iptu": 0, "zoneamento": 0}

    # Lista de CPFs disponíveis para uso em eventos
    cpfs_pfs = list(pf_chains.keys())

    for i in range(NUM_IM):
        matricula = f"MAT-{random.randint(100000, 999999)}-{random.choice(string.ascii_uppercase)}"
        while matricula in matriculas_usadas:
            matricula = f"MAT-{random.randint(100000, 999999)}-{random.choice(string.ascii_uppercase)}"
        matriculas_usadas.add(matricula)

        uf = _uf()
        cidade = _cidade(uf)
        area_terreno = round(random.uniform(100, 5000), 2)
        proprietarios_iniciais = []

        # 1-3 proprietários iniciais
        num_proprietarios = random.randint(1, 3)
        proprietarios_cpf = []
        for _ in range(num_proprietarios):
            cpf_proprietario = random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.3 else _cpf_aleatorio()
            proprietarios_cpf.append(cpf_proprietario)
            proprietarios_iniciais.append({
                "cpf": cpf_proprietario,
                "nome": _nome_completo(),
                "participacao": round(100 / num_proprietarios, 1),
                "origem": "CADASTRO_INICIAL",
            })

        chain = PropertyChain(difficulty=DIFFICULTY)

        # ── TERRENO (genesis) ──────────────────────────────────────────
        dados = PropertyEventFactory.terreno(
            matricula=matricula,
            endereco_logradouro=_rua(),
            endereco_bairro=_bairro(),
            endereco_cidade=cidade,
            endereco_uf=uf,
            endereco_cep=_cep(),
            lat=round(random.uniform(-33.0, 5.0), 6),
            lon=round(random.uniform(-74.0, -35.0), 6),
            area_terreno_m2=area_terreno,
            metragem_frente=round(random.uniform(8, 50), 2),
            metragem_fundo=round(random.uniform(8, 50), 2),
            metragem_lado_esq=round(random.uniform(10, 80), 2),
            metragem_lado_dir=round(random.uniform(10, 80), 2),
            zoneamento=random.choice(["ZER-1", "ZER-2", "ZC-1", "ZI-1", "ZP-1", "ZP-2"]),
            uso_permitido=random.sample(["RESIDENCIAL", "COMERCIAL", "MISTO", "INDUSTRIAL"], k=random.randint(1, 3)),
            altura_maxima=random.choice([10, 15, 20, 30, 45]),
            taxa_ocupacao=round(random.uniform(0.3, 0.8), 2),
            cacau_permitido=round(random.uniform(1.0, 5.0), 2),
            codigo_iptu=f"IPTU-{random.randint(1000000, 9999999)}",
            proprietarios=proprietarios_iniciais,
        )
        genesis = chain.create_genesis(dados)
        stats["terreno"] += 1

        # ── CONSTRUÇÃO (~30%) ─────────────────────────────────────────
        if random.random() < 0.3:
            area_construida = round(random.uniform(50, area_terreno * 0.6), 2)
            chain.add_event(PropertyEventType.CONSTRUCAO.value, PropertyEventFactory.construcao(
                matricula=matricula,
                descricao=random.choice([
                    "Casa térrea de 3 quartos", "Edifício residencial de 10 andares",
                    "Condomínio comercial", "Galpão industrial", "Sobrado de 2 pavimentos",
                    "Loja comercial", "Restaurante", "Escritório",
                ]),
                area_construida_m2=area_construida,
                tipo_construcao=random.choice(["RESIDENCIAL", "COMERCIAL", "MISTO", "INDUSTRIAL"]),
                pavimentos=random.randint(1, 10),
                data_inicio=_data_aleatoria(2015, 2022),
                data_fim=_data_aleatoria(2016, 2024),
                responsavel_tecnico=f"Eng. {_nome_completo()}",
                CRECI=f"CRECI-{random.randint(10000, 99999)}",
                alvara_numero=f"ALV-{random.randint(1000, 9999)}",
            ))
            stats["construcao"] += 1

            # ── DEMOLIÇÃO (~10% dos construídos) ──────────────────────
            if random.random() < 0.1:
                chain.add_event(PropertyEventType.DEMOLICAO.value, PropertyEventFactory.demolicao(
                    matricula=matricula,
                    descricao="Demolição de edificação antiga",
                    area_demolida_m2=round(area_construida * random.uniform(0.3, 1.0), 2),
                    motivo=random.choice(["Reforma total", "Risco de desabamento", "Novo projeto"]),
                    data_demolicao=_data_aleatoria(2020, 2024),
                    responsavel_tecnico=f"Eng. {_nome_completo()}",
                ))
                stats["demolicao"] += 1

            # ── REFORMA (~25% dos construídos) ────────────────────────
            if random.random() < 0.25:
                tipo_reforma = random.choice(["AMPLIACAO", "REDUCAO"])
                area_anterior = area_construida
                if tipo_reforma == "AMPLIACAO":
                    area_nova = round(area_anterior * random.uniform(1.1, 1.5), 2)
                else:
                    area_nova = round(area_anterior * random.uniform(0.6, 0.9), 2)

                chain.add_event(PropertyEventType.REFORMA.value, PropertyEventFactory.reforma(
                    matricula=matricula,
                    descricao=f"Reforma de {tipo_reforma.lower()}",
                    tipo=tipo_reforma,
                    area_anterior_m2=area_anterior,
                    area_nova_m2=area_nova,
                    data_inicio=_data_aleatoria(2020, 2024),
                    data_fim=_data_aleatoria(2021, 2025),
                    responsavel_tecnico=f"Arq. {_nome_completo()}",
                    alvara_numero=f"ALV-R-{random.randint(1000, 9999)}",
                ))
                stats["reforma"] += 1

        # ── CERTIDÃO (~20%) ───────────────────────────────────────────
        if random.random() < 0.2:
            chain.add_event(PropertyEventType.CERTIDAO.value, PropertyEventFactory.certidao(
                matricula=matricula,
                tipo_certidao=random.choice(["NEGATIVA", "POSITIVA", "SITUACAO_FISCAL"]),
                data_emissao=_data_aleatoria(2020, 2025),
                numero=f"CERT-{random.randint(10000, 99999)}",
                orgao_emissor=random.choice(["Cartório de Registro de Imóveis", "Prefeitura", "Receita Federal"]),
                validade=_data_aleatoria(2025, 2027),
            ))
            stats["certidao"] += 1

        # ── IPTU (~25%) ───────────────────────────────────────────────
        if random.random() < 0.25:
            chain.add_event(PropertyEventType.IPTU.value, PropertyEventFactory.iptu(
                matricula=matricula,
                codigo_iptu=f"IPTU-{random.randint(1000000, 9999999)}",
                data_atualizacao=_data_aleatoria(2020, 2025),
                valor_anterior=round(random.uniform(500, 5000), 2),
                valor_novo=round(random.uniform(500, 5000), 2),
                area_tributavel=round(area_terreno * random.uniform(0.5, 1.0), 2),
                motivo=random.choice(["Reavaliação", "Alteração de zona", "Correção monetária"]),
            ))
            stats["iptu"] += 1

        # ── ZONEAMENTO (~10%) ─────────────────────────────────────────
        if random.random() < 0.1:
            chain.add_event(PropertyEventType.ZONEAMENTO.value, PropertyEventFactory.zoneamento(
                matricula=matricula,
                zoneamento_anterior=random.choice(["ZER-1", "ZER-2", "ZC-1"]),
                zoneamento_novo=random.choice(["ZER-2", "ZC-1", "ZI-1", "ZP-1"]),
                data=_data_aleatoria(2020, 2025),
                processo_numero=f"PROC-{random.randint(100000, 999999)}",
                descricao="Alteração de zoneamento por mudança de uso do solo",
            ))
            stats["zoneamento"] += 1

        # ── GARANTIA/HIPOTECA (~20%) ──────────────────────────────────
        if random.random() < 0.2:
            banco = random.choice(_BANCOS)
            chain.add_event(PropertyEventType.GARANTIA.value, PropertyEventFactory.garantia(
                matricula=matricula,
                credor_nome=banco,
                credor_cnpj=''.join(random.choices(string.digits, k=14)),
                valor_garantia=round(random.uniform(100000, 2000000), 2),
                data_garantia=_data_aleatoria(2020, 2024),
                data_vencimento=_data_aleatoria(2025, 2035),
                tipo_garantia=random.choice(["HIPOTECARIA", "ALIENACAO_FIDUCIARIA"]),
                taxa_juros=round(random.uniform(8, 15), 2),
                prazo_meses=random.choice([120, 180, 240, 360]),
                descricao=f"Financiamento imobiliário via {banco}",
            ))
            stats["garantia"] += 1

        # ── COMPRA/VENDA (~40%) ───────────────────────────────────────
        if random.random() < 0.4:
            comprador_cpf = random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.4 else _cpf_aleatorio()
            vendedor_cpf = proprietarios_cpf[0] if proprietarios_cpf else _cpf_aleatorio()
            chain.add_event(PropertyEventType.COMPRA_VENDA.value, PropertyEventFactory.compra_venda(
                matricula=matricula,
                comprador_cpf=comprador_cpf,
                comprador_nome=_nome_completo(),
                vendedor_cpf=vendedor_cpf,
                vendedor_nome=_nome_completo(),
                valor_transacao=round(random.uniform(150000, 3000000), 2),
                data_transacao=_data_aleatoria(2018, 2024),
                escritura_numero=f"ESC-{random.randint(10000, 99999)}",
                cartorio=f"Cartório de {random.choice(['Notas', 'Registro'])} de {_cidade()}",
                regime_bens=random.choice(["", "COMUNHAO_PARCIAL", "SEPARACAO_TOTAL"]),
            ))
            stats["compra_venda"] += 1

        # ── DOAÇÃO (~10%) ─────────────────────────────────────────────
        if random.random() < 0.1:
            chain.add_event(PropertyEventType.DOACAO.value, PropertyEventFactory.doacao(
                matricula=matricula,
                donatario_cpf=random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.3 else _cpf_aleatorio(),
                donatario_nome=_nome_completo(),
                doador_cpf=proprietarios_cpf[0] if proprietarios_cpf else _cpf_aleatorio(),
                doador_nome=_nome_completo(),
                data_doacao=_data_aleatoria(2020, 2024),
                motivo=random.choice(["Doação entre familiares", "Doação para entidade", "Inventário"]),
                escritura_numero=f"ESC-D-{random.randint(10000, 99999)}",
                cartorio=f"Cartório de Notas de {_cidade()}",
            ))
            stats["doacao"] += 1

        # ── HERANÇA (~5%) ────────────────────────────────────────────
        if random.random() < 0.05:
            herdeiros = []
            for _ in range(random.randint(1, 4)):
                herdeiros.append({
                    "cpf": _cpf_aleatorio(),
                    "nome": _nome_completo(),
                    "participacao": round(100 / random.randint(2, 4), 1),
                })
            chain.add_event(PropertyEventType.HERANCA.value, PropertyEventFactory.heranca(
                matricula=matricula,
                inventariado_cpf=proprietarios_cpf[0] if proprietarios_cpf else _cpf_aleatorio(),
                inventariado_nome=_nome_completo(),
                herdeiros=herdeiros,
                data_obito=_data_aleatoria(2015, 2023),
                data_inventario=_data_aleatoria(2020, 2024),
                inventario_tipo=random.choice(["JUDICIAL", "EXTRAJUDICIAL"]),
            ))
            stats["heranca"] += 1

        # ── LEILÃO (~5%) ─────────────────────────────────────────────
        if random.random() < 0.05:
            chain.add_event(PropertyEventType.LEILAO.value, PropertyEventFactory.leilao(
                matricula=matricula,
                data_leilao=_data_aleatoria(2020, 2024),
                valor_minimo=round(random.uniform(100000, 1500000), 2),
                lance_vencedor=round(random.uniform(100000, 1500000), 2),
                vencedor_cpf=random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.3 else _cpf_aleatorio(),
                vencedor_nome=_nome_completo(),
                leiloeiro=f"Leiloeiro {_nome_completo()}",
                processo_numero=f"LEIL-{random.randint(10000, 99999)}",
                tipo=random.choice(["JUDICIAL", "EXTRAJUDICIAL"]),
            ))
            stats["leilao"] += 1

        # ── Registrar cross-chain: pessoa ↔ imóvel ────────────────────
        for cpf_prop in proprietarios_cpf:
            if cpf_prop in pf_chains:
                cross_im.register_pf(cpf_prop, pf_chains[cpf_prop])
                cross_im.register_im(matricula, chain)
                cross_im.create_reference(
                    cpf=cpf_prop,
                    matricula=matricula,
                    tipo_vinculo="PROPRIETARIO",
                )

        im_chains[matricula] = chain
        im_info.append({
            "matricula": matricula,
            "cidade": cidade,
            "uf": uf,
            "area": area_terreno,
            "proprietarios_cpf": proprietarios_cpf,
        })

    # ── Salvar no banco ────────────────────────────────────────────────
    for mat, chain in im_chains.items():
        chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
        db.save_imovel(mat, chain.difficulty, chain_data)

    print(f"\n  ✅ {len(im_chains)} cadeias IM criadas.")
    for evt, count in sorted(stats.items()):
        print(f"     {evt}: {count}")

    return im_chains, im_info, cross_im


# ═══════════════════════════════════════════════════════════════════════
#  FASE 3: CRIAR BLOCKCHAINS MO (300 veículos)
# ═══════════════════════════════════════════════════════════════════════

def gerar_mo(db: Database, pf_chains: dict, pf_info: list,
             im_chains: dict, im_info: list) -> tuple[dict, list]:
    """Gera 300 cadeias de MO com eventos variados."""
    print(f"\n{'='*60}")
    print(f"  FASE 3: Gerando {NUM_MO} cadastros de VEÍCULOS")
    print(f"{'='*60}")

    mo_chains = {}
    placas_usadas = set()
    cross_mo = CrossChainMO()
    mo_info = []

    stats = {"fabricacao": 0, "compra_venda": 0, "doacao": 0, "leilao": 0,
             "confisco": 0, "garantia": 0, "quitacao": 0, "multa": 0,
             "sinistro": 0, "revisao": 0, "troca_peca": 0, "licenciamento": 0,
             "mudanca_cor": 0, "recall": 0, "transferencia": 0}

    cpfs_pfs = list(pf_chains.keys())
    matriculas_ims = list(im_chains.keys())

    for i in range(NUM_MO):
        placa = _placa_existe(placas_usadas)
        marca = random.choice(_MARCAS_CAR)
        modelo = random.choice(_MODELOS[marca])
        ano = random.randint(2010, 2025)
        combustivel = random.choice(_COMBUSTIVEIS)
        odometro = round(random.uniform(0, 150000), 1)

        chain = VehicleChain(difficulty=DIFFICULTY)

        # ── FABRICAÇÃO (genesis) ───────────────────────────────────────
        _uf_mo = _uf()
        dados = VehicleEventFactory.fabricacao(
            placa=placa,
            renavan=_renavan(),
            chassis=_chassis(),
            marca=marca,
            modelo=modelo,
            ano_fabricacao=ano,
            ano_modelo=ano,
            cor=random.choice(_CORES),
            combustivel=combustivel,
            cilindradas=random.choice([1000, 1400, 1600, 2000, 2500, 3000]),
            potencia_cv=round(random.uniform(70, 300), 1),
            tipo_veiculo=random.choice(["AUTOMOVEL", "UTILITARIO"]),
            categoria="PARTICULAR",
            num_portas=random.choice([2, 4]),
            capacidade_passageiros=random.choice([2, 4, 5, 7]),
            fabricante_cnpj=''.join(random.choices(string.digits, k=14)),
            fabricante_nome=marca,
            fabricante_pais=random.choice(["BR", "MX", "AR", "US", "DE", "JP", "KR"]),
            motor_tipo=random.choice(["4 cilindros", "6 cilindros", "Elétrico"]),
            motor_numero=f"MOT-{random.randint(100000, 999999)}",
            carroceria_tipo=random.choice(["Hatch", "Sedan", "SUV", "Pickup", "Perua"]),
            carroceria_material="Fibra de vidro",
            freio_dianteiro="Disco ventilado",
            freio_traseiro=random.choice(["Disco", "Tambor"]),
            suspensao_dianteira="Independente McPherson",
            suspensao_traseira=random.choice(["Independente", "Eixo rígido"]),
            direcao=random.choice(["Elétrica", "Hidráulica", "Mecânica"]),
            transmissao=random.choice(["Manual", "Automática", "CVT", "DCT"]),
            lote_fabricacao=f"LOTE-{random.randint(1000, 9999)}",
            data_fabricacao=_data_aleatoria(ano, ano + 1),
            certificado_homologacao=f"HOM-{random.randint(10000, 99999)}",
            crv=f"CRV-{random.randint(100000, 999999)}",
            odometro_km=odometro,
            uf=_uf_mo,
            cidade=capital_da_uf(_uf_mo),
        )
        genesis = chain.create_genesis(dados)
        stats["fabricacao"] += 1

        # ── COMPRA/VENDA (~50% com pelo menos 1 transferência) ────────
        num_transferencias = 0
        if random.random() < 0.5:
            num_transferencias = random.randint(1, 3)
        for t in range(num_transferencias):
            comprador = random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.3 else _cpf_aleatorio()
            vendedor = random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.3 else _cpf_aleatorio()
            odometro += random.uniform(1000, 30000)
            chain.add_event(VehicleEventType.COMPRA_VENDA.value, VehicleEventFactory.compra_venda(
                placa=placa,
                comprador_cpf=comprador,
                comprador_nome=_nome_completo(),
                vendedor_cpf=vendedor,
                vendedor_nome=_nome_completo(),
                valor_transacao=round(random.uniform(15000, 150000), 2),
                data_transacao=_data_aleatoria(max(ano + 1, 2015), 2025),
                odometro_km=round(odometro, 1),
                notafiscal_numero=f"NF-{random.randint(100000, 999999)}",
                cartorio=f"Cartório de {_cidade()}",
            ))
            stats["compra_venda"] += 1

        # ── DOAÇÃO (~10%) ─────────────────────────────────────────────
        if random.random() < 0.1:
            chain.add_event(VehicleEventType.DOACAO.value, VehicleEventFactory.doacao(
                placa=placa,
                donatario_cpf=random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.3 else _cpf_aleatorio(),
                donatario_nome=_nome_completo(),
                doador_cpf=random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.3 else _cpf_aleatorio(),
                doador_nome=_nome_completo(),
                data_doacao=_data_aleatoria(ano + 1, 2024),
                motivo=random.choice(["Doação familiar", "Doação para instituição", "Herança"]),
                escritura_numero=f"ESC-V-{random.randint(10000, 99999)}",
                cartorio=f"Cartório de {_cidade()}",
                odometro_km=round(odometro, 1),
            ))
            stats["doacao"] += 1

        # ── LEILÃO (~5%) ─────────────────────────────────────────────
        if random.random() < 0.05:
            lance = round(random.uniform(10000, 100000), 2)
            chain.add_event(VehicleEventType.LEILAO.value, VehicleEventFactory.leilao(
                placa=placa,
                data_leilao=_data_aleatoria(2020, 2024),
                valor_minimo=round(lance * 0.7, 2),
                lance_vencedor=lance,
                vencedor_cpf=random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.3 else _cpf_aleatorio(),
                vencedor_nome=_nome_completo(),
                leiloeiro=f"Leiloeiro {_nome_completo()}",
                processo_numero=f"LEIL-V-{random.randint(10000, 99999)}",
                tipo=random.choice(["JUDICIAL", "EXTRAJUDICIAL"]),
                odometro_km=round(odometro, 1),
            ))
            stats["leilao"] += 1

        # ── CONFISCO (~3%) ────────────────────────────────────────────
        if random.random() < 0.03:
            chain.add_event(VehicleEventType.CONFISCO.value, VehicleEventFactory.confisco(
                placa=placa,
                autoridade=random.choice(_ORGAOS),
                processo_numero=f"CONF-{random.randint(10000, 99999)}",
                data_confisco=_data_aleatoria(2020, 2024),
                motivo=random.choice(["Tráfico", "Evasão de divisas", "Crime organizado"]),
                destino="Depósito Policial",
            ))
            stats["confisco"] += 1

        # ── GARANTIA/EMPRÉSTIMO (~15%) ────────────────────────────────
        if random.random() < 0.15:
            banco = random.choice(_BANCOS)
            chain.add_event(VehicleEventType.GARANTIA_EMPRESTIMO.value, VehicleEventFactory.garantia_emprestimo(
                placa=placa,
                credor_nome=banco,
                credor_cnpj=''.join(random.choices(string.digits, k=14)),
                valor_emprestimo=round(random.uniform(5000, 80000), 2),
                data_garantia=_data_aleatoria(2020, 2024),
                data_vencimento=_data_aleatoria(2025, 2030),
                taxa_juros=round(random.uniform(12, 25), 2),
                parcelas=random.choice([12, 24, 36, 48, 60]),
                tipo_garantia=random.choice(["ALIENACAO_FIDUCIARIA", "PENHOR"]),
                descricao=f"Empréstimo pessoal com garantia de veículo via {banco}",
            ))
            stats["garantia"] += 1

            # ── QUITAÇÃO (~30% das garantias) ─────────────────────────
            if random.random() < 0.3:
                chain.add_event(VehicleEventType.QUITACAO_GARANTIA.value, VehicleEventFactory.quitacao_garantia(
                    placa=placa,
                    garantia_index=0,
                    data_quitacao=_data_aleatoria(2023, 2025),
                    valor_pago=round(random.uniform(5000, 80000), 2),
                    descricao="Quitação antecipada",
                ))
                stats["quitacao"] += 1

        # ── MULTA (~30%) ──────────────────────────────────────────────
        if random.random() < 0.3:
            num_multas = random.randint(1, 5)
            for _ in range(num_multas):
                chain.add_event(VehicleEventType.MULTA.value, VehicleEventFactory.multa(
                    placa=placa,
                    numero_auto=f"AUTO-{random.randint(100000, 999999)}",
                    data_infracao=_data_aleatoria(2020, 2025),
                    local_logradouro=_rua(),
                    local_cidade=_cidade(),
                    local_uf=_uf(),
                    enquadramento=random.choice([
                        "Art. 165 - Ultrapassar sinal vermelho",
                        "Art. 163 - Excesso de velocidade",
                        "Art. 166 - Estacionamento irregular",
                        "Art. 171 - Avançar sinal de parada",
                        "Art. 175 - Falta de cinto de segurança",
                        "Art. 218 - Uso de celular ao volante",
                    ]),
                    pontos=random.randint(1, 7),
                    valor_multa=round(random.uniform(80, 3000), 2),
                    orgao_autuador=random.choice(_ORGAOS),
                    condutor_cpf=random.choice(cpfs_pfs) if cpfs_pfs and random.random() < 0.3 else "",
                    condutor_nome=_nome_completo() if random.random() < 0.3 else "",
                ))
                stats["multa"] += 1

        # ── SINISTRO (~10%) ───────────────────────────────────────────
        if random.random() < 0.1:
            chain.add_event(VehicleEventType.SINISTRO.value, VehicleEventFactory.sinistro(
                placa=placa,
                data_sinistro=_data_aleatoria(2020, 2025),
                tipo=random.choice(["COLISAO", "ATROPELAMENTO", "INCENDIO", "ALAGAMENTO", "OUTRO"]),
                bo_numero=f"BO-{random.randint(100000, 999999)}",
                delegacia=f"Delegacia de {_cidade()}",
                seguradora_nome=random.choice(["Porto Seguro", "Bradesco Seguros", "SulAmérica", "Allianz"]),
                seguradora_cnpj=''.join(random.choices(string.digits, k=14)),
                seguradora_apolice=f"APOL-{random.randint(100000, 999999)}",
                valor_dano=round(random.uniform(2000, 80000), 2),
                laudo_perito=f"Perito {_nome_completo()}",
                oficina_responsavel=random.choice(_OFICINAS),
                pecas_danificadas=random.sample(
                    ["para-choque", "capô", "porta dianteira", "para-lama", "farol",
                     "espelho", "teto", "porta-malas", "Grade", "Aleta"],
                    k=random.randint(1, 4),
                ),
                descricao=random.choice([
                    "Colisão traseira em via urbana",
                    "Atropelamento de animal",
                    "Incêncio no motor",
                    "Alagamento durante chuva forte",
                    "Colisão lateral em estacionamento",
                ]),
            ))
            stats["sinistro"] += 1

        # ── REVISÃO (~40%) ────────────────────────────────────────────
        if random.random() < 0.4:
            num_revisoes = random.randint(1, 3)
            for r in range(num_revisoes):
                chain.add_event(VehicleEventType.REVISAO.value, {
                    "evento_tipo": "REVISAO",
                    "placa": placa,
                    "data_revisao": _data_aleatoria(ano + 1, 2025),
                    "tipo_revisao": random.choice(["PREVENTIVA", "CORRETIVA", "PROGRAMADA"]),
                    "km_revisao": round(odometro + r * 10000, 1),
                    "oficina": random.choice(_OFICINAS),
                    "itens_trocados": random.sample(
                        ["Óleo do motor", "Filtro de ar", "Filtro de óleo", "Pastilhas de freio",
                         "Correia dentada", "Velas de ignição", "Fluido de freio", "Bateria"],
                        k=random.randint(1, 4),
                    ),
                    "valor_total": round(random.uniform(200, 3000), 2),
                    "descricao": f"Revisão de {ano + r * 20}km",
                })
                stats["revisao"] += 1

        # ── TROCA DE PEÇA (~20%) ─────────────────────────────────────
        if random.random() < 0.2:
            chain.add_event(VehicleEventType.TROCA_PECA.value, {
                "evento_tipo": "TROCA_PECA",
                "placa": placa,
                "data_troca": _data_aleatoria(2020, 2025),
                "peca_original": random.choice(["Motor", "Câmbio", "Alternador", "Compressor de ar", "Injetor"]),
                "peca_nova": random.choice(["Motor", "Câmbio", "Alternador", "Compressor de ar", "Injetor"]),
                "fabricante_peca": random.choice(["Original", "Paralela", "Recondicionada"]),
                "numero_serie_peca": f"PEC-{random.randint(100000, 999999)}",
                "oficina": random.choice(_OFICINAS),
                "valor_peca": round(random.uniform(500, 15000), 2),
                "mao_de_obra": round(random.uniform(100, 3000), 2),
            })
            stats["troca_peca"] += 1

        # ── LICENCIAMENTO (~30%) ──────────────────────────────────────
        if random.random() < 0.3:
            chain.add_event(VehicleEventType.LICENCIAMENTO.value, {
                "evento_tipo": "LICENCIAMENTO",
                "placa": placa,
                "ano_licenciamento": ano + random.randint(1, 5),
                "data_emissao": _data_aleatoria(2020, 2025),
                "ipva_pago": random.choice([True, False]),
                "valor_ipva": round(random.uniform(500, 8000), 2),
                "taxa_licenciamento": round(random.uniform(100, 400), 2),
                "debitos_quitados": random.choice([True, False]),
                "orgao": random.choice(_ORGAOS),
                "documento_numero": f"LIC-{random.randint(100000, 999999)}",
            })
            stats["licenciamento"] += 1

        # ── MUDANÇA DE COR (~5%) ──────────────────────────────────────
        if random.random() < 0.05:
            chain.add_event(VehicleEventType.MUDANCA_COR.value, {
                "evento_tipo": "MUDANCA_COR",
                "placa": placa,
                "cor_anterior": random.choice(_CORES),
                "cor_nova": random.choice(_CORES),
                "data_mudanca": _data_aleatoria(2020, 2024),
                "processo_numero": f"COR-{random.randint(10000, 99999)}",
                "orgao": random.choice(_ORGAOS),
                "descricao": "Alteração de cor de fábrica para cor sob encomenda",
            })
            stats["mudanca_cor"] += 1

        # ── RECALL (~5%) ──────────────────────────────────────────────
        if random.random() < 0.05:
            chain.add_event(VehicleEventType.RECALL_DE_FABRICA.value, {
                "evento_tipo": "RECALL_DE_FABRICA",
                "placa": placa,
                "numero_recall": f"REC-{random.randint(10000, 99999)}",
                "fabricante": marca,
                "componente": random.choice([
                    "Sistema de freios", "Airbag", "Câmbio automático",
                    "Direção elétrica", "Sistema de injeção", "Correia dentada",
                ]),
                "descricao": random.choice([
                    "Possível falha no sistema de freios ABS",
                    "Substituição preventiva do módulo de airbag",
                    "Ajuste no software do câmbio automático",
                    "Verificação da direção elétrica",
                ]),
                "data_notificacao": _data_aleatoria(2020, 2024),
                "data_conclusao": _data_aleatoria(2021, 2025) if random.random() < 0.7 else "",
                "concessionaria": f"Concessionária {marca} de {_cidade()}",
                "status": random.choice(["CONCLUIDO", "PENDENTE", "EM_EXECUCAO"]),
            })
            stats["recall"] += 1

        # ── Registrar cross-chain: pessoa ↔ veículo ────────────────────
        if cpfs_pfs and random.random() < 0.3:
            cpf_dono = random.choice(cpfs_pfs)
            cross_mo.register_pf(cpf_dono, pf_chains[cpf_dono])
            cross_mo.register_mo(placa, chain)
            cross_mo.create_reference(
                origem_tipo="PF",
                origem_id=cpf_dono,
                destino_tipo="MO",
                destino_id=placa,
                tipo_vinculo="PROPRIETARIO",
            )

        # ── Registrar cross-chain: veículo ↔ imóvel (garagem) ─────────
        if matriculas_ims and random.random() < 0.1:
            mat = random.choice(matriculas_ims)
            cross_mo.register_im(mat, im_chains[mat])
            cross_mo.register_mo(placa, chain)
            cross_mo.create_reference(
                origem_tipo="IM",
                origem_id=mat,
                destino_tipo="MO",
                destino_id=placa,
                tipo_vinculo="GARAGEM",
            )

        mo_chains[placa] = chain
        mo_info.append({
            "placa": placa,
            "marca": marca,
            "modelo": modelo,
            "ano": ano,
        })

    # ── Salvar no banco ────────────────────────────────────────────────
    for placa, chain in mo_chains.items():
        chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
        db.save_veiculo(placa, chain.difficulty, chain_data)

    print(f"\n  ✅ {len(mo_chains)} cadeias MO criadas.")
    for evt, count in sorted(stats.items()):
        print(f"     {evt}: {count}")

    return mo_chains, mo_info, cross_mo


# ═══════════════════════════════════════════════════════════════════════
#  FASE 4: VALIDAÇÃO E RELATÓRIO FINAL
# ═══════════════════════════════════════════════════════════════════════

def validar_e_reportar(pf_chains, im_chains, mo_chains, cross_im, cross_mo, db=None):
    """Valida todas as cadeias e gera relatório final."""
    print(f"\n{'='*60}")
    print(f"  FASE 4: VALIDAÇÃO E RELATÓRIO")
    print(f"{'='*60}")

    # Validar PF
    pf_validas = 0
    pf_invalidas = 0
    for cpf, chain in pf_chains.items():
        valida, _ = chain.validate(require_signatures=False)
        if valida:
            pf_validas += 1
        else:
            pf_invalidas += 1

    # Validar IM
    im_validas = 0
    im_invalidas = 0
    for mat, chain in im_chains.items():
        valida, _ = chain.validate(require_signatures=False)
        if valida:
            im_validas += 1
        else:
            im_invalidas += 1

    # Validar MO
    mo_validas = 0
    mo_invalidas = 0
    for placa, chain in mo_chains.items():
        valida, _ = chain.validate(require_signatures=False)
        if valida:
            mo_validas += 1
        else:
            mo_invalidas += 1

    # Estatísticas cross-chain
    stats_im = cross_im.stats()
    stats_mo = cross_mo.stats()

    # Total de blocos
    total_blocos_pf = sum(len(c) for c in pf_chains.values())
    total_blocos_im = sum(len(c) for c in im_chains.values())
    total_blocos_mo = sum(len(c) for c in mo_chains.values())

    print(f"""
  ┌─────────────────────────────────────────────────────┐
  │           RELATÓRIO FINAL DE GERAÇÃO                │
  ├─────────────────────────────────────────────────────┤
  │                                                     │
  │  📋 PESSOAS FÍSICAS (PF)                           │
  │     Cadastros: {len(pf_chains):>6}                            │
  │     Válidos:   {pf_validas:>6}  |  Inválidos: {pf_invalidas:<6}    │
  │     Blocos:    {total_blocos_pf:>6}                            │
  │                                                     │
  │  🏠 IMÓVEIS (IM)                                   │
  │     Cadastros: {len(im_chains):>6}                            │
  │     Válidos:   {im_validas:>6}  |  Inválidos: {im_invalidas:<6}    │
  │     Blocos:    {total_blocos_im:>6}                            │
  │                                                     │
  │  🚗 VEÍCULOS (MO)                                  │
  │     Cadastros: {len(mo_chains):>6}                            │
  │     Válidos:   {mo_validas:>6}  |  Inválidos: {mo_invalidas:<6}    │
  │     Blocos:    {total_blocos_mo:>6}                            │
  │                                                     │
  │  🔗 CROSS-CHAIN                                    │
  │     PF ↔ IM:  {stats_im['total_referencias']:>6} referências              │
  │     PF/MO/IM: {stats_mo['total_referencias']:>6} referências              │
  │     Vínculos ativos: {stats_im['referencias_ativas'] + stats_mo['referencias_ativas']:>6}                  │
  │                                                     │
  │  📊 TOTAL                                          │
  │     Cadastros: {len(pf_chains) + len(im_chains) + len(mo_chains):>6}                            │
  │     Blocos:    {total_blocos_pf + total_blocos_im + total_blocos_mo:>6}                            │
  │     Refs cross: {stats_im['total_referencias'] + stats_mo['total_referencias']:>5}                            │
  └─────────────────────────────────────────────────────┘
""")

    # Salvar cross-chain em JSON (referencia) + SQLite centralizado
    cross_im.save_to_file("cross_chain_im.json")
    cross_mo.save_to_file("cross_chain_mo.json")
    print("  💾 Cross-chain IM salvo em: cross_chain_im.json")
    print("  💾 Cross-chain MO salvo em: cross_chain_mo.json")
    db.clear_references("im")
    for ref in getattr(cross_im, "_references", []):
        db.save_reference("im", ref.to_dict())
    db.clear_references("mo")
    for ref in getattr(cross_mo, "_references", []):
        db.save_reference("mo", ref.to_dict())
    refs_im = len(db.load_all_references("im"))
    refs_mo = len(db.load_all_references("mo"))
    print(f"  🗄️  Cross-chain no SQLite: IM={refs_im} | MO={refs_mo} referencias")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   GERADOR MASSIVO — 300 Cadastros por Blockchain           ║")
    print("║   PF (Pessoas) + IM (Imóveis) + MO (Veículos)              ║")
    print("║   + Cross-Chain integrado                                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    t0 = time.time()

    # Inicializar banco centralizado (<projeto>/database/blockchain.db)
    db = Database()

    # Fase 1: PF
    pf_chains, pf_info = gerar_pf(db)

    # Fase 2: IM
    im_chains, im_info, cross_im = gerar_im(db, pf_chains, pf_info)

    # Fase 3: MO
    mo_chains, mo_info, cross_mo = gerar_mo(db, pf_chains, pf_info, im_chains, im_info)

    # Fase 4: Validação
    validar_e_reportar(pf_chains, im_chains, mo_chains, cross_im, cross_mo, db)

    elapsed = time.time() - t0
    print(f"  ⏱  Tempo total: {elapsed:.1f}s")
    print(f"  ✅ Concluído! Acesse http://localhost:8000 para ver os dados.\n")


if __name__ == "__main__":
    main()
