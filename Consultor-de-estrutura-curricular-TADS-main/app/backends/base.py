import re
import unicodedata

OPS = ("buscar", "prereq_diretos", "prereq_transitivos", "dependentes_diretos", "dependentes_transitivos")


def normalizar(texto):
    """Minúsculas e sem acento, para busca por nome igual nos três bancos."""
    sem_acento = unicodedata.normalize("NFD", texto or "")
    return re.sub(r"[̀-ͯ]", "", sem_acento).lower().strip()


def achatar(prerequisitos):
    return sorted({cod for grupo in prerequisitos for cod in grupo})


def linhas_prerequisito(curso):
    """(componente, grupo, requisito). Grupos são ligados por E; dentro do grupo, por OU."""
    for comp in curso["componentes"]:
        for grupo, itens in enumerate(comp["prerequisitos"]):
            for req in itens:
                yield comp["codigo"], grupo, req


def validar(curso):
    codigos = {c["codigo"] for c in curso["componentes"]}
    if len(codigos) != len(curso["componentes"]):
        raise ValueError(f"{curso['codigo']}: códigos de componente repetidos")
    for comp, _, req in linhas_prerequisito(curso):
        if req not in codigos:
            raise ValueError(f"{curso['codigo']}: {comp} exige {req}, que não existe")


def limpar(linha):
    """Mesmo formato de saída e mesma ordem, qualquer que seja o banco."""
    return {
        "codigo": linha["codigo"],
        "nome": linha["nome"],
        "periodo": linha.get("periodo"),
        "creditos": linha.get("creditos"),
        "horas": linha.get("horas"),
        "tipo": linha["tipo"],
        "prerequisitos": sorted(sorted(g) for g in (linha.get("prerequisitos") or [])),
    }


def ordenar(linhas):
    return sorted(linhas, key=lambda r: (r["periodo"] is None, r["periodo"] or 0, r["codigo"]))


def mostrar(texto, params):
    """Texto da consulta com os parâmetros no lugar, só para exibir na interface."""
    for p in params:
        texto = texto.replace("%s", repr(p) if isinstance(p, str) else str(p), 1)
    return texto
