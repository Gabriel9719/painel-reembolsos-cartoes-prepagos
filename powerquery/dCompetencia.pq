let
    Fontes = {fReembolso[competencia], fCompraCartao[competencia], fCredito[competencia], fUsoManutencao[competencia],
              fPrestacao[competencia], fFundoFixo[competencia]},
    Lista  = List.Sort(List.Distinct(List.RemoveNulls(List.Combine(Fontes)))),
    Tabela = Table.FromList(Lista, Splitter.SplitByNothing(), {"competencia"}),
    Tipo   = Table.TransformColumnTypes(Tabela, {{"competencia", type text}}),
    Mes    = Table.AddColumn(Tipo, "mes", each Text.Proper(Date.ToText(Date.FromText([competencia] & "-01"), "MMM/yy", "pt-BR")), type text)
in
    Mes
