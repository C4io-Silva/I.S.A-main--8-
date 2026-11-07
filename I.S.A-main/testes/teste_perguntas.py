"""
Teste rapido do banco de perguntas (vindo do projeto do Pedro, onde o arquivo
estava reservado mas vazio).

Roda fora do jogo, sem abrir janela, e mostra:
  - quantas perguntas padrao foram lidas do CSV;
  - quantas perguntas de professores foram convertidas;
  - quais perguntas estao com gabarito invalido ou alternativa vazia.

Uso (a partir da raiz do projeto):
    python testes/teste_perguntas.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nucleo.utils import carregar_perguntas_csv, carregar_perguntas_professores

LETRAS = ("a", "b", "c", "d", "e")


def _alternativa(pergunta, letra):
    """Le a alternativa aceitando as duas grafias usadas no projeto."""
    return (pergunta.get(f"opcao_{letra}") or pergunta.get(f"op\u00e7ao_{letra}") or "").strip()


def validar(perguntas, origem):
    problemas = 0
    for i, p in enumerate(perguntas, start=1):
        titulo = (p.get("pergunta") or "").strip()
        gabarito = (p.get("resposta") or "").strip().lower()

        if not titulo:
            print(f"[{origem} #{i}] enunciado vazio")
            problemas += 1
        if gabarito not in LETRAS:
            print(f"[{origem} #{i}] gabarito invalido: '{gabarito}'")
            problemas += 1
        elif not _alternativa(p, gabarito):
            print(f"[{origem} #{i}] gabarito '{gabarito}' aponta pra alternativa vazia")
            problemas += 1

        preenchidas = [l for l in ("a", "b", "c", "d") if _alternativa(p, l)]
        if len(preenchidas) < 2:
            print(f"[{origem} #{i}] menos de duas alternativas preenchidas")
            problemas += 1
    return problemas


def main():
    try:
        padrao = carregar_perguntas_csv("perguntas.csv")
    except Exception as e:  # noqa: BLE001
        padrao = []
        print(f"Nao foi possivel ler perguntas.csv: {e}")

    professores = carregar_perguntas_professores()

    print(f"Perguntas padrao......: {len(padrao)}")
    print(f"Perguntas professores.: {len(professores)}")
    print(f"Total.................: {len(padrao) + len(professores)}")
    print("-" * 40)

    problemas = validar(padrao, "padrao") + validar(professores, "professor")

    if problemas:
        print("-" * 40)
        print(f"{problemas} problema(s) encontrado(s).")
    else:
        print("Nenhum problema encontrado.")
    return problemas


if __name__ == "__main__":
    # Código de saída 1 quando há problema: assim o rodar_todos.py percebe.
    raise SystemExit(1 if main() else 0)
