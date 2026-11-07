"""
Converte o Word de perguntas dos professores (template_perguntas_ISA.docx)
para o CSV que o jogo I.S.A. lê (perguntas_professores.csv).

Uso:
    python converter_perguntas.py [entrada.docx] [saida.csv] [--substituir]

Sem argumentos:
    template_perguntas_ISA.docx -> assets/banco de dados/perguntas_professores.csv

COMPORTAMENTO (mudou na unificação)
-----------------------------------
Antes, cada conversão APAGAVA o CSV inteiro e gravava só o que estava no
Word: quem tinha corrigido uma pergunta direto no CSV perdia a correção na
próxima conversão. Agora o padrão é MESCLAR:

  * perguntas do Word que ainda não estão no CSV são acrescentadas;
  * perguntas que já estão no CSV (mesmo enunciado) são mantidas como estão
    no CSV — a edição manual vence;
  * antes de gravar, o CSV antigo é copiado para
    assets/banco de dados/backup/.

Use --substituir para recriar o CSV só com o conteúdo do Word (também faz
backup antes).

O CSV sai em UTF-8 com BOM e separador ";" — o formato que o Excel em
português abre direto com duplo clique. O jogo também aceita vírgula.

Marcadores aceitos em cada bloco do Word (maiúsculas não importam):
    Pergunta:, Alternativa A: ... Alternativa E:, Correta:, Categoria:,
    Dificuldade: (opcional — Fácil, Médio ou Difícil; sem ela vale Médio)
"""

import csv
import datetime
import os
import shutil
import sys

from docx import Document

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

from src.quiz.dados_csv import ler_perguntas, normalizar  # noqa: E402

PASTA_PERGUNTAS_PADRAO = os.path.join(RAIZ, "assets", "banco de dados")

MARCADORES = {
    "pergunta": "pergunta:",
    "alt_a": "alternativa a:",
    "alt_b": "alternativa b:",
    "alt_c": "alternativa c:",
    "alt_d": "alternativa d:",
    "alt_e": "alternativa e:",
    "correta": "correta:",
    "categoria": "categoria:",
    "dificuldade": "dificuldade:",
}
COLUNAS = ["pergunta", "alt_a", "alt_b", "alt_c", "alt_d", "alt_e",
           "correta", "categoria", "dificuldade"]
CAMPOS_OBRIGATORIOS = ["pergunta", "alt_a", "alt_b", "correta"]


def extrair_blocos(caminho_docx):
    """Lê o Word e devolve a lista de blocos (dicts) e os avisos."""
    doc = Document(caminho_docx)
    linhas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    # As tabelas do Word NÃO são lidas: no modelo, a tabela é só a
    # ilustração do "Exemplo preenchido".

    blocos, atual, avisos = [], {}, []

    def fechar():
        if not atual:
            return
        if all(atual.get(k) for k in CAMPOS_OBRIGATORIOS):
            atual["correta"] = atual["correta"].strip().lower().rstrip(")")
            blocos.append(dict(atual))
        elif any(atual.values()):
            faltam = [k for k in CAMPOS_OBRIGATORIOS if not atual.get(k)]
            avisos.append(f"Pergunta incompleta ignorada ({', '.join(faltam)} faltando): "
                          f"{atual.get('pergunta', '???')[:60]}")
        atual.clear()

    for linha in linhas:
        baixa = linha.lower()
        for chave, marcador in MARCADORES.items():
            if baixa.startswith(marcador):
                valor = linha[len(marcador):].strip()
                if chave == "pergunta":
                    fechar()  # um novo "Pergunta:" encerra o bloco anterior
                if valor:
                    atual[chave] = valor
                break
    fechar()
    return blocos, avisos


def _backup(caminho_csv):
    if not os.path.exists(caminho_csv):
        return None
    pasta = os.path.join(os.path.dirname(caminho_csv), "backup")
    os.makedirs(pasta, exist_ok=True)
    carimbo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = os.path.splitext(os.path.basename(caminho_csv))[0]
    destino = os.path.join(pasta, f"{nome}_{carimbo}.csv")
    shutil.copy2(caminho_csv, destino)
    return destino


def _como_linha(p):
    """Pergunta no formato do jogo -> linha no formato do CSV dos professores."""
    return {
        "pergunta": p["pergunta"],
        **{f"alt_{l}": p.get(f"opcao_{l}", "") for l in "abcde"},
        "correta": p["resposta"],
        "categoria": p.get("disciplina", ""),
        "dificuldade": p.get("dificuldade", ""),
    }


def converter(caminho_docx, caminho_csv, substituir=False):
    blocos, avisos = extrair_blocos(caminho_docx)
    for a in avisos:
        print(a)
    if not blocos:
        print("Nenhuma pergunta valida encontrada no documento. CSV nao alterado.")
        return 0

    existentes = []
    if not substituir and os.path.exists(caminho_csv):
        lidas, problemas = ler_perguntas(caminho_csv, origem="professor")
        for p in problemas:
            print(f"Aviso no CSV atual: {p}")
        existentes = [_como_linha(p) for p in lidas]

    ja_tem = {normalizar(l["pergunta"]) for l in existentes}
    novas = [b for b in blocos if normalizar(b["pergunta"]) not in ja_tem]
    linhas = existentes + novas

    pasta_destino = os.path.dirname(caminho_csv)
    if pasta_destino:
        os.makedirs(pasta_destino, exist_ok=True)
    copia = _backup(caminho_csv)
    if copia:
        print(f"Backup do CSV anterior: {copia}")

    with open(caminho_csv, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS, delimiter=";",
                                  extrasaction="ignore")
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({c: linha.get(c, "") for c in COLUNAS})

    print(f"{len(novas)} pergunta(s) nova(s) do Word; {len(existentes)} mantida(s) do CSV; "
          f"total {len(linhas)} em '{caminho_csv}'")
    return len(novas)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    entrada = args[0] if args else os.path.join(RAIZ, "template_perguntas_ISA.docx")
    saida = args[1] if len(args) > 1 else os.path.join(
        PASTA_PERGUNTAS_PADRAO, "perguntas_professores.csv"
    )
    converter(entrada, saida, substituir="--substituir" in sys.argv)
