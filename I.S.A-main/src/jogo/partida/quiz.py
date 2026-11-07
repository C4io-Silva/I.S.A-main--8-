"""
A pergunta aberta na partida: a do minério comum (fila normal) ou a do
minério arremessado pelo boss (com prazo). Cuida da resposta, do registro nas
estatísticas e do feedback de acerto/erro.
"""

import random

import pygame

from src.nucleo import constants
from src.sistemas import sons
from src.jogo.partida.perguntas import normalizar_texto
from src.nucleo.utils import obter_alternativas_pergunta

FRAMES_DE_FEEDBACK = 90


class ControleQuiz:
    def __init__(self, partida, tela):
        self.partida = partida
        self.tela = tela              # TelaQuiz: scroll, alternativas, seleção
        self.mensagem = ""
        self.acertou = False          # decide a cor do feedback (não o texto da mensagem)
        self.timer = 0                # frames restantes do feedback
        self.item_para_remover = None
        # Pergunta aberta pelo MINÉRIO DO BOSS (None fora dela): dict com a
        # pergunta, o projétil e o prazo. Fica separada da fila normal para
        # não bagunçar o índice do quiz comum.
        self.boss = None
        self.tela.reiniciar()

    # ── consulta ─────────────────────────────────────────────────────────────
    def pergunta_em_jogo(self):
        """A pergunta mostrada agora: a do minério do boss ou a da fila normal."""
        if self.boss is not None:
            return self.boss["pergunta"]
        return self.partida.perguntas.atual()

    def segundos_restantes_boss(self):
        if self.boss is None:
            return None
        return max(0, (self.boss["prazo"] - pygame.time.get_ticks() + 999) // 1000)

    # ── abertura ─────────────────────────────────────────────────────────────
    def abrir_para_minerio(self, item):
        """Minério tocado: abre a próxima pergunta da fila."""
        self.partida.jogo.ir_para("QUIZ")
        self.tela.reiniciar()
        self.partida.entrada.zerar_movimento()
        self.item_para_remover = item
        self.partida.jogo.audio.abaixar_para_quiz()

    @staticmethod
    def _prazo_boss(pergunta):
        """Tempo justo para ler e responder: mínimo + tamanho do texto."""
        texto = pergunta.get("pergunta", "") + " ".join(
            t for _, t in obter_alternativas_pergunta(pergunta))
        segundos = constants.QUIZ_BOSS_MIN_S + len(texto) / constants.QUIZ_BOSS_CHARS_POR_S
        return int(min(constants.QUIZ_BOSS_MAX_S, segundos) * 1000)

    def iniciar_boss(self, gorila, projetil):
        """
        O minério arremessado pelo Gorila acertou o jogador: abre uma pergunta
        com tempo. Cobre = Fácil, zinco = Médio; prefere perguntas curtas e
        ainda não respondidas. Sem pergunta elegível o minério simplesmente
        causa dano — o jogo nunca fica preso.
        """
        partida = self.partida
        banco = partida.perguntas
        alvo = "facil" if projetil.tipo_minerio == "cobre" else "medio"
        elegiveis = [p for p in banco.todas
                     if normalizar_texto(p.get("dificuldade", "")) == alvo] or list(banco.todas)
        nao_usadas = [p for p in elegiveis if id(p) not in banco.respondidas] or elegiveis
        curtas = [p for p in nao_usadas if len(p.get("pergunta", "")) <= 220] or nao_usadas
        if not curtas:
            projetil.causar_dano(partida.player)
            if projetil in gorila.projeteis:
                gorila.projeteis.remove(projetil)
            return
        pergunta = random.choice(curtas)
        self.boss = {
            "boss": gorila,
            "projetil": projetil,
            "pergunta": pergunta,
            "prazo": pygame.time.get_ticks() + self._prazo_boss(pergunta),
        }
        partida.jogo.ir_para("QUIZ")
        self.tela.reiniciar()
        partida.entrada.zerar_movimento()
        partida.jogo.audio.abaixar_para_quiz()

    # ── resposta ─────────────────────────────────────────────────────────────
    def responder(self, resposta):
        """
        Aplica a resposta da pergunta em jogo. `resposta` é "a".."e"; "" (vazio)
        significa TEMPO ESGOTADO na pergunta do boss e conta como erro.

        Quiz normal : acertou +20 de vida; errou -DAMAGE. O minério é consumido.
        Quiz do boss: acertou -> o minério volta e acerta o Gorila; errou -> o
                      minério acerta o jogador (dano do projétil).
        Em ambos a resposta é gravada no SQLite e a pontuação conta acertos.
        """
        partida = self.partida
        jogo = partida.jogo
        player = partida.player

        pergunta_atual = self.pergunta_em_jogo()
        if pergunta_atual is None or resposta is None:
            return
        if not resposta and self.boss is None:
            return

        gabarito = pergunta_atual.get("resposta", "").strip().lower()
        acertou = bool(resposta) and resposta == gabarito
        self.acertou = acertou
        evento = self.boss

        if acertou:
            partida.pontuacao += 1
            sons.tocar("acerto")
            if evento:
                self.mensagem = "ACERTOU! O MINERIO VOLTOU PARA O GORILA!"
                evento["projetil"].refletir()
            else:
                self.mensagem = "VOCE ACERTOU! +20 de vida"
                if player and player.alive:
                    player.player_health = min(player.player_health + 20,
                                               constants.PLAYER_HEALTH)
        else:
            sons.tocar("erro")
            if evento:
                self.mensagem = ("TEMPO ESGOTADO! O MINERIO TE ACERTOU!" if not resposta
                                 else "ERROU! O MINERIO TE ACERTOU!")
                projetil = evento["projetil"]
                if player and player.alive:
                    player.invulnerable = False   # o acerto do minério sempre conta
                    projetil.causar_dano(player)
                if projetil in evento["boss"].projeteis:
                    evento["boss"].projeteis.remove(projetil)
            else:
                self.mensagem = "VOCE ERROU!"
                if player and player.alive:
                    player.player_health -= constants.DAMAGE
                    if player.player_health <= 0:
                        player.player_health = 0
                        player.alive = False

        self._registrar_nas_estatisticas(pergunta_atual, gabarito, resposta)

        # Marca como usada para o filtro de fase não sortear de novo.
        partida.perguntas.marcar_respondida(pergunta_atual)

        self.timer = FRAMES_DE_FEEDBACK
        if evento:
            self.boss = None
            if player:
                # Volta do quiz com um respiro: nenhuma banana em voo acerta o
                # jogador no primeiro frame de controle.
                player.invulnerable = True
                player.last_stunned_time = (pygame.time.get_ticks()
                                            - player.invulnerable_duration
                                            + constants.GRACA_POS_QUIZ_MS)
        else:
            partida.perguntas.indice += 1
            if self.item_para_remover and self.item_para_remover in partida.itens:
                partida.itens.remove(self.item_para_remover)
            self.item_para_remover = None
        self.tela.reiniciar()   # próxima pergunta começa do topo
        partida.entrada.zerar_movimento()
        jogo.ir_para("QUIZ_FEEDBACK")
        jogo.audio.restaurar_volume()

    def _registrar_nas_estatisticas(self, pergunta, gabarito, resposta):
        """Cada resposta é salva na hora: a tela de desempenho funciona mesmo
        se o jogador sair no meio da partida."""
        partida = self.partida
        if partida.sessao_id is None:
            return
        partida.ordem_resposta += 1
        try:
            partida.jogo.banco.registrar_resposta(
                partida.sessao_id,
                partida.ordem_resposta,
                pergunta.get("disciplina", "Geral"),
                pergunta.get("dificuldade", pergunta.get("nivel", "Médio")),
                pergunta.get("pergunta", ""),
                obter_alternativas_pergunta(pergunta),
                gabarito,
                resposta,
            )
        except Exception as e:  # noqa: BLE001 - nunca derruba o quiz por causa disso
            print(f"Erro ao salvar resposta nas estatísticas: {e}")

    def cancelar(self):
        """
        ESC / botão voltar no quiz NORMAL: fecha a pergunta SEM consumir o
        minério (ele volta a aparecer e pode ser coletado de novo). O quiz do
        boss não pode ser cancelado — o minério já está no ar.
        """
        if self.boss is not None:
            return
        if self.item_para_remover is not None:
            self.item_para_remover.liberar()
        self.item_para_remover = None
        self.tela.reiniciar()
        self.partida.entrada.zerar_movimento()
        self.partida.jogo.ir_para("JOGANDO")
        self.partida.jogo.audio.restaurar_volume()

    # ── por frame ────────────────────────────────────────────────────────────
    def atualizar_prazo_boss(self):
        """Prazo da pergunta do minério do boss: estourou, conta como erro."""
        if self.boss is not None and pygame.time.get_ticks() >= self.boss["prazo"]:
            self.responder("")

    def atualizar_feedback(self):
        """Conta os frames do feedback; ao acabar, volta ao jogo (ou ao game over)."""
        if self.timer > 0:
            self.timer -= 1
        if self.timer == 0:
            self.mensagem = ""
            if self.partida.player and not self.partida.player.alive:
                self.partida.fim_de_jogo()
            else:
                self.partida.jogo.ir_para("JOGANDO")
