import math

import pygame

from src.nucleo import constants
from src.nucleo.utils import carregar_imagem


class Enemy:
    """
    Inimigo base do jogo: a cobra que anda pelo chao.

    Serve tambem de classe-mae para os outros inimigos (Tucano, Aranha), que
    reaproveitam o carregamento/recorte dos sprites, a animacao, o desenho com
    camera e a colisao com o jogador, sobrescrevendo apenas o que muda.

    Cada subclasse DEVE definir sua propria lista ARQUIVOS_FRAMES, senao
    herda os sprites da cobra.

    Pontos de extensao para inimigos novos (o boss, src/enemies/boss.py, usa todos):
      - atributos de combate (VIDA_MAX, DANO, INVENCIVEL, RECOMPENSA_PONTOS);
      - receber_dano() / ao_derrotar(): o main remove quem ficar `derrotado`
        e chama o evento de derrota (ver main._atualizar_inimigos);
      - cooldowns nomeados: em_cooldown() / iniciar_cooldown();
      - SEMPRE_ATIVO e area_desenho(): controlam o culling feito pelo main;
      - o registro de classes fica em src/enemies/__init__.py.
    """

    # ── Sprites ──────────────────────────────────────────────────────
    PASTA_SPRITES   = "inimigos"
    ARQUIVOS_FRAMES = ["cobra_01.png", "cobra_02.png", "cobra_03.png"]
    # Para que lado a ARTE original olha. Os sprites antigos olham para a
    # esquerda; os do Gorila (boss) olham para a direita.
    SPRITE_FACES_LEFT = True

    # Largura final do sprite renderizado, em pixels — escalada junto com o
    # zoom do mundo (constants.SCALE) a partir da referência original (190px
    # com SCALE=5), igual ao que constants.py faz para player/inimigo base.
    LARGURA_ALVO = max(1, int(190 * constants.SCALE / 5))

    VEL_ANIM_PATRULHA    = 220  # ms entre frames enquanto patrulha (devagar)
    VEL_ANIM_PERSEGUICAO = 90   # ms entre frames perseguindo (mais rápido)

    # ── Movimento ──────────────────────────────────────────────────
    VELOCIDADE_PATRULHA    = constants.ENEMY_SPEED * 0.8
    VELOCIDADE_PERSEGUICAO = constants.ENEMY_SPEED * 1.7
    SUAVIZACAO             = 0.05              # 0-1, quanto maior mais rápido acelera/freia
    ALCANCE                = constants.ENEMY_RANGE   # patrulha: pixels para cada lado da origem
    RAIO_DETECCAO          = ALCANCE * 1.73    # distância para começar a perseguir
    RAIO_DESISTENCIA       = ALCANCE * 3.53    # distância para desistir da perseguição
    MARGEM_BORDA           = 6                 # o quanto "olha à frente" pra achar chão

    COR_DEBUG      = (200, 0, 0)
    COR_PROVISORIA = (120, 60, 140)  # usada só quando falta o PNG do inimigo

    # Nome do estado em que o inimigo faz o vaivém da rota. Subclasses que usam
    # outros nomes de estado (o Tucano usa "CRUZEIRO") só redefinem isto para
    # continuar respeitando os limites de patrulha.
    ESTADO_PATRULHA = "PATRULHA"

    # ── Combate ─────────────────────────────────────────────────────
    # Golpe de asa tira constants.DANO_GOLPE; pisão tira DANO_PISAO. Com os
    # valores padrão (vida 2, golpe 1, pisão 2): dois golpes ou um pisão.
    # constants.INIMIGOS_MORREM_COM_PISAO = False volta ao comportamento
    # antigo da v12 (invencíveis; golpe e pisão só empurram/quicam).
    VIDA_MAX          = constants.VIDA_INIMIGO_COMUM
    DANO              = constants.DAMAGE   # dano por contato no jogador
    INVENCIVEL        = not constants.INIMIGOS_MORREM_COM_PISAO
    RECOMPENSA_PONTOS = 0
    IMUNE_A_GOLPE     = False   # o Gorila liga isto: ele se vence pelas perguntas
    RECUA_COM_GOLPE   = True    # a Aranha, presa ao fio, desliga

    # False = o main so atualiza este inimigo quando ele esta perto da camera.
    # Um boss (ou qualquer um que precise agir fora da tela) usa True.
    SEMPRE_ATIVO = False

    # Cache de sprites POR CLASSE: {classe: (frames_esquerda, frames_direita)}.
    # É um dicionário (e não um único valor) para que Tucano/Aranha não
    # encontrem os frames já carregados da cobra e desenhem o sprite errado.
    _cache_frames = {}

    def __init__(self, x, y):
        self.frames_esquerda, self.frames_direita = self._carregar_frames()

        largura, altura = self.frames_esquerda[0].get_size()
        self.rect  = pygame.Rect(x, y, largura, altura)
        self.pos_x = float(x)
        self.pos_y = float(y)

        self.vel_y       = 0.0
        self.vel_x_atual = 0.0
        self.on_ground   = False

        self.direcao  = 1           # 1 = direita, -1 = esquerda
        self.origem_x = float(x)    # centro da rota de patrulha
        self.limite_esquerda = None
        self.limite_direita  = None

        self.estado = "PATRULHA"    # "PATRULHA" ou "PERSEGUICAO"

        self.frame_atual    = 0
        self.tempo_animacao = pygame.time.get_ticks()

        self.vida      = self.VIDA_MAX
        self.derrotado = False
        self._cooldowns = {}   # nome -> instante (ms) em que libera

        # Feedback de dano (ver receber_golpe / desenhar_feedback)
        self.atordoado_golpe_ate = 0    # ms: sem IA e sem dano de contato
        self.empurrao_restante   = 0.0  # px que ainda faltam empurrar (com sinal)
        self.barra_vida_ate      = 0    # ms: barrinha de vida visível
        self.flash_ate           = 0    # ms: piscando branco

    # ── Combate / ciclo de vida ───────────────────────────────────────
    @property
    def proporcao_vida(self):
        """0.0 a 1.0 — pronto para uma barra de vida (ver main.desenhar_barra_vida)."""
        return max(0.0, min(1.0, self.vida / self.VIDA_MAX)) if self.VIDA_MAX else 0.0

    def receber_dano(self, quantidade):
        """Tira vida. Devolve True se este golpe derrotou o inimigo."""
        if self.INVENCIVEL or self.derrotado:
            return False
        self.vida -= quantidade
        if self.vida <= 0:
            self.vida = 0
            self.derrotado = True
            self.ao_derrotar()
            return True
        return False

    def ao_derrotar(self):
        """Evento de derrota. Subclasses sobrescrevem (animacao, drop, fase...)."""

    # ── Golpe / atordoamento (usado pelo combate da Areninha) ───────────
    @property
    def atordoado_por_golpe(self):
        return pygame.time.get_ticks() < self.atordoado_golpe_ate

    def receber_golpe(self, dano, origem_x, empurrar=True):
        """
        Dano vindo da Areninha (golpe de asa ou pisão), com o feedback:
        pisca, mostra a barrinha de vida, fica atordoado e é empurrado para
        longe de `origem_x`. Devolve "imune", "derrotado" ou "atingido".

        Quem garante que um mesmo golpe não acerta duas vezes é o próprio
        golpe (src/combate.py guarda quem já atingiu); aqui não há janela de
        invencibilidade, então um pisão logo depois de um golpe ainda conta.
        """
        if self.IMUNE_A_GOLPE or self.derrotado:
            return "imune"
        agora = pygame.time.get_ticks()
        self.flash_ate = agora + 120
        if self.INVENCIVEL:
            return "imune"
        self.barra_vida_ate = agora + constants.BARRA_VIDA_INIMIGO_MS
        derrotou = self.receber_dano(dano)
        if derrotou:
            return "derrotado"
        self.atordoado_golpe_ate = agora + constants.ATORDOAMENTO_GOLPE_MS
        self.vel_x_atual = 0.0
        if empurrar and self.RECUA_COM_GOLPE:
            lado = 1 if self.rect.centerx >= origem_x else -1
            self.empurrao_restante = lado * constants.EMPURRAO_GOLPE
        return "atingido"

    def atualizar_atordoado(self, obstacles):
        """
        Frame de atordoamento: sem IA (o main chama isto no lugar de update).
        Só desliza o empurrão restante, parando em parede, e mantém a animação.
        """
        if self.empurrao_restante:
            passo = self.empurrao_restante * 0.25
            if abs(passo) < 1:
                passo = self.empurrao_restante
            self.empurrao_restante -= passo
            self.pos_x += passo
            self.rect.x = int(self.pos_x)
            for obs in obstacles:
                if self.rect.colliderect(obs):
                    if passo > 0:
                        self.rect.right = obs.left
                    else:
                        self.rect.left = obs.right
                    self.pos_x = float(self.rect.x)
                    self.empurrao_restante = 0.0
                    break
            if hasattr(self, "origem_x") and self.RECUA_COM_GOLPE:
                # A rota de patrulha acompanha o empurrão: sem isso o inimigo
                # voltaria correndo para o ponto antigo.
                self.origem_x += passo

    def imagem_atual(self):
        """Quadro que o draw() está mostrando agora (usado no piscar)."""
        quadros = self.frames_direita if self.direcao > 0 else self.frames_esquerda
        return quadros[min(self.frame_atual, len(quadros) - 1)]

    def desenhar_feedback(self, surface, camera_x, camera_y):
        """Piscar branco ao levar dano + barrinha de vida acima do inimigo."""
        agora = pygame.time.get_ticks()
        if agora < self.flash_ate:
            silhueta = pygame.mask.from_surface(self.imagem_atual()).to_surface(
                setcolor=(255, 255, 255, 200), unsetcolor=(0, 0, 0, 0))
            surface.blit(silhueta, (self.rect.x - camera_x, self.rect.y - camera_y))
        if agora < self.barra_vida_ate and not self.derrotado and self.VIDA_MAX > 1:
            larg = max(24, min(self.rect.width, 60))
            x = self.rect.centerx - larg // 2 - camera_x
            y = self.rect.top - 10 - camera_y
            pygame.draw.rect(surface, (30, 10, 10), (x - 1, y - 1, larg + 2, 7))
            pygame.draw.rect(surface, (230, 70, 50),
                             (x, y, int(larg * self.proporcao_vida), 5))

    def em_cooldown(self, nome):
        return pygame.time.get_ticks() < self._cooldowns.get(nome, 0)

    def iniciar_cooldown(self, nome, duracao_ms):
        self._cooldowns[nome] = pygame.time.get_ticks() + duracao_ms

    def precisa_atualizar(self, area_ativa):
        """True se o inimigo deve rodar update() neste frame."""
        return self.SEMPRE_ATIVO or area_ativa.colliderect(self.rect)

    def area_desenho(self):
        """Retangulo (no mundo) que o desenho pode ocupar — usado no culling."""
        return self.rect

    # ── Carregamento e recorte dos sprites (com cache) ─────────────────────
    @classmethod
    def _carregar_frames(cls):
        if cls in Enemy._cache_frames:
            return Enemy._cache_frames[cls]

        try:
            brutos = [
                carregar_imagem(cls.PASTA_SPRITES, nome)
                for nome in cls.ARQUIVOS_FRAMES
            ]
        except (FileNotFoundError, pygame.error):
            # Sprite ainda não desenhado: usa uma silhueta provisória em vez de
            # derrubar o jogo, para dar pra testar o comportamento do inimigo.
            return cls._frames_provisorios()

        # Descobre a área real ocupada pelo inimigo em cada sprite
        caixas = []
        for surf in brutos:
            # Cria uma máscara usando as áreas visíveis do sprite
            mask = pygame.mask.from_surface(surf)

            # get_bounding_rects() retorna uma lista de retângulos.
            # Unimos todos eles para obter uma única caixa envolvendo
            # toda a parte visível do inimigo.
            rects = mask.get_bounding_rects()

            if rects:
                caixa = rects[0].unionall(rects[1:])
            else:
                caixa = surf.get_rect()

            caixas.append(caixa)

        # Área comum para todos os frames
        largura_uniao = max(c.width for c in caixas)
        altura_uniao  = max(c.height for c in caixas)

        recortados = []

        for surf, caixa in zip(brutos, caixas):

            # Recorta somente a parte que realmente contém o inimigo
            recorte = pygame.Surface(
                caixa.size,
                pygame.SRCALPHA
            )

            recorte.blit(
                surf,
                (0, 0),
                caixa
            )

            # Cria uma área de tamanho igual para todos os frames
            canvas = pygame.Surface(
                (largura_uniao, altura_uniao),
                pygame.SRCALPHA
            )

            # Centraliza horizontalmente
            destino_x = (
                largura_uniao - caixa.width
            ) // 2

            # Mantém a BASE do inimigo sempre no mesmo lugar
            destino_y = (
                altura_uniao - caixa.height
            )

            canvas.blit(
                recorte,
                (destino_x, destino_y)
            )

            recortados.append(canvas)

        # Redimensionamento final
        razao = cls.LARGURA_ALVO / largura_uniao

        altura_alvo = max(
            1,
            int(altura_uniao * razao)
        )

        frames_esquerda = [
            pygame.transform.smoothscale(
                frame,
                (
                    cls.LARGURA_ALVO,
                    altura_alvo
                )
            )
            for frame in recortados
        ]

        # Cria os frames olhando para a direita
        frames_direita = [
            pygame.transform.flip(
                frame,
                True,
                False
            )
            for frame in frames_esquerda
        ]

        if not cls.SPRITE_FACES_LEFT:
            frames_esquerda, frames_direita = frames_direita, frames_esquerda

        Enemy._cache_frames[cls] = (
            frames_esquerda,
            frames_direita
        )

        return Enemy._cache_frames[cls]

    @classmethod
    def _frames_provisorios(cls):
        """Frames de emergência (elipse colorida) para quando falta o PNG."""
        if cls in Enemy._cache_frames:
            return Enemy._cache_frames[cls]

        largura = cls.LARGURA_ALVO
        altura  = max(1, int(largura * 0.7))

        frames_esquerda = []

        for passo in (-0.15, 0.0, 0.15):
            frame = pygame.Surface((largura, altura), pygame.SRCALPHA)

            pygame.draw.ellipse(
                frame,
                cls.COR_PROVISORIA,
                (
                    largura * 0.15,
                    altura * (0.30 + passo * 0.3),
                    largura * 0.70,
                    altura * 0.55
                )
            )

            frames_esquerda.append(frame)

        frames_direita = [
            pygame.transform.flip(frame, True, False)
            for frame in frames_esquerda
        ]

        Enemy._cache_frames[cls] = (frames_esquerda, frames_direita)

        return Enemy._cache_frames[cls]

    # ── IA / Física ────────────────────────────────────────────────
    def _tem_chao_a_frente(self, obstacles):
        """Verifica se existe chão logo à frente da cobra."""

        if self.direcao > 0:
            ponto_x = self.rect.right + self.MARGEM_BORDA
        else:
            ponto_x = self.rect.left - self.MARGEM_BORDA

        # O sensor fica um pouco abaixo dos pés.
        sensor = pygame.Rect(
            ponto_x,
            self.rect.bottom + 1,
            2,
            8
        )

        return any(
            sensor.colliderect(obs)
            for obs in obstacles
        )

    def _atualizar_estado(self, player):
        """Decide entre patrulhar ou perseguir o jogador."""
        if player is None:
            self.estado = "PATRULHA"
            return

        distancia = abs(player.rect.centerx - self.rect.centerx)
        if self.estado == "PATRULHA" and distancia <= self.RAIO_DETECCAO:
            self.estado = "PERSEGUICAO"
        elif self.estado == "PERSEGUICAO" and distancia >= self.RAIO_DESISTENCIA:
            self.estado = "PATRULHA"

        if self.estado == "PERSEGUICAO":
            self.direcao = 1 if player.rect.centerx >= self.rect.centerx else -1

    def _inverter_no_limite_de_patrulha(self):
        """
        Inverte a direção ao chegar na ponta da rota (não vale perseguindo).

        Só inverte se o inimigo ainda estiver indo PARA FORA do limite. Sem essa
        checagem de direção, como a verificação acontece depois do movimento (ou
        seja, já passou alguns pixels do limite), a condição continuaria
        verdadeira em todos os frames seguintes e ele ficaria invertendo sem
        parar, travado tremendo na borda.
        """
        if self.estado != self.ESTADO_PATRULHA:
            return

        deslocamento = self.pos_x - self.origem_x

        if deslocamento >= self.ALCANCE and self.direcao > 0:
            self.direcao     = -1
            self.vel_x_atual = 0.0
        elif deslocamento <= -self.ALCANCE and self.direcao < 0:
            self.direcao     = 1
            self.vel_x_atual = 0.0

    def update(self, obstacles, player=None):
        self._atualizar_estado(player)

        # Gravidade
        self.vel_y += constants.GRAVITY
        if self.vel_y > constants.VEL_TERMINAL:
            self.vel_y = constants.VEL_TERMINAL

        # Foge de precipícios apenas enquanto patrulha no chão
        if self.on_ground and self.estado == "PATRULHA":
            if not self._tem_chao_a_frente(obstacles):
                self.direcao     *= -1
                self.vel_x_atual  = 0.0   # reverte na hora, sem "deslizar" pra fora

        self.on_ground = False

        # Aceleração suave em direção à velocidade alvo (patrulha ou perseguição)
        velocidade_alvo = (
            self.VELOCIDADE_PERSEGUICAO
            if self.estado == "PERSEGUICAO"
            else self.VELOCIDADE_PATRULHA
        )
        alvo_x = velocidade_alvo * self.direcao
        self.vel_x_atual += (alvo_x - self.vel_x_atual) * self.SUAVIZACAO

        # Colisão horizontal
        self.pos_x += self.vel_x_atual
        self.rect.x = int(self.pos_x)
        for obs in obstacles:
            if self.rect.colliderect(obs):
                if self.vel_x_atual > 0:
                    self.rect.right = obs.left
                elif self.vel_x_atual < 0:
                    self.rect.left  = obs.right
                self.pos_x       = float(self.rect.x)
                self.vel_x_atual = 0.0
                self.direcao    *= -1   # inverte ao bater em parede

        self._inverter_no_limite_de_patrulha()

        # Colisão vertical
        self.pos_y += self.vel_y
        self.rect.y = int(self.pos_y)
        for obs in obstacles:
            if self.rect.colliderect(obs):
                if self.vel_y > 0:
                    self.rect.bottom = obs.top
                    self.on_ground   = True
                elif self.vel_y < 0:
                    self.rect.top    = obs.bottom
                self.vel_y = 0
                self.pos_y = float(self.rect.y)

        self._atualizar_animacao()

    def foi_pisado_por(self, player):
        """
        True se o jogador caiu em cima deste inimigo neste frame.

        Usa a posição dos pés ANTES do movimento do frame (Character.move
        guarda em `pes_antes`): numa queda rápida o jogador já atravessou o
        inimigo quando a colisão é testada, e olhar só a posição atual
        transformava o pisão em contato lateral.
        """
        pes_antes = getattr(player, "pes_antes", player.rect.bottom)
        caindo = getattr(player, "caindo", player.vel_y > 0) or player.vel_y > 0
        return caindo and pes_antes <= self.rect.top + constants.PISAO_TOLERANCIA

    def pisar(self, player):
        """Quique do jogador + dano de pisão no inimigo."""
        player.vel_y = -constants.QUIQUE_Y
        player.pos_y = float(self.rect.top - player.rect.height)
        player.rect.bottom = self.rect.top
        player.on_ground = False
        player.jumps_left = player.MAX_JUMPS   # pode emendar outro pulo
        self.receber_golpe(constants.DANO_PISAO, player.rect.centerx, empurrar=False)

    def check_player_collision(self, player):
        """Pisão fere o inimigo; contato lateral machuca o jogador.

        Atordoado por um golpe, o inimigo não machuca ninguém: é a janela de
        respiro depois de acertá-lo (e o que impede trocar golpe por dano
        no mesmo instante)."""
        if self.derrotado or not self.rect.colliderect(player.rect):
            return False

        if self.foi_pisado_por(player):
            self.pisar(player)
            return False

        if self.atordoado_por_golpe:
            return False

        # Colisão lateral: aplica dano se não estiver invulnerável
        if not player.invulnerable:
            player.stunned      = True
            player.wrong_answer = True
            player.apply_damage(self.DANO)

        # Knockback lateral
        if player.rect.centerx < self.rect.centerx:
            player.pos_x -= constants.KNOCKBACK_X
        else:
            player.pos_x += constants.KNOCKBACK_X

        return True

    # ── Animação ───────────────────────────────────────────────────
    def _velocidade_animacao(self):
        """
        ms entre frames. Ponto de extensão: subclasses com outros estados
        (a Aranha, por exemplo) sobrescrevem só este método.
        """
        return (
            self.VEL_ANIM_PERSEGUICAO
            if self.estado == "PERSEGUICAO"
            else self.VEL_ANIM_PATRULHA
        )

    def _atualizar_animacao(self):
        agora = pygame.time.get_ticks()

        if agora - self.tempo_animacao >= self._velocidade_animacao():
            self.tempo_animacao = agora
            quadros = self.frames_direita if self.direcao > 0 else self.frames_esquerda
            self.frame_atual = (self.frame_atual + 1) % len(quadros)

    # ── Renderização ───────────────────────────────────────────────
    def draw(self, surface, camera_x, camera_y):
        quadros = self.frames_direita if self.direcao > 0 else self.frames_esquerda
        imagem  = quadros[min(self.frame_atual, len(quadros) - 1)]

        surface.blit(imagem, (self.rect.x - camera_x, self.rect.y - camera_y))

        if getattr(constants, "DEBUG", False):
            pygame.draw.rect(
                surface, self.COR_DEBUG, self.rect.move(-camera_x, -camera_y), 2
            )


class Tucano(Enemy):
    """
    Inimigo voador que ataca em RASANTE, nao em perseguicao.

    Ciclo de estados:

        CRUZEIRO  → voa em vaivem pela rota de patrulha, ondulando (senoide)
                    em torno da altura de spawn.
        MERGULHO  → ao ver o jogador, MIRA UMA VEZ e desce em linha reta para
                    aquele ponto. Nao corrige a mira no meio do caminho: e isso
                    que faz o ataque parecer um rasante e nao uma perseguicao,
                    e e o que da ao jogador a chance de sair da linha de voo.
        RETORNO   → sobe de volta para a altitude de cruzeiro seguindo em
                    frente, sem virar.
        (cooldown)→ espera COOLDOWN_RASANTE ms voando normal. Se o jogador
                    continuar dentro do raio, ele repete o rasante; se tiver
                    saido, volta ao voo normal indefinidamente.
    """

    PASTA_SPRITES   = "inimigos"
    ARQUIVOS_FRAMES = [
        "tucano_01.png",
        "tucano_02.png",
        "tucano_03.png",
        "tucano_04.png"
    ]

    LARGURA_ALVO = max(1, int(85 * constants.SCALE / 5))

    # O vaivem do tucano acontece no estado "CRUZEIRO", nao em "PATRULHA".
    ESTADO_PATRULHA = "CRUZEIRO"

    VEL_ANIM_CRUZEIRO = 120  # asinhas em voo normal
    VEL_ANIM_RASANTE  = 55   # asas a mil durante o ataque

    # ── Voo normal ────────────────────────────────────────────────
    VELOCIDADE_CRUZEIRO = constants.ENEMY_SPEED * 1.1
    SUAVIZACAO          = 0.08
    ALCANCE             = constants.ENEMY_RANGE * 1.5   # rota de vaivem
    AMPLITUDE_VOO       = 1.2 * constants.TILE_SIZE     # sobe/desce da senoide
    PERIODO_VOO         = 1800                          # ms de um ciclo
    SUAVIZA_CRUZEIRO    = 0.12

    # ── Rasante ────────────────────────────────────────────────────
    RAIO_DETECCAO    = ALCANCE * 1.6   # distancia para iniciar o rasante
    RAIO_DESISTENCIA = ALCANCE * 2.6   # fora disso ele nem tenta
    VELOCIDADE_RASANTE = constants.ENEMY_SPEED * 5.0
    VELOCIDADE_SUBIDA  = constants.ENEMY_SPEED * 2.5
    COOLDOWN_RASANTE   = 1400          # ms entre um rasante e o proximo
    DURACAO_MAX_RASANTE = 2500         # ms: trava de seguranca do mergulho
    MARGEM_ALVO        = constants.TILE_SIZE * 0.5  # "chegou" no ponto mirado

    COR_DEBUG      = (0, 90, 200)
    COR_PROVISORIA = (40, 40, 60)

    def __init__(self, x, y):
        super().__init__(x, y)

        self.origem_y  = float(y)   # altitude de cruzeiro
        self.on_ground = False      # nasce no ar e nunca pousa

        # Defasagem da senoide: tucanos criados em instantes diferentes nao
        # sobem e descem em sincronia.
        self.fase_voo = pygame.time.get_ticks()

        self.estado = "CRUZEIRO"    # CRUZEIRO | MERGULHO | RETORNO

        # Ponto mirado no inicio do rasante e vetor unitario ate ele.
        self.alvo_rasante   = None
        self.dir_rasante    = (0.0, 0.0)
        self.inicio_rasante = 0
        self.proximo_rasante = 0

    # ── Decisao ───────────────────────────────────────────────────
    def _distancia_ate(self, player):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        return math.hypot(dx, dy)

    def _iniciar_rasante(self, player):
        """Mira UMA vez a posicao atual do jogador e trava a rota do ataque."""
        alvo_x = player.rect.centerx - self.rect.width / 2
        alvo_y = player.rect.centery - self.rect.height / 2

        dx = alvo_x - self.pos_x
        dy = alvo_y - self.pos_y
        distancia = math.hypot(dx, dy) or 1.0

        self.alvo_rasante   = (alvo_x, alvo_y)
        self.dir_rasante    = (dx / distancia, dy / distancia)
        self.inicio_rasante = pygame.time.get_ticks()

        # Vira o sprite para o lado do ataque e ja entra na velocidade cheia.
        self.direcao     = 1 if dx >= 0 else -1
        self.vel_x_atual = self.dir_rasante[0] * self.VELOCIDADE_RASANTE

        self.estado = "MERGULHO"

    def _terminar_rasante(self):
        self.alvo_rasante    = None
        self.proximo_rasante = pygame.time.get_ticks() + self.COOLDOWN_RASANTE
        self.estado          = "RETORNO"

    # ── Ciclo ──────────────────────────────────────────────────────
    def update(self, obstacles, player=None):
        agora = pygame.time.get_ticks()

        # Sem gravidade e sem pouso: ele se sustenta no ar.
        self.on_ground = False

        if self.estado == "CRUZEIRO":
            if (
                player is not None
                and agora >= self.proximo_rasante
                and self._distancia_ate(player) <= self.RAIO_DETECCAO
            ):
                self._iniciar_rasante(player)
            else:
                self._voar_normal(obstacles)

        if self.estado == "MERGULHO":
            self._mergulhar(obstacles)
        elif self.estado == "RETORNO":
            self._subir(obstacles)

        self._atualizar_animacao()

    # ── Voo normal (vaivem + senoide) ─────────────────────────────────
    def _voar_normal(self, obstacles):
        alvo_x = self.VELOCIDADE_CRUZEIRO * self.direcao
        self.vel_x_atual += (alvo_x - self.vel_x_atual) * self.SUAVIZACAO

        self._aplicar_horizontal(obstacles, inverter_ao_bater=True)
        self._inverter_no_limite_de_patrulha()

        decorrido = pygame.time.get_ticks() - self.fase_voo
        angulo    = decorrido / self.PERIODO_VOO * 2 * math.pi
        destino_y = self.origem_y + math.sin(angulo) * self.AMPLITUDE_VOO
        self.vel_y = (destino_y - self.pos_y) * self.SUAVIZA_CRUZEIRO

        self._aplicar_vertical(obstacles, reajustar_altitude=True)

    # ── Rasante ────────────────────────────────────────────────────
    def _mergulhar(self, obstacles):
        ux, uy = self.dir_rasante

        self.vel_x_atual = ux * self.VELOCIDADE_RASANTE
        self.vel_y       = uy * self.VELOCIDADE_RASANTE

        bateu_lado = self._aplicar_horizontal(obstacles, inverter_ao_bater=False)
        bateu_cima = self._aplicar_vertical(obstacles, reajustar_altitude=False)

        if bateu_lado or bateu_cima:
            self._terminar_rasante()
            return

        # Passou do ponto mirado? Projeta o quanto falta sobre a direcao do voo:
        # se o resultado ficou negativo, ele ja atravessou o alvo.
        alvo_x, alvo_y = self.alvo_rasante
        restante = (alvo_x - self.pos_x) * ux + (alvo_y - self.pos_y) * uy

        tempo_estourado = (
            pygame.time.get_ticks() - self.inicio_rasante
            >= self.DURACAO_MAX_RASANTE
        )

        if restante <= self.MARGEM_ALVO or tempo_estourado:
            self._terminar_rasante()

    # ── Volta para a altitude de cruzeiro ─────────────────────────────
    def _subir(self, obstacles):
        # Segue em frente enquanto ganha altura (nao vira no meio da subida).
        alvo_x = self.VELOCIDADE_CRUZEIRO * self.direcao
        self.vel_x_atual += (alvo_x - self.vel_x_atual) * self.SUAVIZACAO
        self._aplicar_horizontal(obstacles, inverter_ao_bater=True)

        if self.pos_y > self.origem_y:
            self.vel_y = -self.VELOCIDADE_SUBIDA
        else:
            self.vel_y = self.VELOCIDADE_SUBIDA

        self._aplicar_vertical(obstacles, reajustar_altitude=False)

        # Chegou perto da altitude de cruzeiro: volta ao voo normal e recomeca a
        # senoide dali, para nao dar um "pulo" de altura.
        if abs(self.pos_y - self.origem_y) <= self.VELOCIDADE_SUBIDA:
            self.pos_y  = self.origem_y
            self.rect.y = int(self.pos_y)
            self.vel_y  = 0.0

            self.fase_voo = pygame.time.get_ticks()
            self.estado   = "CRUZEIRO"

    # ── Movimento + colisao (compartilhado pelos tres estados) ──────────────
    def _aplicar_horizontal(self, obstacles, inverter_ao_bater):
        self.pos_x += self.vel_x_atual
        self.rect.x = int(self.pos_x)

        bateu = False

        for obs in obstacles:
            if self.rect.colliderect(obs):
                if self.vel_x_atual > 0:
                    self.rect.right = obs.left
                elif self.vel_x_atual < 0:
                    self.rect.left  = obs.right
                self.pos_x       = float(self.rect.x)
                self.vel_x_atual = 0.0
                bateu = True

                if inverter_ao_bater:
                    self.direcao *= -1

        return bateu

    def _aplicar_vertical(self, obstacles, reajustar_altitude):
        self.pos_y += self.vel_y
        self.rect.y = int(self.pos_y)

        bateu = False

        for obs in obstacles:
            if self.rect.colliderect(obs):
                if self.vel_y > 0:
                    self.rect.bottom = obs.top
                elif self.vel_y < 0:
                    self.rect.top    = obs.bottom
                self.pos_y = float(self.rect.y)
                self.vel_y = 0.0
                bateu = True

                if reajustar_altitude:
                    # Em voo normal, adota a altura livre como nova altitude de
                    # cruzeiro para nao ficar raspando no bloco a cada ciclo.
                    self.origem_y = self.pos_y

        return bateu

    # ── Animacao ───────────────────────────────────────────────────
    def _velocidade_animacao(self):
        return (
            self.VEL_ANIM_CRUZEIRO
            if self.estado == "CRUZEIRO"
            else self.VEL_ANIM_RASANTE
        )



class Aranha(Enemy):
    """
    Aranha que fica pendurada num fio, balancando, e desce em cima do jogador
    quando ele passa por baixo. Prende o jogador por alguns instantes e volta
    para o topo do fio.

    Ela nao patrulha nem persegue: usa estados proprios
    (ESPERA | DESCENDO | PRENDENDO | SUBINDO) e nunca sai da coluna onde nasceu.
    """

    PASTA_SPRITES   = "inimigos"
    ARQUIVOS_FRAMES = [
        "aranha_01.png",
        "aranha_02.png",
        "aranha_03.png",
        "aranha_04.png"
    ]

    LARGURA_ALVO = max(1, int(85 * constants.SCALE / 5))

    VEL_ANIM_ESPERA = 300      # balancando no fio
    VEL_ANIM_ATAQUE = 80       # descida/subida

    # ── Gatilho ────────────────────────────────────────────────────
    TOLERANCIA_X     = LARGURA_ALVO * 0.7             # largura da "armadilha"
    ALCANCE_VERTICAL = constants.ENEMY_RANGE * 2.0    # até onde ela desce/enxerga

    # ── Movimento vertical ─────────────────────────────────────────
    VELOCIDADE_DESCIDA = constants.ENEMY_SPEED * 5.5
    VELOCIDADE_SUBIDA  = constants.ENEMY_SPEED * 1.5

    # ── Balanço parado ───────────────────────────────────────────
    AMPLITUDE_BALANCO  = max(2, int(6 * constants.SCALE / 5))
    FREQUENCIA_BALANCO = 0.06   # radianos por frame (~1,7 s por ciclo a 60 FPS)

    # ── Tempos (ms) ──────────────────────────────────────────────
    DURACAO_PRISAO = 1500      # quanto tempo o player fica preso
    COOLDOWN       = 1200      # espera antes de poder atacar de novo

    DANO_AO_PRENDER = True     # se False, só imobiliza sem tirar vida

    COR_DEBUG      = (200, 160, 0)
    COR_PROVISORIA = (60, 30, 60)
    COR_FIO        = (230, 230, 230)

    def __init__(self, x, y):
        super().__init__(x, y)

        # Centro da coluna onde ela vive (x recebido é o canto esquerdo).
        self.ancora_x = float(x) + self.rect.width / 2

        self.altura_inicial = float(y)    # topo do fio
        self.pos_y          = float(y)
        self.tempo_balanco  = 0.0

        self.estado = "ESPERA"            # ESPERA | DESCENDO | PRENDENDO | SUBINDO
        self.player_preso = None

        self.tempo_estado    = pygame.time.get_ticks()
        self.proximo_ataque  = 0

    # ── Gatilho ────────────────────────────────────────────────────
    def _player_na_armadilha(self, player):
        if player is None:
            return False

        dx = abs(player.rect.centerx - self.ancora_x)
        dy = player.rect.top - self.rect.bottom

        return dx <= self.TOLERANCIA_X and 0 <= dy <= self.ALCANCE_VERTICAL

    def _trocar_estado(self, novo):
        self.estado = novo
        self.tempo_estado = pygame.time.get_ticks()

    # ── Ciclo ──────────────────────────────────────────────────────
    def update(self, obstacles, player=None):
        agora = pygame.time.get_ticks()

        self.rect.x = int(self.ancora_x - self.rect.width / 2)
        self.pos_x  = float(self.rect.x)

        if self.estado == "ESPERA":
            self.tempo_balanco += self.FREQUENCIA_BALANCO
            self.pos_y = (
                self.altura_inicial
                + self.AMPLITUDE_BALANCO * math.sin(self.tempo_balanco)
            )

            if agora >= self.proximo_ataque and self._player_na_armadilha(player):
                self._trocar_estado("DESCENDO")

        elif self.estado == "DESCENDO":
            self.pos_y += self.VELOCIDADE_DESCIDA
            self.rect.y = int(self.pos_y)

            # Acertou o player → prende
            if player is not None and self.rect.colliderect(player.rect):
                self.player_preso = player
                self._prender(player)
                self._trocar_estado("PRENDENDO")

            # Bateu no chão / desceu demais → volta
            elif (
                self._colidiu_vertical(obstacles)
                or self.pos_y - self.altura_inicial >= self.ALCANCE_VERTICAL
            ):
                self._trocar_estado("SUBINDO")

        elif self.estado == "PRENDENDO":
            # Acompanha o player preso para o sprite ficar em cima dele
            if self.player_preso is not None:
                self.rect.bottom = (
                    self.player_preso.rect.top + self.rect.height // 2
                )
                self.pos_y = float(self.rect.y)

            if agora - self.tempo_estado >= self.DURACAO_PRISAO:
                self._soltar()
                self._trocar_estado("SUBINDO")

        elif self.estado == "SUBINDO":
            self.pos_y -= self.VELOCIDADE_SUBIDA

            if self.pos_y <= self.altura_inicial:
                self.pos_y          = self.altura_inicial
                self.tempo_balanco  = 0.0
                self.proximo_ataque = agora + self.COOLDOWN
                self._trocar_estado("ESPERA")

        self.rect.y = int(self.pos_y)

        self._atualizar_animacao()

    def _colidiu_vertical(self, obstacles):
        for obs in obstacles:
            if self.rect.colliderect(obs):
                self.rect.bottom = obs.top
                self.pos_y = float(self.rect.y)
                return True
        return False

    # ── Prender / soltar ───────────────────────────────────────────
    def _prender(self, player):
        player.preso     = True
        player.preso_ate = pygame.time.get_ticks() + self.DURACAO_PRISAO

        # Dano único no momento da captura (respeita a invulnerabilidade).
        if self.DANO_AO_PRENDER and not player.invulnerable:
            player.stunned      = True
            player.wrong_answer = True
            player.apply_damage(self.DANO)

    RECUA_COM_GOLPE = False   # presa ao fio: não é empurrada

    def receber_golpe(self, dano, origem_x, empurrar=True):
        """Golpeada, a aranha solta o jogador (se o prendia) e recua pelo fio."""
        resultado = super().receber_golpe(dano, origem_x, empurrar)
        if resultado == "atingido":
            self._soltar()
            if self.estado in ("DESCENDO", "PRENDENDO"):
                self._trocar_estado("SUBINDO")
        return resultado

    def _soltar(self):
        if self.player_preso is not None:
            self.player_preso.preso = False
        self.player_preso = None

    # ── Culling ────────────────────────────────────────────────────
    def precisa_atualizar(self, area_ativa):
        # Segurando o jogador ela precisa rodar ate solta-lo, mesmo que a
        # camera tenha se afastado.
        return self.player_preso is not None or super().precisa_atualizar(area_ativa)

    def area_desenho(self):
        # Inclui o fio: ele aparece na tela mesmo quando a aranha ainda nao.
        topo = int(self.altura_inicial)
        return self.rect.union(pygame.Rect(int(self.ancora_x) - 1, topo, 2,
                                           max(1, self.rect.bottom - topo)))

    # ── Colisão ────────────────────────────────────────────────────
    def check_player_collision(self, player):
        """
        A aranha não usa o dano lateral com knockback da cobra: o "ataque" dela
        é descer e prender, tratado em update(). Sem sobrescrever este método, o
        main aplicaria dano e empurrão todo frame enquanto ela estivesse em cima
        do jogador.

        Pisão: cair em cima dela (descendo, subindo ou parada no fio) derrota a
        aranha e solta o jogador se ela o estivesse prendendo.
        """
        if (not self.derrotado and self.rect.colliderect(player.rect)
                and self.foi_pisado_por(player)):
            self._soltar()
            self.pisar(player)
            return False
        return self.estado == "PRENDENDO"

    # ── Animação ───────────────────────────────────────────────────
    def _velocidade_animacao(self):
        return (
            self.VEL_ANIM_ESPERA
            if self.estado == "ESPERA"
            else self.VEL_ANIM_ATAQUE
        )

    # ── Renderização ───────────────────────────────────────────────
    def draw(self, surface, camera_x=0, camera_y=0):
        # Fio de seda: do topo original até a aranha
        pygame.draw.line(
            surface,
            self.COR_FIO,
            (int(self.ancora_x - camera_x), int(self.altura_inicial - camera_y)),
            (int(self.rect.centerx - camera_x), int(self.rect.centery - camera_y)),
            2
        )

        super().draw(surface, camera_x, camera_y)