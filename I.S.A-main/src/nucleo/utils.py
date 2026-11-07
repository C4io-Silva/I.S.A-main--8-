import os
import sys
import time
from functools import lru_cache
from pathlib import Path

import pygame

from src.nucleo import constants

# Suporte a executável empacotado (PyInstaller) e execução normal
from src.nucleo.caminhos import RAIZ as ROOT

ASSETS_PATH = ROOT / "assets"


@lru_cache(maxsize=256)
def _carregar_imagem_cache(pasta_interna, nome_arquivo, escala):
    caminho = ASSETS_PATH / "images" / pasta_interna / nome_arquivo

    img = pygame.image.load(str(caminho)).convert_alpha()
    if escala:
        img = pygame.transform.scale(img, escala)
    return img


def carregar_imagem(pasta_interna, nome_arquivo, escala=None):
    """
    Carrega uma imagem de assets/images/<pasta>/<arquivo>.

    O disco é lido UMA vez por (arquivo, escala); as chamadas seguintes saem
    do cache. Isso importa porque havia carga repetida em massa: cada um dos
    27 minérios do mapa abria o MESMO PNG no disco no seu __init__ — 241 ms
    só nisso, dentro dos 811 ms de carregamento do nível.

    Devolve uma CÓPIA, não a Surface do cache. Sem isso, qualquer chamador que
    desenhasse sobre a imagem (ou trocasse o alpha dela) corromperia a cópia
    de todo mundo — um bug que só apareceria muito longe da causa. Copiar
    custa microssegundos; ler o disco custa milissegundos.
    """
    return _carregar_imagem_cache(pasta_interna, nome_arquivo, escala).copy()


def carregar_tile(nome_arquivo, tamanho):
    return carregar_imagem("tiles", nome_arquivo, (tamanho, tamanho))


def _tile_placeholder(tamanho):
    """
    Surface de emergência (xadrez magenta/preto) para quando NENHUM sprite
    pôde ser carregado — nem o do fallback. Segue a convenção clássica de
    "textura faltando": aparece na tela sem derrubar o jogo.
    """
    s = pygame.Surface((tamanho, tamanho))
    s.fill((255, 0, 255))
    meio = tamanho // 2
    preto = (0, 0, 0)
    pygame.draw.rect(s, preto, (0, 0, meio, meio))
    pygame.draw.rect(s, preto, (meio, meio, tamanho - meio, tamanho - meio))
    return s


def carregar_tiles(tile_sprites, tamanho, fallback_id=0):
    """
    Constrói o dicionário {ID: Surface} a partir do mapa ID->arquivo definido
    em constants.TILE_SPRITES.

    - Cada arquivo é lido do disco UMA vez, mesmo que vários IDs o usem
      (cache interno por nome de arquivo).
    - IDs cujo arquivo não exista caem no sprite do fallback_id, para o jogo
      nunca quebrar por um asset faltando durante o desenvolvimento.
    - Retorna (tiles, fallback): o dict e a Surface de fallback já resolvida,
      que World.process_data usa para IDs que aparecem no CSV mas não estão
      no mapa.
    """
    cache = {}   # nome_arquivo -> Surface (ou None se falhou)
    tiles = {}

    for tile_id, nome in tile_sprites.items():
        if nome not in cache:
            try:
                cache[nome] = carregar_tile(nome, tamanho)
            except (FileNotFoundError, pygame.error):
                cache[nome] = None
        tiles[tile_id] = cache[nome]

    fallback = tiles.get(fallback_id) or _tile_placeholder(tamanho)

    # Substitui os que falharam pelo fallback já resolvido
    for tile_id, surf in tiles.items():
        if surf is None:
            tiles[tile_id] = fallback

    return tiles, fallback


def carregar_fundo(pasta_interna, nome_arquivo, tamanho):
    """
    Carrega uma imagem de fundo cobrindo o espaço pedido SEM distorcer.

    Diferente de carregar_imagem(..., escala), que estica a imagem para as
    dimensões exatas: aqui a proporção original é mantida, a imagem é
    ampliada até cobrir os dois eixos e o excedente é recortado pelo centro.
    Necessário desde que a largura da tela virtual passou a variar conforme
    o formato do monitor — antes, com 800x600 fixo, esticar não fazia mal.
    """
    largura_alvo, altura_alvo = tamanho
    img = carregar_imagem(pasta_interna, nome_arquivo)
    largura_orig, altura_orig = img.get_size()

    # max() garante cobertura total; min() deixaria faixas vazias
    fator = max(largura_alvo / largura_orig, altura_alvo / altura_orig)
    ampliada = pygame.transform.smoothscale(
        img, (max(1, int(largura_orig * fator)), max(1, int(altura_orig * fator)))
    )

    recorte = pygame.Surface((largura_alvo, altura_alvo), pygame.SRCALPHA)
    recorte.blit(
        ampliada,
        (
            (largura_alvo - ampliada.get_width()) // 2,
            (altura_alvo - ampliada.get_height()) // 2,
        ),
    )
    return recorte.convert_alpha()


@lru_cache(maxsize=64)
def carregar_fonte(nome_fonte, tamanho):
    """
    Carrega uma fonte do disco. O resultado é cacheado por (nome, tamanho),
    porque várias telas chamam isso dentro do loop de render — sem cache,
    um objeto Font novo era criado a cada frame.

    Objetos Font do pygame não guardam estado entre chamadas de render(),
    então compartilhar a mesma instância é seguro.
    """
    caminho = ASSETS_PATH / "fonts" / nome_fonte
    return pygame.font.Font(str(caminho), tamanho)


@lru_cache(maxsize=64)
def carregar_fonte_typewriter(tamanho, bold=True):
    """
    Fonte de leitura (Century Gothic do sistema) para enunciados e
    alternativas do quiz e da tela de estatísticas.

    A fonte pixel (upheavtt) fica nos títulos e na HUD; texto longo de
    pergunta fica bem mais legível numa sans-serif. Ordem de tentativa:
    Century Gothic, Arial, Verdana, Helvetica — o pygame usa a primeira que
    existir no computador e cai na fonte padrão se nenhuma existir.

    Cacheada por (tamanho, bold) pelo mesmo motivo de carregar_fonte: é
    chamada dentro do loop de desenho, e SysFont é caro de criar.
    """
    return pygame.font.SysFont(
        "century gothic,arial,verdana,helvetica,sans-serif",
        max(8, int(tamanho)),
        bold=bold,
    )


def carregar_musica(nome_arquivo, pasta_interna="music"):
    caminho = ASSETS_PATH / pasta_interna / nome_arquivo
    return str(caminho)


class ErroMapa(ValueError):
    """CSV de nível malformado: a mensagem diz linha e coluna do problema."""


def carregar_nivel_csv(nome_arquivo):
    """
    Lê o CSV do nível como matriz de inteiros (ver MAPA-CSV.md).

    Aceita o arquivo como o Excel/LibreOffice salvam: separador vírgula OU
    ponto e vírgula, UTF-8 com ou sem BOM, ANSI (cp1252) e separador sobrando
    no fim da linha (ver src/dados_csv.py).

    Falha com ErroMapa, apontando linha/coluna, se houver célula não numérica
    ou linhas de larguras diferentes. IDs desconhecidos não derrubam o jogo
    (viram o bloco de fallback), mas são avisados no console.
    """
    from src.quiz.dados_csv import ler_grade

    caminho = ASSETS_PATH / "levels" / nome_arquivo
    world_data = []
    for n_linha, row in ler_grade(str(caminho)):
        try:
            world_data.append([int(v) for v in row])
        except ValueError:
            col = next(i for i, v in enumerate(row, start=1)
                       if not v.strip().lstrip("-").isdigit())
            raise ErroMapa(f"{nome_arquivo}: valor invalido na linha {n_linha}, "
                           f"coluna {col}: {row[col - 1]!r}") from None
    if not world_data:
        raise ErroMapa(f"{nome_arquivo}: arquivo vazio")
    larguras = {len(linha) for linha in world_data}
    if len(larguras) > 1:
        curtas = [i for i, l in enumerate(world_data, start=1) if len(l) != len(world_data[0])]
        raise ErroMapa(f"{nome_arquivo}: linhas com larguras diferentes {sorted(larguras)} "
                       f"(primeira divergente: linha {curtas[0] if curtas else '?'})")

    estranhos = ids_desconhecidos(world_data)
    if estranhos:
        print(f"Aviso: {nome_arquivo} tem IDs sem significado {sorted(estranhos)} "
              f"(desenhados como bloco padrao)")
    return world_data


def ids_desconhecidos(world_data):
    """IDs da grade que não são terreno, marcador nem vazio."""
    conhecidos = set(constants.TILE_SPRITES) | set(constants.TILES_MARCADORES) | {-1}
    return {v for linha in world_data for v in linha} - conhecidos


def extrair_marcadores(world_data, apagar=True):
    """
    Varre a grade do CSV e devolve tudo que NÃO é terreno: spawn do player,
    inimigos, minérios, entradas de passagem e pontos de chegada.

    Esta função é a metade "leitura" do mapa data-driven. A outra metade é
    constants.PASSAGENS_CSV, que diz o que cada ID significa. Aqui não há
    NENHUMA coordenada fixa: a posição de cada coisa é a célula em que o
    marcador foi desenhado no CSV.

    Convenção (a mesma para todos): a célula do marcador é a célula que a
    entidade ocupa. Como o resto do jogo (_assentar, _criar_inimigo) trabalha
    com "linha do bloco de apoio", a conversão é feita aqui, num lugar só:
        chão  -> row = linha_do_marcador + 1  (apoia no bloco de baixo)
        teto  -> row = linha_do_marcador - 1  (pendura no bloco de cima)

    apagar=True troca cada marcador por VAZIO na própria grade recebida. É o
    que impede o marcador de virar um tile visível: World.process_data manda
    qualquer ID desconhecido para o sprite de fallback, então um 91 esquecido
    na grade apareceria como um tijolo sólido no meio do mapa.

    Devolve dict com as chaves: player, inimigos, minerios, passagens,
    chegadas, area_boss. `player` é None se o CSV não tiver o marcador — quem chama
    decide o que fazer (main.py cai no valor antigo de nivel_dados).
    """
    VAZIO = -1
    achados = {
        "player": None,
        "inimigos": [],
        "minerios": [],
        "curas": [],       # itens de cura (maçã), mesma convenção do minério
        "passagens": {},   # (linha, coluna) -> dados da entrada
        "chegadas": {},    # id do marcador de chegada -> (coluna, linha)
        "area_boss": None,  # (coluna, linha) do marcador da arena, se houver
    }

    for linha_idx, linha in enumerate(world_data):
        for col_idx, tile_id in enumerate(linha):
            if tile_id not in constants.TILES_MARCADORES:
                continue

            if tile_id == constants.TILE_PLAYER_SPAWN:
                achados["player"] = (col_idx, linha_idx + 1)

            elif tile_id == constants.TILE_AREA_BOSS:
                achados["area_boss"] = (col_idx, linha_idx)

            elif tile_id == constants.TILE_ITEM_CURA:
                achados["curas"].append({"col": col_idx, "row": linha_idx + 1})

            elif tile_id == constants.TILE_MINERIO:
                achados["minerios"].append(
                    {"col": col_idx, "row": linha_idx + 1, "regiao": ""}
                )

            elif tile_id in constants.MARCADORES_MOB:
                classe, ancora = constants.MARCADORES_MOB[tile_id]
                row = linha_idx - 1 if ancora == "teto" else linha_idx + 1
                achados["inimigos"].append({
                    "col": col_idx, "row": row, "classe": classe,
                    "altura": 0, "regiao": "", "ancora": ancora,
                })

            elif tile_id in constants.TILES_PASSAGEM:
                # A entrada some da grade como qualquer outro marcador: quem a
                # desenha agora é src/passagens.py, como estrutura de cenário.
                # Deixá-la aqui faria World.process_data mandá-la para o sprite
                # de fallback — ou seja, um tijolo no meio da entrada.
                achados["passagens"][(linha_idx, col_idx)] = dict(
                    constants.PASSAGENS_CSV[tile_id], id_tile=tile_id
                )

            elif tile_id in constants.TILES_CHEGADA:
                achados["chegadas"][tile_id] = (col_idx, linha_idx)

            if apagar:
                linha[col_idx] = VAZIO

    return achados


# Nomes procurados para o CSV dos professores, em ordem de prioridade.
# O lugar oficial é "banco de dados/" (é onde converter_perguntas.py grava).
# A subpasta "perguntas/" (usada no fork do boss) ainda é aceita.
CAMINHOS_PERGUNTAS_PROFESSORES = (
    Path("perguntas_professores.csv"),
    Path("perguntas") / "perguntas_professores.csv",
)
CAMINHOS_PERGUNTAS_PADRAO = (
    Path("perguntas.csv"),
    Path("perguntas") / "perguntas.csv",
)

# Últimos problemas encontrados na leitura (mostrados no console e usados
# pelos testes / validar_dados.py).
PROBLEMAS_PERGUNTAS = {}


def _achar_banco(relativos):
    for relativo in relativos:
        candidato = ASSETS_PATH / "banco de dados" / relativo
        if candidato.exists():
            return candidato
    return None


def _relatar(caminho, problemas):
    PROBLEMAS_PERGUNTAS[str(caminho)] = problemas
    if problemas:
        print(f"Aviso: {len(problemas)} problema(s) em {caminho}:")
        for p in problemas[:15]:
            print(f"   - {p}")
        if len(problemas) > 15:
            print(f"   ... e mais {len(problemas) - 15} (rode python validar_dados.py)")


def carregar_perguntas_professores(caminho=None):
    """
    Lê o CSV de perguntas dos professores (gerado por converter_perguntas.py
    a partir do Word, ou editado à mão) no formato único do jogo.

    Aceita o cabeçalho do converter (pergunta, alt_a..alt_d, correta,
    categoria[, dificuldade]) ou o mesmo cabeçalho do banco padrão. Sem
    coluna de dificuldade, a pergunta entra como "Médio" — antes ela recebia
    "Professor", que nenhuma fase aceitava, e sumia do jogo.

    O arquivo é OPCIONAL: ausente ou vazio -> lista vazia.
    """
    from src.quiz.dados_csv import ler_perguntas

    caminho = caminho or _achar_banco(CAMINHOS_PERGUNTAS_PROFESSORES)
    if caminho is None:
        return []
    perguntas, problemas = ler_perguntas(str(caminho), origem="professor")
    _relatar(caminho, problemas)
    if perguntas:
        print(f" {len(perguntas)} perguntas de professores carregadas")
    return perguntas


def obter_alternativas_pergunta(pergunta):
    """
    Extrai as alternativas não vazias de uma pergunta como lista de
    tuplas (letra, texto), na ordem A..E.

    Aceita tanto as chaves sem acento (opcao_a..e) quanto as chaves com
    acento (opçao_a..e) de CSVs antigos.
    """
    letras = ["a", "b", "c", "d", "e"]
    resultado = []
    for letra in letras:
        texto = pergunta.get(f"opcao_{letra}", "") or pergunta.get(f"opçao_{letra}", "")
        texto = str(texto).strip()
        if texto and texto.lower() != "nan":
            resultado.append((letra, texto))
    return resultado


def carregar_perguntas_csv(nome_arquivo="perguntas.csv"):
    """
    Lê o banco de perguntas padrão e devolve a lista no formato único
    (ver src/dados_csv.ler_perguntas). Linhas inválidas são puladas e
    listadas no console — nunca derrubam o jogo.

    O arquivo é lido do disco A CADA chamada: editar o CSV e iniciar uma
    nova partida (ou reabrir o jogo) já usa o conteúdo novo.
    """
    from src.quiz.dados_csv import ler_perguntas

    caminho = ASSETS_PATH / "banco de dados" / nome_arquivo
    if not caminho.exists():
        caminho = _achar_banco(CAMINHOS_PERGUNTAS_PADRAO) or caminho
    perguntas, problemas = ler_perguntas(str(caminho), origem="padrao")
    _relatar(caminho, problemas)
    return perguntas

def texto_contorno(fonte, texto, cor, cor_contorno, espessura=3, sombra=(0, 4)):
    """Renderiza texto com contorno grosso e sombra. Devolve uma Surface."""
    base = fonte.render(texto, True, cor)
    borda = fonte.render(texto, True, cor_contorno)
    w = base.get_width() + espessura * 2 + sombra[0]
    h = base.get_height() + espessura * 2 + sombra[1]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    # sombra
    for dx in range(-espessura, espessura + 1):
        for dy in range(-espessura, espessura + 1):
            surf.blit(borda, (espessura + dx + sombra[0], espessura + dy + sombra[1]))
    # contorno
    for dx in range(-espessura, espessura + 1):
        for dy in range(-espessura, espessura + 1):
            if dx or dy:
                surf.blit(borda, (espessura + dx, espessura + dy))
    # letra
    surf.blit(base, (espessura, espessura))
    return surf