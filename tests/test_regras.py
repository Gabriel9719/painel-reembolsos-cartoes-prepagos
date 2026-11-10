from pathlib import Path

import pandas as pd
import pytest

from despesas.regras import (conciliar_compras, conciliar_fundo_fixo, status_prestacoes, tratar_reembolsos,
                             uso_manutencao, processar)

RAIZ = Path(__file__).resolve().parents[1]


def test_quilometragem_confere_tarifa():
    df = pd.DataFrame({"tipo": ["Quilometragem", "Quilometragem", "Alimentação"], "km": [100, 100, 0],
                       "valor": [120.0, 138.0, 50.0], "veiculo": ["Próprio", "Próprio", ""],
                       "data_despesa": pd.to_datetime(["2026-01-01"] * 3), "data_envio": pd.to_datetime(["2026-01-05"] * 3),
                       "data_pagamento": pd.to_datetime(["2026-01-10"] * 3)})
    r = tratar_reembolsos(df)
    assert list(r["alerta_km"]) == [False, True, False]


def test_limite_de_manutencao():
    c = pd.DataFrame({"data": pd.to_datetime(["2026-03-02", "2026-03-20", "2026-03-05"]), "pa": ["01", "01", "02"],
                      "natureza": ["Manutenção", "Manutenção", "Despesa administrativa"], "valor": [200.0, 150.0, 999.0]})
    m = uso_manutencao(c).set_index("pa")
    assert m.loc["01", "excedente"] == pytest.approx(50.0)
    assert m.loc["02", "gasto_manutencao"] == 0 and not m.loc["02", "estourou_limite"]


def test_status_da_prestacao_de_contas():
    p = pd.DataFrame({"prazo": pd.to_datetime(["2026-10-15"] * 3 + ["2026-11-15"]),
                      "data_envio": pd.to_datetime(["2026-10-10", "2026-10-20", None, None])})
    s = status_prestacoes(p, pd.Timestamp("2026-11-10"))
    assert list(s["status"]) == ["No prazo", "Enviada com atraso", "Pendente (atrasada)", "Aguardando (no prazo)"]
    assert list(s["dias_atraso"]) == [0, 5, 26, 0]


def test_fundo_fixo_fecha():
    compras = pd.DataFrame({"compra_id": [1, 2], "data": pd.to_datetime(["2026-01-10", "2026-01-12"]),
                            "valor": [100.0, 50.0]})
    baixas = pd.DataFrame({"compra_id": [1], "data_baixa": pd.to_datetime(["2026-01-20"]), "valor": [100.0]})
    ff = pd.DataFrame({"data": pd.to_datetime(["2026-01-01", "2026-01-28"]),
                       "movimento": ["Crédito à plataforma", "Devolução da plataforma"], "valor": [500.0, 30.0]})
    f = conciliar_fundo_fixo(ff, conciliar_compras(compras, baixas)).iloc[0]
    assert f["falta_baixar"] == 50.0
    assert f["saldo_fundo_fixo"] == 370.0


def test_fluxo_completo_encontra_padroes_plantados(tmp_path):
    import subprocess, sys
    subprocess.run([sys.executable, str(RAIZ / "scripts/gerar_dados.py")], cwd=tmp_path, check=True)
    t = processar(tmp_path / "data/bruto", tmp_path / "out")
    assert set(t["fUsoManutencao"].query("estourou_limite")["pa"]) == {"05"}
    atrasos = t["fPrestacao"].groupby("pa")["dias_atraso"].mean()
    assert {"08", "11"} <= set(atrasos.nlargest(3).index)
    assert t["fReembolso"]["alerta_km"].sum() > 0
