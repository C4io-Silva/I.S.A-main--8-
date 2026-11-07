"""
Tela de pergunta (quiz) — desenho e estado de layout.

Extraída do main.py porque tem uma FRONTEIRA DE ESTADO própria: scroll,
limite de scroll, retângulos das alternativas, área visível e alternativa
selecionada formavam cinco variáveis globais que só esta tela lia e escrevia.
Eram tocadas em sete pontos diferentes do main (desenho, roda do mouse,
clique, navegação por controle, reset ao responder, reset ao iniciar).

Agora são atributos de um objeto, e o main fala com ele por métodos. Não há
`import main` em lugar nenhum: o que vem de fora entra pelo construtor
(o conversor de escala) ou por parâmetro (a superfície, a pergunta, se o
foco está no controle).
"""

from functools import lru_cache

import pygame

from src.nucleo import constants
from src.nucleo.utils import carregar_fonte, carregar_fonte_typewriter


@lru_cache(maxsize=256)
def _quebrar_texto(texto, tamanho_fonte, larg_max):
    """
    Quebra o texto em linhas que cabem em `larg_max`.

    Memoizada porque a tela de quiz redesenha tudo a cada frame, e a quebra
    chama fonte.size() uma vez por PALAVRA: com a pergunta e as cinco
    alternativas, são centenas de medições de texto por quadro para produzir
    sempre o mesmo resultado — a pergunta não muda enquanto está na tela.
    Medido em 3,4 ms por frame antes do cache.

    A chave é (texto, tamanho da fonte, largura): tudo que pode mudar o
    resultado. Por isso a fonte entra como TAMANHO e não como objeto —
    carregar_fonte_typewriter já é cacheada, e assim a chave continua hashável e estável
    entre trocas de resolução.
    """
    # Tem que ser a MESMA fonte usada no desenho, senão a quebra mede uma
    # largura e o render ocupa outra.
    fonte = carregar_fonte_typewriter(tamanho_fonte)
    palavras = texto.split()
    linhas = []
    linha = ""
    for p in palavras:
        teste = linha + " " + p if linha else p
        if fonte.size(teste)[0] <= larg_max:
            linha = teste
        else:
            if linha:
                linhas.append(linha)
            linha = p
    if linha:
        linhas.append(linha)
    return tuple(linhas) if linhas else (texto[:60],)


class TelaQuiz:
    """
    Estado de layout da tela de pergunta.

    `sf` (conversor de escala) e `mouse_virtual` (posição do cursor no espaço
    virtual 800x600) são recebidos por injeção. É o que permite esta tela não
    conhecer o sistema de janela do jogo — e não precisar de `import main`.
    """

    def __init__(self, sf, mouse_virtual):
        self.sf = sf
        self.mouse_virtual = mouse_virtual
        self.scroll = 0            # posição atual do scroll
        self.max_scroll = 0        # limite, recalculado a cada desenho
        self.alt_rects = []        # [(letra, Rect)] das alternativas do frame
        self.conteudo_rect = None  # área visível, para validar cliques
        self.selecao = 0           # alternativa destacada no controle

    # ── estado ──────────────────────────────────────────────────────────────
    def reiniciar(self):
        """Pergunta nova: volta ao topo e à primeira alternativa."""
        self.scroll = 0
        self.selecao = 0

    def rolar(self, delta):
        """Move o scroll respeitando os limites calculados no último desenho."""
        self.scroll = max(0, min(self.scroll + delta, self.max_scroll))

    def alternativa_em(self, pos):
        """A letra da alternativa sob `pos`, ou None. Só vale dentro da área visível."""
        if not self.conteudo_rect or not self.conteudo_rect.collidepoint(pos):
            return None
        for letra, rect in self.alt_rects:
            if rect.collidepoint(pos):
                return letra
        return None

    def navegar(self, passo):
        """
        Move a seleção do controle e rola para deixá-la visível.

        Usa os retângulos do último frame desenhado — é a única informação de
        posição que existe, e ela está sempre um frame atrás, o que na prática
        não se percebe.
        """
        if not self.alt_rects:
            return
        self.selecao = (self.selecao + passo) % len(self.alt_rects)
        if not self.conteudo_rect:
            return
        _, alvo = self.alt_rects[self.selecao]
        if alvo.bottom > self.conteudo_rect.bottom:
            self.rolar(alvo.bottom - self.conteudo_rect.bottom)
        elif alvo.top < self.conteudo_rect.top:
            self.rolar(-(self.conteudo_rect.top - alvo.top))

    def letra_selecionada(self):
        """A letra destacada agora, ou None se não há alternativas desenhadas."""
        if not self.alt_rects:
            return None
        return self.alt_rects[self.selecao][0]

    # ── desenho ─────────────────────────────────────────────────────────────
    def desenhar(self, screen, pergunta, pontuacao, indice, total,
                 mensagem="", tempo_msg=0, foco_no_controle=False,
                 segundos_restantes=None):
        """Desenha a tela de pergunta e atualiza o estado de layout do objeto."""
        sf = self.sf

        W = constants.SCREEN_WIDTH
        H = constants.SCREEN_HEIGHT

        # Cores
        CORES = {
            "bg": (20, 20, 40),
            "box": (45, 45, 65),
            "box_alt": (55, 55, 75),
            "texto": (255, 255, 255),
            "titulo": (241, 187, 52),
            "destaque": (100, 200, 255),
            "verde": (76, 175, 80),
            "vermelho": (244, 67, 54),
            "cinza": (100, 100, 120),
        }

        # Fundo com gradiente suave
        for i in range(H):
            cor = (20 + i // 30, 20 + i // 30, 40 + i // 20)
            pygame.draw.line(screen, cor, (0, i), (W, i))

        # Caixa principal
        box_w = int(W * 0.82)
        box_h = int(H * 0.82)
        box_x = (W - box_w) // 2
        box_y = (H - box_h) // 2
        pygame.draw.rect(
            screen, CORES["box"], (box_x, box_y, box_w, box_h), border_radius=20
        )
        pygame.draw.rect(
            screen, CORES["titulo"], (box_x, box_y, box_w, box_h), width=3, border_radius=20
        )

        # Barra de progresso
        prog_w = box_w - 50
        prog_h = 12
        prog_x = box_x + 25
        prog_y = box_y + 50
        proporcao = indice / total if total > 0 else 0
        pygame.draw.rect(
            screen, CORES["cinza"], (prog_x, prog_y, prog_w, prog_h), border_radius=6
        )
        pygame.draw.rect(
            screen,
            CORES["verde"],
            (prog_x, prog_y, int(prog_w * proporcao), prog_h),
            border_radius=6,
        )

        # Título e pontuação
        fonte_tit = carregar_fonte("upheavtt.ttf", sf(24))
        tit = fonte_tit.render(" PERGUNTA", True, CORES["titulo"])
        screen.blit(tit, (box_x + 25, box_y + 20))
        fonte_score = carregar_fonte("upheavtt.ttf", sf(20))
        score_txt = fonte_score.render(f" {pontuacao}/{total}", True, CORES["titulo"])
        screen.blit(score_txt, (box_x + box_w - score_txt.get_width() - 25, box_y + 22))

        # Disciplina e dificuldade
        disc = pergunta.get("disciplina", "Geral")[:25]
        diff = pergunta.get("dificuldade", pergunta.get("nivel", "Médio"))[:15]
        fonte_info = carregar_fonte("upheavtt.ttf", sf(16))
        info = fonte_info.render(f"{disc}  |  {diff}", True, CORES["destaque"])
        screen.blit(info, (box_x + 28, prog_y + 25))

        # Linha separadora
        separador_y = prog_y + 55
        pygame.draw.line(
            screen,
            CORES["titulo"],
            (box_x + 25, separador_y),
            (box_x + box_w - 25, separador_y),
            2,
        )

        # ── Área de conteúdo rolável (pergunta + alternativas) ──────────────────
        conteudo_top = separador_y + 15
        conteudo_bottom = box_y + box_h - 50  # deixa espaço pra instrução embaixo
        conteudo_rect = pygame.Rect(
            box_x, conteudo_top, box_w, conteudo_bottom - conteudo_top
        )
        self.conteudo_rect = (
            conteudo_rect  # guarda pra checar clique dentro da área visível
        )

        # Pergunta (com quebra de linha) — sem corte agressivo, o scroll cuida do resto
        texto_pergunta = pergunta.get("pergunta", "Pergunta não disponível")[:1000]
        fonte_perg = carregar_fonte_typewriter(sf(16))

        larg_max_perg = box_w - 60
        linhas_perg = _quebrar_texto(texto_pergunta, sf(16), larg_max_perg)

        # Alternativas
        opcoes = []
        chaves = ["opcao_a", "opcao_b", "opcao_c", "opcao_d", "opcao_e"]
        chaves_acento = ["opçao_a", "opçao_b", "opçao_c", "opçao_d", "opçao_e"]
        letras = ["A", "B", "C", "D", "E"]
        for i, chave in enumerate(chaves):
            texto = pergunta.get(chave, "")
            if not texto and i < len(chaves_acento):
                texto = pergunta.get(chaves_acento[i], "")
            if texto and len(str(texto)) > 1:
                opcoes.append((letras[i], str(texto)[:220]))
        if not opcoes:
            opcoes = [
                ("A", "Alternativa A"),
                ("B", "Alternativa B"),
                ("C", "Alternativa C"),
            ]

        # Fonte das alternativas (definida aqui pra poder medir a quebra de linha)
        fonte_alt = carregar_fonte_typewriter(sf(15))

        # Quebra o texto de cada alternativa, respeitando a largura da caixinha
        # (largura da caixa menos o espaço da "bolinha" da letra e a margem direita)
        larg_max_alt = box_w - 50 - 55 - 20
        PAD_ALT_TOPO = 10
        PAD_ALT_BASE = 10
        ALT_LINHA_H = 20
        ALT_MIN_H = 42
        ALT_ESPACAMENTO = 10  # espaço vertical entre uma caixinha e outra

        opcoes_processadas = []  # (letra, [linhas], altura_da_caixinha)
        for letra, texto in opcoes[:5]:
            linhas_opcao = _quebrar_texto(texto, sf(15), larg_max_alt)[:4]  # até 4 linhas
            altura_opcao = max(
                ALT_MIN_H, PAD_ALT_TOPO + len(linhas_opcao) * ALT_LINHA_H + PAD_ALT_BASE
            )
            opcoes_processadas.append((letra, linhas_opcao, altura_opcao))

        # Altura total do conteúdo (pergunta + espaço + alternativas)
        altura_pergunta = len(linhas_perg) * 26 + 20
        altura_alternativas = sum(h for _, _, h in opcoes_processadas) + ALT_ESPACAMENTO * max(
            0, len(opcoes_processadas) - 1
        )
        altura_total = altura_pergunta + altura_alternativas

        # Calcula scroll máximo e aplica clamp na global
        self.max_scroll = max(0, altura_total - conteudo_rect.height)
        self.scroll = max(0, min(self.scroll, self.max_scroll))

        # Recorta a tela pra não desenhar fora da caixa
        clip_anterior = screen.get_clip()
        screen.set_clip(conteudo_rect)

        y_perg = conteudo_top - self.scroll
        for i, linha in enumerate(linhas_perg):
            render = fonte_perg.render(linha, True, CORES["texto"])
            screen.blit(render, (box_x + 30, y_perg + i * 26))

        y_alt = y_perg + altura_pergunta
        mouse_pos = self.mouse_virtual()  # coordenada no espaço virtual 800x600

        # Limpa a lista de retângulos clicáveis e recalcula a cada frame
        self.alt_rects = []

        # Com o controle, o destaque não segue o mouse: segue a alternativa
        # selecionada. Clamp aqui porque o número de alternativas muda de pergunta
        # pra pergunta (umas têm 4, outras 5).
        self.selecao = max(0, min(self.selecao, len(opcoes_processadas) - 1))

        y_cursor = y_alt
        for i, (letra, linhas_opcao, altura_opcao) in enumerate(opcoes_processadas):
            alt_rect = pygame.Rect(box_x + 25, y_cursor, box_w - 50, altura_opcao)
            # Guarda (letra minúscula, rect) pra detecção de clique no loop de eventos
            self.alt_rects.append((letra.lower(), alt_rect))

            if foco_no_controle:
                hover = i == self.selecao
            else:
                hover = alt_rect.collidepoint(mouse_pos) and conteudo_rect.collidepoint(
                    mouse_pos
                )
            cor_fundo = CORES["box_alt"] if hover else (55, 55, 75)
            pygame.draw.rect(screen, cor_fundo, alt_rect, border_radius=12)
            cor_borda = CORES["verde"] if hover else CORES["destaque"]
            largura_borda = 2 if hover else 1
            pygame.draw.rect(
                screen, cor_borda, alt_rect, width=largura_borda, border_radius=12
            )
            # Letra
            letra_rect = pygame.Rect(alt_rect.x + 12, alt_rect.y + 8, 28, 26)
            pygame.draw.rect(screen, CORES["titulo"], letra_rect, border_radius=6)
            letra_surf = fonte_alt.render(letra, True, CORES["bg"])
            screen.blit(letra_surf, (letra_rect.x + 8, letra_rect.y + 4))
            # Texto (uma ou mais linhas, dentro da largura da caixinha)
            for li, linha_txt in enumerate(linhas_opcao):
                texto_render = fonte_alt.render(linha_txt, True, CORES["texto"])
                screen.blit(
                    texto_render,
                    (alt_rect.x + 55, alt_rect.y + PAD_ALT_TOPO + li * ALT_LINHA_H),
                )

            y_cursor += altura_opcao + ALT_ESPACAMENTO

        # Restaura o clip
        screen.set_clip(clip_anterior)

        # Barra de scroll lateral, só aparece se precisar rolar
        if self.max_scroll > 0:
            barra_x = conteudo_rect.right - 6
            barra_altura = max(
                20, conteudo_rect.height * conteudo_rect.height / altura_total
            )
            proporcao_scroll = self.scroll / self.max_scroll
            barra_y = conteudo_rect.top + proporcao_scroll * (
                conteudo_rect.height - barra_altura
            )
            pygame.draw.rect(
                screen,
                CORES["cinza"],
                (barra_x, conteudo_rect.top, 5, conteudo_rect.height),
                border_radius=3,
            )
            pygame.draw.rect(
                screen,
                CORES["destaque"],
                (barra_x, barra_y, 5, barra_altura),
                border_radius=3,
            )

        # Instrução (muda conforme o jogador esteja de controle ou teclado/mouse)
        fonte_inst = carregar_fonte("upheavtt.ttf", sf(14))
        if segundos_restantes is not None:
            # Pergunta do minério do boss: tem tempo e não dá para fugir.
            texto_inst = (f"MINERIO DO BOSS - responda em {segundos_restantes}s  |  "
                          + ("A = Responder" if foco_no_controle else "A-E / 1-5 ou clique"))
        elif foco_no_controle:
            texto_inst = "Direcional = Escolher   |   A = Responder   |   B = Voltar"
        else:
            texto_inst = (
                "Clique ou use A B C D E / 1 2 3 4 5 = Responder   |   ESC = Voltar"
            )
        cor_inst = CORES["destaque"]
        if segundos_restantes is not None and segundos_restantes <= 5:
            cor_inst = CORES["vermelho"]
        instrucao = fonte_inst.render(texto_inst, True, cor_inst)
        if instrucao.get_width() > box_w - 20:   # nunca vaza da caixa
            escala = (box_w - 20) / instrucao.get_width()
            instrucao = pygame.transform.smoothscale(
                instrucao, (box_w - 20, max(1, int(instrucao.get_height() * escala))))
        screen.blit(instrucao, instrucao.get_rect(center=(W // 2, box_y + box_h - 25)))

        # Mensagem de feedback
        if mensagem and tempo_msg > 0:
            fonte_msg = carregar_fonte("upheavtt.ttf", sf(28))
            cor_msg = CORES["verde"] if "ACERTOU" in mensagem else CORES["vermelho"]
            msg_surf = fonte_msg.render(mensagem, True, cor_msg)
            msg_bg = pygame.Surface(
                (msg_surf.get_width() + 40, msg_surf.get_height() + 20), pygame.SRCALPHA
            )
            msg_bg.fill((0, 0, 0, 200))
            msg_x = (W - msg_bg.get_width()) // 2
            msg_y = H - 90
            screen.blit(msg_bg, (msg_x, msg_y))
            screen.blit(msg_surf, (msg_x + 20, msg_y + 10))

        return mouse_pos