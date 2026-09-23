#!/usr/bin/env python3
"""
demo.py — Demonstracao interativa da Blockchain de Eventos Vitais PF
com assinaturas digitais ECDSA.

Execute: python demo.py

Funcionalidades:
  1. Criar PF (nascimento -> genesis)
  2. Registrar adocao
  3. Registrar casamento
  4. Registrar divorcio
  5. Registrar obito
  6. Alterar nome
  7. Disvinculacao materna/paterna
  8. Ver timeline completa
  9. Validar cadeia
  10. Gerar predicoes
  11. Verificar assinaturas ECDSA
  12. Gerar/chave de autoridade
  13. Salvar/Carregar cadeia
  14. Sair
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blockchain_pf import (
    Blockchain, EventFactory, EventType, ChainProtector,
    KeyPair, Signer, generate_authority_keypair,
    BlockSignature, SignatureVerifier,
)
from blockchain_pf.predictor import LifeEventPredictor


# ── Cores ANSI ──────────────────────────────────────────────────────────

class Cor:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    DIM     = "\033[2m"


def banner():
    print(f"""
{Cor.CYAN}+============================================================+
|                                                              |
|   BLOCKCHAIN DE EVENTOS VITAIS -- PESSOA FISICA              |
|   com Assinaturas Digitais ECDSA (P-256 / secp256r1)        |
|                                                              |
|   Registre toda a vida de uma pessoa em uma cadeia           |
|   imutavel de blocos, assinados digitalmente.                |
|                                                              |
+============================================================+{Cor.RESET}
""")


def menu():
    print(f"""
{Cor.YELLOW}+----------------------- MENU ------------------------+{Cor.RESET}
|  {Cor.GREEN}1{Cor.RESET}  Criar PF (Nascimento)                             |
|  {Cor.GREEN}2{Cor.RESET}  Registrar Adocao                                  |
|  {Cor.GREEN}3{Cor.RESET}  Registrar Casamento                               |
|  {Cor.GREEN}4{Cor.RESET}  Registrar Divorcio                                |
|  {Cor.GREEN}5{Cor.RESET}  Registrar Obito                                   |
|  {Cor.GREEN}6{Cor.RESET}  Alterar Nome                                      |
|  {Cor.GREEN}7{Cor.RESET}  Disvinculacao Parental                            |
|  {Cor.GREEN}8{Cor.RESET}  Ver Timeline Completa                             |
|  {Cor.GREEN}9{Cor.RESET}  Validar Cadeia                                    |
|  {Cor.GREEN}10{Cor.RESET} Gerar Predicoes de Eventos                        |
|  {Cor.GREEN}11{Cor.RESET} Verificar Assinaturas ECDSA                       |
|  {Cor.GREEN}12{Cor.RESET} Gerar Chave de Autoridade                         |
|  {Cor.GREEN}13{Cor.RESET} Salvar Cadeia em Arquivo                          |
|  {Cor.GREEN}14{Cor.RESET} Carregar Cadeia de Arquivo                        |
|  {Cor.GREEN}0{Cor.RESET}  Sair                                              |
{Cor.YELLOW}+----------------------------------------------------+{Cor.RESET}
""")


def input_str(prompt: str, default: str = "") -> str:
    val = input(f"  {Cor.CYAN}>{Cor.RESET} {prompt} [{default}]: ").strip()
    return val if val else default


def sucesso(msg: str):
    print(f"  {Cor.GREEN}+{Cor.RESET} {msg}")


def erro(msg: str):
    print(f"  {Cor.RED}x{Cor.RESET} {msg}")


def info(msg: str):
    print(f"  {Cor.BLUE}i{Cor.RESET} {msg}")


def warning(msg: str):
    print(f"  {Cor.YELLOW}!{Cor.RESET} {msg}")


# ── Funcoes de cada operacao ───────────────────────────────────────────

def criar_nascimento(chain: Blockchain):
    print(f"\n{Cor.BOLD}  CADASTRO DE NASCIMENTO{Cor.RESET}\n")

    cpf = input_str("CPF (11 digitos)", "")
    nome = input_str("Nome completo", "")
    data = input_str("Data de nascimento (DD/MM/AAAA)", "")
    sexo = input_str("Sexo (M/F)", "M")
    cidade = input_str("Cidade de nascimento", "")
    uf = input_str("UF", "SP")
    mae = input_str("Nome da mae", "")
    pai = input_str("Nome do pai (Enter se nao informado)", "")

    try:
        dados = EventFactory.nascimento(
            cpf=cpf, nome_completo=nome, data_nascimento=data,
            sexo=sexo, cidade_nascimento=cidade, uf_nascimento=uf,
            nome_mae=mae, nome_pai=pai if pai else None,
        )
        block = chain.create_genesis(dados)
        sucesso(f"Bloco genesis criado!")
        if block.has_signature():
            info(f"Assinado por: {block.signature['signer_label']}")
        info(f"Hash: {block.hash[:20]}...")
    except ValueError as e:
        erro(f"Erro de validacao: {e}")


def registrar_evento(chain: Blockchain, event_type: str, prompt_fn):
    ja_obito = len(chain.get_events_by_type(EventType.OBITO.value)) > 0
    if ja_obito and not ChainProtector.pode_adicionar(event_type, True):
        warning("Cadeia encerrada por OBITO. Evento bloqueado.")
        return

    print(f"\n{Cor.BOLD}  REGISTRAR {event_type}{Cor.RESET}\n")
    try:
        dados = prompt_fn(chain)
        if dados is None:
            info("Operacao cancelada.")
            return
        block = chain.add_event(event_type, dados)
        sucesso(f"Bloco #{block.index} criado!")
        if block.has_signature():
            info(f"Assinado por: {block.signature['signer_label']}")
        info(f"Hash: {block.hash[:20]}...")
    except ValueError as e:
        erro(f"Erro de validacao: {e}")


def prompt_adocao(chain: Blockchain) -> dict:
    cpf = input_str("CPF da PF adotada", "")
    nome = input_str("Nome adotivo (Enter para manter)", "")
    data = input_str("Data da adocao (DD/MM/AAAA)", "")
    mae = input_str("Nome da mae adotiva", "")
    pai = input_str("Nome do pai adotivo (Enter se nao aplicavel)", "")
    mantem = input_str("Manter nome biologico? (s/n)", "n")
    return EventFactory.adocao(
        cpf=cpf, nome_adotivo=nome if nome else None,
        data_adocao=data, nome_mae_adotiva=mae,
        nome_pai_adotivo=pai if pai else None,
        mantem_nome_biologico=(mantem.lower() == "s"),
    )


def prompt_casamento(chain: Blockchain) -> dict:
    cpf = input_str("CPF da PF", "")
    conjuge = input_str("Nome do conjuge", "")
    cpf_conjuge = input_str("CPF do conjuge", "")
    data = input_str("Data do casamento (DD/MM/AAAA)", "")
    regime = input_str("Regime de bens", "COMUNHAO_PARCIAL")
    cidade = input_str("Cidade", "")
    uf = input_str("UF", "")
    return EventFactory.casamento(
        cpf=cpf, nome_conjuge=conjuge, cpf_conjuge=cpf_conjuge,
        data_casamento=data, regime_bens=regime, cidade=cidade, uf=uf,
    )


def prompt_divorcio(chain: Blockchain) -> dict:
    cpf = input_str("CPF da PF", "")
    data = input_str("Data do divorcio (DD/MM/AAAA)", "")
    tipo = input_str("Tipo (CONSENSUAL/JUDICIAL)", "CONSENSUAL")
    guarda = input_str("Guarda dos filhos (MATERNA/PATERNA/COMPARTILHADA/Nenhum)", "")
    pensao = input_str("Pensao alimenticia? (s/n)", "n")
    return EventFactory.divorcio(
        cpf=cpf, data_divorcio=data, tipo=tipo,
        guarda_filhos=guarda if guarda else None,
        pensao_alimenticia=(pensao.lower() == "s"),
    )


def prompt_obito(chain: Blockchain) -> dict:
    cpf = input_str("CPF da PF", "")
    data = input_str("Data do obito (DD/MM/AAAA)", "")
    cidade = input_str("Cidade do obito", "")
    uf = input_str("UF do obito", "")
    causa = input_str("Causa da morte (Enter se desconhecida)", "")
    return EventFactory.obito(
        cpf=cpf, data_obito=data, cidade_obito=cidade,
        uf_obito=uf, causa_morte=causa if causa else None,
    )


def prompt_alteracao_nome(chain: Blockchain) -> dict:
    cpf = input_str("CPF da PF", "")
    anterior = input_str("Nome anterior", "")
    novo = input_str("Nome novo", "")
    data = input_str("Data da alteracao (DD/MM/AAAA)", "")
    motivo = input_str("Motivo", "")
    return EventFactory.alteracao_nome(
        cpf=cpf, nome_anterior=anterior, nome_novo=novo,
        data_alteracao=data, motivo=motivo,
    )


def prompt_disvinculacao(chain: Blockchain) -> dict:
    cpf = input_str("CPF da PF", "")
    data = input_str("Data da disvinculacao (DD/MM/AAAA)", "")
    motivo = input_str("Motivo judicial", "")
    tipo = input_str("Vinculo: M (materno) ou P (paterno)", "M")
    if tipo.upper() == "P":
        return EventFactory.disvinculacao_paterna(
            cpf=cpf, data_disvinculacao=data, motivo=motivo,
        )
    else:
        return EventFactory.disvinculacao_materna(
            cpf=cpf, data_disvinculacao=data, motivo=motivo,
        )


def ver_timeline(chain: Blockchain):
    print(f"\n{Cor.BOLD}  TIMELINE COMPLETA{Cor.RESET}\n")
    timeline = chain.get_timeline()
    if not timeline:
        info("Cadeia vazia.")
        return

    for ev in timeline:
        ass_tag = ""
        if ev["assinado"]:
            ass_tag = f" {Cor.GREEN}[ASS: {ev['emissor']}]{Cor.RESET}"
        else:
            ass_tag = f" {Cor.DIM}[SEM ASS]{Cor.RESET}"

        print(
            f"  {Cor.DIM}[{ev['indice']:02d}]{Cor.RESET} "
            f"{Cor.BOLD}{ev['tipo']}{Cor.RESET} "
            f"({ev['data_registro']}){ass_tag}"
        )
        dados = ev["dados"]
        for k, v in dados.items():
            if k not in ("evento_tipo", "status_vivo") and v is not None and v != "":
                if isinstance(v, dict):
                    print(f"       {Cor.CYAN}{k}:{Cor.RESET}")
                    for sk, sv in v.items():
                        print(f"         - {sk}: {sv}")
                else:
                    print(f"       {Cor.CYAN}{k}:{Cor.RESET} {v}")
        print()


def validar_cadeia(chain: Blockchain):
    print(f"\n{Cor.BOLD}  VALIDACAO DA CADEIA{Cor.RESET}\n")
    valida, msg = chain.validate(require_signatures=False)
    if valida:
        sucesso(msg)
    else:
        erro(msg)

    info(f"Blocos: {len(chain)}")
    if chain.chain:
        ultimo = chain.get_last_event()
        if ultimo:
            info(f"Ultimo hash: {ultimo.hash[:32]}...")
            if ultimo.has_signature():
                info(f"Ultimo emissor: {ultimo.signature['signer_label']}")


def gerar_predicoes(chain: Blockchain):
    print(f"\n{Cor.BOLD}  PREDICOES DE EVENTOS FUTUROS{Cor.RESET}\n")
    predictor = LifeEventPredictor(chain)
    report = predictor.gerar_relatorio()
    print(report.resumo())


def verificar_assinaturas(chain: Blockchain):
    print(f"\n{Cor.BOLD}  VERIFICACAO DE ASSINATURAS ECDSA{Cor.RESET}\n")

    from blockchain_pf.signatures import BlockSignature, SignatureVerifier

    for block in chain.chain:
        if block.has_signature():
            sig = BlockSignature.from_dict(block.signature)
            ok, msg = chain._verify_signature(block, sig)
            status = f"{Cor.GREEN}VALIDA{Cor.RESET}" if ok else f"{Cor.RED}INVALIDA{Cor.RESET}"
            print(f"  Bloco #{block.index} ({block.data.get('evento_tipo','?')}): "
                  f"{status} — emitido por '{sig.signer_label}'")
        else:
            print(f"  Bloco #{block.index} ({block.data.get('evento_tipo','?')}): "
                  f"{Cor.YELLOW}SEM ASSINATURA{Cor.RESET}")

    print()
    all_ok, all_msg = chain.verify_all_signatures()
    if all_ok:
        sucesso(all_msg)
    else:
        erro(all_msg)


def gerar_chave(chain: Blockchain):
    print(f"\n{Cor.BOLD}  GERAR CHAVE DE AUTORIDADE ECDSA{Cor.RESET}\n")
    label = input_str("Nome/label da autoridade", "Autoridade")
    keypair = generate_authority_keypair(label)

    info(f"Chave publica (hex): {keypair.public_key_hex()[:32]}...")
    info(f"Fingerprint:         {keypair.fingerprint()}")
    info(f"Label:               {keypair.label}")

    chain.set_signer(keypair)
    sucesso(f"Signer configurado para a cadeia!")


def salvar_cadeia(chain: Blockchain):
    arquivo = input_str("Caminho do arquivo", "cadeia_pf.json")
    chain.save_to_file(arquivo)
    sucesso(f"Cadeia salva em: {arquivo}")


def carregar_cadeia() -> Blockchain:
    arquivo = input_str("Caminho do arquivo", "cadeia_pf.json")
    try:
        chain = Blockchain.load_from_file(arquivo)
        sucesso(f"Cadeia carregada: {len(chain)} bloco(s)")
        return chain
    except FileNotFoundError:
        erro(f"Arquivo nao encontrado: {arquivo}")
        return Blockchain()
    except Exception as e:
        erro(f"Erro ao carregar: {e}")
        return Blockchain()


# ── Main ────────────────────────────────────────────────────────────────

def main():
    banner()

    chain = Blockchain(difficulty=2)

    while True:
        menu()
        opcao = input_str("Escolha uma opcao", "0")

        if opcao == "1":
            criar_nascimento(chain)
        elif opcao == "2":
            registrar_evento(chain, EventType.ADOCAO.value, prompt_adocao)
        elif opcao == "3":
            registrar_evento(chain, EventType.CASAMENTO.value, prompt_casamento)
        elif opcao == "4":
            registrar_evento(chain, EventType.DIVORCIO.value, prompt_divorcio)
        elif opcao == "5":
            registrar_evento(chain, EventType.OBITO.value, prompt_obito)
        elif opcao == "6":
            registrar_evento(
                chain, EventType.ALTERACAO_NOME.value, prompt_alteracao_nome
            )
        elif opcao == "7":
            print(f"\n  {Cor.BOLD}Disvinculacao Parental{Cor.RESET}")
            print(f"  {Cor.DIM}  M = Materna | P = Paterna{Cor.RESET}")
            registrar_evento(
                chain, EventType.DISVINC_MATERNA.value, prompt_disvinculacao
            )
        elif opcao == "8":
            ver_timeline(chain)
        elif opcao == "9":
            validar_cadeia(chain)
        elif opcao == "10":
            gerar_predicoes(chain)
        elif opcao == "11":
            verificar_assinaturas(chain)
        elif opcao == "12":
            gerar_chave(chain)
        elif opcao == "13":
            salvar_cadeia(chain)
        elif opcao == "14":
            chain = carregar_cadeia()
        elif opcao == "0":
            print(f"\n  {Cor.GREEN}Ate logo!{Cor.RESET}\n")
            break
        else:
            warning("Opcao invalida. Tente novamente.")

        input(f"\n  {Cor.DIM}Pressione Enter para continuar...{Cor.RESET}")


if __name__ == "__main__":
    main()
