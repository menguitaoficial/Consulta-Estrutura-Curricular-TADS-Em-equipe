# Consultor de Estrutura Curricular — TADS

Sistema web para consultar a estrutura curricular do curso de **Tecnologia em Análise e Desenvolvimento de Sistemas (TADS/UFRN, versão 2019)** e **comparar o desempenho de três paradigmas de banco de dados** executando a mesma consulta:

| Paradigma | Banco |
|---|---|
| Relacional | PostgreSQL |
| Não relacional — documentos | MongoDB |
| Não relacional — grafo | Neo4j |

Trabalho da disciplina **Fundamentos e Técnicas em Ciência de Dados** (Etapa 2, em equipe). Os dados foram extraídos do [fluxograma de 2019 do SIGAA](https://sigaa.ufrn.br/sigaa/downloadArquivoPublico?idProducao=6317915&key=300ba6bebacf53bae709c86d9662d6b9).

## O que o sistema faz

Uma interface web em que se escolhe o banco (ou **todos, para comparar**), faz a consulta e vê o resultado, o **tempo de resposta** e a **consulta nativa** executada (SQL, pipeline do MongoDB ou Cypher).

Consultas disponíveis:

- **Buscar componentes** por nome (sem diferenciar acentos), código, período, tipo (obrigatória, optativa, atividade) ou "tem como pré-requisito X".
- **Pré-requisitos** de um componente, diretos ou a cadeia completa.
- **Dependentes**: o que cada componente libera, direto ou em cadeia.

O tempo mostrado é a média de N execuções (padrão 10, após uma execução de aquecimento), com mínimo e máximo. As consultas rodam uma por vez, para não distorcer a medição.

Os três bancos rodam em `localhost` via Docker, para que a comparação de tempo seja justa (misturar banco local e em nuvem invalida a comparação).

## Como rodar

Requisitos: Docker e Python 3.11 ou superior.

```bash
docker compose up -d                        # Postgres, Mongo e Neo4j (o Neo4j leva ~30 s para ficar pronto)
python -m pip install -r requirements.txt
python -m app.loader                        # carrega data/cursos/*.json nos três bancos
python -m uvicorn app.main:app --port 8000
```

Abra http://localhost:8000. Para parar os bancos: `docker compose stop`.

## Notebook

[notebooks/estrutura_curricular.ipynb](notebooks/estrutura_curricular.ipynb) usa o mesmo código do sistema para carregar os dados, mostrar como o mesmo componente fica em cada modelo, rodar a mesma consulta nos três bancos (conferindo que os resultados são idênticos) e fazer um benchmark com gráfico. Já está salvo com as saídas, então dá para ler direto no GitHub. Para reexecutar: suba os bancos e use `python -m pip install nbformat nbconvert ipykernel pandas matplotlib`.

## Os três modelos

Os diagramas e a explicação de cada modelo estão em [docs/modelos_logicos.md](docs/modelos_logicos.md). Em resumo:

- **Relacional:** tabelas `curso`, `componente` e `prerequisito` (associativa N:N do componente com ele mesmo). Cadeias de pré-requisitos com `WITH RECURSIVE`.
- **Documentos:** um documento por componente, com os pré-requisitos embutidos. Cadeias com `$graphLookup`.
- **Grafo:** nós `Componente` ligados por arestas `REQUER`. Cadeias com `-[:REQUER*]->`.

Nos três, os pré-requisitos guardam a lógica **E/OU** do fluxograma: grupos são ligados por E, e os itens dentro de um grupo por OU. Exemplo: Arquitetura de Software exige `TAD0103 OU TAD0111`.

A escolha final entre os três e a justificativa estão em [docs/justificativa.md](docs/justificativa.md).

## Estrutura do projeto

```
app/
  main.py            API FastAPI (/api/consulta, /api/cursos) e medição de tempo
  loader.py          carrega os cursos nos três bancos
  backends/          um módulo por banco, com a consulta no idioma nativo
  static/index.html  interface web
data/cursos/         um JSON por curso
docs/                modelos lógicos e justificativa
docker-compose.yml   Postgres, MongoDB e Neo4j
```

## Adicionar outro curso

Nada no código é específico do TADS. Crie `data/cursos/<curso>.json` no mesmo formato de [tads-2019.json](data/cursos/tads-2019.json) e rode `python -m app.loader`. O curso aparece no seletor da interface.

```json
{
  "codigo": "ADS-2020", "nome": "...", "instituicao": "...", "ano": 2020,
  "componentes": [
    {"codigo": "X1", "nome": "...", "periodo": 1, "creditos": 4, "tipo": "obrigatoria", "prerequisitos": []},
    {"codigo": "X2", "nome": "...", "periodo": 2, "creditos": 4, "tipo": "obrigatoria", "prerequisitos": [["X1"]]},
    {"codigo": "X3", "nome": "...", "periodo": 3, "creditos": 4, "tipo": "obrigatoria", "prerequisitos": [["X1", "X2"]]}
  ]
}
```

`prerequisitos` é uma lista de grupos: grupos são ligados por **E** e itens dentro de um grupo por **OU** (`[["X1","X2"]]` significa X1 OU X2). `tipo` é `obrigatoria`, `optativa` ou `atividade`; `periodo` pode ser `null`; use `horas` no lugar de `creditos` quando for o caso. O loader valida que todo pré-requisito citado existe no curso.

## Sobre os dados

O PDF do SIGAA é uma figura, sem texto para períodos e setas. Os períodos (linhas da grade) e os pré-requisitos (setas contínuas = E, tracejadas = OU) foram lidos visualmente e **vale conferir contra o original**. O número ao lado de cada código foi interpretado como créditos. TAD0140 (TCC II) não tem seta de pré-requisito no fluxograma e foi mantido sem pré-requisito.

## Tecnologias

Python, FastAPI, PostgreSQL 16, MongoDB 7, Neo4j 5, Docker Compose, HTML/JavaScript puro.
