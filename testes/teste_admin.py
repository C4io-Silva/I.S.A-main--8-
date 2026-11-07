"""
Teste do ADMIN: senha 0000 e painel de perguntas (adicionar, editar, excluir,
buscar, rolar), sempre numa CÓPIA temporária dos CSVs — os do projeto não são
tocados.

Cobre:
  1. Banco: validação, adicionar/editar/excluir gravam no CSV (UTF-8 com BOM e
     ";"), o jogo (ler_perguntas) lê de volta, backup na 1ª gravação e
     desfazer na memória se o arquivo não puder ser gravado.
  2. Campo de texto: quebra de linha sem perder caractere, cursor, inserir no
     meio, apagar, máximo de caracteres.
  3. Tela de senha: errada avisa e limpa; 0000 abre o painel.
  4. Painel pelo mouse e teclado: lista, busca, rolagem, novo, editar (também
     com duplo clique), excluir com confirmação, ESC em cada modo.

Uso (a partir da raiz do projeto):
    python testes/teste_admin.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import pygame  # noqa: E402

if hasattr(pygame, "init"):
    pygame.init()

from src.admin import SENHA_ADMIN  # noqa: E402
from src.admin.banco import BancoAdmin, ErroSalvar  # noqa: E402
from src.admin.campos import Campo, quebrar  # noqa: E402
from src.admin.tela_perguntas import TelaPerguntas  # noqa: E402
from src.admin.tela_senha import TelaSenhaAdmin  # noqa: E402
from src.quiz.dados_csv import ler_perguntas  # noqa: E402

CABECALHO = ("disciplina;dificuldade;pergunta;opcao_a;opcao_b;opcao_c;opcao_d;"
             "opcao_e;resposta\r\n")
CSV_INICIAL = (
    CABECALHO
    + "Matemática;Fácil;Quanto é 2+2?;3;4;5;6;;B\r\n"
    + "História;Difícil;Quem chegou ao Brasil em 1500?;Cabral;Colombo;;;;A\r\n"
    + "Ruim;Fácil;;x;y;;;;A\r\n"            # enunciado vazio: o jogo ignora
)
TMP = Path(tempfile.mkdtemp(prefix="isa_teste_admin_"))


def ok(msg):
    print(f"OK  {msg}")


def nova_pasta(nome, professores=False):
    pasta = TMP / nome
    pasta.mkdir()
    (pasta / "perguntas.csv").write_bytes(("﻿" + CSV_INICIAL).encode("utf-8"))
    if professores:
        (pasta / "perguntas_professores.csv").write_bytes(
            ("﻿" + CABECALHO + "Física;Médio;Qual a unidade de força?;Newton;Joule;;;;A\r\n"
             ).encode("utf-8"))
    return pasta


def dados(**extra):
    base = {"disciplina": "Geo", "dificuldade_chave": "facil",
            "pergunta": "Capital da França?", "opcao_a": "Paris", "opcao_b": "Roma",
            "opcao_c": "", "opcao_d": "", "opcao_e": "", "resposta": "a"}
    base.update(extra)
    return base


# ══════════════════════════════════════════════════════════════════════════
# 1. BANCO
# ══════════════════════════════════════════════════════════════════════════
def teste_banco():
    pasta = nova_pasta("banco", professores=True)
    b = BancoAdmin(pasta)
    b.carregar()
    assert len(b.perguntas) == 3 and b.problemas == 1, (len(b.perguntas), b.problemas)

    # validações
    assert b.validar(dados(pergunta="")) == "DIGITE O ENUNCIADO DA PERGUNTA"
    assert "2 ALTERNATIVAS" in b.validar(dados(opcao_b=""))
    assert "RESPOSTA CORRETA" in b.validar(dados(resposta=""))
    assert "VAZIA" in b.validar(dados(resposta="c"))
    assert "IGUAL" in b.validar(dados(pergunta="quanto é 2+2?"))       # sem caixa/acento
    assert b.validar(dados()) is None
    ok("banco: validações (enunciado, 2 alternativas, gabarito, duplicada)")

    # adicionar -> vai para o perguntas.csv, antes das dos professores
    nova = b.adicionar(dados())
    assert b.perguntas.index(nova) == 2 and b.perguntas[3]["origem"] == "professor"
    lidas, problemas = ler_perguntas(str(pasta / "perguntas.csv"), origem="padrao")
    assert [p["pergunta"] for p in lidas][-1] == "Capital da França?"
    assert lidas[-1]["resposta"] == "a" and lidas[-1]["dificuldade_chave"] == "facil"
    assert problemas == [], problemas          # o arquivo regravado não tem linha ruim
    bruto = (pasta / "perguntas.csv").read_bytes()
    assert bruto.startswith(b"\xef\xbb\xbfdisciplina;dificuldade;pergunta"), bruto[:40]
    ok("banco: adicionar grava no CSV padrão (UTF-8 com BOM e ';') e o jogo lê de volta")

    # backup só na 1ª gravação
    backups = list((pasta / "backup").glob("perguntas_*.csv"))
    assert len(backups) == 1 and "Ruim" in backups[0].read_text("utf-8-sig")
    b.adicionar(dados(pergunta="Capital da Itália?", opcao_a="Milão", opcao_b="Roma",
                      resposta="b"))
    assert len(list((pasta / "backup").glob("perguntas_*.csv"))) == 1
    ok("banco: backup do arquivo original na 1ª gravação (e só nela)")

    # editar pergunta de professor: continua no arquivo dos professores
    prof = next(p for p in b.perguntas if p["origem"] == "professor")
    b.editar(prof, dados(pergunta="Unidade de força?", opcao_a="Joule", opcao_b="Newton",
                         resposta="b", dificuldade_chave="dificil", disciplina="Física"))
    lidas, _ = ler_perguntas(str(pasta / "perguntas_professores.csv"), origem="professor")
    assert len(lidas) == 1 and lidas[0]["pergunta"] == "Unidade de força?"
    assert lidas[0]["resposta"] == "b" and lidas[0]["dificuldade"] == "Difícil"
    # editar sem mudar o enunciado não conta como duplicada de si mesma
    b.editar(b.perguntas[0], dict(b.perguntas[0], disciplina="Mat"))
    ok("banco: editar mantém o arquivo de origem e não acusa duplicada contra si mesma")

    # excluir
    antes = len(b.perguntas)
    b.excluir(b.perguntas[0])
    b2 = BancoAdmin(pasta)
    b2.carregar()
    assert len(b.perguntas) == antes - 1 == len(b2.perguntas)
    assert all(p["pergunta"] != "Quanto é 2+2?" for p in b2.perguntas)
    ok("banco: excluir some do CSV")

    # não gravou -> desfaz na memória
    copia = list(b.perguntas)
    original = BancoAdmin.salvar

    def falha(self, origem):
        raise ErroSalvar("arquivo aberto")
    BancoAdmin.salvar = falha
    try:
        for acao in (lambda: b.adicionar(dados(pergunta="Outra?")),
                     lambda: b.excluir(b.perguntas[0]),
                     lambda: b.editar(b.perguntas[0], dados(pergunta="Mudou?"))):
            try:
                acao()
                raise AssertionError("devia ter falhado")
            except ErroSalvar:
                pass
            assert b.perguntas == copia
    finally:
        BancoAdmin.salvar = original
    ok("banco: se não der para gravar, a alteração é desfeita na memória")

    # CSV novo (sem arquivo): é criado
    vazia = TMP / "vazia"
    vazia.mkdir()
    b3 = BancoAdmin(vazia)
    b3.carregar()
    b3.adicionar(dados())
    assert (vazia / "perguntas.csv").exists() and not (vazia / "backup").exists()
    ok("banco: sem CSV ainda, o primeiro 'adicionar' cria o arquivo")


# ══════════════════════════════════════════════════════════════════════════
# 2. CAMPO DE TEXTO
# ══════════════════════════════════════════════════════════════════════════
def evento_tecla(tecla, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=tecla, mod=mod)


def teste_campo():
    fonte = pygame.font.SysFont("arial", 15)
    texto = ("Uma pergunta bem longa que precisa quebrar em varias linhas, "
             "inclusive_com_uma_palavra_gigante_sem_espacos_que_nao_cabe_na_linha_sozinha ok")
    for largura in (60, 120, 240, 500):
        linhas = quebrar(texto, fonte, largura)
        assert linhas[0][0] == 0 and linhas[-1][1] == len(texto)
        for (_, fim), (ini, _) in zip(linhas, linhas[1:]):
            assert fim == ini, "linhas devem ser contíguas"
        for ini, fim in linhas:
            assert fim > ini
            assert fonte.size(texto[ini:fim])[0] <= largura or fim - ini == 1
    assert quebrar("", fonte, 100) == [(0, 0)]
    ok("campo: quebra de linha cobre o texto inteiro, sem perder caractere")

    c = Campo((0, 0, 300, 32), 10, fonte)
    c.inserir("abcdef")
    c.tecla(evento_tecla(pygame.K_LEFT))
    c.tecla(evento_tecla(pygame.K_LEFT))
    c.inserir("XY")
    assert c.texto == "abcdXYef" and c.cursor == 6
    c.tecla(evento_tecla(pygame.K_BACKSPACE))
    c.tecla(evento_tecla(pygame.K_DELETE))
    assert c.texto == "abcdYf" or c.texto == "abcdXf", c.texto
    c.tecla(evento_tecla(pygame.K_HOME))
    assert c.cursor == 0
    c.tecla(evento_tecla(pygame.K_END))
    c.inserir("1234567890")
    assert len(c.texto) == 10                      # máximo respeitado
    c.definir("")
    c.inserir("linha1\nlinha2\tfim")
    assert "\n" not in c.texto and "\t" not in c.texto
    ok("campo: cursor, inserir no meio, apagar, Home/End, máximo e sem quebra de linha")

    m = Campo((0, 0, 200, 80), 500, fonte, multilinha=True)
    m.inserir(texto)
    m.tecla(evento_tecla(pygame.K_UP))
    m.tecla(evento_tecla(pygame.K_DOWN))
    m.tecla(evento_tecla(pygame.K_HOME))
    m.clique((50, 10))
    assert 0 <= m.cursor <= len(texto)
    ok("campo: várias linhas (cima/baixo/Home/clique) sem erro")


# ══════════════════════════════════════════════════════════════════════════
# 3. TELA DE SENHA
# ══════════════════════════════════════════════════════════════════════════
def clique(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)


def texto_evt(txt):
    return pygame.event.Event(pygame.TEXTINPUT, text=txt)


def teste_senha():
    assert SENHA_ADMIN == "0000"
    tela = pygame.Surface((1067, 600))
    fundo = pygame.Surface((1067, 600))
    destino = []
    voltou = []
    s = TelaSenhaAdmin(tela, fundo, callback_voltar=lambda: voltou.append(1),
                       callback_sucesso=lambda: destino.append("ADMIN"))
    s.resetar()

    s.handle_event(evento_tecla(pygame.K_RETURN))             # vazio
    assert s.mensagem == "DIGITE A SENHA!" and not destino
    s.handle_event(texto_evt("1234"))
    s.handle_event(evento_tecla(pygame.K_RETURN))
    assert s.mensagem == "SENHA INCORRETA!" and s.campo.texto == "" and not destino
    s.handle_event(texto_evt("0000"))
    assert s.mensagem == ""                                    # digitar limpa o aviso
    s.desenhar((0, 0))
    s.handle_event(clique(s.btn_entrar.rect.center))           # clique em ENTRAR
    assert destino == ["ADMIN"]
    s.handle_event(evento_tecla(pygame.K_ESCAPE))
    s.handle_event(clique(s.btn_voltar.rect.center))
    assert len(voltou) == 2
    ok("senha: errada avisa e limpa; 0000 (Enter ou botão ENTRAR) abre o painel; ESC/seta voltam")


# ══════════════════════════════════════════════════════════════════════════
# 4. PAINEL
# ══════════════════════════════════════════════════════════════════════════
def digitar(t, campo_txt):
    t.handle_event(texto_evt(campo_txt))


def teste_painel():
    pasta = nova_pasta("painel", professores=True)
    tela = pygame.Surface((1067, 600))
    fundo = pygame.Surface((1067, 600))
    saiu = []
    t = TelaPerguntas(tela, fundo, callback_voltar=lambda: saiu.append(1),
                      banco=BancoAdmin(pasta))
    t.recarregar()
    assert t.modo == "lista" and len(t.filtrados) == 3 and t.sel is t.filtrados[0]
    t.desenhar((10, 10))

    # ── novo (pelo mouse) ────────────────────────────────────────────────
    t.handle_event(clique(t.btn_adicionar.rect.center))
    assert t.modo == "editor" and t.alvo_edicao is None
    t.desenhar((10, 10))
    t.handle_event(clique(t.btn_salvar.rect.center))           # tudo vazio
    assert t.modo == "editor" and "ENUNCIADO" in t.erro
    digitar(t, "Qual é a capital da França?")                  # foco já na pergunta
    t.handle_event(evento_tecla(pygame.K_TAB))                 # -> alternativa A
    digitar(t, "Paris")
    t.handle_event(evento_tecla(pygame.K_RETURN))              # -> B
    digitar(t, "Roma")
    t.handle_event(clique(t.btn_salvar.rect.center))
    assert "RESPOSTA CORRETA" in t.erro and t.modo == "editor"
    t.handle_event(clique(t.badges["a"].center))               # letra certa
    t.handle_event(clique(t.seg_nivel["dificil"].center))      # dificuldade
    t.handle_event(clique(t.campo_disc.rect.center))
    digitar(t, "Geografia")
    t.desenhar((10, 10))
    t.handle_event(evento_tecla(pygame.K_s, pygame.KMOD_CTRL))  # Ctrl+S
    assert t.modo == "lista" and t.sel["pergunta"].startswith("Qual é a capital")
    assert t.sel["dificuldade_chave"] == "dificil" and t.sel["disciplina"] == "Geografia"
    lidas, _ = ler_perguntas(str(pasta / "perguntas.csv"), origem="padrao")
    assert lidas[-1]["pergunta"] == "Qual é a capital da França?"
    assert lidas[-1]["resposta"] == "a"
    ok("painel: nova pergunta (validações, letra certa, dificuldade, Ctrl+S) grava no CSV")

    # ── cancelar não grava ───────────────────────────────────────────────
    tamanho = (pasta / "perguntas.csv").stat().st_size
    t.handle_event(clique(t.btn_adicionar.rect.center))
    digitar(t, "Pergunta que será descartada")
    t.handle_event(evento_tecla(pygame.K_ESCAPE))
    assert t.modo == "lista" and (pasta / "perguntas.csv").stat().st_size == tamanho
    ok("painel: ESC no editor descarta sem gravar")

    # ── editar (botão e duplo clique) ────────────────────────────────────
    t.sel = t.filtrados[0]
    t.handle_event(clique(t.btn_editar.rect.center))
    assert t.modo == "editor" and t.campo_perg.texto == "Quanto é 2+2?"
    assert t.dados_edicao["resposta"] == "b"
    t.handle_event(clique(t.campo_perg.rect.center))
    t.handle_event(evento_tecla(pygame.K_END))
    digitar(t, " (revisada)")
    t.handle_event(clique(t.btn_salvar.rect.center))
    assert t.modo == "lista" and t.sel["pergunta"] == "Quanto é 2+2? (revisada)"
    assert t.sel["resposta"] == "b"
    a = t.lista_area
    linha1 = (a.x + 50, a.y + t.linha_h + 5)                    # 2ª linha da lista
    t.handle_event(clique(linha1))
    assert t.modo == "lista" and t.sel is t.filtrados[1]
    t.handle_event(clique(linha1))                              # duplo clique
    assert t.modo == "editor" and t.alvo_edicao is t.filtrados[1]
    t.handle_event(evento_tecla(pygame.K_ESCAPE))
    ok("painel: editar por botão e por duplo clique; salvar mantém o gabarito")

    # ── busca ────────────────────────────────────────────────────────────
    digitar(t, "brasil")
    assert len(t.filtrados) == 1 and "Brasil" in t.filtrados[0]["pergunta"]
    t.handle_event(evento_tecla(pygame.K_ESCAPE))               # 1º ESC limpa a busca
    assert t.busca.texto == "" and len(t.filtrados) == len(t.banco.perguntas)
    assert not saiu
    digitar(t, "zzzz")
    assert t.filtrados == [] and t.sel is None
    t.desenhar((0, 0))                                          # lista vazia desenha
    t.handle_event(evento_tecla(pygame.K_ESCAPE))
    ok("painel: busca filtra (sem acento/caixa); ESC limpa a busca antes de sair")

    # ── excluir com confirmação ──────────────────────────────────────────
    total = len(t.banco.perguntas)
    t.sel = t.filtrados[0]
    pergunta_excluida = t.sel["pergunta"]
    t.handle_event(clique(t.btn_excluir.rect.center))
    assert t.modo == "confirmar"
    t.desenhar((0, 0))
    t.handle_event(clique(t.btn_nao.rect.center))
    assert t.modo == "lista" and len(t.banco.perguntas) == total
    t.handle_event(clique(t.btn_excluir.rect.center))
    t.handle_event(evento_tecla(pygame.K_ESCAPE))
    assert t.modo == "lista" and len(t.banco.perguntas) == total
    t.handle_event(clique(t.btn_excluir.rect.center))
    t.handle_event(clique(t.btn_sim.rect.center))
    assert t.modo == "lista" and len(t.banco.perguntas) == total - 1
    b2 = BancoAdmin(pasta)
    b2.carregar()
    assert all(p["pergunta"] != pergunta_excluida for p in b2.perguntas)
    assert t.sel is not None
    ok("painel: excluir só depois do SIM (NAO e ESC cancelam) e some do CSV")

    # ── muitas perguntas: rolagem, barra e teclado ──────────────────────
    for i in range(40):
        t.banco.adicionar(dados(pergunta=f"Pergunta numero {i}?", opcao_a=f"A{i}",
                                opcao_b=f"B{i}"))
    t._filtrar()
    assert t._thumb() is not None and t._max_scroll() > 0
    t.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-3))
    assert t.scroll == 6
    t.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=10))
    assert t.scroll == 0
    thumb = t._thumb()
    t.handle_event(clique(thumb.center))                         # pega a barra
    t.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(thumb.centerx, thumb.centery + 80),
                                      rel=(0, 80), buttons=(1, 0, 0)))
    assert t.scroll > 0
    t.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(0, 0), button=1))
    assert t._arrastando is None
    for _ in range(60):
        t.handle_event(evento_tecla(pygame.K_DOWN))
    assert t.sel is t.filtrados[min(len(t.filtrados) - 1, t._indice_sel())]
    assert t.scroll <= t._indice_sel() < t.scroll + t.visiveis   # seleção sempre à vista
    t.handle_event(evento_tecla(pygame.K_PAGEUP))
    t.desenhar((100, 200))
    ok("painel: rolagem por roda, barra arrastável e setas mantêm a seleção à vista")

    # ── pergunta nova escondida pela busca: a busca é limpa ──────────────
    digitar(t, "numero 1")
    t.handle_event(clique(t.btn_adicionar.rect.center))
    digitar(t, "Totalmente diferente?")
    t.handle_event(evento_tecla(pygame.K_TAB))
    digitar(t, "sim")
    t.handle_event(evento_tecla(pygame.K_TAB))
    digitar(t, "nao")
    t.handle_event(clique(t.badges["a"].center))
    t.handle_event(clique(t.btn_salvar.rect.center))
    assert t.modo == "lista" and t.sel["pergunta"] == "Totalmente diferente?"
    assert t.busca.texto == ""
    ok("painel: pergunta nova que a busca escondia aparece selecionada")

    # ── arquivo que não grava: avisa, segue no editor ───────────────────
    original = BancoAdmin.salvar
    BancoAdmin.salvar = lambda self, origem: (_ for _ in ()).throw(ErroSalvar("aberto"))
    try:
        t.handle_event(clique(t.btn_adicionar.rect.center))
        digitar(t, "Não vai gravar?")
        t.handle_event(evento_tecla(pygame.K_TAB))
        digitar(t, "a")
        t.handle_event(evento_tecla(pygame.K_TAB))
        digitar(t, "b")
        t.handle_event(clique(t.badges["a"].center))
        n = len(t.banco.perguntas)
        t.handle_event(clique(t.btn_salvar.rect.center))
        assert t.modo == "editor" and "EXCEL" in t.erro and len(t.banco.perguntas) == n
    finally:
        BancoAdmin.salvar = original
    t.handle_event(evento_tecla(pygame.K_ESCAPE))
    t.tecla_voltar()
    assert saiu == [1]
    ok("painel: CSV aberto no Excel -> avisa e não perde nem duplica nada; ESC sai do painel")


if __name__ == "__main__":
    try:
        teste_banco()
        teste_campo()
        teste_senha()
        teste_painel()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    print("TODOS OS TESTES DO ADMIN PASSARAM")
