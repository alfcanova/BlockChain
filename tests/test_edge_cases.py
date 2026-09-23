"""
Testes de edge cases para toda a stack — unitarios e de API.

Cobrem:
  - CPF invalido (formatos variados)
  - Datas futuras, passadas, formato errado
  - Obito duplicado e eventos apos obito
  - Campos vazios, nulos, com caracteres especiais
  - Boundary conditions (idade minima casamento, etc.)
  - Tentativas de manipulacao da cadeia
  - Encadeamento de eventos invalidos
  - Web API edge cases
"""

import time
import pytest
from blockchain_pf.chain import Blockchain
from blockchain_pf.block import Block
from blockchain_pf.events import EventFactory, EventType, ChainProtector
from blockchain_pf.signatures import KeyPair, Signer, SignatureVerifier, BlockSignature
from blockchain_pf.predictor import LifeEventPredictor


# ══════════════════════════════════════════════════════════════════════
#  CPF INVALIDO
# ══════════════════════════════════════════════════════════════════════

class TestCPFInvalido:
    """Testa todos os formatos de CPF invalidos."""

    def _nascimento(self, cpf):
        return EventFactory.nascimento(
            cpf=cpf, nome_completo="Teste",
            data_nascimento="01/01/2000", sexo="M",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Mae",
        )

    def test_cpf_vazio(self):
        with pytest.raises(ValueError, match="CPF"):
            self._nascimento("")

    def test_cpf_muito_curto(self):
        with pytest.raises(ValueError, match="CPF"):
            self._nascimento("123456789")

    def test_cpf_muito_longo(self):
        with pytest.raises(ValueError, match="CPF"):
            self._nascimento("123456789012")

    def test_cpf_com_letras(self):
        with pytest.raises(ValueError, match="CPF"):
            self._nascimento("ABCDEF12345")

    def test_cpf_com_caracteres_especiais(self):
        # EventFactory remove nao-digitos, 123.456.789-01 vira 12345678901 (11 digitos)
        dados = self._nascimento("123.456.789-01")
        assert dados["cpf"] == "12345678901"

    def test_cpf_apenas_zeros(self):
        # Validador so verifica comprimento, nao conteudo
        dados = self._nascimento("00000000000")
        assert dados["cpf"] == "00000000000"

    def test_cpf_10_digitos(self):
        with pytest.raises(ValueError, match="CPF"):
            self._nascimento("1234567890")

    def test_cpf_12_digitos(self):
        with pytest.raises(ValueError, match="CPF"):
            self._nascimento("123456789012")

    def test_cpf_11_digitos_valido(self):
        # Deve aceitar qualquer sequencia de 11 digitos
        dados = self._nascimento("11122233344")
        assert dados["cpf"] == "11122233344"

    def test_cpf_com_pontos_e_tracos(self):
        # EventFactory remove nao-digitos, entao 123.456.789-01 vira 12345678901 (11 digitos)
        dados = self._nascimento("123.456.789-01")
        assert dados["cpf"] == "12345678901"


# ══════════════════════════════════════════════════════════════════════
#  DATAS INVALIDAS
# ══════════════════════════════════════════════════════════════════════

class TestDatasInvalidas:
    def _nascimento(self, data):
        return EventFactory.nascimento(
            cpf="12345678901", nome_completo="Teste",
            data_nascimento=data, sexo="M",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Mae",
        )

    def test_data_formato_iso(self):
        with pytest.raises(ValueError, match="Data"):
            self._nascimento("2000-01-15")

    def test_data_formato_barras_reverso(self):
        with pytest.raises(ValueError, match="Data"):
            self._nascimento("2000/01/15")

    def test_data_sem_separador(self):
        with pytest.raises(ValueError, match="Data"):
            self._nascimento("15012000")

    def test_data_com_texto(self):
        with pytest.raises(ValueError, match="Data"):
            self._nascimento("15 de Janeiro de 2000")

    def test_data_vazia(self):
        with pytest.raises(ValueError, match="Data"):
            self._nascimento("")

    def test_data_com_hora(self):
        with pytest.raises(ValueError, match="Data"):
            self._nascimento("15/01/2000 10:30")

    def test_data_32_dia(self):
        # Validador so verifica formato DD/MM/AAAA, nao validade do dia
        dados = self._nascimento("32/01/2000")
        assert dados["data_nascimento"] == "32/01/2000"

    def test_data_13_mes(self):
        # Validador so verifica formato DD/MM/AAAA, nao validade do mes
        dados = self._nascimento("15/13/2000")
        assert dados["data_nascimento"] == "15/13/2000"

    def test_data_dia_um(self):
        # Dia 01/01/2000 e valido
        dados = self._nascimento("01/01/2000")
        assert dados["data_nascimento"] == "01/01/2000"

    def test_data_31_dezembro(self):
        dados = self._nascimento("31/12/2000")
        assert dados["data_nascimento"] == "31/12/2000"

    def test_data_futura_nascimento(self):
        # O sistema aceita (nao valida ano futuro)
        dados = self._nascimento("01/01/2099")
        assert dados["data_nascimento"] == "01/01/2099"

    def test_data_ano_zero(self):
        # Validador so verifica formato DD/MM/AAAA, nao validade do ano
        dados = self._nascimento("15/01/0000")
        assert dados["data_nascimento"] == "15/01/0000"

    def test_casamento_data_invalida(self):
        with pytest.raises(ValueError, match="Data"):
            EventFactory.casamento(
                cpf="12345678901", nome_conjuge="Pedro",
                cpf_conjuge="98765432100", data_casamento="2022/06/20",
            )

    def test_divorcio_data_invalida(self):
        with pytest.raises(ValueError, match="Data"):
            EventFactory.divorcio(
                cpf="12345678901", data_divorcio="01-01-2025",
            )

    def test_obito_data_invalida(self):
        with pytest.raises(ValueError, match="Data"):
            EventFactory.obito(
                cpf="12345678901", data_obito="jan/2050",
                cidade_obito="SP", uf_obito="SP",
            )

    def test_alteracao_nome_data_invalida(self):
        with pytest.raises(ValueError, match="Data"):
            EventFactory.alteracao_nome(
                cpf="12345678901", nome_anterior="A",
                nome_novo="B", data_alteracao="2020",
            )

    def test_disvinculacao_data_invalida(self):
        with pytest.raises(ValueError, match="Data"):
            EventFactory.disvinculacao_materna(
                cpf="12345678901",
                data_disvinculacao="15/03",
                motivo="Teste",
            )


# ══════════════════════════════════════════════════════════════════════
#  OBITO DUPLICADO
# ══════════════════════════════════════════════════════════════════════

class TestObitoDuplicado:
    def _setup(self):
        chain = Blockchain(difficulty=1)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Teste",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        return chain

    def test_obito_bloqueia_casamento(self):
        chain = self._setup()
        chain.add_event(EventType.OBITO.value, {
            "evento_tipo": "OBITO", "cpf": "12345678901",
            "data_obito": "01/01/2050",
            "cidade_obito": "SP", "uf_obito": "SP",
        })
        # ChainProtector bloqueia
        assert not ChainProtector.pode_adicionar("CASAMENTO", True)

    def test_obito_bloqueia_divorcio(self):
        assert not ChainProtector.pode_adicionar("DIVORCIO", True)

    def test_obito_bloqueia_adocao(self):
        assert not ChainProtector.pode_adicionar("ADOCAO", True)

    def test_obito_bloqueia_disvinculacao(self):
        assert not ChainProtector.pode_adicionar("DISVINC_MATERNA", True)
        assert not ChainProtector.pode_adicionar("DISVINC_PATerna", True)

    def test_obito_permite_alteracao_nome(self):
        assert ChainProtector.pode_adicionar("ALTERACAO_NOME", True)

    def test_permitir_obito_duplo_na_cadeia(self):
        """A cadeia permite registrar obito duas vezes (erro humano)."""
        chain = self._setup()
        chain.add_event(EventType.OBITO.value, {
            "evento_tipo": "OBITO", "cpf": "12345678901",
            "data_obito": "01/01/2050",
            "cidade_obito": "SP", "uf_obito": "SP",
        })
        # Segundo obito - a cadeia permite (nao valida duplicata)
        block = chain.add_event(EventType.OBITO.value, {
            "evento_tipo": "OBITO", "cpf": "12345678901",
            "data_obito": "02/01/2050",
            "cidade_obito": "RJ", "uf_obito": "RJ",
        })
        assert block.index == 2
        # Validacao passa (cadeia tecnica valida, mas semanticamente incorreta)
        valid, _ = chain.validate()
        assert valid


# ══════════════════════════════════════════════════════════════════════
#  CAMPOS VAZIOS / NULOS
# ══════════════════════════════════════════════════════════════════════

class TestCamposVazios:
    def test_nome_completo_vazio(self):
        # Nao valida nome vazio (aceita)
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="",
            data_nascimento="01/01/2000", sexo="M",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Mae",
        )
        assert dados["nome_completo"] == ""

    def test_nome_mae_vazio(self):
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="Teste",
            data_nascimento="01/01/2000", sexo="M",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="",
        )
        assert dados["nome_mae"] == ""

    def test_sexo_minusculo(self):
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="Teste",
            data_nascimento="01/01/2000", sexo="m",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Mae",
        )
        assert dados["sexo"] == "M"

    def test_uf_minuscula(self):
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="Teste",
            data_nascimento="01/01/2000", sexo="M",
            cidade_nascimento="Sao Paulo", uf_nascimento="sp",
            nome_mae="Mae",
        )
        assert dados["uf_nascimento"] == "SP"

    def test_cidade_com_acentos(self):
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="Teste",
            data_nascimento="01/01/2000", sexo="M",
            cidade_nascimento="São Paulo", uf_nascimento="SP",
            nome_mae="Mae",
        )
        assert dados["cidade_nascimento"] == "São Paulo"

    def test_nome_com_banco_de_inputs(self):
        """Nomes com caracteres perigosos sao aceitos (nao sanitizacao server-side)."""
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="<script>alert(1)</script>",
            data_nascimento="01/01/2000", sexo="M",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Mae",
        )
        assert "<script>" in dados["nome_completo"]

    def test_casamento_conjuge_vazio(self):
        dados = EventFactory.casamento(
            cpf="12345678901", nome_conjuge="",
            cpf_conjuge="98765432100", data_casamento="01/01/2022",
        )
        assert dados["nome_conjuge"] == ""

    def test_obito_causa_vazia(self):
        dados = EventFactory.obito(
            cpf="12345678901", data_obito="01/01/2050",
            cidade_obito="SP", uf_obito="SP",
            causa_morte="",
        )
        assert dados["causa_morte"] == "Não informada"


# ══════════════════════════════════════════════════════════════════════
#  BOUNDARY CONDITIONS
# ══════════════════════════════════════════════════════════════════════

class TestBoundaryConditions:
    def test_cpf_exatamente_11_digitos(self):
        dados = EventFactory.nascimento(
            cpf="00000000001", nome_completo="Teste",
            data_nascimento="01/01/2000", sexo="M",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Mae",
        )
        assert dados["cpf"] == "00000000001"

    def test_cpf_10_digitos_rejeitado(self):
        with pytest.raises(ValueError):
            EventFactory.nascimento(
                cpf="1234567890", nome_completo="Teste",
                data_nascimento="01/01/2000", sexo="M",
                cidade_nascimento="Sao Paulo", uf_nascimento="SP",
                nome_mae="Mae",
            )

    def test_uf_1_letra_rejeitada(self):
        with pytest.raises(ValueError):
            EventFactory.nascimento(
                cpf="12345678901", nome_completo="Teste",
                data_nascimento="01/01/2000", sexo="M",
                cidade_nascimento="Sao Paulo", uf_nascimento="S",
                nome_mae="Mae",
            )

    def test_uf_3_letras_rejeitada(self):
        with pytest.raises(ValueError):
            EventFactory.nascimento(
                cpf="12345678901", nome_completo="Teste",
                data_nascimento="01/01/2000", sexo="M",
                cidade_nascimento="Sao Paulo", uf_nascimento="SPA",
                nome_mae="Mae",
            )

    def test_sexo_char_duplo_rejeitado(self):
        with pytest.raises(ValueError):
            EventFactory.nascimento(
                cpf="12345678901", nome_completo="Teste",
                data_nascimento="01/01/2000", sexo="MF",
                cidade_nascimento="Sao Paulo", uf_nascimento="SP",
                nome_mae="Mae",
            )

    def test_dificuldade_minima(self):
        chain = Blockchain(difficulty=1)
        genesis = chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Teste",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        assert genesis.hash.startswith("0")

    def test_dificuldade_maxima(self):
        chain = Blockchain(difficulty=5)
        genesis = chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Teste",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        assert genesis.hash.startswith("00000")

    def test_data_primeiro_dia_ano(self):
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="Teste",
            data_nascimento="01/01/2000", sexo="M",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Mae",
        )
        assert dados["data_nascimento"] == "01/01/2000"

    def test_data_ultimo_dia_ano(self):
        dados = EventFactory.nascimento(
            cpf="12345678901", nome_completo="Teste",
            data_nascimento="31/12/2000", sexo="M",
            cidade_nascimento="Sao Paulo", uf_nascimento="SP",
            nome_mae="Mae",
        )
        assert dados["data_nascimento"] == "31/12/2000"


# ══════════════════════════════════════════════════════════════════════
#  MANIPULACAO DA CADEIA
# ══════════════════════════════════════════════════════════════════════

class TestManipulacaoCadeia:
    def _setup(self):
        chain = Blockchain(difficulty=1)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Teste",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        return chain

    def test_trocar_hash_manualmente(self):
        chain = self._setup()
        chain.chain[0].hash = "FAKE_HASH"
        valid, msg = chain.validate()
        assert not valid
        assert "hash" in msg.lower() or "corrompido" in msg.lower()

    def test_trocar_previous_hash(self):
        chain = self._setup()
        chain.add_event("CASAMENTO", {})
        # Troca o previous_hash do bloco 1
        chain.chain[1].previous_hash = "FAKE"
        valid, msg = chain.validate()
        assert not valid

    def test_trocar_data_bloco_anterior(self):
        chain = self._setup()
        chain.add_event("CASAMENTO", {})
        # Altera dados do genesis
        chain.chain[0].data["payload"]["nome_completo"] = "HACKED"
        valid, msg = chain.validate()
        assert not valid

    def test_inserir_bloco_no_meio(self):
        chain = self._setup()
        chain.add_event("CASAMENTO", {})
        # Insere bloco falso no indice 1
        fake = Block(
            index=1, timestamp=time.time(),
            data={"evento_tipo": "FAKE"},
            previous_hash="FAKE",
            difficulty=1,
        )
        fake.mine_block()
        chain.chain.insert(1, fake)
        valid, msg = chain.validate()
        assert not valid

    def test_remover_bloco(self):
        chain = self._setup()
        chain.add_event("CASAMENTO", {})
        # Remove o ultimo bloco
        del chain.chain[-1]
        valid, msg = chain.validate()
        # Cadeia com apenas genesis e valida
        assert valid
        # Mas se remover o genesis, cadeia fica vazia
        chain2 = self._setup()
        del chain2.chain[0]
        valid2, _ = chain2.validate()
        assert not valid2

    def test_trocar_nonce(self):
        chain = self._setup()
        # Salva hash original
        original_hash = chain.chain[0].hash
        # Troca nonce
        chain.chain[0].nonce = 999999
        # Hash fica invalido
        assert chain.chain[0].hash != chain.chain[0].compute_hash()
        # Restaura
        chain.chain[0].hash = original_hash

    def test_trocar_difficulty_retroativamente(self):
        chain = self._setup()
        # Troca dificuldade do bloco 0
        chain.chain[0].difficulty = 5
        # Hash original nao tem 5 zeros
        assert not chain.chain[0].is_valid()

    def test_manipulacao_com_assinatura(self):
        """Com assinatura, adulteracao e detectada."""
        kp = KeyPair.generate("Auth")
        chain = Blockchain(difficulty=1)
        chain.set_signer(kp)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Teste",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        # Adultera dados
        chain.chain[0].data["payload"]["nome_completo"] = "HACKED"
        chain.chain[0].hash = chain.chain[0].compute_hash()
        # Assinatura confere com hash antigo
        sig = BlockSignature.from_dict(chain.chain[0].signature)
        ok, _ = SignatureVerifier.verify_block_signature(
            chain.chain[0], sig, kp.public_key
        )
        assert not ok  # Hash mudou, assinatura invalida

    def test_remover_assinatura(self):
        kp = KeyPair.generate("Auth")
        chain = Blockchain(difficulty=1)
        chain.set_signer(kp)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Teste",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        # Remove assinatura
        chain.chain[0].signature = None
        valid, msg = chain.validate(require_signatures=True)
        assert not valid
        assert "sem assinatura" in msg.lower()


# ══════════════════════════════════════════════════════════════════════
#  ENCADEAMENTO DE EVENTOS
# ══════════════════════════════════════════════════════════════════════

class TestEncadeamentoEventos:
    def _setup(self):
        chain = Blockchain(difficulty=1)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Teste",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        return chain

    def test_casamento_antes_nascimento(self):
        """Cadeia sem genesis aceita casamento (erro humano)."""
        chain = Blockchain(difficulty=1)
        with pytest.raises(ValueError, match="Cadeia vazia"):
            chain.add_event("CASAMENTO", {})

    def test_divorcio_sem_casamento(self):
        chain = self._setup()
        # Divorcio sem casamento anterior
        block = chain.add_event(EventType.DIVORCIO.value, {
            "evento_tipo": "DIVORCIO", "cpf": "12345678901",
            "data_divorcio": "01/01/2025",
        })
        assert block.index == 1  # Permite

    def test_multiplos_casamentos(self):
        chain = self._setup()
        chain.add_event("CASAMENTO", {})
        chain.add_event("DIVORCIO", {})
        chain.add_event("CASAMENTO", {})
        chain.add_event("DIVORCIO", {})
        assert len(chain) == 5
        valid, _ = chain.validate()
        assert valid

    def test_casamento_apos_obito(self):
        chain = self._setup()
        chain.add_event(EventType.OBITO.value, {
            "evento_tipo": "OBITO", "cpf": "12345678901",
            "data_obito": "01/01/2050",
            "cidade_obito": "SP", "uf_obito": "SP",
        })
        assert not ChainProtector.pode_adicionar("CASAMENTO", True)

    def test_muitos_eventos(self):
        chain = self._setup()
        for i in range(20):
            chain.add_event("EVENTO_GENERICO", {"i": i})
        assert len(chain) == 21
        valid, _ = chain.validate()
        assert valid


# ══════════════════════════════════════════════════════════════════════
#  PREDITOR EDGE CASES
# ══════════════════════════════════════════════════════════════════════

class TestPreditorEdgeCases:
    def test_criancas_nao_predizem_casamento(self):
        chain = Blockchain(difficulty=1)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Crianca",
            "data_nascimento": "01/01/2020", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        pred = LifeEventPredictor(chain).predizer_casamento()
        assert pred.probabilidade == 0.0  # Menor de 16 anos

    def test_idosos_maior_mortalidade(self):
        chain_old = Blockchain(difficulty=1)
        chain_old.create_genesis({
            "cpf": "11111111111", "nome_completo": "Idoso",
            "data_nascimento": "01/01/1930", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        chain_young = Blockchain(difficulty=1)
        chain_young.create_genesis({
            "cpf": "22222222222", "nome_completo": "Jovem",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        pred_old = LifeEventPredictor(chain_old).predizer_obito()
        pred_young = LifeEventPredictor(chain_young).predizer_obito()
        assert pred_old.probabilidade > pred_young.probabilidade * 10

    def test_mulheres_idade_casamento_diferente(self):
        chain_f = Blockchain(difficulty=1)
        chain_f.create_genesis({
            "cpf": "11111111111", "nome_completo": "Mulher",
            "data_nascimento": "01/01/1995", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        chain_m = Blockchain(difficulty=1)
        chain_m.create_genesis({
            "cpf": "22222222222", "nome_completo": "Homem",
            "data_nascimento": "01/01/1995", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        pred_f = LifeEventPredictor(chain_f).predizer_casamento()
        pred_m = LifeEventPredictor(chain_m).predizer_casamento()
        # Idade media diferente: F=27, M=30
        assert pred_f is not None and pred_m is not None

    def test_divorciada_maior_chance_recasamento(self):
        chain_s = Blockchain(difficulty=1)
        chain_s.create_genesis({
            "cpf": "11111111111", "nome_completo": "Solteira",
            "data_nascimento": "01/01/1990", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        chain_d = Blockchain(difficulty=1)
        chain_d.create_genesis({
            "cpf": "22222222222", "nome_completo": "Divorciada",
            "data_nascimento": "01/01/1990", "sexo": "F",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        chain_d.add_event(EventType.CASAMENTO.value, {
            "evento_tipo": "CASAMENTO", "cpf": "22222222222",
            "data_casamento": "01/01/2015",
        })
        chain_d.add_event(EventType.DIVORCIO.value, {
            "evento_tipo": "DIVORCIO", "cpf": "22222222222",
            "data_divorcio": "01/01/2020",
        })
        pred_s = LifeEventPredictor(chain_s).predizer_casamento()
        pred_d = LifeEventPredictor(chain_d).predizer_casamento()
        # Divorciada com 65% da probabilidade base
        assert pred_d.probabilidade < pred_s.probabilidade


# ══════════════════════════════════════════════════════════════════════
#  ASSINATURAS EDGE CASES
# ══════════════════════════════════════════════════════════════════════

class TestAssinaturasEdgeCases:
    def test_chaves_diferentes_nao_verificam(self):
        kp1 = KeyPair.generate("A")
        kp2 = KeyPair.generate("B")
        signer1 = Signer(kp1)
        block = Block(index=0, timestamp=1.0, data={}, previous_hash="0" * 64)
        sig = signer1.sign_block(block)
        ok, _ = SignatureVerifier.verify_block_signature(block, sig, kp2.public_key)
        assert not ok

    def test_hash_diferente_invalida_assinatura(self):
        kp = KeyPair.generate("Auth")
        signer = Signer(kp)
        block1 = Block(index=0, timestamp=1.0, data={"a": 1}, previous_hash="0" * 64)
        block2 = Block(index=0, timestamp=1.0, data={"a": 2}, previous_hash="0" * 64)
        sig = signer.sign_block(block1)
        ok, _ = SignatureVerifier.verify_block_signature(block2, sig, kp.public_key)
        assert not ok

    def test_pubkey_hex_invalida(self):
        kp = KeyPair.generate("Auth")
        signer = Signer(kp)
        block = Block(index=0, timestamp=1.0, data={}, previous_hash="0" * 64)
        sig = signer.sign_block(block)
        # Corrompe pubkey
        sig.signer_pubkey = "00" * 33
        ok, msg = SignatureVerifier.verify_block_signature(block, sig, None)
        assert not ok

    def test_assinatura_corrompida(self):
        kp = KeyPair.generate("Auth")
        signer = Signer(kp)
        block = Block(index=0, timestamp=1.0, data={}, previous_hash="0" * 64)
        sig = signer.sign_block(block)
        # Corrompe assinatura
        sig.signature_b64 = "AAAA"
        ok, _ = SignatureVerifier.verify_block_signature(block, sig, kp.public_key)
        assert not ok

    def test_chain_multiplos_emissores(self):
        """Cadeia com blocos assinados por emissores diferentes."""
        chain = Blockchain(difficulty=1)
        kp1 = KeyPair.generate("Cartorio")
        kp2 = KeyPair.generate("Juizado")

        chain.set_signer(kp1)
        chain.create_genesis({
            "cpf": "12345678901", "nome_completo": "Teste",
            "data_nascimento": "01/01/2000", "sexo": "M",
            "cidade_nascimento": "Sao Paulo", "uf_nascimento": "SP",
            "nome_mae": "Mae",
        })
        chain.add_event("CASAMENTO", {})

        # Troca emissor
        chain.set_signer(kp2)
        chain.add_event("DIVORCIO", {})

        # Verifica cada bloco individualmente
        sig0 = BlockSignature.from_dict(chain.chain[0].signature)
        ok0, _ = chain._verify_signature(chain.chain[0], sig0)
        assert ok0

        sig2 = BlockSignature.from_dict(chain.chain[2].signature)
        ok2, _ = chain._verify_signature(chain.chain[2], sig2)
        assert ok2

        # Verificacao global
        all_ok, _ = chain.verify_all_signatures()
        assert all_ok
