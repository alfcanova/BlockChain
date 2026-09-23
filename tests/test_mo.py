"""
tests/test_mo.py
Testes unitários para o módulo blockchain_mo (Veículos/Móveis).
"""

import os
import tempfile
import pytest

from blockchain_mo import (
    VehicleEventType,
    VehicleEventFactory,
    VehicleChain,
    VehicleChainProtector,
    CrossChainMO,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def veiculo_genesis_data() -> dict:
    """Dados de fabricação de um veículo para testes."""
    return VehicleEventFactory.fabricacao(

        uf="SP",
        cidade="Sao Paulo",        placa="ABC1D23",
        renavan="12345678901",
        chassis="9BWZZZ377VT000001",
        marca="Volkswagen",
        modelo="Gol",
        ano_fabricacao=2024,
        ano_modelo=2024,
        cor="Prata",
        combustivel="FLEX",
        cilindradas=1000,
        potencia_cv=75,
        tipo_veiculo="AUTOMOVEL",
        categoria="PARTICULAR",
        num_portas=4,
        capacidade_passageiros=5,
        fabricante_cnpj="12345678000195",
        fabricante_nome="Volkswagen do Brasil",
        fabricante_pais="BR",
        motor_tipo="1.0 MPI",
        motor_numero="MOT-001",
        freio_dianteiro="DISCO",
        freio_traseiro="TAMBOR",
        direcao="HIDRAULICA",
        transmissao="MANUAL 5 MARCHAS",
        lote_fabricacao="LOTE-2024-001",
        data_fabricacao="15/03/2024",
        certificado_homologacao="CERT-2024-001",
        crv="CRV-2024-001",
        odometro_km=0.0,
    )


@pytest.fixture
def chain() -> VehicleChain:
    """Cadeia de veículos vazia."""
    return VehicleChain(difficulty=2)


@pytest.fixture
def chain_com_genesis(veiculo_genesis_data: dict) -> VehicleChain:
    """Cadeia com bloco gênesis."""
    chain = VehicleChain(difficulty=2)
    chain.create_genesis(veiculo_genesis_data)
    return chain


# ── Testes do EventType ───────────────────────────────────────────────


class TestVehicleEventType:
    """Testa os tipos de evento."""

    def test_todos_os_eventos_existem(self):
        """Verifica que todos os eventos esperados estão definidos."""
        eventos_esperados = {
            "FABRICACAO", "COMPRA_VENDA", "DOACAO", "GARANTIA_EMPRESTIMO",
            "QUITACAO_GARANTIA", "LEILAO", "CONFISCO", "MULTA",
            "SINISTRO", "SINISTRO_PERDA_TOTAL", "TROCA_PECA",
            "VALIDACAO_PECA", "TRANSFERENCIA_PROPRIEDADE", "REVISAO",
            "LICENCIAMENTO", "MUDANCA_COR", "BAIXA", "RECALL_DE_FABRICA",
        }
        eventos_definidos = {e.value for e in VehicleEventType}
        assert eventos_esperados == eventos_definidos

    def test_evento_e_string(self):
        """Verifica que os enums são strings (compatível com Block data)."""
        assert isinstance(VehicleEventType.FABRICACAO.value, str)
        assert VehicleEventType.FABRICACAO == "FABRICACAO"


# ── Testes do EventFactory ────────────────────────────────────────────


class TestVehicleEventFactory:
    """Testa a fábrica de eventos."""

    def test_fabricacao_dados_validos(self, veiculo_genesis_data: dict):
        """Fabricação com dados válidos deve criar dict correto."""
        dados = veiculo_genesis_data
        assert dados["evento_tipo"] == "FABRICACAO"
        assert dados["placa"] == "ABC1D23"
        assert dados["renavan"] == "12345678901"
        assert dados["chassis"] == "9BWZZZ377VT000001"
        assert dados["marca"] == "Volkswagen"
        assert dados["modelo"] == "Gol"
        assert dados["situacao"] == "REGULAR"
        assert dados["odometro_km"] == 0.0

    def test_fabricacao_placa_invalida(self):
        """Placa inválida deve levantar ValueError."""
        with pytest.raises(ValueError, match="Placa inválida"):
            VehicleEventFactory.fabricacao(
                uf="SP",
                cidade="Sao Paulo",
                placa="INVALIDA",
                renavan="12345678901",
                chassis="9BWZZZ377VT000001",
                marca="Volkswagen",
                modelo="Gol",
                ano_fabricacao=2024,
                ano_modelo=2024,
                cor="Prata",
                combustivel="FLEX",
                cilindradas=1000,
                potencia_cv=75,
            )

    def test_fabricacao_renavan_invalido(self):
        """RENAVAN inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="RENAVAN inválido"):
            VehicleEventFactory.fabricacao(
                uf="SP",
                cidade="Sao Paulo",
                placa="ABC1D23",
                renavan="123",
                chassis="9BWZZZ377VT000001",
                marca="Volkswagen",
                modelo="Gol",
                ano_fabricacao=2024,
                ano_modelo=2024,
                cor="Prata",
                combustivel="FLEX",
                cilindradas=1000,
                potencia_cv=75,
            )

    def test_fabricacao_chassi_invalido(self):
        """Chassi inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="Chassi inválido"):
            VehicleEventFactory.fabricacao(
                uf="SP",
                cidade="Sao Paulo",
                placa="ABC1D23",
                renavan="12345678901",
                chassis="CURTO",
                marca="Volkswagen",
                modelo="Gol",
                ano_fabricacao=2024,
                ano_modelo=2024,
                cor="Prata",
                combustivel="FLEX",
                cilindradas=1000,
                potencia_cv=75,
            )

    def test_fabricacao_ano_invalido(self):
        """Ano de fabricação inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="Ano de fabricação inválido"):
            VehicleEventFactory.fabricacao(
                uf="SP",
                cidade="Sao Paulo",
                placa="ABC1D23",
                renavan="12345678901",
                chassis="9BWZZZ377VT000001",
                marca="Volkswagen",
                modelo="Gol",
                ano_fabricacao=1800,
                ano_modelo=2024,
                cor="Prata",
                combustivel="FLEX",
                cilindradas=1000,
                potencia_cv=75,
            )

    def test_compra_venda_valida(self):
        """Compra/venda com dados válidos."""
        dados = VehicleEventFactory.compra_venda(
            placa="ABC1D23",
            comprador_cpf="12345678901",
            comprador_nome="João Silva",
            vendedor_cpf="98765432100",
            vendedor_nome="Maria Santos",
            valor_transacao=35000.00,
            data_transacao="01/06/2024",
            odometro_km=45000.0,
        )
        assert dados["evento_tipo"] == "COMPRA_VENDA"
        assert dados["comprador"]["cpf"] == "12345678901"
        assert dados["vendedor"]["cpf"] == "98765432100"
        assert dados["valor_transacao"] == 35000.00

    def test_compra_venda_cpf_invalido(self):
        """CPF inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="CPF do comprador inválido"):
            VehicleEventFactory.compra_venda(
                placa="ABC1D23",
                comprador_cpf="123",
                comprador_nome="João Silva",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria Santos",
                valor_transacao=35000.00,
                data_transacao="01/06/2024",
            )

    def test_compra_venda_valor_negativo(self):
        """Valor negativo deve levantar ValueError."""
        with pytest.raises(ValueError, match="não pode ser negativo"):
            VehicleEventFactory.compra_venda(
                placa="ABC1D23",
                comprador_cpf="12345678901",
                comprador_nome="João Silva",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria Santos",
                valor_transacao=-1000.00,
                data_transacao="01/06/2024",
            )

    def test_doacao_valida(self):
        """Doação com dados válidos."""
        dados = VehicleEventFactory.doacao(
            placa="ABC1D23",
            donatario_cpf="12345678901",
            donatario_nome="João Silva",
            doador_cpf="98765432100",
            doador_nome="Maria Santos",
            data_doacao="15/06/2024",
            motivo="Presente de aniversário",
        )
        assert dados["evento_tipo"] == "DOACAO"
        assert dados["motivo"] == "Presente de aniversário"

    def test_garantia_emprestimo_valida(self):
        """Garantia de empréstimo com dados válidos."""
        dados = VehicleEventFactory.garantia_emprestimo(
            placa="ABC1D23",
            credor_nome="Banco do Brasil",
            credor_cnpj="00000000000191",
            valor_emprestimo=20000.00,
            data_garantia="01/07/2024",
            data_vencimento="01/07/2026",
            taxa_juros=1.99,
            parcelas=24,
            tipo_garantia="ALIENACAO_FIDUCIARIA",
        )
        assert dados["evento_tipo"] == "GARANTIA_EMPRESTIMO"
        assert dados["status"] == "ATIVA"
        assert dados["credor"]["cnpj"] == "00000000000191"

    def test_garantia_emprestimo_cnpj_invalido(self):
        """CNPJ inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="CNPJ do credor inválido"):
            VehicleEventFactory.garantia_emprestimo(
                placa="ABC1D23",
                credor_nome="Banco",
                credor_cnpj="123",
                valor_emprestimo=20000.00,
                data_garantia="01/07/2024",
                data_vencimento="01/07/2026",
            )

    def test_quitacao_garantia_valida(self):
        """Quitação de garantia com dados válidos."""
        dados = VehicleEventFactory.quitacao_garantia(
            placa="ABC1D23",
            garantia_index=0,
            data_quitacao="01/07/2026",
            valor_pago=22000.00,
            descricao="Quitação antecipada",
        )
        assert dados["evento_tipo"] == "QUITACAO_GARANTIA"
        assert dados["garantia_index"] == 0

    def test_leilao_valido(self):
        """Leilão com dados válidos."""
        dados = VehicleEventFactory.leilao(
            placa="ABC1D23",
            data_leilao="15/08/2024",
            valor_minimo=15000.00,
            lance_vencedor=18000.00,
            vencedor_cpf="12345678901",
            vencedor_nome="João Silva",
            leiloeiro="Leiloeira XYZ",
            tipo="JUDICIAL",
        )
        assert dados["evento_tipo"] == "LEILAO"
        assert dados["status"] == "CONCLUIDO"
        assert dados["lance_vencedor"] == 18000.00

    def test_leilao_sem_vencedor(self):
        """Leilão sem vencedor deve ter status AGUARDANDO."""
        dados = VehicleEventFactory.leilao(
            placa="ABC1D23",
            data_leilao="15/08/2024",
            valor_minimo=15000.00,
        )
        assert dados["status"] == "AGUARDANDO"

    def test_confisco_valido(self):
        """Confisco com dados válidos."""
        dados = VehicleEventFactory.confisco(
            placa="ABC1D23",
            autoridade="Juiz Federal",
            processo_numero="0001234-56.2024.8.26.0100",
            data_confisco="01/09/2024",
            motivo="Tráfico de drogas",
        )
        assert dados["evento_tipo"] == "CONFISCO"

    def test_multa_valida(self):
        """Multa com dados válidos."""
        dados = VehicleEventFactory.multa(
            placa="ABC1D23",
            numero_auto="AUTO-2024-001",
            data_infracao="10/06/2024",
            local_logradouro="Av. Paulista, 1000",
            local_cidade="São Paulo",
            local_uf="SP",
            enquadramento="Art. 165 CTB",
            pontos=7,
            valor_multa=293.47,
            orgao_autuador="DETRAN/SP",
            condutor_cpf="12345678901",
            condutor_nome="João Silva",
        )
        assert dados["evento_tipo"] == "MULTA"
        assert dados["pontos"] == 7
        assert dados["status"] == "PENDENTE"

    def test_multa_pontos_invalidos(self):
        """Pontos inválidos devem levantar ValueError."""
        with pytest.raises(ValueError, match="Pontos inválidos"):
            VehicleEventFactory.multa(
                placa="ABC1D23",
                numero_auto="AUTO-2024-001",
                data_infracao="10/06/2024",
                local_logradouro="Av. Paulista",
                local_cidade="São Paulo",
                local_uf="SP",
                enquadramento="Art. 165 CTB",
                pontos=10,
                valor_multa=293.47,
                orgao_autuador="DETRAN/SP",
            )

    def test_sinistro_valido(self):
        """Sinistro com dados válidos."""
        dados = VehicleEventFactory.sinistro(
            placa="ABC1D23",
            data_sinistro="20/06/2024",
            tipo="COLISAO",
            bo_numero="BO-2024-001",
            seguradora_nome="Porto Seguro",
            seguradora_cnpj="61198164000123",
            seguradora_apolice="AP-2024-001",
            valor_dano=12000.00,
            pecas_danificadas=["Para-choque dianteiro", "Farol esquerdo"],
        )
        assert dados["evento_tipo"] == "SINISTRO"
        assert dados["perda_total"] is False
        assert len(dados["pecas_danificadas"]) == 2

    def test_sinistro_tipo_invalido(self):
        """Tipo de sinistro inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="Tipo de sinistro inválido"):
            VehicleEventFactory.sinistro(
                placa="ABC1D23",
                data_sinistro="20/06/2024",
                tipo="TIPO_INVALIDO",
                bo_numero="BO-2024-001",
            )

    def test_sinistro_perda_total_valido(self):
        """Sinistro com perda total com dados válidos."""
        dados = VehicleEventFactory.sinistro_perda_total(
            placa="ABC1D23",
            data_sinistro="20/06/2024",
            tipo="INCENDIO",
            bo_numero="BO-2024-002",
            seguradora_nome="Porto Seguro",
            valor_indenizacao=28000.00,
            destino="DESTRUIDO",
            data_baixa_detran="01/07/2024",
        )
        assert dados["evento_tipo"] == "SINISTRO_PERDA_TOTAL"
        assert dados["perda_total"] is True
        assert dados["valor_indenizacao"] == 28000.00

    def test_sinistro_perda_total_destino_invalido(self):
        """Destino inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="Destino inválido"):
            VehicleEventFactory.sinistro_perda_total(
                placa="ABC1D23",
                data_sinistro="20/06/2024",
                tipo="INCENDIO",
                bo_numero="BO-2024-002",
                destino="INVALIDO",
            )

    def test_troca_peca_valida(self):
        """Troca de peça com dados válidos."""
        dados = VehicleEventFactory.troca_peca(
            placa="ABC1D23",
            peca_nome="Motor",
            peca_numero_serie="MOT-12345",
            peca_fabricante="Volkswagen",
            peca_origem="ORIGINAL",
            data_troca="01/08/2024",
            oficina_responsavel="Oficina Mecânica XYZ",
            mecanico_cpf="12345678901",
            motivo="Desgaste natural",
            odometro_km=80000.0,
        )
        assert dados["evento_tipo"] == "TROCA_PECA"
        assert dados["peca"]["origem"] == "ORIGINAL"
        assert dados["odometro_km"] == 80000.0

    def test_troca_peca_origem_invalida(self):
        """Origem inválida deve levantar ValueError."""
        with pytest.raises(ValueError, match="Origem da peça inválida"):
            VehicleEventFactory.troca_peca(
                placa="ABC1D23",
                peca_nome="Motor",
                peca_numero_serie="MOT-12345",
                peca_fabricante="Volkswagen",
                peca_origem="INVALIDA",
                data_troca="01/08/2024",
            )

    def test_validacao_peca_valida(self):
        """Validação de peça com dados válidos."""
        dados = VehicleEventFactory.validacao_peca(
            placa="ABC1D23",
            peca_nome="Motor",
            peca_numero_serie="MOT-12345",
            validador_cpf="12345678901",
            validador_nome="João Silva",
            data_validacao="15/08/2024",
            resultado="AUTENTICADA",
            metodo_validacao="Análise documental + física",
        )
        assert dados["evento_tipo"] == "VALIDACAO_PECA"
        assert dados["resultado"] == "AUTENTICADA"

    def test_validacao_peca_resultado_invalido(self):
        """Resultado inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="Resultado inválido"):
            VehicleEventFactory.validacao_peca(
                placa="ABC1D23",
                peca_nome="Motor",
                peca_numero_serie="MOT-12345",
                validador_cpf="12345678901",
                validador_nome="João Silva",
                data_validacao="15/08/2024",
                resultado="INVALIDO",
            )

    def test_transferencia_propriedade_valida(self):
        """Transferência de propriedade com dados válidos."""
        dados = VehicleEventFactory.transferencia_propriedade(
            placa="ABC1D23",
            novo_proprietario_cpf="12345678901",
            novo_proprietario_nome="João Silva",
            data_transferencia="01/06/2024",
            documento_tipo="CRV",
            documento_numero="CRV-2024-001",
            orgao_emissor="DETRAN/SP",
            odometro_km=45000.0,
        )
        assert dados["evento_tipo"] == "TRANSFERENCIA_PROPRIEDADE"
        assert dados["novo_proprietario"]["cpf"] == "12345678901"

    def test_revisao_valida(self):
        """Revisão com dados válidos."""
        dados = VehicleEventFactory.revisao(
            placa="ABC1D23",
            data_revisao="01/09/2024",
            oficina_responsavel="Oficina XYZ",
            tipo_revisao="PREVENTIVA",
            itens_revisados=["Óleo", "Filtros", "Freios"],
            pecas_substituidas=["Óleo do motor", "Filtro de óleo"],
            odometro_km=10000.0,
            proxima_revisao_km=20000.0,
            valor_total=500.00,
        )
        assert dados["evento_tipo"] == "REVISAO"
        assert len(dados["itens_revisados"]) == 3

    def test_licenciamento_valido(self):
        """Licenciamento com dados válidos."""
        dados = VehicleEventFactory.licenciamento(
            placa="ABC1D23",
            ano_licenciamento=2024,
            data_licenciamento="01/03/2024",
            ipva_pago=True,
            valor_ipva=1500.00,
        )
        assert dados["evento_tipo"] == "LICENCIAMENTO"
        assert dados["ipva_pago"] is True

    def test_mudanca_cor_valida(self):
        """Mudança de cor com dados válidos."""
        dados = VehicleEventFactory.mudanca_cor(
            placa="ABC1D23",
            cor_anterior="Prata",
            cor_nova="Preto",
            data_mudanca="01/10/2024",
        )
        assert dados["evento_tipo"] == "MUDANCA_COR"
        assert dados["cor_nova"] == "Preto"

    def test_mudanca_cor_nova_cor_vazia(self):
        """Nova cor vazia deve levantar ValueError."""
        with pytest.raises(ValueError, match="Nova cor é obrigatória"):
            VehicleEventFactory.mudanca_cor(
                placa="ABC1D23",
                cor_anterior="Prata",
                cor_nova="",
                data_mudanca="01/10/2024",
            )

    def test_baixa_valida(self):
        """Baixa com dados válidos."""
        dados = VehicleEventFactory.baixa(
            placa="ABC1D23",
            data_baixa="01/07/2024",
            motivo="PERDA_TOTAL",
        )
        assert dados["evento_tipo"] == "BAIXA"
        assert dados["motivo"] == "PERDA_TOTAL"

    def test_baixa_motivo_vazio(self):
        """Motivo vazio deve levantar ValueError."""
        with pytest.raises(ValueError, match="Motivo da baixa é obrigatório"):
            VehicleEventFactory.baixa(
                placa="ABC1D23",
                data_baixa="01/07/2024",
                motivo="",
            )


# ── Testes do VehicleChain ────────────────────────────────────────────


class TestVehicleChain:
    """Testa a cadeia de blocos de veículos."""

    def test_cadeia_vazia(self, chain: VehicleChain):
        """Cadeia recém-criada deve estar vazia."""
        assert len(chain) == 0

    def test_criar_genesis(self, chain: VehicleChain, veiculo_genesis_data: dict):
        """Criar gênesis deve adicionar 1 bloco."""
        genesis = chain.create_genesis(veiculo_genesis_data)
        assert len(chain) == 1
        assert genesis.index == 0
        assert genesis.previous_hash == "0" * 64
        assert genesis.data["evento_tipo"] == "FABRICACAO"

    def test_genesis_com_dados_corretos(self, chain: VehicleChain, veiculo_genesis_data: dict):
        """Gênesis deve conter os dados do veículo."""
        chain.create_genesis(veiculo_genesis_data)
        genesis = chain.get_genesis_block()
        payload = genesis.data["payload"]
        assert payload["placa"] == "ABC1D23"
        assert payload["renavan"] == "12345678901"
        assert payload["chassis"] == "9BWZZZ377VT000001"
        assert payload["marca"] == "Volkswagen"

    def test_placa_e_renavan(self, chain_com_genesis: VehicleChain):
        """Métodos get_placa e get_renavan devem retornar valores corretos."""
        assert chain_com_genesis.get_placa() == "ABC1D23"
        assert chain_com_genesis.get_renavan() == "12345678901"
        assert chain_com_genesis.get_chassis() == "9BWZZZ377VT000001"

    def test_adicionar_evento(self, chain_com_genesis: VehicleChain):
        """Adicionar evento deve aumentar o tamanho da cadeia."""
        chain_com_genesis.add_event(
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventFactory.compra_venda(
                placa="ABC1D23",
                comprador_cpf="12345678901",
                comprador_nome="João Silva",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria Santos",
                valor_transacao=35000.00,
                data_transacao="01/06/2024",
            ),
        )
        assert len(chain_com_genesis) == 2

    def test_evento_encadeia_hash(self, chain_com_genesis: VehicleChain):
        """O hash do segundo bloco deve referenciar o primeiro."""
        chain_com_genesis.add_event(
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventFactory.compra_venda(
                placa="ABC1D23",
                comprador_cpf="12345678901",
                comprador_nome="João Silva",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria Santos",
                valor_transacao=35000.00,
                data_transacao="01/06/2024",
            ),
        )
        genesis_hash = chain_com_genesis.chain[0].hash
        assert chain_com_genesis.chain[1].previous_hash == genesis_hash

    def test_adicionar_evento_sem_genesis(self):
        """Adicionar evento sem gênesis deve levantar ValueError."""
        chain = VehicleChain(difficulty=2)
        with pytest.raises(ValueError, match="Cadeia vazia"):
            chain.add_event("COMPRA_VENDA", {})

    def test_validar_cadeia(self, chain_com_genesis: VehicleChain):
        """Cadeia com gênesis deve ser válida."""
        ok, msg = chain_com_genesis.validate()
        assert ok is True
        assert "válida" in msg

    def test_estado_atual_apos_compra(self, chain_com_genesis: VehicleChain):
        """Estado deve refletir novo proprietário após compra."""
        chain_com_genesis.add_event(
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventFactory.compra_venda(
                placa="ABC1D23",
                comprador_cpf="12345678901",
                comprador_nome="João Silva",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria Santos",
                valor_transacao=35000.00,
                data_transacao="01/06/2024",
                odometro_km=45000.0,
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert len(estado["proprietarios"]) == 1
        assert estado["proprietarios"][0]["cpf"] == "12345678901"
        assert estado["proprietarios"][0]["nome"] == "João Silva"
        assert estado["odometro_km"] == 45000.0

    def test_estado_atual_apos_leilao(self, chain_com_genesis: VehicleChain):
        """Leilão sem vencedor deve poner estado EM_LEILAO."""
        chain_com_genesis.add_event(
            VehicleEventType.LEILAO.value,
            VehicleEventFactory.leilao(
                placa="ABC1D23",
                data_leilao="15/08/2024",
                valor_minimo=15000.00,
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert estado["situacao"] == "EM_LEILAO"

    def test_estado_atual_apos_confisco(self, chain_com_genesis: VehicleChain):
        """Confisco deve poner estado CONFISCADO e remover proprietários."""
        chain_com_genesis.add_event(
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventFactory.compra_venda(
                placa="ABC1D23",
                comprador_cpf="12345678901",
                comprador_nome="João Silva",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria Santos",
                valor_transacao=35000.00,
                data_transacao="01/06/2024",
            ),
        )
        chain_com_genesis.add_event(
            VehicleEventType.CONFISCO.value,
            VehicleEventFactory.confisco(
                placa="ABC1D23",
                autoridade="Juiz Federal",
                processo_numero="0001234-56.2024.8.26.0100",
                data_confisco="01/09/2024",
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert estado["situacao"] == "CONFISCADO"
        assert len(estado["proprietarios"]) == 0

    def test_estado_atual_apos_sinistro_perda_total(self, chain_com_genesis: VehicleChain):
        """Sinistro com perda total deve poner estado PERDA_TOTAL."""
        chain_com_genesis.add_event(
            VehicleEventType.SINISTRO_PERDA_TOTAL.value,
            VehicleEventFactory.sinistro_perda_total(
                placa="ABC1D23",
                data_sinistro="20/06/2024",
                tipo="INCENDIO",
                bo_numero="BO-2024-002",
                destino="DESTRUIDO",
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert estado["situacao"] == "PERDA_TOTAL"

    def test_estado_atual_apos_baixa(self, chain_com_genesis: VehicleChain):
        """Baixa deve poner estado BAIXADO."""
        chain_com_genesis.add_event(
            VehicleEventType.BAIXA.value,
            VehicleEventFactory.baixa(
                placa="ABC1D23",
                data_baixa="01/07/2024",
                motivo="PERDA_TOTAL",
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert estado["situacao"] == "BAIXADO"

    def test_troca_peca_registra_peca(self, chain_com_genesis: VehicleChain):
        """Troca de peça deve adicionar peça ao estado."""
        chain_com_genesis.add_event(
            VehicleEventType.TROCA_PECA.value,
            VehicleEventFactory.troca_peca(
                placa="ABC1D23",
                peca_nome="Motor",
                peca_numero_serie="MOT-12345",
                peca_fabricante="Volkswagen",
                peca_origem="ORIGINAL",
                data_troca="01/08/2024",
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert len(estado["pecas_atuais"]) == 1
        assert estado["pecas_atuais"][0]["nome"] == "Motor"

    def test_multa_registra_no_estado(self, chain_com_genesis: VehicleChain):
        """Multa deve ser registrada no estado."""
        chain_com_genesis.add_event(
            VehicleEventType.MULTA.value,
            VehicleEventFactory.multa(
                placa="ABC1D23",
                numero_auto="AUTO-2024-001",
                data_infracao="10/06/2024",
                local_logradouro="Av. Paulista",
                local_cidade="São Paulo",
                local_uf="SP",
                enquadramento="Art. 165 CTB",
                pontos=7,
                valor_multa=293.47,
                orgao_autuador="DETRAN/SP",
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert len(estado["multas_pendentes"]) == 1
        assert estado["multas_pendentes"][0]["valor"] == 293.47

    def test_garantia_muda_estado(self, chain_com_genesis: VehicleChain):
        """Garantia deve poner estado GARANTIDO."""
        chain_com_genesis.add_event(
            VehicleEventType.GARANTIA_EMPRESTIMO.value,
            VehicleEventFactory.garantia_emprestimo(
                placa="ABC1D23",
                credor_nome="Banco XYZ",
                credor_cnpj="00000000000191",
                valor_emprestimo=20000.00,
                data_garantia="01/07/2024",
                data_vencimento="01/07/2026",
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert estado["situacao"] == "GARANTIDO"
        assert len(estado["garantias_ativas"]) == 1

    def test_quitacao_garantia(self, chain_com_genesis: VehicleChain):
        """Quitação deve liberar o veículo da garantia."""
        chain_com_genesis.add_event(
            VehicleEventType.GARANTIA_EMPRESTIMO.value,
            VehicleEventFactory.garantia_emprestimo(
                placa="ABC1D23",
                credor_nome="Banco XYZ",
                credor_cnpj="00000000000191",
                valor_emprestimo=20000.00,
                data_garantia="01/07/2024",
                data_vencimento="01/07/2026",
            ),
        )
        chain_com_genesis.add_event(
            VehicleEventType.QUITACAO_GARANTIA.value,
            VehicleEventFactory.quitacao_garantia(
                placa="ABC1D23",
                garantia_index=0,
                data_quitacao="01/07/2026",
                valor_pago=22000.00,
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert estado["situacao"] == "REGULAR"
        assert estado["garantias_ativas"][0]["status"] == "QUITADA"

    def test_mudanca_cor_atualiza_estado(self, chain_com_genesis: VehicleChain):
        """Mudança de cor deve atualizar a cor no estado."""
        chain_com_genesis.add_event(
            VehicleEventType.MUDANCA_COR.value,
            VehicleEventFactory.mudanca_cor(
                placa="ABC1D23",
                cor_anterior="Prata",
                cor_nova="Preto",
                data_mudanca="01/10/2024",
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert estado["cor"] == "Preto"

    def test_historico_completo(self, chain_com_genesis: VehicleChain):
        """Histórico completo deve retornar todos os eventos."""
        chain_com_genesis.add_event(
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventFactory.compra_venda(
                placa="ABC1D23",
                comprador_cpf="12345678901",
                comprador_nome="João Silva",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria Santos",
                valor_transacao=35000.00,
                data_transacao="01/06/2024",
            ),
        )
        historico = chain_com_genesis.get_historico_completo()
        assert len(historico) == 2
        assert historico[0]["tipo"] == "FABRICACAO"
        assert historico[1]["tipo"] == "COMPRA_VENDA"

    def test_fluxo_financeiro(self, chain_com_genesis: VehicleChain):
        """Fluxo financeiro deve retornar apenas transações monetárias."""
        chain_com_genesis.add_event(
            VehicleEventType.COMPRA_VENDA.value,
            VehicleEventFactory.compra_venda(
                placa="ABC1D23",
                comprador_cpf="12345678901",
                comprador_nome="João Silva",
                vendedor_cpf="98765432100",
                vendedor_nome="Maria Santos",
                valor_transacao=35000.00,
                data_transacao="01/06/2024",
            ),
        )
        chain_com_genesis.add_event(
            VehicleEventType.MULTA.value,
            VehicleEventFactory.multa(
                placa="ABC1D23",
                numero_auto="AUTO-2024-001",
                data_infracao="10/06/2024",
                local_logradouro="Av. Paulista",
                local_cidade="São Paulo",
                local_uf="SP",
                enquadramento="Art. 165 CTB",
                pontos=7,
                valor_multa=293.47,
                orgao_autuador="DETRAN/SP",
            ),
        )
        fluxo = chain_com_genesis.get_fluxo_financeiro()
        assert len(fluxo) == 2
        assert fluxo[0]["tipo"] == "COMPRA_VENDA"
        assert fluxo[0]["valor"] == 35000.00
        assert fluxo[1]["tipo"] == "MULTA"

    def test_get_event_por_indice(self, chain_com_genesis: VehicleChain):
        """get_event deve retornar bloco pelo índice."""
        block = chain_com_genesis.get_event(0)
        assert block is not None
        assert block.index == 0
        assert chain_com_genesis.get_event(999) is None

    def test_get_events_by_type(self, chain_com_genesis: VehicleChain):
        """get_events_by_type deve retornar blocos filtrados por tipo."""
        chain_com_genesis.add_event(
            VehicleEventType.MULTA.value,
            VehicleEventFactory.multa(
                placa="ABC1D23",
                numero_auto="AUTO-2024-001",
                data_infracao="10/06/2024",
                local_logradouro="Av. Paulista",
                local_cidade="São Paulo",
                local_uf="SP",
                enquadramento="Art. 165 CTB",
                pontos=7,
                valor_multa=293.47,
                orgao_autuador="DETRAN/SP",
            ),
        )
        multas = chain_com_genesis.get_events_by_type("MULTA")
        assert len(multas) == 1

    def test_get_garantias_ativas(self, chain_com_genesis: VehicleChain):
        """get_garantias_ativas deve retornar apenas garantias ativas."""
        chain_com_genesis.add_event(
            VehicleEventType.GARANTIA_EMPRESTIMO.value,
            VehicleEventFactory.garantia_emprestimo(
                placa="ABC1D23",
                credor_nome="Banco XYZ",
                credor_cnpj="00000000000191",
                valor_emprestimo=20000.00,
                data_garantia="01/07/2024",
                data_vencimento="01/07/2026",
            ),
        )
        garantias = chain_com_genesis.get_garantias_ativas()
        assert len(garantias) == 1


# ── Testes do VehicleChainProtector ───────────────────────────────────


class TestVehicleChainProtector:
    """Testa o protetor de cadeia."""

    def test_estado_regular_permite_tudo(self):
        """Em estado REGULAR, todos os eventos devem ser permitidos."""
        for evt in VehicleEventType:
            assert VehicleChainProtector.pode_adicionar(evt.value, "REGULAR") is True

    def test_em_leilao_bloqueia_compra_venda(self):
        """Em leilão, compra/venda deve ser bloqueada."""
        assert VehicleChainProtector.pode_adicionar("COMPRA_VENDA", "EM_LEILAO") is False

    def test_em_leilao_permite_sinistro(self):
        """Em leilão, sinistro deve ser permitido."""
        assert VehicleChainProtector.pode_adicionar("SINISTRO", "EM_LEILAO") is True

    def test_garantido_bloqueia_leilao(self):
        """Em garantido, leilão deve ser bloqueado."""
        assert VehicleChainProtector.pode_adicionar("LEILAO", "GARANTIDO") is False

    def test_garantido_permite_multa(self):
        """Em garantido, multa deve ser permitida."""
        assert VehicleChainProtector.pode_adicionar("MULTA", "GARANTIDO") is True

    def test_confiscado_bloqueia_compra_venda(self):
        """Em confiscado, compra/venda deve ser bloqueada."""
        assert VehicleChainProtector.pode_adicionar("COMPRA_VENDA", "CONFISCADO") is False

    def test_confiscado_permite_certidao(self):
        """Em confiscado, certidão deve ser permitida (usando evento não bloqueado)."""
        assert VehicleChainProtector.pode_adicionar("MULTA", "CONFISCADO") is True

    def test_perda_total_bloqueia_troca_peca(self):
        """Em perda total, troca de peça deve ser bloqueada."""
        assert VehicleChainProtector.pode_adicionar("TROCA_PECA", "PERDA_TOTAL") is False

    def test_perda_total_bloqueia_revisao(self):
        """Em perda total, revisão deve ser bloqueada."""
        assert VehicleChainProtector.pode_adicionar("REVISAO", "PERDA_TOTAL") is False

    def test_perda_total_permite_baixa(self):
        """Em perda total, baixa deve ser permitida."""
        assert VehicleChainProtector.pode_adicionar("BAIXA", "PERDA_TOTAL") is True

    def test_baixado_bloqueia_tudo(self):
        """Em baixado, todos os eventos devem ser bloqueados."""
        for evt in VehicleEventType:
            assert VehicleChainProtector.pode_adicionar(evt.value, "BAIXADO") is False


# ── Testes de persistência ────────────────────────────────────────────


class TestVehicleChainPersistencia:
    """Testa salvar e carregar cadeia."""

    def test_save_and_load(self, chain_com_genesis: VehicleChain):
        """Salvar e carregar deve manter integridade."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            chain_com_genesis.save_to_file(filepath)
            loaded = VehicleChain.load_from_file(filepath)

            assert len(loaded) == len(chain_com_genesis)
            assert loaded.get_placa() == chain_com_genesis.get_placa()
            assert loaded.get_renavan() == chain_com_genesis.get_renavan()

            ok, _ = loaded.validate()
            assert ok is True
        finally:
            os.unlink(filepath)


# ── Testes do CrossChainMO ────────────────────────────────────────────


class TestCrossChainMO:
    """Testa o gerenciador de referências cruzadas."""

    def test_criar_referencia_pf_mo(self):
        """Criar referência PF→MO deve funcionar."""
        manager = CrossChainMO()
        ref = manager.create_reference(
            origem_tipo="PF",
            origem_id="12345678901",
            destino_tipo="MO",
            destino_id="ABC1D23",
            tipo_vinculo="PROPRIETARIO",
        )
        assert ref.entidade_origem_tipo == "PF"
        assert ref.entidade_origem_id == "12345678901"
        assert ref.entidade_destino_tipo == "MO"
        assert ref.entidade_destino_id == "ABC1D23"
        assert ref.tipo_vinculo == "PROPRIETARIO"
        assert ref.ativo is True

    def test_deactivate_reference(self):
        """Desativar referência deve funcionar."""
        manager = CrossChainMO()
        manager.create_reference(
            origem_tipo="PF",
            origem_id="12345678901",
            destino_tipo="MO",
            destino_id="ABC1D23",
            tipo_vinculo="PROPRIETARIO",
        )
        count = manager.deactivate_reference(
            origem_tipo="PF",
            origem_id="12345678901",
            destino_tipo="MO",
            destino_id="ABC1D23",
        )
        assert count == 1
        assert len(manager.get_vinculos_ativos()) == 0

    def test_get_vinculos_ativos_filtro(self):
        """Filtros de vínculos ativos devem funcionar."""
        manager = CrossChainMO()
        manager.create_reference(
            origem_tipo="PF",
            origem_id="12345678901",
            destino_tipo="MO",
            destino_id="ABC1D23",
            tipo_vinculo="PROPRIETARIO",
        )
        manager.create_reference(
            origem_tipo="PF",
            origem_id="98765432100",
            destino_tipo="MO",
            destino_id="ABC1D23",
            tipo_vinculo="GARANTIDOR",
        )
        proprietarios = manager.get_vinculos_ativos(tipo_vinculo="PROPRIETARIO")
        assert len(proprietarios) == 1
        garantidores = manager.get_vinculos_ativos(tipo_vinculo="GARANTIDOR")
        assert len(garantidores) == 1

    def test_stats(self):
        """Estatísticas devem ser corretas."""
        manager = CrossChainMO()
        manager.create_reference(
            origem_tipo="PF",
            origem_id="12345678901",
            destino_tipo="MO",
            destino_id="ABC1D23",
            tipo_vinculo="PROPRIETARIO",
        )
        stats = manager.stats()
        assert stats["total_referencias"] == 1
        assert stats["referencias_ativas"] == 1

    def test_save_and_load(self):
        """Salvar e carregar referências deve manter integridade."""
        manager = CrossChainMO()
        manager.create_reference(
            origem_tipo="PF",
            origem_id="12345678901",
            destino_tipo="MO",
            destino_id="ABC1D23",
            tipo_vinculo="PROPRIETARIO",
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            manager.save_to_file(filepath)
            loaded = CrossChainMO.load_from_file(filepath)
            assert len(loaded._references) == 1
            assert loaded._references[0].entidade_origem_id == "12345678901"
        finally:
            os.unlink(filepath)


# ── Testes do RECALL DE FÁBRICA ──────────────────────────────────────


class TestRecallFabrica:
    """Testa o evento de recall de fábrica."""

    def test_recall_dados_validos(self):
        """Recall com dados válidos deve criar dict correto."""
        dados = VehicleEventFactory.recall_fabrica(
            placa="ABC1D23",
            data_notificacao="01/10/2024",
            fabricante_nome="Volkswagen do Brasil",
            fabricante_cnpj="12345678000195",
            numero_recall="RC-2024-001",
            peca_defeituosa="Airbag",
            descricao_defeito="Mau funcionamento do sensor de colisão",
            risco="ALTO",
            lote_inicio="LOTE-2024-001",
            lote_fim="LOTE-2024-050",
            ano_fabricacao_inicio=2023,
            ano_fabricacao_fim=2024,
            solucao="Troca do módulo do airbag",
            oficina_autorizada="Oficina VW Autorizada SP",
            prazo_conclusao="31/12/2024",
            custo_para_proprietario=0.0,
        )
        assert dados["evento_tipo"] == "RECALL_DE_FABRICA"
        assert dados["numero_recall"] == "RC-2024-001"
        assert dados["peca_defeituosa"] == "Airbag"
        assert dados["risco"] == "ALTO"
        assert dados["status"] == "PENDENTE"
        assert dados["custo_para_proprietario"] == 0.0

    def test_recall_placa_invalida(self):
        """Placa inválida deve levantar ValueError."""
        with pytest.raises(ValueError, match="Placa inválida"):
            VehicleEventFactory.recall_fabrica(
                placa="INVALIDA",
                data_notificacao="01/10/2024",
                fabricante_nome="Volkswagen",
                fabricante_cnpj="12345678000195",
                numero_recall="RC-2024-001",
                peca_defeituosa="Airbag",
                descricao_defeito="Defeito",
            )

    def test_recall_cnpj_invalido(self):
        """CNPJ inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="CNPJ do fabricante inválido"):
            VehicleEventFactory.recall_fabrica(
                placa="ABC1D23",
                data_notificacao="01/10/2024",
                fabricante_nome="Volkswagen",
                fabricante_cnpj="123",
                numero_recall="RC-2024-001",
                peca_defeituosa="Airbag",
                descricao_defeito="Defeito",
            )

    def test_recall_risco_invalido(self):
        """Risco inválido deve levantar ValueError."""
        with pytest.raises(ValueError, match="Nível de risco inválido"):
            VehicleEventFactory.recall_fabrica(
                placa="ABC1D23",
                data_notificacao="01/10/2024",
                fabricante_nome="Volkswagen",
                fabricante_cnpj="12345678000195",
                numero_recall="RC-2024-001",
                peca_defeituosa="Airbag",
                descricao_defeito="Defeito",
                risco="INVALIDO",
            )

    def test_recall_custo_negativo(self):
        """Custo negativo deve levantar ValueError."""
        with pytest.raises(ValueError, match="não pode ser negativo"):
            VehicleEventFactory.recall_fabrica(
                placa="ABC1D23",
                data_notificacao="01/10/2024",
                fabricante_nome="Volkswagen",
                fabricante_cnpj="12345678000195",
                numero_recall="RC-2024-001",
                peca_defeituosa="Airbag",
                descricao_defeito="Defeito",
                custo_para_proprietario=-50.0,
            )

    def test_recall_sem_prazo(self):
        """Recall sem prazo de conclusão deve funcionar."""
        dados = VehicleEventFactory.recall_fabrica(
            placa="ABC1D23",
            data_notificacao="01/10/2024",
            fabricante_nome="Volkswagen",
            fabricante_cnpj="12345678000195",
            numero_recall="RC-2024-001",
            peca_defeituosa="Airbag",
            descricao_defeito="Defeito",
        )
        assert dados["prazo_conclusao"] == ""

    def test_recall_na_cadeia(self, chain_com_genesis: VehicleChain):
        """Recall registrado na cadeia deve aparecer no estado."""
        chain_com_genesis.add_event(
            VehicleEventType.RECALL_DE_FABRICA.value,
            VehicleEventFactory.recall_fabrica(
                placa="ABC1D23",
                data_notificacao="01/10/2024",
                fabricante_nome="Volkswagen",
                fabricante_cnpj="12345678000195",
                numero_recall="RC-2024-001",
                peca_defeituosa="Airbag",
                descricao_defeito="Mau funcionamento",
                risco="ALTO",
                solucao="Troca do módulo",
                oficina_autorizada="Oficina VW",
                prazo_conclusao="31/12/2024",
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert len(estado["recalls_pendentes"]) == 1
        recall = estado["recalls_pendentes"][0]
        assert recall["numero"] == "RC-2024-001"
        assert recall["risco"] == "ALTO"
        assert recall["status"] == "PENDENTE"
        assert recall["peca_defeituosa"] == "Airbag"

    def test_recall_risco_baixo(self, chain_com_genesis: VehicleChain):
        """Recall de risco baixo deve funcionar."""
        chain_com_genesis.add_event(
            VehicleEventType.RECALL_DE_FABRICA.value,
            VehicleEventFactory.recall_fabrica(
                placa="ABC1D23",
                data_notificacao="01/10/2024",
                fabricante_nome="Volkswagen",
                fabricante_cnpj="12345678000195",
                numero_recall="RC-2024-002",
                peca_defeituosa="Vidro traseiro",
                descricao_defeito="Vidro com bolha",
                risco="BAIXO",
                solucao="Troca do vidro",
            ),
        )
        estado = chain_com_genesis.get_estado_atual()
        assert estado["recalls_pendentes"][0]["risco"] == "BAIXO"

    def test_recall_gratuito(self):
        """Recall gratuito (custo 0) deve ser aceito."""
        dados = VehicleEventFactory.recall_fabrica(
            placa="ABC1D23",
            data_notificacao="01/10/2024",
            fabricante_nome="Volkswagen",
            fabricante_cnpj="12345678000195",
            numero_recall="RC-2024-001",
            peca_defeituosa="Airbag",
            descricao_defeito="Defeito",
            custo_para_proprietario=0.0,
        )
        assert dados["custo_para_proprietario"] == 0.0

    def test_recall_com_custo(self):
        """Recall com custo para o proprietário deve ser aceito."""
        dados = VehicleEventFactory.recall_fabrica(
            placa="ABC1D23",
            data_notificacao="01/10/2024",
            fabricante_nome="Volkswagen",
            fabricante_cnpj="12345678000195",
            numero_recall="RC-2024-001",
            peca_defeituosa="Airbag",
            descricao_defeito="Defeito",
            custo_para_proprietario=150.00,
        )
        assert dados["custo_para_proprietario"] == 150.00
