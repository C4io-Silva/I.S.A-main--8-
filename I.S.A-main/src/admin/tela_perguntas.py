"""
Painel ADMIN das perguntas, no mesmo estilo do jogo (fundo com véu azul,
painel azul-escuro com borda dourada, botões dourados, fonte pixel).

Três modos, na mesma tela:
    lista      busca + lista rolável + ADICIONAR / EDITAR / EXCLUIR
    editor     formulário de uma pergunta (nova ou existente)
    confirmar  "excluir esta pergunta?" (SIM / NAO)

Toda alteração é gravada na hora nos CSVs (ver banco.py).
"""

import pygame

from src.admin.banco import NIVEIS, BancoAdmin, ErroSalvar, pergunta_vazia
from src.admin.campos import Campo, cortar, quebrar
from src.admin.tela_senha import fonte_pixel
from src.interface.buttons import Botao
from src.nucleo.estilo import (
    AMARELO_TITULO,
    AZUL_ESCURO,
    AZUL_LINHA,
    BRANCO,
    CONTORNO_TITULO,
    COR_ACERTO,
    COR_ERRO,
    DOURADO,
    BotaoVoltar,
    CacheTexto,
    criar_painel,
    criar_veu_topo,
)
from src.nucleo.utils import carregar_fonte_typewriter
from src.quiz.dados_csv import LETRAS, normalizar

TXT_ESCURO = (35, 40, 60)
TXT_CLARO = (235, 240, 255)
TXT_SUAVE = (170, 185, 240)
LINHA_A = (16, 22, 80)
LINHA_B = (22, 30, 98)
LINHA_HOVER = (44, 60, 150)
COR_NIVEL = {"facil": COR_ACERTO, "medio": AMARELO_TITULO, "dificil": COR_ERRO}
ROTULO_NIVEL = {"facil": "FACIL", "medio": "MEDIO", "dificil": "DIFICIL"}

MAX_DISCIPLINA = 30
MAX_ENUNCIADO = 500
MAX_ALTERNATIVA = 160
DUPLO_CLIQUE_MS = 400


class TelaPerguntas:
    def __init__(self, screen, fundo, callback_voltar=None, banco=None):
        self.screen = screen
        self.W, self.H = screen.get_width(), screen.get_height()
        self.fundo = fundo
        self.callback_voltar = callback_voltar
        self.banco = banco or BancoAdmin()

        self.modo = "lista"
        self.sel = None                # pergunta selecionada (a própria dict)
        self.filtrados = []
        self.numeros = {}              # id(pergunta) -> posição no banco (1, 2, ...)
        self.scroll = 0
        self.alvo_edicao = None        # pergunta sendo editada; None = nova
        self.erro = ""                 # aviso dentro do editor
        self.mensagem = ""
        self.mensagem_ate = 0
        self._arrastando = None        # deslocamento do clique dentro da barra
        self._ultimo_clique = (0, None)
        self._cortes = {}
        self._txt = CacheTexto()
        self._veu = criar_veu_topo(self.W)

        self._montar_layout()

    # ══════════════════════════════════════════════════════════════════════
    # LAYOUT
    # ══════════════════════════════════════════════════════════════════════
    def _montar_layout(self):
        k = self.H / 600
        sx = sy = lambda v: int(v * k)
        self.sx, self.sy = sx, sy

        self.f_titulo = fonte_pixel(sy(36))
        self.f_label = fonte_pixel(sy(15))
        self.f_pequena = fonte_pixel(sy(14))
        self.f_aviso = fonte_pixel(sy(16))
        self.f_campo = carregar_fonte_typewriter(sy(15), bold=False)
        self.f_lista = carregar_fonte_typewriter(sy(14), bold=False)
        self.f_lista_neg = carregar_fonte_typewriter(sy(14), bold=True)

        pw, ph = min(self.W - sx(60), sx(900)), sy(484)
        self.painel_rect = pygame.Rect((self.W - pw) // 2, sy(72), pw, ph)
        self._img_painel = criar_painel(pw, ph, raio=sx(24), prof=sy(8))
        p = self.painel_rect
        pad = sx(30)
        x0, iw = p.x + pad, pw - 2 * pad
        self.x0, self.iw = x0, iw

        # ── lista ─────────────────────────────────────────────────────────
        rot = sx(96)
        self.busca = Campo(
            (x0 + rot, p.y + sy(12), iw - rot - sx(190), sy(34)),
            60, self.f_campo, placeholder="DIGITE PARA BUSCAR")
        self.lista_area = pygame.Rect(x0, p.y + sy(60), iw, sy(340))
        self.linha_h = sy(34)
        self.visiveis = self.lista_area.height // self.linha_h
        self.barra = pygame.Rect(self.lista_area.right - sx(14), self.lista_area.y,
                                 sx(14), self.lista_area.height)
        self.linhas_largura = self.barra.x - sx(8) - x0

        bw, bh, gap = sx(190), sy(52), sx(20)
        total = 3 * bw + 2 * gap
        by = p.y + sy(412)
        bx = p.centerx - total // 2
        self.btn_adicionar = Botao("ADICIONAR", bx, by, bw, bh, self._novo)
        self.btn_editar = Botao("EDITAR", bx + bw + gap, by, bw, bh, self._editar)
        self.btn_excluir = Botao("EXCLUIR", bx + 2 * (bw + gap), by, bw, bh,
                                 self._pedir_exclusao)

        # ── editor ────────────────────────────────────────────────────────
        dw = int(iw * 0.46)
        self.campo_disc = Campo((x0, p.y + sy(30), dw, sy(32)), MAX_DISCIPLINA,
                                self.f_campo, placeholder="EX.: MATEMATICA")
        nx = x0 + dw + sx(24)
        gap_n = sx(6)
        seg_w = (x0 + iw - nx - 2 * gap_n) // 3
        self.seg_nivel = {
            chave: pygame.Rect(nx + i * (seg_w + gap_n), p.y + sy(30), seg_w, sy(32))
            for i, (chave, _) in enumerate(NIVEIS)
        }
        self.pos_label_nivel = (nx, p.y + sy(12))
        self.campo_perg = Campo((x0, p.y + sy(88), iw, sy(78)), MAX_ENUNCIADO,
                                self.f_campo, multilinha=True,
                                placeholder="ESCREVA A PERGUNTA")
        self.badges, self.campo_alt = {}, {}
        raio = sy(16)
        for i, letra in enumerate(LETRAS):
            y = p.y + sy(190) + i * sy(37)
            self.badges[letra] = pygame.Rect(x0, y, 2 * raio, 2 * raio)
            self.campo_alt[letra] = Campo(
                (x0 + sy(42), y, iw - sy(42), sy(32)), MAX_ALTERNATIVA, self.f_campo,
                placeholder=f"ALTERNATIVA {letra.upper()}"
                + (" (OPCIONAL)" if letra in "cde" else ""))
        self.campos_foco = [self.campo_disc, self.campo_perg,
                            *(self.campo_alt[l] for l in LETRAS)]
        self.foco = 1
        self.dados_edicao = pergunta_vazia()

        ew, eh = sx(210), sy(52)
        ey = p.y + sy(408)
        self.btn_salvar = Botao("SALVAR", p.centerx - ew - sx(12), ey, ew, eh,
                                self._salvar_editor)
        self.btn_cancelar = Botao("CANCELAR", p.centerx + sx(12), ey, ew, eh,
                                  self._cancelar_editor)

        # ── confirmação de exclusão ───────────────────────────────────────
        cw, ch = sx(520), sy(250)
        self.conf_rect = pygame.Rect((self.W - cw) // 2, (self.H - ch) // 2, cw, ch)
        self._img_conf = criar_painel(cw, ch, raio=sx(24), prof=sy(8))
        c = self.conf_rect
        sw = sx(210)
        self.btn_sim = Botao("SIM, EXCLUIR", c.centerx - sw - sx(10), c.bottom - sy(76),
                             sw, sy(52), self._confirmar_exclusao)
        self.btn_nao = Botao("NAO", c.centerx + sx(10), c.bottom - sy(76), sw, sy(52),
                             self._cancelar_exclusao)
        self._veu_modal = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._veu_modal.fill((0, 0, 20, 170))

        self.btn_voltar = BotaoVoltar(cx=sx(38), cy=sy(38), raio=max(25, sx(30)),
                                      acao=self.tecla_voltar)

    # ══════════════════════════════════════════════════════════════════════
    # DADOS / LISTA
    # ══════════════════════════════════════════════════════════════════════
    def recarregar(self):
        """Relê os CSVs e volta para a lista (chamado ao entrar no painel)."""
        self.banco.carregar()
        self.modo = "lista"
        self.busca.definir("")
        self.sel = None
        self.scroll = 0
        self._filtrar()
        if self.banco.problemas:
            n = self.banco.problemas
            self._aviso(f"{n} LINHA(S) INVALIDA(S) IGNORADA(S) - BACKUP AO SALVAR", 5000)
        pygame.key.start_text_input()

    def _aviso(self, texto, ms=2500):
        self.mensagem = texto
        self.mensagem_ate = pygame.time.get_ticks() + ms

    def _filtrar(self):
        self.numeros = {id(p): i + 1 for i, p in enumerate(self.banco.perguntas)}
        termo = normalizar(self.busca.texto)
        if termo:
            self.filtrados = [
                p for p in self.banco.perguntas
                if termo in normalizar(f"{p['pergunta']} {p['disciplina']} {p['dificuldade']}")
            ]
        else:
            self.filtrados = list(self.banco.perguntas)
        if self.sel is None or not any(p is self.sel for p in self.filtrados):
            self.sel = self.filtrados[0] if self.filtrados else None
        self.scroll = max(0, min(self.scroll, self._max_scroll()))
        self._garantir_visivel()

    def _max_scroll(self):
        return max(0, len(self.filtrados) - self.visiveis)

    def _indice_sel(self):
        for i, p in enumerate(self.filtrados):
            if p is self.sel:
                return i
        return -1

    def _garantir_visivel(self):
        i = self._indice_sel()
        if i < 0:
            return
        if i < self.scroll:
            self.scroll = i
        elif i >= self.scroll + self.visiveis:
            self.scroll = i - self.visiveis + 1

    def _mover(self, delta):
        if not self.filtrados:
            return
        i = max(0, min(len(self.filtrados) - 1, self._indice_sel() + delta))
        self.sel = self.filtrados[i]
        self._garantir_visivel()

    def _rolar(self, delta):
        self.scroll = max(0, min(self._max_scroll(), self.scroll + delta))

    # ══════════════════════════════════════════════════════════════════════
    # AÇÕES
    # ══════════════════════════════════════════════════════════════════════
    def tecla_voltar(self):
        """ESC / seta / botão B do controle: sai do nível atual da tela."""
        if self.modo == "editor":
            self._cancelar_editor()
        elif self.modo == "confirmar":
            self._cancelar_exclusao()
        elif self.busca.texto:
            self.busca.definir("")
            self._filtrar()
        elif self.callback_voltar:
            self.callback_voltar()

    def _novo(self):
        self._abrir_editor(None)

    def _editar(self):
        if self.sel is not None:
            self._abrir_editor(self.sel)

    def _abrir_editor(self, pergunta):
        self.alvo_edicao = pergunta
        dados = dict(pergunta) if pergunta else pergunta_vazia()
        self.dados_edicao = dados
        self.campo_disc.definir("" if pergunta is None else dados["disciplina"])
        self.campo_perg.definir(dados["pergunta"])
        for letra in LETRAS:
            self.campo_alt[letra].definir(dados[f"opcao_{letra}"])
        self.foco = 1
        self.erro = ""
        self.modo = "editor"

    def _cancelar_editor(self):
        self.modo = "lista"

    def _coletar(self):
        d = {"disciplina": self.campo_disc.texto,
             "dificuldade_chave": self.dados_edicao.get("dificuldade_chave", "medio"),
             "pergunta": self.campo_perg.texto,
             "resposta": self.dados_edicao.get("resposta", "")}
        for letra in LETRAS:
            d[f"opcao_{letra}"] = self.campo_alt[letra].texto
        return d

    def _salvar_editor(self):
        dados = self._coletar()
        try:
            if self.alvo_edicao is None:
                nova = self.banco.adicionar(dados)
            else:
                nova = self.banco.editar(self.alvo_edicao, dados)
        except ValueError as e:
            self.erro = str(e)
            return
        except ErroSalvar:
            self.erro = "NAO FOI POSSIVEL SALVAR (CSV ABERTO NO EXCEL?)"
            return
        self.modo = "lista"
        self.sel = nova
        self._filtrar()
        if self.sel is not nova:        # a busca escondia a pergunta: limpa
            self.busca.definir("")
            self.sel = nova
            self._filtrar()
        self._garantir_visivel()
        self._aviso("PERGUNTA SALVA!")

    def _pedir_exclusao(self):
        if self.sel is not None:
            self.modo = "confirmar"

    def _cancelar_exclusao(self):
        self.modo = "lista"

    def _confirmar_exclusao(self):
        if self.sel is None:
            self.modo = "lista"
            return
        i = self._indice_sel()
        try:
            self.banco.excluir(self.sel)
        except ErroSalvar:
            self.modo = "lista"
            self._aviso("NAO FOI POSSIVEL SALVAR (CSV ABERTO NO EXCEL?)", 4000)
            return
        self.modo = "lista"
        self.sel = None
        self._filtrar()
        if self.filtrados:
            self.sel = self.filtrados[min(i, len(self.filtrados) - 1)]
            self._garantir_visivel()
        self._aviso("PERGUNTA EXCLUIDA!")

    # ══════════════════════════════════════════════════════════════════════
    # EVENTOS
    # ══════════════════════════════════════════════════════════════════════
    def handle_event(self, ev):
        if self.modo == "confirmar":
            self._evento_confirmar(ev)
        elif self.modo == "editor":
            self._evento_editor(ev)
        else:
            self._evento_lista(ev)

    def _clique_botoes(self, ev, botoes):
        """Aciona o botão sob o clique. True se algum foi clicado."""
        for botao in botoes:
            if botao.rect.collidepoint(ev.pos):
                botao.verificar_click(ev)
                return True
        return False

    # ── confirmar ────────────────────────────────────────────────────────
    def _evento_confirmar(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self._clique_botoes(ev, (self.btn_sim, self.btn_nao))
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._cancelar_exclusao()

    # ── lista ────────────────────────────────────────────────────────────
    def _evento_lista(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self._clique_botoes(ev, (self.btn_voltar, self.btn_adicionar,
                                        self.btn_editar, self.btn_excluir)):
                return
            self._clique_lista(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self._arrastando = None
        elif ev.type == pygame.MOUSEMOTION and self._arrastando is not None:
            self._arrastar_barra(ev.pos[1])
        elif ev.type == pygame.MOUSEWHEEL:
            self._rolar(-ev.y * 2)
        elif ev.type == pygame.TEXTINPUT:
            self.busca.inserir(ev.text)
            self._filtrar()
        elif ev.type == pygame.KEYDOWN:
            self._tecla_lista(ev)

    def _tecla_lista(self, ev):
        k = ev.key
        if k == pygame.K_ESCAPE:
            self.tecla_voltar()
        elif k == pygame.K_UP:
            self._mover(-1)
        elif k == pygame.K_DOWN:
            self._mover(1)
        elif k == pygame.K_PAGEUP:
            self._mover(-self.visiveis)
        elif k == pygame.K_PAGEDOWN:
            self._mover(self.visiveis)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._editar()
        elif k == pygame.K_v and ev.mod & pygame.KMOD_CTRL:
            self.busca.colar()
            self._filtrar()
        elif self.busca.tecla(ev):
            self._filtrar()

    def _thumb(self):
        """Retângulo do botão da barra de rolagem (None se não há o que rolar)."""
        total = len(self.filtrados)
        if total <= self.visiveis:
            return None
        h = max(self.sy(30), self.barra.height * self.visiveis // total)
        livre = self.barra.height - h
        y = self.barra.y + (livre * self.scroll // max(1, self._max_scroll()))
        return pygame.Rect(self.barra.x, y, self.barra.width, h)

    def _arrastar_barra(self, y):
        thumb = self._thumb()
        if thumb is None:
            return
        livre = self.barra.height - thumb.height
        topo = y - self._arrastando - self.barra.y
        self.scroll = max(0, min(self._max_scroll(),
                                 round(topo / max(1, livre) * self._max_scroll())))

    def _clique_lista(self, pos):
        thumb = self._thumb()
        if self.barra.collidepoint(pos) and thumb is not None:
            if thumb.collidepoint(pos):
                self._arrastando = pos[1] - thumb.y
            else:                                   # clique no trilho: uma página
                self._rolar(-self.visiveis if pos[1] < thumb.y else self.visiveis)
            return
        if self.busca.rect.collidepoint(pos):
            self.busca.clique(pos)
            return
        if (self.lista_area.collidepoint(pos) and pos[0] < self.barra.x):
            i = self.scroll + (pos[1] - self.lista_area.y) // self.linha_h
            if 0 <= i < len(self.filtrados):
                escolhida = self.filtrados[i]
                agora = pygame.time.get_ticks()
                tempo, anterior = self._ultimo_clique
                self.sel = escolhida
                self._ultimo_clique = (agora, escolhida)
                if anterior is escolhida and agora - tempo <= DUPLO_CLIQUE_MS:
                    self._ultimo_clique = (0, None)
                    self._abrir_editor(escolhida)

    # ── editor ───────────────────────────────────────────────────────────
    def _evento_editor(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self._clique_botoes(ev, (self.btn_voltar, self.btn_salvar,
                                        self.btn_cancelar)):
                return
            self._clique_editor(ev.pos)
        elif ev.type == pygame.TEXTINPUT:
            self.campos_foco[self.foco].inserir(ev.text)
            self.erro = ""
        elif ev.type == pygame.KEYDOWN:
            self._tecla_editor(ev)

    def _clique_editor(self, pos):
        for chave, rect in self.seg_nivel.items():
            if rect.collidepoint(pos):
                self.dados_edicao["dificuldade_chave"] = chave
                return
        for letra, rect in self.badges.items():
            if rect.collidepoint(pos):
                self.dados_edicao["resposta"] = letra
                self.erro = ""
                return
        for i, campo in enumerate(self.campos_foco):
            if campo.rect.collidepoint(pos):
                self.foco = i
                campo.clique(pos)
                return

    def _tecla_editor(self, ev):
        k = ev.key
        ctrl = ev.mod & pygame.KMOD_CTRL
        if k == pygame.K_ESCAPE:
            self._cancelar_editor()
        elif k == pygame.K_s and ctrl:
            self._salvar_editor()
        elif k == pygame.K_v and ctrl:
            self.campos_foco[self.foco].colar()
        elif k == pygame.K_TAB or k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            passo = -1 if (k == pygame.K_TAB and ev.mod & pygame.KMOD_SHIFT) else 1
            self.foco = (self.foco + passo) % len(self.campos_foco)
        elif self.campos_foco[self.foco].tecla(ev):
            self.erro = ""

    # ══════════════════════════════════════════════════════════════════════
    # DESENHO
    # ══════════════════════════════════════════════════════════════════════
    def _titulo_atual(self):
        if self.modo == "editor":
            return "NOVA PERGUNTA" if self.alvo_edicao is None else "EDITAR PERGUNTA"
        return "PERGUNTAS"

    def desenhar(self, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        tela, sy = self.screen, self.sy
        p = self.painel_rect

        tela.blit(self.fundo, (0, 0))
        tela.blit(self._veu, (0, 0))
        titulo = self._txt(self.f_titulo, self._titulo_atual(), AMARELO_TITULO,
                           CONTORNO_TITULO, 4)
        tela.blit(titulo, titulo.get_rect(center=(self.W // 2, sy(38))))
        tela.blit(self._img_painel, p.topleft)

        if self.modo == "editor":
            self._desenhar_editor(mouse_pos)
        else:
            self._desenhar_lista(mouse_pos)
        self.btn_voltar.desenhar(tela, mouse_pos)

        if self.modo == "confirmar":
            self._desenhar_confirmar(mouse_pos)
        self._desenhar_aviso()

    def _t(self, fonte, texto, cor=BRANCO, espessura=2):
        return self._txt(fonte, texto, cor, CONTORNO_TITULO, espessura)

    def _cortado(self, fonte, texto, largura):
        chave = (id(fonte), texto, largura)
        r = self._cortes.get(chave)
        if r is None:
            if len(self._cortes) > 800:
                self._cortes.clear()
            r = self._cortes[chave] = cortar(texto, fonte, largura)
        return r

    # ── lista ────────────────────────────────────────────────────────────
    def _desenhar_lista(self, mouse_pos):
        tela, sx, sy, p = self.screen, self.sx, self.sy, self.painel_rect

        rot = self._t(self.f_label, "BUSCAR:")
        tela.blit(rot, rot.get_rect(midleft=(self.x0, self.busca.rect.centery)))
        self.busca.desenhar(tela, True)
        total = len(self.banco.perguntas)
        achadas = len(self.filtrados)
        txt = f"{total} PERGUNTAS" if achadas == total else f"{achadas} DE {total}"
        cont = self._t(self.f_label, txt, AMARELO_TITULO)
        tela.blit(cont, cont.get_rect(midright=(p.right - sx(30), self.busca.rect.centery)))

        self._desenhar_linhas(mouse_pos)
        self._desenhar_barra()

        self.btn_adicionar.desenhar(tela, mouse_pos)
        self.btn_editar.desenhar(tela, mouse_pos)
        self.btn_excluir.desenhar(tela, mouse_pos)

    def _desenhar_linhas(self, mouse_pos):
        tela, sx = self.screen, self.sx
        a = self.lista_area
        if not self.filtrados:
            vazio = ("NENHUMA PERGUNTA ENCONTRADA" if self.banco.perguntas
                     else "NENHUMA PERGUNTA CADASTRADA - CLIQUE EM ADICIONAR")
            img = self._t(self.f_label, vazio, TXT_SUAVE)
            tela.blit(img, img.get_rect(center=a.center))
            return

        w_num, w_nivel, w_disc = sx(46), sx(78), sx(120)
        for k in range(self.visiveis):
            i = self.scroll + k
            if i >= len(self.filtrados):
                break
            pergunta = self.filtrados[i]
            r = pygame.Rect(a.x, a.y + k * self.linha_h, self.linhas_largura,
                            self.linha_h - 4)
            selecionada = pergunta is self.sel
            if selecionada:
                cor_fundo, cor_txt = DOURADO, TXT_ESCURO
            elif r.collidepoint(mouse_pos):
                cor_fundo, cor_txt = LINHA_HOVER, TXT_CLARO
            else:
                cor_fundo, cor_txt = (LINHA_A if i % 2 == 0 else LINHA_B), TXT_CLARO
            pygame.draw.rect(tela, cor_fundo, r, border_radius=sx(8))
            pygame.draw.rect(tela, AZUL_ESCURO if selecionada else AZUL_LINHA, r, 2,
                             border_radius=sx(8))

            x = r.x + sx(10)
            num = self.f_lista_neg.render(str(self.numeros.get(id(pergunta), "")), True,
                                          TXT_ESCURO if selecionada else TXT_SUAVE)
            tela.blit(num, (x, r.centery - num.get_height() // 2))
            x += w_num

            nivel = self._t(self.f_pequena, ROTULO_NIVEL[pergunta["dificuldade_chave"]],
                            COR_NIVEL[pergunta["dificuldade_chave"]])
            tela.blit(nivel, nivel.get_rect(midleft=(x, r.centery)))
            x += w_nivel

            disc = self._cortado(self.f_lista, pergunta["disciplina"], w_disc - sx(10))
            img = self.f_lista.render(disc, True, TXT_ESCURO if selecionada else TXT_SUAVE)
            tela.blit(img, (x, r.centery - img.get_height() // 2))
            x += w_disc

            if pergunta["origem"] == "professor":
                marca = self._t(self.f_pequena, "PROF", TXT_SUAVE if not selecionada
                                else TXT_ESCURO)
                tela.blit(marca, marca.get_rect(midright=(r.right - sx(10), r.centery)))
                limite = r.right - sx(60)
            else:
                limite = r.right - sx(10)
            enun = self._cortado(self.f_lista, pergunta["pergunta"], limite - x)
            img = self.f_lista.render(enun, True, cor_txt)
            tela.blit(img, (x, r.centery - img.get_height() // 2))

    def _desenhar_barra(self):
        thumb = self._thumb()
        if thumb is None:
            return
        tela = self.screen
        pygame.draw.rect(tela, AZUL_ESCURO, self.barra, border_radius=self.barra.width // 2)
        pygame.draw.rect(tela, DOURADO, thumb.inflate(-4, -2),
                         border_radius=self.barra.width // 2)

    # ── editor ───────────────────────────────────────────────────────────
    def _desenhar_editor(self, mouse_pos):
        tela, sx, sy, p = self.screen, self.sx, self.sy, self.painel_rect

        tela.blit(self._t(self.f_label, "DISCIPLINA:"), (self.x0, p.y + sy(10)))
        tela.blit(self._t(self.f_label, "DIFICULDADE:"), self.pos_label_nivel)
        tela.blit(self._t(self.f_label, "PERGUNTA:"), (self.x0, p.y + sy(68)))
        y = p.y + sy(172)
        tela.blit(self._t(self.f_label, "ALTERNATIVAS:"), (self.x0, y))
        dica = self._t(self.f_pequena, "CLIQUE NA LETRA DA RESPOSTA CERTA", TXT_SUAVE)
        tela.blit(dica, (self.x0 + sx(190), y + sy(2)))

        self.campo_disc.desenhar(tela, self.foco == 0)
        self._desenhar_niveis()
        self.campo_perg.desenhar(tela, self.foco == 1)
        for i, letra in enumerate(LETRAS):
            self._desenhar_badge(letra, mouse_pos)
            self.campo_alt[letra].desenhar(tela, self.foco == i + 2)

        if self.erro:
            msg = self._t(self.f_aviso, self.erro, COR_ERRO)
            tela.blit(msg, msg.get_rect(midtop=(p.centerx, p.y + sy(380))))
        self.btn_salvar.desenhar(tela, mouse_pos)
        self.btn_cancelar.desenhar(tela, mouse_pos)

    def _desenhar_niveis(self):
        tela = self.screen
        atual = self.dados_edicao.get("dificuldade_chave", "medio")
        for chave, rect in self.seg_nivel.items():
            ativo = chave == atual
            pygame.draw.rect(tela, DOURADO if ativo else AZUL_ESCURO, rect,
                             border_radius=rect.height // 3)
            pygame.draw.rect(tela, AZUL_ESCURO if ativo else AZUL_LINHA, rect, 3,
                             border_radius=rect.height // 3)
            img = self._t(self.f_pequena, ROTULO_NIVEL[chave],
                          BRANCO if ativo else TXT_SUAVE)
            tela.blit(img, img.get_rect(center=rect.center))

    def _desenhar_badge(self, letra, mouse_pos):
        tela = self.screen
        rect = self.badges[letra]
        certa = self.dados_edicao.get("resposta", "") == letra
        r = rect.width // 2
        fundo = DOURADO if certa else (LINHA_HOVER if rect.collidepoint(mouse_pos)
                                       else AZUL_ESCURO)
        pygame.draw.circle(tela, fundo, rect.center, r)
        pygame.draw.circle(tela, AZUL_ESCURO if certa else AZUL_LINHA, rect.center, r, 3)
        img = self._t(self.f_label, letra.upper(), BRANCO)
        tela.blit(img, img.get_rect(center=rect.center))

    # ── confirmar ────────────────────────────────────────────────────────
    def _desenhar_confirmar(self, mouse_pos):
        tela, sx, sy, c = self.screen, self.sx, self.sy, self.conf_rect
        tela.blit(self._veu_modal, (0, 0))
        tela.blit(self._img_conf, c.topleft)
        titulo = self._t(self.f_aviso, "EXCLUIR ESTA PERGUNTA?", AMARELO_TITULO, 3)
        tela.blit(titulo, titulo.get_rect(center=(c.centerx, c.y + sy(40))))

        if self.sel is not None:
            largura = c.width - 2 * sx(36)
            linhas = quebrar(self.sel["pergunta"], self.f_campo, largura)[:3]
            y = c.y + sy(72)
            for ini, fim in linhas:
                trecho = self.sel["pergunta"][ini:fim].rstrip()
                if (ini, fim) == linhas[-1] and fim < len(self.sel["pergunta"]):
                    trecho = self._cortado(self.f_campo, trecho + " ...", largura)
                img = self.f_campo.render(trecho, True, TXT_CLARO)
                tela.blit(img, img.get_rect(midtop=(c.centerx, y)))
                y += img.get_height() + sy(2)
        aviso = self._t(self.f_pequena, "ESTA ACAO NAO PODE SER DESFEITA", COR_ERRO)
        tela.blit(aviso, aviso.get_rect(center=(c.centerx, c.bottom - sy(94))))
        self.btn_sim.desenhar(tela, mouse_pos)
        self.btn_nao.desenhar(tela, mouse_pos)

    # ── aviso temporário (rodapé) ────────────────────────────────────────
    def _desenhar_aviso(self):
        if not self.mensagem or pygame.time.get_ticks() >= self.mensagem_ate:
            return
        tela, sx, sy = self.screen, self.sx, self.sy
        msg = self._t(self.f_aviso, self.mensagem, BRANCO)
        caixa = msg.get_rect(center=(self.W // 2, self.H - sy(20)))
        fundo = pygame.Surface((caixa.width + sx(28), caixa.height + sy(10)),
                               pygame.SRCALPHA)
        pygame.draw.rect(fundo, (10, 14, 55, 225), fundo.get_rect(), border_radius=sy(10))
        pygame.draw.rect(fundo, DOURADO, fundo.get_rect(), 2, border_radius=sy(10))
        tela.blit(fundo, fundo.get_rect(center=caixa.center))
        tela.blit(msg, caixa)
