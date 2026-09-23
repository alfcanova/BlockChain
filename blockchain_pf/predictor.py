"""
blockchain_pf/predictor.py
Modelo de predição de eventos futuros baseado em:
- Dados demográficos (IBGE/INEP — faixas etárias)
- Estatísticas de nupcialidade/divórcio brasileiras
- Padrões da cadeia atual

ATENÇÃO: Este é um modelo simplificado para fins didáticos.
Em produção, seria necessário dados reais do IBGE e modelos de ML.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .chain import Blockchain
from .events import EventType


@dataclass
class Prediction:
    """Uma predição individual."""
    evento: str
    probabilidade: float  # 0.0 a 1.0
    timeframe: str        # ex: "18-25 anos", "5-10 anos"
    fundamento: str       # Por que essa predição
    confianca: str        # "ALTA", "MEDIA", "BAIXA"

    def to_dict(self) -> dict[str, Any]:
        return {
            "evento": self.evento,
            "probabilidade": round(self.probabilidade, 3),
            "timeframe": self.timeframe,
            "fundamento": self.fundamento,
            "confianca": self.confianca,
        }


@dataclass
class PredictionReport:
    """Relatório completo de predições para uma PF."""
    cpf: str
    nome: str
    idade_atual: int
    situacao_atual: list[str]
    predicoes: list[Prediction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpf": self.cpf,
            "nome": self.nome,
            "idade_atual": self.idade_atual,
            "situacao_atual": self.situacao_atual,
            "predicoes": [p.to_dict() for p in self.predicoes],
        }

    def resumo(self) -> str:
        """Retorna um resumo textual do relatório."""
        lines = [
            f"{'='*60}",
            f"  RELATÓRIO DE PREDIÇÕES — {self.nome}",
            f"  CPF: {self.cpf} | Idade: {self.idade_atual} anos",
            f"{'='*60}",
            "",
            "  Situação Atual:",
        ]
        for s in self.situacao_atual:
            lines.append(f"    • {s}")
        lines.append("")
        lines.append("  Predições Futuras:")

        if not self.predicoes:
            lines.append("    Nenhuma predição disponível.")
        else:
            for p in self.predicoes:
                pct = f"{p.probabilidade*100:.0f}%"
                lines.append(f"    [{p.confianca}] {p.evento}")
                lines.append(f"      Probabilidade: {pct} | Prazo: {p.timeframe}")
                lines.append(f"      Fundamento: {p.fundamento}")
                lines.append("")

        lines.append(f"{'='*60}")
        return "\n".join(lines)


class LifeEventPredictor:
    """
    Preditor de eventos vitais baseado em estatísticas demográficas
    brasileiras (dados aproximados do IBGE/PNAD).
    """

    # ── Taxas demográficas aproximadas (Brasil) ───────────────────────
    # Fontes: IBGE, PNAD, CNSF, SAÚDE

    # Idade média de primeiro casamento (2023)
    IDADE_MEDIA_CASAMENTO_H = 30
    IDADE_MEDIA_CASAMENTO_M = 27

    # Taxa de divórcio dentro de 10 anos do casamento
    TAXA_DIVORCIO_10_ANOS = 0.35

    # Taxa de divórcio dentro de 20 anos
    TAXA_DIVORCIO_20_ANOS = 0.50

    # Idade mínima legal para casamento: 18 (ou 16 com autorização)
    IDADE_MINIMA_CASAMENTO = 16

    # Taxa de mortalidade por faixa (por 1000 habitantes/ano)
    TAXA_MORTALIDADE = {
        "0-9":   0.0015,
        "10-19": 0.0004,
        "20-29": 0.0008,
        "30-39": 0.0012,
        "40-49": 0.0025,
        "50-59": 0.0055,
        "60-69": 0.0130,
        "70-79": 0.0350,
        "80-89": 0.0900,
        "90+":   0.2000,
    }

    # Probabilidade de adoção (adoção de crianças)
    PROB_ADOCAO_ADULTO = 0.02  # 2% dos adultos adotam

    # ── Construção ─────────────────────────────────────────────────────

    def __init__(self, chain: Blockchain) -> None:
        self.chain = chain
        self.timeline = chain.get_timeline()

    def _idade_atual(self) -> int:
        """Calcula a idade atual a partir do nascimento."""
        birth = self.chain.get_birth_block()
        if not birth:
            return 0
        data = birth.data.get("payload", {})
        data_str = data.get("data_nascimento", "")
        try:
            dia, mes, ano = map(int, data_str.split("/"))
            import datetime
            nasc = datetime.date(ano, mes, dia)
            hoje = datetime.date.today()
            idade = hoje.year - nasc.year
            if (hoje.month, hoje.day) < (nasc.month, nasc.day):
                idade -= 1
            return max(idade, 0)
        except Exception:
            return 0

    def _sexo(self) -> str:
        """Retorna o sexo da PF."""
        birth = self.chain.get_birth_block()
        if birth:
            return birth.data.get("payload", {}).get("sexo", "M")
        return "M"

    def _ja_casou(self) -> bool:
        return len(self.chain.get_events_by_type(EventType.CASAMENTO.value)) > 0

    def _esta_casado(self) -> bool:
        casamentos = self.chain.get_events_by_type(EventType.CASAMENTO.value)
        divorcios = self.chain.get_events_by_type(EventType.DIVORCIO.value)
        return len(casamentos) > len(divorcios)

    def _ja_teve_obito(self) -> bool:
        return len(self.chain.get_events_by_type(EventType.OBITO.value)) > 0

    def _nome_atual(self) -> str:
        """Retorna o nome atual da PF (considerando alterações)."""
        nome = ""
        birth = self.chain.get_birth_block()
        if birth:
            nome = birth.data.get("payload", {}).get("nome_completo", "")
        for block in self.chain.chain:
            if block.data.get("evento_tipo") == EventType.ALTERACAO_NOME.value:
                nome = block.data.get("payload", {}).get("nome_novo", nome)
        return nome

    def _situacao_atual(self) -> list[str]:
        """Descreve a situação atual da PF."""
        situacao = []
        idade = self._idade_atual()
        situacao.append(f"Idade: {idade} anos")

        birth = self.chain.get_birth_block()
        if birth:
            pf = birth.data.get("payload", {})
            situacao.append(f"Cidade natal: {pf.get('cidade_nascimento')}/{pf.get('uf_nascimento')}")

        nome = self._nome_atual()
        if nome:
            situacao.append(f"Nome atual: {nome}")

        if self._ja_casou():
            if self._esta_casado():
                situacao.append("Estado civil: CASADO(A)")
            else:
                situacao.append("Estado civil: DIVORCIADO(A)")
        else:
            situacao.append("Estado civil: SOLTEIRO(A)")

        if self._ja_teve_obito():
            situacao.append("⚠️  ÓBITO registrado — cadeia encerrada.")

        return situacao

    # ── Predições ──────────────────────────────────────────────────────

    def predizer_casamento(self) -> Optional[Prediction]:
        """Prediz probabilidade de casamento."""
        idade = self._idade_atual()
        sexo = self._sexo()

        if self._ja_teve_obito():
            return None

        if self._ja_casou() and self._esta_casado():
            return None  # Já casado e não divorciado

        idade_meta = (
            self.IDADE_MEDIA_CASAMENTO_H if sexo == "M"
            else self.IDADE_MEDIA_CASAMENTO_M
        )

        if idade < self.IDADE_MINIMA_CASAMENTO:
            return Prediction(
                evento="CASAMENTO",
                probabilidade=0.0,
                timeframe=f"{self.IDADE_MINIMA_CASAMENTO - idade}+ anos",
                fundamento="Idade mínima legal não atingida.",
                confianca="ALTA",
            )

        # Modelo simples: probabilidade cresce até a média, depois decresce
        if idade < idade_meta:
            prob = 0.3 + 0.5 * (idade - self.IDADE_MINIMA_CASAMENTO) / (idade_meta - self.IDADE_MINIMA_CASAMENTO)
            prob = min(prob, 0.85)
        else:
            # Após a média, diminui 5% por ano
            anos_pos_media = idade - idade_meta
            prob = max(0.15, 0.85 - 0.05 * anos_pos_media)

        if self._ja_casou() and not self._esta_casado():
            prob *= 0.65  # Pós-divórcio, 65% da probabilidade original

        return Prediction(
            evento="CASAMENTO",
            probabilidade=round(prob, 3),
            timeframe="5-10 anos",
            fundamento=(
                f"Idade média de primeiro casamento no Brasil: "
                f"{idade_meta} anos ({sexo}). "
                f"Taxa de re-casamento pós-divórcio: ~65%."
            ),
            confianca="MEDIA",
        )

    def predizer_divorcio(self) -> Optional[Prediction]:
        """Prediz probabilidade de divórcio (se casado)."""
        if not self._esta_casado():
            return None
        if self._ja_teve_obito():
            return None

        # Encontra a data do último casamento
        casamentos = self.chain.get_events_by_type(EventType.CASAMENTO.value)
        if not casamentos:
            return None

        ultimo_casamento = casamentos[-1]
        data_cas = ultimo_casamento.data.get("payload", {}).get("data_casamento", "")
        try:
            dia, mes, anos = map(int, data_cas.split("/"))
            import datetime
            casamento_date = datetime.date(anos, mes, dia)
            anos_casados = (datetime.date.today() - casamento_date).days / 365.25
        except Exception:
            anos_casados = 0

        if anos_casados < 1:
            prob = 0.10
            timeframe = "5-10 anos"
        elif anos_casados < 5:
            prob = 0.30
            timeframe = "5-15 anos"
        elif anos_casados < 10:
            prob = self.TAXA_DIVORCIO_10_ANOS
            timeframe = "1-10 anos"
        else:
            prob = self.TAXA_DIVORCIO_20_ANOS
            timeframe = "Variável"

        return Prediction(
            evento="DIVÓRCIO",
            probabilidade=round(prob, 3),
            timeframe=timeframe,
            fundamento=(
                f"Casado há ~{anos_casados:.0f} anos. "
                f"Taxa de divórcio em 10 anos no Brasil: {self.TAXA_DIVORCIO_10_ANOS*100:.0f}%. "
                f"Taxa em 20 anos: {self.TAXA_DIVORCIO_20_ANOS*100:.0f}%."
            ),
            confianca="MEDIA",
        )

    def predizer_obito(self) -> Optional[Prediction]:
        """Prediz a probabilidade anual de óbito."""
        if self._ja_teve_obito():
            return None

        idade = self._idade_atual()
        faixa = self._faixa_mortalidade(idade)
        taxa = self.TAXA_MORTALIDADE.get(faixa, 0.001)

        # Ajuste: óbito natural ≈ 70%, acidente 20%, violência 10%
        prob_anual = taxa

        return Prediction(
            evento="ÓBITO",
            probabilidade=round(prob_anual, 4),
            timeframe="Risco anual",
            fundamento=(
                f"Faixa etária: {faixa} anos. "
                f"Taxa de mortalidade: {taxa*1000:.1f} por 1000 habitantes/ano (IBGE)."
            ),
            confianca="ALTA" if idade > 60 else "MEDIA",
        )

    def predizer_adocao(self) -> Optional[Prediction]:
        """Prediz probabilidade de adotar uma criança."""
        idade = self._idade_atual()

        if self._ja_teve_obito():
            return None

        if idade < 18:
            return Prediction(
                evento="ADOÇÃO (como adotado)",
                probabilidade=0.01,
                timeframe="Até 18 anos",
                fundamento="Adoção de crianças geralmente ocorre nos primeiros anos de vida.",
                confianca="BAIXA",
            )

        return Prediction(
            evento="ADOÇÃO (como adotante)",
            probabilidade=self.PROB_ADOCAO_ADULTO,
            timeframe="10+ anos",
            fundamento=(
                f"Aproximadamente {self.PROB_ADOCAO_ADULTO*100:.0f}% dos casais brasileiros "
                f"adotam uma criança ao longo da vida."
            ),
            confianca="BAIXA",
        )

    def predizer_disvinculacao(self) -> Optional[Prediction]:
        """Prediz probabilidade de disvinculação parental."""
        idade = self._idade_atual()

        if self._ja_teve_obito():
            return None

        # Disvinculação é rara — baseada em casos judiciais
        if idade < 12:
            prob = 0.005  # 0.5%
        elif idade < 25:
            prob = 0.002  # 0.2%
        else:
            prob = 0.001  # 0.1%

        return Prediction(
            evento="DISVINCULAÇÃO PARENTAL",
            probabilidade=prob,
            timeframe="Qualquer idade",
            fundamento=(
                "Disvinculação é um evento judicial raro. "
                "Baseado em estatísticas do CNJ — menos de 1% dos vínculos "
                "são desfeitos judicialmente."
            ),
            confianca="BAIXA",
        )

    def predizer_alteracao_nome(self) -> Optional[Prediction]:
        """Prediz probabilidade de alteração de nome."""
        if self._ja_teve_obito():
            return None

        # Se já alterou o nome, probabilidade de alterar novamente é maior
        ja_alterou = len(
            self.chain.get_events_by_type(EventType.ALTERACAO_NOME.value)
        ) > 0

        prob = 0.15 if ja_alterou else 0.05

        return Prediction(
            evento="ALTERAÇÃO DE NOME",
            probabilidade=prob,
            timeframe="10-20 anos",
            fundamento=(
                "Aproximadamente 5% dos brasileiros alteram o nome ao longo da vida "
                "(casamento, divórcio, mudança de identidade de gênero, etc.). "
                + ("Histórico de alteração aumenta a probabilidade." if ja_alterou else "")
            ),
            confianca="BAIXA",
        )

    # ── CNH ───────────────────────────────────────────────────────────

    def predizer_cnh(self) -> Optional[Prediction]:
        """Prediz probabilidade de obter ou renovar CNH."""
        idade = self._idade_atual()

        if self._ja_teve_obito():
            return None

        cnhs = self.chain.get_events_by_type(EventType.CNH.value)
        ja_possui = len(cnhs) > 0

        IDADE_MINIMA_CNH = 18
        IDADE_MEDIA_CNH = 21

        if not ja_possui:
            # Prediz obtenção da primeira CNH
            if idade < IDADE_MINIMA_CNH:
                anos_restantes = IDADE_MINIMA_CNH - idade
                return Prediction(
                    evento="CNH (obtenção)",
                    probabilidade=0.0,
                    timeframe=f"{anos_restantes}+ anos",
                    fundamento="Idade mínima legal para habilitação: 18 anos.",
                    confianca="ALTA",
                )

            # 85% dos brasileiros entre 18-30 possuem CNH (IBGE/PRF)
            if idade <= 30:
                prob = 0.85 - 0.02 * (idade - IDADE_MINIMA_CNH)
            elif idade <= 50:
                prob = 0.50 - 0.01 * (idade - 30)
            else:
                prob = 0.20  # Menos provável obter CNH depois dos 50

            return Prediction(
                evento="CNH (obtenção)",
                probabilidade=round(prob, 3),
                timeframe="1-5 anos",
                fundamento=(
                    f"~85% dos brasileiros entre 18-30 anos possuem CNH (IBGE/PRF). "
                    f"Idade mínima: {IDADE_MINIMA_CNH} anos. "
                    f"A probabilidade diminui com a idade."
                ),
                confianca="MEDIA",
            )
        else:
            # Já possui CNH — prediz renovação
            ultima_cnh = cnhs[-1]
            payload = ultima_cnh.data.get("payload", {})
            data_validade = payload.get("data_validade", "")
            situacao = payload.get("situacao", "VALIDA")

            if situacao in ("SUSPENSA", "CASSADA", "CANCELADA"):
                return Prediction(
                    evento="CNH (reativação)",
                    probabilidade=0.40,
                    timeframe="1-3 anos",
                    fundamento=(
                        f"CNH com situação '{situacao}'. "
                        f"Reabilitação pode ser solicitada após cumprir penalidade."
                    ),
                    confianca="MEDIA",
                )

            # Prediz renovação baseada na validade
            try:
                dia, mes, ano = map(int, data_validade.split("/"))
                import datetime
                validade_date = datetime.date(ano, mes, dia)
                hoje = datetime.date.today()
                dias_para_vencer = (validade_date - hoje).days

                if dias_para_vencer <= 0:
                    return Prediction(
                        evento="CNH (renovação)",
                        probabilidade=0.95,
                        timeframe="Imediato",
                        fundamento="CNH vencida — renovação urgente necessária.",
                        confianca="ALTA",
                    )
                elif dias_para_vencer <= 365:
                    return Prediction(
                        evento="CNH (renovação)",
                        probabilidade=0.80,
                        timeframe="Até 12 meses",
                        fundamento=f"CNH vence em {dias_para_vencer} dias.",
                        confianca="ALTA",
                    )
            except Exception:
                pass

            return Prediction(
                evento="CNH (renovação)",
                probabilidade=0.10,
                timeframe="5-10 anos",
                fundamento=(
                    "CNH renovada. Renovação a cada 10 anos (menores de 65) "
                    "ou 5 anos (65+)."
                ),
                confianca="BAIXA",
            )

    # ── Escolaridade ───────────────────────────────────────────────────

    def predizer_escolaridade(self) -> Optional[Prediction]:
        """Prediz próximo nível de escolaridade."""
        idade = self._idade_atual()

        if self._ja_teve_obito():
            return None

        escolas = self.chain.get_events_by_type(EventType.ESCOLARIDADE.value)
        niveis_ja_feitos = set()
        for e in escolas:
            nivel = e.data.get("payload", {}).get("nivel", "")
            niveis_ja_feitos.add(nivel.lower())

        # Hierarquia de escolaridade
        hierarquia = ["fundamental", "medio", "tecnico", "superior", "pos", "mestrado", "doutorado"]
        proximo_nivel = None
        for nivel in hierarquia:
            if nivel not in niveis_ja_feitos:
                proximo_nivel = nivel
                break

        if proximo_nivel is None:
            return Prediction(
                evento="ESCOLARIDADE (formação completa)",
                probabilidade=0.05,
                timeframe="Variável",
                fundamento="Todos os níveis de escolaridade já registrados.",
                confianca="BAIXA",
            )

        # Predição baseada na idade
        if proximo_nivel == "fundamental" and idade < 14:
            prob = 0.95
            timeframe = f"Até {15 - idade} anos"
            fundamento = "Educação fundamental é obrigatória dos 6 aos 14 anos (CF/88)."
            confianca = "ALTA"
        elif proximo_nivel == "medio" and idade < 18:
            prob = 0.80
            timeframe = f"Até {18 - idade} anos"
            fundamento = "Educação média é obrigatória dos 14 aos 17 anos."
            confianca = "ALTA"
        elif proximo_nivel == "superior" and idade >= 18:
            # ~20% dos brasileiros entre 18-24 ingressam no ensino superior (INEP)
            if idade <= 25:
                prob = 0.55
                timeframe = "2-5 anos"
                fundamento = "~20% dos jovens 18-24 ingressam no ensino superior (INEP)."
            elif idade <= 35:
                prob = 0.30
                timeframe="3-7 anos"
                fundamento = "Graduação tardia cresce no Brasil — 30% dos 25-35 anos."
            else:
                prob = 0.15
                timeframe="5-10 anos"
                fundamento = "EAD e graduação tardia permitem ingresso em qualquer idade."
            confianca = "MEDIA"
        elif proximo_nivel in ("pos", "mestrado", "doutorado") and idade >= 22:
            # ~15% dos formados fazem pós (INEP)
            prob = 0.15
            timeframe = "3-7 anos"
            fundamento = "~15% dos graduados prosseguem para pós-graduação (INEP)."
            confianca = "BAIXA"
        elif proximo_nivel == "tecnico" and 15 <= idade <= 25:
            prob = 0.25
            timeframe = "1-3 anos"
            fundamento = "Cursos técnicos são populares entre 15-25 anos."
            confianca = "BAIXA"
        else:
            prob = 0.10
            timeframe = "Variável"
            fundamento = f"Próximo nível: {proximo_nivel}. Probabilidade baseada na idade."
            confianca = "BAIXA"

        return Prediction(
            evento=f"ESCOLARIDADE ({proximo_nivel})",
            probabilidade=round(prob, 3),
            timeframe=timeframe,
            fundamento=fundamento,
            confianca=confianca,
        )

    def predizer_titulo_eleitor(self) -> Optional[Prediction]:
        """Prediz probabilidade de obter título de eleitor."""
        idade = self._idade_atual()

        if self._ja_teve_obito():
            return None

        titulos = self.chain.get_events_by_type(EventType.TITULO_ELEITOR.value)
        ja_possui = len(titulos) > 0

        IDADE_OBRIGATORIA = 18
        IDADE_MINIMA = 16

        if not ja_possui:
            if idade < IDADE_MINIMA:
                return Prediction(
                    evento="TÍTULO DE ELEITOR (obtenção)",
                    probabilidade=0.0,
                    timeframe=f"{IDADE_MINIMA - idade}+ anos",
                    fundamento="Título de eleitor é obrigatório dos 18 aos 70 anos.",
                    confianca="ALTA",
                )

            # 95% dos brasileiros entre 18-70 possuem título (TSE)
            if idade <= 70:
                prob = 0.95
                timeframe = "Imediato" if idade >= IDADE_OBRIGATORIA else "1-2 anos"
                fundamento = "Título de eleitor é obrigatório dos 18 aos 70 anos (TSE)."
                confianca = "ALTA"
            else:
                prob = 0.10
                timeframe = "Variável"
                fundamento = "Após 70 anos, título é facultativo."
                confianca = "BAIXA"

            return Prediction(
                evento="TÍTULO DE ELEITOR (obtenção)",
                probabilidade=round(prob, 3),
                timeframe=timeframe,
                fundamento=fundamento,
                confianca=confianca,
            )
        else:
            # Já possui — prediz transferência ou atualização
            ultimo_titulo = titulos[-1]
            payload = ultimo_titulo.data.get("payload", {})
            situacao = payload.get("situacao", "REGULAR")

            if situacao == "SUSPENSO":
                return Prediction(
                    evento="TÍTULO DE ELEITOR (reativação)",
                    probabilidade=0.60,
                    timeframe="1-2 anos",
                    fundamento="Título suspenso pode ser reativado com regularização.",
                    confianca="MEDIA",
                )

            return Prediction(
                evento="TÍTULO DE ELEITOR (atualização)",
                probabilidade=0.30,
                timeframe="5-10 anos",
                fundamento="Transferência de zona/seção ao mudar de município.",
                confianca="BAIXA",
            )

    # ── Relatório completo ─────────────────────────────────────────────

    def gerar_relatorio(self) -> PredictionReport:
        """Gera o relatório completo de predições."""
        nome = self._nome_atual()
        birth = self.chain.get_birth_block()
        cpf = ""
        if birth:
            cpf = birth.data.get("payload", {}).get("cpf", "")

        report = PredictionReport(
            cpf=cpf,
            nome=nome,
            idade_atual=self._idade_atual(),
            situacao_atual=self._situacao_atual(),
        )

        # Coleta todas as predições aplicáveis
        for pred_fn in [
            self.predizer_casamento,
            self.predizer_divorcio,
            self.predizer_obito,
            self.predizer_adocao,
            self.predizer_disvinculacao,
            self.predizer_alteracao_nome,
            self.predizer_cnh,
            self.predizer_titulo_eleitor,
            self.predizer_escolaridade,
        ]:
            pred = pred_fn()
            if pred is not None:
                report.predicoes.append(pred)

        return report

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _faixa_mortalidade(idade: int) -> str:
        """Retorna a faixa etária para consulta de mortalidade."""
        if idade < 10:
            return "0-9"
        elif idade < 20:
            return "10-19"
        elif idade < 30:
            return "20-29"
        elif idade < 40:
            return "30-39"
        elif idade < 50:
            return "40-49"
        elif idade < 60:
            return "50-59"
        elif idade < 70:
            return "60-69"
        elif idade < 80:
            return "70-79"
        elif idade < 90:
            return "80-89"
        else:
            return "90+"
