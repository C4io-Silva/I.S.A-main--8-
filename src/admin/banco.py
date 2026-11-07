"""
Banco de perguntas do painel ADMIN: carrega, valida, adiciona, edita, exclui
e SALVA nos mesmos CSVs que o jogo lê (assets/banco de dados/).

Este módulo não usa pygame (a tela fica em tela_perguntas.py), então pode ser
testado sem abrir janela.

Regras de segurança dos dados
-----------------------------
* Cada alteração é salva NA HORA, no formato padrão do projeto (UTF-8 com BOM
  e ";", o mesmo de `validar_dados.py --padronizar`), então o Excel abre certo.
* Antes da PRIMEIRA gravação de cada arquivo na sessão, uma cópia vai para
  `banco de dados/backup/` (mesmo lugar e nome que o padronizar usa).
* A gravação é atômica (arquivo temporário + troca), então uma queda de luz
  no meio não deixa o CSV pela metade.
* Se não der para gravar (ex.: o CSV está aberto no Excel), a alteração é
  desfeita na memória e o erro volta para a tela avisar.
* Linhas inválidas/duplicadas do CSV não são carregadas (é assim que o jogo
  também lê). Por isso o backup acima importa: ele guarda o arquivo original.
"""

import csv
import datetime
import os
import shutil
from pathlib import Path

from src.nucleo.caminhos import RAIZ
from src.quiz.dados_csv import DIFICULDADES, LETRAS, ler_perguntas, normalizar

COLUNAS = ("disciplina", "dificuldade", "pergunta",
           "opcao_a", "opcao_b", "opcao_c", "opcao_d", "opcao_e", "resposta")

# Ordem em que as dificuldades aparecem no editor: (chave, rótulo).
NIVEIS = (("facil", "Fácil"), ("medio", "Médio"), ("dificil", "Difícil"))

# origem -> nome do arquivo (os dois que o jogo lê).
ARQUIVOS = {"padrao": "perguntas.csv", "professor": "perguntas_professores.csv"}
# Subpasta aceita pelo jogo (ver utils.CAMINHOS_PERGUNTAS_*).
_SUBPASTA = "perguntas"


class ErroSalvar(OSError):
    """Não foi possível gravar o CSV (arquivo aberto em outro programa, etc.)."""


def pasta_padrao():
    return RAIZ / "assets" / "banco de dados"


def pergunta_vazia():
    """Dados de uma pergunta nova, no formato que o editor usa."""
    return {"disciplina": "", "dificuldade_chave": "medio", "pergunta": "",
            **{f"opcao_{l}": "" for l in LETRAS}, "resposta": ""}


class BancoAdmin:
    def __init__(self, pasta=None):
        self.pasta = Path(pasta) if pasta else pasta_padrao()
        self.perguntas = []      # padrão primeiro, depois professores (ordem do arquivo)
        self.problemas = 0       # linhas que o jogo também ignora ao ler
        self._caminhos = {}
        self._backup_feito = set()

    # ── leitura ──────────────────────────────────────────────────────────────
    def _achar(self, origem):
        nome = ARQUIVOS[origem]
        for candidato in (self.pasta / nome, self.pasta / _SUBPASTA / nome):
            if candidato.exists():
                return candidato
        return self.pasta / nome     # ainda não existe: será criado aqui

    def carregar(self):
        """Lê os dois CSVs do disco (descarta qualquer alteração não salva)."""
        self.perguntas = []
        self.problemas = 0
        for origem in ARQUIVOS:
            caminho = self._achar(origem)
            self._caminhos[origem] = caminho
            if not caminho.exists():
                continue
            lidas, problemas = ler_perguntas(str(caminho), origem=origem)
            self.perguntas += lidas
            self.problemas += len(problemas)
        return self.perguntas

    # ── validação ────────────────────────────────────────────────────────────
    def validar(self, dados, ignorar=None):
        """Devolve a mensagem do primeiro problema, ou None se está tudo certo.
        `ignorar` é a pergunta que está sendo editada (não conta como duplicada)."""
        enunciado = (dados.get("pergunta") or "").strip()
        if not enunciado:
            return "DIGITE O ENUNCIADO DA PERGUNTA"
        preenchidas = {l for l in LETRAS if (dados.get(f"opcao_{l}") or "").strip()}
        if len(preenchidas) < 2:
            return "PREENCHA PELO MENOS 2 ALTERNATIVAS"
        resposta = (dados.get("resposta") or "").strip().lower()
        if resposta not in LETRAS:
            return "ESCOLHA A RESPOSTA CORRETA (CLIQUE NA LETRA)"
        if resposta not in preenchidas:
            return "A ALTERNATIVA CORRETA ESTA VAZIA"
        chave = normalizar(enunciado)
        for p in self.perguntas:
            if p is not ignorar and normalizar(p["pergunta"]) == chave:
                return "JA EXISTE UMA PERGUNTA IGUAL"
        return None

    @staticmethod
    def _montar(dados, origem, linha_csv=None):
        """Dados do editor -> pergunta no formato único do jogo."""
        chave = dados.get("dificuldade_chave", "medio")
        if chave not in DIFICULDADES:
            chave = "medio"
        if chave == "media":
            chave = "medio"
        return {
            "disciplina": (dados.get("disciplina") or "").strip() or "Geral",
            "dificuldade": DIFICULDADES[chave],
            "dificuldade_chave": chave,
            "pergunta": (dados.get("pergunta") or "").strip(),
            **{f"opcao_{l}": (dados.get(f"opcao_{l}") or "").strip() for l in LETRAS},
            "resposta": (dados.get("resposta") or "").strip().lower(),
            "origem": origem,
            "linha_csv": linha_csv,
        }

    # ── alterações (todas salvam em disco) ───────────────────────────────────
    def adicionar(self, dados):
        """Acrescenta ao fim do banco padrão. Devolve a pergunta criada."""
        erro = self.validar(dados)
        if erro:
            raise ValueError(erro)
        nova = self._montar(dados, "padrao")
        antes = list(self.perguntas)
        posicao = sum(1 for p in self.perguntas if p["origem"] == "padrao")
        self.perguntas.insert(posicao, nova)
        self._salvar_ou_desfazer(antes, "padrao")
        return nova

    def editar(self, pergunta, dados):
        """Troca `pergunta` pelos dados novos (mesma posição e mesmo arquivo)."""
        erro = self.validar(dados, ignorar=pergunta)
        if erro:
            raise ValueError(erro)
        nova = self._montar(dados, pergunta["origem"], pergunta.get("linha_csv"))
        antes = list(self.perguntas)
        self.perguntas[self._indice(pergunta)] = nova
        self._salvar_ou_desfazer(antes, nova["origem"])
        return nova

    def excluir(self, pergunta):
        antes = list(self.perguntas)
        del self.perguntas[self._indice(pergunta)]
        self._salvar_ou_desfazer(antes, pergunta["origem"])

    def _indice(self, pergunta):
        for i, p in enumerate(self.perguntas):
            if p is pergunta:
                return i
        raise ValueError("pergunta não está mais no banco")

    def _salvar_ou_desfazer(self, antes, origem):
        try:
            self.salvar(origem)
        except OSError:
            self.perguntas = antes
            raise

    # ── gravação ─────────────────────────────────────────────────────────────
    def salvar(self, origem):
        caminho = self._caminhos.get(origem) or self._achar(origem)
        self._caminhos[origem] = caminho
        linhas = [p for p in self.perguntas if p["origem"] == origem]
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            self._backup(caminho)
            temporario = caminho.with_name(caminho.name + ".tmp")
            with open(temporario, "w", newline="", encoding="utf-8-sig") as f:
                escritor = csv.writer(f, delimiter=";")
                escritor.writerow(COLUNAS)
                for p in linhas:
                    escritor.writerow([p["disciplina"], p["dificuldade"], p["pergunta"],
                                       *(p[f"opcao_{l}"] for l in LETRAS), p["resposta"]])
            os.replace(temporario, caminho)
        except OSError as e:
            try:
                caminho.with_name(caminho.name + ".tmp").unlink()
            except OSError:
                pass
            raise ErroSalvar(str(e)) from e

    def _backup(self, caminho):
        """Cópia do arquivo original, uma vez por sessão e por arquivo."""
        if caminho in self._backup_feito or not caminho.exists():
            return
        pasta = caminho.parent / "backup"
        pasta.mkdir(exist_ok=True)
        carimbo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(caminho, pasta / f"{caminho.stem}_{carimbo}.csv")
        self._backup_feito.add(caminho)
