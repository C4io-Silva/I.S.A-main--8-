# I.S.A. v0.9 — Roteiro de playtest manual

Os mapas foram validados por simulação com a física real, por testes do loop
real e por capturas do Pygame. **Nenhuma partida manual completa foi jogada.**
Este roteiro cobre o que a simulação não mede: sensação, clareza e cansaço.

**Preparação.** Rode `python main.py`. Para conferir posições, ligue
`constants.DEBUG = True`: o retângulo da luta aparece em vermelho e os
avisos saem no terminal. Anote cada problema com **setor, coluna aproximada,
o que aconteceu e o que você esperava**.

Prioridade: **A** = jogar sempre; **B** = se houver tempo.

## A1. Ritmo das perguntas (todos os setores)

- [ ] Jogue a floresta inteira sem pressa e cronometre o tempo entre o fim de
      uma pergunta e o toque no minério seguinte. Marque os trechos em que
      pareceu "uma pergunta atrás da outra". A auditoria aponta a sequência
      colina → ravina (colunas 46–94) e a região do outeiro (240–275) como as
      mais densas.
- [ ] Caverna: a gruta inferior (colunas 157–202) tem 4 minérios; teve muito
      ou pouco?
- [ ] Copas: trecho ninho → galho baixo → cume da Espiral (colunas 55–90).
- [ ] Algum minério ficou difícil de **ver** (escondido por decoração, fundo
      parecido, fora da câmera)?
- [ ] ESC numa pergunta devolve o minério: ele reabre a pergunta rápido demais
      ao andar de novo?

## A2. Grutas e tocas da floresta

- [ ] Gruta da Guardiã (coluna ~190, entrada pelo paredão leste, coluna ~200):
      a entrada é percebida? A placa ajuda?
- [ ] Dentro da gruta: o fundo da floresta aparecendo **quebra** a sensação de
      estar embaixo da terra? (limitação conhecida, ver README §2)
- [ ] Toca da baixada (coluna ~306): a descida é percebida? Dá para sair sem
      frustração?

## A3. Quedas nas copas

- [ ] Percorra a rota principal e as rotas alta e baixa (Ancestral, colunas
      27–45; raízes, 30–43; Espiral, 84–98; Vigia, 99–144).
- [ ] Toda queda fatal pareceu **consequência de um erro seu**? Ou houve
      queda "surpresa"?
- [ ] As lianas nas bordas de decolagem ajudam a ler onde o salto começa?
- [ ] Algum salto pareceu exigir precisão demais para o pulo duplo?

## A4. Combate na arena

- [ ] O Gorila e os projéteis ficam sempre visíveis contra o fundo?
- [ ] Os obeliscos e braseiros (colunas 14 e 34) atrapalham a leitura dos
      limites do chão ou das plataformas?
- [ ] A saída da arena antes de cruzar a borda da luta continua acessível?
- [ ] Game over na arena → tentar de novo: tudo volta ao estado inicial?

## A5. Portais e retorno

- [ ] Floresta → caverna → floresta: você reaparece num lugar que faz sentido?
- [ ] Floresta → copas → arena → copas → floresta.
- [ ] Depois de voltar, os minérios já coletados continuam sumidos?

## B1. Percursos alternativos

- [ ] Floresta: atalho do tronco caído sobre a clareira afundada (colunas
      102–118); rota alta da Guardiã (196–204); escalada da Árvore-Mãe até o
      cume (378–400).
- [ ] Caverna: galeria de mina superior (96–121) **versus** passagem espremida;
      escada de andaimes; poço dos cristais (133–138); minério atrás da
      chegada (coluna 3).
- [ ] Os desvios valem a pena, ou parecem caminho vazio?

## B2. Retorno por caminhos anteriores

- [ ] Volte da metade de cada setor até a entrada. Há algum ponto em que só
      se passa morrendo? (o validador diz que não; confirme na mão)
- [ ] Algum trecho fica tedioso na volta?

## B3. Leitura visual geral

- [ ] Plataformas finas (galhos, andaimes) se distinguem do fundo?
- [ ] Alguma decoração parece sólida e engana o jogador?
- [ ] Algum inimigo nasce em lugar injusto (logo na chegada, em cima de um
      minério)?

## Registro sugerido

| Setor | Coluna | Prioridade | O que aconteceu | Esperado | Gravidade (1–3) |
|---|---|---|---|---|---|
| | | | | | |
