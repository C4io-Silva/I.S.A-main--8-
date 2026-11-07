"""
O Jogo: dono da janela, do áudio, do controle e do estado (tela) atual.

O loop é sempre o mesmo, a cada frame:
    eventos -> controle -> atualizar -> desenhar -> apresentar
e quem sabe o que fazer em cada passo é o Estado ativo (src/jogo/estados/).
"""

import os

import pygame
from pygame import mixer

from src.nucleo import constants
from src.sistemas import sons
from src.mundo.ambientes import GerenciadorAmbientes
from src.sistemas.estatisticas import Banco as BancoEstatisticas
from src.jogo.audio import MUSICA_JOGO, MUSICA_MENU, Audio
from src.jogo.estados import criar_estados
from src.jogo.janela import Janela
from src.jogo.partida import Partida
from src.jogo.visual import Fontes, tamanho_fonte, tela_carregamento
from src.sistemas.joystick import GerenciadorJoystick
from src.quiz.quiz_tela import TelaQuiz
from src.interface.transicao import Transicao
from src.nucleo.utils import carregar_fundo, texto_contorno

TITULO_JANELA = "I.S.A - Intelligent Support Agent"


class Jogo:
    def __init__(self):
        pygame.init()
        try:
            mixer.init()
        except Exception as e:  # noqa: BLE001
            print(f"Mixer não inicializado: {e}")
        sons.iniciar()

        self.audio = Audio()
        sons.definir_volume(self.audio.volume_efeitos)
        self.janela = Janela()
        self.janela.abrir(fullscreen=False)
        pygame.display.set_caption(TITULO_JANELA)
        self.clock = pygame.time.Clock()
        self.carregando(0.0, "Inicializando...")

        # O gamepad é opcional: sem controle, `conectado` fica False e o jogo
        # segue 100% no teclado/mouse. Plugar no meio da partida funciona.
        self.gamepad = GerenciadorJoystick()
        self.banco = BancoEstatisticas()       # SQLite: vive a execução inteira
        self.tela_quiz = TelaQuiz(tamanho_fonte, self.janela.mouse_virtual)

        self.aluno = "Aluno"                   # nome digitado na tela de registro
        self.partida = None                    # None fora da partida
        self.foco_no_controle = False          # quem manda no destaque: controle ou mouse
        self.rodando = True
        self._pdf_atual = None                 # relatório gerado (apagado ao reiniciar/voltar)

        self.estado = None
        self.estado_nome = None
        self.recriar_ui()

        self.audio.tocar_musica(MUSICA_MENU)
        self.ir_para("INTRO_LOGO")

    # ── interface ────────────────────────────────────────────────────────────
    def carregando(self, progresso, mensagem):
        tela_carregamento(self.janela, progresso, mensagem)

    def recriar_ui(self):
        """(Re)cria tudo o que depende da tela: fundo, ambientes, fontes e estados."""
        W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
        self.carregando(0.1, "Carregando interface...")
        # carregar_fundo cobre sem distorcer (a largura virtual varia)
        self.fundo = carregar_fundo("backgrounds", "Entrada.png", (W, H))

        self.carregando(0.3, "Carregando ambientes...")
        # Um único objeto carrega TODOS os ambientes da fase de uma vez. Fica
        # aqui porque as camadas são escaladas pela altura da virtual, e assim
        # reiniciar a partida não recarrega imagem nenhuma.
        self.ambientes = GerenciadorAmbientes(W, H)
        self.ambientes.forcar(constants.SETORES[constants.SETOR_INICIAL]["ambiente"])
        self.transicao = Transicao()    # fade ao usar uma passagem entre regiões

        self.carregando(0.5, "Carregando fontes...")
        self.fontes = Fontes.carregar()
        self.titulo_logo = texto_contorno(
            self.fontes.logo, "I.S.A", (255, 220, 40), (20, 30, 110), espessura=4)

        self.carregando(0.7, "Carregando botões...")
        self.estados = criar_estados(self)
        if self.estado_nome is not None:
            self.estado = self.estados[self.estado_nome]
        self.carregando(1.0, "Pronto!")

    # ── estados ──────────────────────────────────────────────────────────────
    def ir_para(self, nome, **dados):
        """Troca a tela ativa: sai da atual e entra na nova."""
        if self.estado is not None:
            self.estado.sair()
        self.estado_nome = nome
        self.estado = self.estados[nome]
        self.estado.entrar(**dados)

    # ── ações de fluxo (usadas pelos botões e pelas telas) ───────────────────
    def confirmar_login(self, nome):
        """Guarda o nome (usado no relatório em PDF) e abre a cutscene."""
        self.aluno = (nome or "").strip() or "Aluno"
        self.ir_para("CUTSCENE")

    def iniciar_partida(self):
        """
        Partida nova: relê os CSVs, abre uma sessão de estatísticas e monta o
        mundo. REINICIAR chama isto direto; a cutscene só aparece uma vez por
        vez que o jogador clica em JOGAR e registra o nome.
        """
        self.apagar_pdf()
        self.partida = Partida(self)
        self.ir_para("JOGANDO")
        self.audio.tocar_musica(MUSICA_JOGO)

    def abrir_estatisticas(self):
        """Estatísticas da sessão ATUAL; funciona até com 0 perguntas respondidas."""
        sessao = self.partida.sessao_id if self.partida else None
        try:
            resultado = self.banco.buscar_resultado(sessao)
        except Exception as e:  # noqa: BLE001 - a tela não pode quebrar o jogo
            print(f"Erro ao carregar estatísticas: {e}")
            resultado = self.banco.resultado_vazio(self.aluno)
        self.ir_para("ESTATISTICAS", resultado=resultado)

    def voltar_menu(self):
        self.apagar_pdf()
        self.partida = None
        self.ir_para("MENU")
        self.audio.tocar_musica(MUSICA_MENU)
        self.audio.restaurar_volume()

    def encerrar(self):
        self.rodando = False

    # ── relatório em PDF ─────────────────────────────────────────────────────
    def registrar_pdf(self, caminho):
        """Chamado pela tela de estatísticas quando um PDF é gerado: guarda qual
        arquivo apagar depois (reiniciar / voltar ao menu)."""
        self._pdf_atual = caminho

    def apagar_pdf(self):
        """Apaga o PDF da sessão que está sendo encerrada, para não acumular
        relatórios no disco. Nunca derruba o jogo se falhar (ex.: arquivo
        ainda aberto no leitor de PDF)."""
        if not self._pdf_atual:
            return
        try:
            if os.path.exists(self._pdf_atual):
                os.remove(self._pdf_atual)
        except OSError as e:
            print(f"Aviso: não foi possível apagar o PDF de estatísticas: {e}")
        self._pdf_atual = None

    # ── loop ─────────────────────────────────────────────────────────────────
    def rodar(self):
        while self.rodando:
            self.passo()
        self.banco.fechar()
        pygame.quit()

    def passo(self):
        """Um frame completo."""
        dt_ms = self.clock.tick(constants.FPS)
        mouse_pos = self.janela.mouse_virtual()
        if self.partida:
            # Borda, não estado: zera aqui, os eventos ligam e a checagem de
            # passagens consome (ver partida/entrada.py).
            self.partida.entrada.interagir = False

        for evento in pygame.event.get():
            self._tratar_evento(self.janela.converter_evento(evento))
        self._tratar_controle()

        self.estado.atualizar(dt_ms)
        self.estado.desenhar(self.janela.tela, mouse_pos)
        self.janela.apresentar()

    def _tratar_evento(self, evento):
        if evento.type == pygame.QUIT:
            self.rodando = False
        self.gamepad.processar_evento(evento)
        if evento.type == pygame.MOUSEMOTION:
            self.foco_no_controle = False      # mexeu o mouse: o destaque volta ao cursor
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F11:
            self.janela.alternar_fullscreen()
        else:
            self.estado.evento(evento)

    def _tratar_controle(self):
        """Lido por polling, uma vez por frame: o analógico é estado contínuo e
        não gera evento quando fica parado. Soma-se ao teclado."""
        gamepad = self.gamepad
        gamepad.atualizar()
        if not gamepad.conectado:
            return
        if (gamepad.nav_x or gamepad.nav_y or gamepad.confirmou_agora
                or gamepad.voltou_agora or gamepad.pausou_agora):
            self.foco_no_controle = True
        self.estado.controle(gamepad)
