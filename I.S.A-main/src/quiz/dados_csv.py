"""
Leitura e validação dos CSVs editáveis do I.S.A. (perguntas e mapas).

POR QUE ESTE MÓDULO EXISTE
--------------------------
Os CSVs "não aceitavam edição": o arquivo abria no Excel, era salvo, e o
jogo passava a ler errado ou a quebrar. As causas encontradas na auditoria:

  1. O Excel em português salva CSV com PONTO-E-VÍRGULA (;) e em ANSI
     (cp1252). O jogo lia só vírgula e só UTF-8: depois de salvar no Excel,
     a linha inteira virava uma coluna só, ou o arquivo nem decodificava.
  2. "CSV UTF-8" do Excel grava BOM (\\ufeff) no início. Lido com "utf-8"
     puro, o BOM gruda no primeiro cabeçalho ("\\ufeffdisciplina") e a
     coluna some.
  3. perguntas_professores.csv chegou com o TEXTO literal "\\xef\\xbb\\xbf"
     no cabeçalho (um BOM escrito como texto por algum script).
  4. Cabeçalhos com e sem acento (opcao_a / opçao_a), maiúsculas, espaços e
     nomes diferentes entre o banco padrão e o dos professores.

Aqui tudo isso é tratado num lugar só: a leitura descobre a codificação e o
separador, limpa e padroniza os cabeçalhos e devolve, além das linhas, a lista
de problemas encontrados — que o jogo imprime e o validar_dados.py mostra.

O arquivo do usuário NUNCA é reescrito pela leitura: o formato em que ele
salvou continua valendo.
"""

import csv
import io
import unicodedata

# Codificações tentadas, em ordem. utf-8-sig aceita arquivo com e sem BOM;
# cp1252 é o "ANSI" do Excel/Bloco de Notas em Windows português.
CODIFICACOES = ("utf-8-sig", "cp1252", "latin-1")
SEPARADORES = (",", ";", "\t")

# BOM que algum script gravou como TEXTO (e não como bytes).
_BOM_LITERAIS = ("\\xef\\xbb\\xbf", "ï»¿", "﻿")

# Nomes aceitos para cada coluna do banco de perguntas -> nome padrão.
ALIASES_PERGUNTAS = {
    "disciplina": "disciplina", "materia": "disciplina", "categoria": "disciplina",
    "dificuldade": "dificuldade", "nivel": "dificuldade",
    "pergunta": "pergunta", "enunciado": "pergunta",
    "resposta": "resposta", "correta": "resposta", "gabarito": "resposta",
}
for _l in "abcde":
    for _nome in (f"opcao_{_l}", f"alt_{_l}", f"alternativa_{_l}", f"opcao{_l}", _l):
        ALIASES_PERGUNTAS[_nome] = f"opcao_{_l}"

COLUNAS_OBRIGATORIAS = ("pergunta", "opcao_a", "opcao_b", "resposta")
LETRAS = ("a", "b", "c", "d", "e")

# Dificuldades reconhecidas (já normalizadas) -> rótulo exibido.
DIFICULDADES = {"facil": "Fácil", "medio": "Médio", "media": "Médio",
                "dificil": "Difícil"}
# Dificuldade usada quando o CSV não traz uma válida (ex.: "Professor",
# vazio). "medio" entra nas fases 1 e 2 — a pergunta nunca some do fluxo.
DIFICULDADE_PADRAO = "medio"


class ErroCSV(ValueError):
    """CSV ilegível (codificação, vazio, sem cabeçalho)."""


def normalizar(texto):
    """Sem acento, minúsculo, sem espaços nas pontas."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return texto.encode("ascii", "ignore").decode("ascii").strip().lower()


def _limpar_cabecalho(nome):
    nome = str(nome or "")
    for bom in _BOM_LITERAIS:
        nome = nome.replace(bom, "")
    nome = normalizar(nome).replace(" ", "_").replace("-", "_")
    return nome


def ler_texto(caminho):
    """Lê o arquivo descobrindo a codificação. Devolve (texto, codificação)."""
    with open(caminho, "rb") as f:
        bruto = f.read()
    for cod in CODIFICACOES:
        try:
            return bruto.decode(cod), cod
        except UnicodeDecodeError:
            continue
    raise ErroCSV(f"{caminho}: codificação não reconhecida")  # pragma: no cover


def detectar_separador(texto):
    """Separador mais provável, olhando a primeira linha não vazia."""
    primeira = next((l for l in texto.splitlines() if l.strip()), "")
    for bom in _BOM_LITERAIS:
        primeira = primeira.replace(bom, "")
    try:
        return csv.Sniffer().sniff(primeira, delimiters="".join(SEPARADORES)).delimiter
    except csv.Error:
        contagens = {s: primeira.count(s) for s in SEPARADORES}
        melhor = max(contagens, key=contagens.get)
        return melhor if contagens[melhor] else ","


def ler_tabela(caminho):
    """
    Lê um CSV com cabeçalho. Devolve (cabecalhos_limpos, linhas, info) onde
    `linhas` é uma lista de (numero_da_linha, [valores]) e `info` guarda a
    codificação e o separador detectados (para o relatório de validação).
    """
    texto, cod = ler_texto(caminho)
    if not texto.strip():
        raise ErroCSV(f"{caminho}: arquivo vazio")
    sep = detectar_separador(texto)
    leitor = csv.reader(io.StringIO(texto), delimiter=sep)
    cabecalho = None
    linhas = []
    for n, row in enumerate(leitor, start=1):
        if not row or all(not v.strip() for v in row):
            continue
        if cabecalho is None:
            cabecalho = [_limpar_cabecalho(c) for c in row]
            continue
        linhas.append((n, row))
    if cabecalho is None:
        raise ErroCSV(f"{caminho}: sem cabeçalho")
    info = {"codificacao": cod, "separador": sep}
    return cabecalho, linhas, info


def normalizar_dificuldade(valor):
    """'Fácil'/'FACIL'/'facil ' -> 'facil'. Desconhecida -> DIFICULDADE_PADRAO."""
    chave = normalizar(valor)
    if chave == "media":
        chave = "medio"
    return chave if chave in DIFICULDADES else DIFICULDADE_PADRAO


def ler_perguntas(caminho, origem="padrao", dificuldade_padrao=None):
    """
    Lê um banco de perguntas em qualquer um dos formatos aceitos e devolve
    (perguntas_validas, problemas).

    Cada pergunta sai no formato único do jogo:
        disciplina, dificuldade (rótulo exibido), dificuldade_chave
        (facil/medio/dificil, usada pelo filtro de fase), pergunta,
        opcao_a..opcao_e, resposta (a..e minúsculo), origem, linha_csv.

    Linhas com problema NÃO derrubam o jogo: são puladas e descritas em
    `problemas` com o número da linha no arquivo.
    """
    problemas = []
    try:
        cabecalho, linhas, info = ler_tabela(caminho)
    except FileNotFoundError:
        return [], [f"{caminho}: arquivo não encontrado"]
    except ErroCSV as e:
        return [], [str(e)]

    colunas = [ALIASES_PERGUNTAS.get(c, c) for c in cabecalho]
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in colunas]
    if faltando:
        return [], [f"{caminho}: colunas obrigatórias ausentes: {', '.join(faltando)} "
                    f"(cabeçalho lido: {', '.join(cabecalho)}; separador "
                    f"'{info['separador']}', codificação {info['codificacao']})"]

    perguntas = []
    vistos = {}
    for n, valores in linhas:
        if len(valores) < len(colunas):
            valores = valores + [""] * (len(colunas) - len(valores))
        elif len(valores) > len(colunas) and any(v.strip() for v in valores[len(colunas):]):
            problemas.append(f"linha {n}: {len(valores)} campos, cabeçalho tem "
                             f"{len(colunas)} (vírgula sem aspas no texto?)")
            continue
        d = {}
        for col, val in zip(colunas, valores):
            if col and col not in d:
                d[col] = (val or "").strip()
        rotulo = f"linha {n}"
        enunciado = d.get("pergunta", "")
        if not enunciado:
            problemas.append(f"{rotulo}: pergunta vazia")
            continue
        alternativas = {l: d.get(f"opcao_{l}", "") for l in LETRAS}
        alternativas = {l: t for l, t in alternativas.items()
                        if t and t.lower() != "nan"}
        if len(alternativas) < 2:
            problemas.append(f"{rotulo}: menos de 2 alternativas preenchidas")
            continue
        resposta = normalizar(d.get("resposta", "")).rstrip(")").strip()
        if resposta not in LETRAS:
            problemas.append(f"{rotulo}: gabarito inválido {d.get('resposta', '')!r} "
                             f"(use A, B, C, D ou E)")
            continue
        if resposta not in alternativas:
            problemas.append(f"{rotulo}: gabarito '{resposta.upper()}' aponta para "
                             f"alternativa vazia")
            continue
        chave_dup = normalizar(enunciado)
        if chave_dup in vistos:
            problemas.append(f"{rotulo}: pergunta duplicada (igual à linha "
                             f"{vistos[chave_dup]}) — ignorada")
            continue
        vistos[chave_dup] = n

        bruta = d.get("dificuldade", "") or (dificuldade_padrao or "")
        chave_dif = normalizar_dificuldade(bruta)
        if bruta and normalizar(bruta) not in DIFICULDADES and normalizar(bruta) != "media":
            problemas.append(f"{rotulo}: dificuldade {bruta!r} desconhecida — "
                             f"tratada como '{DIFICULDADES[chave_dif]}'")
        perguntas.append({
            "disciplina": d.get("disciplina", "") or "Geral",
            "dificuldade": DIFICULDADES[chave_dif],
            "dificuldade_chave": chave_dif,
            "pergunta": enunciado,
            **{f"opcao_{l}": alternativas.get(l, "") for l in LETRAS},
            "resposta": resposta,
            "origem": origem,
            "linha_csv": n,
        })
    return perguntas, problemas


def ler_grade(caminho):
    """
    Lê um CSV de mapa (só números, sem cabeçalho). Aceita vírgula ou ponto e
    vírgula, BOM e células com espaços — como o Excel/LibreOffice salvam.
    Devolve lista de (numero_da_linha, [str, ...]).
    """
    texto, _ = ler_texto(caminho)
    for bom in _BOM_LITERAIS:
        texto = texto.replace(bom, "")
    sep = detectar_separador(texto)
    linhas = []
    for n, row in enumerate(csv.reader(io.StringIO(texto), delimiter=sep), start=1):
        if not row or all(not v.strip() for v in row):
            continue
        # O Excel às vezes deixa um separador sobrando no fim da linha.
        while row and not row[-1].strip():
            row = row[:-1]
        linhas.append((n, [v.strip() for v in row]))
    return linhas
