#!/usr/bin/env python3
"""
demo_auto.py — Demonstração automática da Blockchain de Eventos Vitais PF
com assinaturas digitais ECDSA.

Executa um cenário completo sem necessidade de input interativo.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blockchain_pf import (
    Blockchain, EventFactory, EventType,
    KeyPair, Signer, generate_authority_keypair,
)
from blockchain_pf.database import Database


def linha(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")


def main():
    print("BLOCKCHAIN DE EVENTOS VITAIS — PF")
    print("Demonstracao Automatica com Assinaturas ECDSA\n")

    # ── 0. Gerar Chaves de Autoridade ──────────────────────────────────
    linha("0. GERACAO DE CHAVES ECDSA (P-256)")

    keypair_cartorio = generate_authority_keypair("Cartorio de Registro Civil - SP")
    keypair_juizado = generate_authority_keypair("Juizado Especial - RJ")

    print(f"  Cartorio SP:")
    print(f"    Public key (hex): {keypair_cartorio.public_key_hex()[:32]}...")
    print(f"    Fingerprint:      {keypair_cartorio.fingerprint()}")
    print(f"    Label:            {keypair_cartorio.label}")
    print()
    print(f"  Juizado RJ:")
    print(f"    Public key (hex): {keypair_juizado.public_key_hex()[:32]}...")
    print(f"    Fingerprint:      {keypair_juizado.fingerprint()}")
    print(f"    Label:            {keypair_juizado.label}")

    # ── 1. Criar PF: Nascimento ────────────────────────────────────────
    linha("1. NASCIMENTO — Bloco Genesis (ass. Cartorio SP)")

    chain = Blockchain(difficulty=2)
    chain.set_signer(keypair_cartorio)  # Todos os blocos serao assinados

    dados_nascimento = EventFactory.nascimento(
        cpf="12345678901",
        nome_completo="Maria Clara de Oliveira Santos",
        data_nascimento="15/03/2000",
        sexo="F",
        cidade_nascimento="Sao Paulo",
        uf_nascimento="SP",
        nome_mae="Ana Paula de Oliveira",
        nome_pai="Joao Carlos Santos",
    )

    genesis = chain.create_genesis(dados_nascimento)
    print(f"  Bloco genesis criado — Hash: {genesis.hash[:20]}...")
    print(f"  Assinatura: {genesis.signature['signer_label']}")
    print(f"  Signature (base64): {genesis.signature['signature_b64'][:40]}...")

    # ── 2. Alteracao de Nome ───────────────────────────────────────────
    linha("2. ALTERACAO DE NOME (aos 18 anos)")

    dados_nome = EventFactory.alteracao_nome(
        cpf="12345678901",
        nome_anterior="Maria Clara de Oliveira Santos",
        nome_novo="Maria Clara Oliveira Santos Pereira",
        data_alteracao="15/03/2018",
        motivo="Inclusao do sobrenome do avo materno",
    )
    block_nome = chain.add_event(EventType.ALTERACAO_NOME.value, dados_nome)
    print(f"  Bloco #{block_nome.index} — Hash: {block_nome.hash[:20]}...")
    print(f"  Assinado por: {block_nome.signature['signer_label']}")

    # ── 3. Casamento ───────────────────────────────────────────────────
    linha("3. CASAMENTO")

    dados_casamento = EventFactory.casamento(
        cpf="12345678901",
        nome_conjuge="Pedro Henrique Almeida Lima",
        cpf_conjuge="98765432100",
        data_casamento="20/06/2022",
        regime_bens="COMUNHAO_PARCIAL",
        cidade="Rio de Janeiro",
        uf="RJ",
    )
    block_casamento = chain.add_event(EventType.CASAMENTO.value, dados_casamento)
    print(f"  Bloco #{block_casamento.index} — Hash: {block_casamento.hash[:20]}...")
    print(f"  Assinado por: {block_casamento.signature['signer_label']}")

    # ── 4. Adocao ──────────────────────────────────────────────────────
    linha("4. ADOTACAO")

    dados_adocao = EventFactory.adocao(
        cpf="12345678901",
        nome_adotivo=None,
        data_adocao="10/11/2023",
        nome_mae_adotiva="Maria Clara Oliveira Santos Pereira",
        nome_pai_adotivo="Pedro Henrique Almeida Lima",
        mantem_nome_biologico=True,
    )
    block_adocao = chain.add_event(EventType.ADOCAO.value, dados_adocao)
    print(f"  Bloco #{block_adocao.index} — Hash: {block_adocao.hash[:20]}...")
    print(f"  Assinado por: {block_adocao.signature['signer_label']}")

    # ── 5. Divorcio (ass. Juizado RJ) ─────────────────────────────────
    linha("5. DIVORCIO (ass. Juizado RJ)")

    # Troca o emissor para o Juizado (simula autoridade diferente)
    chain.set_signer(keypair_juizado)

    dados_divorcio = EventFactory.divorcio(
        cpf="12345678901",
        data_divorcio="05/01/2025",
        tipo="CONSENSUAL",
        guarda_filhos="COMPARTILHADA",
        pensao_alimenticia=False,
    )
    block_divorcio = chain.add_event(EventType.DIVORCIO.value, dados_divorcio)
    print(f"  Bloco #{block_divorcio.index} — Hash: {block_divorcio.hash[:20]}...")
    print(f"  Assinado por: {block_divorcio.signature['signer_label']}")
    print(f"  (Autoridade diferente do Cartorio)")

    # ── 6. Disvinculacao Paterna ───────────────────────────────────────
    linha("6. DISVINCULACAO PATERNA")

    dados_disvinc = EventFactory.disvinculacao_paterna(
        cpf="12345678901",
        data_disvinculacao="15/03/2026",
        motivo="Ausencia prolongada e abandono afetivo comprovado judicialmente",
    )
    block_disvinc = chain.add_event(
        EventType.DISVINC_PATerna.value, dados_disvinc
    )
    print(f"  Bloco #{block_disvinc.index} — Hash: {block_disvinc.hash[:20]}...")
    print(f"  Assinado por: {block_disvinc.signature['signer_label']}")

    # ── 7. Timeline Completa ───────────────────────────────────────────
    linha("7. TIMELINE COMPLETA (com assinaturas)")

    emojis = {
        "NASCIMENTO": "NB",
        "ADOCAO": "AD",
        "CASAMENTO": "CA",
        "DIVORCIO": "DV",
        "OBITO": "OB",
        "ALTERACAO_NOME": "NM",
        "DISVINC_MATERNA": "DM",
        "DISVINC_PATerna": "DP",
    }

    for ev in chain.get_timeline():
        tag = emojis.get(ev["tipo"], "??")
        ass = f" [ASS: {ev['emissor']}]" if ev["assinado"] else " [SEM ASS]"
        print(
            f"  [{ev['indice']:02d}] {tag} {ev['tipo']}"
            f"  ({ev['data_registro']}){ass}"
        )

    # ── 8. Validacao da Cadeia ─────────────────────────────────────────
    linha("8. VALIDACAO DA CADEIA")

    # Sem exigir assinaturas
    valida1, msg1 = chain.validate(require_signatures=False)
    print(f"  [sem exigir assinaturas]  {'OK' if valida1 else 'FALHA'}: {msg1}")

    # Exigindo assinaturas
    valida2, msg2 = chain.validate(require_signatures=True)
    print(f"  [exigindo assinaturas]    {'OK' if valida2 else 'FALHA'}: {msg2}")

    # ── 9. Verificacao individual de assinaturas ───────────────────────
    linha("9. VERIFICACAO DE CADA ASSINATURA")

    from blockchain_pf.signatures import BlockSignature, SignatureVerifier

    for block in chain.chain:
        if block.has_signature():
            sig = BlockSignature.from_dict(block.signature)
            ok, msg = chain._verify_signature(block, sig)
            status = "VALIDA" if ok else "INVALIDA"
            print(f"  Bloco #{block.index} ({block.data.get('evento_tipo','?')}): "
                  f"{status} — emitido por '{sig.signer_label}'")

    # ── 10. Verificacao global de assinaturas ──────────────────────────
    linha("10. VERIFICACAO GLOBAL DE ASSINATURAS")

    all_ok, all_msg = chain.verify_all_signatures()
    print(f"  Resultado: {'TODAS VALIDAS' if all_ok else 'INVALIDACAO ENCONTRADA'}")
    print(f"  Detalhes:  {all_msg}")

    # ── 11. Predicoes ──────────────────────────────────────────────────
    linha("11. PREDICOES DE EVENTOS FUTUROS")

    from blockchain_pf.predictor import LifeEventPredictor
    predictor = LifeEventPredictor(chain)
    report = predictor.gerar_relatorio()
    print(report.resumo())

    # ── 12. Persistencia ───────────────────────────────────────────────
    linha("12. PERSISTENCIA (JSON)")

    chain.save_to_file("cadeia_pf_assinada.json")
    print(f"  Cadeia salva em: cadeia_pf_assinada.json")

    # Persistencia no SQLite centralizado (banco <projeto>/database/blockchain.db)
    db = Database()
    chain_data = {"difficulty": chain.difficulty, "chain": [b.to_dict() for b in chain.chain]}
    db.save_chain("12345678901", chain.difficulty, chain_data)
    db.save_graph_node("12345678901", "Maria Clara Oliveira Santos Pereira", True, 0)
    print(f"  Cadeia persistida no SQLite centralizado: {db.db_path}")

    chain2 = Blockchain.load_from_file("cadeia_pf_assinada.json")
    print(f"  Cadeia recarregada: {len(chain2)} bloco(s)")
    v3, m3 = chain2.validate(require_signatures=True)
    print(f"  Validacao apos recarga: {'OK' if v3 else 'FALHA'}: {m3}")

    # ── 13. Teste de adulteracao ───────────────────────────────────────
    linha("13. TESTE DE ADULTERACAO (simulacao)")

    print("  Simulando alteracao indevida no bloco #2...")
    original_hash = chain.chain[2].hash
    original_data = chain.chain[2].data.copy()
    chain.chain[2].data["payload"]["regime_bens"] = "SEPARACAO_TOTAL"  # adultera

    # Verifica hash (deve falhar)
    if chain.chain[2].hash != chain.chain[2].compute_hash():
        print("  Hash do bloco #2: CORROMPIDO (hash nao confere)")
    else:
        print("  Hash do bloco #2: OK (incomum)")

    # Verifica assinatura com hash original (ainda valida — dado corrompido)
    if chain.chain[2].has_signature():
        sig = BlockSignature.from_dict(chain.chain[2].signature)
        ok_bad, msg_bad = chain._verify_signature(chain.chain[2], sig)
        print(f"  Assinatura vs hash original: {'VALIDA' if ok_bad else 'INVALIDA'}")
        print(f"  (Assinatura confere com hash antigo, mas validate() detecta corrupcao)")

    # Agora simula adulteracao completa: dado + hash
    print("\n  Simulando adulteracao completa (dado + hash + nonce)...")
    chain.chain[2].hash = chain.chain[2].compute_hash()  # recalcula com dado adulterado
    chain.chain[2].nonce = 999999  # nonce falso
    chain.chain[2].hash = chain.chain[2].compute_hash()  # re-hash com nonce falso
    
    if chain.chain[2].has_signature():
        sig = BlockSignature.from_dict(chain.chain[2].signature)
        ok_bad2, msg_bad2 = chain._verify_signature(chain.chain[2], sig)
        print(f"  Assinatura vs hash adulterado: {'VALIDA (ERRO!)' if ok_bad2 else 'INVALIDA (CORRETO)'}")
        print(f"  Mensagem: {msg_bad2}")

    # Restaura
    chain.chain[2].data = original_data
    chain.chain[2].hash = original_hash
    chain.chain[2].nonce = 0  # nonce original (sera recalculado se necessario)
    # Recalcula hash original
    from blockchain_pf.block import Block
    tmp = Block(index=chain.chain[2].index, timestamp=chain.chain[2].timestamp,
                data=original_data, previous_hash=chain.chain[2].previous_hash,
                nonce=0, difficulty=chain.chain[2].difficulty)
    # Encontra o nonce correto
    target = '0' * chain.chain[2].difficulty
    while not tmp.hash.startswith(target):
        tmp.nonce += 1
        tmp.hash = tmp.compute_hash()
    chain.chain[2].nonce = tmp.nonce
    chain.chain[2].hash = tmp.hash
    print(f"\n  Dados e hash restaurados ao original.")
    print(f"  Hash restaurado: {chain.chain[2].hash[:20]}...")

    # ── Resumo Final ───────────────────────────────────────────────────
    linha("RESUMO FINAL")

    print(f"""
  Blockchain de Eventos Vitais PF v2.0
  com Assinaturas Digitais ECDSA (P-256)

  Blocos:            {len(chain)}
  Assinados:         {sum(1 for b in chain.chain if b.has_signature())}/{len(chain.chain)}
  Dificuldade:       {chain.difficulty} zeros iniciais
  Integridade:       {'VALIDA' if valida2 else 'INVALIDA'}
  Assinaturas ECDSA: {'TODAS VALIDAS' if all_ok else 'PROBLEMAS ENCONTRADOS'}

  Emissor 1: {keypair_cartorio.label}
    Fingerprint: {keypair_cartorio.fingerprint()}

  Emissor 2: {keypair_juizado.label}
    Fingerprint: {keypair_juizado.fingerprint()}

  Eventos:
    NASCIMENTO:       1  (ass. Cartorio SP)
    ALTERACAO_NOME:   1  (ass. Cartorio SP)
    CASAMENTO:        1  (ass. Cartorio SP)
    ADOCAO:           1  (ass. Cartorio SP)
    DIVORCIO:         1  (ass. Juizado RJ)
    DISVINC_PATerna:  1  (ass. Juizado RJ)

  Demonstracao concluida com sucesso!
""")


if __name__ == "__main__":
    main()
