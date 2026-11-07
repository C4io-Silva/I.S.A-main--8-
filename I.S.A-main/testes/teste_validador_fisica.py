"""
Prova que o validador de física real (ferramentas/fisica_nivel.py +
validar_fisica_real.py) DISTINGUE percursos possíveis de impossíveis.

Mapas mínimos montados aqui, com resposta conhecida, rodados duas vezes:
com pulo duplo (o jogo) e com pulo simples (controle). Se o validador
aprovasse tudo, ou reprovasse tudo, este teste falha.

Também confere com mapas reais adulterados em memória (os CSVs não são
tocados) que os erros de passagem, chegada e área do Gorila são acusados, e
que a parede de borda do simulador é a mesma do jogo.

Uso (a partir da raiz do projeto):
    python testes/teste_validador_fisica.py
"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("ISA_DB", os.path.join(tempfile.mkdtemp(prefix="isa_teste_"), "estatisticas.db"))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "ferramentas"))
os.chdir(RAIZ)

import ferramentas.fisica.fisica_nivel as F  # noqa: E402

pygame = F.iniciar_pygame()
from src.nucleo import constants  # noqa: E402

T = constants.TILE_SIZE
SOLIDO, VAZIO = 24, -1


def ok(msg):
    print("ok:", msg)


def mapa_salto(vao, desnivel, largura_alvo=3):
    """Plataforma de saída (colunas 0-9) e alvo depois de `vao` colunas, `desnivel` tiles acima."""
    linhas, base = 30, 20
    colunas = 10 + vao + largura_alvo + 4
    g = [[VAZIO] * colunas for _ in range(linhas)]
    for l in (base, base + 1):
        for c in range(10):
            g[l][c] = SOLIDO
    topo = base - desnivel
    c0 = 10 + vao
    for l in (topo, topo + 1):
        for c in range(c0, c0 + largura_alvo):
            g[l][c] = SOLIDO
    return g, base, pygame.Rect(c0 * T, topo * T - 2, largura_alvo * T, 2)


def alcanca(vao, desnivel, pulos):
    g, base, alvo = mapa_salto(vao, desnivel)
    sim = F.Simulador(g, pulos)
    sim.colocar(8, base)
    assert sim.assentar()[0]
    grafo = F.explorar(g, [sim.estado()], [alvo], pulos=pulos)
    return 0 in grafo.alcancados()


CASOS = [
    # (vão, desnível, alcança com pulo duplo?, alcança com pulo simples?)
    (0, 1, True, True),     # degrau de 1 tile
    (0, 2, True, False),    # degrau de 2 tiles: só com pulo duplo
    (0, 3, False, False),   # degrau de 3 tiles: impossível
    (2, 0, True, True),     # vão de 2 tiles
    (4, 0, True, False),    # vão de 4 tiles: só com pulo duplo
    (9, 0, False, False),   # vão de 9 tiles: impossível
    (3, 2, True, False),    # vão 3 subindo 2: só com pulo duplo
]


def teste_distingue_possivel_e_impossivel():
    for vao, dy, duplo, simples in CASOS:
        r2, r1 = alcanca(vao, dy, 2), alcanca(vao, dy, 1)
        assert r2 == duplo, f"vao {vao}, desnivel {dy}: pulo duplo deu {r2}, esperado {duplo}"
        assert r1 == simples, f"vao {vao}, desnivel {dy}: pulo simples deu {r1}, esperado {simples}"
    ok(f"{len(CASOS)} saltos com resposta conhecida: pulo duplo e pulo simples classificados certo")


def teste_poco_sem_saida():
    """Poço de 4 tiles de fundo e 4 de largura (colunas 10-13): quem cai não sobe mais.
    A "passagem" fica à esquerda, no nível do chão."""
    linhas, colunas = 30, 30
    g = [[VAZIO] * colunas for _ in range(linhas)]
    for l in range(20, 30):
        for c in range(colunas):
            if not (10 <= c <= 13 and l < 24):
                g[l][c] = SOLIDO
    sim = F.Simulador(g)
    sim.colocar(5, 20)
    sim.assentar()
    saida = pygame.Rect(2 * T, 16 * T, T, 4 * T)          # "passagem" à esquerda, no chão
    grafo = F.explorar(g, [sim.estado()], [saida])
    presos = F.sem_saida(grafo, {0})
    assert presos, "o poco deveria gerar pontos sem saida"
    # a chave do nó é (x // QUANT, topo do retângulo); o centro fica ~16 px à direita de x
    assert all(10 * T <= k[0] * F.QUANT + 16 < 14 * T and k[1] > 20 * T for k in presos), presos
    ok(f"poço-armadilha detectado ({len(presos)} posições sem saída, todas dentro do poço)")


def teste_parede_de_borda_igual_ao_jogo():
    from types import SimpleNamespace

    from src.entidades.character import Character
    from src.jogo.partida.partida import Partida
    g = [[VAZIO] * 20 for _ in range(10)]
    sim = F.Simulador(g)

    class SetorFalso:
        largura_px = sim.largura
    # limitar_ao_setor só lê `setor_atual` e `player`: dispensa montar uma partida inteira.
    partida = SimpleNamespace(
        setor_atual=SetorFalso(),
        player=Character(0, 0, constants.PLAYER_SIZE, constants.PLAYER_SPEED, None,
                         constants.PLAYER_HEALTH))
    for x in (-40, -1, 0, 300, sim.largura - 10, sim.largura + 25):
        for alvo in (sim.p, partida.player):
            alvo.rect.x = x
            alvo.pos_x = float(x)
        sim.limitar()
        Partida.limitar_ao_setor(partida)
        assert (sim.p.rect.x, sim.p.pos_x) == (partida.player.rect.x, partida.player.pos_x), x
    ok("parede invisível do simulador = Partida.limitar_ao_setor")


def teste_mutacoes_em_mapa_real():
    import ferramentas.validacao.validar_fisica_real as V
    from src.mundo.passagens import Passagem
    d = V.montar_setor("arena")
    rel, _ = V.analisar_setor("arena", dados=d)
    assert not rel.erros, rel.erros
    # 1) saída da arena dentro da área de luta (o bug corrigido em 13/10)
    d = V.montar_setor("arena")
    p0 = d["passagens"][0]
    d["passagens"][0] = Passagem(p0.linha, 36, p0.destino, d["grade"])
    rel, _ = V.analisar_setor("arena", dados=d)
    assert any("area de luta" in e for e in rel.erros), rel.erros
    # 2) chegada dentro da área da passagem (teleporte em sequência)
    d = V.montar_setor("arena")
    d["marcadores"]["chegadas"][constants.TILE_CHEGADA_ARENA] = (1, 23)
    rel, _ = V.analisar_setor("arena", dados=d)
    assert any("teleporte em sequencia" in e for e in rel.erros), rel.erros
    # 3) maçã num lugar inalcançável (bem acima de tudo)
    d = V.montar_setor("arena")
    d["curas"][0] = pygame.Rect(20 * T, 2 * T, 24, 24)
    rel, _ = V.analisar_setor("arena", dados=d)
    assert any("maca #0" in e and "inalcancavel" in e for e in rel.erros), rel.erros
    # 4) pulo simples: as maçãs da arena ficam inalcançáveis (controle no mapa real)
    rel, _ = V.analisar_setor("arena", pulos=1)
    assert any("maca" in e and "inalcancavel" in e for e in rel.erros), rel.erros
    ok("arena real: aprovada; saída na área de luta, chegada dentro de passagem, maçã no alto "
       "e pulo simples são reprovados")


if __name__ == "__main__":
    teste_distingue_possivel_e_impossivel()
    teste_poco_sem_saida()
    teste_parede_de_borda_igual_ao_jogo()
    teste_mutacoes_em_mapa_real()
    print("TODOS OS TESTES DO VALIDADOR DE FISICA PASSARAM")
