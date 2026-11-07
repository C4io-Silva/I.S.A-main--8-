"""
Setores do mapa: cada região do mundo é um CSV próprio.

Um Setor junta tudo o que pertence a um pedaço do mundo — a grade de tiles
(World), os inimigos, os minérios, as passagens e os pontos de chegada — e
guarda esse estado durante a partida inteira. Todos os setores são montados
no início (carregar_setores) e o main só troca qual está ativo quando o
jogador atravessa uma passagem. Por isso um minério coletado na floresta não
reaparece quando o jogador volta da caverna.

Para criar um setor novo: gere/escreva o CSV em assets/levels/setores/,
registre-o em constants.SETORES e ligue-o aos outros com um par de
passagem + chegada em constants.PASSAGENS_CSV (ver MAPA-CSV.md).
"""

import os

import pygame

from src.nucleo import constants
from src.mundo import nivel_dados
from src.entidades.enemies import CLASSE_BOSS, CLASSES_INIMIGO
from src.entidades.itens.item_cura import ItemCura
from src.entidades.itens.minerio_cobre import minerio_cobre
from src.mundo.passagens import GerenciadorPassagens
from src.mundo.decoracoes import DecoracaoSetor
from src.mundo.estruturas_cenario import EstruturasCenario
from src.mundo.world import World
from src.nucleo.utils import ASSETS_PATH, ErroMapa, carregar_nivel_csv, extrair_marcadores

T = constants.TILE_SIZE


class Setor:
    """Um pedaço do mundo com seu próprio CSV, entidades e estado."""

    def __init__(self, nome, config, tiles, tile_fallback):
        self.nome = nome
        self.ambiente = config["ambiente"]
        caminho = os.path.join(constants.PASTA_SETORES, config["arquivo"])
        try:
            self.grade = carregar_nivel_csv(caminho)
        except FileNotFoundError:
            raise ErroMapa(_mensagem_csv_faltando(config["arquivo"])) from None

        # Marcadores são lidos (e apagados da grade) ANTES de montar o World:
        # senão virariam blocos de fallback no meio do mapa.
        marcadores = extrair_marcadores(self.grade)
        self.player_spawn = marcadores["player"]
        self.chegadas = marcadores["chegadas"]

        self.world = World()
        self.world.process_data(self.grade, tiles, tile_fallback)
        self.decoracoes = DecoracaoSetor(nome, self.world.linhas, self.world.colunas)
        self.estruturas = EstruturasCenario(nome)
        self.passagens = GerenciadorPassagens(marcadores["passagens"], self.grade)
        self.inimigos = [criar_inimigo(d) for d in marcadores["inimigos"]]
        self.inimigos = [e for e in self.inimigos if e is not None]
        self.itens = [criar_minerio(d) for d in marcadores["minerios"]]
        self.curas = [criar_cura(d) for d in marcadores["curas"]]
        self._curas_iniciais = [dict(d) for d in marcadores["curas"]]
        self.area_boss = montar_area_boss(nome, marcadores["area_boss"])
        self.boss = None
        if self.area_boss:
            self.boss = criar_boss(self)
            self.inimigos.append(self.boss)

    def reiniciar_boss(self):
        """
        Recomeça a luta do zero: troca a instância do boss por uma nova (a
        antiga sai da lista — nada de boss duplicado nem estado herdado) e
        devolve as maçãs da arena.
        """
        if self.area_boss is None:
            return None
        if self.boss in self.inimigos:
            self.inimigos.remove(self.boss)
        self.boss = criar_boss(self)
        self.inimigos.append(self.boss)
        self.curas[:] = [criar_cura(d) for d in self._curas_iniciais]
        return self.boss

    @property
    def largura_px(self):
        return self.world.colunas * T

    @property
    def altura_px(self):
        return self.world.linhas * T

    def __repr__(self):
        return (f"Setor({self.nome}: {self.world.colunas}x{self.world.linhas}, "
                f"{len(self.inimigos)} inimigos, {len(self.itens)} minerios)")


def _mensagem_csv_faltando(arquivo):
    """Explica o que falta e o que existe na pasta — o erro mais comum é o
    arquivo estar com outro nome (ex.: 'floresta.csv.txt', 'floresta (1).csv')."""
    pasta = ASSETS_PATH / "levels" / constants.PASTA_SETORES
    if pasta.is_dir():
        achados = sorted(p.name for p in pasta.iterdir()) or ["(pasta vazia)"]
        situacao = "Arquivos encontrados nessa pasta: " + ", ".join(achados)
    else:
        situacao = "A pasta nao existe."
    esperados = ", ".join(c["arquivo"] for c in constants.SETORES.values())
    return (f"Mapa do setor nao encontrado: {pasta / arquivo}\n"
            f"  {situacao}\n"
            f"  O jogo precisa de: {esperados}\n"
            f"  Confira se o nome nao ficou como '{arquivo}.txt' (o Windows esconde"
            f" extensoes) ou '{arquivo[:-4]} (1).csv'.")


def criar_inimigo(dados):
    """
    Instancia o inimigo já na posição certa.

    A instância é criada duas vezes de propósito: a primeira só para MEDIR o
    rect real (depende do sprite, que só é conhecido depois de carregado), a
    segunda já com o x/y final. É barato — os frames ficam em cache por
    classe — e preserva as invariantes calculadas no __init__ de cada
    subclasse (a Aranha guarda `ancora_x` e `altura_inicial` ali).
    """
    classe = CLASSES_INIMIGO.get(dados["classe"])
    if classe is None:
        print(f"Inimigo de classe desconhecida ignorado: {dados['classe']}")
        return None
    molde = classe(x=0, y=0)
    largura, altura = molde.rect.width, molde.rect.height
    x = dados["col"] * T + (T - largura) // 2
    if dados.get("ancora") == "teto":
        y = (dados["row"] + 1) * T + dados.get("altura", 0) * T
    else:
        y = dados["row"] * T - altura - dados.get("altura", 0) * T
    return classe(x=x, y=y)


def criar_minerio(dados):
    """Minério centralizado na coluna e apoiado no topo do bloco declarado."""
    tam = constants.MINERIO_SIZE
    return minerio_cobre(
        "m_minerio.png",
        x=dados["col"] * T + (T - tam) // 2,
        y=dados["row"] * T - tam,
        tamanho=(tam, tam),
    )


def criar_cura(dados):
    """Maçã centralizada na coluna e apoiada no topo do bloco declarado."""
    tam = constants.ITEM_CURA_SIZE
    return ItemCura("maca.png", x=dados["col"] * T + (T - tam) // 2,
                    y=dados["row"] * T - tam, tamanho=(tam, tam))


def criar_boss(setor):
    """Gorila no marcador da arena, apoiado no chão e ligado ao mundo."""
    col, linha = setor.area_boss["marcador"]
    molde = CLASSE_BOSS(x=0, y=0)
    boss = CLASSE_BOSS(x=col * T + (T - molde.rect.width) // 2,
                       y=(linha + 1) * T - molde.rect.height)
    boss.conectar(setor.world, pygame.Rect(0, 0, setor.largura_px, setor.altura_px))
    boss.direcao = -1   # começa olhando para a entrada da arena
    return boss


def montar_area_boss(nome_setor, marcador):
    """
    Limites da arena do boss, em pixels do setor, ou None se o setor não for
    a arena. O boss nasce no marcador; a luta começa quando o jogador entra
    em `rect` (main._checar_inicio_da_luta).
    """
    dados = getattr(nivel_dados, "AREA_BOSS", None)
    if dados is None or dados.get("setor") != nome_setor:
        return None
    rect = pygame.Rect(
        dados["c0"] * T,
        dados["linha_topo"] * T,
        (dados["c1"] - dados["c0"] + 1) * T,
        (dados["linha_chao"] - dados["linha_topo"]) * T,
    )
    return {"rect": rect, "marcador": marcador or dados["marcador"],
            "setor": nome_setor}


def carregar_setores(tiles, tile_fallback):
    """Monta todos os setores de constants.SETORES e confere as ligações."""
    setores = {
        nome: Setor(nome, config, tiles, tile_fallback)
        for nome, config in constants.SETORES.items()
    }
    inicial = setores.get(constants.SETOR_INICIAL)
    if inicial is None or inicial.player_spawn is None:
        raise ErroMapa(f"setor inicial '{constants.SETOR_INICIAL}' sem marcador "
                       f"de spawn do player ({constants.TILE_PLAYER_SPAWN})")
    for setor in setores.values():
        for passagem in setor.passagens.itens:
            destino = passagem.destino
            alvo = setores.get(destino.get("setor"))
            if alvo is None or destino.get("chegada") not in alvo.chegadas:
                print(f"Aviso: passagem em '{setor.nome}' aponta para "
                      f"{destino.get('setor')}/{destino.get('chegada')}, que nao existe")
    return setores