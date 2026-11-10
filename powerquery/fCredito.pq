let
    Origem = fxLerProcessado("fCredito"),
    Tipos = Table.TransformColumnTypes(Origem, {
        {"competencia", type text},
        {"pa", type text},
        {"credito_total", Currency.Type},
        {"parcela_manutencao", Currency.Type},
        {"parcela_administrativa", Currency.Type}}, "en-US"),
    Competencia = Table.TransformColumns(Tipos, {{"competencia", each Text.Start(_, 7), type text}})
in
    Competencia
