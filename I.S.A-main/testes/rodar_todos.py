"""
Roda todos os testes automatizados do I.S.A. e resume o resultado.

    python testes/rodar_todos.py            # todos
    python testes/rodar_todos.py --rapido   # pula o benchmark

Cada teste roda em processo separado (vídeo e áudio "dummy", banco de
estatísticas temporário), então nenhum deles abre janela nem grava no
estatisticas.db real. Sai com código 1 se algum falhar.
"""
import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TESTES = [
    ("teste_perguntas.py", "banco de perguntas (gabaritos, alternativas)"),
    ("teste_csv_edicao.py", "edição/salvamento/recarga dos CSVs"),
    ("teste_admin.py", "ADMIN: senha 0000 e painel de perguntas (adicionar/editar/excluir)"),
    ("teste_mapa.py", "mapas, setores, gerador e validação"),
    ("teste_level_design_profissional.py", "rotas, portais, apoio, decoracoes e novos CSVs"),
    ("teste_joystick.py", "controle: conexão, eixos, navegação"),
    ("teste_quiz_controle.py", "quiz pelo controle"),
    ("teste_animacao_pulo.py", "animação de andar/pular"),
    ("teste_gamepad_falso.py", "partida com controle simulado: andar, golpe B/Y, quiz, pausa"),
    ("teste_teclado.py", "loop real: menu, nome, cutscene, golpe J/F, pausa (teclado)"),
    ("teste_estados.py", "máquina de estados: botões, pausa, tentar de novo, F11, feedback do quiz"),
    ("teste_partida.py", "partida: spawn, coleta, quiz, setores, arena"),
    ("teste_bordas_e_saidas.py", "bordas do mapa e saida da arena antes da luta"),
    ("teste_validador_fisica.py", "validador de fisica real: pulo duplo x simples, poco, mutacoes"),
    ("teste_voadores.py", "tucano (ID 93): IA real + fisica real, casos bons e ruins"),
    ("teste_inimigos.py", "pisão derrota inimigos; lateral machuca; boss imune"),
    ("teste_combate.py", "golpe de asa: vida, cooldown, atordoamento, setores, Gorila imune"),
    ("teste_estatisticas.py", "SQLite e relatório PDF"),
    ("teste_boss_projetil.py", "ciclo de arremessos e derrota do boss"),
    ("teste_boss.py", "luta completa contra o boss"),
    ("teste_benchmark.py", "desempenho (FPS) — comparativo"),
]


def main():
    rapido = "--rapido" in sys.argv
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    resultados = []
    for arquivo, descricao in TESTES:
        if rapido and arquivo == "teste_benchmark.py":
            resultados.append((arquivo, descricao, "NAO EXECUTADO", 0.0, ""))
            continue
        inicio = time.time()
        proc = subprocess.run([sys.executable, os.path.join("testes", arquivo)],
                              cwd=RAIZ, env=env, capture_output=True, text=True,
                              timeout=1800)
        dur = time.time() - inicio
        saida = (proc.stdout + proc.stderr).strip()
        status = "APROVADO" if proc.returncode == 0 else "REPROVADO"
        resultados.append((arquivo, descricao, status, dur, saida))
        print(f"[{status:9}] {arquivo:26} {dur:6.1f}s  {descricao}")
        if proc.returncode != 0:
            print("    " + "\n    ".join(saida.splitlines()[-12:]))
    falhas = [r for r in resultados if r[2] == "REPROVADO"]
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} sem falha"
          f"{' (benchmark pulado)' if rapido else ''}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
