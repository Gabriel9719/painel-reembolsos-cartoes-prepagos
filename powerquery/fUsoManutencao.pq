let
    Origem = fxLerProcessado("fUsoManutencao"),
    Tipos = Table.TransformColumnTypes(Origem, {
        {"competencia", type text},
        {"pa", type text},
        {"gasto_manutencao", Currency.Type},
        {"limite", Currency.Type},
        {"excedente", Currency.Type},
        {"estourou_limite", type logical}}, "en-US")
in
    Tipos
