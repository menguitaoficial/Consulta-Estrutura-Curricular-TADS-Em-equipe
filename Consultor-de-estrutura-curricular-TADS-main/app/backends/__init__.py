from .mongo import Mongo
from .neo4j_backend import Neo4j
from .postgres import Postgres

BACKENDS = {b.nome: b for b in (Postgres(), Mongo(), Neo4j())}
