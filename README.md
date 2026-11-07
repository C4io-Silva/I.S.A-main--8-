# I.S.A — Intelligent Support Agent

Jogo 2D de plataforma educativo em Python + Pygame. A Areninha percorre a
floresta, a caverna e as copas das árvores coletando minérios; cada minério
abre uma pergunta (acertou: +20 de vida; errou: dano). No alto da
árvore-mãe fica a **arena**, onde o **Gorila Guardião** — o boss final —
encerra a campanha. Cada resposta vai para um banco SQLite e vira um
relatório em PDF para o professor.

Esta é a **versão unificada** das cópias ISA-v12, ISA (Cutscenes e
relatório), isa_boss (em andamento) e main_4. O que veio de cada uma, as
decisões tomadas e os resultados dos testes estão em
[`docs/INTEGRACAO.md`](docs/INTEGRACAO.md).

---

## Instalação

Requisitos: **Python 3.10+** (testado com **3.12** e 3.13) e:

```bash
pip install -r requirements.txt
```

**No Windows com Python 3.12** (vários Pythons instalados), use o lançador `py`:

```bat
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
py -3.12 testes\rodar_todos.py
```

| Pacote | Para quê |
|---|---|
| `pygame` | o jogo |
| `fpdf2` | relatório em PDF |
| `python-docx` | só o `converter_perguntas.py` (Word → CSV) |

(O `pandas` deixou de ser necessário.)

## Execução

Na pasta do projeto:

```bash
python main.py
```

No drive de rede (`Z:`), apague o cache antes se algo "não mudou":
`rmdir /s /q __pycache__ src\__pycache__ src\enemies\__pycache__ src\itens\__pycache__`

## Fluxo do jogo

`MENU → JOGAR → nome do aluno → cutscene (6 imagens, ESC pula) → floresta`
→ caverna e copas pelas passagens (tecla **E**) → **arena** (passagem no alto
da árvore-mãe) → **luta contra o Gorila** → **VITÓRIA** (relatório / jogar de
novo / menu). Morrer mostra o GAME OVER; morrendo na arena aparece também
**TENTAR DE NOVO**, que recomeça só a luta.

## Controles

| Ação | Teclado / mouse | Controle (padrão Xbox) |
|---|---|---|
| Andar | A / D ou ← / → | analógico esquerdo / direcional |
| Pular (pulo duplo) | W, ↑ ou Espaço | A |
| **Golpe de asa** | **J** ou **F** | **B** ou **Y** |
| Pisão | cair em cima do inimigo | — |
| Usar passagem | E ou Enter | X |
| Pausar | ESC | Start |
| Responder | clique, A–E ou 1–5 | direcional + A |
| Fechar a pergunta sem responder (minério volta ao mapa) | ESC | B |
| Rolar pergunta longa | roda do mouse | LB / RB |
| Tela cheia | F11 | — |

Na pergunta do **minério do boss** não dá para sair: há um tempo para
responder (15 s + tempo de leitura, no máximo 40 s), mostrado no rodapé.

## Inimigos comuns e combate

A Areninha enfrenta cobra, tucano e aranha de duas formas:

| Forma | Como | Dano |
|---|---|---|
| **Golpe de asa** | J/F (teclado) ou B/Y (controle). Rajada curta à frente; vale parada, andando e no ar | 1 |
| **Pisão** | cair em cima do inimigo; a Areninha quica e recupera o pulo duplo | 2 |

- Inimigos comuns têm **2 de vida**: dois golpes ou um pisão.
- Atingido, o inimigo **pisca**, mostra uma **barrinha de vida**, é empurrado
  e fica **atordoado** por 0,35 s, sem andar e sem machucar.
- O golpe tem **cooldown** de 0,38 s; apertar um pouco antes do fim é
  guardado (o toque não se perde). Cada golpe acerta cada inimigo uma vez só.
- Golpear a aranha que está te prendendo te solta, e ela recua pelo fio.
- Encostar de lado num inimigo (não atordoado) tira 15 de vida, com 1 s de
  invencibilidade.
- Derrotados somem com um "puf" e não voltam na mesma partida, nem trocando
  de setor. Derrotar inimigo **não dá pontos**: a pontuação continua sendo os
  acertos no quiz. A tela de vitória só mostra quantos foram derrotados.
- O **Gorila é imune** ao golpe e ao pisão. Ele continua sendo vencido
  devolvendo minérios com respostas certas (ver abaixo).
- Ajustes (vida, dano, alcance, cooldown, empurrão): bloco "Combate da
  Areninha" em `constants.py`. Detalhes em [`docs/COMBATE.md`](docs/COMBATE.md).

## O boss (arena)

O Gorila nasce no marcador `95` da arena e espera. A luta começa quando o
jogador passa da borda da área de luta; daí a saída da arena fica trancada
até o fim.

| Ataque | Aviso | Como lidar |
|---|---|---|
| **Banana** (arco) | pose de arremesso + sombra no chão onde vai cair | saia do lugar |
| **Minério** (cobre/zinco), 1 a cada 5 arremessos | o gorila aparece segurando a pedra | **deixe acertar**: abre uma pergunta. Acertou → o minério volta, o boss perde 1 de vida e fica **atordoado** 3 s. Errou ou acabou o tempo → 10 de dano |
| **Salto-pancada** (só fase 2, com metade da vida) | tremor + faixa vermelha no chão | pule as ondas de choque |
| Contato | — | encostar no gorila machuca; pular na cabeça só quica |

8 minérios devolvidos vencem a luta. Duas maçãs (uma em cada plataforma)
recuperam 15 de vida e voltam se a luta for reiniciada. Todo ataque tem aviso,
o dano nunca se repete a cada frame (1 s de invencibilidade após cada golpe),
e ao voltar de uma pergunta o jogador tem 1,2 s de proteção.
Ajustes de dificuldade: bloco `Boss` em `constants.py`.

---

## Editando os CSVs (perguntas e mapas)

Todos os CSVs são editáveis no **Excel, LibreOffice ou Bloco de Notas**. O
jogo aceita vírgula **ou** ponto e vírgula, UTF-8 com ou sem BOM e ANSI. Os
arquivos são entregues em **UTF-8 com BOM e `;`**, que o Excel em português
abre direto com duplo clique.

1. Feche o arquivo em outros programas antes de rodar o jogo (o Excel trava o
   arquivo enquanto está aberto).
2. Ao salvar no Excel, mantenha **"CSV UTF-8 (delimitado por vírgulas)"**.
   Se salvar como "CSV (separado por vírgulas)" comum (ANSI), símbolos como
   π, ₂ e ⁺ viram `?` — o jogo continua abrindo, mas o texto fica errado.
3. Rode **`python validar_dados.py`**: ele mostra codificação/separador lidos
   e aponta, com o número da linha, colunas faltando, linhas incompletas,
   gabaritos inválidos, duplicadas, IDs de mapa desconhecidos, passagens sem
   chegada, minério sem chão e trechos inalcançáveis. Sai com código 1 se
   houver erro.
4. Clique em **JOGAR** (ou REINICIAR): as perguntas e os mapas são relidos
   a cada partida — não precisa fechar o jogo.

`python validar_dados.py --padronizar` reescreve todos os CSVs no formato
padrão (com backup em `backup/`), sem mudar o conteúdo.

### Perguntas — `assets/banco de dados/perguntas.csv`

Colunas: `disciplina; dificuldade; pergunta; opcao_a; opcao_b; opcao_c;
opcao_d; opcao_e; resposta`

- `dificuldade`: **Fácil, Médio ou Difícil** (acento e maiúscula tanto faz).
  Outro valor vira Médio, com aviso.
- `resposta`: a letra (A–E) de uma alternativa **preenchida**.
- Alternativa E é opcional; são necessárias pelo menos 2.
- Fases: floresta = Fácil+Médio, caverna = Médio+Difícil, copas/arena =
  Difícil. Se a fase ficar sem pergunta, o jogo usa as outras — nunca trava e
  nunca some com o minério.
- `perguntas_revisar.csv` guarda 79 perguntas tiradas do jogo na revisão
  (dependiam de figura, estavam sem enunciado ou com gabarito impossível).
  Corrija e copie de volta para o `perguntas.csv` — veja
  [`docs/REVISAO_PERGUNTAS.md`](docs/REVISAO_PERGUNTAS.md).

### Painel ADMIN — adicionar, editar e excluir perguntas dentro do jogo

Menu → **JOGAR** → botão **ADMIN** (canto superior direito) → senha **`0000`**.

- Lista com busca, rolagem, **ADICIONAR**, **EDITAR** (ou duplo clique) e
  **EXCLUIR** (pede confirmação).
- No editor, clique na **letra** da alternativa certa; C, D e E são opcionais.
  `Tab` muda de campo e `Ctrl+S` salva.
- Cada alteração é gravada na hora em `perguntas.csv` (as dos professores
  ficam no `perguntas_professores.csv`), no formato padrão (UTF-8 com BOM e
  `;`). Antes da primeira gravação de cada arquivo vai uma cópia para
  `assets/banco de dados/backup/`.
- Se o CSV estiver aberto no Excel, o painel avisa e não grava.
- Linhas inválidas do CSV (que o jogo já ignora) não aparecem no painel e
  somem do arquivo ao salvar — elas continuam no backup.
- A senha fica em `src/admin/__init__.py` (`SENHA_ADMIN`).

### Perguntas dos professores — Word → CSV

1. Preencha `template_perguntas_ISA.docx` (marcadores `Pergunta:`,
   `Alternativa A:`…`E:`, `Correta:`, `Dificuldade:` opcional, `Categoria:`).
2. `python converter_perguntas.py` → grava
   `assets/banco de dados/perguntas_professores.csv`.

O conversor **mescla**: perguntas que já estão no CSV (inclusive corrigidas
à mão) são mantidas, e só as novas do Word são acrescentadas; o CSV anterior
vai para `assets/banco de dados/backup/`. `--substituir` recria do zero
(também com backup). O CSV dos professores pode ser editado à mão como o
banco padrão.

### Mapas — `assets/levels/setores/*.csv`

Um CSV por setor (`floresta`, `caverna`, `copas`, `arena`), uma grade de
números. A tabela completa de IDs e as receitas estão em
[`MAPA-CSV.md`](MAPA-CSV.md).

**Arquivo-fonte × gerado:** o `gerar_mundo.py` cria os mapas, mas **não
sobrescreve um CSV editado à mão**. Ele guarda a "impressão digital" do que
gravou em `assets/levels/setores/_gerado.json`; se o arquivo mudou desde
então, a versão nova vai para `assets/levels/gerados/` e o terminal avisa.
`python gerar_mundo.py --sobrescrever` troca mesmo assim, com backup em
`assets/levels/backup/`. Hoje `caverna.csv` está nesse estado (tem uma edição
manual do grupo que foi preservada).

---

## Relatórios e estatísticas

- Cada partida cria uma sessão no `estatisticas.db` (SQLite) e cada resposta
  é gravada na hora (também as do boss; tempo esgotado conta como erro).
- **MENU** na pausa/game over e **RELATÓRIO** na vitória abrem a tela de
  desempenho, onde se gera o PDF (`relatorio_sessao_N.pdf`, apagado ao voltar
  ao menu). O PDF mostra aluno, data, resultado da campanha (vitória/derrota),
  acertos, erros, percentual e cada pergunta com a alternativa escolhida e a
  correta.
- `ISA_DB=caminho.db python main.py` usa outro arquivo de banco (os testes
  usam isso para nunca tocar no banco real).

## Testes

```bash
python testes/rodar_todos.py          # todos (≈ 2 min), sem janela
python testes/rodar_todos.py --rapido # sem o benchmark
python testes/teste_boss.py           # um só
```

| Arquivo | Cobre |
|---|---|
| `teste_perguntas.py` | banco de perguntas |
| `teste_csv_edicao.py` | edição no Excel/LibreOffice/Bloco de Notas, recarga no jogo, validações |
| `teste_mapa.py` | CSVs × gerador, edição manual protegida, Excel |
| `teste_joystick.py`, `teste_quiz_controle.py` | controle |
| `teste_gamepad_falso.py` | loop real com controle: cutscene, andar, golpe B/Y, quiz pelo controle, pausa |
| `teste_teclado.py` | loop real com teclado: menu, nome, cutscene, golpe J/F, pausa |
| `teste_animacao_pulo.py` | animação andar/pulo |
| `teste_partida.py` | spawn, culling, coleta → quiz, setores, arena |
| `teste_bordas_e_saidas.py` | bordas laterais dos 4 setores (não dá para sair do mapa); saída da arena utilizável antes da luta |
| `teste_validador_fisica.py` | o validador de física real distingue saltos possíveis/impossíveis (pulo duplo × pulo simples), acha poço-armadilha e reprova mapas adulterados |
| `teste_inimigos.py` | pisão em cobra/tucano/aranha, contato lateral, boss imune |
| `teste_combate.py` | golpe de asa: vida, um acerto por golpe, cooldown/buffer, direção, atordoamento, empurrão, física inalterada, aranha, tucano, Gorila imune, setores, minérios/quiz |
| `teste_estatisticas.py` | SQLite, migração, PDF (acentos, texto longo, sessão vazia) |
| `teste_boss_projetil.py`, `teste_boss.py` | ciclo de arremessos; luta completa até a vitória, derrota e reinício |
| `teste_benchmark.py` | ms por frame |

Validação com a física real (fora do `rodar_todos`, ~2 min): `python ferramentas/validar_fisica_real.py --dificuldade` simula cada salto com o `Character.move` do jogo (pulo duplo) e confere minérios, maçãs, passagens, chegadas, spawns, colisões e pontos sem saída; `--exigir-volta` exige caminho de volta e `--pulos 1` é o controle. Inimigos com a IA real: `python ferramentas/testar_inimigos_reais.py caverna`; encontros obrigatórios: `python ferramentas/inimigos_no_caminho.py caverna`; correção candidata em memória: `python ferramentas/testar_correcoes_mapa.py caverna "nome=linha,coluna,id"`. Relatório da validação de 13/10/2026: `docs/RELATORIO_VALIDACAO_PYGAME.md`.

**Preparação para o redesign dos mapas** (documentação para quem desenha os CSVs):
`docs/ISA_MAPA_TECNICO.md` (IDs, portais, spawns, inimigos, minérios), `docs/ISA_FISICA_LEVEL_DESIGN.md` (física medida da Areninha), `docs/MAPAS_TECNICOS/` (imagens dos 4 setores), `docs/ISA_INTEGRACAO_REDESIGN.md` (como integrar + checklist) e `docs/ISA_RELATORIO_PREPARACAO_REDESIGN.md`. Regenerar depois de mudar um mapa: `python ferramentas/gerar_mapas_tecnicos.py`.

O que só um humano consegue avaliar está em `docs/INTEGRACAO.md` →
"Testes manuais".

## Estrutura

```
main.py                 ponto de entrada (só cria o Jogo e roda)
constants.py            física, IDs do mapa, setores, fases, boss
utils.py                imagens, fontes, leitura dos CSVs
validar_dados.py        validador dos CSVs (perguntas + mapas)
gerar_mundo.py          gerador dos mapas (não sobrescreve edição manual)
converter_perguntas.py  Word dos professores -> CSV (mescla)
src/
  jogo/                 o jogo em si (antes tudo morava no main.py)
    app.py              Jogo: janela, áudio, controle e o loop (eventos -> atualizar -> desenhar)
    janela.py           superfície virtual + escala para a janela real / F11
    audio.py            música e volumes
    visual.py           véus, painéis, textos com cache, barra de vida, carregamento
    menu_botoes.py      lista de botões com destaque por mouse ou controle
    intro_personagem.py a Areninha que corre e fala no menu inicial
    estados/            uma tela por arquivo (menu, login, cutscene, jogando, pausa,
                        quiz, quiz_feedback, game_over, vitoria, configuracoes,
                        creditos, estatisticas), todas com o contrato de base.py
    partida/            a partida em andamento (partida.py), câmera, banco de perguntas,
                        controle do quiz, teclas (entrada.py) e desenho (render.py)
  dados_csv.py          leitura tolerante (BOM, ';', ANSI) + validação
  setores.py            Setor: mundo, inimigos, minérios, maçãs, boss
  combate.py            golpe de asa + efeitos de combate (o único sistema de combate)
  enemies/enemy.py      Cobra, Tucano, Aranha (base Enemy: vida, golpe, pisão, atordoamento)
  enemies/boss.py       Gorila, projéteis, onda de choque
  itens/                minério e maçã
  character.py          Areninha (andar 4 quadros, pulo 4 quadros, pose de golpe)
  quiz_tela.py, cutscene.py, estatisticas.py, sons.py, joystick.py,
  ambientes.py, passagens.py, transicao.py, world.py, telas.py, ...
assets/
  banco de dados/       perguntas.csv, perguntas_professores.csv, perguntas_revisar.csv
  levels/setores/       floresta.csv, caverna.csv, copas.csv, arena.csv, _gerado.json
  images/ fonts/ songs/
testes/                 testes headless + rodar_todos.py (compat_main.py: fachada p/ a API antiga)
docs/                   INTEGRACAO.md, REVISAO_PERGUNTAS.md, HISTORICO.md
```


## Redesign de mundos — outubro/2026

Quatro mapas refeitos, portais tematicos, backgrounds novos e uma camada de decoracoes separada da colisao. Consulte `docs/LEVEL_DESIGN_PROFISSIONAL_2026.md`. Execute `py -3.12 ferramentas\auditar_level_design.py` antes dos testes habituais. **Nao execute o gerador antigo com --sobrescrever.**
