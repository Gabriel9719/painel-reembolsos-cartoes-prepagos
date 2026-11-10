"""python -m despesas  ->  lê data/bruto, aplica as regras e grava data/processado (entrada do Power BI)."""
from pathlib import Path

from .regras import processar

t = processar(Path("data/bruto"), Path("data/processado"))
r, m, p, f = t["fReembolso"], t["fUsoManutencao"], t["fPrestacao"], t["fFundoFixo"]
print(f"Reembolsos: {len(r)} | R$ {r['valor'].sum():,.2f} | alertas de km: {int(r['alerta_km'].sum())} | "
      f"fora do prazo de envio: {int(r['fora_do_prazo_envio'].sum())}")
print(f"PA/mês que estouraram o limite de manutenção: {int(m['estourou_limite'].sum())} "
      f"(PAs: {', '.join(sorted(m.loc[m['estourou_limite'], 'pa'].unique()))})")
print("Prestações:", p["status"].value_counts().to_dict())
print(f"Falta baixar no sistema: R$ {f['falta_baixar'].sum():,.2f} | saldo acumulado do fundo fixo: R$ {f['saldo_acumulado'].iloc[-1]:,.2f}")
