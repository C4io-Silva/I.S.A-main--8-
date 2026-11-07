"""Desenho da partida: cena (mundo + entidades) e HUD."""

import random

import pygame

from src.nucleo import constants
from src.jogo.visual import desenhar_barra_vida, texto


def desenhar_partida(jogo, partida, tela, sobreposicao=None, tremor_ativo=True,
                     mostrar_aviso_passagem=True):
    """
    Cena + HUD (+ `sobreposicao`, se houver) + transição por cima de tudo.

    `sobreposicao(tela)` é desenhada depois da HUD e antes do fade — é onde o
    menu de pausa entra. `tremor_ativo` liga o tremor de câmera pedido pelo
    boss (rugido, pancada); ele existe só no desenho: a câmera real não muda.
    """
    boss = partida.boss
    tremor = boss.tremor if (boss is not None and tremor_ativo) else 0
    camera_x, camera_y = partida.camera.x, partida.camera.y
    if tremor:
        camera_x += random.randint(-tremor, tremor)
        camera_y += random.randint(-tremor, tremor)
    desenhar_cena(jogo, partida, tela, camera_x, camera_y)
    desenhar_hud(jogo, partida, tela, mostrar_aviso_passagem)
    if sobreposicao is not None:
        sobreposicao(tela)
    # Última camada: o fade precisa esconder a cena inteira, HUD incluída.
    jogo.transicao.desenhar(tela)


def desenhar_cena(jogo, partida, tela, camera_x, camera_y):
    """Mundo e entidades, com culling pela área visível."""
    area = partida.area_ativa()
    setor = partida.setor_atual
    player = partida.player

    # O ambiente é escolhido pela ALTURA do jogador, não da câmera: nas bordas
    # do mapa a câmera trava e a transição congelaria pela metade.
    jogo.ambientes.desenhar(tela, camera_x, player.rect.centery if player else None, camera_y)
    setor.estruturas.render(tela, camera_x, camera_y)
    setor.decoracoes.render(tela, camera_x, camera_y)
    partida.world.render(tela, camera_x, camera_y)
    # Depois do mundo e antes das entidades: o player passa NA FRENTE da
    # entrada, e a entrada na frente do terreno.
    if partida.passagens:
        partida.passagens.desenhar(tela, camera_x, camera_y, pygame.time.get_ticks() / 1000.0)
    for enemy in partida.enemies:
        if area.colliderect(enemy.area_desenho()):
            enemy.draw(tela, camera_x, camera_y)
            enemy.desenhar_feedback(tela, camera_x, camera_y)
    for item in partida.itens:
        if area.colliderect(item.rect):
            item.draw(tela, camera_x, camera_y)
    for cura in partida.curas:
        if area.colliderect(cura.rect):
            cura.draw(tela, camera_x, camera_y)
    if player and player.alive:
        player.draw(tela, camera_x, camera_y)
        partida.golpe.desenhar(tela, camera_x, camera_y, player)
    partida.efeitos.desenhar(tela, camera_x, camera_y)
    # Tonalidade, luz e partículas: depois da cena e antes da HUD, porque
    # escurecer a caverna faz sentido, escurecer a barra de vida não.
    jogo.ambientes.desenhar_atmosfera(tela, camera_x, camera_y)
    if constants.DEBUG and partida.area_boss:
        pygame.draw.rect(tela, (255, 60, 60),
                         partida.area_boss["rect"].move(-camera_x, -camera_y), 2)


def desenhar_hud(jogo, partida, tela, mostrar_aviso_passagem=True):
    W = constants.SCREEN_WIDTH
    fontes = jogo.fontes
    gamepad = jogo.gamepad
    player = partida.player
    if constants.DEBUG:
        ambientes = jogo.ambientes
        dbg = fontes.titulo.render(
            f"{ambientes.nome_atual}  {ambientes.mistura:.0%}", True, constants.YELLOW)
        tela.blit(dbg, (10, 70))
    dica = ("Start = Pausa   B = Golpe" if gamepad.conectado
            else "ESC = Pausa   J = Golpe")
    tela.blit(texto(fontes.titulo, dica, constants.WHITE), (10, 10))
    if (partida.passagem_ao_alcance and mostrar_aviso_passagem
            and not jogo.transicao.ativa):
        _desenhar_aviso_passagem(jogo, partida, tela)
    if player and player.alive:
        desenhar_barra_vida(tela, 10, 35, 200, 18,
                            player.player_health / constants.PLAYER_HEALTH)
        pontos = texto(fontes.ui, f"Pontos: {partida.pontuacao}", constants.WHITE)
        tela.blit(pontos, (W - pontos.get_width() - 14, 10))
    _desenhar_hud_boss(jogo, partida, tela)
    _desenhar_aviso_jogo(jogo, partida, tela)


def _desenhar_aviso_passagem(jogo, partida, tela):
    W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
    botao = "X" if jogo.gamepad.conectado else "E"
    aviso = texto(jogo.fontes.titulo, f"{botao} - {partida.passagem_ao_alcance.rotulo}",
                  constants.YELLOW)
    caixa = aviso.get_rect(center=(W // 2, H - 70))
    fundo = pygame.Surface((caixa.width + 28, caixa.height + 16), pygame.SRCALPHA)
    fundo.fill((0, 0, 0, 170))
    tela.blit(fundo, fundo.get_rect(center=caixa.center))
    tela.blit(aviso, caixa)


def _desenhar_hud_boss(jogo, partida, tela):
    """Nome + barra de vida do boss (sincronizada com boss.vida) no topo."""
    boss = partida.boss
    if boss is None or not boss.ativo:
        return
    titulo = jogo.fontes.titulo
    W = constants.SCREEN_WIDTH
    larg = min(420, W - 460)
    x = (W - larg) // 2
    y = 14
    nome = texto(titulo, f"{boss.NOME}  -  FASE {boss.fase}", constants.YELLOW)
    tela.blit(nome, nome.get_rect(midbottom=(W // 2, y + 16)))
    desenhar_barra_vida(tela, x, y + 20, larg, 16, boss.proporcao_vida,
                        cor_cheia=(200, 60, 40), cor_vazia=(50, 20, 20))
    # Marcas de cada ponto de vida: mostram quantos minérios faltam.
    for i in range(1, boss.VIDA_MAX):
        mx = x + larg * i // boss.VIDA_MAX
        pygame.draw.line(tela, (20, 10, 10), (mx, y + 21), (mx, y + 34), 1)
    if boss.estado == "ATORDOADO":
        st = texto(titulo, "ATORDOADO!", (255, 230, 120))
        tela.blit(st, st.get_rect(midtop=(W // 2, y + 40)))


def _desenhar_aviso_jogo(jogo, partida, tela):
    msg, ate = partida.aviso
    if not msg or pygame.time.get_ticks() >= ate:
        return
    W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
    surf = texto(jogo.fontes.titulo, msg, constants.WHITE)
    if surf.get_width() > W - 40:
        surf = pygame.transform.smoothscale(
            surf, (W - 40, max(1, int(surf.get_height() * (W - 40) / surf.get_width()))))
    caixa = surf.get_rect(center=(W // 2, H - 110))
    fundo = pygame.Surface((caixa.width + 24, caixa.height + 12), pygame.SRCALPHA)
    fundo.fill((0, 0, 0, 180))
    tela.blit(fundo, fundo.get_rect(center=caixa.center))
    tela.blit(surf, caixa)
