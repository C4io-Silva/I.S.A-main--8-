import pygame

from src.interface.buttons import Botao, BotaoConfig
from src.nucleo.estilo import (
    AMARELO_TITULO,
    CONTORNO_TITULO,
    DOURADO,
    BotaoVoltar,
    CacheTexto,
    SliderMenu,
    criar_painel,
    criar_veu_topo,
    desenhar_separador,
)
from src.nucleo.utils import carregar_fonte, carregar_fundo, carregar_imagem, texto_contorno


# ==========================================
# CORES
# ==========================================

AZUL = (70, 100, 220)
AMARELO = (255, 180, 0)
BRANCO = (255, 255, 255)
CINZA = (230, 230, 230)
PRETO = (0, 0, 0)
ESCURO = (30, 30, 30)


# ==========================================
# TELA LOGIN
# ==========================================


class GerenciadorTelas:
    def __init__(self, screen):

        self.screen = screen

        self.W = screen.get_width()
        self.H = screen.get_height()

        # Funcoes de escala
        self.sx = lambda v: int(v * self.W / 800)
        self.sy = lambda v: int(v * self.H / 600)
        self.sf = lambda v: max(8, int(v * min(self.W / 800, self.H / 600)))

        self.font = pygame.font.SysFont("arial", self.sf(28), bold=True)

        self.font_small = pygame.font.SysFont("arial", self.sf(18))

        # ==================================
        # BACKGROUNDS
        # ==================================

        self.bg_login = carregar_imagem("backgrounds", "Entrada.png", (self.W, self.H))

        self.bg_menu = carregar_imagem("backgrounds", "FundoMenu.png", (self.W, self.H))

        self._calcular_layout()

    def redimensionar(self, nova_largura, nova_altura):
        """Atualiza dimensoes quando a tela e redimensionada"""
        self.W = nova_largura
        self.H = nova_altura
        self.sx = lambda v: int(v * self.W / 800)
        self.sy = lambda v: int(v * self.H / 600)
        self.sf = lambda v: max(8, int(v * min(self.W / 800, self.H / 600)))

        self.font = pygame.font.SysFont("arial", self.sf(28), bold=True)
        self.font_small = pygame.font.SysFont("arial", self.sf(18))

        # Recarregar backgrounds
        self.bg_login = carregar_imagem("backgrounds", "Entrada.png", (self.W, self.H))
        self.bg_menu = carregar_imagem("backgrounds", "FundoMenu.png", (self.W, self.H))

        self._calcular_layout()

    def _calcular_layout(self):
        """Calcula e guarda os retangulos da caixa de login, dos inputs
        e do botao ENTRAR, para serem usados tanto no desenho quanto na
        deteccao de clique (handle_event)."""

        box_largura = self.sx(350)
        box_altura = self.sy(350)
        box_x = (self.W - box_largura) // 2
        box_y = (self.H - box_altura) // 2

        self.box_x = box_x
        self.box_y = box_y
        self.box_largura = box_largura
        self.box_altura = box_altura

        input_largura = self.sx(260)
        input_altura = self.sy(45)
        input_x = box_x + (box_largura - input_largura) // 2

        self.input_rm_rect = pygame.Rect(
            input_x, box_y + self.sy(93), input_largura, input_altura
        )
        self.input_senha_rect = pygame.Rect(
            input_x, box_y + self.sy(173), input_largura, input_altura
        )

        btn_largura = self.sx(150)
        btn_altura = self.sy(50)
        btn_x = box_x + (box_largura - btn_largura) // 2
        btn_y = box_y + box_altura - btn_altura - self.sy(30)

        self.btn_entrar_rect = pygame.Rect(btn_x, btn_y, btn_largura, btn_altura)

    # ======================================
    # DESENHAR LOGIN
    # ======================================

    def desenhar(self):

        screen = self.screen

        # ==================================
        # FUNDO
        # ==================================

        screen.blit(self.bg_login, (0, 0))

        # Dimensoes da caixa de login (proporcionais, ja calculadas)
        box_largura = self.box_largura
        box_altura = self.box_altura
        box_x = self.box_x
        box_y = self.box_y

        # ==================================
        # SOMBRA
        # ==================================

        pygame.draw.rect(
            screen,
            PRETO,
            (box_x + 5, box_y + 5, box_largura, box_altura),
            border_radius=20,
        )

        # ==================================
        # CAIXA LOGIN
        # ==================================

        pygame.draw.rect(
            screen, AZUL, (box_x, box_y, box_largura, box_altura), border_radius=20
        )

        # ==================================
        # TOPO LOGIN
        # ==================================

        topo_largura = self.sx(150)
        topo_altura = self.sy(40)
        topo_x = box_x + (box_largura - topo_largura) // 2
        topo_y = box_y - self.sy(20)

        pygame.draw.rect(
            screen,
            PRETO,
            (topo_x + 2, topo_y + 2, topo_largura, topo_altura),
            border_radius=15,
        )

        pygame.draw.rect(
            screen,
            AMARELO,
            (topo_x, topo_y, topo_largura, topo_altura),
            border_radius=15,
        )

        txt_login = self.font.render("LOGIN", True, BRANCO)

        screen.blit(
            txt_login,
            (topo_x + (topo_largura - txt_login.get_width()) // 2, topo_y + self.sy(8)),
        )

        # ==================================
        # LABELS
        # ==================================

        label_rm = self.font.render("RM:", True, BRANCO)
        screen.blit(label_rm, (box_x + self.sx(20), box_y + self.sy(60)))

        label_senha = self.font.render("SENHA:", True, BRANCO)
        screen.blit(label_senha, (box_x + self.sx(20), box_y + self.sy(140)))

        # ==================================
        # INPUTS
        # ==================================

        rm_rect = self.input_rm_rect
        senha_rect = self.input_senha_rect

        # Texto/valores atuais (existem apenas na subclasse TelaLogin,
        # entao usamos getattr para nao quebrar caso desenhar() seja
        # chamado direto pela classe base)
        texto_rm = getattr(self, "texto_rm", "")
        texto_senha = getattr(self, "texto_senha", "")
        campo_ativo = getattr(self, "campo_ativo", None)

        # Input RM
        pygame.draw.rect(
            screen,
            PRETO,
            (rm_rect.x + 3, rm_rect.y + 3, rm_rect.width, rm_rect.height),
            border_radius=20,
        )

        pygame.draw.rect(screen, CINZA, rm_rect, border_radius=20)

        # Destaca a borda quando o campo esta selecionado
        if campo_ativo == "rm":
            pygame.draw.rect(screen, AMARELO, rm_rect, 3, border_radius=20)

        if texto_rm:
            txt_rm = self.font_small.render(texto_rm, True, PRETO)
            screen.blit(
                txt_rm,
                (rm_rect.x + self.sx(15), rm_rect.centery - txt_rm.get_height() // 2),
            )

        # Input Senha
        pygame.draw.rect(
            screen,
            PRETO,
            (senha_rect.x + 3, senha_rect.y + 3, senha_rect.width, senha_rect.height),
            border_radius=20,
        )

        pygame.draw.rect(screen, CINZA, senha_rect, border_radius=20)

        if campo_ativo == "senha":
            pygame.draw.rect(screen, AMARELO, senha_rect, 3, border_radius=20)

        if texto_senha:
            txt_senha = self.font_small.render("*" * len(texto_senha), True, PRETO)
            screen.blit(
                txt_senha,
                (
                    senha_rect.x + self.sx(15),
                    senha_rect.centery - txt_senha.get_height() // 2,
                ),
            )

        # ==================================
        # BOTAO ENTRAR
        # ==================================

        btn_rect = self.btn_entrar_rect

        pygame.draw.rect(
            screen,
            PRETO,
            (btn_rect.x + 3, btn_rect.y + 3, btn_rect.width, btn_rect.height),
            border_radius=15,
        )

        pygame.draw.rect(screen, AMARELO, btn_rect, border_radius=15)

        txt_btn = self.font.render("ENTRAR", True, BRANCO)

        screen.blit(
            txt_btn,
            (btn_rect.centerx - txt_btn.get_width() // 2, btn_rect.y + self.sy(12)),
        )

        # Mensagem de feedback (ex: "preencha os campos")
        mensagem = getattr(self, "mensagem", "")
        if mensagem:
            msg_surf = self.font_small.render(mensagem, True, (255, 220, 220))
            screen.blit(
                msg_surf,
                (
                    box_x + (box_largura - msg_surf.get_width()) // 2,
                    box_y - self.sy(45),
                ),
            )

        # ==================================
        # TEXTO FINAL
        # ==================================

        txt_info = self.font_small.render("REGISTRO FUNCIONAL EM BREVE", True, BRANCO)

        screen.blit(
            txt_info,
            (
                box_x + (box_largura - txt_info.get_width()) // 2,
                box_y + box_altura - self.sy(15),
            ),
        )


# ==========================================
# TELA LOGIN COM BOTAO VOLTAR
# ==========================================


class TelaLogin(GerenciadorTelas):
    """
    Tela de REGISTRO DO NOME, exibida quando o jogador clica em JOGAR
    no menu. O nome digitado aqui é o que aparece no relatório em PDF
    das estatísticas.

    Visual igual ao do menu inicial: mesmo fundo (Entrada.png) com o véu
    azul no topo, logo "I.S.A", botões dourados com sombra azul-escura
    (classe Botao), ícones redondos de voltar e configurações, e um painel
    azul-escuro com borda dourada onde fica o campo de nome.

    Layout:
        - seta (voltar) no canto superior esquerdo
        - engrenagem (configurações) no canto superior direito, como no menu
        - botão ADMIN ao lado da engrenagem (abre a tela de senha do ADMIN)
        - logo I.S.A no topo
        - painel com "LOGIN", label "NOME:", campo de texto e botão JOGAR
    """

    DOURADO = (247, 181, 20)
    AZUL_ESCURO = (22, 28, 90)
    CLARO = (255, 245, 220)
    TXT_ESCURO = (35, 40, 60)
    TXT_PLACEHOLDER = (150, 145, 135)
    AMARELO_TITULO = (255, 220, 40)
    CONTORNO_TITULO = (20, 30, 110)
    COR_ERRO = (255, 120, 100)

    MAX_CARACTERES = 18

    def __init__(
        self,
        screen,
        callback_voltar=None,
        callback_entrar=None,
        callback_config=None,
        callback_admin=None,
    ):
        super().__init__(screen)

        self.callback_voltar = callback_voltar
        self.callback_entrar = callback_entrar
        self.callback_config = callback_config
        self.callback_admin = callback_admin

        self.texto_nome = ""
        self.campo_ativo = False
        self.mensagem = ""

        self._cache_txt = {}
        self._cache_veu = None

        self._ajustar_escala()
        self._montar_layout()

    # ======================================
    # ESCALA E LAYOUT
    # ======================================

    def _ajustar_escala(self):
        """
        Mesma regra do main.py: a ALTURA virtual é fixa em 600 e a largura
        varia conforme o monitor. Por isso nada aqui cresce com a largura
        (a escala antiga, W/800, esticava a interface em telas widescreen).
        """
        k = self.H / 600
        self.sx = lambda v: int(v * k)
        self.sy = lambda v: int(v * k)
        self.sf = lambda v: max(8, int(v * k))
        # Cobre a tela sem distorcer, igual ao fundo do menu
        self.bg_login = carregar_fundo("backgrounds", "Entrada.png", (self.W, self.H))

    def _fonte_pixel(self, tamanho):
        """Mesma fonte pixel do resto do jogo, com fallback monoespaçado."""
        try:
            return carregar_fonte("upheavtt.ttf", self.sf(tamanho))
        except (FileNotFoundError, pygame.error):
            return pygame.font.SysFont(
                "consolas,couriernew,monospace", self.sf(tamanho), bold=True
            )

    def _montar_layout(self):
        sx, sy = self.sx, self.sy
        W = self.W

        self.f_titulo = self._fonte_pixel(64)
        self.f_cabecalho = self._fonte_pixel(30)
        self.f_label = self._fonte_pixel(22)
        self.f_input = self._fonte_pixel(26)
        self.f_info = self._fonte_pixel(16)

        self._cache_txt.clear()
        self._img_logo = texto_contorno(
            self.f_titulo,
            "I.S.A",
            self.AMARELO_TITULO,
            self.CONTORNO_TITULO,
            espessura=4,
        )

        # Painel central
        pw, ph = sx(460), sy(330)
        self.painel_rect = pygame.Rect((W - pw) // 2, sy(165), pw, ph)
        self._img_painel = self._criar_painel(pw, ph)
        p = self.painel_rect

        # Campo de texto
        margem = sx(40)
        self.input_rect = pygame.Rect(
            p.x + margem, p.y + sy(105), pw - 2 * margem, sy(52)
        )
        self._img_input = {
            False: self._criar_campo(False),
            True: self._criar_campo(True),
        }

        # Botões: mesmos tamanhos e proporções do menu inicial
        bw, bh = max(180, sx(220)), max(50, sy(60))
        self.btn_jogar = Botao(
            "JOGAR",
            p.centerx - bw // 2,
            p.bottom - bh - sy(35),
            bw,
            bh,
            self._confirmar,
        )
        raio = max(25, sx(30))
        self.btn_voltar = BotaoVoltar(
            cx=sx(38), cy=sy(38), raio=raio, acao=self._voltar
        )
        # Engrenagem na mesma posição que tem no menu inicial
        self.btn_config = BotaoConfig(
            cx=W - sx(38), cy=sy(38), raio=raio, acao=self._abrir_config
        )
        aw, ah = sx(140), sy(50)
        self.btn_admin = Botao(
            "ADMIN",
            self.btn_config.rect.left - sx(14) - aw,
            sy(38) - ah // 2,
            aw,
            ah,
            self._admin,
        )

        self._botoes = [
            self.btn_jogar,
            self.btn_voltar,
            self.btn_config,
            self.btn_admin,
        ]

    def redimensionar(self, nova_largura, nova_altura):
        super().redimensionar(nova_largura, nova_altura)
        self._ajustar_escala()
        self._cache_veu = None
        self._montar_layout()

    # ======================================
    # IMAGENS EM CACHE (desenhadas em alta resolução e reduzidas, como os
    # botões do menu: bordas sem serrilhado)
    # ======================================

    def _criar_painel(self, w, h):
        return criar_painel(w, h, raio=self.sx(24), prof=self.sy(8))

    def _criar_campo(self, ativo):
        r = self.input_rect
        k = 4
        prof = self.sy(4)
        raio = max(8, r.height // 4)
        alta = pygame.Surface((r.width * k, (r.height + prof) * k), pygame.SRCALPHA)

        pygame.draw.rect(
            alta,
            (10, 14, 55),
            (0, prof * k, r.width * k, r.height * k),
            border_radius=raio * k,
        )
        corpo = pygame.Rect(0, 0, r.width * k, r.height * k)
        pygame.draw.rect(alta, self.CLARO, corpo, border_radius=raio * k)
        pygame.draw.rect(
            alta,
            self.DOURADO if ativo else self.AZUL_ESCURO,
            corpo,
            (4 if ativo else 3) * k,
            border_radius=raio * k,
        )
        return pygame.transform.smoothscale(alta, (r.width, r.height + prof))

    def _veu_topo(self, altura=230, alpha_max=150):
        """Degradê azul-escuro no topo (o mesmo do menu inicial)."""
        chave = (self.W, altura, alpha_max)
        if self._cache_veu is None or self._cache_veu[0] != chave:
            surf = pygame.Surface((self.W, altura), pygame.SRCALPHA)
            for y in range(altura):
                a = int(alpha_max * (1 - y / altura) ** 2)
                pygame.draw.line(surf, (10, 20, 80, a), (0, y), (self.W, y))
            self._cache_veu = (chave, surf)
        return self._cache_veu[1]

    def _txt(self, fonte, conteudo, cor, cor_contorno, espessura=2):
        """Texto com contorno (como os botões), renderizado uma vez só."""
        chave = (id(fonte), conteudo, cor, cor_contorno, espessura)
        surf = self._cache_txt.get(chave)
        if surf is None:
            if len(self._cache_txt) > 128:
                self._cache_txt.clear()
            surf = texto_contorno(
                fonte, conteudo, cor, cor_contorno, espessura=espessura, sombra=(0, 2)
            )
            self._cache_txt[chave] = surf
        return surf

    # ======================================
    # AÇÕES
    # ======================================

    def _voltar(self):
        pygame.key.stop_text_input()
        if self.callback_voltar:
            self.callback_voltar()

    def _abrir_config(self):
        if self.callback_config:
            self.callback_config()

    def _admin(self):
        if self.callback_admin:
            self.callback_admin()

    def _confirmar(self):
        """Valida o nome e dispara o callback que inicia a partida."""
        nome = self.texto_nome.strip()
        if not nome:
            self.mensagem = "DIGITE SEU NOME!"
            self.campo_ativo = True
            pygame.key.start_text_input()
            return
        self.mensagem = ""
        pygame.key.stop_text_input()
        if self.callback_entrar:
            self.callback_entrar(nome)

    def resetar(self):
        """Limpa o campo e já deixa pronto pra digitar (chamado ao abrir a tela)."""
        self.texto_nome = ""
        self.campo_ativo = True
        self.mensagem = ""
        pygame.key.start_text_input()

    # ======================================
    # EVENTOS
    # ======================================

    def handle_event(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for botao in self._botoes:
                if botao.rect.collidepoint(evento.pos):
                    botao.verificar_click(evento)
                    return
            if self.input_rect.collidepoint(evento.pos):
                self.campo_ativo = True
                pygame.key.start_text_input()
                return
            self.campo_ativo = False

        elif evento.type == pygame.TEXTINPUT:
            if self.campo_ativo and len(self.texto_nome) < self.MAX_CARACTERES:
                self.texto_nome = (self.texto_nome + evento.text)[: self.MAX_CARACTERES]
                self.mensagem = ""

        elif evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_BACKSPACE:
                self.texto_nome = self.texto_nome[:-1]
            elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirmar()

    # ======================================
    # DESENHO
    # ======================================

    def desenhar(self, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        screen = self.screen
        sx, sy = self.sx, self.sy
        p = self.painel_rect

        # Fundo, véu e logo: iguais aos do menu inicial
        screen.blit(self.bg_login, (0, 0))
        screen.blit(self._veu_topo(), (0, 0))
        screen.blit(
            self._img_logo, self._img_logo.get_rect(center=(self.W // 2, sy(95)))
        )

        # Painel
        screen.blit(self._img_painel, p.topleft)

        cabecalho = self._txt(
            self.f_cabecalho, "LOGIN", self.AMARELO_TITULO, self.CONTORNO_TITULO, 3
        )
        screen.blit(cabecalho, cabecalho.get_rect(center=(p.centerx, p.y + sy(42))))

        # Label + campo de texto
        r = self.input_rect
        label = self._txt(self.f_label, "NOME:", BRANCO, self.CONTORNO_TITULO, 2)
        screen.blit(label, (r.x + sx(4), r.y - label.get_height() - sy(6)))
        self._desenhar_campo()

        # Texto informativo / mensagem de erro (centralizado)
        y = r.bottom + sy(18)
        if self.mensagem:
            msg = self._txt(
                self.f_info, self.mensagem, self.COR_ERRO, self.CONTORNO_TITULO, 2
            )
            screen.blit(msg, msg.get_rect(midtop=(p.centerx, y)))
        else:
            for linha in ("ADICIONE SEU NOME", "PARA O REGISTRO"):
                surf = self._txt(self.f_info, linha, BRANCO, self.CONTORNO_TITULO, 2)
                screen.blit(surf, surf.get_rect(midtop=(p.centerx, y)))
                y += surf.get_height() + sy(2)

        # Botões (JOGAR, voltar, configurações, ADMIN)
        for botao in self._botoes:
            botao.desenhar(screen, mouse_pos)

    def _desenhar_campo(self):
        screen = self.screen
        r = self.input_rect
        screen.blit(self._img_input[bool(self.campo_ativo)], r.topleft)

        area = r.inflate(-self.sx(32), 0)
        if self.texto_nome:
            render = self.f_input.render(self.texto_nome, True, self.TXT_ESCURO)
        elif not self.campo_ativo:
            render = self.f_input.render("SEU NOME", True, self.TXT_PLACEHOLDER)
        else:
            render = None

        largura = render.get_width() if render else 0
        # Se o texto passar do campo, mostra o final (onde está o cursor)
        desloc = min(0, area.width - largura - self.sx(4))
        y_meio = r.centery

        screen.set_clip(area)
        if render:
            screen.blit(render, (area.x + desloc, y_meio - render.get_height() // 2))
        if self.campo_ativo and (pygame.time.get_ticks() // 500) % 2 == 0:
            cx = area.x + desloc + (largura if self.texto_nome else 0) + 2
            pygame.draw.rect(
                screen,
                self.TXT_ESCURO,
                (cx, y_meio - self.sy(13), max(2, self.sx(3)), self.sy(26)),
            )
        screen.set_clip(None)


# ==========================================
# SLIDER
# ==========================================


class ControleDeslizante:
    def __init__(self, x, y, larg, valor=0.5):
        self.retangulo = pygame.Rect(x, y, larg, 8)
        self.valor = valor
        self.controle_ret = pygame.Rect(x + int(valor * larg) - 4, y - 4, 8, 16)
        self.arrastando = False

    def desenhar(self, superficie):
        # Desenha a linha do slider
        for i in range(self.retangulo.width):
            pygame.draw.rect(
                superficie,
                CINZA,
                (self.retangulo.x + i, self.retangulo.y, 1, self.retangulo.height),
            )
        # Desenha o controle
        pygame.draw.rect(superficie, BRANCO, self.controle_ret)
        pygame.draw.rect(superficie, PRETO, self.controle_ret, 1)

    def atualizar(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN:
            if self.controle_ret.collidepoint(evento.pos):
                self.arrastando = True
            # Tambem permite clicar diretamente na linha do slider
            elif self.retangulo.collidepoint(evento.pos):
                x = max(
                    self.retangulo.x,
                    min(evento.pos[0], self.retangulo.x + self.retangulo.w),
                )
                self.controle_ret.x = x - self.controle_ret.width // 2
                self.valor = (x - self.retangulo.x) / self.retangulo.w
                self.arrastando = True

        elif evento.type == pygame.MOUSEBUTTONUP:
            self.arrastando = False

        elif evento.type == pygame.MOUSEMOTION and self.arrastando:
            x = max(
                self.retangulo.x,
                min(evento.pos[0], self.retangulo.x + self.retangulo.w),
            )
            self.controle_ret.x = x - self.controle_ret.width // 2
            self.valor = (x - self.retangulo.x) / self.retangulo.w


# ==========================================
# TELA CONFIGURACOES
# ==========================================


class TelaConfiguracoes:
    """
    Tela de configurações no mesmo estilo do menu inicial: fundo com véu
    azul no topo, painel azul-escuro com borda dourada, sliders e botões
    dourados. A interface para o main.py é a mesma de antes
    (handle_event, desenhar, redimensionar e os callbacks); desenhar() agora
    aceita `mouse_pos` (coordenada virtual) para o hover dos botões.
    """

    def __init__(
        self,
        screen,
        largura,
        altura,
        callback_voltar=None,
        callback_creditos=None,
        callback_toggle_fullscreen=None,
        callback_volume_musica=None,
        callback_volume_efeitos=None,
    ):

        self.screen = screen
        self.W = largura
        self.H = altura
        self.callback_voltar = callback_voltar
        self.callback_creditos = callback_creditos
        self.callback_toggle_fullscreen = callback_toggle_fullscreen
        self.callback_volume_musica = callback_volume_musica
        self.callback_volume_efeitos = callback_volume_efeitos

        # Configuracoes
        self.volume_musica = 0.7
        self.volume_efeitos = 0.7
        self.tela_cheia = False

        self.scanline = False
        self.pos_scanline = 0
        self.mensagem = ""
        self.mensagem_ate = 0  # get_ticks() em que o aviso some

        self._txt = CacheTexto()
        self._cache_veu = None

        self._ajustar_escala()
        self._montar_layout()

    # ======================================
    # ESCALA E LAYOUT
    # ======================================

    def _ajustar_escala(self):
        """
        Mesma regra do main.py: a ALTURA virtual é fixa em 600 e a largura
        varia conforme o monitor, então nada aqui cresce com a largura.
        """
        k = self.H / 600
        self.sx = lambda v: int(v * k)
        self.sy = lambda v: int(v * k)
        self.sf = lambda v: max(8, int(v * k))

    def _fonte(self, tamanho):
        try:
            return carregar_fonte("upheavtt.ttf", self.sf(tamanho))
        except Exception as e:
            print(f"Erro ao carregar fonte 'upheavtt.ttf': {e}")
            return pygame.font.SysFont("couriernew", self.sf(tamanho), bold=True)

    def _montar_layout(self):
        sx, sy = self.sx, self.sy
        W, H = self.W, self.H

        self.f_titulo = self._fonte(40)
        self.f_secao = self._fonte(22)
        self.f_texto = self._fonte(18)
        self.f_pequena = self._fonte(14)
        self._txt.limpar()
        self._cache_veu = None

        # Cobre a tela sem distorcer, igual ao fundo do menu
        self.fundo = carregar_fundo("backgrounds", "Entrada.png", (W, H))

        # Painel central
        pw, ph = sx(560), sy(470)
        self.painel_rect = pygame.Rect((W - pw) // 2, sy(85), pw, ph)
        self._img_painel = criar_painel(pw, ph, raio=sx(24), prof=sy(8))
        p = self.painel_rect

        self.x_esq = p.x + sx(44)
        self.x_dir = p.right - sx(44)

        # Posições verticais (centro de cada linha)
        self.y_audio = p.y + sy(34)
        self.y_musica = p.y + sy(80)
        self.y_efeitos = p.y + sy(126)
        self.y_sep1 = p.y + sy(160)
        self.y_video = p.y + sy(184)
        self.y_tela = p.y + sy(238)
        self.y_dica = p.y + sy(282)
        self.y_sep2 = p.y + sy(308)
        self.y_info = p.y + sy(332)

        # Sliders (mantêm o valor atual ao redimensionar)
        slider_x = p.x + sx(190)
        slider_larg = pw - sx(190) - sx(44) - sx(80)
        self.slider_musica = SliderMenu(
            slider_x,
            self.y_musica,
            slider_larg,
            self.volume_musica,
            altura=sy(14),
            botao=sy(26),
        )
        self.slider_efeitos = SliderMenu(
            slider_x,
            self.y_efeitos,
            slider_larg,
            self.volume_efeitos,
            altura=sy(14),
            botao=sy(26),
        )

        # Botões: mesmos tamanhos e proporções do menu inicial
        bw, bh = max(160, sx(200)), max(50, sy(50))
        bx, by = self.x_dir - bw, self.y_tela - bh // 2
        self.btn_tela_cheia = Botao("TELA CHEIA", bx, by, bw, bh, self._alternar_tela)
        self.btn_janela = Botao("JANELA", bx, by, bw, bh, self._alternar_tela)
        cw, ch = max(180, sx(220)), max(50, sy(56))
        self.btn_creditos = Botao(
            "CREDITOS",
            p.centerx - cw // 2,
            self.y_info + sy(28),
            cw,
            ch,
            self._abrir_creditos,
        )
        self.btn_voltar = BotaoVoltar(
            cx=sx(38), cy=sy(38), raio=max(25, sx(30)), acao=self._voltar
        )

    def redimensionar(self, nova_largura, nova_altura):
        """Atualiza dimensoes quando a tela e redimensionada"""
        self.W = nova_largura
        self.H = nova_altura
        self._ajustar_escala()
        self._montar_layout()

    # ======================================
    # AÇÕES
    # ======================================

    def _voltar(self):
        if self.callback_voltar:
            self.callback_voltar()

    def _abrir_creditos(self):
        if self.callback_creditos:
            self.callback_creditos()

    def _alternar_tela(self):
        if self.callback_toggle_fullscreen:
            self.callback_toggle_fullscreen()
            self.tela_cheia = not self.tela_cheia
            self.mensagem = "PRESSIONE F11 PARA ALTERNAR O MODO DE TELA"
            self.mensagem_ate = pygame.time.get_ticks() + 3000

    def _botoes(self):
        """Botões clicáveis agora (o de tela cheia troca de rótulo)."""
        return [
            self.btn_voltar,
            self.btn_janela if self.tela_cheia else self.btn_tela_cheia,
            self.btn_creditos,
        ]

    # ======================================
    # EVENTOS
    # ======================================

    def handle_event(self, evento):
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_s:
                self.scanline = not self.scanline

        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for botao in self._botoes():
                if botao.rect.collidepoint(evento.pos):
                    botao.verificar_click(evento)
                    return

        self.slider_musica.atualizar(evento)
        self.slider_efeitos.atualizar(evento)

        # Atualiza os valores
        self.volume_musica = self.slider_musica.valor
        self.volume_efeitos = self.slider_efeitos.valor

        if self.callback_volume_musica:
            self.callback_volume_musica(self.volume_musica)
        if self.callback_volume_efeitos:
            self.callback_volume_efeitos(self.volume_efeitos)

    # ======================================
    # DESENHO
    # ======================================

    def _veu_topo(self):
        if self._cache_veu is None or self._cache_veu.get_width() != self.W:
            self._cache_veu = criar_veu_topo(self.W)
        return self._cache_veu

    def _secao(self, nome, y):
        surf = self._txt(self.f_secao, nome, AMARELO_TITULO, CONTORNO_TITULO, 3)
        self.screen.blit(surf, surf.get_rect(center=(self.painel_rect.centerx, y)))

    def _linha_slider(self, rotulo, slider, valor, y, mouse_pos):
        tela = self.screen
        lab = self._txt(self.f_texto, rotulo, BRANCO, CONTORNO_TITULO, 2)
        tela.blit(lab, lab.get_rect(midleft=(self.x_esq, y)))
        slider.desenhar(tela, mouse_pos)
        pct = self._txt(
            self.f_texto, f"{int(valor * 100)}%", AMARELO_TITULO, CONTORNO_TITULO, 2
        )
        tela.blit(pct, pct.get_rect(midright=(self.x_dir, y)))

    def desenhar(self, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        tela = self.screen
        sx, sy = self.sx, self.sy
        p = self.painel_rect

        # Fundo e véu: iguais aos do menu inicial
        tela.blit(self.fundo, (0, 0))
        tela.blit(self._veu_topo(), (0, 0))
        titulo = self._txt(
            self.f_titulo, "CONFIGURACOES", AMARELO_TITULO, CONTORNO_TITULO, 4
        )
        tela.blit(titulo, titulo.get_rect(center=(self.W // 2, sy(45))))

        # Painel
        tela.blit(self._img_painel, p.topleft)

        # ===== AUDIO =====
        self._secao("AUDIO", self.y_audio)
        self._linha_slider(
            "MUSICA", self.slider_musica, self.volume_musica, self.y_musica, mouse_pos
        )
        self._linha_slider(
            "EFEITOS",
            self.slider_efeitos,
            self.volume_efeitos,
            self.y_efeitos,
            mouse_pos,
        )
        desenhar_separador(tela, p.x + sx(36), p.right - sx(36), self.y_sep1)

        # ===== VIDEO =====
        self._secao("VIDEO", self.y_video)
        lab = self._txt(self.f_texto, "MODO DE TELA", BRANCO, CONTORNO_TITULO, 2)
        tela.blit(lab, lab.get_rect(midleft=(self.x_esq, self.y_tela)))
        dica = self._txt(
            self.f_pequena,
            "F11 ALTERNA ENTRE JANELA E TELA CHEIA",
            (200, 210, 255),
            CONTORNO_TITULO,
            2,
        )
        tela.blit(dica, dica.get_rect(center=(p.centerx, self.y_dica)))
        desenhar_separador(tela, p.x + sx(36), p.right - sx(36), self.y_sep2)

        # ===== INFORMACOES =====
        self._secao("INFORMACOES", self.y_info)
        versao = self._txt(
            self.f_pequena,
            "I.S.A - PRÉ-ALPHA VERSION",
            (170, 180, 230),
            CONTORNO_TITULO,
            2,
        )
        tela.blit(versao, versao.get_rect(center=(p.centerx, p.bottom - sy(24))))

        # Botões por cima de tudo
        for botao in self._botoes():
            botao.desenhar(tela, mouse_pos)

        # Aviso temporário no rodapé
        if self.mensagem and pygame.time.get_ticks() < self.mensagem_ate:
            msg = self._txt(self.f_texto, self.mensagem, BRANCO, CONTORNO_TITULO, 2)
            caixa = msg.get_rect(center=(self.W // 2, self.H - sy(20)))
            fundo = pygame.Surface(
                (caixa.width + sx(28), caixa.height + sy(10)), pygame.SRCALPHA
            )
            pygame.draw.rect(
                fundo, (10, 14, 55, 215), fundo.get_rect(), border_radius=sy(10)
            )
            pygame.draw.rect(fundo, DOURADO, fundo.get_rect(), 2, border_radius=sy(10))
            tela.blit(fundo, fundo.get_rect(center=caixa.center))
            tela.blit(msg, caixa)

        # Efeito scanline
        if self.scanline:
            self.pos_scanline = (self.pos_scanline + 2) % self.H
            for i in range(0, self.H, 4):
                linha = (self.pos_scanline + i) % self.H
                pygame.draw.line(tela, (0, 0, 0, 50), (0, linha), (self.W, linha), 1)
