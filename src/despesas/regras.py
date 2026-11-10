"""Regras de negócio da plataforma de despesas, aplicadas no ETL antes do Power BI.

Manter as regras em Python (testadas) e entregar ao Power BI tabelas já tratadas deixa o
modelo mais simples e garante o mesmo resultado em qualquer ferramenta.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

TARIFA_KM = 1.20
LIMITE_MANUTENCAO = 300.00          # parcela do crédito mensal reservada à manutenção
DIA_PRAZO_PRESTACAO = 15            # prestação de contas até o dia 15 do mês seguinte
SLA_ENVIO_REEMBOLSO = 30            # dias entre a despesa e o envio do pedido


def ler(pasta: Path) -> dict[str, pd.DataFrame]:
    def r(nome, datas=()):
        return pd.read_csv(pasta / nome, sep=";", dtype={"pa": str}, parse_dates=list(datas))
    return {
        "reembolsos": r("reembolsos.csv", ["data_despesa", "data_envio", "data_aprovacao", "data_pagamento"]),
        "creditos": r("creditos_cartao.csv", ["competencia"]),
        "compras": r("compras_cartao.csv", ["data"]),
        "prestacoes": r("prestacoes.csv", ["prazo", "data_envio"]),
        "baixas": r("baixas_sistema.csv", ["data_baixa"]),
        "fundo_fixo": r("fundo_fixo.csv", ["data"]),
    }


def tratar_reembolsos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["valor_esperado_km"] = (df["km"] * TARIFA_KM).round(2).where(df["tipo"] == "Quilometragem")
    df["divergencia_km"] = (df["valor"] - df["valor_esperado_km"]).round(2).where(df["tipo"] == "Quilometragem")
    df["alerta_km"] = df["divergencia_km"].abs() > 0.01
    df["dias_para_envio"] = (df["data_envio"] - df["data_despesa"]).dt.days
    df["fora_do_prazo_envio"] = df["dias_para_envio"] > SLA_ENVIO_REEMBOLSO
    df["dias_ate_pagamento"] = (df["data_pagamento"] - df["data_envio"]).dt.days
    df["veiculo_alugado"] = df["veiculo"].eq("Alugado")
    df["competencia"] = df["data_despesa"].dt.to_period("M").astype(str)
    return df


def uso_manutencao(compras: pd.DataFrame) -> pd.DataFrame:
    """Gasto de manutenção por PA/mês contra o limite de R$ 300."""
    c = compras.assign(competencia=compras["data"].dt.to_period("M").astype(str))
    m = (c[c["natureza"] == "Manutenção"].groupby(["competencia", "pa"])["valor"].sum()
         .reindex(pd.MultiIndex.from_product([sorted(c["competencia"].unique()), sorted(c["pa"].unique())],
                                             names=["competencia", "pa"]), fill_value=0).reset_index())
    m["limite"] = LIMITE_MANUTENCAO
    m["excedente"] = (m["valor"] - LIMITE_MANUTENCAO).clip(lower=0).round(2)
    m["estourou_limite"] = m["excedente"] > 0
    return m.rename(columns={"valor": "gasto_manutencao"})


def status_prestacoes(prest: pd.DataFrame, hoje: pd.Timestamp) -> pd.DataFrame:
    p = prest.copy()
    ref = p["data_envio"].fillna(hoje)
    p["dias_atraso"] = (ref - p["prazo"]).dt.days.clip(lower=0)
    p["status"] = "No prazo"
    p.loc[p["data_envio"].notna() & (p["dias_atraso"] > 0), "status"] = "Enviada com atraso"
    p.loc[p["data_envio"].isna() & (hoje > p["prazo"]), "status"] = "Pendente (atrasada)"
    p.loc[p["data_envio"].isna() & (hoje <= p["prazo"]), "status"] = "Aguardando (no prazo)"
    return p


def conciliar_compras(compras: pd.DataFrame, baixas: pd.DataFrame) -> pd.DataFrame:
    """O que já foi baixado no sistema contábil e o que falta baixar, por compra."""
    c = compras.merge(baixas[["compra_id", "data_baixa", "valor"]].rename(columns={"valor": "valor_baixado"}),
                      on="compra_id", how="left", validate="1:1")
    c["situacao_baixa"] = c["valor_baixado"].notna().map({True: "Baixada no sistema", False: "Falta baixar"})
    c["competencia"] = c["data"].dt.to_period("M").astype(str)
    return c


def conciliar_fundo_fixo(ff: pd.DataFrame, compras_conc: pd.DataFrame) -> pd.DataFrame:
    """Por mês: créditos enviados à plataforma − devoluções − baixas no sistema = saldo a baixar."""
    f = ff.assign(competencia=ff["data"].dt.to_period("M").astype(str))
    piv = f.pivot_table(index="competencia", columns="movimento", values="valor", aggfunc="sum", fill_value=0)
    piv = piv.reindex(columns=["Crédito à plataforma", "Devolução da plataforma"], fill_value=0)
    baixado = compras_conc.groupby("competencia")["valor_baixado"].sum()
    gasto = compras_conc.groupby("competencia")["valor"].sum()
    out = pd.DataFrame({
        "creditos": piv["Crédito à plataforma"],
        "devolucoes": piv["Devolução da plataforma"],
        "gasto_cartoes": gasto,
        "baixado_sistema": baixado,
    }).fillna(0)
    out["falta_baixar"] = (out["gasto_cartoes"] - out["baixado_sistema"]).round(2)
    out["saldo_fundo_fixo"] = (out["creditos"] - out["devolucoes"] - out["baixado_sistema"]).round(2)
    out["saldo_acumulado"] = out["saldo_fundo_fixo"].cumsum().round(2)
    return out.reset_index().rename(columns={"index": "competencia"})


def processar(entrada: Path, saida: Path, hoje: str = "2026-11-10") -> dict[str, pd.DataFrame]:
    b = ler(entrada)
    comp = conciliar_compras(b["compras"], b["baixas"])
    tabelas = {
        "fReembolso": tratar_reembolsos(b["reembolsos"]),
        "fCompraCartao": comp,
        "fCredito": b["creditos"],
        "fUsoManutencao": uso_manutencao(b["compras"]),
        "fPrestacao": status_prestacoes(b["prestacoes"], pd.Timestamp(hoje)),
        "fFundoFixo": conciliar_fundo_fixo(b["fundo_fixo"], comp),
    }
    saida.mkdir(parents=True, exist_ok=True)
    for nome, df in tabelas.items():
        df.to_csv(saida / f"{nome}.csv", sep=";", index=False, date_format="%Y-%m-%d")
    return tabelas
