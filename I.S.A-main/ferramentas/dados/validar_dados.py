"""
Valida TODOS os CSVs editáveis do I.S.A. — rode depois de editar qualquer um.

    python validar_dados.py                 # valida perguntas e mapas
    python validar_dados.py --padronizar    # reescreve os CSVs no formato
                                            # padrão (UTF-8 com BOM, ";"),
                                            # com backup, sem mudar conteúdo

O que é verificado
------------------
Perguntas (assets/banco de dados/perguntas.csv e perguntas_professores.csv):
  colunas obrigatórias, linhas incompletas, gabarito inválido ou apontando
  para alternativa vazia, perguntas duplicadas, dificuldade desconhecida,
  codificação e separador detectados, quantas perguntas cada fase recebe.

Mapas (assets/levels/setores/*.csv, um por setor de constants.SETORES):
  arquivo presente e legível, grade retangular, IDs desconhecidos, marcador
  de spawn só no setor inicial, toda passagem com chegada no setor de
  destino, minérios/inimigos com chão de verdade e sem bloco por cima,
  alcance (toda plataforma alcançável e sem poço-armadilha), marcador do
  boss na arena, e se o CSV está igual ao gerador ou foi editado à mão.

Sai com código 1 se houver ERRO (o jogo não abriria ou o quiz perderia
perguntas); AVISOS não bloqueiam.
"""

import datetime
import json
import os
import shutil
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from src.nucleo import constants  # noqa: E402
from src.mundo import nivel_dados  # noqa: E402
from src.mundo import validacao_mapa as val  # noqa: E402
from src.quiz.dados_csv import DIFICULDADES, ler_grade, ler_perguntas, ler_tabela
from src.nucleo.utils import ASSETS_PATH, ErroMapa, carregar_nivel_csv, extrair_marcadores  # noqa: E402

PASTA_BANCO = ASSETS_PATH / "banco de dados"
CLASSES_VOADORAS = {"Tucano"}  # nascem no ar: o marcador não tem chão embaixo
PASTA_SETORES = ASSETS_PATH / "levels" / constants.PASTA_SETORES


def _titulo(texto):
    print(f"\n== {texto} " + "=" * max(0, 64 - len(texto)))


def validar_perguntas():
    erros, avisos = [], []
    total = []
    for nome, origem, obrigatorio in (("perguntas.csv", "padrao", True),
                                      ("perguntas_professores.csv", "professor", False)):
        caminho = PASTA_BANCO / nome
        _titulo(f"PERGUNTAS — {nome}")
        if not caminho.exists():
            (erros if obrigatorio else avisos).append(f"{nome}: arquivo ausente")
            print("   arquivo ausente" + ("" if obrigatorio else " (opcional)"))
            continue
        try:
            _, _, info = ler_tabela(str(caminho))
            print(f"   codificação: {info['codificacao']}   separador: '{info['separador']}'")
        except Exception as e:  # noqa: BLE001
            erros.append(f"{nome}: {e}")
            print(f"   ERRO: {e}")
            continue
        perguntas, problemas = ler_perguntas(str(caminho), origem=origem)
        total += perguntas
        for p in problemas:
            grave = "colunas obrigatórias" in p or "gabarito" in p or "campos" in p
            (erros if grave else avisos).append(f"{nome}: {p}")
            print(f"   {'ERRO ' if grave else 'aviso'}  {p}")
        print(f"   {len(perguntas)} pergunta(s) válida(s)")
    _titulo("PERGUNTAS POR FASE")
    por_dif = {k: sum(1 for p in total if p['dificuldade_chave'] == k) for k in ("facil", "medio", "dificil")}
    print("   " + "   ".join(f"{DIFICULDADES[k]}: {v}" for k, v in por_dif.items()))
    for fase, difs in sorted(constants.DIFICULDADES_POR_FASE.items()):
        n = sum(por_dif.get(d, 0) for d in difs)
        setores = [s for s, f in constants.FASE_POR_REGIAO.items() if f == fase]
        print(f"   fase {fase} ({', '.join(setores) or '-'}): {n} pergunta(s) elegível(is)")
        if n == 0:
            avisos.append(f"fase {fase} sem perguntas da dificuldade certa (o jogo usa as demais)")
    if not total:
        erros.append("nenhuma pergunta válida: o quiz usaria só as 2 perguntas de emergência")
    return erros, avisos


def _digital(grade):
    import hashlib
    texto = "\n".join(",".join(str(v) for v in linha) for linha in grade)
    return hashlib.sha256(texto.encode("ascii")).hexdigest()


def validar_mapas():
    erros, avisos = [], []
    try:
        manifesto = json.loads((PASTA_SETORES / "_gerado.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        manifesto = {}
    marcadores = {}
    for nome, cfg in constants.SETORES.items():
        arquivo = cfg["arquivo"]
        _titulo(f"MAPA — setor '{nome}' ({arquivo})")
        caminho = PASTA_SETORES / arquivo
        if not caminho.exists():
            erros.append(f"{arquivo}: arquivo ausente")
            print("   ERRO: arquivo ausente (rode python gerar_mundo.py)")
            continue
        try:
            grade = carregar_nivel_csv(os.path.join(constants.PASTA_SETORES, arquivo))
        except ErroMapa as e:
            erros.append(str(e))
            print(f"   ERRO: {e}")
            continue
        digital = _digital(grade)
        if manifesto.get(arquivo) == digital:
            print("   origem: igual à última saída do gerar_mundo.py")
        else:
            print("   origem: EDITADO À MÃO (o gerador não sobrescreve este arquivo)")
        print(f"   tamanho: {len(grade)} linhas x {len(grade[0])} colunas")
        for p in val.validar_csv(grade):
            erros.append(f"{arquivo}: {p}")
            print(f"   ERRO  {p}")
        copia = [list(l) for l in grade]
        m = extrair_marcadores(copia)
        marcadores[nome] = (m, copia)
        info = nivel_dados.SETORES_GERADOS.get(nome, {})
        if m["player"] and nome == constants.SETOR_INICIAL:
            entrada = m["player"]
        elif m["chegadas"]:
            col, lin = next(iter(m["chegadas"].values()))
            entrada = (col, lin + 1)
        else:
            entrada = (info.get("entrada_col"), info.get("entrada_row"))
        if entrada[0] is not None:
            for p in val.validar_regiao(copia, nome, 0, len(copia[0]) - 1, *entrada):
                erros.append(f"{arquivo}: {p}")
                print(f"   ERRO  {p}")
        for i, mi in enumerate(m["minerios"]):
            for p in val.validar_celula_entidade(copia, f"minerio#{i}", mi["col"], mi["row"]):
                erros.append(f"{arquivo}: {p}")
                print(f"   ERRO  {p}")
        for i, e in enumerate(m["inimigos"]):
            if e["classe"] in CLASSES_VOADORAS:
                # Voa: não precisa de chão, só de não nascer dentro de bloco.
                lin = e["row"] - 1
                if copia[lin][e["col"]] in constants.SOLID_TILES:
                    erros.append(f"{arquivo}: {e['classe']}#{i} nasce dentro de bloco "
                                 f"(linha {lin}, col {e['col']})")
                    print(f"   ERRO  {e['classe']}#{i} dentro de bloco")
                continue
            for p in val.validar_celula_entidade(copia, f"{e['classe']}#{i}", e["col"],
                                                 e["row"], e["altura"], e["ancora"]):
                erros.append(f"{arquivo}: {p}")
                print(f"   ERRO  {p}")
        print(f"   marcadores: spawn={'sim' if m['player'] else 'não'}  "
              f"minérios={len(m['minerios'])}  inimigos={len(m['inimigos'])}  "
              f"passagens={len(m['passagens'])}  chegadas={len(m['chegadas'])}  "
              f"boss={'sim' if m['area_boss'] else 'não'}")

    _titulo("LIGAÇÕES ENTRE SETORES")
    ok = True
    com_spawn = [n for n, (m, _) in marcadores.items() if m["player"]]
    if com_spawn != [constants.SETOR_INICIAL]:
        erros.append(f"spawn do player deveria estar só em '{constants.SETOR_INICIAL}' (está em {com_spawn})")
        ok = False
    for nome, (m, _) in marcadores.items():
        for (lin, col), destino in m["passagens"].items():
            alvo = marcadores.get(destino["setor"])
            if alvo is None or destino["chegada"] not in alvo[0]["chegadas"]:
                erros.append(f"{nome}: passagem {destino['id_tile']} em (linha {lin}, col {col}) "
                             f"leva a '{destino['setor']}' sem a chegada {destino['chegada']}")
                ok = False
    arena = nivel_dados.AREA_BOSS.get("setor")
    if arena in marcadores and not marcadores[arena][0]["area_boss"]:
        erros.append(f"setor '{arena}' sem o marcador do boss ({constants.TILE_AREA_BOSS})")
        ok = False
    print("   OK" if ok else "   ver erros acima")
    return erros, avisos


def padronizar():
    """Reescreve os CSVs no formato padrão, com backup e sem mudar conteúdo."""
    import csv
    alvos = [PASTA_BANCO / "perguntas.csv", PASTA_BANCO / "perguntas_professores.csv"]
    alvos += [PASTA_SETORES / c["arquivo"] for c in constants.SETORES.values()]
    carimbo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for caminho in alvos:
        if not caminho.exists():
            continue
        bkp = caminho.parent / "backup"
        bkp.mkdir(exist_ok=True)
        shutil.copy2(caminho, bkp / f"{caminho.stem}_{carimbo}.csv")
        if caminho.parent == PASTA_SETORES:
            linhas = [row for _, row in ler_grade(str(caminho))]
        else:
            cab, corpo, _ = ler_tabela(str(caminho))
            linhas = [cab] + [row for _, row in corpo]
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerows(linhas)
        print(f"padronizado: {caminho.relative_to(RAIZ)}  (backup em {bkp.relative_to(RAIZ)})")


def main():
    if "--padronizar" in sys.argv:
        padronizar()
    e1, a1 = validar_perguntas()
    e2, a2 = validar_mapas()
    erros, avisos = e1 + e2, a1 + a2
    _titulo("RESUMO")
    print(f"   {len(erros)} erro(s), {len(avisos)} aviso(s)")
    if erros:
        print("   Corrija os ERROS: eles impedem o jogo de abrir ou tiram perguntas do quiz.")
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
