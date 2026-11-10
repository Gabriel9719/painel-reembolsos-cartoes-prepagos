let
    Origem = fxLerProcessado("fFundoFixo"),
    Tipos = Table.TransformColumnTypes(Origem, {
        {"competencia", type text}, {"creditos", Currency.Type}, {"devolucoes", Currency.Type},
        {"gasto_cartoes", Currency.Type}, {"baixado_sistema", Currency.Type}, {"falta_baixar", Currency.Type},
        {"saldo_fundo_fixo", Currency.Type}, {"saldo_acumulado", Currency.Type}}, "en-US")
in
    Tipos
