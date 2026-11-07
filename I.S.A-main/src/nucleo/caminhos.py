"""Caminhos do projeto: funcionam rodando do codigo-fonte e dentro do PyInstaller."""
import sys
from pathlib import Path


def _raiz() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller: os assets ficam em dist/ISA/_internal/assets
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for pasta in Path(__file__).resolve().parents:
        if (pasta / "assets").is_dir() and (pasta / "main.py").exists():
            return pasta
    raise RuntimeError("Raiz do projeto nao encontrada (esperava assets/ e main.py).")


RAIZ = _raiz()
ASSETS = RAIZ / "assets"
