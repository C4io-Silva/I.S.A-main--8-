from functools import lru_cache

import pygame

from src.nucleo import constants
from src.nucleo.utils import ASSETS_PATH

PASTA_PERSONAGENS = ASSETS_PATH / "images" / "personagens"
# Sprites antigos (v12): só parado + andando. Ficam como fallback.
SPRITE_PARADO = "Areninha2 1.png"
SPRITE_ANDANDO = "Areninha4 2.png"

# Sprites animados (vieram do fork do boss): 4 quadros andando + 4 de pulo.
# A arte foi desenhada OLHANDO PARA A ESQUERDA; o carregador vira os quadros
# para a direita uma vez só, e o resto da classe continua usando a convenção
# antiga (flip=True = olhando para a esquerda).
PASTA_ANIMADA = PASTA_PERSONAGENS / "areninha"
ARQUIVOS_ANDANDO = [f"areninha_normal_andando_{i}.png" for i in range(1, 5)]
ARQUIVOS_PULO = [f"areninha_pulo{i}.png" for i in range(1, 5)]
ARTE_OLHA_PARA_ESQUERDA = True


@lru_cache(maxsize=8)
def _load_sprite(path: str, target_h: int) -> pygame.Surface:
    """
    Carrega um sprite PNG, recorta a borda vazia/preta e redimensiona
    mantendo a proporção.

    Cacheado: o recorte lê pixel a pixel (~45 ms por sprite) e antes rodava
    de novo a cada partida iniciada.
    """
    sprite = pygame.image.load(path).convert_alpha()
    w, h = sprite.get_size()

    min_x, min_y = w, h
    max_x, max_y = 0, 0
    found = False

    for y in range(h):
        for x in range(w):
            r, g, b, a = sprite.get_at((x, y))
            if a > 0 and not (r < 30 and g < 30 and b < 30):
                found = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if not found:
        return pygame.Surface((target_h, target_h), pygame.SRCALPHA)

    crop_rect = pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    cropped = pygame.Surface(crop_rect.size, pygame.SRCALPHA)
    cropped.blit(sprite, (0, 0), crop_rect)

    ratio = target_h / crop_rect.height
    target_w = max(1, int(crop_rect.width * ratio))
    return pygame.transform.scale(cropped, (target_w, target_h))


@lru_cache(maxsize=4)
def _carregar_animacao(target_h: int):
    """
    Carrega os quadros animados, recortados pela MESMA caixa (união das
    áreas visíveis de todos os quadros) e escalados para a mesma altura.

    Mesma caixa para todos = mesmo tamanho de rect em todos os quadros: o
    personagem não "treme" nem muda de hitbox ao trocar de quadro. O recorte
    usa a máscara de alpha (rápido) e não descarta pixels pretos — o
    contorno preto da arte nova faz parte do desenho.

    Devolve (andando, pulo) já virados para a direita, ou None se faltar
    algum arquivo.
    """
    caminhos = [PASTA_ANIMADA / n for n in ARQUIVOS_ANDANDO + ARQUIVOS_PULO]
    if not all(c.exists() for c in caminhos):
        return None
    brutos = [pygame.image.load(str(c)).convert_alpha() for c in caminhos]
    caixa = None
    for surf in brutos:
        rects = pygame.mask.from_surface(surf).get_bounding_rects()
        if not rects:
            continue
        r = rects[0].unionall(rects[1:])
        caixa = r if caixa is None else caixa.union(r)
    if caixa is None:
        return None
    escala = target_h / caixa.height
    tam = (max(1, int(caixa.width * escala)), target_h)
    quadros = []
    for surf in brutos:
        recorte = surf.subsurface(caixa).copy()
        quadro = pygame.transform.smoothscale(recorte, tam)
        if ARTE_OLHA_PARA_ESQUERDA:
            quadro = pygame.transform.flip(quadro, True, False)
        quadros.append(quadro)
    return quadros[:4], quadros[4:]


class Character:
    # Dois sprites: [0] parado, [1] andando
    ANIM_SPEED = 200     # ms por frame nos sprites antigos (idle <-> walk)
    ANIM_WALK_MS = 110   # ms por frame no ciclo de 4 quadros da arte nova
    # ─── Pulo duplo: quantidade máxima de pulos antes de tocar o chão ───
    # Valor vem de constants.MAX_JUMPS (fonte única da verdade); o 2 aqui é
    # só a garantia de que o jogo roda mesmo com um constants.py antigo.
    MAX_JUMPS  = getattr(constants, "MAX_JUMPS", 2)

    def __init__(self, x, y, size, speed, image, health):
        animacao = _carregar_animacao(size)
        parado = PASTA_PERSONAGENS / SPRITE_PARADO
        andando = PASTA_PERSONAGENS / SPRITE_ANDANDO
        # walk_frames / jump_frames: animação completa (arte nova). Sem ela,
        # cai nos dois sprites antigos e, por fim, na imagem passada.
        self.walk_frames = []
        self.jump_frames = []
        if animacao:
            self.walk_frames, self.jump_frames = animacao
            self.frames = list(self.walk_frames)
            self.animated = True
        elif parado.exists() and andando.exists():
            self.frames = [_load_sprite(str(parado), size),
                           _load_sprite(str(andando), size)]
            self.animated = True
        elif image is not None:
            self.frames = [pygame.transform.scale(image, (size, size))]
            self.animated = False
        else:
            self.frames = [pygame.Surface((size * 2 // 3, size), pygame.SRCALPHA)]
            self.frames[0].fill((240, 240, 220))
            self.animated = False
        self.jump_frames_espelhados = [
            pygame.transform.flip(f, True, False) for f in self.jump_frames
        ]
        # Versões espelhadas calculadas UMA vez. Antes o flip rodava a cada
        # frame, criando uma Surface nova 60 vezes por segundo.
        self.frames_espelhados = [
            pygame.transform.flip(f, True, False) for f in self.frames
        ]

        self.frame_index    = 0
        self.last_anim_time = 0

        self.image_normal  = self.frames[0]
        self.image_flipped = self.frames_espelhados[0]

        self.rect  = self.image_normal.get_rect(topleft=(x, y))
        self.pos_x = float(x)
        self.pos_y = float(y)

        self.player_health         = health
        self.alive                 = True
        self.stunned               = False
        self.invulnerable          = False
        self.last_stunned_time     = 0
        self.invulnerable_duration = 1000
        self.wrong_answer          = False
        self.right_answer          = True

        # Imobilizado por um inimigo (a Aranha prende o jogador por um tempo).
        # O main zera 'preso' quando pygame.time.get_ticks() passa de 'preso_ate'.
        self.preso     = False
        self.preso_ate = 0

        self.speed     = speed
        self.size      = size
        self.flip      = False
        self.running   = False

        self.vel_y     = 0.0
        self.on_ground = False
        self.jumping   = False
        self.pes_antes = self.rect.bottom
        self.caindo    = False
        # Pose do golpe de asa (src/combate.py liga ao iniciar o golpe).
        self.pose_golpe_inicio = -10 ** 9
        self.pose_golpe_ate    = -10 ** 9

        # ─── Pulo duplo ─────────────────────────────────────────────────────
        self.jumps_left = self.MAX_JUMPS

    # ── Animação ──────────────────────────────────────────────────────────────
    def _quadro_de_pulo(self):
        """Quadro do pulo pela fase do salto: subida, topo, queda."""
        if self.vel_y < -constants.SPEED_JUMP * 0.45:
            return 0
        if self.vel_y < 0:
            return 1
        if self.vel_y < constants.SPEED_JUMP * 0.35:
            return 2
        return 3

    def _update_animation(self):
        if not self.animated:
            return
        now = pygame.time.get_ticks()

        # Golpe de asa: antecipação com as asas abertas e depois o bote. Só
        # muda o QUADRO desenhado — o rect, a física e a direção não mudam.
        if self.jump_frames and now < self.pose_golpe_ate:
            antecipando = now - self.pose_golpe_inicio < constants.GOLPE_INICIO_MS
            idx = 1 if antecipando else min(3, len(self.jump_frames) - 1)
            self.image_normal = self.jump_frames[idx]
            self.image_flipped = self.jump_frames_espelhados[idx]
            return

        # "No ar" de verdade: parado no chão o on_ground alterna a cada frame
        # (a gravidade de um frame não chega a mover o rect 1 px), e usar só
        # ele fazia o sprite piscar para o quadro de pulo enquanto andava.
        no_ar = not self.on_ground and abs(self.vel_y) > constants.GRAVITY * 3
        if self.jump_frames and no_ar:
            idx = min(self._quadro_de_pulo(), len(self.jump_frames) - 1)
            self.image_normal = self.jump_frames[idx]
            self.image_flipped = self.jump_frames_espelhados[idx]
            return

        if self.walk_frames:
            # Ciclo de 4 quadros andando; parado mostra o quadro 0.
            if self.running:
                if now - self.last_anim_time > self.ANIM_WALK_MS:
                    self.frame_index = (self.frame_index + 1) % len(self.walk_frames)
                    self.last_anim_time = now
            else:
                self.frame_index = 0
        elif self.running and len(self.frames) >= 2:
            # Alterna entre frame idle (0) e walk (1) enquanto se move
            if now - self.last_anim_time > self.ANIM_SPEED:
                self.frame_index    = 1 - (self.frame_index if self.frame_index <= 1 else 0)
                self.last_anim_time = now
        else:
            self.frame_index = 0

        idx = min(self.frame_index, len(self.frames) - 1)
        self.image_normal  = self.frames[idx]
        self.image_flipped = self.frames_espelhados[idx]

    # ── Movimento ─────────────────────────────────────────────────────────────
    def move(self, dx, obstacles):
        self.running = dx != 0
        if dx < 0:
            self.flip = True
        elif dx > 0:
            self.flip = False

        self.vel_y += constants.GRAVITY
        if self.vel_y > constants.VEL_TERMINAL:
            self.vel_y = constants.VEL_TERMINAL

        self.on_ground = False
        # Para o pisão nos inimigos: onde estavam os pés ANTES da queda deste
        # frame e se o personagem estava caindo. Sem isso, cair numa cobra
        # (15 px de altura) atravessava ela e pousava no chão no mesmo frame,
        # e o contato era lido como lateral (dano no jogador).
        self.pes_antes = self.rect.bottom
        self.caindo = self.vel_y > 0

        self.pos_x += dx
        self.rect.x = int(self.pos_x)
        for obs in obstacles:
            if self.rect.colliderect(obs):
                if dx > 0:
                    self.rect.right = obs.left
                elif dx < 0:
                    self.rect.left  = obs.right
                self.pos_x = float(self.rect.x)

        self.pos_y += self.vel_y
        self.rect.y = int(self.pos_y)
        for obs in obstacles:
            if self.rect.colliderect(obs):
                if self.vel_y > 0:
                    self.rect.bottom = obs.top
                    self.on_ground   = True
                    # ─── Pulo duplo: tocou o chão, recarrega os pulos ───
                    self.jumps_left  = self.MAX_JUMPS
                elif self.vel_y < 0:
                    self.rect.top    = obs.bottom
                self.vel_y = 0
                self.pos_y = float(self.rect.y)

        self._update_animation()

    def jump(self):
        # ─── Pulo duplo: usa jumps_left em vez de on_ground ───
        if self.jumps_left > 0:
            self.vel_y       = -constants.SPEED_JUMP
            self.jumping     = True
            self.on_ground   = False
            self.jumps_left -= 1
            return True
        return False

    def apply_damage(self, dano=None):
        """Aplica `dano` (padrão: constants.DAMAGE) se não estiver invulnerável."""
        if self.stunned and self.wrong_answer and not self.invulnerable:
            self.player_health    -= constants.DAMAGE if dano is None else dano
            self.invulnerable      = True
            self.last_stunned_time = pygame.time.get_ticks()
            self.stunned           = False
            self.wrong_answer      = False
            if constants.DEBUG:
                print(f"Dano recebido! Vida restante: {self.player_health}")
            if self.player_health <= 0:
                self.alive         = False
                self.player_health = 0

    def update_invulnerable(self):
        if self.invulnerable:
            if pygame.time.get_ticks() - self.last_stunned_time >= self.invulnerable_duration:
                self.invulnerable = False

    # ── Renderização ──────────────────────────────────────────────────────────
    def draw(self, surface, camera_x, camera_y):
        if self.invulnerable and pygame.time.get_ticks() % 200 < 100:
            return
        image     = self.image_flipped if self.flip else self.image_normal
        draw_rect = self.rect.move(-camera_x, -camera_y)
        surface.blit(image, draw_rect)