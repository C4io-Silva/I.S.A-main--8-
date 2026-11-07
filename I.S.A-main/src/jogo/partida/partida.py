"""
Uma partida em andamento: mundo, jogador, inimigos, combate, quiz e câmera.

A Partida não desenha (ver render.py) e não conhece janelas ou telas de menu:
quando precisa mudar a tela do jogo ela chama `jogo.ir_para(...)`. Os objetos
do setor ativo (world, enemies, itens...) são lidos direto do Setor, então
trocar de setor não deixa nenhuma referência velha para trás.
"""

import pygame

from src.nucleo import constants
from src.mundo import nivel_dados
from src.sistemas import sons
from src.entidades.character import Character
from src.sistemas.combate import EfeitosCombate, GolpeAsa
from src.entidades.enemies.boss import Gorila
from src.jogo.partida.camera import Camera
from src.jogo.partida.entrada import Entrada
from src.jogo.partida.perguntas import BancoPerguntas
from src.jogo.partida.quiz import ControleQuiz
from src.mundo.setores import carregar_setores
from src.nucleo.utils import carregar_imagem, carregar_tiles


def assentar(entidade, col, row_superficie, altura_tiles=0):
    """Apoia o rect da entidade EM CIMA do tile sólido (col, row_superficie)."""
    T = constants.TILE_SIZE
    entidade.rect.centerx = col * T + T // 2
    entidade.rect.bottom = row_superficie * T - altura_tiles * T
    entidade.pos_x = float(entidade.rect.x)
    entidade.pos_y = float(entidade.rect.y)
    return entidade


class Partida:
    def __init__(self, jogo):
        self.jogo = jogo

        self.entrada = Entrada()
        self.camera = Camera()
        self.golpe = GolpeAsa()
        self.efeitos = EfeitosCombate()
        self.perguntas = BancoPerguntas()
        self.quiz = ControleQuiz(self, jogo.tela_quiz)

        self.pontuacao = 0
        self.ordem_resposta = 0
        self.inimigos_derrotados = 0   # só informativo (tela de vitória); não vale ponto
        self.morreu_na_arena = False
        self.aviso = ("", 0)           # aviso curto no rodapé: (texto, até quando)
        self.passagem_ao_alcance = None  # passagem que o player pode usar AGORA

        self.setores = {}
        self.setor_atual = None
        self.player = None

        # Banco relido a cada partida: quem editou os CSVs (Excel, Bloco de
        # Notas) vê a mudança ao clicar em JOGAR/REINICIAR, sem fechar o jogo.
        self.perguntas.nova_partida(
            constants.FASE_POR_REGIAO.get(constants.SETOR_INICIAL, 1))
        # Nova partida = nova sessão de estatísticas: o ID é o que a tela de
        # estatísticas usa para buscar só as respostas DESTA partida.
        self.sessao_id = jogo.banco.nova_sessao(jogo.aluno)
        self._carregar_mundo()

    # ── setor ativo ──────────────────────────────────────────────────────────
    @property
    def world(self):
        return self.setor_atual.world

    @property
    def enemies(self):
        return self.setor_atual.inimigos

    @property
    def itens(self):
        return self.setor_atual.itens

    @property
    def curas(self):
        return self.setor_atual.curas

    @property
    def passagens(self):
        return self.setor_atual.passagens

    @property
    def area_boss(self):
        return self.setor_atual.area_boss

    @property
    def boss(self):
        return self.setor_atual.boss

    def luta_em_andamento(self):
        boss = self.boss
        return boss is not None and boss.em_luta

    def ativar_setor(self, nome):
        """Troca o setor ativo: mundo, inimigos, minérios e passagens juntos."""
        self.setor_atual = self.setores[nome]
        self.efeitos.limpar()
        self.golpe.reiniciar()
        if constants.DEBUG:
            print(f"[setor] {self.setor_atual}")
            self._validar_setor(self.setor_atual)

    @staticmethod
    def _validar_setor(setor):
        """
        Só com DEBUG: confere com os rects REAIS se alguma entidade ficou dentro
        de bloco, sobreposta a outra ou fora do setor, e se todo trecho do setor
        é alcançável a partir da entrada.
        """
        from src.mundo import validacao_mapa

        entidades = [(f"{type(e).__name__}#{i}", e.rect) for i, e in enumerate(setor.inimigos)]
        entidades += [(f"minerio#{i}", it.rect) for i, it in enumerate(setor.itens)]
        entidades += [(f"cura#{i}", c.rect) for i, c in enumerate(setor.curas)]
        problemas = validacao_mapa.validar_csv(setor.grade)
        problemas += validacao_mapa.validar_entidades(
            setor.grade, setor.world.obstacles, entidades
        )
        info = nivel_dados.SETORES_GERADOS.get(setor.nome)
        if info:
            problemas += validacao_mapa.validar_regiao(
                setor.grade, setor.nome, 0, setor.world.colunas - 1,
                info["entrada_col"], info["entrada_row"]
            )
        validacao_mapa.relatorio(problemas, f"VALIDACAO DO SETOR {setor.nome.upper()}")

    def _carregar_mundo(self):
        jogo = self.jogo
        jogo.carregando(0.2, "Carregando tiles...")
        tiles, tile_fallback = carregar_tiles(
            constants.TILE_SPRITES,
            constants.TILE_SIZE,
            constants.TILE_FALLBACK_ID,
        )

        # Todos os setores de uma vez: montar a grade leva poucos ms, e assim o
        # estado de cada setor (minério coletado etc.) sobrevive às idas e voltas.
        jogo.carregando(0.4, "Construindo setores...")
        self.setores = carregar_setores(tiles, tile_fallback)
        self.ativar_setor(constants.SETOR_INICIAL)

        jogo.carregando(0.7, "Carregando personagem...")
        # A animação (andando/pulo) é carregada pelo próprio Character; esta
        # imagem é só o último recurso se faltarem os sprites.
        player_image = carregar_imagem("personagens", "areninha_ISA.png")
        self.player = Character(
            constants.PLAYER_START_X,
            constants.PLAYER_START_Y,
            constants.PLAYER_SIZE,
            constants.PLAYER_SPEED,
            player_image,
            constants.PLAYER_HEALTH,
        )
        # Assenta o player na célula do marcador 90 usando a ALTURA REAL do rect
        # (o sprite é escalado mantendo a proporção).
        assentar(self.player, *self.setor_atual.player_spawn)

        # Enquadra o spawn de imediato: sem isso o primeiro frame mostrava o
        # canto do mapa.
        self.atualizar_camera(instantaneo=True)
        # Força o ambiente inicial (o player pode ter morrido na caverna na
        # partida anterior).
        jogo.ambientes.forcar(self.setor_atual.ambiente)
        # Defensivo: uma transição presa (morte no meio do fade) não passa
        # para a próxima partida.
        jogo.transicao.ativa = False
        jogo.transicao.alpha = 0.0
        jogo.carregando(1.0, "Pronto!")

    # ── câmera ───────────────────────────────────────────────────────────────
    def atualizar_camera(self, instantaneo=False):
        if self.player is None:
            return
        boss = self.boss if self.luta_em_andamento() else None
        self.camera.atualizar(self.player, self.setor_atual.largura_px,
                              self.setor_atual.altura_px, boss, instantaneo)

    # ── avisos ───────────────────────────────────────────────────────────────
    def avisar(self, texto, ms=2500):
        self.aviso = (texto, pygame.time.get_ticks() + ms)

    # ── passagens entre regiões (Fade Out -> reposicionamento -> Fade In) ────
    def _resolver_passagem(self, destino):
        """
        Devolve o callback que a Transicao roda no instante 100% preto: repõe o
        player no spawn do destino, troca o ambiente ativo e resincroniza a
        câmera. Isolado numa função por causa do late binding de closures em
        laço — sem isso, todo callback usaria o último `destino` do laço.
        """
        def _callback():
            # Onde o player reaparece vem do MARCADOR DE CHEGADA desenhado no CSV
            # do setor de destino (constants.PASSAGENS_CSV amarra cada entrada ao
            # seu setor e ao ID da chegada). A célula é a posição.
            destino_setor = self.setores.get(destino.get("setor"))
            chegada = (destino_setor.chegadas.get(destino.get("chegada"))
                       if destino_setor else None)
            if chegada is None:
                print(f"Passagem sem destino valido, ignorada: {destino}")
                return
            self.ativar_setor(destino_setor.nome)
            col, linha = chegada
            player = self.player
            # A base do rect encosta na base da célula da chegada, seja qual for
            # a altura real do sprite.
            player.rect.centerx = col * constants.TILE_SIZE + constants.TILE_SIZE // 2
            player.rect.bottom = (linha + 1) * constants.TILE_SIZE
            player.pos_x, player.pos_y = float(player.rect.x), float(player.rect.y)
            # Zera o momentum: sem isso o player chegava já "caindo" com a
            # velocidade que tinha antes de entrar na passagem.
            player.vel_y = 0.0
            player.on_ground = False
            player.jumps_left = player.MAX_JUMPS
            self.jogo.ambientes.forcar(self.setor_atual.ambiente)
            # O setor é a "fase" do quiz: entrar na caverna endurece as perguntas.
            self.perguntas.avancar_fase(
                constants.FASE_POR_REGIAO.get(self.setor_atual.nome, self.perguntas.fase))
            # instantaneo=True: o reposicionamento acontece com a tela 100% preta,
            # então a câmera tem que SALTAR para o novo enquadramento.
            self.atualizar_camera(instantaneo=True)

        return _callback

    def checar_passagens(self):
        """
        Chamada uma vez por frame enquanto o player está jogando (e nenhuma
        transição já está em andamento).

        "Encostou, aparece o aviso; apertou, entra": a especificação pede que
        o jogador UTILIZE a passagem. Um estilo pode voltar ao teleporte
        automático declarando `"interacao": "toque"` em src/passagens.py.
        """
        self.passagem_ao_alcance = None
        passagens = self.passagens
        if passagens is None:
            return

        perto = passagens.ao_alcance(self.player.rect)
        if perto is None:
            return
        if self.luta_em_andamento():
            # A arena fecha durante a luta: a saída só reabre com o boss vencido.
            if self.entrada.interagir:
                self.avisar("A saida esta bloqueada! Derrote o Gorila primeiro.")
            return

        transicao = self.jogo.transicao
        if not perto.exige_tecla:
            transicao.iniciar(self._resolver_passagem(perto.destino))
            return

        self.passagem_ao_alcance = perto
        if self.entrada.interagir:
            self.entrada.zerar_movimento()
            transicao.iniciar(self._resolver_passagem(perto.destino))

    # ── boss ─────────────────────────────────────────────────────────────────
    def _checar_inicio_da_luta(self):
        """A luta começa quando o jogador cruza a borda da área do boss."""
        boss, area = self.boss, self.area_boss
        if boss is None or boss.ativo or area is None:
            return
        if self.player.rect.left >= area["rect"].left:
            boss.ativar()
            self.avisar("Desvie das BANANAS! Deixe o MINERIO te acertar e responda!", 5000)

    def reiniciar_luta_boss(self):
        """
        TENTAR DE NOVO (game over na arena): recomeça SÓ a luta. O setor da arena
        troca o boss por uma instância nova (nada duplicado, nada herdado) e
        devolve as maçãs; o jogador volta inteiro para a entrada da arena.
        Mapa, minérios já coletados, perguntas e pontuação ficam como estavam.
        """
        jogo = self.jogo
        arena = self.setores.get(nivel_dados.AREA_BOSS["setor"])
        player = self.player
        if arena is None or player is None:
            jogo.iniciar_partida()
            return
        arena.reiniciar_boss()
        self.ativar_setor(arena.nome)
        chegada = arena.chegadas.get(constants.TILE_CHEGADA_ARENA)
        col, linha = chegada if chegada else (3, arena.world.linhas // 2)
        player.rect.centerx = col * constants.TILE_SIZE + constants.TILE_SIZE // 2
        player.rect.bottom = (linha + 1) * constants.TILE_SIZE
        player.pos_x, player.pos_y = float(player.rect.x), float(player.rect.y)
        player.player_health = constants.PLAYER_HEALTH
        player.alive = True
        player.vel_y = 0.0
        player.invulnerable = False
        player.preso = False
        player.jumps_left = player.MAX_JUMPS
        self.quiz.boss = None
        self.quiz.mensagem = ""
        self.morreu_na_arena = False
        self.entrada.zerar_movimento()
        jogo.transicao.ativa = False
        jogo.transicao.alpha = 0.0
        self.atualizar_camera(instantaneo=True)
        jogo.ir_para("JOGANDO")
        jogo.audio.restaurar_volume()

    # ── atualização por frame ────────────────────────────────────────────────
    def area_ativa(self):
        """
        Retângulo (no mundo) onde inimigos são atualizados e desenhados: a tela
        da câmera mais uma folga. Fora dele, nada roda — com dezenas de
        inimigos espalhados pelo mapa, quase todos estão sempre fora.
        """
        folga = constants.MARGEM_ATIVACAO_TILES * constants.TILE_SIZE
        return pygame.Rect(
            self.camera.x - folga,
            self.camera.y - folga,
            constants.SCREEN_WIDTH + 2 * folga,
            constants.SCREEN_HEIGHT + 2 * folga,
        )

    def movimento_do_player(self):
        """Lê a entrada (teclado + analógico) e devolve o dx deste frame."""
        player, entrada, gamepad = self.player, self.entrada, self.jogo.gamepad
        if player.preso and pygame.time.get_ticks() >= player.preso_ate:
            player.preso = False
        if player.preso:
            # Preso pela Aranha: não anda nem pula até o tempo da prisão acabar.
            entrada.pulo = False
            return 0
        if entrada.pulo and player.jump():
            entrada.pulo = False
        # O teclado produz -1/0/1; o analógico soma um valor contínuo, o que
        # permite andar devagar inclinando pouco o direcional.
        eixo = entrada.direita - entrada.esquerda
        if gamepad.conectado:
            eixo += gamepad.eixo_x
        eixo = max(-1.0, min(1.0, eixo))
        return eixo * constants.PLAYER_SPEED

    def _atualizar_inimigos(self, area):
        """Atualiza só os inimigos ativos e trata os que foram derrotados.

        Inimigo atordoado por um golpe não roda a IA (só desliza o empurrão); o
        golpe de asa é aplicado depois do movimento, sobre os inimigos ativos."""
        player, world = self.player, self.world
        inimigos = self.enemies
        for enemy in inimigos:
            if not enemy.precisa_atualizar(area):
                continue
            obstaculos = world.obstaculos_proximos(enemy.rect)
            if getattr(enemy, "atordoado_por_golpe", False):
                enemy.atualizar_atordoado(obstaculos)
            else:
                enemy.update(obstaculos, player)
            enemy.check_player_collision(player)
        # Recalculado depois do movimento: a Aranha, por exemplo, passa a
        # contar (ou deixa de contar) como ativa ao prender/soltar o jogador.
        ativos = [e for e in inimigos if e.precisa_atualizar(area)]
        resultados = self.golpe.atualizar(pygame.time.get_ticks(), player, ativos, self.efeitos)
        for inimigo, resultado in resultados:
            if resultado == "imune" and isinstance(inimigo, Gorila):
                self.avisar("O golpe nao fere o Gorila: devolva os MINERIOS respondendo!", 2500)
        derrotados = [e for e in inimigos if e.derrotado]
        for enemy in derrotados:
            inimigos.remove(enemy)
            self.ao_inimigo_derrotado(enemy)

    def ao_inimigo_derrotado(self, inimigo):
        """
        Evento de derrota de inimigo. Comum (golpe de asa ou pisão): some com um
        "puf" e fica derrotado só neste setor e nesta partida. Boss: encerra a
        campanha (VITORIA).
        """
        if constants.DEBUG:
            print(f"[inimigo] {type(inimigo).__name__} derrotado "
                  f"(recompensa {inimigo.RECOMPENSA_PONTOS})")
        if not isinstance(inimigo, Gorila):
            self.efeitos.puf(inimigo.rect)
            self.inimigos_derrotados += 1
            sons.tocar("pisao")
            return
        if self.setor_atual is not None and self.setor_atual.boss is inimigo:
            self.setor_atual.boss = None
        self.entrada.zerar_movimento()
        try:
            self.jogo.banco.marcar_resultado(self.sessao_id, "vitoria")
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: não foi possível gravar o resultado da sessão: {e}")
        sons.tocar("vitoria")
        self.jogo.ir_para("VITORIA")

    def verificar_coletas(self):
        """Minério tocado abre o quiz. Devolve True se o estado mudou."""
        player = self.player
        for cura in self.curas:
            if cura.verificar_coleta(player):
                self.avisar(f"+{cura.cura} de vida!", 1200)
        self.curas[:] = [c for c in self.curas if not c.coletado]

        banco = self.perguntas
        for item in self.itens:
            if not item.verificar_coleta(player):
                continue
            if banco.indice >= len(banco.fila):
                # A fatia da fase acabou: remonta com o que ainda não foi
                # respondido (o filtro cai para outras dificuldades e, no
                # limite, para o banco inteiro). Antes o minério sumia sem pergunta.
                banco.aplicar_fase(banco.fase)
            if banco.indice < len(banco.fila):
                self.quiz.abrir_para_minerio(item)
                return True
            # Banco vazio (CSV ilegível e sem fallback): o minério fica no mapa.
            item.liberar()
            self.avisar("Nenhuma pergunta disponivel - confira os CSVs (validar_dados.py)")
            return False
        return False

    def limitar_ao_setor(self):
        """
        Parede invisível nas bordas laterais do setor.

        O redesign tirou as colunas de rocha das bordas; sem elas, segurar para
        a esquerda no spawn levava a Areninha para fora do mapa (x < 0), onde
        não há chão. Limitar aqui protege todos os CSVs sem mexer na geometria.
        """
        largura = self.setor_atual.largura_px if self.setor_atual else None
        if not largura:
            return
        player = self.player
        if player.rect.left < 0:
            player.rect.left = 0
            player.pos_x = float(player.rect.x)
        elif player.rect.right > largura:
            player.rect.right = largura
            player.pos_x = float(player.rect.x)

    def atualizar_jogando(self, dt_ms):
        """Um frame de partida: player, câmera, inimigos, coleta e passagens."""
        jogo = self.jogo
        transicao = jogo.transicao
        if transicao.ativa:
            # Fade em andamento: nada de física, inimigo ou item. O callback
            # (reposicionar + trocar ambiente) roda dentro de transicao.atualizar().
            transicao.atualizar(dt_ms)
            return

        player = self.player
        player.move(self.movimento_do_player(), self.world.obstaculos_proximos(player.rect))
        self.limitar_ao_setor()
        self.atualizar_camera()
        player.update_invulnerable()
        self._checar_inicio_da_luta()
        self._atualizar_inimigos(self.area_ativa())
        if jogo.estado_nome != "JOGANDO":       # boss derrotado -> VITORIA
            return
        boss = self.boss
        if boss is not None and boss.minerio_atingiu_player is not None:
            projetil = boss.minerio_atingiu_player
            boss.minerio_atingiu_player = None
            if player.alive:
                self.quiz.iniciar_boss(boss, projetil)
                if jogo.estado_nome == "QUIZ":
                    return
        if self.verificar_coletas():
            return

        if not player.alive or player.rect.top > self.setor_atual.altura_px:
            self.fim_de_jogo()
        else:
            self.checar_passagens()

    def fim_de_jogo(self):
        self.morreu_na_arena = self.luta_em_andamento()
        self.entrada.zerar_movimento()
        if self.sessao_id is not None:
            try:
                self.jogo.banco.marcar_resultado(
                    self.sessao_id, "derrota no boss" if self.morreu_na_arena else "derrota")
            except Exception as e:  # noqa: BLE001
                print(f"Aviso: não foi possível gravar o resultado da sessão: {e}")
        self.jogo.ir_para("GAME_OVER")
