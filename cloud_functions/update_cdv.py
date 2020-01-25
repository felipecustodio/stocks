from google.cloud import storage
import re
import json
import pandas as pd
from flask import escape


def update_cdv(request):
    print("Initializing Storage...")
    try:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket('carteiras')
        portfolio = bucket.blob('portfolio_cdv.json')
        stocks_info = bucket.blob('stocks_info.json')
    except Exception as e:
        print(e)
        return str(e)

    url_fundamentus = "http://www.fundamentus.com.br/resultado.php"

    filtro_setores = ["Financeiros", "Holdings Diversificadas",
                      "Previdência e Seguros", "Serviços Financeiros Diversos"]

    print("Downloading current portfolio...")
    current_portfolio = pd.read_json(portfolio.download_as_string())

    print("Reading stocks table...")
    try:
        stocks = pd.read_html(url_fundamentus, thousands=None)[0]
    except Exception as e:
        print(e)
        return str(e)

    print("Parsing stocks info...")
    for column in stocks:
        if (column != "Papel"):
            try:
                stocks[column] = stocks[column].map(
                    lambda x: x.replace("%", ""))
                stocks[column] = stocks[column].map(
                    lambda x: x.replace(".", ""))
                stocks[column] = stocks[column].map(
                    lambda x: x.replace(",", "."))
                stocks[column] = pd.to_numeric(stocks[column])
            except Exception as e:
                print(e)
                return str(e)

    print("Merge stocks info...")
    try:
        stocks_info = pd.read_json(stocks_info.download_as_string())
        stocks = (stocks.merge(stocks_info, left_on="Papel", right_on="Papel"))
    except Exception as e:
        print(e)
        return str(e)

    print("Filter by liquidity...")
    try:
        filtered_stocks = stocks[stocks["Liq.2meses"] >= 150000]
    except Exception as e:
        print(e)
        return str(e)

    print("Filter by Ebit...")
    try:
        filtered_stocks = filtered_stocks[filtered_stocks["Mrg Ebit"] > 0]
    except Exception as e:
        print(e)
        return str(e)

    print("Rank by EV/Ebit...")
    try:
        filtered_stocks.sort_values("EV/EBIT", axis=0, ascending=True,
                                    inplace=True, kind="mergesort", na_position="last")
        filtered_stocks["Rank EV/Ebit"] = filtered_stocks["EV/EBIT"].rank(
            method="min")
    except Exception as e:
        print(e)
        return str(e)

    print("Generating CDV ranking...")
    try:
        filtered_stocks = filtered_stocks.copy(deep=True)
        filtered_stocks.sort_values("Rank EV/Ebit", axis=0, ascending=True,
                                inplace=True, kind="mergesort", na_position="last")
    except Exception as e:
        print(e)
        return str(e)

    print("Filter by sector...")
    try:
        filtered_stocks = filtered_stocks[~filtered_stocks["Setor"].isin(
            filtro_setores)]
    except Exception as e:
        print(e)
        return str(e)

    print("Update portfolio...")
    try:
        updated_portfolio = filtered_stocks.head(
            30)[["Papel", "Tipo", "Empresa", "Setor", "Rank EV/Ebit"]]

        current_portfolio = current_portfolio[~current_portfolio["Status"].isin([
            "Saindo"])]

        for index, row in updated_portfolio.iterrows():
            if (current_portfolio["Papel"].str.contains(row["Papel"]).any()):
                updated_portfolio.at[index, "Status"] = "Mantém"
            else:
                updated_portfolio.at[index, "Status"] = "Nova"

        for index, row in current_portfolio.iterrows():
            if (~updated_portfolio["Papel"].str.contains(row["Papel"]).any()):
                row["Status"] = "Saindo"
                updated_portfolio.loc[updated_portfolio.shape[0]] = row
    except Exception as e:
        print(e)
        return str(e)

    print("Uploading to Storage...")
    try:
        data = []
        for jdict in updated_portfolio.to_dict(orient='records'):
            data.append(jdict)
        portfolio.upload_from_string(json.dumps(data))
        return json.dumps(data)
    except Exception as e:
        print(e)
        return str(e)
