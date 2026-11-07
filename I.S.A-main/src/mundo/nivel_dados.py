"""Coordenadas auxiliares da campanha profissional.

Mapas e marcadores sao fonte primaria nos CSVs. Nao execute gerar_mundo.py
para substituir mapas editados: use backup e --sobrescrever conscientemente.
"""

PLAYER_SPAWN = (8, 30)  # superfície do novo começo da campanha

SETORES_GERADOS = {
    'floresta': {'colunas': 404, 'linhas': 44, 'entrada_col': 8, 'entrada_row': 30},
    'caverna': {'colunas': 251, 'linhas': 44, 'entrada_col': 7, 'entrada_row': 30},
    'copas': {'colunas': 171, 'linhas': 44, 'entrada_col': 5, 'entrada_row': 34},
    'arena': {'colunas': 41, 'linhas': 44, 'entrada_col': 5, 'entrada_row': 24},
}

AREA_BOSS = {'c0': 10, 'c1': 39, 'linha_topo': 12, 'linha_chao': 24, 'setor': 'arena', 'marcador': (24, 23)}
