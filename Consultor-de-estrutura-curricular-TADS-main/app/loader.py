"""Carrega os cursos de data/cursos/*.json nos três bancos.

Uso:  python -m app.loader                      (todos os arquivos da pasta)
      python -m app.loader data/cursos/x.json   (arquivos específicos)
"""
import glob
import json
import os
import sys

from . import config
from .backends import BACKENDS
from .backends.base import validar


def main(argv):
    arquivos = argv or sorted(glob.glob(os.path.join(config.CURSOS_DIR, "*.json")))
    if not arquivos:
        sys.exit("nenhum arquivo de curso encontrado")
    for caminho in arquivos:
        with open(caminho, encoding="utf-8") as f:
            curso = json.load(f)
        validar(curso)
        for nome, backend in BACKENDS.items():
            backend.carregar(curso)
            print(f"{curso['codigo']}: {len(curso['componentes'])} componentes -> {nome}")


if __name__ == "__main__":
    main(sys.argv[1:])
