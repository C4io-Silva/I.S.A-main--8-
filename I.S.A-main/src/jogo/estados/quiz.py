import pygame

from src.nucleo import constants
from src.jogo.estados.base import Estado

TECLAS_RESPOSTA = {
    pygame.K_1: "a", pygame.K_2: "b", pygame.K_3: "c", pygame.K_4: "d", pygame.K_5: "e",
    pygame.K_a: "a", pygame.K_b: "b", pygame.K_c: "c", pygame.K_d: "d", pygame.K_e: "e",
}
PASSO_ROLAGEM_MOUSE = 25
# B também é o golpe: um B dado para atacar no instante em que o minério foi
# tocado não deve fechar a pergunta recém-aberta.
JANELA_ANTI_CANCELAMENTO_MS = 600


class EstadoQuiz(Estado):
    def evento(self, ev):
        partida = self.jogo.partida
        quiz = partida.quiz
        if ev.type == pygame.MOUSEWHEEL:
            quiz.tela.rolar(-ev.y * PASSO_ROLAGEM_MOUSE)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            # Só conta se estiver na área visível (recortada) do conteúdo;
            # senão daria para "clicar" numa alternativa escondida pelo scroll.
            letra = quiz.tela.alternativa_em(ev.pos)
            if letra:
                quiz.responder(letra)
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                quiz.cancelar()   # só o quiz normal; o do boss ignora
                return
            resposta = TECLAS_RESPOSTA.get(ev.key)
            if resposta:
                quiz.responder(resposta)

    def controle(self, gamepad):
        partida = self.jogo.partida
        quiz = partida.quiz
        if gamepad.nav_y:
            quiz.tela.navegar(gamepad.nav_y)
        if gamepad.scroll:
            quiz.tela.rolar(gamepad.scroll * constants.JOY_SCROLL_PASSO)
        if gamepad.confirmou_agora:
            letra = quiz.tela.letra_selecionada()
            if letra:
                quiz.responder(letra)
        elif (gamepad.voltou_agora
              and pygame.time.get_ticks() - partida.golpe.inicio > JANELA_ANTI_CANCELAMENTO_MS):
            quiz.cancelar()

    def atualizar(self, dt_ms):
        self.jogo.partida.quiz.atualizar_prazo_boss()

    def desenhar(self, tela, mouse_pos):
        jogo = self.jogo
        partida = jogo.partida
        quiz = partida.quiz
        try:
            pergunta = quiz.pergunta_em_jogo()
            if pergunta is not None:
                no_boss = quiz.boss is not None
                quiz.tela.desenhar(
                    tela, pergunta, partida.pontuacao,
                    0 if no_boss else partida.perguntas.indice,
                    1 if no_boss else len(partida.perguntas.fila),
                    quiz.mensagem, quiz.timer,
                    foco_no_controle=jogo.foco_no_controle,
                    segundos_restantes=quiz.segundos_restantes_boss(),
                )
                return
        except Exception as e:  # noqa: BLE001
            print(f"Erro ao desenhar pergunta: {e}")
        # Não deveria acontecer (a coleta já checa), mas se acontecer a música
        # não pode ficar baixa nem o jogo preso aqui.
        jogo.ir_para("JOGANDO")
        jogo.audio.restaurar_volume()
