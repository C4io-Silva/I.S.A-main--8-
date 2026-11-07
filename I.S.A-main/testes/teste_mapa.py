"""
Teste do mapa: CSV em disco, parser e gerador precisam concordar.

  1. Cada CSV de setor em disco é a saída do gerar_mundo.py OU uma edição
     manual registrada — e, nos dois casos, é jogável (alcance, sem poço-
     armadilha). Antes este teste exigia CSV == gerador, o que tornava
     QUALQUER edição manual um erro (e o gerador a apagava em silêncio).
  1b. O gerador não sobrescreve um CSV editado à mão (só com --sobrescrever,
     e com backup).
  2. A validação completa do gerador passa (alcance, armadilhas, entidades,
     encontros, arena do boss).
  3. O parser lê os marcadores de cada setor, toda passagem tem chegada no
     setor de destino, e CSV malformado gera erro com linha/coluna.

Uso (a partir da raiz do projeto):
    python testes/teste_mapa.py
"""
import contextlib
import io
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

from src.nucleo import constants  # noqa: E402
from src.mundo import nivel_dados  # noqa: E402
from src.nucleo.utils import ErroMapa, carregar_nivel_csv, extrair_marcadores  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    import ferramentas.dados.gerar_mundo as G  # noqa: E402  (monta a grade ao importar)


def _ler(nome):
    return carregar_nivel_csv(os.path.join(constants.PASTA_SETORES,
                                           constants.SETORES[nome]["arquivo"]))


def _digital(grade):
    return G.impressao_digital(grade)


def _manifesto():
    import json
    caminho = os.path.join(RAIZ, "assets", "levels", constants.PASTA_SETORES, "_gerado.json")
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


EDITADOS = set()


def teste_csv_gerado_ou_edicao_valida():
    from src.mundo import validacao_mapa as val
    G.carimbar_marcadores()
    manifesto = _manifesto()
    for nome, grade_gerador in G.fatiar_setores().items():
        arquivo = constants.SETORES[nome]["arquivo"]
        em_disco = _ler(nome)
        if em_disco == grade_gerador:
            continue
        # Diferente do gerador: tem que ser uma edição manual (o gerador
        # nunca grava algo diferente do que registrou no manifesto)...
        assert manifesto.get(arquivo) != _digital(em_disco), (
            f"{arquivo} difere do gerador mas consta como gerado — rode python gerar_mundo.py")
        EDITADOS.add(nome)
        # ...e a edição precisa continuar jogável.
        copia = [list(l) for l in em_disco]
        m = extrair_marcadores(copia)
        info = nivel_dados.SETORES_GERADOS[nome]
        problemas = val.validar_csv(em_disco) + val.validar_regiao(
            copia, nome, 0, len(copia[0]) - 1, info["entrada_col"], info["entrada_row"])
        assert not problemas, f"{arquivo} (editado à mão) ficou injogável: {problemas}"
        assert m["passagens"] or nome == constants.SETOR_INICIAL
    print(f"ok: CSVs = gerador ou edição manual válida (editados: {sorted(EDITADOS) or 'nenhum'})")


def teste_gerador_preserva_edicao_manual():
    import pathlib
    import shutil
    with tempfile.TemporaryDirectory() as tmp:
        raiz = pathlib.Path(tmp)
        pasta = raiz / "assets" / "levels" / constants.PASTA_SETORES
        pasta.mkdir(parents=True)
        grades = G.fatiar_setores()
        with contextlib.redirect_stdout(io.StringIO()):
            G.gravar_setores(raiz, grades)                     # 1ª geração
        alvo = pasta / constants.SETORES["arena"]["arquivo"]
        texto = alvo.read_text(encoding="utf-8-sig").replace("-1", "2", 1)  # edição manual
        alvo.write_text(texto, encoding="utf-8-sig")
        with contextlib.redirect_stdout(io.StringIO()):
            protegidos = G.gravar_setores(raiz, grades)        # regerar
        assert alvo.name in protegidos, "gerador sobrescreveu a edição manual"
        assert alvo.read_text(encoding="utf-8-sig") == texto, "edição manual perdida"
        assert (raiz / "assets" / "levels" / "gerados" / alvo.name).exists()
        with contextlib.redirect_stdout(io.StringIO()):
            protegidos = G.gravar_setores(raiz, grades, sobrescrever=True)
        assert not protegidos and alvo.read_text(encoding="utf-8-sig") != texto
        assert list((raiz / "assets" / "levels" / "backup").glob("arena_*.csv")), "sem backup"
        shutil.rmtree(raiz / "assets")
    print("ok: gerador preserva CSV editado à mão (e só troca com --sobrescrever + backup)")


def teste_validacao_do_gerador():
    problemas = (G.validar() + G.validar_encontros(G.CELULA_CHEGADA)
                 + G.validar_ligacoes(G.fatiar_setores()))
    assert not problemas, "\n".join(problemas)
    print("ok: validacao completa do mapa e das ligacoes entre setores")


def teste_marcadores_por_setor():
    lidos = {}
    for nome in constants.SETORES:
        grade = _ler(nome)
        info = nivel_dados.SETORES_GERADOS[nome]
        assert (len(grade), len(grade[0])) == (info["linhas"], info["colunas"]), nome
        lidos[nome] = extrair_marcadores(grade)
        restos = {v for linha in grade for v in linha} & constants.TILES_MARCADORES
        assert not restos, f"{nome}: marcadores ficaram na grade: {restos}"

    assert lidos[constants.SETOR_INICIAL]["player"] is not None
    assert all(m["player"] is None for n, m in lidos.items() if n != constants.SETOR_INICIAL)
    if not EDITADOS:
        # As contagens só batem com o gerador se ninguém editou os CSVs.
        assert sum(len(m["inimigos"]) for m in lidos.values()) == len(G.inimigos)
        assert sum(len(m["minerios"]) for m in lidos.values()) == len(G.minerios)
    for nome, m in lidos.items():
        for destino in m["passagens"].values():
            assert destino["chegada"] in lidos[destino["setor"]]["chegadas"], (
                f"{nome}: passagem sem chegada em {destino['setor']}")
    arena = lidos[nivel_dados.AREA_BOSS["setor"]]
    assert arena["area_boss"] == nivel_dados.AREA_BOSS["marcador"]
    assert not arena["inimigos"] and not arena["minerios"], "arena deveria estar vazia"
    resumo = ", ".join(f"{n}: {len(m['inimigos'])} mobs/{len(m['minerios'])} min"
                       for n, m in lidos.items())
    print(f"ok: marcadores por setor ({resumo})")


def teste_csv_malformado():
    casos = {
        "valor nao numerico": "0,0,-1\n0,x,0\n",
        "larguras diferentes": "0,0,-1\n0,0\n",
        "vazio": "\n\n",
        "ponto e virgula com letra": "0;0;-1\n0;x;0\n",
    }
    for nome, conteudo in casos.items():
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(conteudo)
        try:
            carregar_nivel_csv(f.name)  # caminho absoluto ignora a pasta levels/
        except ErroMapa as erro:
            assert "linha" in str(erro) or "vazio" in str(erro) or "larguras" in str(erro)
        else:
            raise AssertionError(f"CSV malformado aceito: {nome}")
        finally:
            os.unlink(f.name)
    print("ok: CSV malformado gera ErroMapa com o local do problema")


def teste_csv_salvo_pelo_excel():
    """O mesmo mapa salvo como o Excel/LibreOffice salvam é lido igual."""
    grade = [[0, -1, 91], [1, 2, -1]]
    formatos = {
        "virgula utf-8": ("0,-1,91\n1,2,-1\n", "utf-8"),
        "ponto e virgula com BOM (Excel pt-BR)": ("0;-1;91\r\n1;2;-1\r\n", "utf-8-sig"),
        "ANSI com separador sobrando": ("0;-1;91;\n1;2;-1;\n", "cp1252"),
        "espacos nas celulas": (" 0 , -1 , 91\n1,2, -1\n", "utf-8"),
    }
    for nome, (conteudo, cod) in formatos.items():
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                         encoding=cod, newline="") as f:
            f.write(conteudo)
        try:
            assert carregar_nivel_csv(f.name) == grade, nome
        finally:
            os.unlink(f.name)
    print("ok: CSV de mapa salvo por Excel/LibreOffice/editor (',' ou ';', BOM, ANSI) é lido")


if __name__ == "__main__":
    teste_csv_gerado_ou_edicao_valida()
    teste_gerador_preserva_edicao_manual()
    teste_validacao_do_gerador()
    teste_marcadores_por_setor()
    teste_csv_malformado()
    teste_csv_salvo_pelo_excel()
    print("TODOS OS TESTES DE MAPA PASSARAM")