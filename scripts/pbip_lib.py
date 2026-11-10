"""Gera um projeto do Power BI em formato texto (PBIP: modelo em model.bim + relatório em report.json).

O PBIP abre no Power BI Desktop (Arquivo > Abrir > .pbip). Depois de atualizar os dados,
use "Salvar como" para gerar o .pbix. Autor: Gabriel Antônio Ribeiro.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

AUTOR = "Gabriel Antônio Ribeiro"
FMT_MOEDA = '"R$" #,0.00'
FMT_PCT = "0.0%"


# ----------------------------------------------------------------------------- DAX
def ler_medidas_dax(caminho: Path) -> list[dict]:
    """Lê um arquivo .dax no formato 'Nome =\\n    expressão' (comentários // são ignorados)."""
    medidas, atual = [], None
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        s = linha.strip()
        if not s or s.startswith("//"):
            continue
        m = re.match(r"^([^\s].*?)\s=\s*(.*)$", linha)
        if m and not linha.startswith((" ", "\t")):
            if atual:
                medidas.append(atual)
            atual = {"name": m.group(1).strip(), "expr": [m.group(2)] if m.group(2) else []}
        elif atual:
            atual["expr"].append(linha.rstrip())
    if atual:
        medidas.append(atual)
    out = []
    for m in medidas:
        expr = "\n".join(l for l in m["expr"] if l.strip())
        nome = m["name"]
        fmt = None
        if nome.startswith("Data"):
            fmt = "dd/mm/yyyy"
        elif nome.startswith(("%", "Var %")) or "%" in nome.split("(")[0]:
            fmt = FMT_PCT
        elif any(k in nome for k in ("Valor", "(R$)", "Diferença", "Saldo", "Custo")):
            fmt = FMT_MOEDA
        elif nome.startswith(("Qtd", "Prestações", "Alertas", "Compras", "PA-mês", "Km")):
            fmt = "#,0"
        item = {"name": nome, "expression": expr.split("\n") if "\n" in expr else expr}
        if fmt:
            item["formatString"] = fmt
        out.append(item)
    return out


# ----------------------------------------------------------------------------- Modelo
def coluna(nome: str, tipo: str, **extra) -> dict:
    c = {"name": nome, "dataType": tipo, "sourceColumn": nome, "lineageTag": str(uuid.uuid4())}
    c["summarizeBy"] = "sum" if tipo in ("decimal", "double") and not nome.startswith(("dias", "peso")) else "none"
    if tipo == "dateTime":
        c["formatString"] = "dd/mm/yyyy"
    if tipo == "decimal":
        c["formatString"] = FMT_MOEDA
    c.update(extra)
    return c


def tabela_m(nome: str, m: str, colunas: list[dict], **extra) -> dict:
    t = {"name": nome, "lineageTag": str(uuid.uuid4()), "columns": colunas,
         "partitions": [{"name": nome, "mode": "import", "source": {"type": "m", "expression": m.strip().split("\n")}}]}
    t.update(extra)
    return t


def tabela_calculada(nome: str, dax: str, colunas: list[tuple[str, str]], **extra) -> dict:
    cols = [{"type": "calculatedTableColumn", "name": n, "dataType": t, "isNameInferred": True,
             "isDataTypeInferred": True, "sourceColumn": f"[{n}]", "lineageTag": str(uuid.uuid4()), "summarizeBy": "none"}
            for n, t in colunas]
    t = {"name": nome, "lineageTag": str(uuid.uuid4()), "columns": cols,
         "partitions": [{"name": nome, "mode": "import", "source": {"type": "calculated", "expression": dax}}]}
    t.update(extra)
    return t


def relacao(de_tabela, de_col, para_tabela, para_col, ativo=True) -> dict:
    r = {"name": str(uuid.uuid4()), "fromTable": de_tabela, "fromColumn": de_col, "toTable": para_tabela, "toColumn": para_col}
    if not ativo:
        r["isActive"] = False
    return r


def tabela_medidas(medidas: list[dict]) -> dict:
    for m in medidas:
        m["lineageTag"] = str(uuid.uuid4())
    t = tabela_calculada("_Medidas", 'ROW("Coluna", BLANK())', [("Coluna", "string")])
    t["columns"][0]["isHidden"] = True
    t["measures"] = medidas
    return t


# ----------------------------------------------------------------------------- Relatório
def _ref(entidade: str, prop: str, medida: bool, alias: str) -> dict:
    chave = "Measure" if medida else "Column"
    return {chave: {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}, "Name": f"{entidade}.{prop}"}


def visual(tipo: str, x, y, w, h, papeis: dict[str, list[tuple[str, str, bool]]], titulo: str | None = None, z=0) -> dict:
    """papeis: {'Category': [(tabela, coluna, False)], 'Y': [('_Medidas', 'Valor Total', True)]}"""
    entidades = sorted({e for itens in papeis.values() for e, _, _ in itens})
    alias = {e: f"t{i}" for i, e in enumerate(entidades)}
    select, proj = [], {}
    for papel, itens in papeis.items():
        proj[papel] = []
        for e, p, med in itens:
            ref = _ref(e, p, med, alias[e])
            if ref not in select:
                select.append(ref)
            proj[papel].append({"queryRef": f"{e}.{p}", **({"active": True} if papel == "Category" else {})})
    nome = uuid.uuid4().hex[:20]
    sv = {"visualType": tipo, "projections": proj,
          "prototypeQuery": {"Version": 2, "From": [{"Name": a, "Entity": e, "Type": 0} for e, a in alias.items()], "Select": select},
          "drillFilterOtherVisuals": True}
    if titulo:
        sv["vcObjects"] = {"title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}},
                                                     "text": {"expr": {"Literal": {"Value": f"'{titulo}'"}}}}}]}
    cfg = {"name": nome, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": z, "width": w, "height": h}}], "singleVisual": sv}
    return {"x": x, "y": y, "z": z, "width": w, "height": h, "config": json.dumps(cfg, ensure_ascii=False), "filters": "[]"}


def pagina(nome: str, visuais: list[dict], ordem: int) -> dict:
    return {"name": uuid.uuid4().hex[:20], "displayName": nome, "displayOption": 1, "width": 1280, "height": 720,
            "ordinal": ordem, "config": "{}", "filters": "[]", "visualContainers": visuais}


# ----------------------------------------------------------------------------- Escrita
def escrever_pbip(destino: Path, nome: str, tabelas: list[dict], relacoes: list[dict], expressoes: list[dict],
                  paginas: list[dict]) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    sm, rp = destino / f"{nome}.SemanticModel", destino / f"{nome}.Report"
    sm.mkdir(exist_ok=True); rp.mkdir(exist_ok=True)
    (destino / f"{nome}.pbip").write_text(json.dumps({
        "version": "1.0", "artifacts": [{"report": {"path": f"{nome}.Report"}}], "settings": {"enableAutoRecovery": True}},
        indent=2), encoding="utf-8")
    (sm / "definition.pbism").write_text(json.dumps({"version": "4.0", "settings": {}}, indent=2), encoding="utf-8")
    modelo = {
        "name": "SemanticModel", "compatibilityLevel": 1567,
        "model": {
            "culture": "pt-BR", "defaultPowerBIDataSourceVersion": "powerBI_V3", "sourceQueryCulture": "pt-BR",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "tables": tabelas, "relationships": relacoes, "expressions": expressoes,
            "annotations": [{"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
                            {"name": "PBI_QueryOrder", "value": json.dumps([e["name"] for e in expressoes] +
                                                                           [t["name"] for t in tabelas if t["partitions"][0]["source"]["type"] == "m"])},
                            {"name": "Autor", "value": AUTOR}],
        },
    }
    (sm / "model.bim").write_text(json.dumps(modelo, ensure_ascii=False, indent=2), encoding="utf-8")
    (rp / "definition.pbir").write_text(json.dumps({
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{nome}.SemanticModel"}, "byConnection": None}},
        indent=2), encoding="utf-8")
    relatorio = {"config": json.dumps({"version": "5.43", "activeSectionIndex": 0, "objects": {}}),
                 "layoutOptimization": 0, "sections": paginas, "filters": "[]"}
    (rp / "report.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    (destino / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n", encoding="utf-8")
    return destino / f"{nome}.pbip"
