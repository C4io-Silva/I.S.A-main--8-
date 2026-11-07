"""
Teste do problema "os CSVs não aceitam edição": edita, salva (do jeito que
Excel, LibreOffice e Bloco de Notas salvam), recarrega e confere que o JOGO
usa o dado novo.

Tudo acontece numa CÓPIA da pasta assets/ (utils.ASSETS_PATH é apontado
para ela): os CSVs originais do projeto não são tocados.

Cobre:
  1. perguntas.csv salvo pelo Excel pt-BR (ANSI/cp1252, ";" e CRLF) com uma
     pergunta editada -> o jogo lê a edição.
  2. "CSV UTF-8" do Excel (BOM + vírgula) e do LibreOffice (UTF-8 + ";").
  3. perguntas_professores.csv com o cabeçalho quebrado "\\xef\\xbb\\xbfpergunta"
     e dificuldade "Professor" -> carregado e presente nas fases 1 e 2.
  4. Validações: colunas ausentes, linha incompleta, gabarito inválido ou
     vazio, duplicada, arquivo vazio — o problema é apontado com a linha e
     as linhas boas continuam valendo.
  5. Ciclo completo no jogo: editar o CSV com o jogo aberto -> JOGAR de novo
     -> o quiz aberto pelo minério mostra a pergunta editada.
  6. Mapa: um minério acrescentado à mão no floresta.csv (salvo com ";")
     aparece no setor ao iniciar a partida; um marcador desconhecido é
     acusado pelo validar_dados.py.

Uso (a partir da raiz do projeto):
    python testes/teste_csv_edicao.py
"""
import contextlib
import csv
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
TMP = Path(tempfile.mkdtemp(prefix="isa_teste_csv_"))
os.environ["ISA_DB"] = str(TMP / "estatisticas.db")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pygame  # noqa: E402

from src.nucleo import utils  # noqa: E402

# ── cópia isolada de assets/ ───────────────────────────────────────────────
ASSETS_TMP = TMP / "assets"
ASSETS_TMP.mkdir()
for nome in os.listdir(utils.ASSETS_PATH):
    origem = utils.ASSETS_PATH / nome
    destino = ASSETS_TMP / nome
    # Cópias temporárias evitam WinError 1314 (symlink requer privilégio
    # especial em instalações padrão do Windows).
    if origem.is_dir():
        shutil.copytree(origem, destino)
    else:
        shutil.copy2(origem, destino)
utils.ASSETS_PATH = ASSETS_TMP
BANCO = ASSETS_TMP / "banco de dados"

from src.nucleo import constants  # noqa: E402
from compat_main import M  # noqa: E402
from src.quiz.dados_csv import ler_perguntas  # noqa: E402
from src.sistemas.joystick import GerenciadorJoystick  # noqa: E402


def ok(msg):
    print("ok:", msg)


def _linhas_do_banco():
    with open(BANCO / "perguntas.csv", encoding="utf-8-sig", newline="") as f:
        # o perguntas.csv tem uma linha em branco após o cabeçalho: ignorada aqui
        return [linha for linha in csv.reader(f, delimiter=";") if linha]


def _gravar(caminho, linhas, encoding, sep, eol="\n"):
    # errors="replace": é o que o Excel faz ao salvar em ANSI — caracteres
    # fora do cp1252 (π, ₂, ⁺...) viram "?". Por isso o README recomenda
    # "CSV UTF-8"; o arquivo é entregue com BOM, que o Excel preserva.
    with open(caminho, "w", encoding=encoding, newline="", errors="replace") as f:
        csv.writer(f, delimiter=sep, lineterminator=eol).writerows(linhas)


def teste_excel_ptbr_ansi():
    linhas = _linhas_do_banco()
    total = len(linhas) - 1
    linhas[1][2] = "Pergunta EDITADA no Excel: quanto é 6 × 7? (ç, ã, é)"
    linhas[1][3:8] = ["40", "41", "42", "43", "44"]
    linhas[1][8] = "c"
    destino = TMP / "excel_ansi.csv"
    _gravar(destino, linhas, "cp1252", ";", "\r\n")
    perguntas, problemas = ler_perguntas(str(destino))
    assert len(perguntas) == total, (len(perguntas), total, problemas[:3])
    assert perguntas[0]["pergunta"].startswith("Pergunta EDITADA no Excel")
    assert perguntas[0]["opcao_c"] == "42" and perguntas[0]["resposta"] == "c"
    ok(f"Excel pt-BR (ANSI, ';', CRLF): {total} perguntas lidas, edição com acentos preservada")


def teste_utf8_bom_e_libreoffice():
    linhas = _linhas_do_banco()
    total = len(linhas) - 1
    for nome, enc, sep in (("utf8_bom_virgula.csv", "utf-8-sig", ","),
                           ("libreoffice.csv", "utf-8", ";"),
                           ("tab.csv", "utf-8", "\t")):
        _gravar(TMP / nome, linhas, enc, sep)
        perguntas, problemas = ler_perguntas(str(TMP / nome))
        assert len(perguntas) == total and not problemas, (nome, problemas[:3])
    ok("UTF-8 com BOM + vírgula, UTF-8 + ';' e TAB: mesmo banco, sem perder coluna")


def teste_professores_cabecalho_quebrado_e_dificuldade():
    caminho = TMP / "prof.csv"
    caminho.write_text(
        "\\xef\\xbb\\xbfpergunta,alt_a,alt_b,alt_c,alt_d,correta,categoria\n"
        "Quanto é 3+3?,5,6,7,8,b,Matemática\n", encoding="utf-8")
    perguntas = utils.carregar_perguntas_professores(caminho)
    assert len(perguntas) == 1 and perguntas[0]["pergunta"] == "Quanto é 3+3?"
    assert perguntas[0]["dificuldade_chave"] == "medio"
    # "Professor" como dificuldade (como o loader antigo gravava)
    caminho.write_text("pergunta;alt_a;alt_b;correta;dificuldade\n"
                       "Cor do céu?;Azul;Verde;a;Professor\n", encoding="utf-8")
    perguntas = utils.carregar_perguntas_professores(caminho)
    assert perguntas and perguntas[0]["dificuldade_chave"] == "medio"
    for fase in (1, 2):
        M._ids_respondidas.clear()
        filtradas = M.filtrar_perguntas_por_fase(perguntas + M.carregar_perguntas(), fase)
        assert perguntas[0] in filtradas, f"pergunta de professor sumiu da fase {fase}"
    ok("professores: cabeçalho com BOM literal lido; 'Professor' vira Médio e entra nas fases 1 e 2")


def teste_validacoes():
    casos = {
        "colunas ausentes": ("disciplina;pergunta;opcao_a\nX;Y;Z\n", "colunas obrigatórias"),
        "vazio": ("", "vazio"),
    }
    for nome, (conteudo, esperado) in casos.items():
        (TMP / "v.csv").write_text(conteudo, encoding="utf-8")
        perguntas, problemas = ler_perguntas(str(TMP / "v.csv"))
        assert not perguntas and any(esperado in p for p in problemas), (nome, problemas)
    conteudo = (
        "disciplina;dificuldade;pergunta;opcao_a;opcao_b;opcao_c;opcao_d;opcao_e;resposta\n"
        "Mat;Fácil;Boa 1;1;2;3;4;;a\n"
        "Mat;Fácil;Sem gabarito;1;2;3;4;;x\n"
        "Mat;Fácil;Gabarito vazio;1;2;3;4;;e\n"
        "Mat;Fácil;;1;2;3;4;;a\n"
        "Mat;Fácil;Incompleta;1\n"
        "Mat;Fácil;Boa 1;1;2;3;4;;a\n"
        "Mat;Medio;Boa 2;1;2;3;4;;b\n"
    )
    (TMP / "v.csv").write_text(conteudo, encoding="utf-8")
    perguntas, problemas = ler_perguntas(str(TMP / "v.csv"))
    textos = " | ".join(problemas)
    assert [p["pergunta"] for p in perguntas] == ["Boa 1", "Boa 2"], perguntas
    for trecho in ("linha 3: gabarito inválido", "linha 4: gabarito 'E' aponta",
                   "linha 5: pergunta vazia", "linha 6: menos de 2 alternativas",
                   "linha 7: pergunta duplicada"):
        assert trecho in textos, (trecho, problemas)
    ok("validação aponta linha a linha (gabarito, vazio, incompleta, duplicada) e mantém as boas")


def preparar_jogo():
    pygame.init()
    M.configurar_janela()
    M.clock = pygame.time.Clock()
    M.gamepad = GerenciadorJoystick()
    M.recriar_ui()


def teste_ciclo_completo_no_jogo():
    """Edita o CSV com o jogo aberto, clica JOGAR e coleta um minério."""
    preparar_jogo()
    with contextlib.redirect_stdout(io.StringIO()):
        M.iniciar_jogo()
    antes = len(M.todas_perguntas)
    cab = ["disciplina", "dificuldade", "pergunta", "opcao_a", "opcao_b",
           "opcao_c", "opcao_d", "opcao_e", "resposta"]
    novas = [cab] + [
        ["Biologia", "Fácil", f"PERGUNTA NOVA {i} feita pelo professor no Excel?",
         "sim", "não", "talvez", "nunca", "", "a"] for i in range(3)
    ]
    _gravar(BANCO / "perguntas.csv", novas, "cp1252", ";", "\r\n")   # Excel pt-BR
    # Só o banco editado nesta partida: a pergunta de exemplo dos professores
    # (Geografia, priorizada na floresta) poderia sair antes das novas.
    (BANCO / "perguntas_professores.csv").unlink()
    with contextlib.redirect_stdout(io.StringIO()):
        M.iniciar_jogo()                                              # JOGAR de novo
    textos = {p["pergunta"] for p in M.todas_perguntas}
    assert {f"PERGUNTA NOVA {i} feita pelo professor no Excel?" for i in range(3)} <= textos
    assert len(M.todas_perguntas) < antes, "o jogo ainda usa o banco antigo"
    minerio = M.itens[0]
    M.player.rect.center = minerio.rect.center
    M.player.pos_x, M.player.pos_y = float(M.player.rect.x), float(M.player.rect.y)
    M._verificar_coletas()
    assert M.estado_jogo == "QUIZ"
    assert M.pergunta_em_jogo()["pergunta"].startswith("PERGUNTA NOVA"), M.pergunta_em_jogo()
    M.processar_resposta("a")
    assert "ACERTOU" in M.quiz_mensagem and minerio not in M.itens
    ok("CSV editado (Excel pt-BR) com o jogo aberto -> JOGAR -> o minério abre a pergunta nova")


def teste_cancelar_quiz_nao_consome_minerio():
    minerio = M.itens[0]
    M.player.rect.center = minerio.rect.center
    M._verificar_coletas()
    assert M.estado_jogo == "QUIZ"
    M.cancelar_quiz()
    assert M.estado_jogo == "JOGANDO" and minerio in M.itens and not minerio.coletado
    M._verificar_coletas()
    assert M.estado_jogo == "JOGANDO", "reabriu o quiz no mesmo instante"
    ok("ESC no quiz devolve o minério ao mapa (não é consumido em silêncio)")


def teste_edicao_de_mapa_no_jogo():
    arquivo = ASSETS_TMP / "levels" / constants.PASTA_SETORES / "floresta.csv"
    grade = utils.carregar_nivel_csv(str(arquivo))
    spawn = next((c, l) for l, linha in enumerate(grade) for c, v in enumerate(linha)
                 if v == constants.TILE_PLAYER_SPAWN)
    col, lin = spawn[0] + 6, spawn[1]
    assert grade[lin][col] == -1 and grade[lin + 1][col] in constants.SOLID_TILES
    grade[lin][col] = constants.TILE_MINERIO           # minério novo, à mão
    _gravar(arquivo, grade, "utf-8-sig", ";", "\r\n")
    with contextlib.redirect_stdout(io.StringIO()):
        M.iniciar_jogo()
    T = constants.TILE_SIZE
    assert any(m.rect.centerx == col * T + T // 2 for m in M.setores["floresta"].itens), \
        "minério acrescentado no CSV não apareceu no jogo"
    # marcador desconhecido é acusado pelo validador
    grade[lin][col] = 77
    _gravar(arquivo, grade, "utf-8-sig", ";")
    from ferramentas.dados import validar_dados
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        codigo = validar_dados.main()
    assert codigo == 1 and "id 77" in saida.getvalue(), saida.getvalue()[-600:]
    ok("mapa editado à mão (';' + BOM) é usado ao iniciar; ID desconhecido é acusado pelo validador")


if __name__ == "__main__":
    teste_excel_ptbr_ansi()
    teste_utf8_bom_e_libreoffice()
    teste_professores_cabecalho_quebrado_e_dificuldade()
    teste_validacoes()
    teste_ciclo_completo_no_jogo()
    teste_cancelar_quiz_nao_consome_minerio()
    teste_edicao_de_mapa_no_jogo()
    M.banco_estatisticas.fechar()
    print("TODOS OS TESTES DE EDICAO DE CSV PASSARAM")
