"""
atualizar_referencia_terreno.py — regenera docs/TERRENO_REFERENCIA.json.

`ferramentas/validar_redesign.py` e `ferramentas/validar_terreno.py` comparam
os CSVs com essa referência CONGELADA (tamanho, lista de marcadores e hash
das colisões). Isso é proposital: qualquer mudança de geometria reprova até
alguém aprovar a versão nova. Depois que o redesign passou em todos os testes
do checklist (docs/ISA_INTEGRACAO_REDESIGN.md), rode esta ferramenta para
"assinar" os mapas novos.

uso (na raiz do projeto):
    python ferramentas/atualizar_referencia_terreno.py            # só mostra as diferenças
    python ferramentas/atualizar_referencia_terreno.py --gravar   # grava a referência nova

Não altera nenhum mapa. Avisa também quando src/nivel_dados.py
(SETORES_GERADOS, AREA_BOSS) não bate mais com os CSVs — esse arquivo é
código e deve ser ajustado à mão.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from src.nucleo import constants  # noqa: E402
from src.mundo import nivel_dados  # noqa: E402

REF = RAIZ / "docs" / "TERRENO_REFERENCIA.json"


def ler(nome):
    texto = (RAIZ / "assets/levels/setores" / f"{nome}.csv").read_text(encoding="utf-8-sig")
    sep = ";" if texto.splitlines()[0].count(";") > texto.splitlines()[0].count(",") else ","
    return [[int(v) for v in r] for r in csv.reader(texto.splitlines(), delimiter=sep) if r]


def referencia(grade):
    return {
        "altura": len(grade), "largura": len(grade[0]),
        "marcadores": sorted([x, y, v] for y, row in enumerate(grade) for x, v in enumerate(row)
                             if v in constants.TILES_MARCADORES),
        "colisoes_sha256": hashlib.sha256(
            bytes(int(v in constants.SOLID_TILES) for row in grade for v in row)).hexdigest(),
    }


def main():
    gravar = "--gravar" in sys.argv
    antiga = json.loads(REF.read_text(encoding="utf-8")) if REF.exists() else {}
    nova = {}
    mudou = False
    for nome in constants.SETORES:
        grade = ler(nome)
        r = referencia(grade)
        nova[nome] = r
        a = antiga.get(nome)
        if a is None:
            print(f"{nome}: novo na referência"); mudou = True
            continue
        dif = []
        if (a["altura"], a["largura"]) != (r["altura"], r["largura"]):
            dif.append(f"tamanho {a['largura']}x{a['altura']} -> {r['largura']}x{r['altura']}")
        sa, sn = {tuple(m) for m in a["marcadores"]}, {tuple(m) for m in r["marcadores"]}
        if sa != sn:
            dif.append(f"marcadores: -{len(sa - sn)} +{len(sn - sa)}")
            for m in sorted(sa - sn)[:10]:
                dif.append(f"   saiu  id {m[2]} em col {m[0]}, linha {m[1]}")
            for m in sorted(sn - sa)[:10]:
                dif.append(f"   entrou id {m[2]} em col {m[0]}, linha {m[1]}")
        if a["colisoes_sha256"] != r["colisoes_sha256"]:
            dif.append("geometria de colisão mudou")
        if dif:
            mudou = True
            print(f"{nome}:")
            for d in dif:
                print("   " + d)
        else:
            print(f"{nome}: igual à referência")
        meta = nivel_dados.SETORES_GERADOS.get(nome)
        if meta and (meta["colunas"], meta["linhas"]) != (r["largura"], r["altura"]):
            print(f"   ATENÇÃO: src/nivel_dados.SETORES_GERADOS['{nome}'] diz "
                  f"{meta['colunas']}x{meta['linhas']}; o CSV tem {r['largura']}x{r['altura']}")
        ab = nivel_dados.AREA_BOSS
        if ab.get("setor") == nome and ab["c1"] >= r["largura"]:
            print(f"   ATENÇÃO: AREA_BOSS vai até a coluna {ab['c1']}, mas o CSV só tem {r['largura']}")
    if gravar and mudou:
        REF.write_text(json.dumps(nova, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nreferência gravada em {REF.relative_to(RAIZ)}")
    elif mudou:
        print("\n(nada gravado; use --gravar depois de aprovar os mapas)")
    else:
        print("\nreferência já está em dia")


if __name__ == "__main__":
    main()
