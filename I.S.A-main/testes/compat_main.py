"""
Fachada de COMPATIBILIDADE só para os testes.

Os testes antigos foram escritos contra o `main.py` monolítico, com dezenas de
variáveis globais (`M.player`, `M.estado_jogo`, `M.moving_right`...). Em vez de
reescrever a lógica de cada teste — e perder a prova de que o jogo continua
fazendo a mesma coisa —, esta fachada traduz o nome antigo para o objeto novo
(Jogo ou Partida). O código do jogo NÃO usa isto.

    from compat_main import M
"""



from src.jogo.estados.jogando import TECLAS_GOLPE
from src.jogo.partida.partida import assentar
from src.jogo.partida.perguntas import carregar_perguntas, filtrar_por_fase

# nome antigo -> (objeto base, caminho no objeto)
_ROTAS = {
    # partida
    "player": ("partida", "player"),
    "setor_atual": ("partida", "setor_atual"),
    "setores": ("partida", "setores"),
    "enemies": ("partida", "enemies"),
    "itens": ("partida", "itens"),
    "curas": ("partida", "curas"),
    "boss": ("partida", "boss"),
    "area_boss": ("partida", "area_boss"),
    "world": ("partida", "world"),
    "golpe": ("partida", "golpe"),
    "efeitos": ("partida", "efeitos"),
    "passagens_cenario": ("partida", "passagens"),
    "passagem_ao_alcance": ("partida", "passagem_ao_alcance"),
    "inimigos_derrotados": ("partida", "inimigos_derrotados"),
    "pontuacao": ("partida", "pontuacao"),
    "ordem_resposta": ("partida", "ordem_resposta"),
    "sessao_atual_id": ("partida", "sessao_id"),
    "morreu_na_arena": ("partida", "morreu_na_arena"),
    "aviso_jogo": ("partida", "aviso"),
    "quiz_mensagem": ("partida", "quiz.mensagem"),
    "quiz_boss": ("partida", "quiz.boss"),
    "perguntas": ("partida", "perguntas.fila"),
    "indice": ("partida", "perguntas.indice"),
    "fase_atual": ("partida", "perguntas.fase"),
    "todas_perguntas": ("partida", "perguntas.todas"),
    "moving_left": ("partida", "entrada.esquerda"),
    "moving_right": ("partida", "entrada.direita"),
    "jump_pressed": ("partida", "entrada.pulo"),
    "interagir_pressionado": ("partida", "entrada.interagir"),
    # jogo
    "gamepad": ("jogo", "gamepad"),
    "clock": ("jogo", "clock"),
    "transicao": ("jogo", "transicao"),
    "ambientes": ("jogo", "ambientes"),
    "banco_estatisticas": ("jogo", "banco"),
    "aluno_atual": ("jogo", "aluno"),
    "quiz_tela": ("jogo", "tela_quiz"),
    "foco_no_controle": ("jogo", "foco_no_controle"),
    "screen": ("jogo", "janela.tela"),
    "botoes_game_over_boss": ("jogo", "estados.GAME_OVER.menu_boss.botoes"),
}


def _resolver(raiz, caminho):
    objeto = raiz
    for parte in caminho.split("."):
        objeto = objeto[parte] if isinstance(objeto, dict) else getattr(objeto, parte)
    return objeto


class _Legado:
    def __init__(self):
        object.__setattr__(self, "_jogo", None)
        object.__setattr__(self, "_ids_avulsos", set())   # antes de existir partida

    # ── acesso preguiçoso: o Jogo só nasce no primeiro uso ───────────────────
    @property
    def jogo(self):
        if self._jogo is None:
            from src.jogo.app import Jogo
            object.__setattr__(self, "_jogo", Jogo())
        return self._jogo

    def _base(self, nome):
        return self.jogo if nome == "jogo" else self.jogo.partida

    def __getattr__(self, nome):
        if nome == "estado_jogo":
            return self.jogo.estado_nome
        if nome == "_ids_respondidas":
            partida = self.jogo.partida
            return partida.perguntas.respondidas if partida else self._ids_avulsos
        if nome in _ROTAS:
            base, caminho = _ROTAS[nome]
            return _resolver(self._base(base), caminho)
        raise AttributeError(nome)

    def __setattr__(self, nome, valor):
        if nome == "estado_jogo":
            # Troca direta, sem entrar/sair: é o que o `estado_jogo = ...` antigo fazia.
            self.jogo.estado_nome = valor
            self.jogo.estado = self.jogo.estados[valor]
            return
        if nome not in _ROTAS:
            raise AttributeError(f"a fachada não conhece '{nome}'")
        base, caminho = _ROTAS[nome]
        *pai, folha = caminho.split(".")
        alvo = _resolver(self._base(base), ".".join(pai)) if pai else self._base(base)
        setattr(alvo, folha, valor)

    # ── funções do antigo main ───────────────────────────────────────────────
    TECLAS_GOLPE = TECLAS_GOLPE

    def configurar_janela(self, fullscreen=False):
        self.jogo.janela.abrir(fullscreen)

    def recriar_ui(self):
        self.jogo.recriar_ui()

    def iniciar_jogo(self):
        self.jogo.iniciar_partida()

    def atualizar_jogando(self, dt_ms):
        self.jogo.partida.atualizar_jogando(dt_ms)

    def passo_da_partida(self, dt_ms):
        self.jogo.estado.atualizar(dt_ms)

    def desenhar_jogo(self, mouse_pos):
        nome = "PAUSADO" if self.jogo.estado_nome == "PAUSADO" else "JOGANDO"
        self.jogo.estados[nome].desenhar(self.jogo.janela.tela, mouse_pos)

    def desenhar_vitoria(self, mouse_pos):
        self.jogo.estados["VITORIA"].desenhar(self.jogo.janela.tela, mouse_pos)

    def pergunta_em_jogo(self):
        return self.jogo.partida.quiz.pergunta_em_jogo()

    def processar_resposta(self, resposta):
        self.jogo.partida.quiz.responder(resposta)

    def cancelar_quiz(self):
        self.jogo.partida.quiz.cancelar()

    def segundos_restantes_boss(self):
        return self.jogo.partida.quiz.segundos_restantes_boss()

    def reiniciar_movimento(self):
        self.jogo.partida.entrada.zerar_movimento()

    def reiniciar_luta_boss(self):
        self.jogo.partida.reiniciar_luta_boss()

    def ativar_setor(self, nome):
        self.jogo.partida.ativar_setor(nome)

    def atualizar_camera(self, instantaneo=False):
        self.jogo.partida.atualizar_camera(instantaneo)

    def area_ativa(self):
        return self.jogo.partida.area_ativa()

    def carregar_perguntas(self):
        return carregar_perguntas()

    def filtrar_perguntas_por_fase(self, lista, fase, disciplinas=None, embaralhar=False):
        return filtrar_por_fase(lista, fase, self._ids_respondidas, disciplinas, embaralhar)

    def _assentar(self, entidade, col, row_superficie, altura_tiles=0):
        return assentar(entidade, col, row_superficie, altura_tiles)

    def _checar_passagens(self):
        self.jogo.partida.checar_passagens()

    def _verificar_coletas(self):
        return self.jogo.partida.verificar_coletas()

    def _limitar_player_ao_setor(self):
        self.jogo.partida.limitar_ao_setor()

    def _movimento_do_player(self):
        return self.jogo.partida.movimento_do_player()


M = _Legado()
