"""
Banco de perguntas da partida: carga dos CSVs, filtro por fase e controle de
repetição.

`todas` é o banco inteiro; `fila` é a fatia da fase atual; `indice` caminha
dentro dela. `respondidas` guarda a identidade (id()) das perguntas já usadas
nesta partida, para que trocar de fase (ou voltar para uma região anterior)
nunca repita pergunta.
"""

import random
import unicodedata

from src.nucleo import constants
from src.nucleo.utils import carregar_perguntas_csv, carregar_perguntas_professores

_PERGUNTAS_DE_EMERGENCIA = (
    {
        "disciplina": "Teste", "dificuldade": "Fácil",
        "pergunta": "Quanto é 2+2?",
        "opcao_a": "3", "opcao_b": "4", "opcao_c": "5", "opcao_d": "6", "opcao_e": "",
        "resposta": "b",
    },
    {
        "disciplina": "Teste", "dificuldade": "Fácil",
        "pergunta": "Qual a cor do céu?",
        "opcao_a": "Verde", "opcao_b": "Azul", "opcao_c": "Vermelho",
        "opcao_d": "Amarelo", "opcao_e": "",
        "resposta": "b",
    },
)


def carregar_perguntas():
    """Perguntas padrão + as cadastradas pelos professores (CSV opcional)."""
    padrao = []
    try:
        padrao = carregar_perguntas_csv("perguntas.csv")
        if padrao:
            print(f" {len(padrao)} perguntas carregadas")
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao carregar perguntas: {e}")

    professores = carregar_perguntas_professores()

    todas = padrao + professores
    if todas:
        return todas

    print(" Usando perguntas padrão")
    return [dict(p) for p in _PERGUNTAS_DE_EMERGENCIA]


def normalizar_texto(texto):
    """Remove acentos e caixa, pra 'Fácil'/'FACIL'/'fácil' baterem igual.
    Serve tanto para dificuldade quanto para disciplina."""
    texto = (
        unicodedata.normalize("NFKD", str(texto or ""))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return texto.strip().lower()


def filtrar_por_fase(lista, fase, respondidas=(), disciplinas=None, embaralhar=False):
    """Retorna as perguntas permitidas na fase, na ordem em que devem sair.

    1. Perguntas já respondidas NESTA partida (`respondidas`, ids) ficam de
       fora, para que atravessar uma passagem (ou voltar para uma região
       anterior) não repita conteúdo.
    2. Dificuldade: só as de constants.DIFICULDADES_POR_FASE[fase].
    3. Disciplina: as de constants.DISCIPLINAS_POR_FASE[fase] — ou do
       parâmetro `disciplinas` — saem PRIMEIRO. Com DISCIPLINA_ESTRITA, só
       elas saem.

    Por que prioridade e não corte: o banco tem poucas perguntas por
    disciplina. Se o filtro cortasse, a floresta ficaria com 1 pergunta e os
    outros minérios sumiriam sem quiz.

    Nenhum filtro trava o quiz: se um passo zerar a lista, ele é ignorado.
    `embaralhar` embaralha DENTRO de cada grupo, sem desfazer a prioridade.
    """
    disponiveis = [p for p in lista if id(p) not in respondidas]
    if not disponiveis:
        disponiveis = list(lista)

    permitidas = constants.DIFICULDADES_POR_FASE.get(fase)
    if permitidas:
        por_dificuldade = [
            p for p in disponiveis
            if normalizar_texto(p.get("dificuldade", p.get("nivel", ""))) in permitidas
        ]
        if por_dificuldade:
            disponiveis = por_dificuldade

    if disciplinas is None:
        disciplinas = constants.DISCIPLINAS_POR_FASE.get(fase)
    alvos = {normalizar_texto(d) for d in (disciplinas or ())}

    if not alvos:
        if embaralhar:
            random.shuffle(disponiveis)
        return disponiveis

    da_disciplina = [
        p for p in disponiveis if normalizar_texto(p.get("disciplina", "")) in alvos
    ]
    ids_da_disciplina = {id(p) for p in da_disciplina}
    outras = [p for p in disponiveis if id(p) not in ids_da_disciplina]
    if embaralhar:
        random.shuffle(da_disciplina)
        random.shuffle(outras)

    if constants.DISCIPLINA_ESTRITA and da_disciplina:
        return da_disciplina
    return da_disciplina + outras


class BancoPerguntas:
    def __init__(self):
        self.todas = []
        self.fila = []
        self.indice = 0
        self.fase = 1
        self.respondidas = set()

    # ── ciclo da partida ─────────────────────────────────────────────────────
    def nova_partida(self, fase_inicial):
        """Relê os CSVs (quem editou o banco vê a mudança ao clicar em JOGAR),
        zera o histórico e monta a fila da primeira fase."""
        self.todas = carregar_perguntas()
        self.respondidas.clear()
        self.aplicar_fase(fase_inicial)

    def marcar_respondida(self, pergunta):
        self.respondidas.add(id(pergunta))

    # ── fila da fase ─────────────────────────────────────────────────────────
    def filtrar(self, lista, fase, disciplinas=None, embaralhar=False):
        return filtrar_por_fase(lista, fase, self.respondidas, disciplinas, embaralhar)

    def aplicar_fase(self, nova_fase, embaralhar=True):
        """Troca a fase ativa e remonta a fila do quiz.

        O `indice` volta a zero de propósito: ele caminha dentro da fatia da
        fase, não dentro do banco inteiro. A pontuação é global."""
        self.fase = nova_fase
        self.fila = self.filtrar(self.todas, nova_fase, embaralhar=embaralhar)
        self.indice = 0
        if constants.DEBUG:
            print(f"[fase] {nova_fase} -> {len(self.fila)} perguntas disponíveis")

    def avancar_fase(self, nova_fase):
        """Chamada quando o player entra numa região nova."""
        if nova_fase != self.fase:
            self.aplicar_fase(nova_fase)

    # ── consulta ─────────────────────────────────────────────────────────────
    def atual(self):
        """A próxima pergunta da fila, ou None se a fila acabou."""
        if self.indice < len(self.fila):
            return self.fila[self.indice]
        return None
