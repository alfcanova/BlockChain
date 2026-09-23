"""
blockchain_mo/chain.py
Cadeia de blocos para eventos de veículos (móveis).
Gênesis = fabricação do veículo.
Validação integral (hash + PoW + assinaturas ECDSA),
persistência em JSON e operações de busca.
"""

import json
import os
import time
from typing import Any, Optional

from blockchain_pf.block import Block
from blockchain_pf.signatures import (
    KeyPair,
    Signer,
    BlockSignature,
    SignatureVerifier,
    generate_authority_keypair,
)

from .events import VehicleEventType, VehicleChainProtector


class VehicleChain:
    """
    Cadeia de blocos para um veículo.

    A cadeia começa com um bloco gênesis que representa a fabricação
    do veículo (placa, RENAVAN, chassi, especificações técnicas).
    Cada bloco pode ser assinado digitalmente com ECDSA.
    """

    def __init__(self, difficulty: int = 2) -> None:
        self.difficulty = difficulty
        self.chain: list[Block] = []
        self._event_index: dict[str, list[int]] = {}
        self._default_keypair = generate_authority_keypair("detran")
        self._signer = Signer(self._default_keypair)

    # ── Configuração de assinatura ─────────────────────────────────────

    def set_signer(self, keypair: KeyPair) -> None:
        """Configura o assinador da cadeia."""
        self._signer = Signer(keypair)

    @property
    def signer(self) -> Optional[Signer]:
        """Retorna o assinador atual."""
        return self._signer

    # ── Inicialização ─────────────────────────────────────────────────

    def create_genesis(self, veiculo_data: dict[str, Any]) -> Block:
        """
        Cria o bloco gênesis com dados de fabricação do veículo.
        O bloco é obrigatoriamente assinado com ECDSA.

        Raises:
            ValueError: Se nenhum signer estiver configurado.

        Args:
            veiculo_data: Dicionário com dados do veículo (placa, RENAVAN, chassi, etc).

        Returns:
            O bloco gênesis criado.
        """
        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")

        genesis = Block(
            index=0,
            timestamp=time.time(),
            data={
                "evento_tipo": VehicleEventType.FABRICACAO.value,
                "payload": veiculo_data,
                "hash_cadeia": "GENESIS",
            },
            previous_hash="0" * 64,
            difficulty=self.difficulty,
        )
        genesis.mine_block()

        # Assina obrigatoriamente
        sig = self._signer.sign_block(genesis)
        genesis.set_signature(
            signer_label=sig.signer_label,
            signer_pubkey=sig.signer_pubkey,
            signature_b64=sig.signature_b64,
            signed_at=sig.signed_at,
        )

        self.chain.append(genesis)
        self._index_event(VehicleEventType.FABRICACAO.value, 0)
        return genesis

    # ── Adição de blocos ──────────────────────────────────────────────

    def add_event(self, event_type: str, payload: dict[str, Any]) -> Block:
        """
        Adiciona um novo evento à cadeia.

        Args:
            event_type: Tipo do evento (ex: "COMPRA_VENDA", "SINISTRO").
            payload:    Dados do evento.

        Returns:
            O bloco adicionado.

        Raises:
            ValueError: Se a cadeia estiver vazia ou o evento for bloqueado.
        """
        if not self.chain:
            raise ValueError("Cadeia vazia — crie o bloco gênesis primeiro.")

        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")

        # Verifica se o evento pode ser adicionado
        estado = self.get_estado_atual()
        if not VehicleChainProtector.pode_adicionar(event_type, estado.get("situacao", "REGULAR")):
            raise ValueError(
                f"Evento '{event_type}' bloqueado para veículo com estado '{estado.get('situacao')}'."
            )

        last_block = self.chain[-1]
        new_block = Block(
            index=last_block.index + 1,
            timestamp=time.time(),
            data={
                "evento_tipo": event_type,
                "payload": payload,
                "hash_cadeia": last_block.hash,
            },
            previous_hash=last_block.hash,
            difficulty=self.difficulty,
        )
        new_block.mine_block()

        # Assina obrigatoriamente
        sig = self._signer.sign_block(new_block)
        new_block.set_signature(
            signer_label=sig.signer_label,
            signer_pubkey=sig.signer_pubkey,
            signature_b64=sig.signature_b64,
            signed_at=sig.signed_at,
        )

        self.chain.append(new_block)
        self._index_event(event_type, new_block.index)
        return new_block

    # ── Estado acumulado ──────────────────────────────────────────────

    def get_estado_atual(self) -> dict[str, Any]:
        """
        Retorna o estado consolidado do veículo.
        Calcula a partir de todos os blocos da cadeia.
        """
        if not self.chain:
            return {}

        genesis = self.chain[0]
        payload_genesis = genesis.data.get("payload", {})

        estado = {
            "placa": payload_genesis.get("placa", ""),
            "renavan": payload_genesis.get("renavan", ""),
            "chassis": payload_genesis.get("chassis", ""),
            "marca": payload_genesis.get("marca", ""),
            "modelo": payload_genesis.get("modelo", ""),
            "ano_fabricacao": payload_genesis.get("ano_fabricacao", 0),
            "ano_modelo": payload_genesis.get("ano_modelo", 0),
            "cor": payload_genesis.get("cor", ""),
            "combustivel": payload_genesis.get("combustivel", ""),
            "tipo_veiculo": payload_genesis.get("tipo_veiculo", ""),
            "categoria": payload_genesis.get("categoria", ""),
            "situacao": payload_genesis.get("situacao", "REGULAR"),
            "proprietarios": list(payload_genesis.get("proprietarios", [])),
            "pecas_atuais": list(payload_genesis.get("pecas_homologadas", [])),
            "multas_pendentes": [],
            "sinistros": [],
            "garantias_ativas": [],
            "odometro_km": payload_genesis.get("odometro_km", 0.0),
            "historico_transmissoes": [],
            "recalls_pendentes": [],
        }

        # Processa cada evento subsequente
        for block in self.chain[1:]:
            evento = block.data.get("evento_tipo", "")
            payload = block.data.get("payload", {})

            if evento == VehicleEventType.COMPRA_VENDA.value:
                comprador = payload.get("comprador", {})
                vendedor = payload.get("vendedor", {})
                cpf_comprador = comprador.get("cpf", "")
                cpf_vendedor = vendedor.get("cpf", "")

                transmissao = {
                    "tipo": "COMPRA_VENDA",
                    "data": payload.get("data_transacao", ""),
                    "valor": payload.get("valor_transacao", 0),
                    "comprador": comprador.get("nome", ""),
                    "vendedor": vendedor.get("nome", ""),
                    "bloco": block.index,
                }
                estado["historico_transmissoes"].append(transmissao)

                # Remove vendedor, adiciona comprador
                estado["proprietarios"] = [
                    p for p in estado["proprietarios"]
                    if p.get("cpf") != cpf_vendedor
                ]
                existe = any(p.get("cpf") == cpf_comprador for p in estado["proprietarios"])
                if not existe and cpf_comprador:
                    estado["proprietarios"].append({
                        "cpf": cpf_comprador,
                        "nome": comprador.get("nome", ""),
                        "participacao": 100.0,
                        "origem": "COMPRA",
                    })

                # Atualiza odômetro
                odometro = payload.get("odometro_km", 0)
                if odometro > estado["odometro_km"]:
                    estado["odometro_km"] = odometro

            elif evento == VehicleEventType.DOACAO.value:
                donatario = payload.get("donatario", {})
                doador = payload.get("doador", {})
                cpf_donatario = donatario.get("cpf", "")
                cpf_doador = doador.get("cpf", "")

                transmissao = {
                    "tipo": "DOACAO",
                    "data": payload.get("data_doacao", ""),
                    "valor": 0,
                    "comprador": donatario.get("nome", ""),
                    "vendedor": doador.get("nome", ""),
                    "bloco": block.index,
                }
                estado["historico_transmissoes"].append(transmissao)

                estado["proprietarios"] = [
                    p for p in estado["proprietarios"]
                    if p.get("cpf") != cpf_doador
                ]
                existe = any(p.get("cpf") == cpf_donatario for p in estado["proprietarios"])
                if not existe and cpf_donatario:
                    estado["proprietarios"].append({
                        "cpf": cpf_donatario,
                        "nome": donatario.get("nome", ""),
                        "participacao": 100.0,
                        "origem": "DOACAO",
                    })

                odometro = payload.get("odometro_km", 0)
                if odometro > estado["odometro_km"]:
                    estado["odometro_km"] = odometro

            elif evento == VehicleEventType.LEILAO.value:
                if payload.get("lance_vencedor", 0) > 0:
                    vencedor = payload.get("vencedor", {})
                    cpf_v = vencedor.get("cpf", "")
                    estado["proprietarios"] = [{
                        "cpf": cpf_v,
                        "nome": vencedor.get("nome", ""),
                        "participacao": 100.0,
                        "origem": "LEILAO",
                    }]
                    estado["situacao"] = "REGULAR"
                else:
                    estado["situacao"] = "EM_LEILAO"

            elif evento == VehicleEventType.CONFISCO.value:
                estado["situacao"] = "CONFISCADO"
                estado["proprietarios"] = []

            elif evento == VehicleEventType.GARANTIA_EMPRESTIMO.value:
                garantia = {
                    "tipo": payload.get("tipo_garantia", ""),
                    "credor": payload.get("credor", {}),
                    "valor": payload.get("valor_emprestimo", 0),
                    "data": payload.get("data_garantia", ""),
                    "vencimento": payload.get("data_vencimento", ""),
                    "status": "ATIVA",
                    "bloco_index": block.index,
                }
                estado["garantias_ativas"].append(garantia)
                estado["situacao"] = "GARANTIDO"

            elif evento == VehicleEventType.QUITACAO_GARANTIA.value:
                idx = payload.get("garantia_index", -1)
                if 0 <= idx < len(estado["garantias_ativas"]):
                    estado["garantias_ativas"][idx]["status"] = "QUITADA"
                # Verifica se ainda há garantias ativas
                tem_ativa = any(
                    g.get("status") == "ATIVA"
                    for g in estado["garantias_ativas"]
                )
                if not tem_ativa and estado["situacao"] == "GARANTIDO":
                    estado["situacao"] = "REGULAR"

            elif evento == VehicleEventType.MULTA.value:
                multa = {
                    "numero_auto": payload.get("numero_auto", ""),
                    "data": payload.get("data_infracao", ""),
                    "local": payload.get("local", {}),
                    "enquadramento": payload.get("enquadramento", ""),
                    "pontos": payload.get("pontos", 0),
                    "valor": payload.get("valor_multa", 0),
                    "orgao": payload.get("orgao_autuador", ""),
                    "condutor": payload.get("condutor", {}),
                    "status": payload.get("status", "PENDENTE"),
                    "bloco_index": block.index,
                }
                estado["multas_pendentes"].append(multa)

            elif evento == VehicleEventType.SINISTRO.value:
                sinistro = {
                    "data": payload.get("data_sinistro", ""),
                    "tipo": payload.get("tipo", ""),
                    "perda_total": False,
                    "bo_numero": payload.get("bo_numero", ""),
                    "seguradora": payload.get("seguradora", {}),
                    "valor_dano": payload.get("valor_dano", 0),
                    "pecas_danificadas": payload.get("pecas_danificadas", []),
                    "reparado": payload.get("reparado", False),
                    "bloco_index": block.index,
                }
                estado["sinistros"].append(sinistro)

            elif evento == VehicleEventType.SINISTRO_PERDA_TOTAL.value:
                sinistro = {
                    "data": payload.get("data_sinistro", ""),
                    "tipo": payload.get("tipo", ""),
                    "perda_total": True,
                    "bo_numero": payload.get("bo_numero", ""),
                    "seguradora": payload.get("seguradora", {}),
                    "valor_indenizacao": payload.get("valor_indenizacao", 0),
                    "destino": payload.get("destino", ""),
                    "bloco_index": block.index,
                }
                estado["sinistros"].append(sinistro)
                estado["situacao"] = "PERDA_TOTAL"

            elif evento == VehicleEventType.TROCA_PECA.value:
                peca = payload.get("peca", {})
                peca_entry = {
                    "nome": peca.get("nome", ""),
                    "numero_serie": peca.get("numero_serie", ""),
                    "fabricante": peca.get("fabricante", ""),
                    "origem": peca.get("origem", ""),
                    "data_troca": payload.get("data_troca", ""),
                    "bloco_index": block.index,
                }
                estado["pecas_atuais"].append(peca_entry)

            elif evento == VehicleEventType.VALIDACAO_PECA.value:
                # Atualiza status da peça nos pecas_atuais
                peca_info = payload.get("peca", {})
                resultado = payload.get("resultado", "")
                for p in estado["pecas_atuais"]:
                    if p.get("numero_serie") == peca_info.get("numero_serie"):
                        p["status_validacao"] = resultado
                        p["data_validacao"] = payload.get("data_validacao", "")
                        break

            elif evento == VehicleEventType.TRANSFERENCIA_PROPRIEDADE.value:
                novo = payload.get("novo_proprietario", {})
                cpf_novo = novo.get("cpf", "")
                if cpf_novo:
                    # Limpa proprietários anteriores e adiciona o novo
                    estado["proprietarios"] = [{
                        "cpf": cpf_novo,
                        "nome": novo.get("nome", ""),
                        "participacao": 100.0,
                        "origem": "TRANSFERENCIA_DETRAN",
                    }]
                    transmissao = {
                        "tipo": "TRANSFERENCIA_DETRAN",
                        "data": payload.get("data_transferencia", ""),
                        "valor": 0,
                        "comprador": novo.get("nome", ""),
                        "vendedor": "",
                        "bloco": block.index,
                    }
                    estado["historico_transmissoes"].append(transmissao)

                odometro = payload.get("odometro_km", 0)
                if odometro > estado["odometro_km"]:
                    estado["odometro_km"] = odometro

            elif evento == VehicleEventType.REVISAO.value:
                odometro = payload.get("odometro_km", 0)
                if odometro > estado["odometro_km"]:
                    estado["odometro_km"] = odometro

            elif evento == VehicleEventType.MUDANCA_COR.value:
                estado["cor"] = payload.get("cor_nova", estado["cor"])

            elif evento == VehicleEventType.LICENCIAMENTO.value:
                pass  # Apenas registra, não altera estado consolidado

            elif evento == VehicleEventType.BAIXA.value:
                estado["situacao"] = "BAIXADO"

            elif evento == VehicleEventType.RECALL_DE_FABRICA.value:
                recall = {
                    "numero": payload.get("numero_recall", ""),
                    "fabricante": payload.get("fabricante", {}),
                    "peca_defeituosa": payload.get("peca_defeituosa", ""),
                    "descricao_defeito": payload.get("descricao_defeito", ""),
                    "risco": payload.get("risco", "MEDIO"),
                    "solucao": payload.get("solucao", ""),
                    "oficina_autorizada": payload.get("oficina_autorizada", ""),
                    "prazo_conclusao": payload.get("prazo_conclusao", ""),
                    "custo_para_proprietario": payload.get("custo_para_proprietario", 0.0),
                    "data_notificacao": payload.get("data_notificacao", ""),
                    "status": payload.get("status", "PENDENTE"),
                    "bloco_index": block.index,
                }
                estado["recalls_pendentes"].append(recall)

        return estado

    # ── Busca ─────────────────────────────────────────────────────────

    def get_event(self, index: int) -> Optional[Block]:
        """Retorna o bloco pelo índice."""
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None

    def get_events_by_type(self, event_type: str) -> list[Block]:
        """Retorna todos os blocos de um tipo de evento."""
        indices = self._event_index.get(event_type, [])
        return [self.chain[i] for i in indices if i < len(self.chain)]

    def get_last_event(self) -> Optional[Block]:
        """Retorna o último bloco da cadeia."""
        return self.chain[-1] if self.chain else None

    def get_genesis_block(self) -> Optional[Block]:
        """Retorna o bloco gênesis (fabricação)."""
        return self.chain[0] if self.chain else None

    def get_placa(self) -> str:
        """Retorna a placa atual do veículo."""
        genesis = self.get_genesis_block()
        if not genesis:
            return ""
        return genesis.data.get("payload", {}).get("placa", "")

    def get_renavan(self) -> str:
        """Retorna o RENAVAN do veículo."""
        genesis = self.get_genesis_block()
        if not genesis:
            return ""
        return genesis.data.get("payload", {}).get("renavan", "")

    def get_chassis(self) -> str:
        """Retorna o número do chassi do veículo."""
        genesis = self.get_genesis_block()
        if not genesis:
            return ""
        return genesis.data.get("payload", {}).get("chassis", "")

    def get_historico_completo(self) -> list[dict[str, Any]]:
        """Retorna timeline de todos os eventos do veículo."""
        timeline = []
        for block in self.chain:
            evento = block.data.get("evento_tipo", "DESCONHECIDO")
            payload = block.data.get("payload", {})
            ts = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp)
            )
            signed = block.has_signature()
            signer = block.signature.get("signer_label", "") if signed else ""
            timeline.append({
                "indice": block.index,
                "tipo": evento,
                "data_registro": ts,
                "hash": block.hash[:16],
                "assinado": signed,
                "emissor": signer,
                "dados": payload,
            })
        return timeline

    def get_fluxo_financeiro(self) -> list[dict[str, Any]]:
        """Retorna todas as transações financeiras do veículo."""
        transacoes = []
        for block in self.chain:
            evento = block.data.get("evento_tipo", "")
            payload = block.data.get("payload", {})
            ts = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp)
            )
            if evento == VehicleEventType.COMPRA_VENDA.value:
                transacoes.append({
                    "tipo": "COMPRA_VENDA",
                    "data": ts,
                    "valor": payload.get("valor_transacao", 0),
                    "comprador": payload.get("comprador", {}).get("nome", ""),
                    "vendedor": payload.get("vendedor", {}).get("nome", ""),
                    "bloco": block.index,
                })
            elif evento == VehicleEventType.LEILAO.value:
                if payload.get("lance_vencedor", 0) > 0:
                    transacoes.append({
                        "tipo": "LEILAO",
                        "data": ts,
                        "valor": payload.get("lance_vencedor", 0),
                        "vencedor": payload.get("vencedor", {}).get("nome", ""),
                        "bloco": block.index,
                    })
            elif evento == VehicleEventType.MULTA.value:
                transacoes.append({
                    "tipo": "MULTA",
                    "data": ts,
                    "valor": payload.get("valor_multa", 0),
                    "orgao": payload.get("orgao_autuador", ""),
                    "bloco": block.index,
                })
            elif evento == VehicleEventType.SINISTRO_PERDA_TOTAL.value:
                transacoes.append({
                    "tipo": "INDENIZACAO",
                    "data": ts,
                    "valor": payload.get("valor_indenizacao", 0),
                    "seguradora": payload.get("seguradora", {}).get("nome", ""),
                    "bloco": block.index,
                })
        return transacoes

    def get_garantias_ativas(self) -> list[dict[str, Any]]:
        """Retorna garantias/empréstimos vigentes."""
        estado = self.get_estado_atual()
        return [g for g in estado.get("garantias_ativas", []) if g.get("status") == "ATIVA"]

    def get_multas_pendentes(self) -> list[dict[str, Any]]:
        """Retorna multas pendentes de pagamento."""
        estado = self.get_estado_atual()
        return [m for m in estado.get("multas_pendentes", []) if m.get("status") == "PENDENTE"]

    # ── Validação ─────────────────────────────────────────────────────

    def validate(self, require_signatures: bool = True) -> tuple[bool, str]:
        """
        Valida toda a cadeia.

        Args:
            require_signatures: Se True, exige assinatura ECDSA em todos os blocos.

        Returns:
            Tuple (é_válida, mensagem).
        """
        if not self.chain:
            return False, "Cadeia vazia."

        genesis = self.chain[0]
        if genesis.previous_hash != "0" * 64:
            return False, "Hash do gênesis inválido."

        if not genesis.is_valid():
            return False, f"Bloco gênesis (#{genesis.index}) corrompido."

        if require_signatures and not genesis.has_signature():
            return False, f"Bloco gênesis (#{genesis.index}) sem assinatura."

        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.previous_hash != previous.hash:
                return (
                    False,
                    f"Bloco #{current.index}: previous_hash não confere.",
                )

            if current.hash != current.compute_hash():
                return (
                    False,
                    f"Bloco #{current.index}: hash próprio não confere.",
                )

            if not current.is_valid():
                return (
                    False,
                    f"Bloco #{current.index}: proof-of-work inválido.",
                )

            if current.index != i:
                return (
                    False,
                    f"Bloco #{current.index}: índice fora de sequência (esperado {i}).",
                )

            if require_signatures:
                if not current.has_signature():
                    return (
                        False,
                        f"Bloco #{current.index}: sem assinatura ECDSA.",
                    )
                sig = BlockSignature.from_dict(current.signature)
                ok, msg = self._verify_signature(current, sig)
                if not ok:
                    return (
                        False,
                        f"Bloco #{current.index}: assinatura inválida — {msg}",
                    )

        sig_count = sum(1 for b in self.chain if b.has_signature())
        suffix = f" | {sig_count}/{len(self.chain)} assinado(s)" if sig_count else ""
        return True, f"Cadeia válida — {len(self.chain)} bloco(s).{suffix}"

    def verify_all_signatures(self) -> tuple[bool, str]:
        """Verifica todas as assinaturas da cadeia."""
        unsigned = []
        invalid = []

        for block in self.chain:
            if not block.has_signature():
                unsigned.append(block.index)
                continue

            sig = BlockSignature.from_dict(block.signature)
            ok, msg = self._verify_signature(block, sig)
            if not ok:
                invalid.append((block.index, msg))

        lines = []
        if unsigned:
            lines.append(f"Sem assinatura: blocos {unsigned}")
        if invalid:
            for idx, msg in invalid:
                lines.append(f"Bloco #{idx}: {msg}")
        if not unsigned and not invalid:
            lines.append(f"Todas as {len(self.chain)} assinaturas ECDSA são válidas.")

        all_valid = not unsigned and not invalid
        return all_valid, " | ".join(lines)

    def _verify_signature(self, block: Block, sig: BlockSignature) -> tuple[bool, str]:
        """Verifica a assinatura de um bloco individual."""
        try:
            pubkey = SignatureVerifier._reconstruct_pubkey(sig.signer_pubkey)
            return SignatureVerifier.verify_block_signature(block, sig, pubkey)
        except Exception as e:
            return False, f"Erro na verificação: {e}"

    # ── Persistência ──────────────────────────────────────────────────

    def save_to_file(self, filepath: str) -> None:
        """Serializa a cadeia para JSON e salva em disco."""
        data = {
            "difficulty": self.difficulty,
            "chain": [b.to_dict() for b in self.chain],
        }
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    @classmethod
    def load_from_file(cls, filepath: str) -> "VehicleChain":
        """Carrega uma cadeia de um arquivo JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        chain = cls(difficulty=data["difficulty"])
        chain.chain = [Block.from_dict(b) for b in data["chain"]]
        for i, block in enumerate(chain.chain):
            evento = block.data.get("evento_tipo", "DESCONHECIDO")
            chain._index_event(evento, i)
        return chain

    # ── Privados ──────────────────────────────────────────────────────

    def _index_event(self, event_type: str, index: int) -> None:
        """Indexa um evento para busca rápida."""
        if event_type not in self._event_index:
            self._event_index[event_type] = []
        self._event_index[event_type].append(index)

    # ── Representação ─────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.chain)

    def __repr__(self) -> str:
        placa = self.get_placa()
        signer_info = f", signer={self._signer.keypair.label}" if self._signer else ""
        return f"VehicleChain(placa={placa}, blocks={len(self.chain)}, difficulty={self.difficulty}{signer_info})"
