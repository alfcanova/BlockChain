"""
blockchain_im/chain.py
Cadeia de blocos para eventos de imóveis.
Gênesis = terreno no espaço geográfico real.
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

from .events import PropertyEventType, PropertyChainProtector


class PropertyChain:
    """
    Cadeia de blocos para um imóvel.

    A cadeia começa com um bloco gênesis que representa o terreno
    no espaço geográfico real (matrícula, coordenadas, área).
    Cada bloco pode ser assinado digitalmente com ECDSA.
    """

    def __init__(self, difficulty: int = 2) -> None:
        self.difficulty = difficulty
        self.chain: list[Block] = []
        self._event_index: dict[str, list[int]] = {}
        self._default_keypair = generate_authority_keypair("cartorio_imoveis")
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

    def create_genesis(self, terreno_data: dict[str, Any]) -> Block:
        """
        Cria o bloco gênesis com dados do terreno.
        O bloco é obrigatoriamente assinado com ECDSA.

        Args:
            terreno_data: Dicionário com dados do terreno.

        Raises:
            ValueError: Se nenhum signer estiver configurado.

        Returns:
            O bloco gênesis criado e assinado.
        """
        if not self._signer:
            raise ValueError("Cadeia requer assinador configurado (set_signer) para registrar operações.")
        genesis = Block(
            index=0,
            timestamp=time.time(),
            data={
                "evento_tipo": PropertyEventType.TERRENO.value,
                "payload": terreno_data,
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
        self._index_event(PropertyEventType.TERRENO.value, 0)
        return genesis

    # ── Adição de blocos ──────────────────────────────────────────────

    def add_event(self, event_type: str, payload: dict[str, Any]) -> Block:
        """
        Adiciona um novo evento à cadeia.

        Args:
            event_type: Tipo do evento (ex: "CONSTRUCAO", "COMPRA_VENDA").
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
        if not PropertyChainProtector.pode_adicionar(event_type, estado.get("situacao", "LIVRE")):
            raise ValueError(
                f"Evento '{event_type}' bloqueado para imóvel com estado '{estado.get('situacao')}'."
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
        Retorna o estado consolidado do imóvel.
        Calcula a partir de todos os blocos da cadeia.
        """
        if not self.chain:
            return {}

        genesis = self.chain[0]
        payload_genesis = genesis.data.get("payload", {})

        estado = {
            "matricula": payload_genesis.get("matricula", ""),
            "endereco": payload_genesis.get("endereco", {}),
            "coordenadas": payload_genesis.get("coordenadas", {}),
            "area_terreno_m2": payload_genesis.get("area_terreno_m2", 0.0),
            "area_construida_m2": payload_genesis.get("area_construida_m2", 0.0),
            "situacao": payload_genesis.get("situacao", "LIVRE"),
            "proprietarios": list(payload_genesis.get("proprietarios", [])),
            "onus_reais": list(payload_genesis.get("onus_reais", [])),
            "certidoes": list(payload_genesis.get("certidoes", [])),
            "codigo_iptu": payload_genesis.get("codigo_iptu", ""),
            "zoneamento": payload_genesis.get("zoneamento", ""),
            "uso_permitido": list(payload_genesis.get("uso_permitido", [])),
            "altura_maxima": payload_genesis.get("altura_maxima", 0.0),
            "taxa_ocupacao": payload_genesis.get("taxa_ocupacao", 0.0),
            "cacau_permitido": payload_genesis.get("cacau_permitido", 0.0),
        }

        # Processa cada evento subseqüente
        for block in self.chain[1:]:
            evento = block.data.get("evento_tipo", "")
            payload = block.data.get("payload", {})

            if evento == PropertyEventType.CONSTRUCAO.value:
                estado["area_construida_m2"] += payload.get("area_construida_m2", 0)
                if estado["area_construida_m2"] > 0:
                    estado["situacao"] = "CONSTRUIDO"

            elif evento == PropertyEventType.DEMOLICAO.value:
                estado["area_construida_m2"] -= payload.get("area_demolida_m2", 0)
                if estado["area_construida_m2"] <= 0:
                    estado["area_construida_m2"] = 0
                    estado["situacao"] = "LIVRE"

            elif evento == PropertyEventType.REFORMA.value:
                delta = payload.get("delta_area_m2", 0)
                estado["area_construida_m2"] += delta
                if estado["area_construida_m2"] < 0:
                    estado["area_construida_m2"] = 0

            elif evento == PropertyEventType.COMPRA_VENDA.value:
                comprador = payload.get("comprador", {})
                vendedor = payload.get("vendedor", {})
                if comprador.get("cpf"):
                    # Remove vendedor, adiciona comprador
                    cpf_vendedor = vendedor.get("cpf", "")
                    cpf_comprador = comprador.get("cpf", "")
                    estado["proprietarios"] = [
                        p for p in estado["proprietarios"]
                        if p.get("cpf") != cpf_vendedor
                    ]
                    # Verifica se já existe
                    existe = any(p.get("cpf") == cpf_comprador for p in estado["proprietarios"])
                    if not existe:
                        estado["proprietarios"].append({
                            "cpf": cpf_comprador,
                            "nome": comprador.get("nome", ""),
                            "participacao": 100.0,
                            "origem": "COMPRA",
                        })

            elif evento == PropertyEventType.DOACAO.value:
                donatario = payload.get("donatario", {})
                doador = payload.get("doador", {})
                if donatario.get("cpf"):
                    cpf_doador = doador.get("cpf", "")
                    cpf_donatario = donatario.get("cpf", "")
                    estado["proprietarios"] = [
                        p for p in estado["proprietarios"]
                        if p.get("cpf") != cpf_doador
                    ]
                    existe = any(p.get("cpf") == cpf_donatario for p in estado["proprietarios"])
                    if not existe:
                        estado["proprietarios"].append({
                            "cpf": cpf_donatario,
                            "nome": donatario.get("nome", ""),
                            "participacao": 100.0,
                            "origem": "DOACAO",
                        })

            elif evento == PropertyEventType.HERANCA.value:
                herdeiros = payload.get("herdeiros", [])
                inventariado = payload.get("inventariado", {})
                cpf_inventariado = inventariado.get("cpf", "")
                # Remove inventariado
                estado["proprietarios"] = [
                    p for p in estado["proprietarios"]
                    if p.get("cpf") != cpf_inventariado
                ]
                # Adiciona herdeiros
                for h in herdeiros:
                    cpf_h = h.get("cpf", "")
                    if cpf_h:
                        existe = any(p.get("cpf") == cpf_h for p in estado["proprietarios"])
                        if not existe:
                            estado["proprietarios"].append({
                                "cpf": cpf_h,
                                "nome": h.get("nome", ""),
                                "participacao": h.get("participacao", 0),
                                "origem": "HERANCA",
                            })

            elif evento == PropertyEventType.PROPRIETARIO.value:
                prop = payload.get("proprietario", {})
                cpf = prop.get("cpf", "")
                participacao = payload.get("participacao", 0)
                if cpf:
                    existe = any(p.get("cpf") == cpf for p in estado["proprietarios"])
                    if participacao <= 0:
                        # Remoção
                        estado["proprietarios"] = [
                            p for p in estado["proprietarios"]
                            if p.get("cpf") != cpf
                        ]
                    elif existe:
                        # Atualização
                        for p in estado["proprietarios"]:
                            if p.get("cpf") == cpf:
                                p["participacao"] = participacao
                                p["nome"] = prop.get("nome", p.get("nome", ""))
                    else:
                        # Adição
                        estado["proprietarios"].append({
                            "cpf": cpf,
                            "nome": prop.get("nome", ""),
                            "participacao": participacao,
                            "origem": payload.get("origem", ""),
                        })

            elif evento == PropertyEventType.GARANTIA.value:
                onus = {
                    "tipo": "GARANTIA",
                    "credor": payload.get("credor", {}),
                    "valor": payload.get("valor_garantia", 0),
                    "data": payload.get("data_garantia", ""),
                    "vencimento": payload.get("data_vencimento", ""),
                    "tipo_garantia": payload.get("tipo_garantia", ""),
                    "status": "ATIVA",
                    "bloco_index": block.index,
                }
                estado["onus_reais"].append(onus)
                estado["situacao"] = "GARANTIDO"

            elif evento == PropertyEventType.QUITACAO.value:
                idx = payload.get("garantia_index", -1)
                if 0 <= idx < len(estado["onus_reais"]):
                    estado["onus_reais"][idx]["status"] = "QUITADA"
                # Verifica se ainda há garantias ativas
                tem_ativa = any(
                    o.get("status") == "ATIVA"
                    for o in estado["onus_reais"]
                )
                if not tem_ativa and estado["situacao"] == "GARANTIDO":
                    estado["situacao"] = "CONSTRUIDO" if estado["area_construida_m2"] > 0 else "LIVRE"

            elif evento == PropertyEventType.LEILAO.value:
                if payload.get("lance_vencedor", 0) > 0:
                    vencedor = payload.get("vencedor", {})
                    cpf_v = vencedor.get("cpf", "")
                    if cpf_v:
                        estado["proprietarios"] = [{
                            "cpf": cpf_v,
                            "nome": vencedor.get("nome", ""),
                            "participacao": 100.0,
                            "origem": "LEILAO",
                        }]
                    estado["situacao"] = "LIVRE"
                else:
                    estado["situacao"] = "EM_LEILAO"

            elif evento == PropertyEventType.CONFISCO.value:
                estado["situacao"] = "CONFISCADO"
                estado["proprietarios"] = []

            elif evento == PropertyEventType.PENHORA.value:
                onus = {
                    "tipo": "PENHORA",
                    "autoridade": payload.get("autoridade", ""),
                    "processo": payload.get("processo_numero", ""),
                    "valor": payload.get("valor_penhorado", 0),
                    "data": payload.get("data_penhora", ""),
                    "status": "ATIVA",
                    "bloco_index": block.index,
                }
                estado["onus_reais"].append(onus)

            elif evento == PropertyEventType.ZONEAMENTO.value:
                estado["zoneamento"] = payload.get("zoneamento_novo", "")

            elif evento == PropertyEventType.IPTU.value:
                estado["codigo_iptu"] = payload.get("codigo_iptu", "")

            elif evento == PropertyEventType.CERTIDAO.value:
                cert = {
                    "tipo": payload.get("tipo_certidao", ""),
                    "data": payload.get("data_emissao", ""),
                    "numero": payload.get("numero", ""),
                    "orgao": payload.get("orgao_emissor", ""),
                }
                estado["certidoes"].append(cert)

            elif evento == PropertyEventType.MATRICULA.value:
                estado["matricula"] = payload.get("nova_matricula", "")

            elif evento == PropertyEventType.LOTEAMENTO.value:
                estado["situacao"] = "LOTEADO"

            elif evento == PropertyEventType.DESMEMBRAMENTO.value:
                estado["situacao"] = "DESMEMBRADO"

            elif evento == PropertyEventType.FUSAO.value:
                estado["area_terreno_m2"] = payload.get("area_total_m2", estado["area_terreno_m2"])
                if payload.get("endereco"):
                    estado["endereco"] = {"logradouro": payload["endereco"]}

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
        """Retorna o bloco gênesis (terreno)."""
        return self.chain[0] if self.chain else None

    def get_matricula(self) -> str:
        """Retorna a matrícula atual do imóvel."""
        genesis = self.get_genesis_block()
        if not genesis:
            return ""
        matricula = genesis.data.get("payload", {}).get("matricula", "")
        # Verifica se houve atualização de matrícula
        for block in self.chain[1:]:
            if block.data.get("evento_tipo") == PropertyEventType.MATRICULA.value:
                matricula = block.data.get("payload", {}).get("nova_matricula", matricula)
        return matricula

    def get_historico_completo(self) -> list[dict[str, Any]]:
        """
        Retorna timeline de todos os eventos do imóvel.
        """
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
        """Retorna todas as transações financeiras do imóvel."""
        transacoes = []
        for block in self.chain:
            evento = block.data.get("evento_tipo", "")
            payload = block.data.get("payload", {})
            ts = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp)
            )
            if evento == PropertyEventType.COMPRA_VENDA.value:
                transacoes.append({
                    "tipo": "COMPRA_VENDA",
                    "data": ts,
                    "valor": payload.get("valor_transacao", 0),
                    "comprador": payload.get("comprador", {}).get("nome", ""),
                    "vendedor": payload.get("vendedor", {}).get("nome", ""),
                    "bloco": block.index,
                })
            elif evento == PropertyEventType.LEILAO.value:
                if payload.get("lance_vencedor", 0) > 0:
                    transacoes.append({
                        "tipo": "LEILAO",
                        "data": ts,
                        "valor": payload.get("lance_vencedor", 0),
                        "vencedor": payload.get("vencedor", {}).get("nome", ""),
                        "bloco": block.index,
                    })
        return transacoes

    def get_onus_ativos(self) -> list[dict[str, Any]]:
        """Retorna ônus reais vigentes."""
        estado = self.get_estado_atual()
        return [o for o in estado.get("onus_reais", []) if o.get("status") == "ATIVA"]

    # ── Validação ─────────────────────────────────────────────────────

    def validate(self, require_signatures: bool = True) -> tuple[bool, str]:
        """
        Valida toda a cadeia.

        Args:
            require_signatures: Se True (padrão), exige assinatura ECDSA em todos os blocos.

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
    def load_from_file(cls, filepath: str) -> "PropertyChain":
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
        matricula = self.get_matricula()
        signer_info = f", signer={self._signer.keypair.label}" if self._signer else ""
        return f"PropertyChain(matricula={matricula}, blocks={len(self.chain)}, difficulty={self.difficulty}{signer_info})"
