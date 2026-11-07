# -*- coding: utf-8 -*-
"""
=====================================================================
 TELA DE ESTATÍSTICAS (fim de jogo / meio de jogo)
=====================================================================
Mostra o desempenho da sessão atual do jogador: quantas perguntas
foram respondidas, quantos acertos, e o detalhe de cada pergunta
(enunciado, todas as alternativas, matéria, dificuldade e qual
alternativa foi escolhida) — com opção de gerar um PDF para o
professor.

Este módulo NÃO cria janela nem chama pygame.init()/pygame.quit():
ele é só mais um "estado" desenhado dentro da MESMA janela/loop do
jogo (main.py), igual à TelaCreditos e à TelaConfiguracoes.

Contém:
    - Banco:            acesso ao SQLite local (sessões + respostas)
    - TelaEstatisticas:  desenho + eventos (scroll, clique, PDF)
    - gerar_pdf_relatorio: relatório em PDF para o professor
=====================================================================
"""

import os
import sys
import json
import sqlite3
import datetime

import pygame

from src.nucleo.utils import ROOT, carregar_fonte, carregar_fonte_typewriter, carregar_imagem

# =====================================================================
#  CAMINHOS
# =====================================================================
# ISA_DB permite apontar para outro arquivo (os testes usam um banco
# temporário e nunca tocam no estatisticas.db de verdade).
CAMINHO_BANCO = os.environ.get("ISA_DB") or (ROOT / "estatisticas.db")
PASTA_SAIDA_PDF = ROOT

FONTE_JOGO = "upheavtt.ttf"  # mesma fonte pixel já usada no resto do jogo

# Rodapé institucional impresso em TODAS as páginas do relatório PDF
RODAPE_LINHA_1 = "Fundação Salvador Arena"
RODAPE_LINHA_2 = "Curso Técnico em Informática - Formandos 2º Semestre de 2026"


def _latin1(texto):
    """As fontes nativas do PDF (Helvetica) só aceitam latin-1. Isso troca
    caracteres fora dessa faixa (travessão, aspas curvas etc.) por
    equivalentes simples, evitando que a geração do PDF quebre."""
    substituicoes = {
        "\u2013": "-", "\u2014": "-",  # travessões
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u2022": "-",
        # Símbolos do banco de perguntas (fórmulas de Química/Física/Mat.):
        # sem isto o relatório do professor mostrava "?" no lugar deles.
        "\u03c0": "pi", "\u0394": "Delta", "\u2192": "->", "\u21cc": "<=>",
        "\u2248": "~", "\u2264": "<=", "\u2265": ">=", "\u2260": "!=",
        "\u207a": "+", "\u207b": "-",
    }
    # Subscritos (H₂O -> H2O) e sobrescritos (5p⁶ -> 5p6).
    for i in range(10):
        substituicoes[chr(0x2080 + i)] = str(i)
    for i, ch in enumerate("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079"):
        if ord(ch) > 255:
            substituicoes[ch] = str(i)
    texto = str(texto)
    for original, novo in substituicoes.items():
        texto = texto.replace(original, novo)
    return texto.encode("latin-1", "replace").decode("latin-1")

# =====================================================================
#  CORES / ESTILO (baseado na imagem de referência)
# =====================================================================
PAINEL_MARGEM = 14
PAINEL_RAIO = 26
PAINEL_COR = (18, 26, 46)
PAINEL_ALPHA = 130
PAINEL_BORDA = (232, 240, 248)

PILL_TOP, PILL_BOT = (247, 249, 252), (206, 214, 226)
PILL_BORDA = (150, 162, 180)
PILL_TEXTO = (38, 48, 70)
PILL_HOVER_TOP, PILL_HOVER_BOT = (86, 132, 240), (40, 82, 205)
PILL_HOVER_BORDA = (235, 242, 255)
PILL_HOVER_TEXTO = (255, 255, 255)

BTN_PDF_TOP, BTN_PDF_BOT = (252, 196, 70), (240, 150, 22)
BTN_PDF_BORDA = (255, 244, 210)
BTN_PDF_TEXTO = (60, 40, 0)

COR_ACERTO = (90, 210, 120)
COR_ERRO = (235, 90, 90)
COR_TXT = (245, 246, 238)
COR_OUT = (16, 22, 40)
COR_TAG = (255, 214, 120)

TITULO_TOP, TITULO_BOT = (255, 255, 255), (200, 226, 255)
TITULO_SOMBRA = (18, 40, 78)

SCROLL_VELOCIDADE = 45


# =====================================================================
#  FUNÇÕES UTILITÁRIAS DE DESENHO
# =====================================================================
def _mix(a, b, t):
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _conv(surf):
    try:
        return surf.convert_alpha()
    except pygame.error:
        return surf


def texto_gradiente(texto, fonte, cor_top, cor_bot, cor_sombra=None, off=(3, 4)):
    base = fonte.render(texto, True, (255, 255, 255))
    w, h = base.get_size()
    grad = pygame.Surface((max(1, w), max(1, h)))
    for y in range(h):
        pygame.draw.line(grad, _mix(cor_top, cor_bot, y / max(1, h - 1)), (0, y), (w, y))
    grad = _conv(grad)
    grad.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    res = pygame.Surface((w + abs(off[0]) + 2, h + abs(off[1]) + 2), pygame.SRCALPHA)
    if cor_sombra:
        res.blit(fonte.render(texto, True, cor_sombra), (off[0], off[1]))
    res.blit(grad, (0, 0))
    return res


def texto_contorno(texto, fonte, cor, cor_contorno=COR_OUT, esp=2):
    base = fonte.render(texto, True, cor)
    w, h = base.get_size()
    surf = pygame.Surface((w + 2 * esp, h + 2 * esp), pygame.SRCALPHA)
    o = fonte.render(texto, True, cor_contorno)
    for dx in range(-esp, esp + 1):
        for dy in range(-esp, esp + 1):
            if dx * dx + dy * dy <= esp * esp + 1:
                surf.blit(o, (esp + dx, esp + dy))
    surf.blit(base, (esp, esp))
    return surf


def criar_pilula(w, h, top, bot, borda, raio, texto=None, fonte=None, cor_texto=(0, 0, 0)):
    w, h = max(1, w), max(1, h)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    grad = pygame.Surface((w, h))
    for y in range(h):
        pygame.draw.line(grad, _mix(top, bot, y / max(1, h - 1)), (0, y), (w, y))
    grad = _conv(grad)
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=raio)
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(grad, (0, 0))
    gloss = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(gloss, (255, 255, 255, 70), (4, 3, max(1, w - 8), max(1, h // 2 - 2)), border_radius=raio)
    surf.blit(gloss, (0, 0))
    pygame.draw.rect(surf, borda, (0, 0, w, h), width=3, border_radius=raio)
    if texto and fonte:
        t = fonte.render(texto, True, cor_texto)
        surf.blit(t, ((w - t.get_width()) // 2, (h - t.get_height()) // 2))
    return surf


def quebrar_texto(texto, fonte, largura_max):
    palavras, linhas, atual = str(texto).split(" "), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if fonte.size(teste)[0] <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas or [""]


# =====================================================================
#  BANCO DE DADOS LOCAL (SQLite)
# =====================================================================
class Banco:
    """
    Banco SQLite local com duas tabelas:

      sessoes  -> uma partida do aluno (id, aluno, data_hora)
      respostas-> cada pergunta respondida naquela sessão, já com
                  matéria e dificuldade (id, sessao_id, ordem, materia,
                  dificuldade, enunciado, alternativas[JSON],
                  alternativa_correta, alternativa_escolhida, acertou)

    Uso durante o jogo:
        banco = Banco()
        sid = banco.nova_sessao("Nome do Aluno")
        banco.registrar_resposta(
            sid, ordem=1, materia="Matemática", dificuldade="Fácil",
            enunciado="Quanto é 7 x 8?",
            alternativas=[("a","54"), ("b","56"), ("c","64"), ("d","58")],
            letra_correta="b", letra_escolhida="b",
        )
        ...
        resultado = banco.buscar_resultado(sid)
    """

    def __init__(self, caminho=None):
        self.caminho = str(caminho or CAMINHO_BANCO)
        self.conn = sqlite3.connect(self.caminho)
        self.conn.row_factory = sqlite3.Row
        self._criar_tabelas()
        self._migrar_se_necessario()

    # ---- criação / migração (nunca apaga dados existentes) ----
    def _criar_tabelas(self):
        c = self.conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS sessoes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                aluno     TEXT,
                data_hora TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS respostas (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                sessao_id             INTEGER,
                ordem                 INTEGER,
                materia               TEXT,
                dificuldade           TEXT,
                enunciado             TEXT,
                alternativas          TEXT,
                alternativa_correta   TEXT,
                alternativa_escolhida TEXT,
                acertou               INTEGER,
                FOREIGN KEY (sessao_id) REFERENCES sessoes(id)
            )"""
        )
        self.conn.commit()

    def _colunas(self, tabela):
        cur = self.conn.execute(f"PRAGMA table_info({tabela})")
        return {row["name"] for row in cur.fetchall()}

    def _migrar_se_necessario(self):
        """
        Migração segura e aditiva: só ADICIONA colunas que ainda não
        existem (ex.: um estatisticas.db mais antigo, gerado sem
        matéria/dificuldade). Nunca remove tabelas ou linhas.
        """
        colunas = self._colunas("respostas")
        migracoes = {
            "materia": "TEXT DEFAULT ''",
            "dificuldade": "TEXT DEFAULT ''",
            "alternativa_correta": "TEXT DEFAULT ''",
            "alternativa_escolhida": "TEXT DEFAULT ''",
        }
        for coluna, definicao in migracoes.items():
            if coluna not in colunas:
                try:
                    self.conn.execute(
                        f"ALTER TABLE respostas ADD COLUMN {coluna} {definicao}"
                    )
                except sqlite3.OperationalError as e:
                    print(f"Aviso: não foi possível migrar coluna '{coluna}': {e}")
        if "resultado" not in self._colunas("sessoes"):
            try:
                self.conn.execute("ALTER TABLE sessoes ADD COLUMN resultado TEXT DEFAULT ''")
            except sqlite3.OperationalError as e:
                print(f"Aviso: não foi possível migrar coluna 'resultado': {e}")
        if "data_hora" not in self._colunas("sessoes"):
            try:
                self.conn.execute("ALTER TABLE sessoes ADD COLUMN data_hora TEXT")
            except sqlite3.OperationalError as e:
                print(f"Aviso: não foi possível migrar coluna 'data_hora': {e}")
        self.conn.commit()

    # ---- gravação (chamado pelo jogo) ----
    def nova_sessao(self, aluno="Aluno"):
        aluno = (aluno or "Aluno").strip() or "Aluno"
        data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        try:
            cur = self.conn.execute(
                "INSERT INTO sessoes (aluno, data_hora) VALUES (?, ?)", (aluno, data)
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.Error as e:
            print(f"Erro ao criar sessão no banco de estatísticas: {e}")
            return None

    def registrar_resposta(
        self,
        sessao_id,
        ordem,
        materia,
        dificuldade,
        enunciado,
        alternativas,
        letra_correta,
        letra_escolhida,
    ):
        """
        alternativas: lista de tuplas (letra, texto), ex.: [("a","54"), ("b","56")]
        letra_correta / letra_escolhida: "a".."e" (minúsculo)
        """
        if sessao_id is None:
            return
        acertou = 1 if (letra_escolhida or "").strip().lower() == (letra_correta or "").strip().lower() else 0
        try:
            self.conn.execute(
                """INSERT INTO respostas
                   (sessao_id, ordem, materia, dificuldade, enunciado,
                    alternativas, alternativa_correta, alternativa_escolhida, acertou)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    sessao_id,
                    ordem,
                    materia or "Geral",
                    dificuldade or "Médio",
                    enunciado or "",
                    json.dumps(alternativas, ensure_ascii=False),
                    (letra_correta or "").strip().lower(),
                    (letra_escolhida or "").strip().lower(),
                    acertou,
                ),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Erro ao registrar resposta no banco de estatísticas: {e}")

    def marcar_resultado(self, sessao_id, resultado):
        """Fim da campanha: 'vitoria', 'derrota' ou 'derrota no boss'."""
        if sessao_id is None:
            return
        try:
            self.conn.execute("UPDATE sessoes SET resultado=? WHERE id=?",
                              (resultado, sessao_id))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Erro ao gravar o resultado da sessão {sessao_id}: {e}")

    # ---- leitura (usado pela tela) ----
    def buscar_resultado(self, sessao_id):
        if sessao_id is None:
            return self.resultado_vazio()
        try:
            s = self.conn.execute(
                "SELECT * FROM sessoes WHERE id=?", (sessao_id,)
            ).fetchone()
            rows = self.conn.execute(
                "SELECT * FROM respostas WHERE sessao_id=? ORDER BY ordem",
                (sessao_id,),
            ).fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao buscar estatísticas da sessão {sessao_id}: {e}")
            return self.resultado_vazio()

        perguntas = []
        for r in rows:
            try:
                alternativas = json.loads(r["alternativas"] or "[]")
            except (TypeError, ValueError):
                alternativas = []
            perguntas.append(
                {
                    "ordem": r["ordem"],
                    "materia": r["materia"] or "Geral",
                    "dificuldade": r["dificuldade"] or "Médio",
                    "enunciado": r["enunciado"] or "",
                    "alternativas": [tuple(a) for a in alternativas],
                    "correta": (r["alternativa_correta"] or "").lower(),
                    "escolhida": (r["alternativa_escolhida"] or "").lower(),
                    "acertou": bool(r["acertou"]),
                }
            )
        return {
            "sessao_id": sessao_id,
            "aluno": (s["aluno"] if s else "Aluno") or "Aluno",
            "data": (s["data_hora"] if s else "") or "",
            "resultado": (s["resultado"] if s and "resultado" in s.keys() else "") or "",
            "respondidas": len(perguntas),
            "acertos": sum(1 for p in perguntas if p["acertou"]),
            "perguntas": perguntas,
        }

    def resultado_vazio(self, aluno="Aluno"):
        return {
            "sessao_id": None,
            "aluno": aluno,
            "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "respondidas": 0,
            "acertos": 0,
            "perguntas": [],
        }

    def fechar(self):
        """Fecha a conexão SQLite. Chamado ao sair do jogo."""
        try:
            self.conn.close()
        except sqlite3.Error:
            pass


# =====================================================================
#  GERAÇÃO DO PDF (relatório para o professor)
# =====================================================================
def gerar_pdf_relatorio(resultado, pasta_saida=None):
    """Gera o relatório de desempenho em PDF e devolve o caminho do arquivo."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pasta_saida = str(pasta_saida or PASTA_SAIDA_PDF)
    os.makedirs(pasta_saida, exist_ok=True)

    NX, NY = XPos.LMARGIN, YPos.NEXT
    letra_upper = lambda l: (l or "?").upper()

    respondidas = resultado["respondidas"]
    acertos = resultado["acertos"]
    erros = respondidas - acertos
    percentual = (acertos / respondidas * 100) if respondidas else 0

    class RelatorioPDF(FPDF):
        """FPDF com rodapé institucional fixo.

        O método footer() é chamado automaticamente pelo fpdf2 ao fechar
        CADA página, então as duas linhas aparecem em todas elas sem
        precisar repetir nada no meio do relatório.
        """

        def footer(self):
            self.set_y(-14)  # 14mm a partir do fim da página
            self.set_font("Helvetica", "", 8)
            self.set_text_color(90, 90, 90)
            # Entrelinha curta (4mm) pra as duas linhas ficarem juntinhas
            self.cell(0, 4, _latin1(RODAPE_LINHA_1), align="C", new_x=NX, new_y=NY)
            self.cell(0, 4, _latin1(RODAPE_LINHA_2), align="C", new_x=NX, new_y=NY)

    pdf = RelatorioPDF()
    # Margem inferior maior que o padrão pra o conteúdo nunca encostar
    # nas duas linhas do rodapé.
    pdf.set_auto_page_break(True, margin=22)
    pdf.add_page()

    # Cabeçalho
    pdf.set_fill_color(40, 82, 205)
    pdf.rect(0, 0, 210, 26, "F")
    pdf.set_xy(10, 7)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, _latin1("Relatório de Desempenho"), new_x=NX, new_y=NY)

    pdf.set_text_color(30, 30, 30)
    pdf.set_xy(10, 32)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, _latin1(f"Aluno: {resultado['aluno']}"), new_x=NX, new_y=NY)
    pdf.cell(0, 6, _latin1(f"Data: {resultado['data']}"), new_x=NX, new_y=NY)
    rotulos = {"vitoria": "Vitória - Gorila derrotado", "derrota": "Derrota",
               "derrota no boss": "Derrota na luta contra o Gorila"}
    if resultado.get("resultado"):
        pdf.cell(0, 6, _latin1(f"Resultado da campanha: "
                               f"{rotulos.get(resultado['resultado'], resultado['resultado'])}"),
                 new_x=NX, new_y=NY)
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, f"Perguntas respondidas: {respondidas}", new_x=NX, new_y=NY)
    pdf.cell(0, 7, f"Acertos: {acertos}", new_x=NX, new_y=NY)
    pdf.cell(0, 7, f"Erros: {erros}", new_x=NX, new_y=NY)
    pdf.cell(0, 7, f"Percentual de acerto: {percentual:.0f}%", new_x=NX, new_y=NY)
    pdf.ln(2)

    if not resultado["perguntas"]:
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 6, _latin1("Nenhuma pergunta foi respondida nesta sessão."), new_x=NX, new_y=NY)

    for p in resultado["perguntas"]:
        pdf.set_draw_color(200, 200, 200)
        pdf.cell(0, 2, "", border="T", new_x=NX, new_y=NY)
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 11)
        tag = "ACERTO" if p["acertou"] else "ERRO"
        pdf.set_text_color(*(COR_ACERTO if p["acertou"] else COR_ERRO))
        pdf.multi_cell(0, 6, f"PERGUNTA {p['ordem']}  [{tag}]", new_x=NX, new_y=NY)

        pdf.set_text_color(90, 90, 90)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 5, _latin1(f"Materia: {p['materia']}    Dificuldade: {p['dificuldade']}"), new_x=NX, new_y=NY)

        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 5.5, "Enunciado:", new_x=NX, new_y=NY)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.5, _latin1(p["enunciado"]), new_x=NX, new_y=NY)
        pdf.ln(1)

        pdf.set_font("Helvetica", "", 10)
        for letra, texto in p["alternativas"]:
            marcas = []
            if letra == p["escolhida"]:
                marcas.append("<- escolhida")
            if letra == p["correta"]:
                marcas.append("(correta)")
            sufixo = ("   " + "  ".join(marcas)) if marcas else ""
            if letra == p["correta"]:
                pdf.set_text_color(*COR_ACERTO)
            elif letra == p["escolhida"]:
                pdf.set_text_color(*COR_ERRO)
            else:
                pdf.set_text_color(70, 70, 70)
            pdf.multi_cell(0, 5.5, _latin1(f"   {letra_upper(letra)}) {texto}{sufixo}"), new_x=NX, new_y=NY)

        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "B", 10)
        resp_correta = next((t for l, t in p["alternativas"] if l == p["correta"]), "-")
        resp_escolhida = next((t for l, t in p["alternativas"] if l == p["escolhida"]), "-")
        pdf.multi_cell(0, 5.5, _latin1(f"Resposta correta: {letra_upper(p['correta'])}) {resp_correta}"), new_x=NX, new_y=NY)
        pdf.multi_cell(0, 5.5, _latin1(f"Resposta escolhida: {letra_upper(p['escolhida'])}) {resp_escolhida}"), new_x=NX, new_y=NY)
        pdf.ln(3)

    nome = f"relatorio_sessao_{resultado['sessao_id'] or 'sem_id'}.pdf"
    caminho = os.path.join(pasta_saida, nome)
    pdf.output(caminho)
    return caminho


def _abrir_arquivo_no_sistema(caminho):
    """Abre o PDF gerado no visualizador padrão do sistema (best-effort)."""
    try:
        if os.name == "nt":
            os.startfile(caminho)  # noqa: S606 - Windows
        elif sys.platform == "darwin":
            os.system(f'open "{caminho}"')
        else:
            os.system(f'xdg-open "{caminho}" >/dev/null 2>&1 &')
    except Exception as e:  # noqa: BLE001 - abrir automaticamente é opcional
        print(f"Não foi possível abrir o PDF automaticamente: {e}")


# =====================================================================
#  TELA DE ESTATÍSTICAS
# =====================================================================
class TelaEstatisticas:
    """
    Tela de estatísticas desenhada na MESMA superfície (`screen`) e
    dentro do MESMO loop do jogo — segue o padrão de TelaCreditos /
    TelaConfiguracoes: __init__(screen, largura, altura, ...),
    handle_event(evento), desenhar(mouse_pos).
    """

    def __init__(self, screen, largura, altura, resultado, callback_voltar=None, callback_pdf_gerado=None):
        self.screen = screen
        self.largura = largura
        self.altura = altura
        self.res = resultado
        self.callback_voltar = callback_voltar
        self.callback_pdf_gerado = callback_pdf_gerado

        self._carregar_fontes()
        self._carregar_fundo()
        self._montar_estatico()
        self._montar_blocos()

        self.scroll = 0
        self.max_scroll = 0
        self.hover_idx = -1
        self.hover_pdf = False
        self.hover_voltar = False
        self.toast = None  # (texto, cor, frames_restantes)
        self._recalcular_scroll_max()

    # ---------- carregamento ----------
    def _fonte(self, tamanho):
        try:
            return carregar_fonte(FONTE_JOGO, max(8, int(tamanho)))
        except (FileNotFoundError, pygame.error):
            return pygame.font.SysFont("consolas,couriernew,monospace", max(8, int(tamanho)), bold=True)

    def _carregar_fontes(self):
        base = self.altura / 606  # a referência foi desenhada para 606px de altura
        self.f_titulo = self._fonte(40 * base)
        self.f_score = self._fonte(22 * base)
        self.f_pill = self._fonte(17 * base)
        self.f_tag = self._fonte(14 * base)
        # Enunciados e alternativas na fonte de leitura (Century Gothic)
        self.f_enun = carregar_fonte_typewriter(16 * base)
        self.f_alt = carregar_fonte_typewriter(15 * base)
        self.f_pdf = self._fonte(18 * base)
        self.f_voltar = self._fonte(14 * base)
        self.f_toast = self._fonte(15 * base)

    def _carregar_fundo(self):
        try:
            img = carregar_imagem("backgrounds", "FundoMenu.png")
            self.fundo = pygame.transform.scale(img, (self.largura, self.altura))
        except (FileNotFoundError, pygame.error) as e:
            print(f"Aviso: não foi possível carregar o fundo da tela de estatísticas: {e}")
            self.fundo = pygame.Surface((self.largura, self.altura))
            for y in range(self.altura):
                self.fundo.fill(
                    _mix((40, 60, 120), (90, 130, 190), y / max(1, self.altura)), (0, y, self.largura, 1)
                )

    def _montar_estatico(self):
        W, H = self.largura, self.altura

        # Painel translúcido arredondado (deixa o cenário visível atrás)
        self.painel_rect = pygame.Rect(
            PAINEL_MARGEM, PAINEL_MARGEM, W - 2 * PAINEL_MARGEM, H - 2 * PAINEL_MARGEM
        )
        self.painel = pygame.Surface(self.painel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            self.painel, (*PAINEL_COR, PAINEL_ALPHA), self.painel.get_rect(), border_radius=PAINEL_RAIO
        )
        pygame.draw.rect(
            self.painel, PAINEL_BORDA, self.painel.get_rect(), width=3, border_radius=PAINEL_RAIO
        )

        # Título (posição derivada da altura real do texto renderizado, não
        # de um número mágico — evita sobreposição em qualquer resolução)
        self.titulo = texto_gradiente(
            "ESTATISTICAS", self.f_titulo, TITULO_TOP, TITULO_BOT, TITULO_SOMBRA
        )
        titulo_y = PAINEL_MARGEM + int(12 * H / 606)
        self.titulo_pos = (W // 2 - self.titulo.get_width() // 2, titulo_y)

        # Resumo (XX/YY ACERTOS) — logo abaixo do título, à esquerda
        if self.res["respondidas"] > 0:
            txt_score = f"{self.res['acertos']}/{self.res['respondidas']} ACERTOS"
        else:
            txt_score = "0/0 ACERTOS"
        self.score = texto_contorno(txt_score, self.f_score, (255, 255, 255), (20, 40, 80), esp=2)
        score_y = titulo_y + self.titulo.get_height() + int(10 * H / 606)
        self.score_pos = (PAINEL_MARGEM + int(24 * W / 886), score_y)

        self.sem_perguntas = None
        if self.res["respondidas"] == 0:
            self.sem_perguntas = texto_contorno(
                "NENHUMA PERGUNTA RESPONDIDA", self.f_enun, COR_TAG, COR_OUT, esp=2
            )

        # Botão GERAR PDF (canto inferior direito, pílula dourada)
        btn_w, btn_h = int(150 * W / 886), int(44 * H / 606)
        self.btn_pdf_rect = pygame.Rect(
            W - PAINEL_MARGEM - btn_w - 14, H - PAINEL_MARGEM - btn_h - 14, btn_w, btn_h
        )
        self.btn_pdf_normal = criar_pilula(
            btn_w, btn_h, BTN_PDF_TOP, BTN_PDF_BOT, BTN_PDF_BORDA, 16, "GERAR PDF", self.f_pdf, BTN_PDF_TEXTO
        )
        self.btn_pdf_hover = criar_pilula(
            btn_w,
            btn_h,
            _mix(BTN_PDF_TOP, (255, 255, 255), 0.18),
            _mix(BTN_PDF_BOT, (255, 255, 255), 0.12),
            (255, 255, 255),
            16,
            "GERAR PDF",
            self.f_pdf,
            BTN_PDF_TEXTO,
        )

        # Link para voltar ao menu (canto inferior esquerdo)
        self.voltar_normal = texto_contorno("VOLTAR AO MENU", self.f_voltar, (235, 240, 245), COR_OUT, esp=2)
        self.voltar_hover = texto_contorno("VOLTAR AO MENU", self.f_voltar, (255, 220, 120), COR_OUT, esp=2)
        self.voltar_rect = self.voltar_normal.get_rect(
            bottomleft=(PAINEL_MARGEM + 18, H - PAINEL_MARGEM - 12)
        )

        # Área de conteúdo rolável (entre o resumo e a linha do botão PDF)
        topo = self.score_pos[1] + self.score.get_height() + int(14 * H / 606)
        fundo_area = self.btn_pdf_rect.top - int(10 * H / 606)
        self.area = pygame.Rect(
            PAINEL_MARGEM + 6, topo, W - 2 * (PAINEL_MARGEM + 6), max(10, fundo_area - topo)
        )

        self.pill_largura = min(int(340 * W / 886), self.area.width - 20)
        self.bloco_largura = min(int(640 * W / 886), self.area.width - 20)
        self.pill_x = self.area.centerx - self.pill_largura // 2
        self.bloco_x = self.area.centerx - self.bloco_largura // 2
        self.pill_altura = int(38 * H / 606)

    # ---------- monta um bloco visual por pergunta ----------
    def _montar_blocos(self):
        self.blocos = []
        largura_txt = self.bloco_largura - 24
        he = self.f_enun.get_height() + 3
        ha = self.f_alt.get_height() + 5

        def centralizar(corpo, superficie, y):
            corpo.blit(superficie, ((self.bloco_largura - superficie.get_width()) // 2, y))

        for p in self.res["perguntas"]:
            linhas_tag = [f"{p['materia'].upper()}  |  {p['dificuldade'].upper()}"]
            linhas_en = quebrar_texto(p["enunciado"], self.f_enun, largura_txt)

            linhas_alt = []  # cada item: (linhas_de_texto, cor)
            for letra, texto in p["alternativas"]:
                cor = COR_TXT
                sufixo = ""
                if letra == p["correta"]:
                    cor = COR_ACERTO
                    if letra != p["escolhida"]:
                        sufixo = "  <- CORRETA"
                if letra == p["escolhida"] and letra != p["correta"]:
                    cor = COR_ERRO
                    sufixo = "  <- ERRADA"
                texto_linha = f"{letra.upper()}) {texto}{sufixo}"
                linhas_alt.append((quebrar_texto(texto_linha, self.f_alt, largura_txt), cor))

            resp_escolhida_txt = next(
                (t for l, t in p["alternativas"] if l == p["escolhida"]), "-"
            )
            cor_resp = COR_ACERTO if p["acertou"] else COR_ERRO
            linha_resp = quebrar_texto(
                f"RESPOSTA ESCOLHIDA: {p['escolhida'].upper()}) {resp_escolhida_txt}"
                + ("" if p["acertou"] else "  <- ERRADA"),
                self.f_alt,
                largura_txt,
            )

            # altura total do corpo desse bloco
            h = 6
            h += len(linhas_tag) * (self.f_tag.get_height() + 4) + 6
            h += len(linhas_en) * he + 10
            for ls, _cor in linhas_alt:
                h += len(ls) * ha
            h += 8 + len(linha_resp) * ha + 8

            corpo = pygame.Surface((self.bloco_largura, h), pygame.SRCALPHA)
            y = 4
            for ln in linhas_tag:
                centralizar(corpo, texto_contorno(ln, self.f_tag, COR_TAG, COR_OUT, 2), y)
                y += self.f_tag.get_height() + 4
            y += 6
            for ln in linhas_en:
                centralizar(corpo, texto_contorno(ln, self.f_enun, COR_TXT, COR_OUT, 2), y)
                y += he
            y += 10
            for ls, cor in linhas_alt:
                for ln in ls:
                    centralizar(corpo, texto_contorno(ln, self.f_alt, cor, COR_OUT, 2), y)
                    y += ha
            y += 8
            for ln in linha_resp:
                centralizar(corpo, texto_contorno(ln, self.f_alt, cor_resp, COR_OUT, 2), y)
                y += ha

            cab_normal = criar_pilula(
                self.pill_largura, self.pill_altura, PILL_TOP, PILL_BOT, PILL_BORDA, self.pill_altura // 2,
                f"PERGUNTA {p['ordem']}", self.f_pill, PILL_TEXTO,
            )
            cab_hover = criar_pilula(
                self.pill_largura, self.pill_altura, PILL_HOVER_TOP, PILL_HOVER_BOT, PILL_HOVER_BORDA,
                self.pill_altura // 2, f"PERGUNTA {p['ordem']}", self.f_pill, PILL_HOVER_TEXTO,
            )

            self.blocos.append(
                {
                    "cab_normal": cab_normal,
                    "cab_hover": cab_hover,
                    "corpo": corpo,
                    "altura": self.pill_altura + 8 + h,
                }
            )

    def _recalcular_scroll_max(self):
        espaco = int(24 * self.altura / 606)
        total = sum(b["altura"] + espaco for b in self.blocos)
        self.max_scroll = max(0, total - self.area.height)
        self.scroll = min(self.scroll, self.max_scroll)

    # ---------- eventos ----------
    def handle_event(self, evento):
        if evento.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll, self.scroll - evento.y * SCROLL_VELOCIDADE))
        elif evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                self.scroll = min(self.max_scroll, self.scroll + SCROLL_VELOCIDADE)
            elif evento.key in (pygame.K_UP, pygame.K_PAGEUP):
                self.scroll = max(0, self.scroll - SCROLL_VELOCIDADE)
            elif evento.key == pygame.K_ESCAPE:
                self._voltar()
        elif evento.type == pygame.MOUSEMOTION:
            self.hover_pdf = self.btn_pdf_rect.collidepoint(evento.pos)
            self.hover_voltar = self.voltar_rect.collidepoint(evento.pos)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.btn_pdf_rect.collidepoint(evento.pos):
                self._acao_gerar_pdf()
            elif self.voltar_rect.collidepoint(evento.pos):
                self._voltar()

    def _voltar(self):
        if self.callback_voltar:
            self.callback_voltar()

    def _bloco_sob_mouse(self, pos):
        """Índice do bloco cuja pílula 'PERGUNTA N' está sob o mouse (ou -1)."""
        if not self.area.collidepoint(pos):
            return -1
        mx, my = pos
        y = self.area.top - self.scroll
        espaco = int(24 * self.altura / 606)
        for idx, b in enumerate(self.blocos):
            if self.pill_x <= mx <= self.pill_x + self.pill_largura and y <= my <= y + self.pill_altura:
                return idx
            y += b["altura"] + espaco
        return -1

    def _acao_gerar_pdf(self):
        try:
            caminho = gerar_pdf_relatorio(self.res)
            self.toast = ("PDF GERADO COM SUCESSO", COR_ACERTO, 60 * 4)
            if self.callback_pdf_gerado:
                self.callback_pdf_gerado(caminho)
            _abrir_arquivo_no_sistema(caminho)
        except Exception as e:  # noqa: BLE001 - nunca pode derrubar o jogo
            print(f"Erro ao gerar PDF: {e}")
            self.toast = ("ERRO AO GERAR PDF", COR_ERRO, 60 * 4)

    # ---------- desenho ----------
    def desenhar(self, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        self.hover_pdf = self.btn_pdf_rect.collidepoint(mouse_pos)
        self.hover_voltar = self.voltar_rect.collidepoint(mouse_pos)

        tela = self.screen
        tela.blit(self.fundo, (0, 0))
        tela.blit(self.painel, self.painel_rect.topleft)
        tela.blit(self.titulo, self.titulo_pos)
        tela.blit(self.score, self.score_pos)

        if self.sem_perguntas:
            tela.blit(self.sem_perguntas, self.sem_perguntas.get_rect(center=self.area.center))
        else:
            tela.set_clip(self.area)
            y = self.area.top - self.scroll
            espaco = int(24 * self.altura / 606)
            self.hover_idx = self._bloco_sob_mouse(mouse_pos)
            for idx, b in enumerate(self.blocos):
                if y + b["altura"] >= self.area.top and y <= self.area.bottom:
                    cab = b["cab_hover"] if idx == self.hover_idx else b["cab_normal"]
                    tela.blit(cab, (self.pill_x, y))
                    tela.blit(b["corpo"], (self.bloco_x, y + self.pill_altura + 8))
                y += b["altura"] + espaco
            tela.set_clip(None)

            if self.max_scroll > 0:
                trilho = pygame.Rect(self.area.right - 6, self.area.top, 5, self.area.height)
                pygame.draw.rect(tela, (255, 255, 255, 60), trilho, border_radius=3)
                frac = self.area.height / (self.max_scroll + self.area.height)
                alt_polegar = max(24, int(self.area.height * frac))
                pos_y = self.area.top + int(
                    (self.area.height - alt_polegar) * (self.scroll / self.max_scroll)
                )
                pygame.draw.rect(tela, (255, 255, 255), (trilho.x, pos_y, 5, alt_polegar), border_radius=3)

        tela.blit(self.btn_pdf_hover if self.hover_pdf else self.btn_pdf_normal, self.btn_pdf_rect)
        tela.blit(self.voltar_hover if self.hover_voltar else self.voltar_normal, self.voltar_rect)

        if self.toast:
            txt, cor, tempo = self.toast
            s = texto_contorno(txt, self.f_toast, cor, (10, 20, 40), esp=2)
            r = s.get_rect(center=(self.largura // 2, self.btn_pdf_rect.top - int(30 * self.altura / 606)))
            fundo = pygame.Surface((r.width + 24, r.height + 14), pygame.SRCALPHA)
            pygame.draw.rect(fundo, (20, 40, 70, 215), fundo.get_rect(), border_radius=10)
            tela.blit(fundo, (r.x - 12, r.y - 7))
            tela.blit(s, r)
            self.toast = (txt, cor, tempo - 1) if tempo > 1 else None