"""Mockup das páginas do painel a partir de data/processado (dados fictícios)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
P = RAIZ / "data/processado"
AZUL, VERDE, VERM, CINZA, FUNDO = "#003641", "#00AE9D", "#C0392B", "#7F8C8D", "#F4F7F8"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out"]


def brl(v):
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def ler(n):
    return pd.read_csv(P / f"{n}.csv", sep=";", dtype={"pa": str})


r, m, pr, ff, cc = ler("fReembolso"), ler("fUsoManutencao"), ler("fPrestacao"), ler("fFundoFixo"), ler("fCompraCartao")
fig = plt.figure(figsize=(16, 9), facecolor=FUNDO)
fig.text(0.03, 0.94, "Reembolsos e cartões pré-pagos", fontsize=24, fontweight="bold", color=AZUL)
fig.text(0.03, 0.905, "jan–out/2026 · dados fictícios · mockup gerado em Python", fontsize=11, color=CINZA)
fechadas = pr[pr["status"] != "Aguardando (no prazo)"]
kpis = [("Reembolsos", brl(r["valor"].sum()), AZUL),
        ("Veículo alugado", brl(r.loc[r["veiculo_alugado"], "valor"].sum()), AZUL),
        ("Alertas de km", str(int(r["alerta_km"].sum())), VERM),
        ("Prestações no prazo", f"{(fechadas['status'] == 'No prazo').mean():.0%}", VERDE),
        ("Falta baixar no sistema", brl(ff["falta_baixar"].sum()), VERM)]
for i, (rot, val, cor) in enumerate(kpis):
    ax = fig.add_axes([0.03 + i * 0.19, 0.74, 0.175, 0.13]); ax.set_facecolor("white")
    ax.set_xticks([]); ax.set_yticks([]); [s.set_color("#DDE3E6") for s in ax.spines.values()]
    ax.text(0.06, 0.62, val, fontsize=19, fontweight="bold", color=cor, transform=ax.transAxes)
    ax.text(0.06, 0.22, rot, fontsize=11, color=CINZA, transform=ax.transAxes)

tipo = r.groupby("tipo")["valor"].sum().sort_values()
ax1 = fig.add_axes([0.17, 0.40, 0.30, 0.28]); ax1.set_facecolor("white")
ax1.barh(tipo.index, tipo.values / 1e3, color=AZUL); ax1.set_title("Reembolsos por tipo (R$ mil)", loc="left", color=AZUL, fontweight="bold")
ax1.spines[["top", "right"]].set_visible(False); ax1.tick_params(labelsize=9)

ax2 = fig.add_axes([0.56, 0.40, 0.41, 0.28]); ax2.set_facecolor("white")
x = range(len(ff))
ax2.bar([i - 0.2 for i in x], ff["gasto_cartoes"] / 1e3, width=0.4, color=AZUL, label="Gasto nos cartões")
ax2.bar([i + 0.2 for i in x], ff["baixado_sistema"] / 1e3, width=0.4, color=VERDE, label="Baixado no sistema")
ax2.set_xticks(list(x)); ax2.set_xticklabels(MESES[: len(ff)])
ax2.set_title("Fundo fixo: gasto × baixado (R$ mil)", loc="left", color=AZUL, fontweight="bold")
ax2.legend(frameon=False, fontsize=9); ax2.spines[["top", "right"]].set_visible(False)

atraso = pr.groupby("pa")["dias_atraso"].mean().sort_values(ascending=False).head(8)
ax3 = fig.add_axes([0.05, 0.06, 0.40, 0.26]); ax3.set_facecolor("white")
ax3.bar("PA " + atraso.index, atraso.values, color=[VERM if v > 3 else AZUL for v in atraso.values])
ax3.set_title("Atraso médio da prestação de contas (dias)", loc="left", color=AZUL, fontweight="bold")
ax3.spines[["top", "right"]].set_visible(False); ax3.tick_params(labelsize=9)

man = m.groupby("pa")["gasto_manutencao"].mean().sort_values(ascending=False).head(8)
ax4 = fig.add_axes([0.56, 0.06, 0.41, 0.26]); ax4.set_facecolor("white")
ax4.bar("PA " + man.index, man.values, color=[VERM if v > 300 else VERDE for v in man.values])
ax4.axhline(300, ls="--", color=VERM, lw=1); ax4.text(len(man) - 1.6, 310, "limite R$ 300", color=VERM, fontsize=9)
ax4.set_title("Manutenção: gasto médio mensal por PA (R$)", loc="left", color=AZUL, fontweight="bold")
ax4.spines[["top", "right"]].set_visible(False); ax4.tick_params(labelsize=9)
fig.savefig(RAIZ / "docs/mockup.png", dpi=110, facecolor=FUNDO)
print("docs/mockup.png")
