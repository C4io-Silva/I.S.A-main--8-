from src.nucleo import constants


class World:
    """
    Grade de tiles do nível: desenho e colisão.

    Tudo é indexado por CÉLULA (linha, coluna) numa grade 2D. O mapa atual tem
    ~19.000 blocos, mas numa tela cabem ~400 e em volta de uma entidade cabem
    algumas dezenas. Com a grade, tanto o render quanto a colisão consultam só
    as células da região pedida, e o custo por frame deixa de depender do
    tamanho do mapa.

    Versões anteriores indexavam só por COLUNA: cada consulta devolvia as 44
    linhas de cada coluna, e um inimigo testava colisão contra ~400 blocos
    para usar uns 10. A grade corta isso também na vertical.
    """

    def __init__(self):
        self.linhas = 0
        self.colunas = 0
        # _sprites[linha][coluna] = Surface ou None (vazio)
        self._sprites = []
        # _solidos[linha][coluna] = Rect do bloco com colisão, ou None
        self._solidos = []
        self.total_tiles = 0
        self.total_obstaculos = 0

    @property
    def obstacles(self):
        """
        Lista com todos os Rects sólidos. Montada sob demanda: só a validação
        de DEBUG precisa do mapa inteiro, e o jogo não paga por ela.
        """
        return [r for linha in self._solidos for r in linha if r is not None]

    def process_data(self, data, tiles, fallback=None):
        """
        Monta a grade a partir da matriz de IDs do CSV (-1 = vazio).

        tiles: dict {ID: Surface} vindo de utils.carregar_tiles(). IDs sem
               sprite próprio usam `fallback` (ou o sprite de TILE_FALLBACK_ID).
        """
        if not isinstance(tiles, dict):
            tiles = {i: img for i, img in enumerate(tiles)}
        if fallback is None:
            fallback = tiles.get(constants.TILE_FALLBACK_ID)

        T = constants.TILE_SIZE
        self.linhas = len(data)
        self.colunas = max((len(linha) for linha in data), default=0)
        self._sprites = [[None] * self.colunas for _ in range(self.linhas)]
        self._solidos = [[None] * self.colunas for _ in range(self.linhas)]
        self.total_tiles = 0
        self.total_obstaculos = 0

        for y, linha in enumerate(data):
            for x, tile_id in enumerate(linha):
                if tile_id < 0:
                    continue
                img = tiles.get(tile_id, fallback)
                if img is None:
                    continue
                self._sprites[y][x] = img
                self.total_tiles += 1
                if tile_id in constants.SOLID_TILES:
                    self._solidos[y][x] = img.get_rect(topleft=(x * T, y * T))
                    self.total_obstaculos += 1

    def _faixa(self, inicio_px, fim_px, limite, margem):
        T = constants.TILE_SIZE
        ini = max(0, inicio_px // T - margem)
        fim = min(limite - 1, fim_px // T + margem)
        return ini, fim

    def obstaculos_proximos(self, rect, margem=4):
        """
        Rects sólidos nas células em volta de `rect` — nada mais.

        `margem` é a folga em tiles de cada lado. Precisa cobrir o maior
        deslocamento possível num frame (o mergulho do tucano) mais o sensor
        de chão à frente da cobra. 4 tiles cobre os dois com sobra.

        Devolve os MESMOS objetos Rect da grade (nada é copiado).
        """
        c0, c1 = self._faixa(rect.left, rect.right, self.colunas, margem)
        l0, l1 = self._faixa(rect.top, rect.bottom, self.linhas, margem)
        perto = []
        for linha in self._solidos[l0:l1 + 1]:
            for r in linha[c0:c1 + 1]:
                if r is not None:
                    perto.append(r)
        return perto

    def render(self, surface, camera_x, camera_y):
        """Desenha só as células que aparecem na câmera."""
        T = constants.TILE_SIZE
        c0, c1 = self._faixa(camera_x, camera_x + constants.SCREEN_WIDTH - 1,
                             self.colunas, 0)
        l0, l1 = self._faixa(camera_y, camera_y + constants.SCREEN_HEIGHT - 1,
                             self.linhas, 0)
        blit = surface.blit
        for y in range(l0, l1 + 1):
            linha = self._sprites[y]
            py = y * T - camera_y
            for x in range(c0, c1 + 1):
                img = linha[x]
                if img is not None:
                    blit(img, (x * T - camera_x, py))