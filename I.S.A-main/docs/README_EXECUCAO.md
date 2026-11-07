# I.S.A. — Candidata POLIDA (integrada + fundos oficiais + polimento v0.5)

**Esta pasta é uma CANDIDATA experimental. Não é a versão estável e não substitui a estável.**
Origem: branch `isa-polimento-v05` (o commit exato está em `docs/polimento_v05/RELATORIO_POLIMENTO_FINAL.md` e no `COMMIT.txt` da entrega).

## Como montar a pasta a partir dos ZIPs

A entrega vem em **5 partes**, porque cada arquivo tem limite de 30 MB. Extraia **todas na mesma pasta**; todas criam `ISA_candidata_polida/`:

| Parte | Conteúdo |
|---|---|
| `ISA_CANDIDATA_POLIDA_FINAL_parte1_codigo_mapas_imagens.zip` | código, mapas, decorações, estruturas, testes, ferramentas e imagens (menos fundos e cutscenes) |
| `ISA_CANDIDATA_POLIDA_FINAL_parte2_imagens_fundos_cutscenes.zip` | backgrounds (inclusive os fundos oficiais) e cutscenes |
| `ISA_CANDIDATA_POLIDA_FINAL_parte3_docs.zip` a `parte5_docs.zip` | documentação, relatórios e evidências das fases anteriores e desta |

As partes 1 e 2 bastam para jogar. As capturas reais desta fase estão em `ISA_CAPTURAS_PYGAME_V05.zip`.
**Não extraia por cima da pasta da versão estável.**

## Como jogar

Requisitos: Python 3.10+ (testado em **3.12**) e as bibliotecas do `requirements.txt`.

```bash
pip install -r requirements.txt
python main.py
```

No Windows com vários Pythons:

```bat
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

Controles:

| Tecla | Ação |
|---|---|
| A / D | andar |
| Espaço | pular (aperte de novo no ar para o pulo duplo) |
| J | golpe de asa |
| E | usar passagem |
| ESC | pausa |

Também funciona com controle (gamepad).

A campanha começa na Floresta:

1. Floresta → **Caverna** (pela entrada de pedra) → volta à Floresta.
2. Floresta → **Copas** (pelo cipó).
3. Copas → **Arena** (portão no alto das copas).
4. Na Arena, o **Gorila Guardião**: desvie das bananas, deixe o minério acertar, responda certo e pule as ondas de choque.
5. Depois da vitória, **RELATÓRIO** gera o PDF para o professor.

## Como testar

```bash
python validar_dados.py                                        # dados: 0 erros
python ferramentas/validar_fisica_real.py --dificuldade --exigir-volta   # física real dos 4 setores
python ferramentas/auditar_level_design.py                     # auditoria offline (83 minérios)
python testes/rodar_todos.py                                   # suíte (19 testes)
```

Ferramentas de análise (não alteram nada):

| Ferramenta | Para quê |
|---|---|
| `ferramentas/testar_inimigos_reais.py <setor>` | IA real de cada inimigo: ataque, derrota e esquiva |
| `ferramentas/inimigos_no_caminho.py <setor>` | quais encontros são obrigatórios |
| `ferramentas/validar_voadores.py` | regras do tucano (ID 93) |
| `ferramentas/auditar_estruturas.py <setor>` | estruturas de cenário: apoio no chão, parte visível, invasão do caminho |
| `ferramentas/auditar_decoracoes.py [setor]` | enfeites da camada de decoração soltos no ar ou sobre marcadores |
| `ferramentas/prototipos/medir_trecho.py` | dano num trecho curto com IA real (vários tempos de entrada) |

## O que mudou em relação à estável

Resumo; os detalhes estão em `docs/integracao_final/LOG_INTEGRACAO.md`.

- **Caverna v0.4e:** geometria aprovada (corredores seguros sob as aranhas 31 e 229, aranha 81 sobre a viga, desvio D1b), polimento artístico (12 PNGs, 28 estruturas) e auditor/teste específicos para o tucano.
- **Floresta v0.6:** redesign completo com túneis, Árvore Guardiã e Árvore-Mãe; IDs novos 64–67 e 118–123. **Correções:** o ID 67 (pilar de raiz) passou a ser só visual, porque, sólido, prendia o jogador no início; uma cobra foi movida 1 coluna, porque nascia dentro de um bloco; uma pedra decorativa foi movida.
- **Copas v0.1:** 6 galhos novos, 66 decorações e 5 estruturas.
- **Arena v0.1:** só arte (4 estruturas). Correções: o brilho de dano do Gorila passou a ter a forma do sprite (antes era uma caixa), e as colunas de santuário foram assentadas no chão.

- **Fundos oficiais (fase final, etapa 1):** Floresta `fundo_cenario01` (0,25) + `frente_cenario01` (0,50); Copas `floresta_cenario_01` (0,25) + `nuvens_cenario_01` (0,55).
- **Polimento v0.5 (fase final):** raízes ancoradas e árvores reposicionadas na Floresta; apoios de madeira e conectores nas Copas; pilares de mina e arco assentado na Caverna; arco da Arena afastado do Gorila. Na auditoria, 4 árvores foram assentadas 1 tile e enfeites soltos no ar foram levados ao chão ou ao teto. Só JSON de estruturas e CSV de decoração; terreno, física e marcadores idênticos. Detalhes em `docs/polimento_v05/RELATORIO_POLIMENTO_FINAL.md`.

Não mudaram (fora os fundos acima): parallax, física, combate, IA dos inimigos, Gorila (vida, ataques e tempos), quizzes, SQLite, PDF, menu, cutscenes e portais. A campanha continua com 83 minérios.

## Não incluído (protótipos em branches separadas, aguardando aprovação)

- `prototipo-aviso-aranha`: aviso "!" antes da descida da aranha.
- `prototipo-empurrao-parede`: correção do empurrão que sobe parede.
