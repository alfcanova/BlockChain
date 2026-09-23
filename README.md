# Blockchain Brasil — Sistema de Registro Imutavel

Sistema de registro imutavel com **7 blockchains** para o cenario brasileiro,
cada uma cobrindo um dominio civil/comercial diferente. Todas utilizam
**assinaturas digitais ECDSA (P-256)** e **Proof-of-Work**.

| Blockchain | Sigla | Dominio | Chave Primaria |
|-----------|-------|---------|----------------|
| Pessoas Fisicas | **PF** | Eventos vitais | CPF |
| Imoveis | **IM** | Registro imobiliario | Matricula |
| Veiculos | **MO** | Movel / Veiculo | Placa |
| Empresas | **CO** | Pessoa juridica | CNPJ |
| Embarcacoes | **EM** | Registro naval | Registro NR |
| Aeronaves | **AC** | Registro aeronautico | Matricula |
| Animais | **AN** | Registro animal | ID (hash) |

## Estrutura do Projeto

```
blockchain_pf/          # Pessoas Fisicas (CPF)
blockchain_im/          # Imoveis (Matricula)
blockchain_mo/          # Veiculos (Placa)
blockchain_co/          # Empresas (CNPJ)
blockchain_em/          # Embarcacoes (Registro NR)
blockchain_ac/          # Aeronaves (Matricula)
blockchain_an/          # Animais (ID)

web_app.py              # Interface Web + API REST (FastAPI)
demo_auto.py            # Demo automatica da blockchain PF
demo_auto_new.py        # Demo automatica das 4 novas blockchains
generate_300.py         # Gerador de dados demo (300 registros)

admin_pf.html           # Interface admin PF
admin_im.html           # Interface admin IM
admin_mo.html           # Interface admin MO
admin_co.html           # Interface admin CO
admin_em.html           # Interface admin EM
admin_ac.html           # Interface admin AC
admin_an.html           # Interface admin AN

landing_pf.html         # Landing page PF
landing_im.html         # Landing page IM
landing_mo.html         # Landing page MO
landing_co.html         # Landing page CO
landing_em.html         # Landing page EM
landing_ac.html         # Landing page AC
landing_an.html         # Landing page AN
```

## Como Usar

### Interface Web (FastAPI)

```bash
PYTHONIOENCODING=utf-8 python web_app.py
```

- **Home:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Admin PF:** http://localhost:8000/admin/pf
- **Admin IM:** http://localhost:8000/admin/im
- **Admin MO:** http://localhost:8000/admin/mo
- **Admin CO:** http://localhost:8000/admin/co
- **Admin EM:** http://localhost:8000/admin/em
- **Admin AC:** http://localhost:8000/admin/ac
- **Admin AN:** http://localhost:8000/admin/an

### Demonstracao Automatica

```bash
# Blockchain PF
PYTHONIOENCODING=utf-8 python demo_auto.py

# 4 novas blockchains (CO, EM, AC, AN)
PYTHONIOENCODING=utf-8 python demo_auto_new.py
```

### CLI Interativo

```bash
PYTHONIOENCODING=utf-8 python demo.py
```

---

## Blockchain PF — Pessoas Fisicas

Registra toda a vida de uma pessoa, do **nascimento** ao **obito**.

### Eventos

| Evento | Descricao |
|--------|-----------|
| `NASCIMENTO` | Bloco genesis — dados de nascimento |
| `ADOCAO` | Registro de adocao |
| `CASAMENTO` | Casamento com regime de bens |
| `DIVORCIO` | Divorcio consensual ou judicial |
| `OBITO` | Obito (encerra a cadeia) |
| `ALTERACAO_NOME` | Mudanca de nome |
| `DISVINC_MATERNA` | Disvinculacao do vinculo materno |
| `DISVINC_PATerna` | Disvinculacao do vinculo paterno |
| `VACINACAO` | Registro de vacina |
| `PROTESE` | Registro de protese/implante |

### Predicoes

O preditor gera predicoes baseadas em estatisticas demograficas (IBGE/PNAD):
- Casamento, Divorcio, Obito, Adocao, Disvinculacao, Alteracao de nome.

### Exemplo

```python
from blockchain_pf import Blockchain, EventFactory, EventType, generate_authority_keypair

chain = Blockchain(difficulty=2)
keypair = generate_authority_keypair("Cartorio SP")
chain.set_signer(keypair)

dados = EventFactory.nascimento(
    cpf="12345678901", nome_completo="Maria Clara",
    data_nascimento="15/03/2000", sexo="F",
    cidade_nascimento="Sao Paulo", uf_nascimento="SP",
    nome_mae="Ana Paula",
)
genesis = chain.create_genesis(dados)
chain.add_event(EventType.CASAMENTO.value, {
    "cpf": "12345678901", "nome_conjuge": "Pedro",
    "data_casamento": "20/06/2022",
})
ok, msg = chain.validate(require_signatures=True)
```

---

## Blockchain IM — Imoveis

Registra toda a vida de um imovel, do **terreno** (gênesis no espaco geografico real)
ate **transferencias**, **garantias** e **leiloes**.

### Eventos

| Evento | Descricao |
|--------|-----------|
| `TERRENO` | Cadastro do terreno (gênesis) |
| `CONSTRUCAO` | Nova construcao |
| `DEMOLICAO` | Demolição |
| `REFORMA` | Reforma (ampliacao/reducao) |
| `LOTEAMENTO` | Subdivisao em lotes |
| `DESMEMBRAMENTO` | Divisao legal (novas matriculas) |
| `FUSAO` | Uniao de imoveis |
| `COMPRA_VENDA` | Transferencia com pagamento |
| `DOACAO` | Transferencia sem pagamento |
| `HERANCA` | Transferencia por inventario |
| `GARANTIA` | Hipoteca / garantia |
| `QUITACAO` | Baixa de garantia |
| `LEILAO` | Leilao judicial/extrajudicial |
| `CONFISCO` | Apreensao judicial |

### Exemplo

```python
from blockchain_im import PropertyChain, PropertyEventFactory

chain = PropertyChain(difficulty=2)
dados = PropertyEventFactory.terreno(
    matricula="MAT-001", endereco_logradouro="Rua A, 100",
    endereco_bairro="Centro", endereco_cidade="SP",
    endereco_uf="SP", endereco_cep="01000-000",
    lat=-23.55, lon=-46.63, area_terreno_m2=500.0,
)
chain.create_genesis(dados)
chain.add_event("COMPRA_VENDA", PropertyEventFactory.compra_venda(
    matricula="MAT-001", comprador_cpf="12345678901",
    comprador_nome="Joao", vendedor_cpf="98765432100",
    vendedor_nome="Maria", valor_transacao=350000.0,
    data_transacao="15/03/2025",
))
```

---

## Blockchain MO — Veiculos (Moveis)

Registra toda a vida util de um **veiculo**, desde a **fabricacao** (gênesis) ate a **baixa**.

### Eventos

| Evento | Descricao |
|--------|-----------|
| `FABRICACAO` | Fabricacao do veiculo (gênesis) |
| `COMPRA_VENDA` | Transferencia com pagamento |
| `DOACAO` | Transferencia sem pagamento |
| `LEILAO` | Venda em leilao |
| `CONFISCO` | Apreensao judicial |
| `GARANTIA_EMPRESTIMO` | Veiculo como garantia |
| `MULTA` | Infracao de transito |
| `SINISTRO` | Acidente com avaria parcial |
| `SINISTRO_PERDA_TOTAL` | Destruicao total |
| `TROCA_PECA` | Substituicao de componente |
| `REVISAO` | Manutencao programada |
| `LICENCIAMENTO` | Renovacao de licenciamento |
| `BAIXA` | Baixa definitiva |
| `RECALL_DE_FABRICA` | Recall de fabrica |

### Exemplo

```python
from blockchain_mo import VehicleChain, VehicleEventFactory

chain = VehicleChain(difficulty=2)
dados = VehicleEventFactory.fabricacao(
    placa="ABC1D23", renavan="12345678901",
    chassis="9BWZZZ377VT000001", marca="Volkswagen",
    modelo="Gol", ano_fabricacao=2024, ano_modelo=2024,
    cor="Prata", combustivel="FLEX", cilindradas=1000,
    potencia_cv=75,
)
chain.create_genesis(dados)
chain.add_event("COMPRA_VENDA", VehicleEventFactory.compra_venda(
    placa="ABC1D23", comprador_cpf="12345678901",
    comprador_nome="Joao", vendedor_cpf="98765432100",
    vendedor_nome="Maria", valor_transacao=35000.0,
    data_transacao="01/06/2024",
))
```

---

## Blockchain CO — Empresas (CNPJ)

Registra toda a vida de uma **empresa**, da **constituicao** (gênesis) ate a **baixa**.

### Eventos

| Evento | Descricao |
|--------|-----------|
| `CONSTITUICAO` | Abertura da empresa (gênesis) |
| `ADICAO_SOCIO` | Entrada de novo socio |
| `REMOCAO_SOCIO` | Saida de socio |
| `MUDANCA_QUOTA` | Alteracao de participacao societaria |
| `ALTERACAO_CONTRATUAL` | Mudanca no contrato social |
| `MUDANCA_ENDERECO` | Nova sede |
| `MUDANCA_CAPITAL` | Alteracao do capital social |
| `FUSAO` | Uniao com outra empresa |
| `CISAO` | Divisao em empresas menores |
| `INCORPORACAO` | Absorcao por outra empresa |
| `SUSPENSAO` | Suspensao de atividades |
| `REABERTURA` | Retorno de atividades |
| `LIQUIDACAO` | Inicio da liquidacao |
| `BAIXA` | Encerramento definitivo |
| `CERTIDAO` | Certidao emitida (negativa, positiva) |
| `GARANTIA` | Garantia/fianca oferecida |

### Exemplo

```python
from blockchain_co import CompanyChain, CompanyEventFactory

chain = CompanyChain(difficulty=2)
dados = CompanyEventFactory.constituicao(
    cnpj="12345678000190", razao_social="TechSolutions LTDA",
    nome_fantasia="TechSol", data_constituicao="01/01/2024",
    tipo_empresa="LTDA", porte="ME", capital_social=50000,
    natureza_juridica="2062", atividade_principal="6201501",
)
chain.create_genesis(dados)
chain.add_event("ADICAO_SOCIO", CompanyEventFactory.adicao_socio(
    cnpj="12345678000190", socio_cpf="98765432100",
    socio_nome="Maria Santos", participacao=30.0,
    data_entrada="15/06/2024",
))
```

---

## Blockchain EM — Embarcacoes

Registra toda a vida util de uma **embarcacao**, desde a **construcao** (gênesis)
ate a **baixa**.

### Eventos

| Evento | Descricao |
|--------|-----------|
| `CONSTRUCAO` | Construcao/cadastro (gênesis) |
| `COMPRA_VENDA` | Transferencia com pagamento |
| `DOACAO` | Transferencia sem pagamento |
| `LEILAO` | Venda em leilao |
| `REVISAO` | Manutencao programada |
| `INSPECAO` | Inspecao de seguranca |
| `LICENCIAMENTO` | Renovacao de licenciamento |
| `MUDANCA_NOME` | Mudanca do nome |
| `SEGURO` | Contratacao de seguro |
| `SINISTRO` | Registro de sinistro |
| `BAIXA` | Baixa definitiva |

### Exemplo

```python
from blockchain_em import VesselChain, VesselEventFactory

chain = VesselChain(difficulty=2)
dados = VesselEventFactory.construcao(
    registro_nr="NR-001", nome_embarcacao="Estrela do Mar",
    tipo_embarcacao="Iate", porte="MEDIO",
    comprimento_m=12.5, beam_m=4.0, pontal_m=2.0,
    calado_m=1.2, deslocamento_ton=8.5,
    casco_material="Fibra", motorizacao="Inboard",
    motor_potencia_cv=300,
)
chain.create_genesis(dados)
chain.add_event("COMPRA_VENDA", VesselEventFactory.compra_venda(
    registro_nr="NR-001", comprador_cpf="12345678901",
    comprador_nome="Joao", vendedor_cpf="98765432100",
    vendedor_nome="Maria", valor_transacao=250000.0,
    data_transacao="01/06/2024",
))
```

---

## Blockchain AC — Aeronaves

Registra toda a vida util de uma **aeronave**, desde a **fabricacao** (gênesis)
ate a **baixa**.

### Eventos

| Evento | Descricao |
|--------|-----------|
| `FABRICACAO` | Fabricacao/cadastro (gênesis) |
| `COMPRA_VENDA` | Transferencia com pagamento |
| `DOACAO` | Transferencia sem pagamento |
| `REVISAO` | Manutencao programada |
| `INSPECAO` | Inspecao tecnica |
| `AIRWORTHINESS` | Certificado de aeronavegabilidade |
| `LICENCA_VOO` | Licenca de voo |
| `REGISTRO` | Registro em nova autoridade |
| `MUDANCA_NOME` | Alteracao de identificacao |
| `SEGURO` | Contratacao de seguro |
| `SINISTRO` | Registro de sinistro |
| `BAIXA` | Baixa definitiva |

### Exemplo

```python
from blockchain_ac import AircraftChain, AircraftEventFactory

chain = AircraftChain(difficulty=2)
dados = AircraftEventFactory.fabricacao(
    matricula="PT-ABC", nome_aeronave="Cessna 172",
    fabricante="Cessna", modelo="172S",
    tipo_aeronave="AVIAO", ano_fabricacao=2022,
    peso_max_decolagem_kg=1111, motorizacao="PISTAO",
    num_motores=1, motor_potencia_cv=180,
)
chain.create_genesis(dados)
chain.add_event("AIRWORTHINESS", AircraftEventFactory.airworthiness(
    matricula="PT-ABC", data_emissao="01/01/2023",
    data_validade="01/01/2025", numero_certificado="CVA-001",
))
```

---

## Blockchain AN — Animais

Registra toda a vida de um **animal**, desde o **nascimento/cadastro** (gênesis)
ate o **obito**.

### Eventos

| Evento | Descricao |
|--------|-----------|
| `NASCIMENTO` | Nascimento/cadastro (gênesis) |
| `COMPRA_VENDA` | Transferencia com pagamento |
| `DOACAO` | Transferencia sem pagamento |
| `ADOCAO` | Adocao de animal abandonado |
| `VACINACAO` | Aplicacao de vacina |
| `CASTRACAO` | Castracao/esterilizacao |
| `TRATAMENTO` | Tratamento veterinario |
| `MICROCHIP` | Implantacao de microchip |
| `LICENCA` | Licenca de posse |
| `MUDANCA_NOME` | Mudanca do nome |
| `OBITO` | Obito do animal |
| `CERTIDAO` | Certidao de nascimento/raca |

### Exemplo

```python
from blockchain_an import AnimalChain, AnimalEventFactory

chain = AnimalChain(difficulty=2)
dados = AnimalEventFactory.nascimento(
    nome="Rex", especie="CAO", raca="Labrador",
    sexo="M", data_nascimento="15/03/2024",
    cor="Dourado", peso_kg=5.0,
    proprietario_cpf="12345678901",
    proprietario_nome="Joao Silva",
)
chain.create_genesis(dados)
chain.add_event("VACINACAO", AnimalEventFactory.vacinacao(
    nome_vacina="Raiva", data_vacinacao="01/04/2024",
    dose="1a dose", fabricante="Zoetis",
))
```

---

## API REST (FastAPI)

### Rotas PF

| Metodo | Rota | Descricao |
|--------|------|----------|
| GET | `/api/health` | Status do servidor |
| POST | `/api/chain?cpf=X` | Criar nova cadeia |
| GET | `/api/chains` | Listar todas as cadeias |
| GET | `/api/chain/{cpf}` | Dados da cadeia |
| POST | `/api/chain/{cpf}/event` | Registrar evento |
| GET | `/api/chain/{cpf}/timeline` | Timeline completa |
| GET | `/api/chain/{cpf}/validate` | Validar cadeia |
| GET | `/api/chain/{cpf}/predictions` | Gerar predicoes |

### Rotas IM (Imoveis)

| Metodo | Rota | Descricao |
|--------|------|----------|
| GET | `/api/im` | Listar imoveis |
| POST | `/api/im` | Criar imovel |
| GET | `/api/im/{matricula}` | Dados do imovel |
| POST | `/api/im/{matricula}/event` | Registrar evento |
| GET | `/api/im/{matricula}/timeline` | Timeline |

### Rotas MO (Veiculos)

| Metodo | Rota | Descricao |
|--------|------|----------|
| GET | `/api/mo` | Listar veiculos |
| POST | `/api/mo` | Criar veiculo |
| GET | `/api/mo/{placa}` | Dados do veiculo |
| POST | `/api/mo/{placa}/event` | Registrar evento |
| GET | `/api/mo/{placa}/timeline` | Timeline |

### Rotas CO (Empresas)

| Metodo | Rota | Descricao |
|--------|------|----------|
| GET | `/api/co` | Listar empresas |
| POST | `/api/co` | Criar empresa |
| GET | `/api/co/{cnpj}` | Dados da empresa |
| POST | `/api/co/{cnpj}/event` | Registrar evento |
| GET | `/api/co/{cnpj}/timeline` | Timeline |

### Rotas EM (Embarcacoes)

| Metodo | Rota | Descricao |
|--------|------|----------|
| GET | `/api/em` | Listar embarcacoes |
| POST | `/api/em` | Criar embarcacao |
| GET | `/api/em/{registro}` | Dados da embarcacao |
| POST | `/api/em/{registro}/event` | Registrar evento |
| GET | `/api/em/{registro}/timeline` | Timeline |

### Rotas AC (Aeronaves)

| Metodo | Rota | Descricao |
|--------|------|----------|
| GET | `/api/ac` | Listar aeronaves |
| POST | `/api/ac` | Criar aeronave |
| GET | `/api/ac/{matricula}` | Dados da aeronave |
| POST | `/api/ac/{matricula}/event` | Registrar evento |
| GET | `/api/ac/{matricula}/timeline` | Timeline |

### Rotas AN (Animais)

| Metodo | Rota | Descricao |
|--------|------|----------|
| GET | `/api/an` | Listar animais |
| POST | `/api/an` | Criar animal |
| GET | `/api/an/{animal_id}` | Dados do animal |
| POST | `/api/an/{animal_id}/event` | Registrar evento |
| GET | `/api/an/{animal_id}/timeline` | Timeline |

---

## Cross-Chain

As blockchains se comunicam entre si via **referencias cruzadas**:

- **PF ↔ IM**: Pessoa proprietaria de imovel
- **PF ↔ MO**: Pessoa proprietaria de veiculo
- **PF ↔ CO**: Socio de empresa
- **PF ↔ EM**: Proprietario de embarcacao
- **PF ↔ AC**: Proprietario de aeronave
- **PF ↔ AN**: Proprietario de animal

```python
from blockchain_im import CrossChainManager

manager = CrossChainManager()
manager.register_pf("12345678901", chain_pf)
manager.register_im("MAT-001", chain_im)
ref = manager.create_reference(
    cpf="12345678901", matricula="MAT-001",
    tipo_vinculo="PROPRIETARIO",
)
```

---

## Garantias de Integridade

1. **Hash encadeado**: Cada bloco referencia o hash do anterior
2. **Proof-of-Work**: Mineracao com dificuldade configuravel
3. **Assinaturas ECDSA**: Cada bloco e autenticado por autoridade
4. **Validacao integral**: Verificacao de toda a cadeia
5. **Imutabilidade**: Alteracao em qualquer bloco corrompe a cadeia
6. **Protecao por estado**: Eventos bloqueados em certos estados

### Esquema de Assinatura ECDSA

```
    ┌─────────────┐
    │  Gerar Chave │
    │  ECDSA P-256 │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Minerar    │
    │  Bloco      │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Assinar    │
    │  Hash+Index │
    │  +Timestamp │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Verificar  │
    │  Assinatura │
    └─────────────┘
```

---

## Requisitos

- Python 3.10+
- `cryptography` (para ECDSA)
- `fastapi` + `uvicorn` (para API web)

## Testes

```bash
python -m pytest tests/ -v
```

## Licenca
Este projeto é desenvolvido para fins de pesquisa e desenvolvimento de linguagens de programação. Consulte a documentação em docs/ para obter detalhes completos da especificação e licença.

           GNU GENERAL PUBLIC LICENSE

Version 3, 29 June 2007 Copyright (C) 2007 Free Software
