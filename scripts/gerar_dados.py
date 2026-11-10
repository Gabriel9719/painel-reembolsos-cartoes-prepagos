"""Gera dados FICTÍCIOS de uma plataforma de despesas corporativas (jan-out/2026):

  reembolsos.csv          pedidos de reembolso de colaboradores (inclui viagens com veículo alugado)
  creditos_cartao.csv     créditos mensais nos cartões pré-pagos dos PAs
  compras_cartao.csv      compras feitas com os cartões (manutenção / despesa administrativa)
  prestacoes.csv          envio mensal da prestação de contas de cada PA
  baixas_sistema.csv      compras já baixadas no sistema contábil
  fundo_fixo.csv          créditos enviados à plataforma e devoluções (visão do fundo fixo)
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

PAS = [f"{i:02d}" for i in range(1, 13)]
COLABS = [f"Colaborador {c}" for c in "ABCDEFGHIJKLMNOPQRST"]
CATEG_ADM = ["Material de limpeza", "Copa e cozinha", "Material de escritório", "Correios", "Cópias e impressões"]
CATEG_MAN = ["Pequenos reparos", "Material elétrico", "Chaveiro", "Jardinagem"]
TARIFA_KM = 1.20                      # R$/km (parâmetro fictício)


def w(pasta: Path, nome: str, cab: list[str], linhas: list) -> None:
    with (pasta / nome).open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f, delimiter=";"); wr.writerow(cab); wr.writerows(linhas)


def main(saida: str = "data/bruto", seed: int = 15) -> None:
    rng = random.Random(seed)
    p = Path(saida); p.mkdir(parents=True, exist_ok=True)

    # ---------------- reembolsos
    reemb, rid = [], 1
    for _ in range(420):
        d = date(2026, 1, 2) + timedelta(days=rng.randint(0, 290))
        tipo = rng.choices(["Quilometragem", "Alimentação", "Hospedagem", "Pedágio", "Combustível (veículo alugado)"],
                           weights=[35, 30, 12, 8, 15])[0]
        km = rng.randint(20, 480) if tipo == "Quilometragem" else (rng.randint(60, 600) if "alugado" in tipo else 0)
        veiculo = "Próprio" if tipo == "Quilometragem" else "Alugado" if "alugado" in tipo else ""
        if tipo == "Quilometragem":
            valor = round(km * TARIFA_KM, 2)
            if rng.random() < 0.05:
                valor = round(valor * 1.15, 2)                              # divergência plantada
        else:
            valor = round({"Alimentação": rng.uniform(25, 120), "Hospedagem": rng.uniform(180, 420),
                           "Pedágio": rng.uniform(6, 45)}.get(tipo, km * rng.uniform(0.55, 0.75)), 2)
        envio = d + timedelta(days=rng.choice([0, 1, 2, 3, 5, 8, 15, 32]))
        aprov = envio + timedelta(days=rng.randint(0, 6))
        pag = aprov + timedelta(days=rng.randint(1, 5))
        reemb.append([rid, rng.choice(COLABS), rng.choice(PAS), d, envio, aprov, pag if pag <= date(2026, 10, 31) else "",
                      tipo, veiculo, km, valor]); rid += 1
    w(p, "reembolsos.csv", ["id", "colaborador", "pa", "data_despesa", "data_envio", "data_aprovacao", "data_pagamento",
                            "tipo", "veiculo", "km", "valor"], reemb)

    # ---------------- cartões pré-pagos
    creditos, compras, prest, baixas, ff = [], [], [], [], []
    cid = 1
    for mes in range(1, 11):
        total_mes = 0.0
        for pa in PAS:
            credito = rng.choice([800, 900, 1000, 1100])
            creditos.append([date(2026, mes, 1), pa, credito, 300.00, credito - 300.00])
            total_mes += credito
            gasto_man = 0.0
            for _ in range(rng.randint(3, 9)):
                man = rng.random() < 0.3
                v = round(rng.uniform(20, 75) if man else rng.uniform(25, 200), 2)
                if man and pa == "05":
                    v = round(v * 3.5, 2)                                   # PA que estoura manutenção (plantado)
                cat = rng.choice(CATEG_MAN if man else CATEG_ADM)
                dia = date(2026, mes, rng.randint(1, 28))
                compras.append([cid, dia, pa, "Manutenção" if man else "Despesa administrativa", cat, v,
                                "Sim" if rng.random() > 0.04 else "Não"])
                # baixa no sistema: a maioria baixada; o mês mais recente fica parcialmente pendente
                if rng.random() < (0.55 if mes == 10 else 0.97):
                    baixas.append([cid, dia + timedelta(days=rng.randint(5, 25)), v])
                cid += 1
            # prestação de contas do mês: prazo dia 15 do mês seguinte
            prazo = date(2026 + (mes == 12), mes % 12 + 1, 15)
            atraso = rng.choice([0, 0, 0, 0, 0, -3, -7, 2, 5, 12]) + (6 if pa in ("08", "11") else 0)
            envio = prazo + timedelta(days=atraso)
            prest.append([f"2026-{mes:02d}", pa, prazo, envio if envio <= date(2026, 11, 10) else ""])
        ff.append([date(2026, mes, 1), "Crédito à plataforma", round(total_mes, 2)])
        if rng.random() < 0.4:
            ff.append([date(2026, mes, 28), "Devolução da plataforma", round(rng.uniform(100, 600), 2)])
    w(p, "creditos_cartao.csv", ["competencia", "pa", "credito_total", "parcela_manutencao", "parcela_administrativa"], creditos)
    w(p, "compras_cartao.csv", ["compra_id", "data", "pa", "natureza", "categoria", "valor", "comprovante"], compras)
    w(p, "prestacoes.csv", ["competencia", "pa", "prazo", "data_envio"], prest)
    w(p, "baixas_sistema.csv", ["compra_id", "data_baixa", "valor"], baixas)
    w(p, "fundo_fixo.csv", ["data", "movimento", "valor"], ff)
    print(f"{len(reemb)} reembolsos, {len(compras)} compras em cartão, {len(baixas)} baixas -> {p}")


if __name__ == "__main__":
    main()
