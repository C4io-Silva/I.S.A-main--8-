"""
Teste do SQLite de estatísticas e do relatório em PDF (banco temporário).

Cobre: criação das tabelas e migração de um banco antigo, sessões
independentes, registro de respostas, acertos/erros/percentual, sessão vazia,
acentos e símbolos fora do latin-1 (π, ₂, aspas curvas), texto longo com
quebra de página, resultado da campanha, falha de gravação sem derrubar o
jogo e fechamento da conexão. O estatisticas.db do projeto nunca é aberto.

Uso (a partir da raiz do projeto):
    python testes/teste_estatisticas.py
"""
import os
import sqlite3
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
TMP = tempfile.mkdtemp(prefix="isa_teste_est_")
os.environ["ISA_DB"] = os.path.join(TMP, "estatisticas.db")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from src.sistemas.estatisticas import Banco, gerar_pdf_relatorio  # noqa: E402


def ok(msg):
    print("ok:", msg)


def _paginas(caminho):
    with open(caminho, "rb") as f:
        return f.read().count(b"/Type /Page\n") or f.read().count(b"/Type /Page")


def main():
    db_real = os.path.join(RAIZ, "estatisticas.db")
    antes = os.path.getmtime(db_real) if os.path.exists(db_real) else None

    banco = Banco()
    assert banco.caminho == os.environ["ISA_DB"], "teste abriu o banco real"
    s1 = banco.nova_sessao("Joana Conceição")
    s2 = banco.nova_sessao("")
    assert s1 and s2 and s1 != s2
    alts = [("a", "π ≈ 3,14"), ("b", "H₂O"), ("c", "“aspas” — travessão"), ("d", "ç ã é ü")]
    banco.registrar_resposta(s1, 1, "Matemática", "Fácil", "Quanto vale π?", alts, "a", "a")
    banco.registrar_resposta(s1, 2, "Química", "Médio", "Fórmula da água?", alts, "b", "c")
    longo = ("Enunciado muito longo com acentuação — " * 120).strip()
    for i in range(3, 13):
        banco.registrar_resposta(s1, i, "História", "Difícil", longo, alts, "c", "c" if i % 2 else "")
    r = banco.buscar_resultado(s1)
    assert r["aluno"] == "Joana Conceição" and r["respondidas"] == 12
    assert r["acertos"] == 1 + 5, r["acertos"]
    assert banco.buscar_resultado(s2)["respondidas"] == 0, "sessões misturadas"
    ok("sessões independentes, respostas e contagem de acertos corretas")

    banco.marcar_resultado(s1, "vitoria")
    assert banco.buscar_resultado(s1)["resultado"] == "vitoria"
    pdf = gerar_pdf_relatorio(banco.buscar_resultado(s1), TMP)
    assert os.path.getsize(pdf) > 5000
    with open(pdf, "rb") as f:
        assert f.read().count(b"/Type /Page") >= 3, "texto longo deveria quebrar página"
    vazio = gerar_pdf_relatorio(banco.buscar_resultado(s2), TMP)
    assert os.path.getsize(vazio) > 1000
    vazio_sem_id = gerar_pdf_relatorio(banco.resultado_vazio("Sem Sessão"), TMP)
    assert os.path.exists(vazio_sem_id)
    ok("PDF com acentos/π/₂/aspas, texto longo em várias páginas, sessão vazia e sem id")

    # falha de gravação: conexão fechada não derruba o jogo
    banco.fechar()
    banco.registrar_resposta(s1, 99, "X", "Y", "Z", alts, "a", "a")   # só avisa
    assert banco.nova_sessao("x") is None
    try:
        banco.conn.execute("SELECT 1")
        raise AssertionError("conexão deveria estar fechada")
    except sqlite3.ProgrammingError:
        pass
    ok("falha de gravação (conexão fechada) só gera aviso; fechar() encerra a conexão")

    # migração de banco antigo (sem materia/dificuldade/resultado)
    antigo = os.path.join(TMP, "antigo.db")
    con = sqlite3.connect(antigo)
    con.execute("CREATE TABLE sessoes (id INTEGER PRIMARY KEY AUTOINCREMENT, aluno TEXT)")
    con.execute("CREATE TABLE respostas (id INTEGER PRIMARY KEY AUTOINCREMENT, sessao_id INTEGER,"
                " ordem INTEGER, enunciado TEXT, alternativas TEXT, acertou INTEGER)")
    con.execute("INSERT INTO sessoes (aluno) VALUES ('velho')")
    con.commit()
    con.close()
    b2 = Banco(antigo)
    assert {"materia", "dificuldade"} <= b2._colunas("respostas")
    assert {"data_hora", "resultado"} <= b2._colunas("sessoes")
    assert b2.buscar_resultado(1)["aluno"] == "velho", "migração perdeu dados"
    b2.fechar()
    ok("migração aditiva de banco antigo, sem perder dados")

    depois = os.path.getmtime(db_real) if os.path.exists(db_real) else None
    assert antes == depois, "o estatisticas.db real foi modificado"
    ok("estatisticas.db do projeto intocado")
    print("TODOS OS TESTES DE ESTATISTICAS PASSARAM")


if __name__ == "__main__":
    main()
