let
    Origem = fxLerProcessado("fReembolso"),
    Tipos = Table.TransformColumnTypes(Origem, {
        {"id", Int64.Type},
        {"colaborador", type text},
        {"pa", type text},
        {"data_despesa", type date},
        {"data_envio", type date},
        {"data_aprovacao", type date},
        {"data_pagamento", type date},
        {"tipo", type text},
        {"veiculo", type text},
        {"km", Int64.Type},
        {"valor", Currency.Type},
        {"valor_esperado_km", Currency.Type},
        {"divergencia_km", Currency.Type},
        {"alerta_km", type logical},
        {"dias_para_envio", Int64.Type},
        {"fora_do_prazo_envio", type logical},
        {"dias_ate_pagamento", Int64.Type},
        {"veiculo_alugado", type logical},
        {"competencia", type text}}, "en-US")
in
    Tipos
