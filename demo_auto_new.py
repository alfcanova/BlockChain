#!/usr/bin/env python3
"""
demo_auto_new.py — Demonstração automática das 4 novas blockchains:
  CO (Empresas), EM (Embarcações), AC (Aeronaves), AN (Animais)

Executa cenários completos com assinaturas ECDSA sem input interativo.

Executa com: PYTHONIOENCODING=utf-8 python demo_auto_new.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blockchain_pf import generate_authority_keypair
from blockchain_pf.database import Database
from blockchain_co import CompanyChain, CompanyEventFactory, CompanyEventType
from blockchain_em import VesselChain, VesselEventFactory, VesselEventType
from blockchain_ac import AircraftChain, AircraftEventFactory, AircraftEventType
from blockchain_an import AnimalChain, AnimalEventFactory, AnimalEventType


def linha(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


def demo_co():
    """Demonstração da Blockchain de Empresas (CO)."""
    linha("BLOCKCHAIN CO — EMPRESAS (CNPJ)")
    print("  Cadeia de blocos para vida de empresas\n")

    # Gerar chaves
    keypair_jucesp = generate_authority_keypair("JUCESP - Junta Comercial de SP")
    keypair_receita = generate_authority_keypair("Receita Federal")

    # Criar cadeia
    chain = CompanyChain(difficulty=2)
    chain.set_signer(keypair_jucesp)

    # 1. Constituição
    linha("1. CONSTITUICAO — Bloco Genesis")
    dados = CompanyEventFactory.constituicao(
        cnpj="12345678000190",
        razao_social="TechSolutions Inovacao LTDA",
        nome_fantasia="TechSol",
        data_constituicao="01/01/2020",
        tipo_empresa="LTDA",
        porte="ME",
        capital_social=50000.0,
        natureza_juridica="2062",
        atividade_principal="6201501",
        endereco_sede={"logradouro": "Av. Paulista, 1000", "cidade": "Sao Paulo", "uf": "SP"},
        responsavel_cpf="12345678901",
        responsavel_nome="Joao Silva",
        uf="SP",
        cidade="Sao Paulo",
    )
    genesis = chain.create_genesis(dados)
    print(f"  Hash: {genesis.hash[:20]}...")
    print(f"  Assinado por: {genesis.signature['signer_label']}")

    # 2. Adição de Sócio
    linha("2. ADICAO DE SOCIO")
    dados_socio = CompanyEventFactory.adicao_socio(
        cnpj="12345678000190",
        socio_cpf="98765432100",
        socio_nome="Maria Santos",
        participacao=30.0,
        data_entrada="15/06/2021",
    )
    block = chain.add_event(CompanyEventType.ADICAO_SOCIO.value, dados_socio)
    print(f"  Bloco #{block.index} — Hash: {block.hash[:20]}...")
    print(f"  Socia adicionada: Maria Santos (30%)")

    # 3. Mudança de Capital
    linha("3. MUDANCA DE CAPITAL")
    dados_capital = CompanyEventFactory.mudanca_capital(
        cnpj="12345678000190",
        capital_anterior=50000.0,
        capital_novo=150000.0,
        data_mudanca="01/01/2023",
        descricao="Aporte dos socios",
    )
    block = chain.add_event(CompanyEventType.MUDANCA_CAPITAL.value, dados_capital)
    print(f"  Bloco #{block.index} — Capital: R$ 50.000 -> R$ 150.000")

    # 4. Certidão Negativa
    linha("4. CERTIDAO NEGATIVA")
    dados_cert = CompanyEventFactory.certidao(
        cnpj="12345678000190",
        tipo_certidao="NEGATIVA",
        numero="CND-2024-001234",
        data_emissao="01/03/2024",
        orgao_emissor="Receita Federal",
    )
    block = chain.add_event(CompanyEventType.CERTIDAO.value, dados_cert)
    print(f"  Bloco #{block.index} — Certidao emitida")

    # 5. Garantia
    linha("5. GARANTIA BANCARIA")
    dados_garantia = CompanyEventFactory.garantia(
        cnpj="12345678000190",
        credor_nome="Banco do Brasil",
        credor_cnpj="00000000000191",
        valor_garantia=100000.0,
        data_garantia="01/06/2024",
        data_vencimento="01/06/2029",
        tipo_garantia="FIANCA",
    )
    block = chain.add_event(CompanyEventType.GARANTIA.value, dados_garantia)
    print(f"  Bloco #{block.index} — Garantia de R$ 100.000 registrada")

    # 6. Validar
    linha("6. VALIDACAO")
    ok, msg = chain.validate(require_signatures=True)
    print(f"  {msg}")

    # Timeline
    print("\n  Timeline:")
    for ev in chain.get_historico_completo():
        print(f"    [{ev['indice']:02d}] {ev['tipo']} ({ev['data_registro']})")

    # Estado
    estado = chain.get_estado_atual()
    print(f"\n  Estado: {estado['situacao_cadastral']}")
    print(f"  Socios: {len(estado['socios'])}")
    print(f"  Capital: R$ {estado['capital_social']:,.2f}")

    chain.save_to_file("demo_output/co_12345678000190.json")
    print(f"\n  Cadeia salva em demo_output/co_12345678000190.json")
    return chain


def demo_em():
    """Demonstração da Blockchain de Embarcações (EM)."""
    linha("BLOCKCHAIN EMBARCACOES (EM)")
    print("  Cadeia de blocos para vida de embarcacoes\n")

    keypair_capitania = generate_authority_keypair("Capitania dos Portos - SP")

    chain = VesselChain(difficulty=2)
    chain.set_signer(keypair_capitania)

    # 1. Construção
    linha("1. CONSTRUCAO — Bloco Genesis")
    dados = VesselEventFactory.construcao(
        registro_nr="NR-2024-001",
        nome_embarcacao="Estrela do Mar",
        tipo_embarcacao="Iate",
        porte="MEDIO",
        comprimento_m=12.5,
        beam_m=4.0,
        pontal_m=2.0,
        calado_m=1.2,
        deslocamento_ton=8.5,
        casco_material="Fibra",
        motorizacao="Inboard",
        motor_potencia_cv=300,
        motor_tipo="Diesel",
        motor_fabricante="Yanmar",
        ano_construcao=2023,
        estaleiro="Estaleiro ABC",
        porto_registro="Santos",
        capacidade_tripulacao=2,
        capacidade_passageiros=8,
        uf="SP",
        cidade="Santos",
    )
    genesis = chain.create_genesis(dados)
    print(f"  Hash: {genesis.hash[:20]}...")
    print(f"  Embarcacao: {dados['nome_embarcacao']} ({dados['tipo_embarcacao']})")

    # 2. Compra/Venda
    linha("2. COMPRA/VENDA")
    dados_venda = VesselEventFactory.compra_venda(
        registro_nr="NR-2024-001",
        comprador_cpf="98765432100",
        comprador_nome="Pedro Oliveira",
        vendedor_cpf="12345678901",
        vendedor_nome="Joao Silva",
        valor_transacao=250000.0,
        data_transacao="01/03/2024",
    )
    block = chain.add_event(VesselEventType.COMPRA_VENDA.value, dados_venda)
    print(f"  Bloco #{block.index} — Venda por R$ 250.000")

    # 3. Revisão
    linha("3. REVISAO")
    dados_rev = VesselEventFactory.revisao(
        registro_nr="NR-2024-001",
        data_revisao="15/06/2024",
        oficina="Marina Santos",
        tipo_revisao="PREVENTIVA",
        itens_revisados=["Motor", "Casco", "Eletrica", "Sonar"],
        proxima_revisao="15/12/2024",
        valor_total=8500.0,
    )
    block = chain.add_event(VesselEventType.REVISAO.value, dados_rev)
    print(f"  Bloco #{block.index} — Revisao concluida (R$ 8.500)")

    # 4. Inspeção
    linha("4. INSPECAO DE SEGURANCA")
    dados_insp = VesselEventFactory.inspecao(
        registro_nr="NR-2024-001",
        data_inspecao="01/09/2024",
        orgao_inspecao="Capitania dos Portos",
        resultado="APROVADA",
        certificado_numero="INS-2024-001",
    )
    block = chain.add_event(VesselEventType.INSPECAO.value, dados_insp)
    print(f"  Bloco #{block.index} — Inspecao APROVADA")

    # 5. Seguro
    linha("5. SEGURO")
    dados_seg = VesselEventFactory.seguro(
        registro_nr="NR-2024-001",
        seguradora_nome="Porto Seguro",
        seguradora_cnpj="61198164000123",
        apolice_numero="AP-2024-5678",
        data_inicio="01/01/2024",
        data_fim="01/01/2025",
        valor_segurado=300000.0,
        tipo_seguro="CASCO_E_RESPOSTA",
    )
    block = chain.add_event(VesselEventType.SEGURO.value, dados_seg)
    print(f"  Bloco #{block.index} — Seguro contratado (R$ 300.000)")

    # Validar
    linha("VALIDACAO")
    ok, msg = chain.validate(require_signatures=True)
    print(f"  {msg}")

    estado = chain.get_estado_atual()
    print(f"  Nome: {estado['nome_embarcacao']}")
    print(f"  Situacao: {estado['situacao']}")
    print(f"  Proprietarios: {len(estado['proprietarios'])}")

    chain.save_to_file("demo_output/em_NR-2024-001.json")
    print(f"\n  Cadeia salva em demo_output/em_NR-2024-001.json")
    return chain


def demo_ac():
    """Demonstração da Blockchain de Aeronaves (AC)."""
    linha("BLOCKCHAIN AERONAVES (AC)")
    print("  Cadeia de blocos para vida de aeronaves\n")

    keypair_anac = generate_authority_keypair("ANAC - Agencia Nacional de Aviacao Civil")

    chain = AircraftChain(difficulty=2)
    chain.set_signer(keypair_anac)

    # 1. Fabricação
    linha("1. FABRICACAO — Bloco Genesis")
    dados = AircraftEventFactory.fabricacao(
        matricula="PT-ABC",
        nome_aeronave="Cessna 172S Skyhawk",
        fabricante="Cessna Aircraft",
        modelo="172S",
        tipo_aeronave="AVIAO",
        ano_fabricacao=2022,
        peso_max_decolagem_kg=1111,
        motorizacao="PISTAO",
        num_motores=1,
        motor_potencia_cv=180,
        motor_tipo="Lycoming IO-360-L2A",
        envergadura_m=11.0,
        comprimento_m=8.28,
        autonomia_km=1200,
        velocidade_max_kmh=280,
        capacidade_pilotos=1,
        capacidade_passageiros=3,
        numero_serie="172S-12345",
        uf="SP",
        cidade="Sao Paulo",
    )
    genesis = chain.create_genesis(dados)
    print(f"  Hash: {genesis.hash[:20]}...")
    print(f"  Aeronave: {dados['nome_aeronave']} ({dados['matricula']})")

    # 2. Airworthiness
    linha("2. CERTIFICADO DE AERONAVEGABILIDADE")
    dados_aw = AircraftEventFactory.airworthiness(
        matricula="PT-ABC",
        data_emissao="01/01/2023",
        data_validade="01/01/2025",
        numero_certificado="CVA-2023-001",
        orgao_emissor="ANAC",
    )
    block = chain.add_event(AircraftEventType.AIRWORTHINESS.value, dados_aw)
    print(f"  Bloco #{block.index} — Airworthiness emitido")

    # 3. Revisão
    linha("3. REVISAO ANUAL")
    dados_rev = AircraftEventFactory.revisao(
        matricula="PT-ABC",
        data_revisao="01/06/2024",
        oficina="Aero Maintenance SP",
        tipo_revisao="ANUAL",
        itens_revisados=["Motor", "Asas", "Sistema eletrico", "Instrumentos"],
        proxima_revisao="01/06/2025",
        valor_total=25000.0,
    )
    block = chain.add_event(AircraftEventType.REVISAO.value, dados_rev)
    print(f"  Bloco #{block.index} — Revisao anual (R$ 25.000)")

    # 4. Compra/Venda
    linha("4. COMPRA/VENDA")
    dados_venda = AircraftEventFactory.compra_venda(
        matricula="PT-ABC",
        comprador_cpf="98765432100",
        comprador_nome="Carlos Aviador",
        vendedor_cpf="12345678901",
        vendedor_nome="Joao Silva",
        valor_transacao=800000.0,
        data_transacao="01/09/2024",
    )
    block = chain.add_event(AircraftEventType.COMPRA_VENDA.value, dados_venda)
    print(f"  Bloco #{block.index} — Venda por R$ 800.000")

    # 5. Seguro
    linha("5. SEGURO")
    dados_seg = AircraftEventFactory.seguro(
        matricula="PT-ABC",
        seguradora_nome="Tokio Marine",
        seguradora_cnpj="61198164000123",
        apolice_numero="AC-2024-9999",
        data_inicio="01/09/2024",
        data_fim="01/09/2025",
        valor_segurado=900000.0,
        tipo_seguro="TOTAL",
    )
    block = chain.add_event(AircraftEventType.SEGURO.value, dados_seg)
    print(f"  Bloco #{block.index} — Seguro contratado")

    # Validar
    linha("VALIDACAO")
    ok, msg = chain.validate(require_signatures=True)
    print(f"  {msg}")

    estado = chain.get_estado_atual()
    print(f"  Matricula: {estado['matricula']}")
    print(f"  Modelo: {estado['fabricante']} {estado['modelo']}")
    print(f"  Situacao: {estado['situacao']}")
    print(f"  Proprietarios: {len(estado['proprietarios'])}")

    chain.save_to_file("demo_output/ac_PT-ABC.json")
    print(f"\n  Cadeia salva em demo_output/ac_PT-ABC.json")
    return chain


def demo_an():
    """Demonstração da Blockchain de Animais (AN)."""
    linha("BLOCKCHAIN ANIMAIS (AN)")
    print("  Cadeia de blocos para vida de animais\n")

    keypair_vet = generate_authority_keypair("CRMV-SP - Conselho Regional de Veterinarios")

    chain = AnimalChain(difficulty=2)
    chain.set_signer(keypair_vet)

    # 1. Nascimento
    linha("1. NASCIMENTO — Bloco Genesis")
    dados = AnimalEventFactory.nascimento(
        nome="Rex",
        especie="CAO",
        raca="Labrador Retriever",
        sexo="M",
        data_nascimento="15/03/2023",
        cor="Dourado",
        peso_kg=3.5,
        proprietario_cpf="12345678901",
        proprietario_nome="Joao Silva",
        pai_nome="Champion Golden Star",
        mae_nome="Princess Luna",
        microchip="900123456789012",
        cidade="Sao Paulo",
        uf="SP",
    )
    genesis = chain.create_genesis(dados)
    print(f"  Hash: {genesis.hash[:20]}...")
    print(f"  Animal: {dados['nome']} ({dados['especie']} - {dados['raca']})")

    # 2. Vacinação
    linha("2. VACINACAO — 1a Dose")
    dados_vac = AnimalEventFactory.vacinacao(
        nome_vacina="Polivalente (V8)",
        data_vacinacao="15/04/2023",
        lote="LOT-2023-001",
        fabricante="Zoetis",
        dose="1a dose",
        veterinario_cpf="98765432100",
        veterinario_nome="Dra. Ana Veterinaria",
        clinica="PetClinic SP",
    )
    block = chain.add_event(AnimalEventType.VACINACAO.value, dados_vac)
    print(f"  Bloco #{block.index} — Vacina V8 (1a dose)")

    # 3. Castração
    linha("3. CASTRACAO")
    dados_cast = AnimalEventFactory.castracao(
        data_castracao="01/07/2023",
        veterinario_cpf="98765432100",
        veterinario_nome="Dra. Ana Veterinaria",
        clinica="PetClinic SP",
        metodo="Cirurgico",
    )
    block = chain.add_event(AnimalEventType.CASTRACAO.value, dados_cast)
    print(f"  Bloco #{block.index} — Castracao realizada")

    # 4. Tratamento
    linha("4. TRATAMENTO VETERINARIO")
    dados_trat = AnimalEventFactory.tratamento(
        data_inicio="01/10/2023",
        data_fim="15/10/2023",
        diagnostico="Otite bacteriana",
        veterinario_cpf="98765432100",
        veterinario_nome="Dra. Ana Veterinaria",
        clinica="PetClinic SP",
        medicamentos=["Antibiotico", "Anti-inflamatorio", "Otovet"],
        valor=450.0,
    )
    block = chain.add_event(AnimalEventType.TRATAMENTO.value, dados_trat)
    print(f"  Bloco #{block.index} — Tratamento de otite (R$ 450)")

    # 5. Compra/Venda
    linha("5. COMPRA/VENDA")
    dados_venda = AnimalEventFactory.compra_venda(
        nome="Rex",
        comprador_cpf="98765432100",
        comprador_nome="Maria Santos",
        vendedor_cpf="12345678901",
        vendedor_nome="Joao Silva",
        valor_transacao=3500.0,
        data_transacao="01/01/2024",
    )
    block = chain.add_event(AnimalEventType.COMPRA_VENDA.value, dados_venda)
    print(f"  Bloco #{block.index} — Venda por R$ 3.500")

    # 6. Licença
    linha("6. LICENCA DE POSSE")
    dados_lic = AnimalEventFactory.licenca(
        numero_licenca="LIC-SP-2024-001",
        data_emissao="15/01/2024",
        data_validade="15/01/2025",
        orgao_emissor="Prefeitura de Sao Paulo",
    )
    block = chain.add_event(AnimalEventType.LICENCA.value, dados_lic)
    print(f"  Bloco #{block.index} — Licenca emitida")

    # Validar
    linha("VALIDACAO")
    ok, msg = chain.validate(require_signatures=True)
    print(f"  {msg}")

    estado = chain.get_estado_atual()
    print(f"  Nome: {estado['nome']}")
    print(f"  Especie: {estado['especie']} ({estado['raca']})")
    print(f"  Situacao: {estado['situacao']}")
    print(f"  Proprietario: {estado['proprietario']['nome']}")
    print(f"  Vacinas: {len(estado['vacinas'])}")
    print(f"  Tratamentos: {len(estado['tratamentos'])}")

    chain.save_to_file("demo_output/an_rex.json")
    print(f"\n  Cadeia salva em demo_output/an_rex.json")
    return chain


def main():
    print("\n" + "=" * 60)
    print("  DEMONSTRACAO AUTOMATICA — 4 NOVAS BLOCKCHAINS")
    print("  CO (Empresas) | EM (Embarcacoes) | AC (Aeronaves) | AN (Animais)")
    print("=" * 60)

    chains = {}

    try:
        chains["CO"] = demo_co()
    except Exception as e:
        print(f"\n  ERRO na demo CO: {e}")

    try:
        chains["EM"] = demo_em()
    except Exception as e:
        print(f"\n  ERRO na demo EM: {e}")

    try:
        chains["AC"] = demo_ac()
    except Exception as e:
        print(f"\n  ERRO na demo AC: {e}")

    try:
        chains["AN"] = demo_an()
    except Exception as e:
        print(f"\n  ERRO na demo AN: {e}")

    # Resumo
    linha("RESUMO FINAL")
    db = Database()
    ids = {"CO": "12345678000190", "EM": "NR-2024-001", "AC": "PT-ABC", "AN": "rex"}
    for name, chain in chains.items():
        ok, msg = chain.validate(require_signatures=True)
        signed = sum(1 for b in chain.chain if b.has_signature())
        print(f"  {name}: {len(chain)} blocos | {signed} assinados | {'VALIDA' if ok else 'INVALIDA'}")
        if name in ids and chain:
            chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
            db.save_domain_chain(name.lower(), ids[name], chain.difficulty, chain_data)

    print("\n  Demonstracao concluida com sucesso!")
    print(f"  Arquivos salvos em demo_output/")
    print(f"  Cadeias persistidas no SQLite centralizado: {db.db_path}\n")


if __name__ == "__main__":
    main()
