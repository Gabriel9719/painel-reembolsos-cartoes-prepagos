let
    Lista  = List.Sort(List.Distinct(List.RemoveNulls(List.Combine({fReembolso[pa], fCompraCartao[pa], fCredito[pa], fPrestacao[pa]})))),
    Tabela = Table.FromList(Lista, Splitter.SplitByNothing(), {"pa"}),
    Tipo   = Table.TransformColumnTypes(Tabela, {{"pa", type text}}),
    Nome   = Table.AddColumn(Tipo, "nome_pa", each "PA " & [pa], type text)
in
    Nome
