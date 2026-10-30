import os
import threading
import time
from statistics import mean

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .backends import BACKENDS
from .backends.base import OPS, limpar, normalizar, ordenar

app = FastAPI(title="Consulta Estrutura Curricular")
STATIC = os.path.join(os.path.dirname(__file__), "static")
lock = threading.Lock()  # uma consulta por vez, para o tempo medido não sofrer interferência


@app.get("/api/meta")
def meta():
    return {"bancos": list(BACKENDS), "operacoes": OPS}


@app.get("/api/cursos")
def cursos(db: str = "postgres"):
    return _backend(db).cursos()


@app.get("/api/consulta")
def consulta(db: str, curso: str, op: str = "buscar", nome: str = "", codigo: str = "",
             periodo: int | None = None, tipo: str = "", requer: str = "", execucoes: int = 10):
    backend = _backend(db)
    if op not in OPS:
        raise HTTPException(400, f"operação inválida: {op}")
    filtros = {"nome": normalizar(nome), "codigo": codigo.strip().upper(), "periodo": periodo,
               "tipo": tipo.strip(), "requer": requer.strip().upper()}
    if op != "buscar" and not filtros["codigo"]:
        raise HTTPException(400, "informe o código do componente")
    execucoes = max(1, min(execucoes, 100))

    with lock:
        try:
            rodar, texto = backend.executar(op, curso, filtros)
            rodar()  # aquecimento: não entra na média
            tempos, linhas = [], []
            for _ in range(execucoes):
                inicio = time.perf_counter()
                linhas = rodar()
                tempos.append((time.perf_counter() - inicio) * 1000)
        except Exception as e:  # banco fora do ar, etc.
            raise HTTPException(503, f"{db} indisponível: {e}")

    resultados = ordenar([limpar(l) for l in linhas])
    return {
        "db": db, "op": op, "curso": curso, "total": len(resultados),
        "tempo": {"medio_ms": round(mean(tempos), 3), "min_ms": round(min(tempos), 3),
                  "max_ms": round(max(tempos), 3), "execucoes": execucoes},
        "consulta": texto,
        "resultados": resultados,
    }


def _backend(db):
    if db not in BACKENDS:
        raise HTTPException(400, f"banco desconhecido: {db}")
    return BACKENDS[db]


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
