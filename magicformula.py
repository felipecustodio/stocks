from rich import print
import pandas as pd

filtro_setores = ["Financeiros", "Holdings Diversificadas",
                    "Previdência e Seguros", "Serviços Financeiros Diversos"]

stocks = pd.read_json("fundamentus.json")
print(stocks.columns)

print("Filter by liquidity...")
filtered_stocks = stocks[stocks["Liq.2meses"] >= 150000]

print("Filter by Ebit...")
filtered_stocks = filtered_stocks[
    filtered_stocks["Oscilações"].apply(lambda x: x.get("Marg. EBIT", float("-inf")))
    > 0
]

print("Rank by EV / EBIT...")
filtered_stocks["EV / EBIT"] = filtered_stocks["Indicadores fundamentalistas"].apply(
    lambda x: x.get("EV / EBIT", float("inf"))
)

filtered_stocks.sort_values(
    by="EV / EBIT",
    axis=0,
    ascending=True,
    inplace=True,
    kind="mergesort",
    na_position="last",
)

filtered_stocks.drop(columns=['EV / EBIT'], inplace=True)

filtered_stocks["Rank EV / EBIT"] = (
    filtered_stocks["Indicadores fundamentalistas"]
    .apply(lambda x: x["EV / EBIT"])
    .rank(method="min")
)

print("Rank by ROIC...")
filtered_stocks["ROIC"] = filtered_stocks["Oscilações"].apply(
    lambda x: x.get("ROIC", float("inf"))
)

filtered_stocks.sort_values(
    by="ROIC",
    axis=0,
    ascending=True,
    inplace=True,
    kind="mergesort",
    na_position="last",
)

filtered_stocks.drop(columns=["ROIC"], inplace=True)

filtered_stocks["Rank ROIC"] = (
    filtered_stocks["Oscilações"].apply(lambda x: x.get("ROIC")).rank(method="max")
)

print("Generate Magic Formula ranking...")

filtered_stocks["Rank Magic Formula"] = (
    filtered_stocks["Rank EV / EBIT"] + filtered_stocks["Rank ROIC"]
).astype(int)

filtered_stocks.sort_values("Rank Magic Formula", axis=0, ascending=True,
                            inplace=True, kind="mergesort", na_position="last")

# print("Filter by sector...")
# filtered_stocks = filtered_stocks[~filtered_stocks["Setor"].isin(
#     filtro_setores)]

filtered_stocks.to_json("magicformula.json", orient="records", force_ascii=False, indent=4)
