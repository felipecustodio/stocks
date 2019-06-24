#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""magic.py: Applies magic formula to stock list."""

__author__  = "Felipe Scrochio Custódio"
__email__   = "felipe.crochi@gmail.com"

import re
import pandas as pd
import pygsheets
from tqdm import tqdm
import math
from logzero import logger


url_fundamentus = "http://www.fundamentus.com.br/resultado.php"
url_papel = "http://www.fundamentus.com.br/detalhes.php?papel="
setores_financeiros = ["financeiros", "holdings diversificadas", "previdência e seguros", "serviços financeiros diversos"]


logger.debug("Lendo a tabela de ações da Fundamentus...")
try:
    stocks = pd.read_html(url_fundamentus, thousands=None)[0]
    logger.info("Tabela de ações lida com sucesso.")
except Exception as e:
    logger.exception(e)

logger.debug("Limpeza dos dados...")
for column in stocks:
    if (column != "Papel"):
        try:
            stocks[column] = stocks[column].map(lambda x: x.replace('%', ''))
            stocks[column] = stocks[column].map(lambda x: x.replace('.', ''))
            stocks[column] = stocks[column].map(lambda x: x.replace(',', '.'))
            stocks[column] = pd.to_numeric(stocks[column])
        except Exception as e:
            logger.exception(e)
logger.info("Limpeza dos dados concluída.")

logger.debug("Buscando informações sobre os papéis...")
pbar = tqdm(stocks["Papel"])
tipos = []
empresas = []
setores = []
for papel in pbar:
    pbar.set_description("Processando papel %s" % papel)
    try:
        info = pd.read_html(url_papel + papel)[0]
    except Exception as e:
        logger.exception(e)
    tipos.append(info[1][1])
    empresas.append(info[1][2])
    setores.append(info[1][3])
logger.info("Informações sobre os papéis obtidas.")

stocks["Tipo"] = tipos
stocks["Empresa"] = empresas
stocks["Setor"] = setores

logger.debug("Removendo empresas com liquidez inferior à R$150.000...")
try:
    stocks_magic = stocks[stocks["Liq.2meses"] >= 150000]
    logger.info("Empresas removidas com sucesso.")
except Exception as e:
    logger.exception(e)

logger.debug("Removendo empresas com Margem Ebit negativa ou zerada...")
try:
    stocks_magic = stocks_magic[stocks_magic["Mrg Ebit"] > 0]
    logger.info("Empresas removidas com sucesso.")
except Exception as e:
    logger.exception(e)

logger.debug("Gerando rank EV/Ebit...")
try:
    stocks.sort_values("EV/EBIT", axis=0, ascending=True, inplace=True, kind='quicksort', na_position='last')
    stocks_magic["Rank EV/Ebit"] = stocks_magic["EV/EBIT"].rank(method="min")
    logger.info("Rank EV/Ebit gerado.")
except Exception as e:
    logger.exception(e)

logger.debug("Gerando rank ROIC...")
try:
    stocks_magic.sort_values("ROIC", axis=0, ascending=False, inplace=True, kind='quicksort', na_position='last')
    stocks_magic["Rank ROIC"] = stocks_magic["ROIC"].rank(method="max")
    logger.info("Rank ROIC gerado.")
except Exception as e:
    logger.exception(e)

logger.debug("Gerando Magic Formula...")
try:
    stocks_magic['MagicFormula'] = (stocks_magic['Rank EV/Ebit'] + stocks_magic['Rank ROIC']).astype(int)
    stocks_magic.sort_values('MagicFormula', axis=0, ascending=True, inplace=True, kind='quicksort', na_position='last')
    logger.info("Magic Formula gerada.")
except Exception as e:
    logger.exception(e)

logger.debug("Removendo empresas do setor financeiro...")
try:
    stocks_magic = stocks_magic[stocks_magic["Setor"].lower() not in setores_financeiros]
    logger.info("Empresas removidas.")
except Exception as e:
    logger.exception(e)

logger.debug("Gerando carteira de investimentos...")
try:
    carteira = stocks_magic.head(30)[['Papel', 'Tipo', 'Empresa', 'Setor']]
    carteira.to_json(r'carteira.json')
except Exception as e:
    logger.exception(e)
logger.info("Carteira de investimentos gerada.")

logger.debug("Autenticando com Google Sheets...")
try:
    gc = pygsheets.authorize(service_file='credentials.json')
    logger.info("Autenticação concluída.")
except Exception as e:
    logger.exception(e)

logger.debug("Abrindo planilha...")
try:
    sh = gc.open('Stocks')
    logger.info("Planilha aberta.")
except Exception as e:
    logger.exception(e)

stocks_sheet = sh[0]
magic_sheet = sh[1]
carteira_sheet = sh[2]

logger.debug("Escrevendo dados na planilha...")
try:
    stocks_sheet.set_dataframe(stocks,(1,1))
    magic_sheet.set_dataframe(stocks_magic,(1,1))
    carteira_sheet.set_dataframe(carteira, (1,1))
    logger.info("Dados escritos com sucesso!")
except Exception as e:
    logger.exception(e)
