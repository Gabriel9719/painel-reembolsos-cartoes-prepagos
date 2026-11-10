let
    Origem = fxLerProcessado("fPrestacao"),
    Tipos = Table.TransformColumnTypes(Origem, {
        {"competencia", type text}, {"pa", type text}, {"prazo", type date}, {"data_envio", type date},
        {"dias_atraso", Int64.Type}, {"status", type text}}, "en-US")
in
    Tipos
