import pygame

from src.admin.tela_perguntas import TelaPerguntas
from src.admin.tela_senha import TelaSenhaAdmin
from src.jogo.estados.base import Estado


class EstadoAdminSenha(Estado):
    """Pede a senha do ADMIN (ver src/admin/__init__.py)."""

    def __init__(self, jogo):
        super().__init__(jogo)
        self.tela = TelaSenhaAdmin(
            jogo.janela.tela,
            jogo.fundo,
            callback_voltar=lambda: jogo.ir_para("LOGIN"),
            callback_sucesso=lambda: jogo.ir_para("ADMIN"),
        )

    def entrar(self, **dados):
        self.tela.resetar()

    def sair(self):
        pygame.key.stop_text_input()

    def evento(self, ev):
        self.tela.handle_event(ev)

    def controle(self, gamepad):
        if gamepad.voltou_agora:
            self.tela.voltar()

    def desenhar(self, tela, mouse_pos):
        self.tela.desenhar(mouse_pos)


class EstadoAdmin(Estado):
    """Painel para adicionar, editar e excluir perguntas (salva nos CSVs)."""

    def __init__(self, jogo):
        super().__init__(jogo)
        self.tela = TelaPerguntas(
            jogo.janela.tela,
            jogo.fundo,
            callback_voltar=lambda: jogo.ir_para("LOGIN"),
        )

    def entrar(self, **dados):
        self.tela.recarregar()

    def sair(self):
        pygame.key.stop_text_input()

    def evento(self, ev):
        self.tela.handle_event(ev)

    def controle(self, gamepad):
        if gamepad.voltou_agora:
            self.tela.tecla_voltar()

    def desenhar(self, tela, mouse_pos):
        self.tela.desenhar(mouse_pos)
