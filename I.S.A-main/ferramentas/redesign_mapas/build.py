"""Monta os setores redesenhados (v0.9) e grava no jogo.

uso (na raiz do projeto):
    python ferramentas/redesign_mapas/build.py . floresta,caverna,copas,arena --sobrescrever

ATENÇÃO: substitui os CSVs do setor. Sem --sobrescrever só monta e confere,
sem gravar. Faça backup antes se os CSVs tiverem edições à mão posteriores.
Grava assets/levels/setores/<s>.csv, assets/levels/decoracoes/<s>_decor.csv
(mesmo separador / BOM / quebra de linha do arquivo original) e atualiza só as
entradas do setor em assets/levels/estruturas_cenario.json.
"""
import importlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
GAME = os.path.abspath(sys.argv[1])
os.environ["ISA_JOGO"] = GAME
GRAVAR = "--sobrescrever" in sys.argv
sys.path.insert(1, GAME)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
from src.nucleo import constants  # noqa: E402
from kit import ler_formato, gravar_csv, VAZIO  # noqa: E402
from src.mundo.decoracoes_offline import ARTE  # noqa: E402

setores = sys.argv[2].split(",")
est_path = os.path.join(GAME, "assets/levels/estruturas_cenario.json")
estruturas = json.load(open(est_path, encoding="utf-8"))

for nome in setores:
    mod = importlib.import_module(nome)
    t, d, est = mod.construir()
    # checagens locais (as completas ficam com os validadores do jogo)
    for r in range(t.linhas):
        for c in range(t.colunas):
            v, dv = t.g[r][c], d.g[r][c]
            assert v == VAZIO or v in constants.TILE_SPRITES or v in constants.TILES_MARCADORES, (nome, c, r, v)
            if dv != VAZIO:
                assert dv in ARTE, (nome, c, r, dv)
                assert v not in constants.SOLID_TILES and v not in constants.TILES_MARCADORES, (nome, c, r, "decor sobre colisao/marcador")
    p_t = os.path.join(GAME, "assets/levels/setores", f"{nome}.csv")
    p_d = os.path.join(GAME, "assets/levels/decoracoes", f"{nome}_decor.csv")
    if GRAVAR:
        gravar_csv(p_t, t.g, ler_formato(p_t))
        gravar_csv(p_d, d.g, ler_formato(p_d))
    if est is not None:
        estruturas[nome] = est
    n_dec = sum(v != VAZIO for row in d.g for v in row)
    n_min = sum(v == constants.TILE_MINERIO for row in t.g for v in row)
    print(f"{nome}: {t.colunas}x{t.linhas}, {n_min} minerios, {n_dec} decoracoes, {len(est or [])} estruturas")

if GRAVAR:
    with open(est_path, "w", encoding="utf-8") as fp:
        json.dump(estruturas, fp, indent=2, ensure_ascii=False)
else:
    print("(conferido, nada gravado — use --sobrescrever para gravar)")
