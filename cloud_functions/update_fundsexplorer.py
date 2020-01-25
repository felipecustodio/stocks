from urllib.request import urlopen, Request
from google.cloud import storage
import re
import pandas as pd
import numpy as np
import json
from flask import escape


def update_fundsexplorer(request):
    print("Initializing Storage...")
    try:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket('carteiras')
        fundsexplorer = bucket.blob('fundsexplorer.json')
    except Exception as e:
        print(e)
        return str(e)


    url_ranking = "https://www.fundsexplorer.com.br/ranking"
    columns_ranking = ["Código do Fundo", "Setor", "Preço Atual", "Liquidez Diária", "Dividendo", "Dividend Yield", "DY (3M) Acumulado", "DY (6M) Acumulado", "DY (12M) Acumulado", "DY (3M) Média", "DY (6M) Média", "DY (12M) Média", "DY Ano", "Variação Preço",
                    "Rentab. Período", "Rentab. Acumulada", "Patrimônio Líq.", "VPA", "P/VPA", "DY Patrimonial", "Variação Patrimonial", "Rentab. Patr. no Período", "Rentab. Patr. Acumulada", "Vacância Física", "Vacância Financeira", "Quantidade Ativos"]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'}


    print("Reading funds table...")
    try:
        req_ranking = Request(url=url_ranking, headers=headers)
        html_ranking = urlopen(req_ranking).read()

        funds = pd.read_html(html_ranking, thousands=None)[0]
        funds.columns = columns_ranking
        funds = funds.replace(np.nan, '', regex=True)
        funds = funds.astype(str)
    except Exception as e:
        print(e)
        return str(e)

    print("Data cleanup...")
    for column in funds:
        if (column != "Código do Fundo" and column != "Setor"):
            try:
                funds[column] = funds[column].map(
                    lambda x: x.replace('R$', ''))
                funds[column] = funds[column].map(
                    lambda x: x.replace('%', ''))
                funds[column] = funds[column].map(
                    lambda x: x.replace('.', ''))
                funds[column] = funds[column].map(
                    lambda x: x.replace(',', '.'))
                funds[column] = pd.to_numeric(funds[column])
                funds[column] = funds[column].astype(str)
                funds[column] = funds[column].map(
                    lambda x: x.replace('nan', ''))
            except Exception as e:
                print(e)
                return str(e)

    print("Uploading to Storage...")
    try:
        data = []
        for jdict in funds.to_dict(orient='records'):
            data.append(jdict)
        fundsexplorer.upload_from_string(json.dumps(data))
        return json.dumps(data)
    except Exception as e:
        print(e)
        return str(e)
