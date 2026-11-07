"""
Boss final: o GORILA da arena (setor "arena", no alto da copa).

Origem: protótipo do fork "isa_boss (em andamento)" — sprites, arremesso de
bananas, minério que abre pergunta e é devolvido ao boss, atordoamento e
8 minérios para vencer. Na unificação ele foi:

  * integrado ao sistema de inimigos da v12 (herda Enemy, usa VIDA_MAX /
    receber_dano / derrotado / SEMPRE_ATIVO, é criado pelo setor da arena a
    partir do marcador 95 e atualizado pelo mesmo laço dos outros inimigos);
  * ampliado com aparição, duas fases, salto-pancada com onda de choque,
    animação de derrota e reinício limpo.

COMO A LUTA FUNCIONA (o que o jogador vê)
-----------------------------------------
  APARIÇÃO  — quando o jogador cruza a borda da área de luta, o Gorila ruge
              (GORILA_INTRO_MS) sem atacar; a barra de vida aparece.
  ARREMESSO — pose de aviso (GORILA_POSE_ARREMESSO) e depois o projétil,
              mirado onde o jogador ESTAVA:
                * BANANA: desvie (andar ou pular basta). Dano 10.
                * MINÉRIO (cobre/zinco), 1 por ciclo de 5 arremessos, e a
                  pose mostra o gorila segurando a pedra: deixe ACERTAR.
                  Abre uma pergunta com tempo; acertou -> o minério volta e
                  acerta o boss; errou/tempo esgotado -> dano.
  ATORDOADO — ao levar o minério de volta: GORILA_ATORDOADO_MS sem atacar
              (janela de recuperação; as maçãs das plataformas curam).
  FASE 2    — com metade da vida: arremessos mais rápidos e o SALTO-PANCADA
              (tremor + faixa vermelha no chão como aviso -> salto -> duas
              ondas de choque correm pelo chão). Pule a onda.
  DERROTA   — com 0 de vida: animação de queda; ao terminar o boss fica
              `derrotado` e o main abre a tela de vitória.

Justiça do combate: todo ataque tem aviso visual antes; nenhum dano se
repete por frame (a invencibilidade do jogador vale para tudo); sempre há
pelo menos um minério por ciclo, então a vitória é sempre possível.
"""

import math
import random

import pygame

from src.nucleo import constants
from src.sistemas import sons
from src.entidades.enemies.enemy import Enemy
from src.nucleo.utils import carregar_imagem

ARQUIVOS_MINERIO = {
    "cobre": "gorila_minerio_cobre_cenario_01.png",
    "zinco": "gorila_minerio_zinco_cenario_01.png",
}
POSE_PREPARO = {"cobre": "gorila_55_cenario_01.png",
                "zinco": "gorila_63_cenario_01.png",
                None: "gorila_53_cenario_01.png"}
SPRITE_ATORDOADO = "gorila_estunado_cenario_01.png"


def _recortar(surf):
    rects = pygame.mask.from_surface(surf).get_bounding_rects()
    if not rects:
        return surf
    return surf.subsurface(rects[0].unionall(rects[1:])).copy()


_cache_poses = {}


def _pose(arquivo, altura, inverter):
    """Pose recortada e escalada pela ALTURA (as artes têm resoluções diferentes)."""
    chave = (arquivo, altura, inverter)
    if chave not in _cache_poses:
        img = _recortar(carregar_imagem("inimigos", arquivo))
        largura = max(1, round(img.get_width() * altura / img.get_height()))
        img = pygame.transform.smoothscale(img, (largura, altura))
        _cache_poses[chave] = pygame.transform.flip(img, True, False) if inverter else img
    return _cache_poses[chave]


class ProjetilGorila:
    """Banana (dano) ou minério (abre pergunta quando acerta o jogador)."""

    def __init__(self, dono, x, y, vx, vy, tipo_minerio=None, gravidade=0.0, alvo_x=None):
        self.dono = dono
        self.gravidade = gravidade    # banana: arco; minério: linha reta
        self.alvo_x = alvo_x          # onde a banana vai cair (sombra no chão)
        self.tipo_minerio = tipo_minerio
        self.estado = "voando"           # voando | aguardando_resposta | retornando
        tam = constants.GORILA_PROJETIL_SIZE
        if tipo_minerio is None:
            self.image = carregar_imagem("inimigos", constants.GORILA_PROJETIL, (tam, tam))
        else:
            self.image = carregar_imagem("itens", ARQUIVOS_MINERIO[tipo_minerio],
                                         (int(tam * 1.15), int(tam * 1.15)))
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.pos_x, self.pos_y = float(self.rect.x), float(self.rect.y)
        self.vx, self.vy = vx, vy
        self.angulo = 0.0

    @property
    def eh_minerio(self):
        return self.tipo_minerio is not None

    def update(self, player):
        """Devolve False quando o projétil deve sumir."""
        if self.estado == "aguardando_resposta":
            return True
        if self.estado == "retornando":
            dx = self.dono.rect.centerx - self.rect.centerx
            dy = self.dono.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy) or 1.0
            v = constants.GORILA_PROJETIL_SPEED_F2 * 1.4
            self.pos_x += dx / dist * v
            self.pos_y += dy / dist * v
            self.rect.topleft = (round(self.pos_x), round(self.pos_y))
            if self.rect.colliderect(self.dono.rect) or dist < v:
                self.dono.levar_minerio()
                return False
            return True

        self.vy += self.gravidade
        self.pos_x += self.vx
        self.pos_y += self.vy
        self.angulo = (self.angulo + 12) % 360
        self.rect.topleft = (round(self.pos_x), round(self.pos_y))

        # Jogador ANTES do cenário: o projétil mira o centro do jogador, e
        # perto do chão ele encostaria no bloco um frame antes de acertá-lo.
        if player is not None and player.alive and self.rect.colliderect(player.rect):
            if self.eh_minerio:
                # Pausa no ar e avisa o boss: o main abre a pergunta.
                self.estado = "aguardando_resposta"
                self.dono.minerio_atingiu_player = self
                return True
            self.causar_dano(player)
            return False
        # Só o CHÃO da arena para o projétil. As plataformas não servem de
        # escudo: debaixo delas o minério nunca chegaria ao jogador e a luta
        # travaria (achado no teste da luta completa). Elas continuam úteis
        # para mudar de altura e fugir das bananas.
        chao = self.dono.chao_y
        miolo = self.rect.inflate(-self.rect.width // 2, -self.rect.height // 2)
        for o in self.dono.obstaculos_proximos(self.rect):
            if (chao is None or o.top >= chao) and miolo.colliderect(o):
                return False
        return self.dono.limites.colliderect(self.rect)

    def causar_dano(self, player):
        _aplicar_dano(player, constants.GORILA_PROJETIL_DAMAGE)

    def refletir(self):
        self.estado = "retornando"

    def draw(self, surface, camera_x, camera_y):
        img = self.image
        if self.alvo_x is not None and self.estado == "voando" and self.dono.chao_y:
            # Sombra no ponto de queda: mostra para onde NÃO ficar.
            larg = self.rect.width
            sombra = pygame.Rect(0, 0, larg, max(4, larg // 4))
            sombra.midbottom = (int(self.alvo_x) - camera_x, self.dono.chao_y - camera_y)
            pygame.draw.ellipse(surface, (40, 20, 10), sombra)
        if not self.eh_minerio and self.estado == "voando":
            img = pygame.transform.rotate(self.image, self.angulo)
        surface.blit(img, img.get_rect(center=self.rect.center).move(-camera_x, -camera_y))


def _aplicar_dano(player, dano):
    """Dano no jogador respeitando a invencibilidade (nunca repete por frame)."""
    if player is None or not player.alive or player.invulnerable:
        return False
    player.player_health = max(0, player.player_health - dano)
    player.invulnerable = True
    player.last_stunned_time = pygame.time.get_ticks()
    sons.tocar("dano")
    if player.player_health <= 0:
        player.alive = False
    return True


class OndaDeChoque:
    """Onda que corre pelo chão depois do salto-pancada. Pule para desviar."""

    def __init__(self, x, chao_y, direcao, limites):
        self.direcao = direcao
        self.limites = limites
        alt = constants.GORILA_ONDA_ALTURA
        self.rect = pygame.Rect(0, 0, int(alt * 1.4), alt)
        self.rect.midbottom = (int(x), chao_y)
        self.pos_x = float(self.rect.x)
        self.ativa = True

    def update(self, player):
        self.pos_x += constants.GORILA_ONDA_VELOCIDADE * self.direcao
        self.rect.x = int(self.pos_x)
        if player is not None and self.rect.colliderect(player.rect):
            _aplicar_dano(player, constants.GORILA_ONDA_DANO)
        return self.limites.contains(self.rect)

    def draw(self, surface, camera_x, camera_y):
        r = self.rect.move(-camera_x, -camera_y)
        t = pygame.time.get_ticks() / 60.0
        pontos = [(r.left, r.bottom)]
        for i in range(9):
            px = r.left + r.width * i / 8
            py = r.top + r.height * (0.35 + 0.35 * math.sin(t + i))
            pontos.append((px, py))
        pontos.append((r.right, r.bottom))
        pygame.draw.polygon(surface, (235, 205, 120), pontos)
        pygame.draw.lines(surface, (120, 80, 30), False, pontos, 2)


class Gorila(Enemy):
    PASTA_SPRITES = "inimigos"
    SPRITE_FACES_LEFT = False
    ARQUIVOS_FRAMES = [f"gorila_0{i}.png" for i in range(1, 7)]
    LARGURA_ALVO = max(1, int(190 * constants.SCALE / 5))
    COR_PROVISORIA = (40, 40, 60)
    NOME = "GORILA GUARDIÃO"

    VIDA_MAX = constants.GORILA_VIDA
    DANO = constants.GORILA_DANO_CONTATO
    INVENCIVEL = False
    RECOMPENSA_PONTOS = 10
    SEMPRE_ATIVO = True          # age mesmo com a câmera longe (arena larga)
    # O golpe de asa da Areninha não fere o Gorila: ele tem a mecânica
    # própria (devolver minérios respondendo perguntas). Ver src/combate.py.
    IMUNE_A_GOLPE = True
    VELOCIDADE_PATRULHA = 0
    VELOCIDADE_PERSEGUICAO = 0
    VEL_ANIM_PATRULHA = 180
    DURACAO_DERROTA_MS = 1600

    def __init__(self, x, y):
        super().__init__(x, y)
        self.estado = "AGUARDANDO"   # AGUARDANDO|INTRO|COMBATE|ATORDOADO|DERROTA
        self.ativo = False
        self.projeteis = []
        self.ondas = []
        self.lancamentos = 0
        self._pos_minerio_ciclo = 0
        self._tipo_minerio_ciclo = "cobre"
        self.preparando = None        # None ou (tipo_minerio|None, fim_ms)
        self.pancada = None           # None ou dict com fase/tempos
        self.proximo_ataque = 0
        self.proxima_pancada = 0
        self.atordoado_ate = 0
        self.intro_ate = 0
        self.derrota_ate = 0
        self.flash_ate = 0
        self.minerio_atingiu_player = None
        self.tremor = 0               # px de tremor de câmera pedido ao main
        self.obstaculos_proximos = lambda rect: []
        self.limites = pygame.Rect(0, 0, 10 ** 6, 10 ** 6)
        self.chao_y = None

    # ── ligação com o setor/main ──────────────────────────────────────────
    def conectar(self, world, limites_px):
        """Chamado pelo setor: de onde vêm os obstáculos e até onde ir."""
        self.obstaculos_proximos = world.obstaculos_proximos
        self.limites = pygame.Rect(limites_px)

    @property
    def fase(self):
        return 2 if self.vida <= self.VIDA_MAX // 2 else 1

    @property
    def em_luta(self):
        return self.ativo and self.estado != "DERROTA" and not self.derrotado

    def ativar(self):
        if self.ativo:
            return
        agora = pygame.time.get_ticks()
        self.ativo = True
        self.estado = "INTRO"
        self.intro_ate = agora + constants.GORILA_INTRO_MS
        self.proximo_ataque = self.intro_ate + 300
        self.proxima_pancada = self.intro_ate + constants.GORILA_PANCADA_INTERVALO
        self.tremor = 8
        sons.tocar("rugido")

    # ── combate (pontos de extensão do Enemy) ─────────────────────────────
    def receber_dano(self, quantidade):
        """Sobrescreve o Enemy: a derrota tem animação antes do `derrotado`."""
        if self.estado == "DERROTA" or self.derrotado:
            return False
        self.vida = max(0, self.vida - quantidade)
        self.flash_ate = pygame.time.get_ticks() + 250
        sons.tocar("boss_dano")
        if self.vida == 0:
            self.estado = "DERROTA"
            self.derrota_ate = pygame.time.get_ticks() + self.DURACAO_DERROTA_MS
            self.projeteis = [p for p in self.projeteis if p.estado == "aguardando_resposta"]
            self.ondas = []
            self.preparando = self.pancada = None
            return True
        return False

    def levar_minerio(self):
        """O minério devolvido pelo jogador acertou o boss."""
        derrotou = self.receber_dano(1)
        if not derrotou:
            self.estado = "ATORDOADO"
            self.atordoado_ate = pygame.time.get_ticks() + constants.GORILA_ATORDOADO_MS
            self.preparando = None
            self.pancada = None
            self.tremor = 5

    def check_player_collision(self, player):
        if not self.ativo or self.estado == "DERROTA" or not self.rect.colliderect(player.rect):
            return False
        if player.rect.centerx < self.rect.centerx:
            player.pos_x -= constants.KNOCKBACK_X
        else:
            player.pos_x += constants.KNOCKBACK_X
        if player.vel_y >= 0 and player.rect.bottom <= self.rect.top + self.rect.height // 4:
            player.vel_y = -constants.QUIQUE_Y   # pular na cabeça só quica
            return False
        _aplicar_dano(player, self.DANO)
        return True

    # ── ciclo de arremessos ───────────────────────────────────────────────
    def _proximo_tipo_projetil(self):
        """1 minério em posição aleatória a cada ciclo; o resto são bananas."""
        n = constants.GORILA_ARREMESSOS_POR_CICLO
        no_ciclo = self.lancamentos % n
        if no_ciclo == 0:
            self._pos_minerio_ciclo = random.randrange(n)
            self._tipo_minerio_ciclo = random.choice(tuple(ARQUIVOS_MINERIO))
        self.lancamentos += 1
        return self._tipo_minerio_ciclo if no_ciclo == self._pos_minerio_ciclo else None

    def _lancar(self, player, tipo):
        """
        BANANA: arco (parábola) que cai onde o jogador ESTAVA, com sombra no
        chão — desvia-se saindo do lugar. Uma linha reta mirada no centro do
        jogador era praticamente indesviável (o teste com bot apanhava de
        todas). MINÉRIO: linha reta e mais lenta, para ser "pego".
        """
        mao_x = self.rect.centerx + self.direcao * self.rect.width * 0.4
        mao_y = self.rect.top + self.rect.height * 0.35
        v = (constants.GORILA_PROJETIL_SPEED if self.fase == 1
             else constants.GORILA_PROJETIL_SPEED_F2)
        if tipo is not None:
            dx = player.rect.centerx - mao_x
            dy = player.rect.centery - mao_y
            dist = math.hypot(dx, dy) or 1.0
            v *= 0.8
            proj = ProjetilGorila(self, mao_x, mao_y, dx / dist * v, dy / dist * v, tipo)
        else:
            alvo_x = player.rect.centerx
            alvo_y = (self.chao_y or player.rect.bottom) - constants.GORILA_PROJETIL_SIZE // 2
            dx = alvo_x - mao_x
            dy = alvo_y - mao_y
            # tempo de voo em frames: proporcional à distância, com piso (dá
            # tempo de reagir) e teto (não fica pendurado no ar).
            t = max(50.0, min(80.0, abs(dx) / v))
            g = constants.GRAVITY * 0.9
            vx = dx / t
            vy = (dy - 0.5 * g * t * t) / t
            proj = ProjetilGorila(self, mao_x, mao_y, vx, vy, None, gravidade=g, alvo_x=alvo_x)
        self.projeteis.append(proj)
        sons.tocar("arremesso")

    # ── física mínima (o boss não anda; só cai/assenta e salta) ───────────
    def _assentar(self):
        self.vel_y = min(self.vel_y + constants.GRAVITY, constants.VEL_TERMINAL)
        self.pos_y += self.vel_y
        self.rect.y = int(self.pos_y)
        self.on_ground = False
        for obs in self.obstaculos_proximos(self.rect):
            if self.rect.colliderect(obs):
                if self.vel_y > 0:
                    self.rect.bottom = obs.top
                    self.on_ground = True
                    if self.chao_y is None:
                        self.chao_y = obs.top
                elif self.vel_y < 0:
                    self.rect.top = obs.bottom
                self.vel_y = 0.0
                self.pos_y = float(self.rect.y)

    # ── atualização ───────────────────────────────────────────────────────
    def update(self, obstacles, player=None):
        agora = pygame.time.get_ticks()
        self._assentar()
        self.tremor = max(0, self.tremor - 1) if self.tremor else 0
        if player is not None and self.estado not in ("DERROTA",):
            self.direcao = 1 if player.rect.centerx >= self.rect.centerx else -1

        if self.estado == "DERROTA":
            if agora >= self.derrota_ate:
                self.derrotado = True    # o main remove e chama ao_inimigo_derrotado
            self._atualizar_projeteis(player)
            return

        if not self.ativo:
            self._atualizar_animacao()
            return

        if self.estado == "INTRO":
            if agora >= self.intro_ate:
                self.estado = "COMBATE"
            self._atualizar_animacao()
            return

        if self.estado == "ATORDOADO":
            if agora >= self.atordoado_ate:
                self.estado = "COMBATE"
                self.proximo_ataque = agora + 600
            self._atualizar_projeteis(player)
            return

        # COMBATE
        if self.pancada:
            self._atualizar_pancada(agora)
        elif self.preparando:
            tipo, fim = self.preparando
            if agora >= fim:
                self.preparando = None
                if player is not None and player.alive:
                    self._lancar(player, tipo)
                intervalo = (constants.GORILA_INTERVALO_ATAQUE if self.fase == 1
                             else constants.GORILA_INTERVALO_ATAQUE_F2)
                self.proximo_ataque = agora + intervalo
        elif self.fase == 2 and agora >= self.proxima_pancada and self.on_ground:
            self.pancada = {"etapa": "aviso", "ate": agora + constants.GORILA_PANCADA_AVISO_MS}
        elif agora >= self.proximo_ataque and player is not None and player.alive:
            tipo = self._proximo_tipo_projetil()
            self.preparando = (tipo, agora + constants.GORILA_POSE_ARREMESSO)

        self._atualizar_projeteis(player)
        self._atualizar_animacao()

    def _atualizar_pancada(self, agora):
        p = self.pancada
        if p["etapa"] == "aviso" and agora >= p["ate"]:
            p["etapa"] = "salto"
            self.vel_y = -constants.SPEED_JUMP * 1.3
            self.on_ground = False
        elif p["etapa"] == "salto" and self.on_ground and self.vel_y == 0:
            chao = self.rect.bottom
            for d in (-1, 1):
                self.ondas.append(OndaDeChoque(self.rect.centerx + d * self.rect.width * 0.4,
                                               chao, d, self.limites))
            self.tremor = 12
            sons.tocar("pancada")
            p["etapa"] = "recuperacao"
            p["ate"] = agora + 900       # janela: o boss fica parado
        elif p["etapa"] == "recuperacao" and agora >= p["ate"]:
            self.pancada = None
            self.proxima_pancada = agora + constants.GORILA_PANCADA_INTERVALO
            self.proximo_ataque = agora + 500

    def _atualizar_projeteis(self, player):
        self.projeteis = [p for p in self.projeteis if p.update(player)]
        self.ondas = [o for o in self.ondas if o.update(player)]

    def limpar_ataques(self):
        """Some com bananas/ondas em voo (usado ao reiniciar a luta)."""
        self.projeteis = []
        self.ondas = []
        self.minerio_atingiu_player = None

    def area_desenho(self):
        return self.rect.inflate(self.rect.width * 2, self.rect.height)

    def desenhar_feedback(self, surface, camera_x, camera_y):
        """O boss tem flash e barra de vida próprios (HUD); nada aqui."""

    # ── desenho ───────────────────────────────────────────────────────────
    def draw(self, surface, camera_x, camera_y):
        agora = pygame.time.get_ticks()
        h = self.rect.height
        inverter = self.direcao < 0
        imagem = None
        dy = 0
        if self.estado == "DERROTA":
            prog = 1 - max(0, self.derrota_ate - agora) / self.DURACAO_DERROTA_MS
            imagem = _pose(SPRITE_ATORDOADO, int(h * 1.15), inverter).copy()
            imagem.set_alpha(int(255 * (1 - prog * 0.85)))
            dy = int(prog * h * 0.15)
        elif self.estado == "ATORDOADO":
            imagem = _pose(SPRITE_ATORDOADO, int(h * 1.15), inverter)
        elif self.pancada and self.pancada["etapa"] == "aviso":
            imagem = _pose(POSE_PREPARO[None], h, inverter)
            dy = 0
            # aviso: faixa vermelha pulsando no chão dos dois lados
            alcance = self.rect.width * 3
            alpha = 90 + int(80 * (0.5 + 0.5 * math.sin(agora / 70)))
            faixa = pygame.Surface((alcance * 2 + self.rect.width, 8), pygame.SRCALPHA)
            faixa.fill((230, 40, 40, alpha))
            surface.blit(faixa, (self.rect.centerx - faixa.get_width() // 2 - camera_x,
                                 self.rect.bottom - 8 - camera_y))
        elif self.preparando:
            imagem = _pose(POSE_PREPARO[self.preparando[0]], h, inverter)

        if imagem is None:
            super().draw(surface, camera_x, camera_y)
            quadros = self.frames_direita if self.direcao > 0 else self.frames_esquerda
            desenhada = quadros[min(self.frame_atual, len(quadros) - 1)]
            pos = (self.rect.x - camera_x, self.rect.y - camera_y)
        else:
            tremor = (agora // 40) % 3 - 1 if self.pancada and self.pancada["etapa"] == "aviso" else 0
            x = self.rect.centerx - imagem.get_width() // 2 - camera_x + tremor * 2
            y = self.rect.bottom - imagem.get_height() - camera_y + dy
            surface.blit(imagem, (x, y))
            desenhada, pos = imagem, (x, y)

        if agora < self.flash_ate:
            # Brilho com a FORMA do sprite desenhado (antes era um retângulo do
            # tamanho da hitbox, mais estreito que a arte: aparecia uma "caixa").
            brilho = pygame.mask.from_surface(desenhada).to_surface(
                setcolor=(255, 255, 255, 110), unsetcolor=(0, 0, 0, 0))
            surface.blit(brilho, pos)
        for o in self.ondas:
            o.draw(surface, camera_x, camera_y)
        for p in self.projeteis:
            p.draw(surface, camera_x, camera_y)
