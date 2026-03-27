"""
WIP: B3 FII spider.

This spider is incomplete and not yet functional.
It should scrape FII (Fundos de Investimento Imobiliário) listings from B3.
"""

from io import StringIO

import pandas as pd
import scrapy


class B3FIISpider(scrapy.Spider):
    name = "b3_fii"
    allowed_domains = ["www.b3.com.br"]
    start_urls = [
        "http://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/fundos-de-investimentos/fii/fiis-listados/"
    ]

    custom_settings = {
        "FEEDS": {
            "data/raw/b3_fii.json": {
                "format": "json",
                "encoding": "utf8",
                "store_empty": True,
                "indent": 4,
                "overwrite": True,
            }
        },
    }

    def parse(self, response):
        # TODO: B3 FII page loads data via JavaScript/iframe.
        # Need to handle dynamic content (e.g. Splash or Playwright middleware).
        string_io_response = StringIO(response.text)
        df = pd.read_html(string_io_response, thousands=None)[0]
        stocks = df.to_dict(orient="records")
        yield from stocks
