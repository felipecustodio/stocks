from google.cloud import storage
import re
import pandas as pd
import json
from flask import escape


def update_intersection(request):
    print("Initializing Storage...")
    try:
        storage_client = storage.Client()
        bucket = storage_client.get_bucket('carteiras')
        portfolio_magicformula = bucket.blob('portfolio_magicformula.json')
        portfolio_cdv = bucket.blob('portfolio_cdv.json')
        portfolio_intersection = bucket.blob('portfolio_intersection.json')
    except Exception as e:
        print(e)
        return str(e)

    print("Downloading portfolios...")
    try:
        portfolio_magicformula = pd.read_json(
            portfolio_magicformula.download_as_string())
        portfolio_cdv = pd.read_json(
            portfolio_cdv.download_as_string())
    except Exception as e:
        print(e)
        return str(e)

    print("Finding intersection...")
    try:
        intersection = pd.merge(portfolio_magicformula, portfolio_cdv, how="inner")[
            ["Papel", "Tipo", "Empresa", "Setor"]]
    except Exception as e:
        print(e)
        return str(e)
    
    print("Uploading to Storage...")
    try:
        data = []
        for jdict in intersection.to_dict(orient='records'):
            data.append(jdict)
        portfolio_intersection.upload_from_string(json.dumps(data))
        return json.dumps(data)
    except Exception as e:
        print(e)
        return str(e)
