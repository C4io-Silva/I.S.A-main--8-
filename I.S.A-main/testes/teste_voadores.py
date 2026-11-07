"""Regras do inimigo voador (ID 93) — ferramentas/validar_voadores.py (V1, V3–V6).

Casos positivos: os 3 tucanos reais (floresta, caverna, copas).
Casos negativos (tucano hipotético na caverna, sem mexer no CSV):
  (147,18)  alto demais: longe de qualquer chão alcançável (V3, V4, V6)
  (136,14)  bolsão fechado na rocha (V1, V3, V4, V6)
  (12,27)   em cima da chegada 40 (V5)
Resultado reprodutível: relógio simulado e fase do voo fixa.
"""
import os, sys
from pathlib import Path
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "ferramentas")); os.chdir(ROOT)
import ferramentas.validacao.validar_voadores as VV

if __name__ == "__main__":
    reais = []
    for s in ("floresta", "caverna", "copas"):
        reais += VV.tucanos_do_setor(s)
    for r in reais:
        print("  +", VV.linha_txt(r))
        assert r["APROVADO"], ("tucano real reprovado", r)
    assert len(reais) == 3, len(reais)
    negativos = {(147, 18): {"V3", "V4", "V6"}, (136, 14): {"V1", "V3", "V4", "V6"}, (12, 27): {"V5"}}
    for (c, l), esperado in negativos.items():
        r = VV.avaliar("caverna", c, l)
        print("  -", VV.linha_txt(r))
        assert not r["APROVADO"], ("caso ruim aprovado", r)
        assert esperado <= set(r["falhas"]), ((c, l), "esperava", esperado, "veio", r["falhas"])
    # reprodutível: a mesma avaliação dá o mesmo resultado
    a, b = VV.avaliar("caverna", 147, 29), VV.avaliar("caverna", 147, 29)
    assert a == b, (a, b)
    print("TESTE VOADORES APROVADO")
