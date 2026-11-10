"""Gera as consultas Power Query (powerquery/*.pq) e o projeto pbip/ReembolsosCartoes.pbip
a partir das tabelas tratadas em data/processado e de dax/medidas.dax.

    python scripts/gerar_pbip.py --pasta-dados "C:\\Projetos\\painel-reembolsos-cartoes-prepagos\\data\\processado\\"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from pbip_lib import coluna, escrever_pbip, ler_medidas_dax, pagina, relacao, tabela_m, tabela_medidas, visual  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data/processado"
FATOS = ["fReembolso", "fCompraCartao", "fCredito", "fUsoManutencao", "fPrestacao", "fFundoFixo"]
M_TIPO = {"int64": "Int64.Type", "string": "type text", "dateTime": "type date", "decimal": "Currency.Type",
          "boolean": "type logical", "double": "type number"}


def inferir(nome: str) -> list[tuple[str, str]]:
    """Tipo de cada coluna pelo nome/conteúdo do CSV tratado."""
    df = pd.read_csv(PROC / f"{nome}.csv", sep=";", dtype=str, keep_default_na=False)
    cols = []
    for c in df.columns:
        vals = set(v for v in df[c].unique() if v != "")
        if c.startswith(("data", "prazo")):
            t = "dateTime"
        elif vals and vals <= {"True", "False"}:
            t = "boolean"
        elif c in ("pa", "competencia") or not all(v.replace(".", "", 1).lstrip("-").isdigit() for v in vals):
            t = "string"
        elif c in ("id", "compra_id", "km") or c.startswith("dias"):
            t = "int64"
        else:
            t = "decimal"
        cols.append((c, t))
    return cols


def m_fato(nome: str, cols: list[tuple[str, str]]) -> str:
    tipos = ",\n        ".join(f'{{"{c}", {M_TIPO[t]}}}' for c, t in cols)
    extra = ""
    if nome == "fCredito":   # competência vem como data; padroniza para AAAA-MM como nos demais fatos
        extra = ',\n    Competencia = Table.TransformColumns(Tipos, {{"competencia", each Text.Start(_, 7), type text}})'
    ultimo = "Competencia" if extra else "Tipos"
    return (f'let\n    Origem = fxLerProcessado("{nome}"),\n    Tipos = Table.TransformColumnTypes(Origem, {{\n        {tipos}}}, "en-US")'
            f'{extra}\nin\n    {ultimo}\n')


M_DCOMP = """let
    Fontes = {fReembolso[competencia], fCompraCartao[competencia], fCredito[competencia], fUsoManutencao[competencia],
              fPrestacao[competencia], fFundoFixo[competencia]},
    Lista  = List.Sort(List.Distinct(List.RemoveNulls(List.Combine(Fontes)))),
    Tabela = Table.FromList(Lista, Splitter.SplitByNothing(), {"competencia"}),
    Tipo   = Table.TransformColumnTypes(Tabela, {{"competencia", type text}}),
    Mes    = Table.AddColumn(Tipo, "mes", each Text.Proper(Date.ToText(Date.FromText([competencia] & "-01"), "MMM/yy", "pt-BR")), type text)
in
    Mes
"""
M_DPA = """let
    Lista  = List.Sort(List.Distinct(List.RemoveNulls(List.Combine({fReembolso[pa], fCompraCartao[pa], fCredito[pa], fPrestacao[pa]})))),
    Tabela = Table.FromList(Lista, Splitter.SplitByNothing(), {"pa"}),
    Tipo   = Table.TransformColumnTypes(Tabela, {{"pa", type text}}),
    Nome   = Table.AddColumn(Tipo, "nome_pa", each "PA " & [pa], type text)
in
    Nome
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta-dados", default=r"C:\Projetos\painel-reembolsos-cartoes-prepagos\data\processado" + "\\")
    a = ap.parse_args()

    pq_dir = RAIZ / "powerquery"
    tabelas = []
    for f in FATOS:
        cols = inferir(f)
        m = m_fato(f, cols)
        (pq_dir / f"{f}.pq").write_text(m, encoding="utf-8")
        tabelas.append(tabela_m(f, m, [coluna(c, t, **({"isHidden": True} if c in ("pa", "competencia") else {}))
                                         for c, t in cols]))
    (pq_dir / "dCompetencia.pq").write_text(M_DCOMP, encoding="utf-8")
    (pq_dir / "dPA.pq").write_text(M_DPA, encoding="utf-8")
    tabelas.append(tabela_m("dCompetencia", M_DCOMP, [coluna("competencia", "string", isKey=True), coluna("mes", "string")]))
    tabelas.append(tabela_m("dPA", M_DPA, [coluna("pa", "string", isKey=True), coluna("nome_pa", "string")]))
    tabelas.append(tabela_medidas(ler_medidas_dax(RAIZ / "dax/medidas.dax")))

    fx = (pq_dir / "fxLerProcessado.pq").read_text(encoding="utf-8")
    fx = "\n".join(l for l in fx.splitlines() if not l.lstrip().startswith("//"))
    expressoes = [
        {"name": "PastaProcessado", "kind": "m",
         "expression": f'"{a.pasta_dados.replace(chr(92), chr(92) * 2)}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'},
        {"name": "fxLerProcessado", "kind": "m", "expression": fx.split("\n")},
    ]
    relacoes = []
    for f in FATOS:
        relacoes.append(relacao(f, "competencia", "dCompetencia", "competencia"))
        if f != "fFundoFixo":
            relacoes.append(relacao(f, "pa", "dPA", "pa"))

    M = "_Medidas"
    card = lambda x, y, med, tit: visual("card", x, y, 240, 110, {"Values": [(M, med, True)]}, tit)
    p1 = pagina("Reembolsos", [
        card(20, 20, "Reembolsos (R$)", "Reembolsos"), card(270, 20, "Reembolsos Veículo Alugado (R$)", "Veículo alugado"),
        card(520, 20, "Custo por Km (veículo alugado)", "Custo por km (alugado)"), card(770, 20, "Alertas de Km", "Alertas de km"),
        card(1020, 20, "% Enviado Fora do Prazo", "Enviado fora do prazo"),
        visual("clusteredBarChart", 20, 150, 620, 550, {"Category": [("fReembolso", "tipo", False)], "Y": [(M, "Reembolsos (R$)", True)]},
               "Reembolsos por tipo"),
        visual("tableEx", 660, 150, 600, 550, {"Values": [("fReembolso", "colaborador", False), (M, "Qtd Reembolsos", True),
                                                         (M, "Reembolsos (R$)", True), (M, "Alertas de Km", True)]}, "Por colaborador"),
    ], 0)
    p2 = pagina("Cartões e manutenção", [
        card(20, 20, "Créditos nos Cartões (R$)", "Créditos"), card(270, 20, "Gasto nos Cartões (R$)", "Gasto"),
        card(520, 20, "% Utilização do Crédito", "Utilização"), card(770, 20, "PA-mês acima do limite", "PA-mês acima do limite"),
        card(1020, 20, "Compras sem Comprovante", "Sem comprovante"),
        visual("clusteredColumnChart", 20, 150, 1240, 550, {"Category": [("dPA", "nome_pa", False)],
                                                           "Y": [(M, "Gasto Manutenção (R$)", True), (M, "Excedente Manutenção (R$)", True)]},
               "Manutenção por PA (limite R$ 300/mês)"),
    ], 1)
    p3 = pagina("Prestação de contas", [
        card(20, 20, "% Prestações no Prazo", "No prazo"), card(270, 20, "Prestações com Atraso", "Com atraso"),
        card(520, 20, "Atraso Médio (dias)", "Atraso médio (dias)"),
        visual("tableEx", 20, 150, 1240, 550, {"Values": [("dPA", "nome_pa", False), (M, "Prestações com Atraso", True),
                                                         (M, "Atraso Médio (dias)", True)]}, "Atrasos por PA"),
    ], 2)
    p4 = pagina("Fundo fixo", [
        card(20, 20, "Créditos à Plataforma (R$)", "Créditos à plataforma"), card(270, 20, "Baixado no Sistema (R$)", "Baixado no sistema"),
        card(520, 20, "Falta Baixar (R$)", "Falta baixar"), card(770, 20, "% Baixado", "% baixado"),
        card(1020, 20, "Saldo Fundo Fixo Acumulado (R$)", "Saldo acumulado"),
        visual("clusteredColumnChart", 20, 150, 1240, 550, {"Category": [("dCompetencia", "competencia", False)],
                                                           "Y": [(M, "Gasto nos Cartões (R$)", True), (M, "Baixado no Sistema (R$)", True)]},
               "Gasto x baixado por competência"),
    ], 3)
    arq = escrever_pbip(RAIZ / "pbip", "ReembolsosCartoes", tabelas, relacoes, expressoes, [p1, p2, p3, p4])
    print(f"Projeto gerado: {arq}")
    for t in tabelas[:6]:
        print(t["name"], [(c["name"], c["dataType"]) for c in t["columns"]])


if __name__ == "__main__":
    main()
