"""
Câmera da partida.

A câmera antiga travava o centro da tela no centro do player, sem folga
nenhuma. Num mapa alto isso é desconfortável — quem sobe não enxerga o galho
seguinte, quem desce não vê onde vai cair. Três correções, por importância:

1. LOOK-AHEAD HORIZONTAL — desloca-se para o lado que o player está olhando.
2. ANTECIPAÇÃO VERTICAL — a velocidade vertical desloca o alvo: subindo,
   revela o que está acima; caindo, revela o chão que vem.
3. ZONA MORTA VERTICAL — pulinhos não sacodem a câmera; ela só segue o eixo Y
   quando o player realmente sai da faixa.

Tudo é seguido com suavização (interpolação). `instantaneo=True` pula a
suavização — é o que a transição entre regiões usa para já reaparecer
enquadrada.
"""

from src.nucleo import constants


class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        self._foco_y = None      # linha de referência vertical que a câmera persegue
        self._iniciada = False

    def atualizar(self, player, largura_mapa, altura_mapa, boss=None, instantaneo=False):
        """`boss` só deve ser passado durante a luta (enquadra jogador e boss)."""
        W, H = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT

        # 1. Horizontal: empurra o enquadramento para o lado que o player encara.
        direcao = -1 if getattr(player, "flip", False) else 1
        alvo_x = player.rect.centerx + direcao * constants.CAM_AVANCO_X - W // 2

        # 3. Zona morta: o foco vertical só se move quando o player sai da faixa.
        if self._foco_y is None or instantaneo:
            self._foco_y = float(player.rect.centery)
        else:
            desvio = player.rect.centery - self._foco_y
            if abs(desvio) > constants.CAM_ZONA_MORTA_Y:
                self._foco_y += desvio - constants.CAM_ZONA_MORTA_Y * (1 if desvio > 0 else -1)
            if getattr(player, "on_ground", False):
                # Pisou no chão: reancora de vez, senão a zona morta acumula
                # erro e a câmera fica torta depois de uma queda longa.
                self._foco_y = float(player.rect.centery)

        # 2. Antecipação vertical proporcional à velocidade de queda/subida.
        antecipacao = player.vel_y * constants.CAM_ANTECIPACAO_Y
        antecipacao = max(-constants.CAM_AVANCO_SUBIDA,
                          min(constants.CAM_AVANCO_QUEDA, antecipacao))
        alvo_y = self._foco_y + antecipacao - H // 2

        if boss is not None:
            # Luta contra o boss: enquadra jogador E boss (ponto médio, sem
            # perder o jogador de vista) e sobe o horizonte para mostrar o
            # espaço dos arremessos em vez da terra embaixo do chão.
            meio = (player.rect.centerx + boss.rect.centerx) / 2
            folga = W // 2 - constants.TILE_SIZE * 2
            alvo_x = max(player.rect.centerx - W // 2 - folga,
                         min(meio - W // 2, player.rect.centerx - W // 2 + folga))
            alvo_y = boss.rect.bottom - int(H * 0.74)

        # Limites do mapa: impedem a câmera de revelar vazio fora do mundo.
        alvo_x = max(0, min(alvo_x, largura_mapa - W))
        alvo_y = max(0, min(alvo_y, altura_mapa - H))

        if instantaneo or not self._iniciada:
            self.x, self.y = int(alvo_x), int(alvo_y)
            self._iniciada = True
            return

        k = constants.CAM_SUAVIZACAO
        x = self.x + (alvo_x - self.x) * k
        y = self.y + (alvo_y - self.y) * k
        self.x = int(max(0, min(x, largura_mapa - W)))
        self.y = int(max(0, min(y, altura_mapa - H)))
