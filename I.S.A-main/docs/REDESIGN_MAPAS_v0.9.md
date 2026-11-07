# I.S.A. v0.9 — Polimento final dos mapas

Polimento sobre a v0.8: intervenções localizadas, sem redesenho de setor.
Sprites, tilesets, backgrounds, arte de cenário, física, colisão e o sistema
CSV **não foram alterados**. As dimensões dos mapas são as mesmas da v0.8.

## Como instalar

Copie o conteúdo de `ISA_candidata_polida/` por cima da pasta do projeto.
A v0.8 fica preservada em `versoes/v0.8/` e no commit anterior do git.

| Arquivo | Mudança na v0.9 |
|---|---|
| `assets/levels/setores/floresta.csv` | colina, face oeste da Guardiã, gruta, pedestal da Árvore-Mãe, 5 minérios |
| `assets/levels/setores/caverna.csv` | recorte do teto, 7 minérios reposicionados |
| `assets/levels/setores/copas.csv` | ramo de apoio na Vigia, 3 minérios, 1 cobra |
| `assets/levels/setores/arena.csv` | sem mudança de geometria |
| `assets/levels/decoracoes/*_decor.csv` (4) | revisão da composição, coordenada com a geometria |
| `assets/levels/estruturas_cenario.json` | suportes de mina no andaime e no patamar da caverna; ramo conector na Vigia; Árvore-Mãe 1 tile acima |
| `ferramentas/redesign_mapas/*.py` | módulos de autoria atualizados (fonte dos CSVs acima) |

Não mudaram desde a v0.8: `src/nivel_dados.py`, `MAPA-CSV.md` e
`ferramentas/auditar_ritmo_minerios.py` (nenhum limite da auditoria foi alterado).

---

## 1. Triagem da v0.8

| Setor | Região | Classificação | Motivo |
|---|---|---|---|
| Floresta | clareira, ravina, clareira afundada, lago, outeiro, baixada, toca | **Preservar** | geometria e ritmo bons |
| Floresta | colina (38–76) | Refinar | perfil simétrico, "pirâmide" de degraus iguais |
| Floresta | face oeste da Guardiã | Refinar | escada de degraus de 1 tile, regular demais |
| Floresta | **grutas** | **Corrigir** | o fundo da floresta aparece por dentro (ver §2) |
| Floresta | Árvore-Mãe | Refinar | a árvore principal ficava no mesmo plano do resto do platô |
| Caverna | galeria superior, poço de cristais, gruta inferior, saída | **Preservar** | estrutura boa |
| Caverna | tetos | Refinar | recorte serrilhado de 1 coluna e estalactites em pares regulares |
| Caverna | cristais de chão | Refinar | cristais isolados a cada poucas colunas, sem agrupamento |
| Caverna | escada de andaimes até a galeria | **Corrigir** | o andaime alto e o patamar flutuavam, sem suporte |
| Caverna | gruta inferior (minérios) | Corrigir | o trecho mais denso de perguntas do jogo (5 minérios a 2,2 s) |
| Copas | toda a composição vertical | **Preservar** | rotas alta e baixa, apoio na arte |
| Copas | galhos 127–137 (Vigia) | Corrigir | dois galhos sem nenhum apoio visual na arte |
| Copas | bordas de salto sobre o vazio | Refinar | nada indicava onde a queda é fatal |
| Copas | ninho | Corrigir | depois do ajuste de ritmo, a cobra ficou colada no minério |
| Arena | geometria, centro limpo | **Preservar** | — |
| Arena | tochas de chão | Refinar | ficavam na frente dos estandartes de pedra do cenário |

## 2. Grutas da floresta: investigação e limite

**Como o jogo desenha** (`src/jogo/partida/render.py` (`desenhar_cena`)): fundo → estruturas →
decoração → tiles → passagens → entidades. Toda célula vazia do CSV mostra o
background do setor. Não existe camada de "parede de fundo".

**Recursos existentes testados:**

- Os IDs desenhados **sem colisão** pelo `World` são `5`, `50–59` e `67`.
  Nenhum deles é um bloco opaco de terra (`5` é água; os outros são
  enfeites com 12–65% de área opaca).
- As decorações mais opacas (`122` pedra, 80%; `123` folhagem, 75%) foram
  **prototipadas como parede de fundo**, numa cópia separada do jogo e com
  captura real. Resultado: faixas repetidas de pedras ou arbustos que leem
  como objetos flutuando, pior que o problema original. **Descartado.**
- Um ID novo sem colisão apontando para um PNG de terra existente daria fundo
  opaco, mas com aparência **idêntica** à terra sólida. O jogador não
  distinguiria parede de passagem: perda de legibilidade. **Descartado.**

**O que foi feito, dentro do limite:** o teto do salão da gruta da Guardiã
desceu 1 tile. A abertura passou de 3 para 2 tiles de altura: no salão, a área
de background exposta caiu de 21 para 14 células (−33%); na gruta inteira,
de 33 para 26 (−21%). O minério de dentro continua alcançável (física real). A toca já tinha
sido reduzida na v0.8. As duas continuam pequenas, com porta estreita.

**Solução futura recomendada** (precisa de autorização: asset novo ou
mudança no renderizador): um tile "terra de fundo" sem colisão, **mais escuro**
que a terra sólida, para paredes internas. Pode ser uma variação escurecida de
`pro_terra_funda.png` feita pela equipe de arte, ou um escurecimento por
multiplicação aplicado só a esse ID em `World.render`. As duas opções exigem
uma linha em `TILE_SPRITES` e nenhuma mudança no CSV além de pintar o ID.

## 3. Melhorias por setor

### Floresta
- **Colina:** perfil assimétrico. A subida oeste é longa e em patamares
  irregulares; a descida leste, mais curta e íngreme. Deixou de ser uma pirâmide.
- **Face oeste da Guardiã:** terraços de 4, 3 e 3 colunas, com degraus de 2,
  2 e 1, no lugar da escada de degraus de 1 tile.
- **Árvore-Mãe:** pedestal de 1 tile sob as raízes (colunas 376–388). A árvore
  principal fica acima do platô e destacada, e a escalada pela copa continua
  igual.
- **Gruta:** teto rebaixado (§2).
- **5 minérios** reposicionados nos trechos em que dois ficavam a < 2,5 s.

### Caverna
- **Andaimes:** suporte de mina de 7 tiles + viga vertical sob o andaime alto e
  sob o patamar da galeria. A escada de madeira agora se apoia no chão.
- **Tetos:** recortes em blocos de 2–5 colunas, sem o serrilhado de 1 coluna.
- **Estalactites:** grupos de 1 a 3 só onde o teto desce, com espaçamento
  variável. Antes eram pares a ritmo regular.
- **Cristais de chão:** só em grupos de 2–3 junto aos veios e na galeria; os
  cristais isolados saíram. Decorações da caverna: 133 → 102 (menos, mais
  intencionais).
- **Gruta inferior:** 5 → 4 minérios espaçados (vizinho de 2,2 → 3,2 s). O 5º foi
  para a galeria de entrada, **atrás da chegada** (coluna 3): uma recompensa
  para quem olha para trás.
- Os minérios da poça saíram de cima da lâmina d'água.

### Copas
- **Vigia:** ramo conector sob os galhos 127–137, que flutuavam.
- **Leitura do risco:** uma liana longa marca as **bordas de decolagem** sobre o
  vazio. Ela só aparece onde há outra plataforma a até 4 colunas e nada sólido
  nas 12 linhas abaixo do vão. A queda continua dando game over (mecânica
  original preservada), mas o ponto de salto fica visível.
- A densidade dos pendurados genéricos foi reduzida para compensar: 130 → 150
  decorações no total. O aumento vem das lianas de borda, que têm função.
- **Ritmo:** minérios do ninho e do galho redistribuídos (vizinho mínimo
  2,0 → 2,3 s); cobra do ninho movida para longe do minério.

### Arena
- Braseiros no **topo dos obeliscos** (antes no chão, na frente dos estandartes
  de pedra) e tochas nas pontas das plataformas altas.
- O centro da luta (colunas 16–32) segue sem decoração; geometria intocada.

## 4. Ritmo dos minérios

**Auditoria verificada:** `auditar_ritmo_minerios.py` usa o grafo de posições
em pé do validador de física real. Cada movimento é simulado com
`Character.move`/`jump` do jogo (velocidade, gravidade e pulo duplo reais), o
custo é contado em quadros a 60 FPS sem a penalidade de rota, e a caminhada
nas pontas usa `PLAYER_SPEED`.

**Calibração:** spawn (coluna 8) → minério da coluna 15, chão plano:
7 × 48 px ÷ 3 px/quadro = 112 quadros = 1,87 s. A auditoria mede 1,8 s.

**Limite:** os movimentos são uma lista finita e as posições são quantizadas em
12 px. O tempo medido pode ficar um pouco acima do ótimo real.

72 minérios mantidos (32 + 25 + 15).

| | v0.8 | v0.9 |
|---|---|---|
| **Erros** (vizinho < 2,0 s, obrigatório) | 0 | **0** |
| Vizinho mais próximo < 2,5 s | 23 minérios | **15** |
| Vizinho entre 2,5 e 3,5 s | 35 | 43 |
| Vizinho ≥ 3,5 s | 14 | 14 |
| Mínimo por setor (floresta / caverna / copas) | 2,2 / 2,0 / 2,0 s | **2,5 / 2,2 / 2,3 s** |
| Mediana do vizinho (floresta / caverna / copas) | 2,8 / 2,5 / 2,5 s | **2,9 / 2,8 / 2,4 s** |
| Avisos de qualidade: vizinho < 3,5 s | 58 | 58 |
| Avisos de qualidade: > 4 minérios em 15 s | 25 | 27 |
| Avisos de leitura (decoração colada, cobra colada) | 0 | 0 |

**Leitura honesta:**

- A v0.9 tirou os minérios das **faixas mais apertadas**: 23 → 15 abaixo de
  2,5 s, e o mínimo subiu em todos os setores.
- Ela **não** reduziu o total de avisos de qualidade. Com 72 minérios na
  geometria atual, cerca de 58 vizinhos abaixo de 3,5 s é o teto prático sem
  aumentar mapas ou criar corredores vazios, e o brief proíbe os dois.
- A mediana do intervalo na caverna caiu de 4,3 para 3,9 s, porque a ordem de
  percurso mudou com o minério atrás da chegada. Esse minério fica a 1,0 s da
  chegada, mas é opcional: está no sentido contrário ao da progressão.

## 5. Validação executada (arquivos finais)

| Verificação | Resultado |
|---|---|
| `python testes/rodar_todos.py` | **19/19 aprovados** |
| `python validar_dados.py` | 0 erros, 0 avisos |
| `python ferramentas/validar_fisica_real.py` | **0 erros, 0 avisos**. Todas as superfícies pisadas (517 + 364 + 251 + 53); todos os minérios, maçãs e portais alcançáveis; nenhuma posição sem saída |
| `teste_level_design_profissional` | aprovado, 72 minérios; marcadores com apoio; decoração fora de colisão |
| `python ferramentas/auditar_ritmo_minerios.py` | 0 erros; avisos na tabela acima |
| Instalação limpa | cópia instalada a partir desta pasta é idêntica à validada; `build.py` regenera os mesmos bytes |

**Problemas que os validadores pegaram nesta etapa, todos corrigidos no mapa:**

- um minério reposicionado criou um par a 1,8 s nas copas (duas tentativas
  até achar a distribuição certa);
- a cobra do ninho ficou a 1 coluna de um minério;
- a poça e um cristal ficaram encostados em minérios da gruta inferior.

**Visual:**

- `imagens/mapas_v09/`: as três visões por setor (física, decorativa e
  combinada com o background original).
- `imagens/comparacao_regioes/`: v0.8 × v0.9 nas **mesmas regiões e
  enquadramentos**.
- `imagens/jogo_v08_v09/`: 22 capturas do **loop real do Pygame** lado a lado,
  com os mesmos pontos de câmera.

Uma tentativa foi rejeitada a partir das imagens: lianas em todas as pontas das
copas viraram uma franja repetitiva. Ficaram só nos pontos de salto reais.

`auditoria/` traz os relatórios de ritmo (v0.8 e v0.9), a física real e a
saída dos testes.

## 6. Problemas não resolvidos

1. **Fundo das grutas da floresta** (§2): mitigado, não resolvido. Depende de
   asset ou mudança de renderizador autorizados.
2. **Ritmo em avisos de qualidade:** 58 vizinhos abaixo de 3,5 s. Melhorar
   além disso exige baixar o mínimo de minérios ou aumentar a geometria;
   decisão da equipe.
3. **Sem partida manual.** Este ambiente é um contêiner sem tela nem
   teclado. O jogo foi executado de verdade (testes de loop real com teclado e
   controle simulados, e 22 capturas do Pygame), mas **ninguém jogou uma
   partida completa**. Roteiro em `PLAYTEST.md`.
4. A seção "Encontros" do `MAPA-CSV.md` e o README das decorações (IDs
   100–117) continuam desatualizados desde antes da v0.7.

## Ferramentas

```
python ferramentas/redesign_mapas/build.py . floresta,caverna,copas,arena                  # só confere
python ferramentas/redesign_mapas/build.py . floresta,caverna,copas,arena --sobrescrever   # grava
python ferramentas/auditar_ritmo_minerios.py --processos 4 --lista                         # ritmo
python ferramentas/redesign_mapas/renderizar_camadas.py . all renders 0.5 --grid           # 3 visões
python ferramentas/redesign_mapas/capturas_no_jogo.py . capturas                           # loop real
```
