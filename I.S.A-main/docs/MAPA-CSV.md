# Editando o mapa pelo CSV

O mapa é dividido em **setores**, um CSV por setor, em `assets/levels/setores/`:

| Setor | Arquivo | Tamanho | Ambiente |
|-------|---------|---------|----------|
| floresta | `floresta.csv` | 44 × 404 | floresta (setor inicial, tem o spawn `90`) |
| caverna | `caverna.csv` | 44 × 251 | caverna |
| copas | `copas.csv` | 44 × 171 | copas |
| arena | `arena.csv` | 44 × 41 | copas — arena do boss (Gorila) |

**Formato:** separador `;` ou `,`, UTF-8 (com ou sem BOM) ou ANSI — do jeito
que Excel, LibreOffice ou Bloco de Notas salvarem. Os arquivos são entregues
com `;` e BOM (abrem direto no Excel em português). Depois de editar, rode
`python validar_dados.py`.

Cada CSV é uma grade de números com **coordenadas próprias** (coluna 0 = começo
daquele setor). Cada setor pode ter largura e altura diferentes.
**A posição de tudo no mundo é decidida nos CSVs, não no Python.**

O jogador só troca de setor por uma **passagem** (com fade). Todos os setores
são carregados no início da partida, então o estado de cada um (minério
coletado, inimigo derrotado) continua valendo quando o jogador volta.

Divisão de responsabilidade:

| | decide |
|---|---|
| **CSV** | onde está e qual é o elemento |
| **`constants.py`** | o que cada ID significa e para onde cada passagem leva |
| **`src/jogo/partida/`** | como o elemento se comporta |

---

## Tabela de IDs

### Terreno (tem colisão, é desenhado)

| ID | O que é |
|----|---------|
| `-1` | vazio |
| `0` | bloco genérico / rocha da caverna |
| `1` | grama |
| `2` | terra |
| `10`, `11` | variações de grama |
| `20` | variação de terra |

### Passagens (sem colisão, apagadas da grade — desenhadas como cenário)

| ID | Tipo | Leva para | Chega no marcador |
|----|------|-----------|-------------------|
| `30` | `CAVE_ENTRY` | caverna | `40` |
| `31` | `CANOPY_ENTRY` | copas | `41` |
| `32` | `CAVE_EXIT` | floresta | `42` |
| `33` | `CANOPY_EXIT` | floresta | `43` |
| `34` | `ARENA_ENTRY` | arena | `44` |
| `35` | `ARENA_EXIT` | copas | `45` |

A passagem diz **para qual setor** vai (`constants.PASSAGENS_CSV`, campo
`setor`); a chegada com o ID indicado precisa existir no CSV desse setor.

### Chegadas (invisíveis — apagadas da grade ao carregar)

| ID | Onde o player reaparece |
|----|-------------------------|
| `40` | ao entrar na caverna |
| `41` | ao entrar nas copas |
| `42` | ao sair da caverna, de volta na floresta |
| `43` | ao sair das copas, de volta na floresta |
| `44` | ao entrar na arena |
| `45` | ao sair da arena, de volta no alto das copas |

### Entidades (invisíveis — apagadas da grade ao carregar)

| ID | O que nasce ali |
|----|-----------------|
| `90` | spawn do player |
| `91` | minério (é ele que dispara a pergunta) |
| `92` | cobra (anda no chão) |
| `93` | tucano (voa) |
| `94` | aranha (pendura no teto) |
| `95` | **boss (Gorila)** — nasce nesta célula, no centro da arena (logo acima do chão) |
| `96` | **maçã** (item de cura, +15 de vida; só é gasta se o jogador estiver ferido) |

Mapa conceitual → IDs deste projeto:

| Conceito | ID(s) |
|----------|-------|
| área livre | `-1` |
| obstáculo / parede / chão | `0`, `1`, `2`, `10`, `11`, `20` (o que está em `constants.SOLID_TILES`) |
| player | `90` |
| inimigo | `92`, `93`, `94` |
| minério | `91` |
| item de cura | `96` |
| portal (passagem) | `30`–`33`, com chegada em `40`–`43` |
| boss | `95` + limites da luta em `src/nivel_dados.AREA_BOSS` |

Mantivemos números em vez de letras (`P`, `#`, `E`...) porque o formato
numérico já é o que o gerador, o validador e o jogo usam, e um ID por
variação de terreno (grama, terra, rocha) cabe melhor em números.

---

## A regra única

> **A célula do marcador é a célula que a entidade ocupa.**

Um `92` na linha 25 é uma cobra na linha 25, apoiada no bloco da linha 26.
Um `94` na linha 12 é uma aranha pendurada no bloco da linha 11.

Não existe "linha da superfície + altura flutuante". Se você quer o tucano
mais alto, sobe o `93` de linha. É só isso.

---

## Receitas

**Mover a entrada da caverna:** ache o `30`, troque por `-1`, escreva `30` na
célula nova. Só isso — o destino continua valendo, porque o destino está
amarrado ao **ID**, não à posição. A estrutura visual (moldura, vão,
vegetação, partículas) é desenhada em volta do marcador, então ela vai junto.

**Mudar onde o player cai na caverna:** mova o `40`.

**Adicionar um minério:** escreva `91` numa célula vazia que tenha bloco
sólido logo abaixo. Mais minério = mais pergunta.

**Tirar um inimigo:** apague o marcador (troque por `-1`).

**Criar um setor novo:** crie o CSV em `assets/levels/setores/`, registre em
`constants.SETORES` (arquivo + ambiente) e ligue-o com um par de passagem +
chegada em `constants.PASSAGENS_CSV`, desenhando os IDs nos dois CSVs.

**Criar uma passagem nova:** escreva o ID da entrada onde quiser e o ID da
chegada correspondente no destino. Se quiser um par novo (ex.: uma segunda
entrada de caverna que cai em outro ponto), aí sim mexe no Python — basta
uma linha em `constants.PASSAGENS_CSV`.

---

## Cuidados

- **Marcador precisa de chão.** Um `91` ou `92` no ar cai até achar bloco.
  Um marcador dentro de bloco sólido é recusado pelo gerador com aviso.
- **Uma chegada por ID.** Se houver dois `40`, vale o último lido.
- **Entrada sem chegada** imprime aviso no terminal e não teleporta.
- **CSV malformado não abre o jogo:** célula não numérica ou linhas de
  larguras diferentes geram `ErroMapa` dizendo linha e coluna. IDs
  desconhecidos só geram aviso (viram o bloco padrão).
- **Confira depois de editar:** `python validar_dados.py` (aponta linha/coluna
  de cada problema: ID desconhecido, minério sem chão, passagem sem chegada,
  trecho inalcançável ou poço sem volta). `python testes/teste_mapa.py` aceita
  CSV editado à mão, desde que continue jogável.
- **`rmdir /s /q __pycache__`** antes de rodar, se estiver no drive de rede.

---

## E o `gerar_mundo.py`?

Continua sendo o jeito de gerar o mapa do zero: ele monta o terreno, valida
(BFS de acessibilidade, degraus, vãos, espaço de combate) e **carimba os
marcadores no CSV** antes de gravar. Ele nunca grava um mapa que não passou na
validação.

O gerador constrói o mundo numa grade só e **grava fatiado**, um CSV por
setor. Depois de gerados, os CSVs são seus para editar à mão — e o gerador
**não sobrescreve mais as suas edições**:

| Situação do CSV em disco | O que `python gerar_mundo.py` faz |
|---|---|
| não existe | grava |
| igual ao que o gerador gravou da última vez (`_gerado.json`) | atualiza normalmente |
| editado à mão desde então | **não toca**; grava a versão nova em `assets/levels/gerados/` e avisa |
| editado, com `--sobrescrever` | troca, guardando cópia em `assets/levels/backup/` |

A comparação é pela grade (os números), não pelo texto: abrir e salvar no
Excel sem mudar nada não conta como edição. O gerador também recusa gravar se dois marcadores caírem na mesma célula ou se uma
passagem apontar para uma chegada que não existe no setor de destino.

`src/nivel_dados.py` continua sendo gerado, mas só guarda o spawn inicial,
o ponto de entrada de cada setor (para a validação) e os limites da arena.
Inimigos, minérios, passagens e chegadas vêm **só** dos marcadores dos CSVs.


---

## Aparência das passagens

O marcador decide **onde**. A aparência vem de `ESTILOS`, em
`src/passagens.py` — uma entrada por tipo, com:

| campo | o que faz |
|-------|-----------|
| `sprite` | nome do PNG em `assets/images/passagens/`. `None` = desenho procedural |
| `largura` / `altura` | tamanho da estrutura, em tiles (o marcador fica no meio da base) |
| `direcao` | `"baixo"` ou `"cima"` — inverte o degradê do vão e o sentido das partículas |
| `interacao` | `"tecla"` (aparece aviso, precisa apertar) ou `"toque"` (entra ao encostar) |
| `rotulo` | o texto do aviso na tela |
| `cores` | paleta do desenho procedural |

**Para trocar por arte de verdade:** põe o PNG em
`assets/images/passagens/` e escreve o nome em `sprite`. O módulo passa a usar
a imagem e ignora o desenho procedural. Se o arquivo faltar ou falhar, ele
avisa no terminal e volta para o procedural — nunca deixa a passagem invisível.

**Entrar numa passagem:** `E` ou `Enter` no teclado, `X` no controle. Quem
quiser o comportamento antigo (teleporta ao encostar) troca `interacao` para
`"toque"` no estilo daquele tipo.

A estrutura nunca é pintada por cima de bloco sólido: cada célula é checada
contra a grade antes de ser desenhada. Sem isso você veria uma abertura e
bateria numa parede.


---

## Regiões e encontros

O mapa tem quatro setores; os três primeiros têm início, meio e fim:

| Região | Colunas | Estrutura |
|--------|---------|-----------|
| Floresta | 404 | clareira → colina → ravina com a boca da caverna → clareira afundada → colina da Árvore Guardiã (com gruta) → lago e outeiro → baixada com toca → escalada da Árvore-Mãe |
| Caverna | 251 | entrada → corredor descendente → câmara principal → passagem espremida → galeria dos veios → arena → corredor fundo → câmara profunda |
| Copas | 171 | pórtico → Árvore Ancestral (deck, copa, raízes) → ninho → galhos da árvore de fundo → Árvore Espiral (deck, cume, raízes) → Árvore Vigia → deck final com o portal da arena |
| Arena | 41 | clareira com teto de galhos, chão contínuo e 2 plataformas baixas com maçãs — luta contra o Gorila |

### Arena do boss

Setor próprio (`arena.csv`). No alto da copa da árvore-mãe fica a passagem
`34`; ela leva à arena, uma clareira de 40 colunas com o chão na linha 24,
teto de galhos e duas plataformas baixas (2 tiles acima do chão, alcançáveis
com o pulo duplo), cada uma com uma maçã (`96`). A saída (`35`) fica logo na
entrada, antes da área de luta, e leva de volta à copa.

```
floresta (spawn) → ravina → [caverna] → volta → floresta alta
   → grande árvore → [copas] → árvore-mãe → copa → [ARENA DO BOSS]
```

O Gorila nasce no marcador `95`. A luta começa quando o jogador cruza a borda
esquerda de `AREA_BOSS` (`src/nivel_dados.py`); a partir daí a saída fica
trancada até a vitória. `gerar_mundo.validar_area_boss()` recusa gravar o mapa
se a arena ficar estreita, sem chão, com bloco no espaço de luta (fora as
plataformas declaradas em `PLATAFORMAS_ARENA`) ou em cima do boss, com
inimigo comum ou minério dentro, ou inalcançável. Com `constants.DEBUG = True`
o retângulo da luta aparece em vermelho.

Duas áreas secretas: a **sala escondida** (dentro da rocha do teto da câmara
principal) e o **nicho da arena** (pela chaminé acima da plataforma central).
Nas copas, o **ninho** acima da ponte.

### Encontros

Inimigo não é mais item de lista solta. Em `gerar_mundo.py` eles são
declarados por **encontro** — quem está na situação, quanto espaço tem, o que
se ganha:

```python
encontro("arena", "caverna",
         mobs=[(CAV_C0 + 190, 30, "Enemy"),
               (CAV_C0 + 202, 30, "Enemy"),
               (CAV_C0 + 195, 18, "Aranha")],
         minerios=[(CAV_C0 + 198, 24)])
```

Isso permite validar o que a geometria sozinha não pega:

| Regra | O que evita |
|-------|-------------|
| `DIST_MIN_MOBS = 4` | dois inimigos colados viram parede de dano sem espaço para revidar |
| `DIST_MIN_CHEGADA = 10` | chegar numa região e tomar dano antes do primeiro frame de controle |

As duas já pegaram problema real: uma aranha a 3 colunas de uma cobra na arena,
e um tucano em cima de quem chegava nas copas.

O tucano aceita um quarto valor na tupla — a altura em tiles que ele flutua
acima do apoio. Sem ela, ele nasceria andando no chão como uma cobra.

## Sprites adicionais do terreno (redesenho)

Veja `docs/NOVO_TERRENO.md` para os IDs 12–15, 21–29, 36–37 e decorações 50–59. O terreno original foi redesenhado visualmente mantendo colisões e posições dos marcadores.


## Camada de decoracoes da versao profissional

Além dos CSVs tradicionais de colisao e marcadores, existem grades `assets/levels/decoracoes/<setor>_decor.csv`, com exatamente as mesmas dimensoes. IDs 100–117 indicam apenas arte visual, sem fisica; -1 significa vazio. O mapa de colisao continua sendo a unica fonte de terrenos solidos e interacoes. Consulte `src/decoracoes_offline.py`.


## Camada de decoracoes da versao profissional

Além dos CSVs tradicionais de colisao e marcadores, existem grades `assets/levels/decoracoes/<setor>_decor.csv`, com exatamente as mesmas dimensoes. IDs 100–117 indicam apenas arte visual, sem fisica; -1 significa vazio. O mapa de colisao continua sendo a unica fonte de terrenos solidos e interacoes. Consulte `src/decoracoes_offline.py`.


## Camada de decoracoes da versao profissional

Além dos CSVs tradicionais de colisao e marcadores, existem grades `assets/levels/decoracoes/<setor>_decor.csv`, com exatamente as mesmas dimensoes. IDs 100–117 indicam apenas arte visual, sem fisica; -1 significa vazio. O mapa de colisao continua sendo a unica fonte de terrenos solidos e interacoes. Consulte `src/decoracoes_offline.py`.
