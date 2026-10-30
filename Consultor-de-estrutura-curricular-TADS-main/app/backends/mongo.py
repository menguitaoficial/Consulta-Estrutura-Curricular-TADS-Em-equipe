import json
import re

from pymongo import ASCENDING, MongoClient

from .. import config
from .base import achatar, normalizar

OCULTAR = {"_id": 0, "nome_busca": 0, "prereq_flat": 0, "curso": 0}


class Mongo:
    nome = "mongo"

    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = MongoClient(config.MONGO_URI)[config.MONGO_DB]
        return self._db

    @property
    def col(self):
        return self.db.componentes

    def preparar(self):
        self.col.create_index([("curso", ASCENDING), ("codigo", ASCENDING)], unique=True)
        self.col.create_index("prereq_flat")

    def remover(self, codigo):
        self.col.delete_many({"curso": codigo})
        self.db.cursos.delete_one({"_id": codigo})

    def carregar(self, curso):
        self.preparar()
        self.remover(curso["codigo"])
        self.db.cursos.insert_one({"_id": curso["codigo"], "nome": curso["nome"],
                                   "instituicao": curso.get("instituicao"), "ano": curso.get("ano")})
        self.col.insert_many([{
            "_id": f"{curso['codigo']}:{c['codigo']}",
            "curso": curso["codigo"],
            "codigo": c["codigo"],
            "nome": c["nome"],
            "nome_busca": normalizar(c["nome"]),
            "periodo": c.get("periodo"),
            "creditos": c.get("creditos"),
            "horas": c.get("horas"),
            "tipo": c["tipo"],
            # documento autocontido: os pré-requisitos moram dentro do componente
            "prerequisitos": c["prerequisitos"],
            "prereq_flat": achatar(c["prerequisitos"]),
        } for c in curso["componentes"]])

    def cursos(self):
        return [{"codigo": d["_id"], "nome": d["nome"]} for d in self.db.cursos.find().sort("_id")]

    def executar(self, op, curso, f):
        if op == "buscar":
            filtro = {"curso": curso}
            if f.get("nome"):
                filtro["nome_busca"] = {"$regex": re.escape(f["nome"])}
            if f.get("codigo"):
                filtro["codigo"] = {"$regex": re.escape(f["codigo"])}
            if f.get("periodo") is not None:
                filtro["periodo"] = f["periodo"]
            if f.get("tipo"):
                filtro["tipo"] = f["tipo"]
            if f.get("requer"):
                filtro["prereq_flat"] = f["requer"]
            texto = f"db.componentes.find(\n  {json.dumps(filtro, ensure_ascii=False)},\n  {json.dumps(OCULTAR)}\n)"
            return (lambda: list(self.col.find(filtro, OCULTAR))), texto

        if op.startswith("prereq"):
            lookup = {"from": "componentes", "startWith": "$prereq_flat", "connectFromField": "prereq_flat",
                      "connectToField": "codigo", "as": "r", "restrictSearchWithMatch": {"curso": curso}}
        else:
            lookup = {"from": "componentes", "startWith": "$codigo", "connectFromField": "codigo",
                      "connectToField": "prereq_flat", "as": "r", "restrictSearchWithMatch": {"curso": curso}}
        if op.endswith("diretos"):
            lookup["maxDepth"] = 0
        pipeline = [
            {"$match": {"curso": curso, "codigo": f["codigo"]}},
            {"$graphLookup": lookup},
            {"$unwind": "$r"},
            {"$replaceRoot": {"newRoot": "$r"}},
            {"$project": OCULTAR},
        ]
        texto = "db.componentes.aggregate(" + json.dumps(pipeline, ensure_ascii=False, indent=2) + ")"
        return (lambda: list(self.col.aggregate(pipeline))), texto
