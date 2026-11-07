"""Música de fundo e volumes (música e efeitos)."""

from pygame import mixer

from src.sistemas import sons
from src.nucleo.utils import carregar_musica

MUSICA_JOGO = "wily.wav"            # arquivo dentro de assets/songs/
MUSICA_MENU = "audio_cefsa.wav"     # loop de 7 s, só na tela inicial

VOLUME_NORMAL = 1
VOLUME_QUIZ = 0.15


class Audio:
    def __init__(self):
        self.musica_atual = None    # nome do arquivo tocando: evita recarregar à toa
        self.volume_musica = 1.0    # ajustado na tela de configurações
        self.volume_efeitos = 1.0
        self._em_quiz = False

    # ── volumes ──────────────────────────────────────────────────────────────
    def _volume_ativo(self):
        base = VOLUME_QUIZ if self._em_quiz else VOLUME_NORMAL
        return base * self.volume_musica

    def definir_volume_musica(self, valor):
        self.volume_musica = max(0.0, min(1.0, float(valor)))
        if mixer.get_init():
            mixer.music.set_volume(self._volume_ativo())

    def definir_volume_efeitos(self, valor):
        self.volume_efeitos = max(0.0, min(1.0, float(valor)))
        sons.definir_volume(self.volume_efeitos)

    def abaixar_para_quiz(self):
        """Abaixa a música ao entrar no quiz."""
        self._em_quiz = True
        if mixer.get_init():
            mixer.music.set_volume(self._volume_ativo())

    def restaurar_volume(self):
        """
        Devolve a música ao volume normal. Precisa ser chamada em TODA saída
        do quiz — inclusive nas saídas de exceção — senão a trilha fica presa
        no volume baixo pelo resto da partida.
        """
        self._em_quiz = False
        if mixer.get_init():
            mixer.music.set_volume(self._volume_ativo())

    # ── música ───────────────────────────────────────────────────────────────
    def tocar_musica(self, nome_arquivo, pasta_interna="songs", volume=VOLUME_NORMAL,
                     fade_ms=800):
        """Troca a música de fundo em loop, sem recarregar se já for a mesma faixa."""
        if nome_arquivo == self.musica_atual:
            return
        try:
            caminho = carregar_musica(nome_arquivo, pasta_interna)
            mixer.music.load(caminho)
            mixer.music.set_volume(max(0.0, min(1.0, volume * self.volume_musica)))
            mixer.music.play(-1, fade_ms=fade_ms)
            self.musica_atual = nome_arquivo
        except Exception as e:  # noqa: BLE001
            print(f"Erro ao tocar música '{nome_arquivo}': {e}")

    def parar_musica(self, fade_ms=400):
        """Silencia com fade; a próxima tocar_musica() volta a carregar a faixa."""
        if mixer.get_init():
            mixer.music.fadeout(fade_ms)
        self.musica_atual = None
