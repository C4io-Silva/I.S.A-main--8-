"""
Passagens como ELEMENTOS DE CENÁRIO.
Antes cada passagem era uma única célula do CSV pintada de uma cor sólida
(`_sprite_passagem` em main.py desenhava um quadrado com borda). Funcionava
como gatilho e não parecia nada: o jogador via um quadrado roxo no chão, não
uma entrada de caverna.

Este módulo separa as três coisas que estavam grudadas:

    CSV        -> ONDE a passagem está        (a célula do marcador)
    ESTILOS    -> COMO ela se parece          (este arquivo)
    main.py    -> O QUE ela faz               (fade, reposicionamento)

Trocar o visual de uma entrada não exige tocar na lógica de transição, e
mover a entrada não exige tocar no visual. É o que a especificação pede em
§25.5 ("o visual deve ser separado da lógica de transição").

SOBRE A ARTE: não existe PNG para essas entradas ainda, então cada estilo é
desenhado proceduralmente — mesma solução que src/ambientes.py já usa para
camadas de fundo sem arquivo. No dia em que a arte existir, basta colocar o
PNG em assets/images/passagens/ e nomear em ESTILOS["sprite"]: o módulo passa
a usar a imagem e ignora o desenho procedural. Nenhuma outra linha muda.

SOBRE O ESPAÇO DISPONÍVEL: a estrutura é desenhada CÉLULA A CÉLULA e pula
qualquer célula que seja bloco sólido na grade. Isso evita o problema óbvio
de pintar uma "abertura" por cima de um bloco que continua tendo colisão — o
jogador veria um buraco e bateria numa parede.
"""


import pygame

from src.nucleo import constants
from src.nucleo.utils import ASSETS_PATH

# ── Estilos ──────────────────────────────────────────────────────────────────
# Uma entrada por TIPO de passagem (os tipos vêm de constants.PASSAGENS_CSV).
# Campos:
#   sprite      nome do PNG em assets/images/passagens/ (None = desenho procedural)
#   largura     em tiles, ímpar de preferência (a coluna do marcador fica no meio)
#   altura      em tiles, contando a célula do marcador
#   direcao     para onde o jogador vai: "baixo", "cima", "frente"
#   interacao   "tecla" (precisa apertar) ou "toque" (basta encostar)
#   rotulo      texto do aviso na tela
#   cores       paleta do desenho procedural
ESTILOS = {
    "CAVE_ENTRY": {
        "sprite": "entrada_caverna.png",
        "largura": 3, "altura": 2,
        "direcao": "baixo",
        "interacao": "tecla",
        "rotulo": "Descer para a caverna",
        "cores": {
            "vao": (10, 8, 14),          # o buraco em si
            "vao_fundo": (26, 20, 34),   # degradê para dar profundidade
            "moldura": (86, 74, 66),     # rocha da borda
            "moldura_luz": (126, 112, 98),
            "detalhe": (58, 92, 52),     # vegetação pendurada na boca
        },
    },
    "CAVE_EXIT": {
        "sprite": "saida_caverna.png",
        "largura": 3, "altura": 2,
        "direcao": "cima",
        "interacao": "tecla",
        "rotulo": "Voltar para a floresta",
        "cores": {
            "vao": (120, 150, 90),       # luz do dia vista de dentro da caverna
            "vao_fundo": (198, 224, 150),
            "moldura": (74, 66, 60),
            "moldura_luz": (110, 100, 92),
            "detalhe": (96, 130, 70),
        },
    },
    "CANOPY_ENTRY": {
        "sprite": "subida_copas.png",
        "largura": 3, "altura": 2,
        "direcao": "cima",
        "interacao": "tecla",
        "rotulo": "Subir pelo cipo",
        "cores": {
            "vao": (44, 62, 34),
            "vao_fundo": (68, 96, 50),
            "moldura": (78, 56, 34),     # tronco
            "moldura_luz": (108, 80, 50),
            "detalhe": (72, 132, 60),    # folhagem
        },
    },
    "CANOPY_EXIT": {
        "sprite": "descida_copas.png",
        "largura": 3, "altura": 2,
        "direcao": "baixo",
        "interacao": "tecla",
        "rotulo": "Descer para a floresta",
        "cores": {
            "vao": (40, 56, 32),
            "vao_fundo": (62, 88, 46),
            "moldura": (78, 56, 34),
            "moldura_luz": (108, 80, 50),
            "detalhe": (72, 132, 60),
        },
    },
    # Entrada e saída da arena do boss: um arco de galhos no topo da
    # árvore-mãe, com luz dourada vindo da clareira do outro lado.
    "ARENA_ENTRY": {
        "sprite": "portal_arena.png",
        "largura": 3, "altura": 2,
        "direcao": "cima",
        "interacao": "tecla",
        "rotulo": "Entrar na clareira da copa",
        "cores": {
            "vao": (150, 120, 40),
            "vao_fundo": (230, 200, 110),
            "moldura": (78, 56, 34),
            "moldura_luz": (120, 90, 56),
            "detalhe": (72, 132, 60),
        },
    },
    "ARENA_EXIT": {
        "sprite": "saida_arena.png",
        "largura": 3, "altura": 2,
        "direcao": "baixo",
        "interacao": "tecla",
        "rotulo": "Voltar para as copas",
        "cores": {
            "vao": (40, 56, 32),
            "vao_fundo": (62, 88, 46),
            "moldura": (78, 56, 34),
            "moldura_luz": (108, 80, 50),
            "detalhe": (72, 132, 60),
        },
    },
}

# Estilo usado quando um tipo não está na tabela: nunca deixa a passagem
# invisível (o jogador ficaria preso sem saber que há saída ali).
ESTILO_PADRAO = ESTILOS["CAVE_ENTRY"]

# Quantos tiles ao redor da célula do marcador ainda contam como "perto o
# suficiente para interagir". 1 = a célula e as vizinhas imediatas.
ALCANCE_TILES = 1


def _desenhar_vao(sup, rect, cores, direcao):
    """A abertura: degradê vertical que some no escuro, para dar profundidade."""
    topo = cores["vao_fundo"] if direcao == "baixo" else cores["vao"]
    base = cores["vao"] if direcao == "baixo" else cores["vao_fundo"]
    passos = max(1, rect.height // 3)
    for i in range(passos):
        t = i / passos
        cor = tuple(int(topo[c] + (base[c] - topo[c]) * t) for c in range(3))
        faixa = pygame.Rect(rect.x, rect.y + int(rect.height * t),
                            rect.width, rect.height // passos + 1)
        pygame.draw.rect(sup, cor, faixa)


def _desenhar_moldura(sup, rect, cores, lado):
    """Pedra/tronco da borda. `lado` é "esq", "dir" ou "topo"."""
    pygame.draw.rect(sup, cores["moldura"], rect)
    # Blocos irregulares: o contorno reto denunciava "isto é um retângulo".
    passo = max(6, rect.height // 4)
    for i, y in enumerate(range(rect.y, rect.bottom, passo)):
        recuo = (i % 2) * max(2, rect.width // 6)
        if lado == "esq":
            bloco = pygame.Rect(rect.right - recuo - 3, y, 3, passo - 2)
        elif lado == "dir":
            bloco = pygame.Rect(rect.x + recuo, y, 3, passo - 2)
        else:
            bloco = pygame.Rect(rect.x + recuo, rect.bottom - 4, passo - 2, 3)
        pygame.draw.rect(sup, cores["moldura_luz"], bloco)


def _desenhar_detalhe(sup, rect, cores, direcao):
    """Vegetação pendurada na boca (ou raízes, conforme a paleta)."""
    n = max(3, rect.width // 8)
    for i in range(n):
        x = rect.x + int(rect.width * (i + 0.5) / n)
        alt = rect.height // 3 + (i % 3) * (rect.height // 6)
        if direcao == "baixo":
            pygame.draw.line(sup, cores["detalhe"], (x, rect.y), (x, rect.y + alt), 2)
        else:
            pygame.draw.line(sup, cores["detalhe"],
                             (x, rect.bottom), (x, rect.bottom - alt), 2)
        pygame.draw.circle(sup, cores["detalhe"],
                           (x, rect.y + alt if direcao == "baixo" else rect.bottom - alt),
                           max(2, rect.width // 20))


class Passagem:
    """
    Uma passagem concreta no mundo: posição (do CSV), destino (de
    constants.PASSAGENS_CSV) e aparência (de ESTILOS).

    A superfície é construída UMA vez, no __init__. O que muda por frame é só
    apenas a aparencia estatica da estrutura; nada e recalculado por frame
    — sem estado acumulado, então não há o que dessincronizar.
    """

    def __init__(self, linha, coluna, destino, grade=None):
        self.linha = linha
        self.coluna = coluna
        self.destino = destino
        self.tipo = destino.get("tipo", "CAVE_ENTRY")
        self.estilo = ESTILOS.get(self.tipo, ESTILO_PADRAO)

        T = constants.TILE_SIZE
        larg_t = self.estilo["largura"]
        alt_t = self.estilo["altura"]

        # A célula do marcador é a base da estrutura e o centro horizontal:
        # a mesma convenção dos outros marcadores, então arrastar o tile no
        # CSV arrasta a estrutura inteira junto.
        self.col0 = coluna - larg_t // 2
        self.linha0 = linha - (alt_t - 1)

        self.rect = pygame.Rect(self.col0 * T, self.linha0 * T, larg_t * T, alt_t * T)

        # Área que ativa a passagem — maior que a célula, senão o jogador tem
        # que parar em cima de um pixel exato para o aviso aparecer.
        self.rect_interacao = pygame.Rect(
            (coluna - ALCANCE_TILES) * T, (linha - ALCANCE_TILES) * T,
            (1 + 2 * ALCANCE_TILES) * T, (1 + 2 * ALCANCE_TILES) * T,
        )

        self.exige_tecla = self.estilo.get("interacao", "tecla") == "tecla"
        self.rotulo = self.estilo.get("rotulo", "Entrar")

        self.superficie = self._construir(grade)

    # ── construção do visual ────────────────────────────────────────────────
    def _construir(self, grade):
        """Monta a arte da estrutura, pulando células que são bloco sólido."""
        T = constants.TILE_SIZE
        sup = pygame.Surface(self.rect.size, pygame.SRCALPHA)

        # Dimensoes definidas ANTES de aplicar a mascara sobre o PNG.
        # O caminho antigo lancava UnboundLocalError e caia no fallback.
        larg_t = self.estilo["largura"]
        alt_t = self.estilo["altura"]
        arquivo = self.estilo.get("sprite")
        if arquivo:
            caminho = ASSETS_PATH / "images" / "passagens" / arquivo
            try:
                img = pygame.image.load(str(caminho)).convert_alpha()
                sup_img = pygame.transform.scale(img, self.rect.size)
                # Sprite tematico nao deve esconder terreno que ainda possui colisao.
                # Mascara celulas solidas quando o relevo vizinho invade o arco.
                for dl in range(alt_t):
                    for dc in range(larg_t):
                        if self._solido(grade, self.linha0 + dl, self.col0 + dc):
                            sup_img.fill((0, 0, 0, 0), pygame.Rect(dc*T, dl*T, T, T))
                return sup_img
            except Exception as e:  # noqa: BLE001 - arte ausente nunca derruba o jogo
                print(f"Passagem {self.tipo}: sprite '{arquivo}' nao carregou ({e}); "
                      f"usando desenho procedural")

        cores = self.estilo["cores"]
        direcao = self.estilo.get("direcao", "baixo")
        larg_t = self.estilo["largura"]
        alt_t = self.estilo["altura"]
        meio = larg_t // 2

        for dl in range(alt_t):
            for dc in range(larg_t):
                linha_g = self.linha0 + dl
                col_g = self.col0 + dc
                if self._solido(grade, linha_g, col_g):
                    continue  # não pinta por cima de bloco com colisão
                cel = pygame.Rect(dc * T, dl * T, T, T)
                if dc == meio:
                    _desenhar_vao(sup, cel, cores, direcao)
                else:
                    _desenhar_moldura(sup, cel, cores, "esq" if dc < meio else "dir")

        # Vegetação só na linha da boca, para a estrutura "encostar" no cenário.
        linha_boca = (alt_t - 1) if direcao == "baixo" else 0
        if not self._solido(grade, self.linha0 + linha_boca, self.coluna):
            _desenhar_detalhe(
                sup, pygame.Rect(0, linha_boca * T, larg_t * T, T), cores, direcao
            )
        return sup

    @staticmethod
    def _solido(grade, linha, col):
        if grade is None:
            return False
        if not (0 <= linha < len(grade) and 0 <= col < len(grade[linha])):
            return True
        return grade[linha][col] in constants.SOLID_TILES

    # ── desenho ─────────────────────────────────────────────────────────────
    def desenhar(self, surface, camera_x, camera_y, segundos=None):
        destino = self.rect.move(-camera_x, -camera_y)
        tela = surface.get_rect()
        if not tela.colliderect(destino):
            return  # culling: o mapa tem 608 colunas, não vale desenhar fora

        surface.blit(self.superficie, destino)

    # ── interação ───────────────────────────────────────────────────────────
    def alcancavel_por(self, rect_player):
        return self.rect_interacao.colliderect(rect_player)


class GerenciadorPassagens:
    """
    Constrói as Passagem a partir do que o CSV declarou e responde a pergunta
    que o main.py faz uma vez por frame: "tem passagem ao alcance do player?"
    """

    def __init__(self, passagens_csv, grade=None):
        self.itens = [
            Passagem(linha, coluna, destino, grade)
            for (linha, coluna), destino in sorted(passagens_csv.items())
        ]

    def __len__(self):
        return len(self.itens)

    def desenhar(self, surface, camera_x, camera_y, segundos=None):
        # `segundos` so servia ao pulso do brilho, removido. Mantido com
        # default para nao quebrar chamadas que ja passam o argumento.
        for p in self.itens:
            p.desenhar(surface, camera_x, camera_y)

    def ao_alcance(self, rect_player):
        """A passagem mais próxima ao alcance, ou None."""
        candidatas = [p for p in self.itens if p.alcancavel_por(rect_player)]
        if not candidatas:
            return None
        cx, cy = rect_player.center
        return min(candidatas,
                   key=lambda p: (p.rect.centerx - cx) ** 2 + (p.rect.centery - cy) ** 2)