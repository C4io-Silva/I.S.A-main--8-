"""Lista de botões com destaque pelo mouse OU pelo controle (d-pad/analógico)."""

from src.sistemas.joystick import acionar, centro_do_botao, navegar


class MenuBotoes:
    """
    Os botões só conhecem "hover do mouse". Para o controle destacar o item
    selecionado, o menu finge uma posição de mouse sobre ele. Quem manda no
    destaque é `jogo.foco_no_controle`: liga ao usar o controle, desliga ao
    mexer o mouse.
    """

    def __init__(self, jogo, botoes):
        self.jogo = jogo
        self.botoes = botoes
        self.selecao = 0

    def resetar(self):
        self.selecao = 0

    def clicar(self, evento):
        for botao in self.botoes:
            botao.verificar_click(evento)

    def atualizar_controle(self, gamepad):
        """Navega com o d-pad/analógico e aciona o botão com o confirmar."""
        passo = gamepad.nav_y or gamepad.nav_x
        if passo:
            self.selecao = navegar(self.botoes, self.selecao, passo)
        if gamepad.confirmou_agora:
            acionar(self.botoes, self.selecao)

    def posicao_de_foco(self, mouse_pos):
        """Onde desenhar o destaque: sobre o item selecionado ou sob o mouse."""
        if self.jogo.foco_no_controle and 0 <= self.selecao < len(self.botoes):
            return centro_do_botao(self.botoes[self.selecao])
        return mouse_pos

    def desenhar(self, tela, mouse_pos):
        foco = self.posicao_de_foco(mouse_pos)
        for botao in self.botoes:
            botao.desenhar(tela, foco)
