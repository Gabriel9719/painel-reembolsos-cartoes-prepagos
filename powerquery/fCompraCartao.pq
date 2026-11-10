let
    Origem = fxLerProcessado("fCompraCartao"),
    Tipos = Table.TransformColumnTypes(Origem, {
        {"compra_id", Int64.Type},
        {"data", type date},
        {"pa", type text},
        {"natureza", type text},
        {"categoria", type text},
        {"valor", Currency.Type},
        {"comprovante", type text},
        {"data_baixa", type date},
        {"valor_baixado", Currency.Type},
        {"situacao_baixa", type text},
        {"competencia", type text}}, "en-US")
in
    Tipos
