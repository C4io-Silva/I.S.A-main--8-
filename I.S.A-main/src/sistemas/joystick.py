"""
Suporte a joystick / gamepad.

O resto do jogo é baseado em EVENTOS de teclado e mouse, mas analógico é
estado contínuo: não existe "evento de analógico parado no meio". Por isso
aqui a leitura é feita por polling — uma vez por frame, via `atualizar()` — e
o resultado é exposto como propriedades que o main.py combina com o teclado.

Duas ideias sustentam a classe:

1. Zona morta. Analógicos gastos reportam ~0.1 mesmo em repouso; sem filtro o
   personagem anda sozinho e a animação de caminhada nunca para.
2. Detecção de borda. "Botão pressionado" ≠ "botão acabou de ser pressionado".
   Pular precisa da borda, senão o personagem pula em todo frame em que o
   botão estiver segurado.
"""

import pygame

from src.nucleo import constants


class GerenciadorJoystick:
    def __init__(self):
        self.joystick = None
        self.nome = ""
        self._botoes = {}          # estado do frame atual
        self._botoes_antes = {}    # estado do frame anterior (bordas)
        self.eixo_x = 0.0
        self.eixo_y = 0.0
        # Navegação em menus: pulsos discretos com repetição ao segurar.
        self.nav_x = 0
        self.nav_y = 0
        self._dir_x_antes = 0
        self._dir_y_antes = 0
        self._t_repete_x = 0
        self._t_repete_y = 0

        if constants.JOYSTICK_HABILITADO:
            pygame.joystick.init()
            self._conectar()

    # ── Conexão ──────────────────────────────────────────────────────
    @property
    def conectado(self):
        return self.joystick is not None

    def _conectar(self):
        try:
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.nome = self.joystick.get_name()
                print(f"Controle conectado: {self.nome}")
            else:
                self.joystick = None
                self.nome = ""
        except pygame.error as e:
            # Um controle problemático não pode derrubar o jogo inteiro.
            print(f"Falha ao inicializar o controle: {e}")
            self.joystick = None

    def _desconectar(self):
        self.joystick = None
        self.nome = ""
        self._zerar()
        print("Controle desconectado.")

    def processar_evento(self, evento):
        """Chamar para cada evento do loop principal.

        Cuida apenas de conectar/desconectar em tempo de execução — tirar o
        cabo no meio da partida não deve travar nem crashar o jogo.
        """
        if not constants.JOYSTICK_HABILITADO:
            return
        if evento.type == pygame.JOYDEVICEADDED:
            if not self.conectado:
                self._conectar()
        elif evento.type == pygame.JOYDEVICEREMOVED:
            self._desconectar()
        elif evento.type == pygame.JOYBUTTONDOWN and constants.DEBUG:
            # Ajuda a descobrir a numeração real do seu controle para ajustar
            # o mapeamento em constants.py.
            print(f"[joystick] botão {evento.button} pressionado")

    # ── Leitura por frame ────────────────────────────────────────────
    def _zerar(self):
        self._botoes_antes = {}
        self._botoes = {}
        self.eixo_x = self.eixo_y = 0.0
        self.nav_x = self.nav_y = 0
        self._dir_x_antes = self._dir_y_antes = 0

    def _ler_eixo(self, indice):
        if self.joystick.get_numaxes() <= indice:
            return 0.0
        valor = self.joystick.get_axis(indice)
        return valor if abs(valor) > constants.JOY_ZONA_MORTA else 0.0

    def _ler_hat(self):
        """D-pad. Muitos controles reportam o d-pad separado do analógico."""
        if self.joystick.get_numhats() > 0:
            hx, hy = self.joystick.get_hat(0)
            return hx, -hy  # hat manda Y invertido em relação à tela
        return 0, 0

    def atualizar(self):
        """Chamar uma vez por frame, antes de atualizar o jogo."""
        self._botoes_antes = dict(self._botoes)

        if not self.conectado:
            self._zerar()
            return

        try:
            hat_x, hat_y = self._ler_hat()
            ex = self._ler_eixo(constants.JOY_EIXO_X) + hat_x
            ey = self._ler_eixo(constants.JOY_EIXO_Y) + hat_y
            self.eixo_x = max(-1.0, min(1.0, ex))
            self.eixo_y = max(-1.0, min(1.0, ey))

            self._botoes = {
                i: bool(self.joystick.get_button(i))
                for i in range(self.joystick.get_numbuttons())
            }
        except pygame.error:
            # Controle arrancado entre o evento e a leitura.
            self._desconectar()
            return

        agora = pygame.time.get_ticks()
        self.nav_x, self._dir_x_antes, self._t_repete_x = self._pulso(
            self.eixo_x, self._dir_x_antes, self._t_repete_x, agora
        )
        self.nav_y, self._dir_y_antes, self._t_repete_y = self._pulso(
            self.eixo_y, self._dir_y_antes, self._t_repete_y, agora
        )

    def _pulso(self, eixo, dir_antes, t_repete, agora):
        """Converte um eixo contínuo em pulsos -1/0/1 para navegar em menus.

        Dispara na hora em que a direção é assumida e, se continuar segurada,
        volta a disparar em intervalos regulares.
        """
        limiar = constants.JOY_LIMIAR_EIXO
        direcao = 0
        if eixo <= -limiar:
            direcao = -1
        elif eixo >= limiar:
            direcao = 1

        if direcao == 0:
            return 0, 0, 0
        if direcao != dir_antes:
            return direcao, direcao, agora + constants.JOY_REPETICAO_ATRASO
        if agora >= t_repete:
            return direcao, direcao, agora + constants.JOY_REPETICAO_INTERVALO
        return 0, direcao, t_repete

    # ── Consultas de botão ────────────────────────────────────────────
    def pressionado(self, indice):
        return self._botoes.get(indice, False)

    def acabou_de_apertar(self, indice):
        return self._botoes.get(indice, False) and not self._botoes_antes.get(
            indice, False
        )

    # Atalhos com nome de ação, para o main.py não lidar com índices.
    @property
    def pulou_agora(self):
        return self.acabou_de_apertar(constants.JOY_BOTAO_PULO)

    @property
    def confirmou_agora(self):
        return self.acabou_de_apertar(constants.JOY_BOTAO_CONFIRMAR)

    @property
    def voltou_agora(self):
        return self.acabou_de_apertar(constants.JOY_BOTAO_VOLTAR)

    @property
    def pausou_agora(self):
        return self.acabou_de_apertar(
            constants.JOY_BOTAO_PAUSA
        ) or self.acabou_de_apertar(constants.JOY_BOTAO_PAUSA_ALT)

    @property
    def scroll(self):
        """-1 rolar para cima, 1 para baixo, 0 parado (LB/RB segurados)."""
        valor = 0
        if self.pressionado(constants.JOY_BOTAO_SCROLL_CIMA):
            valor -= 1
        if self.pressionado(constants.JOY_BOTAO_SCROLL_BAIXO):
            valor += 1
        return valor

    # ── Utilitários de menu ──────────────────────────────────────────
def centro_do_botao(botao):
    """Centro de um botão, seja ele retangular (Botao) ou circular.

    Os botões redondos (BotaoConfig, BotaoSair) guardam cx/cy em vez de rect,
    então quem navega por eles precisa desta normalização.
    """
    rect = getattr(botao, "rect", None)
    if rect is not None:
        return rect.center
    return (getattr(botao, "cx", 0), getattr(botao, "cy", 0))


def ordem_de_navegacao(botoes):
    """Índices dos botões ordenados de cima para baixo, esquerda para direita.

    As listas de botões do jogo estão na ordem em que foram criadas, que não
    é a ordem visual — no menu, por exemplo, LOGIN aparece acima de JOGAR mas
    vem depois na lista. Navegar na ordem da lista pareceria aleatório.
    """
    return sorted(
        range(len(botoes)),
        key=lambda i: (centro_do_botao(botoes[i])[1], centro_do_botao(botoes[i])[0]),
    )


def navegar(botoes, indice_atual, passo):
    """Move a seleção `passo` posições na ordem visual, circulando nas pontas."""
    if not botoes:
        return indice_atual
    ordem = ordem_de_navegacao(botoes)
    try:
        pos = ordem.index(indice_atual)
    except ValueError:
        pos = 0
    return ordem[(pos + passo) % len(ordem)]


def acionar(botoes, indice):
    """Executa a ação do botão selecionado (equivalente ao clique do mouse)."""
    if 0 <= indice < len(botoes):
        acao = getattr(botoes[indice], "acao", None)
        if acao:
            acao()
            return True
    return False
