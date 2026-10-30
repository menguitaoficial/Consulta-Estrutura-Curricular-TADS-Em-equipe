# Escolha final e justificativa

## Os três bancos para este problema

| | PostgreSQL | MongoDB | Neo4j |
|---|---|---|---|
| Como o dado é guardado | 3 tabelas, pré-requisito em tabela associativa | 1 documento por componente, pré-requisitos embutidos | nós de componente, arestas `REQUER` |
| Listar/filtrar componentes | Natural (`WHERE`, índices) | Natural, um acesso por documento | Funciona, mas não é o ponto forte |
| Pré-requisitos diretos | `JOIN` | Ler o campo do próprio documento | Um salto |
| Cadeia completa de pré-requisitos | `WITH RECURSIVE` (funciona, verboso) | `$graphLookup` (funciona, pouco legível) | `-[:REQUER*]->` (uma linha) |
| "O que depende de X" | Consulta inversa na tabela | Índice no campo achatado | Mesma aresta, outro sentido |
| E/OU nos pré-requisitos | Coluna `grupo` | Lista de listas, direto | Propriedade `grupo` na aresta |
| Adicionar outro curso | Linhas novas, mesmo esquema | Documentos novos | Nós e arestas novos |

## Escolha: PostgreSQL

Para este sistema, **PostgreSQL** é a escolha recomendada.

1. **Os dados são pequenos e bem estruturados.** Um curso tem dezenas de componentes e menos de 100 relações. Nenhum dos três bancos tem problema de desempenho nesse tamanho; a diferença de tempo é de milissegundos e vem mais do protocolo do driver do que da consulta.
2. **A maior parte das consultas é filtro e listagem** (por nome, código, período, tipo), onde o relacional é o mais direto e mais barato de manter.
3. **Os pré-requisitos cabem bem no relacional.** A tabela `PREREQUISITO` com `grupo` representa E/OU sem perda, tem integridade referencial (não existe pré-requisito para componente inexistente) e `WITH RECURSIVE` resolve a cadeia completa.
4. **Generalidade.** Outro curso é só um conjunto novo de linhas no mesmo esquema, sem alterar estrutura. Um sistema de matrícula real, que cruza estrutura curricular com alunos, turmas e históricos, também já é relacional.
5. **Menos peças.** Um banco que o time e a universidade já operam, contra um banco de grafos que seria uma dependência nova para um volume de dados que não exige.

### Quando a resposta mudaria

- **Neo4j** vence se o foco for a *navegação* do currículo: cadeias longas, "caminho mínimo até formar", análise de impacto ao mudar uma disciplina, ou vários cursos com muitas equivalências entre si. A consulta é a mais curta e legível das três.
- **MongoDB** vence se cada componente for consultado como um documento completo (ementa, bibliografia, objetivos) e o esquema variar muito entre cursos.

> Os tempos exibidos na interface servem para comparar na prática, mas com este volume as diferenças são pequenas. A decisão acima se apoia em modelagem, legibilidade e manutenção, não em milissegundos.
