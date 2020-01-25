from google.cloud import storage
import re
import pandas as pd
from flask import escape

def update_stocks_info(request):
    print("Initializing Storage...")
    try:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket('carteiras')
        blob = bucket.blob('stocks_info.json')
    except Exception as e:
        print(e)
        return str(e)

    url_fundamentus = "http://www.fundamentus.com.br/resultado.php"
    url_papel = "http://www.fundamentus.com.br/detalhes.php?papel="

    print("Reading stocks table...")
    try:
        stocks = pd.read_html(url_fundamentus, thousands=None)[0]
    except Exception as e:
        print(e)
        return str(e)

    print("Data cleanup...")
    for column in stocks:
        if (column != "Papel"):
            try:
                stocks[column] = stocks[column].map(lambda x: x.replace('%', ''))
                stocks[column] = stocks[column].map(lambda x: x.replace('.', ''))
                stocks[column] = stocks[column].map(lambda x: x.replace(',', '.'))
                stocks[column] = pd.to_numeric(stocks[column])
            except Exception as e:
                print(e)
                return str(e)

    print("Scraping stocks info...")
    tipos = []
    empresas = []
    setores = []

    for papel in stocks["Papel"]:
        try:
            info = pd.read_html(url_papel + papel)[0]
            tipos.append(info[1][1])
            empresas.append(info[1][2])
            setores.append(info[1][3])
        except Exception as e:
            print(e)
            return str(e)

    stocks["Tipo"] = tipos
    stocks["Empresa"] = empresas
    stocks["Setor"] = setores

    print("Uploading to Storage...")
    try:
        stocks_info = stocks[['Papel', 'Tipo', 'Empresa', 'Setor']]
        json_data = stocks_info.to_json()
        blob.upload_from_string(json_data)
        return str(json_data)
    except Exception as e:
        print(e)
        return str(e)
