import psycopg
from psycopg.rows import dict_row

from .. import config
from .base import linhas_prerequisito, mostrar, normalizar

SCHEMA = """
CREATE TABLE IF NOT EXISTS curso (
    codigo      text PRIMARY KEY,
    nome        text NOT NULL,
    instituicao text,
    ano         int
);
CREATE TABLE IF NOT EXISTS componente (
    curso      text NOT NULL REFERENCES curso(codigo) ON DELETE CASCADE,
    codigo     text NOT NULL,
    nome       text NOT NULL,
    nome_busca text NOT NULL,
    periodo    int,
    creditos   int,
    horas      int,
    tipo       text NOT NULL,
    PRIMARY KEY (curso, codigo)
);
CREATE TABLE IF NOT EXISTS prerequisito (
    curso      text NOT NULL,
    componente text NOT NULL,
    grupo      int  NOT NULL,   -- grupos ligados por E; itens do mesmo grupo por OU
    requisito  text NOT NULL,
    PRIMARY KEY (curso, componente, grupo, requisito),
    FOREIGN KEY (curso, componente) REFERENCES componente(curso, codigo) ON DELETE CASCADE,
    FOREIGN KEY (curso, requisito)  REFERENCES componente(curso, codigo) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_prereq_requisito ON prerequisito (curso, requisito);
"""

SELECT = """SELECT c.codigo, c.nome, c.periodo, c.creditos, c.horas, c.tipo,
  COALESCE((SELECT json_agg(x.itens ORDER BY x.grupo)
            FROM (SELECT p.grupo, json_agg(p.requisito) AS itens
                  FROM prerequisito p
                  WHERE p.curso = c.curso AND p.componente = c.codigo
                  GROUP BY p.grupo) x), '[]'::json) AS prerequisitos
FROM componente c
WHERE c.curso = %s AND """

DIRETOS = "c.codigo IN (SELECT {sel} FROM prerequisito WHERE curso = %s AND {onde} = %s)"
TRANSITIVOS = """c.codigo IN (
  WITH RECURSIVE r(cod) AS (
    SELECT {sel} FROM prerequisito WHERE curso = %s AND {onde} = %s
    UNION
    SELECT p.{sel} FROM prerequisito p JOIN r ON p.{onde} = r.cod WHERE p.curso = %s
  ) SELECT cod FROM r)"""


class Postgres:
    nome = "postgres"

    def __init__(self):
        self._conn = None

    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(config.POSTGRES_DSN, autocommit=True, row_factory=dict_row)
        return self._conn

    def preparar(self):
        self.conn.execute(SCHEMA)

    def remover(self, codigo):
        self.conn.execute("DELETE FROM curso WHERE codigo = %s", (codigo,))

    def carregar(self, curso):
        self.preparar()
        self.remover(curso["codigo"])
        cod = curso["codigo"]
        with self.conn.transaction(), self.conn.cursor() as cur:
            cur.execute("INSERT INTO curso VALUES (%s, %s, %s, %s)",
                        (cod, curso["nome"], curso.get("instituicao"), curso.get("ano")))
            cur.executemany(
                "INSERT INTO componente VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                [(cod, c["codigo"], c["nome"], normalizar(c["nome"]), c.get("periodo"),
                  c.get("creditos"), c.get("horas"), c["tipo"]) for c in curso["componentes"]])
            cur.executemany(
                "INSERT INTO prerequisito VALUES (%s, %s, %s, %s)",
                [(cod, comp, g, req) for comp, g, req in linhas_prerequisito(curso)])

    def cursos(self):
        return list(self.conn.execute("SELECT codigo, nome FROM curso ORDER BY codigo"))

    def consulta(self, op, curso, f):
        """Devolve (sql, parametros). f traz os filtros já normalizados."""
        if op == "buscar":
            conds, params = [], [curso]
            if f.get("nome"):
                conds.append("c.nome_busca LIKE %s")
                params.append(f"%{f['nome']}%")
            if f.get("codigo"):
                conds.append("c.codigo LIKE %s")
                params.append(f"%{f['codigo']}%")
            if f.get("periodo") is not None:
                conds.append("c.periodo = %s")
                params.append(f["periodo"])
            if f.get("tipo"):
                conds.append("c.tipo = %s")
                params.append(f["tipo"])
            if f.get("requer"):
                conds.append("c.codigo IN (SELECT componente FROM prerequisito WHERE curso = %s AND requisito = %s)")
                params += [curso, f["requer"]]
            return SELECT + (" AND ".join(conds) or "TRUE"), params
        # prerequisitos: sobe pelo grafo (componente -> requisito); dependentes: desce
        sel, onde = ("requisito", "componente") if op.startswith("prereq") else ("componente", "requisito")
        if op.endswith("diretos"):
            return SELECT + DIRETOS.format(sel=sel, onde=onde), [curso, curso, f["codigo"]]
        return SELECT + TRANSITIVOS.format(sel=sel, onde=onde), [curso, curso, f["codigo"], curso]

    def executar(self, op, curso, f):
        sql, params = self.consulta(op, curso, f)
        texto = mostrar(sql, params)
        return (lambda: self.conn.execute(sql, params).fetchall()), texto
