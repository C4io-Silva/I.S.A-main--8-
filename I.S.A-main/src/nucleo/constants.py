# ── Tela ──────────────────────────────────────────────────────────────────────
FPS            = 60
SCREEN_WIDTH   = 800
SCREEN_HEIGHT  = 600

# ── Player ────────────────────────────────────────────────────────────────────
PLAYER_HEALTH  = 80
DAMAGE         = 15

# ── Botões ────────────────────────────────────────────────────────────────────
BTN_LARGURA = 200
BTN_ALTURA  = 60

# ── Mundo ─────────────────────────────────────────────────────────────────────
# SCALE é o zoom do mundo. O sprite do tile tem 16px de origem, então SCALE=3
# gera tiles de 48px — ampliação inteira, pixels nítidos.
#
# DIMINUIR o SCALE afasta a câmera (vê mais mapa). AUMENTAR aproxima.
#   SCALE = 5  ->  80px  ->  10,0 x  7,5 tiles na tela   (original, apertado)
#   SCALE = 4  ->  64px  ->  12,5 x  9,4 tiles
#   SCALE = 3  ->  48px  ->  16,7 x 12,5 tiles
#   SCALE = 2  ->  32px  ->  25,0 x 18,8 tiles
SCALE      = 3
TILE_SIZE  = 16 * SCALE

# ID usado quando o CSV pede um tile cujo sprite não existe (ou falha ao
# carregar). Serve de rede de segurança: o mapa nunca fica com buracos.
TILE_FALLBACK_ID = 0

# IDs de tile que são sólidos (colidíveis).
# Fonte única da verdade: usado por src/world.py e por main.py.
# União dos conjuntos das duas versões do projeto: os blocos originais
# (0, 6, 7) mais os tipos de terreno da tabela TILE_SPRITES.
SOLID_TILES = {0, 1, 2, 3, 4, 6, 7, 10, 11, 12, 13, 14, 15, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 36, 37, 60, 61, 62, 63}

# Mapa ID -> arquivo de sprite (dentro de assets/images/tiles).
# IDs sem entrada aqui — ou com arquivo ausente — usam TILE_FALLBACK_ID.
TILE_SPRITES = {
    0:  "tile_brick.png",   # bloco genérico
    1:  "pro_grama_viva.png",
    2:  "pro_terra_raiz.png",
    3:  "areia.png",
    4:  "pedra.png",
    5:  "agua.png",
    10: "grama_var1.png",
    11: "grama_var2.png",
    20: "pro_terra_funda.png",
    12: "pro_grama_flores.png",
    13: "pro_grama_raizes.png",
    14: "pro_copa.png",
    15: "pro_copa_var.png",
    21: "pro_terra_raiz.png",
    22: "pro_terra_pedra.png",
    23: "pro_terra_funda.png",
    24: "pro_rocha.png",
    25: "pro_rocha_var.png",
    26: "pro_rocha_cristal.png",
    27: "pro_templo.png",
    28: "pro_templo_var.png",
    29: "pro_templo_laje.png",
    36: "tronco_copas.png",
    37: "tronco_copas_var.png",
    50: "decor_flor.png",
    51: "decor_arbusto.png",
    52: "decor_samambaia.png",
    53: "decor_cristal.png",
    54: "decor_cogumelo.png",
    55: "decor_cipo.png",
    56: "decor_folhas.png",
    57: "decor_estalactite.png",
    58: "decor_tocha.png",
    59: "decor_runas.png",
    60: "pro_ponte_raiz.png",
    61: "pro_viga_mina.png",
    62: "pro_galho_copa.png",
    63: "pro_laje_templo.png",
}

# Novos blocos complementares da Floresta v0.6 (somente mapa).
# 67 (isa_v04_raiz_escora) e so VISUAL, como 5 e 50-59: no mapa ele e sempre o pilar de raiz
# debaixo das passarelas 64. Solido, cada pilar que chega ao chao vira parede (o spawn ficava
# preso nas colunas 0-17). Ver docs/integracao_final/LOG_INTEGRACAO.md, fase C.
SOLID_TILES.update({64,65,66})
TILE_SPRITES.update({64:'isa_v04_raiz_passarela.png',65:'isa_v04_monte_musgo.png',66:'isa_v04_tunel_rocha.png',67:'isa_v04_raiz_escora.png'})

# IDs de tile de PASSAGEM (troca de setor). NÃO entram em SOLID_TILES nem em
# TILE_SPRITES: são apagados da grade ao carregar e desenhados como cenário
# por src/passagens.py.
TILE_PASSAGEM_CAVERNA  = 30  # na floresta: entrada/buraco -> leva à caverna
TILE_PASSAGEM_COPAS    = 31  # na floresta: pé do cipó     -> leva às copas
TILE_PASSAGEM_FLORESTA = 32  # na caverna: saída            -> volta à floresta
TILE_PASSAGEM_FLORESTA_COPAS = 33  # nas copas: saída       -> volta à floresta
TILE_PASSAGEM_ARENA    = 34  # no alto das copas: entrada  -> arena do boss
TILE_PASSAGEM_SAIDA_ARENA = 35  # na arena: saída          -> volta às copas

# ── Setores do mapa ───────────────────────────────────────────────────────────
# Cada setor é um CSV próprio em assets/levels/setores/ e é uma "fase" do
# ponto de vista do mundo: tem seu próprio tamanho, seus inimigos, minérios,
# passagens e chegadas. O jogador só troca de setor por uma passagem (com o
# fade de src/transicao.py). Todos são carregados no início da partida, então
# o que acontece num setor (minério coletado, inimigo derrotado) continua
# valendo quando o jogador volta. Ver MAPA-CSV.md.
PASTA_SETORES = "setores"
SETOR_INICIAL = "floresta"
SETORES = {
    # nome: arquivo CSV e ambiente visual (chave de AMBIENTES) do setor
    "floresta": {"arquivo": "floresta.csv", "ambiente": "floresta"},
    "caverna":  {"arquivo": "caverna.csv",  "ambiente": "caverna"},
    "copas":    {"arquivo": "copas.csv",    "ambiente": "copas"},
    "arena":    {"arquivo": "arena.csv",    "ambiente": "arena"},
}

# ── Mapa data-driven: marcadores do CSV ───────────────────────────────────────
# O CSV passou a definir ONDE cada coisa está; este arquivo define O QUE cada
# ID significa e main.py define COMO ela se comporta. Antes a posição de
# player, inimigos, minérios e destinos morava em listas Python dentro de
# src/nivel_dados.py: mover um tile de passagem no CSV não movia a entrada
# junto, e o jogo não tinha como perceber — a passagem só parava de funcionar.
#
# CONVENÇÃO ÚNICA, válida para todo marcador: a CÉLULA DO MARCADOR É A CÉLULA
# QUE A ENTIDADE OCUPA. Um 92 na linha 25 significa "a cobra está na linha 25",
# apoiada no bloco de baixo. Nada de "linha da superfície + altura flutuante":
# é isso que permite arrastar o marcador no CSV e ver a entidade obedecer.
#
# Nenhum destes IDs entra em SOLID_TILES nem em TILE_SPRITES: marcador não tem
# colisão nem sprite. Os de entidade e de chegada são apagados da grade assim
# que lidos (utils.extrair_marcadores), então não chegam a ser desenhados.
TILE_PLAYER_SPAWN = 90
TILE_MINERIO      = 91
TILE_MOB_COBRA    = 92
TILE_MOB_TUCANO   = 93
TILE_MOB_ARANHA   = 94  # pendura no teto: usa o bloco de CIMA como âncora

# Arena do boss. O marcador fica na célula logo acima do CHÃO da arena, no
# centro: é ali que o Gorila nasce (src/setores.py). Os limites da luta vêm
# de src/nivel_dados.AREA_BOSS. Nenhum inimigo comum ou minério pode ser
# colocado dentro dela (ver gerar_mundo.validar_area_boss).
TILE_AREA_BOSS    = 95
# Item de cura (maçã do fork do boss). No fork ele usava o ID 95, que aqui já
# era a arena — por isso mudou para 96.
TILE_ITEM_CURA    = 96

# ID do marcador -> (classe do inimigo, âncora). A classe é resolvida em
# main.py por CLASSES_INIMIGO; um ID desconhecido é ignorado com aviso, nunca
# derruba o carregamento do nível.
MARCADORES_MOB = {
    TILE_MOB_COBRA:  ("Enemy",  "chao"),
    TILE_MOB_TUCANO: ("Tucano", "chao"),
    TILE_MOB_ARANHA: ("Aranha", "teto"),
}

# Marcadores de CHEGADA: onde o player reaparece depois de uma transição.
# Substituem o dict SPAWNS, que guardava coordenadas em PIXELS num arquivo
# gerado — impossível de posicionar olhando o mapa.
TILE_CHEGADA_CAVERNA      = 40  # destino de TILE_PASSAGEM_CAVERNA
TILE_CHEGADA_COPAS        = 41  # destino de TILE_PASSAGEM_COPAS
TILE_CHEGADA_FLOR_CAVERNA = 42  # destino de TILE_PASSAGEM_FLORESTA
TILE_CHEGADA_FLOR_COPAS   = 43  # destino de TILE_PASSAGEM_FLORESTA_COPAS
TILE_CHEGADA_ARENA        = 44  # destino de TILE_PASSAGEM_ARENA
TILE_CHEGADA_COPAS_ARENA  = 45  # destino de TILE_PASSAGEM_SAIDA_ARENA

# A tabela que amarra entrada -> ambiente de destino -> célula de chegada.
# É ISTO que substitui o antigo nivel_dados.PASSAGENS com chave (linha,coluna):
# a posição sumiu daqui de propósito. Onde a entrada está é problema do CSV;
# para onde ela leva é problema desta tabela.
PASSAGENS_CSV = {
    TILE_PASSAGEM_CAVERNA: {
        "tipo": "CAVE_ENTRY",    "setor": "caverna",
        "chegada": TILE_CHEGADA_CAVERNA,
    },
    TILE_PASSAGEM_COPAS: {
        "tipo": "CANOPY_ENTRY",  "setor": "copas",
        "chegada": TILE_CHEGADA_COPAS,
    },
    TILE_PASSAGEM_FLORESTA: {
        "tipo": "CAVE_EXIT",     "setor": "floresta",
        "chegada": TILE_CHEGADA_FLOR_CAVERNA,
    },
    TILE_PASSAGEM_FLORESTA_COPAS: {
        "tipo": "CANOPY_EXIT",   "setor": "floresta",
        "chegada": TILE_CHEGADA_FLOR_COPAS,
    },
    TILE_PASSAGEM_ARENA: {
        "tipo": "ARENA_ENTRY",   "setor": "arena",
        "chegada": TILE_CHEGADA_ARENA,
    },
    TILE_PASSAGEM_SAIDA_ARENA: {
        "tipo": "ARENA_EXIT",    "setor": "copas",
        "chegada": TILE_CHEGADA_COPAS_ARENA,
    },
}
# O ambiente de destino sai do setor (uma fonte só da verdade).
for _dados in PASSAGENS_CSV.values():
    _dados["ambiente"] = SETORES[_dados["setor"]]["ambiente"]

TILES_CHEGADA = frozenset(d["chegada"] for d in PASSAGENS_CSV.values())
TILES_PASSAGEM = frozenset(PASSAGENS_CSV)
MARCADORES_ENTIDADE = frozenset(
    {TILE_PLAYER_SPAWN, TILE_MINERIO, TILE_AREA_BOSS, TILE_ITEM_CURA} | set(MARCADORES_MOB)
)
# Tudo que o CSV pode conter além de terreno — usado pela validação para não
# acusar "ID desconhecido" e por utils.extrair_marcadores para varrer a grade.
TILES_MARCADORES = MARCADORES_ENTIDADE | TILES_CHEGADA | TILES_PASSAGEM

# Não existe mais MAP_ROWS/MAP_COLS global: cada setor tem o seu tamanho,
# lido do próprio CSV (World.linhas / World.colunas).

# ── Ambientes (backgrounds da fase) ──────────────────────────────────────────
# Importado do ISA Kauan (src/ambientes.py) e depois adaptado. A fase
# continua sendo UMA só; o que muda entre copas/floresta/caverna é só o
# conjunto de camadas de paralaxe, a tonalidade e as partículas ao fundo.
#
# Cada camada é (arquivo_png, fator_de_paralaxe). O fator é o quanto a camada
# acompanha a câmera no eixo X: 0.0 = parada (infinitamente distante),
# 1.0 = colada no mundo. Camadas de fundo vêm primeiro e usam fatores menores.
#
# "estilo" só entra em cena quando o PNG NÃO existe: aí o jogo desenha uma
# silhueta procedural, para o ambiente já ficar jogável antes da arte final.
#
# Fundos oficiais confirmados pelo grupo (pacote "Cenário 1"):
#   Floresta: fundo_cenario01.png (longe, 0.25) + frente_cenario01.png (perto, 0.50)
#   Copas:    floresta_cenario_01.png (0.25) + nuvens_cenario_01.png (0.55)
# A Floresta continua sendo a zona neutra (tint/luz neutros).
# Os antigos pro_*.png, C1.png e C2.png continuam na pasta como referência.
AMBIENTES = {
    "copas": {
        "estilo": "copas",
        "cor_ceu": (168, 206, 150),
        "camadas": [
            ("floresta_cenario_01.png", 0.25),
            ("nuvens_cenario_01.png", 0.55),
        ],
        "tint": (255, 252, 235),
        "luz": (14, 12, 0),
    },
    "floresta": {
        "estilo": "floresta",
        "cor_ceu": (126, 176, 209),
        "camadas": [
            ("fundo_cenario01.png", 0.25),
            ("frente_cenario01.png", 0.50),
        ],
        "tint": (255, 255, 255),
        "luz": (0, 0, 0),
    },
    "arena": {
        "estilo": "caverna",
        "cor_ceu": (36, 32, 43),
        "camadas": [("pro_arena_fundo.png", 0.13)],
        "tint": (255, 250, 240),
        "luz": (0, 0, 0),
    },
    "caverna": {
        "estilo": "caverna",
        "cor_ceu": (18, 14, 26),
        "camadas": [
            ("caverna_fundo.png", 0.20),
            ("caverna_frente.png", 0.45),
        ],
        "tint": (120, 115, 155),
        "luz": (0, 0, 0),
    },
}

# MODO DE OPERAÇÃO DO GerenciadorAmbientes (src/ambientes.py):
#
#   True  (padrão atual) -> DISCRETO. O ambiente só troca quando main.py
#          chama ambientes.forcar(nome) — e isso só acontece dentro do
#          callback de uma Transicao (Fade Out -> troca -> Fade In), disparado
#          por o player usar um tile de passagem (ver main._resolver_passagem). Não
#          existe blend nem leitura contínua da posição do player.
#
#   False -> CONTÍNUO (comportamento original desta seção, mantido no código
#          por trás da flag em vez de apagado). O ambiente é lido a cada
#          frame a partir de ZONAS_AMBIENTE + a altura do player, com
#          dissolução suave nas fronteiras. Ainda funciona se algum dia fizer
#          sentido voltar a esse modelo — só não é mais o padrão, porque a
#          troca contínua por coordenada Y foi exatamente o que esta rodada
#          de mudanças pediu pra tirar.
AMBIENTE_MODO_DISCRETO = True

EIXO_AMBIENTE = "y"

# Usadas só quando AMBIENTE_MODO_DISCRETO = False (modo contínuo antigo).
# Calibradas para a v1 do level1_mapa.csv (chão único, sem regiões separadas
# por parede) — se o modo contínuo for reativado num mapa diferente, estes
# três números precisam ser recalibrados para bater com as linhas reais de
# chão/platô/piso do CSV em uso.
ZONAS_AMBIENTE = [
    (0,  "copas"),
    (6,  "floresta"),
    (14, "caverna"),
]
TRANSICAO_TILES = 3
SUAVIZACAO_AMBIENTE = 0.04

# ── Escala derivada ───────────────────────────────────────────────────────────
# O jogo foi ajustado originalmente com SCALE = 5. Tudo abaixo é derivado dessa
# referência, para que mudar o SCALE altere apenas o quanto se enxerga — nunca
# a jogabilidade. A altura do pulo e a velocidade MEDIDAS EM TILES ficam
# idênticas em qualquer SCALE, porque velocidade e gravidade escalam juntas.
_SCALE_REF = 5
_K = SCALE / _SCALE_REF

PLAYER_SIZE    = int(75 * _K)
PLAYER_SPEED   = 5 * _K
SPEED_JUMP     = 12 * _K   # pixels/frame (positivo, aplicado para cima)

# O spawn do player não é mais um par de números mágicos: a COLUNA e a LINHA
# DA SUPERFÍCIE vêm de nivel_dados (gerado junto com o CSV), e main.py
# converte para pixels usando a ALTURA REAL do rect do personagem.
#
# Isso conserta um problema silencioso: PLAYER_SIZE é 45, mas o sprite é
# escalado mantendo a proporção, então o rect real do player é 30x45. Um Y
# calibrado "na mão" contra PLAYER_SIZE deixa de valer no dia em que alguém
# trocar a arte do personagem.
#
# PLAYER_START_X/Y continuam existindo, derivados, porque outros pontos do
# projeto (e qualquer script antigo) ainda podem lê-los.
try:
    from src.mundo.nivel_dados import PLAYER_SPAWN
except ImportError:  # pragma: no cover
    PLAYER_SPAWN = (6, 12)

PLAYER_START_X = PLAYER_SPAWN[0] * TILE_SIZE
PLAYER_START_Y = (PLAYER_SPAWN[1] - 1) * TILE_SIZE

VEL_TERMINAL   = 20 * _K   # limite de queda livre

# Quantidade de pulos encadeados antes de tocar o chão (1 = pulo simples,
# 2 = pulo duplo). Contador reiniciado sempre que o player aterrissa.
MAX_JUMPS      = 2
KNOCKBACK_X    = 12 * _K   # empurrão lateral ao levar dano
QUIQUE_Y       = 9 * _K    # impulso ao pular na cabeça do inimigo
# Pisão: cair em cima de cobra, tucano ou aranha DERROTA o inimigo (o boss
# não — ele só quica; o Gorila se vence com as perguntas). False volta ao
# comportamento antigo da v12, em que pular em cima só quicava.
INIMIGOS_MORREM_COM_PISAO = True
# Quantos pixels abaixo do topo do inimigo os pés podiam estar no frame
# ANTERIOR para ainda contar como pisão (folga para quedas rápidas).
PISAO_TOLERANCIA = 10 * _K

# ── Combate da Areninha contra inimigos comuns (src/combate.py) ──────────────
# Golpe de asa: curto, na frente da Areninha, com cooldown. Funciona andando
# e no ar. Não afeta o Gorila (ele se vence pelas perguntas).
# Vida dos comuns = 2: o golpe tira 1 (dois golpes), o pisão tira 2 (continua
# derrubando de uma vez, como já era).
VIDA_INIMIGO_COMUM   = 2
DANO_GOLPE           = 1
DANO_PISAO           = 2
GOLPE_ALCANCE        = int(1.35 * TILE_SIZE)  # px à frente do corpo
GOLPE_ALTURA_EXTRA   = int(0.35 * TILE_SIZE)  # px acima/abaixo do corpo
GOLPE_INICIO_MS      = 40     # antecipação (a asa sobe) antes de acertar
GOLPE_ATIVO_MS       = 140    # janela em que o golpe acerta
GOLPE_COOLDOWN_MS    = 380    # do início de um golpe até poder dar outro
GOLPE_BUFFER_MS      = 120    # apertou um pouco antes do fim do cooldown: sai assim que liberar
# Inimigo atingido: fica atordoado (não anda, não machuca, não toma outro
# golpe) e é empurrado para longe da Areninha.
ATORDOAMENTO_GOLPE_MS = 350
EMPURRAO_GOLPE        = 0.6 * TILE_SIZE    # distância total do empurrão (px); menor que o alcance da asa: dá para emendar o 2º golpe sem andar
BARRA_VIDA_INIMIGO_MS = 1600   # quanto tempo a barrinha fica visível após o dano

ENEMY_SIZE     = int(50 * _K)
ENEMY_SPEED    = 2 * _K
ENEMY_RANGE    = 200 * _K  # alcance da patrulha

# Culling de inimigos: só são atualizados/desenhados os que estão dentro da
# tela mais esta folga (em tiles). 6 tiles cobre com sobra o maior raio de
# detecção (tucano) e o de desistência da cobra, então nenhum comportamento
# perto do jogador muda — só param os que estão longe.
MARGEM_ATIVACAO_TILES = 6

MINERIO_SIZE   = int(40 * _K)
ITEM_CURA_SIZE = int(40 * _K)
ITEM_CURA_VIDA = 15        # quanto a maçã recupera

# ── Boss (Gorila da arena) ───────────────────────────────────────────────────
# Mecânica (veio do fork do boss, ampliada na unificação — ver
# src/enemies/boss.py): o Gorila arremessa BANANAS (desvie) e, uma vez a cada
# ciclo de arremessos, um MINÉRIO (deixe acertar: abre uma pergunta; acertar
# devolve o minério ao boss, que fica atordoado e perde 1 de vida).
GORILA_VIDA               = 8      # minérios devolvidos para vencer
GORILA_DANO_CONTATO       = 15
GORILA_PROJETIL           = "gorila_projetil.png"
GORILA_PROJETIL_SIZE      = int(12 * SCALE)   # 36 px: menor que o jogador
GORILA_PROJETIL_DAMAGE    = 10
GORILA_PROJETIL_SPEED     = 3.6 * SCALE   # fase 1 (px/frame)
GORILA_PROJETIL_SPEED_F2  = 4.5 * SCALE   # fase 2 (o valor do fork)
GORILA_ARREMESSOS_POR_CICLO = 5    # 1 deles é sempre um minério
GORILA_INTERVALO_ATAQUE   = 1400   # ms entre arremessos, fase 1
GORILA_INTERVALO_ATAQUE_F2 = 1000  # fase 2
GORILA_POSE_ARREMESSO     = 450    # aviso (pose) antes de soltar o projétil
GORILA_ATORDOADO_MS       = 3000   # janela de recuperação após levar dano
GORILA_INTRO_MS           = 1600   # aparição: rugido, sem atacar
# Fase 2 (vida <= metade): salto-pancada com onda de choque no chão.
GORILA_PANCADA_AVISO_MS   = 800    # tremor + marcação vermelha antes do salto
GORILA_PANCADA_INTERVALO  = 5200   # ms entre pancadas
GORILA_ONDA_VELOCIDADE    = 2.4 * SCALE
GORILA_ONDA_DANO          = 15
GORILA_ONDA_ALTURA        = int(0.6 * 16 * SCALE)
# Tempo para responder a pergunta do minério: mínimo + tempo de leitura.
QUIZ_BOSS_MIN_S           = 15
QUIZ_BOSS_MAX_S           = 40
QUIZ_BOSS_CHARS_POR_S     = 18     # ~velocidade de leitura de um aluno
# Invencibilidade ao voltar do quiz do boss (não leva banana "de graça").
GRACA_POS_QUIZ_MS         = 1200

# ── Câmera ────────────────────────────────────────────────────────────────────
# Tudo em tiles (multiplicado por TILE_SIZE), para acompanhar o SCALE sem
# precisar recalibrar. Ver a explicação completa em main.atualizar_camera.
#
# CAM_AVANCO_X      quanto a câmera adianta para o lado que o player encara.
#                   3 tiles ≈ 144px: mostra caminho à frente sem desgrudar.
# CAM_ZONA_MORTA_Y  faixa vertical em que o player se move sem mexer a
#                   câmera. 1,5 tile cobre um pulo simples inteiro.
# CAM_ANTECIPACAO_Y multiplicador da velocidade vertical. Quanto maior, mais
#                   cedo a câmera revela para onde o player está indo.
# CAM_AVANCO_*      teto dessa antecipação, para a câmera não disparar numa
#                   queda longa.
# CAM_SUAVIZACAO    fração da distância percorrida por frame (0-1).
#                   0,12 a 60 FPS alcança o alvo em ~0,3s.
CAM_AVANCO_X       = 3.0 * TILE_SIZE
CAM_ZONA_MORTA_Y   = 1.5 * TILE_SIZE
CAM_ANTECIPACAO_Y  = 9.0
CAM_AVANCO_SUBIDA  = 2.5 * TILE_SIZE
CAM_AVANCO_QUEDA   = 3.5 * TILE_SIZE
CAM_SUAVIZACAO     = 0.12

# ── Joystick / Gamepad ────────────────────────────────────────────────────────
# Fonte única da verdade do mapeamento de controle. Os índices seguem o layout
# mais comum (padrão XInput: Xbox / genéricos USB). Se o seu controle usar
# outra numeração, rode o jogo com DEBUG = True: cada botão apertado é
# impresso no terminal, e basta trocar os números aqui.
JOYSTICK_HABILITADO = True

# Zona morta: analógicos gastos reportam valores pequenos mesmo parados
# (0.05 ~ 0.15). Sem isso o personagem desliza sozinho para sempre.
JOY_ZONA_MORTA = 0.25
# A partir de quanto de inclinação conta como "direção pressionada" nos menus.
JOY_LIMIAR_EIXO = 0.5

JOY_EIXO_X = 0   # analógico esquerdo, horizontal
JOY_EIXO_Y = 1   # analógico esquerdo, vertical

JOY_BOTAO_PULO = 0        # A (Xbox) / X (PlayStation)
JOY_BOTAO_CONFIRMAR = 0   # mesmo botão do pulo, em contexto de menu
JOY_BOTAO_VOLTAR = 1      # B / círculo
JOY_BOTAO_PAUSA = 7       # Start
JOY_BOTAO_PAUSA_ALT = 6   # Select/Back (alguns controles invertem 6 e 7)
JOY_BOTAO_INTERAGIR = 2     # X (Xbox) / quadrado — usar passagem do cenário
JOY_BOTAO_ATAQUE = 1        # B (Xbox) / círculo — golpe de asa (na partida)
JOY_BOTAO_ATAQUE_ALT = 3    # Y (Xbox) / triângulo — alternativa
JOY_BOTAO_SCROLL_CIMA = 4   # LB — rolar a tela de pergunta
JOY_BOTAO_SCROLL_BAIXO = 5  # RB

# Repetição ao segurar uma direção em menus (ms): espera antes de repetir e
# intervalo entre repetições. Sem isso, um toque no d-pad pula vários itens.
JOY_REPETICAO_ATRASO = 350
JOY_REPETICAO_INTERVALO = 150

# Passo do scroll por frame ao segurar LB/RB na tela de pergunta.
JOY_SCROLL_PASSO = 8


# ── Dificuldade progressiva ───────────────────────────────────────────────────
# Cada fase só sorteia perguntas das dificuldades permitidas. O conceito de
# "fase" veio do main de perguntas por dificuldade, onde era um contador solto
# (1, 2). Aqui ele foi amarrado às REGIÕES do mapa, que já existem e já trocam
# sozinhas quando o player atravessa uma passagem: floresta -> caverna -> copas
# vira, naturalmente, fácil -> médio -> difícil.
#
# As chaves de FASE_POR_REGIAO são nomes de SETORES.
DIFICULDADES_POR_FASE = {
    1: {"facil", "medio"},
    2: {"medio", "dificil"},
    3: {"dificil"},
}

FASE_POR_REGIAO = {
    "floresta": 1,
    "caverna": 2,
    "copas": 3,
    "arena": 3,
}

# Disciplinas priorizadas em cada fase (veio do filtro por disciplina do
# main_4). As perguntas destas disciplinas saem PRIMEIRO; depois, as demais
# da mesma dificuldade. Escreva do jeito que está no CSV — acento e
# maiúscula não importam ("Biologia" == "biologia").
# Fase sem entrada aqui = sem prioridade por disciplina.
DISCIPLINAS_POR_FASE = {
    1: {"Biologia", "Geografia"},   # floresta
}

# True = a fase usa SÓ as disciplinas acima (se houver alguma pergunta delas).
# Deixe False enquanto o banco tiver poucas perguntas por disciplina.
DISCIPLINA_ESTRITA = False

# Se uma fase não tiver perguntas suficientes no CSV, o jogo NÃO trava: o
# filtro devolve a lista inteira (ver filtrar_perguntas_por_fase em main.py).

# ── Física ────────────────────────────────────────────────────────────────────
GRAVITY = 0.6 * _K

# ── Debug ─────────────────────────────────────────────────────────────────────
DEBUG = False

# ── Cores ─────────────────────────────────────────────────────────────────────
WHITE   = (255, 255, 255)
YELLOW  = (255, 255, 0)
RED     = (255, 0,   0)
GREEN   = (0,   200, 0)