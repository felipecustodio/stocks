from google.cloud import storage
import re
import pandas as pd
import json
from flask import escape


def update_fundamentus(request):
    print("Initializing Storage...")
    try:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket('carteiras')
        fundamentus = bucket.blob('fundamentus.json')
        stocks_info = bucket.blob('stocks_info.json')
    except Exception as e:
        print(e)
        return str(e)

    url_fundamentus = "http://www.fundamentus.com.br/resultado.php"

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
                stocks[column] = stocks[column].map(
                    lambda x: x.replace('%', ''))
                stocks[column] = stocks[column].map(
                    lambda x: x.replace('.', ''))
                stocks[column] = stocks[column].map(
                    lambda x: x.replace(',', '.'))
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

    print("Uploading to Storage...")
    try:
        data = []
        for jdict in stocks.to_dict(orient='records'):
            data.append(jdict)
        fundamentus.upload_from_string(json.dumps(data))
        return json.dumps(data)
    except Exception as e:
        print(e)
        return str(e)
