import pygame
from src.nucleo import constants
from src.nucleo.utils import carregar_fonte

PRETO          = (0,   0,   0)
BRANCO         = (255, 255, 255)
AMARELO        = (241, 187, 52)
AMARELO_ESCURO = (196, 140, 25)

MEMBROS = sorted([
    "LARA DE MELO ANDRADE",
    "VINICIUS CIRQUEIRA DE ARAUJO",
    "JOÃO VITOR MAROTTI",
    "LEANDRO TESTA",
    "ROBERT DANIEL NASCIMENTO CECCHI",
    "VICTÓRIA GEOVANNA DA SILVA SANTOS",
    "VANESSA CRISTINA DO NASCIMENTO",
    "ENZO MODESTO NASCIMENTO DOS SANTOS",
    "MIQUÉIAS SANTOS DE MOURA",
    "ISABELA DOS SANTOS GOMES",
    "THOMAS GARCIA VIANA",
    "MARÍLIA RAYANE CORDEIRO DE OLIVEIRA",
    "PEDRO HENRIQUE TRINDADE SOARES",
    "OTÁVIO PINHEIRO FONSECA SANTOS",
    "FRANCISCO WIRES PAULINO DOS SANTOS JÚNIOR",
    "VINICIUS MACIEL DE OLIVEIRA",
    "MARIA EDUARDA PEREIRA DOS SANTOS",
    "GABRIEL MOURA MATOS",
    "RODRIGO LIMA DE OLIVEIRA",
    "KAUAN SOARES DANTAS",
    "VITÓRIA ALVES BEZERRA BRUNO",
    "KÁTIA MARIA DA SILVA",
    "MAXIMILLIAN BENJAMIN VICENTE",
    "GUILHERME DO CARMO",
    "ENDREW MARCHEZZETTI SANTOS",
    "BEATRIZ CONCEIÇÃO FERREIRA",
    "LUCAS SANTANA SOUZA",
    "JÉSSICA COSTA SILVA",
    "GABRIEL HENRIQUE ANJO MARINHO",
    "CAIO SILVA ROCHA",
    "GABRIEL DANIEL DE SOUSA",
    "PEDRO HENRIQUE CORREIA RODRIGUES",
    "JOÃO PEDRO ALVES DE ALBUQUERQUE",
    "JOÃO VÍTOR BERGARA",
    "ALINE BATISTA DE OLIVEIRA",
])


class TelaCreditos:
    VELOCIDADE_SCROLL = 1.2
    ESPACO_ENTRE     = 35
    ESPACO_TITULO    = 80

    def __init__(self, screen, largura, altura, callback_voltar):
        self.screen          = screen
        self.largura         = largura
        self.altura          = altura
        self.callback_voltar = callback_voltar

        self.fonte_titulo = carregar_fonte("upheavtt.ttf", 32)
        self.fonte_nome   = carregar_fonte("upheavtt.ttf", 16)
        self.fonte_botao  = carregar_fonte("upheavtt.ttf", 18)

        self.scroll_y = float(self.altura)
        self._calcular_altura_total()

        from src.interface.configuracoes import BotaoSimples
        self.btn_voltar = BotaoSimples(
    "VOLTAR", 20, 500, constants.BTN_LARGURA, constants.BTN_ALTURA, acao=self._voltar
        )

    def _calcular_altura_total(self):
        self.altura_total = (
            self.ESPACO_TITULO +
            len(MEMBROS) * self.ESPACO_ENTRE +
            self.altura
        )

    def _voltar(self):
        self.scroll_y = float(self.altura)
        if self.callback_voltar:
            self.callback_voltar()

    def handle_event(self, evento):
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                self._voltar()
            if evento.key == pygame.K_UP:
                self.scroll_y += 40
            if evento.key == pygame.K_DOWN:
                self.scroll_y -= 40
        self.btn_voltar.handle_event(evento)

    def update(self):
        self.scroll_y -= self.VELOCIDADE_SCROLL
        if self.scroll_y < -self.altura_total + self.altura:
            self.scroll_y = float(self.altura)

    def desenhar(self, mouse_pos=None):
        overlay = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))

        cx = self.largura // 2
        y  = self.scroll_y

        surf = self.fonte_titulo.render("CRÉDITOS", True, AMARELO)
        self.screen.blit(surf, surf.get_rect(center=(cx, int(y))))
        y += self.ESPACO_TITULO

        for nome in MEMBROS:
            if -self.ESPACO_ENTRE < y < self.altura + self.ESPACO_ENTRE:
                s_nome = self.fonte_nome.render(nome, True, BRANCO)
                self.screen.blit(s_nome, s_nome.get_rect(center=(cx, int(y))))
            y += self.ESPACO_ENTRE

        # O mouse precisa vir em coordenadas da superfície virtual. Quando não
        # for informado, cai no valor bruto do sistema (válido só em janela).
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        self.btn_voltar.desenhar(self.screen, self.fonte_botao, mouse_pos)