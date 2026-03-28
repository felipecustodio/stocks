import datetime as dt
from collections import defaultdict
from io import StringIO

import pandas as pd
import scrapy

from stocks import pipelines as strategy_pipelines
from stocks.pipelines import ScreeningPipeline


def _build_item_pipelines() -> dict[str, int]:
    item_pipelines = {
        "stocks.pipelines.CleanValuesPipeline": 300,
        "stocks.pipelines.NormalizeValuesPipeline": 400,
        "stocks.pipelines.DateValuesPipeline": 500,
        "stocks.pipelines.NanValuesPipeline": 600,
        "stocks.pipelines.DataSourcesPipeline": 650,
        "stocks.pipelines.AnomalyDetectionPipeline": 660,
    }

    strategy_classes = []
    for obj in vars(strategy_pipelines).values():
        if (
            isinstance(obj, type)
            and issubclass(obj, ScreeningPipeline)
            and obj is not ScreeningPipeline
            and getattr(obj, "output_path", None)
        ):
            strategy_classes.append(obj)

    for strategy_cls in sorted(strategy_classes, key=lambda cls: cls.__name__):
        item_pipelines[f"{strategy_cls.__module__}.{strategy_cls.__name__}"] = 700

    return item_pipelines


class FundamentusSpider(scrapy.Spider):
    name = "fundamentus"
    allowed_domains = ["www.fundamentus.com.br"]
    start_urls = ["http://www.fundamentus.com.br/resultado.php"]
    stock_url_base = "https://www.fundamentus.com.br/detalhes.php?papel={}"

    table_details_mapping = {
        "Mrg Ebit": "Marg. EBIT",
        "Mrg. Líq.": "Marg. Líquida",
        "EV/EBIT": "EV / EBIT",
        "EV/EBITDA": "EV / EBITDA",
        "P/Cap.Giro": "P/Cap. Giro",
        "P/Ativ Circ.Liq": "P/Ativ Circ Liq",
        "Div.Yield": "Div. Yield",
        "Cresc. Rec.5a": "Cres. Rec (5a)",
        "Liq. Corr.": "Liquidez Corr",
    }

    custom_settings = {
        "ITEM_PIPELINES": _build_item_pipelines(),
        "FEEDS": {
            "data/raw/fundamentus.json": {
                "format": "json",
                "encoding": "utf8",
                "store_empty": True,
                "indent": 4,
                "overwrite": True,
            }
        },
    }

    def start_requests(self):
        if hasattr(self, "stock_url"):
            yield scrapy.Request(str(self.stock_url), callback=self.parse_details)
            return

        yield scrapy.Request(self.start_urls[0], callback=self.parse)

    def parse(self, response):
        string_io_response = StringIO(response.text)
        df = pd.read_html(string_io_response, thousands=None)[0]
        stocks = df.to_dict(orient="records")
        for stock in stocks:
            for key in list(stock.keys()):
                if key in self.table_details_mapping:
                    stock[self.table_details_mapping[key]] = stock.pop(key)
            details_url = self.stock_url_base.format(stock["Papel"])
            stock["URL"] = details_url
            yield scrapy.Request(
                details_url,
                callback=self.parse_details,
                meta={"stock": stock},
            )

    def parse_details(self, response):
        stock = response.meta.get("stock", {})

        tables = response.xpath("//table")
        for table in tables:

            removed_keys = []

            table_headers = table.xpath(".//td[contains(@class, 'nivel1')]//text()").getall()
            table_headers_2 = table.xpath(".//td[contains(@class, 'nivel2')]//text()").getall()

            rows = table.xpath(".//tr")
            all_row_values = []

            for row in rows:
                keys = row.xpath(".//td[contains(@class, 'label')]//text()").getall()
                keys = [key for key in keys if key.strip() not in ["?"]]
                values = row.xpath(".//td[contains(@class, 'data')]//text()").getall()
                values = [value for value in values if value.strip() != "\n" and value.strip() != ""]
                row_values = defaultdict(list)
                for key, value in zip(keys, values, strict=False):
                    if key in self.table_details_mapping:
                        key = self.table_details_mapping[key]

                    row_values[key].append(value)

                all_row_values.append(row_values)

            if table_headers and not table_headers_2:
                stock.update({header: defaultdict(dict) for header in table_headers})

                for row_values in all_row_values:
                    for index, (key, values) in enumerate(row_values.items()):
                        for value in values:
                            header_index = index % len(table_headers)
                            header = table_headers[header_index]
                            if key in stock:
                                stock.pop(key)
                                removed_keys.append(key)
                            stock[header][key] = value

            elif table_headers and table_headers_2:
                for header1 in table_headers:
                    stock[header1] = defaultdict(dict)
                    for header2 in table_headers_2:
                        stock[header1][header2] = defaultdict(dict)
                for row_values in all_row_values:
                    if not row_values:
                        continue

                    for _index1, header1 in enumerate(table_headers):
                        for index2, header2 in enumerate(table_headers_2):
                            key = next(iter(row_values.keys()))
                            value = row_values[key][index2]
                            if key in stock:
                                stock.pop(key)
                                removed_keys.append(key)
                            stock[header1][header2][key] = value

            else:
                for row_values in all_row_values:
                    for key, values in row_values.items():
                        if key in removed_keys:
                            continue
                        else:
                            stock[key] = values[0]

        stock["Data"] = dt.datetime.now().strftime("%d/%m/%Y")
        yield stock
