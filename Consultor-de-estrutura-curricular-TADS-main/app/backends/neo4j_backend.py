from neo4j import GraphDatabase

from .. import config
from .base import linhas_prerequisito, normalizar

# Reconstrói [[grupo], [grupo]] a partir das arestas REQUER {grupo}
RETORNO = """
OPTIONAL MATCH (c)-[r:REQUER]->(p:Componente)
WITH c, r.grupo AS g, collect(p.codigo) AS itens
WITH c, collect(CASE WHEN g IS NULL THEN NULL ELSE itens END) AS prerequisitos
RETURN c.codigo AS codigo, c.nome AS nome, c.periodo AS periodo, c.creditos AS creditos,
       c.horas AS horas, c.tipo AS tipo, prerequisitos"""

CAMINHOS = {
    "prereq_diretos": "-[:REQUER]->",
    "prereq_transitivos": "-[:REQUER*]->",
    "dependentes_diretos": "<-[:REQUER]-",
    "dependentes_transitivos": "<-[:REQUER*]-",
}


class Neo4j:
    nome = "neo4j"

    def __init__(self):
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
        return self._driver

    def _run(self, texto, **params):
        with self.driver.session() as s:
            return [dict(r) for r in s.run(texto, **params)]

    def preparar(self):
        self._run("CREATE CONSTRAINT componente_uid IF NOT EXISTS FOR (n:Componente) REQUIRE n.uid IS UNIQUE")
        self._run("CREATE INDEX componente_curso_codigo IF NOT EXISTS FOR (n:Componente) ON (n.curso, n.codigo)")
        self._run("CREATE CONSTRAINT curso_codigo IF NOT EXISTS FOR (n:Curso) REQUIRE n.codigo IS UNIQUE")

    def remover(self, codigo):
        self._run("MATCH (n:Componente {curso: $c}) DETACH DELETE n", c=codigo)
        self._run("MATCH (n:Curso {codigo: $c}) DETACH DELETE n", c=codigo)

    def carregar(self, curso):
        self.preparar()
        self.remover(curso["codigo"])
        cod = curso["codigo"]
        self._run("CREATE (:Curso {codigo: $codigo, nome: $nome, instituicao: $instituicao, ano: $ano})",
                  codigo=cod, nome=curso["nome"], instituicao=curso.get("instituicao"), ano=curso.get("ano"))
        comps = [{"uid": f"{cod}:{c['codigo']}", "codigo": c["codigo"], "nome": c["nome"],
                  "nome_busca": normalizar(c["nome"]), "periodo": c.get("periodo"),
                  "creditos": c.get("creditos"), "horas": c.get("horas"), "tipo": c["tipo"]}
                 for c in curso["componentes"]]
        self._run("""MATCH (cu:Curso {codigo: $curso})
                     UNWIND $comps AS c
                     CREATE (n:Componente {uid: c.uid, curso: $curso, codigo: c.codigo, nome: c.nome,
                                           nome_busca: c.nome_busca, periodo: c.periodo,
                                           creditos: c.creditos, horas: c.horas, tipo: c.tipo})
                     CREATE (cu)-[:OFERECE]->(n)""", curso=cod, comps=comps)
        reqs = [{"a": f"{cod}:{comp}", "b": f"{cod}:{req}", "grupo": g}
                for comp, g, req in linhas_prerequisito(curso)]
        self._run("""UNWIND $reqs AS r
                     MATCH (a:Componente {uid: r.a}), (b:Componente {uid: r.b})
                     CREATE (a)-[:REQUER {grupo: r.grupo}]->(b)""", reqs=reqs)

    def cursos(self):
        return self._run("MATCH (c:Curso) RETURN c.codigo AS codigo, c.nome AS nome ORDER BY codigo")

    def executar(self, op, curso, f):
        params = {"curso": curso}
        if op == "buscar":
            conds = []
            if f.get("nome"):
                conds.append("c.nome_busca CONTAINS $nome")
                params["nome"] = f["nome"]
            if f.get("codigo"):
                conds.append("c.codigo CONTAINS $codigo")
                params["codigo"] = f["codigo"]
            if f.get("periodo") is not None:
                conds.append("c.periodo = $periodo")
                params["periodo"] = f["periodo"]
            if f.get("tipo"):
                conds.append("c.tipo = $tipo")
                params["tipo"] = f["tipo"]
            if f.get("requer"):
                conds.append("EXISTS { (c)-[:REQUER]->(:Componente {curso: $curso, codigo: $requer}) }")
                params["requer"] = f["requer"]
            inicio = "MATCH (c:Componente {curso: $curso})" + (" WHERE " + " AND ".join(conds) if conds else "")
        else:
            params["codigo"] = f["codigo"]
            inicio = (f"MATCH (:Componente {{curso: $curso, codigo: $codigo}}){CAMINHOS[op]}(c:Componente)\n"
                      "WITH DISTINCT c")
        texto = inicio + RETORNO
        exibicao = texto + "\n// parâmetros: " + str(params)
        return (lambda: self._run(texto, **params)), exibicao
