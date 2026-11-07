"""Todos os estados do jogo, indexados pelo nome usado em Jogo.ir_para()."""

from src.jogo.estados.admin import EstadoAdmin, EstadoAdminSenha
from src.jogo.estados.configuracoes import EstadoConfiguracoes
from src.jogo.estados.creditos import EstadoCreditos
from src.jogo.estados.cutscene import EstadoCutscene
from src.jogo.estados.estatisticas import EstadoEstatisticas
from src.jogo.estados.game_over import EstadoGameOver
from src.jogo.estados.intro_logo import EstadoIntroLogo
from src.jogo.estados.jogando import EstadoJogando
from src.jogo.estados.login import EstadoLogin
from src.jogo.estados.menu import EstadoMenu
from src.jogo.estados.pausa import EstadoPausa
from src.jogo.estados.quiz import EstadoQuiz
from src.jogo.estados.quiz_feedback import EstadoQuizFeedback
from src.jogo.estados.vitoria import EstadoVitoria

CLASSES = {
    "INTRO_LOGO": EstadoIntroLogo,
    "MENU": EstadoMenu,
    "LOGIN": EstadoLogin,
    "ADMIN_SENHA": EstadoAdminSenha,
    "ADMIN": EstadoAdmin,
    "CUTSCENE": EstadoCutscene,
    "JOGANDO": EstadoJogando,
    "PAUSADO": EstadoPausa,
    "QUIZ": EstadoQuiz,
    "QUIZ_FEEDBACK": EstadoQuizFeedback,
    "GAME_OVER": EstadoGameOver,
    "VITORIA": EstadoVitoria,
    "CONFIGURACOES": EstadoConfiguracoes,
    "CREDITOS": EstadoCreditos,
    "ESTATISTICAS": EstadoEstatisticas,
}


def criar_estados(jogo):
    return {nome: classe(jogo) for nome, classe in CLASSES.items()}
