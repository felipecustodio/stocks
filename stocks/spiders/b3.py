import scrapy
import pandas as pd
from io import StringIO


class B3FIISpider(scrapy.Spider):
    name = "b3_fii"
    allowed_domains = ["www.b3.com.br"]
    start_urls = [
        "http://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/fundos-de-investimentos/fii/fiis-listados/"
    ]

    def parse(self, response):

        import pdbr
        pdbr.set_trace()

        string_io_response = StringIO(response.text)
        df = pd.read_html(string_io_response, thousands=None)[0]
        stocks = df.to_dict(orient="records")
        for stock in stocks:
            yield stock
