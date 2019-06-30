#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""magic.py - Seleciona as melhores ações baseadas na Magic Formula de Joel Greenblatt
e no método Clube do Valor de Ramiro Gomes, métodos apresentados no curso
DMA - Descomplicando o Mercado de Ações."""

__author__  = "Felipe Scrochio Custódio"
__email__   = "felipe.crochi@gmail.com"

import re
import pandas as pd
import pygsheets
from tqdm import tqdm
import math
from halo import Halo
import logzero
from logzero import logger
logzero.logfile("logfile.log", maxBytes=1e6, backupCount=3)

url_fundamentus = "http://www.fundamentus.com.br/resultado.php"
url_papel = "http://www.fundamentus.com.br/detalhes.php?papel="
filtro_setores = ["Financeiros", "Holdings Diversificadas", "Previdência e Seguros", "Serviços Financeiros Diversos"]
hyperlink_formula = "=HYPERLINK(CONCATENATE(\"http://www.fundamentus.com.br/detalhes.php?papel=\", A2),A2)"

carteira_clube_anterior = pd.read_json("carteira_clube.json")
carteira_magic_anterior = pd.read_json("carteira_magic.json")


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
try:
    stocks_info = pd.read_json("stocks_info.json")
    stocks = (stocks.merge(stocks_info, left_on='Papel', right_on='Papel'))
    logger.info("Informações sobre os papéis obtidas.")
except Exception as e:
    logger.exception(e)

logger.debug("Removendo empresas do setor financeiro...")
try:
    stocks = stocks[~stocks["Setor"].isin(filtro_setores)]
    logger.info("Empresas removidas com sucesso.")
except Exception as e:
    logger.exception(e)

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
    stocks.sort_values("EV/EBIT", axis=0, ascending=True, inplace=True, kind='mergesort', na_position='last')
    stocks_magic["Rank EV/Ebit"] = stocks_magic["EV/EBIT"].rank(method="min")
    logger.info("Rank EV/Ebit gerado.")
except Exception as e:
    logger.exception(e)

logger.debug("Gerando planilha Clube do Valor...")
try:
    stocks_clube = stocks_magic.copy(deep=True)
    stocks_clube.sort_values('Rank EV/Ebit', axis=0, ascending=True, inplace=True, kind='mergesort', na_position='last')
    logger.info("Planilha Clube do Valor completa.")
except Exception as e:
    logger.exception(e)

logger.debug("Gerando rank ROIC...")
try:
    stocks_magic.sort_values("ROIC", axis=0, ascending=False, inplace=True, kind='mergesort', na_position='last')
    stocks_magic["Rank ROIC"] = stocks_magic["ROIC"].rank(method="max")
    logger.info("Rank ROIC gerado.")
except Exception as e:
    logger.exception(e)

logger.debug("Gerando planilha Magic Formula...")
try:
    stocks_magic['MagicFormula'] = (stocks_magic['Rank EV/Ebit'] + stocks_magic['Rank ROIC']).astype(int)
    stocks_magic.sort_values('MagicFormula', axis=0, ascending=True, inplace=True, kind='mergesort', na_position='last')
    logger.info("Planilha Magic Formula completa.")
except Exception as e:
    logger.exception(e)

logger.debug("Gerando carteiras de investimentos...")
try:
    carteira_magic = stocks_magic.head(30)[['Papel', 'Tipo', 'Empresa', 'Setor']]
    carteira_clube = stocks_clube.head(30)[['Papel', 'Tipo', 'Empresa', 'Setor']]
    acoes_em_comum = pd.merge(carteira_magic, carteira_clube, how='inner')
    carteira_magic.to_json(r'carteira_magic.json')
    carteira_clube.to_json(r'carteira_clube.json')
    acoes_em_comum.to_json(r'acoes_em_comum.json')
except Exception as e:
    logger.exception(e)
logger.info("Carteiras de investimentos gerada.")

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
clube_sheet = sh[2]
carteira_magic_sheet = sh[3]
carteira_clube_sheet = sh[4]
acoes_em_comum_sheet = sh[5]

logger.debug("Escrevendo dados na planilha...")
try:
    stocks_sheet.set_dataframe(stocks,(1,1))
    magic_sheet.set_dataframe(stocks_magic,(1,1))
    clube_sheet.set_dataframe(stocks_clube,(1,1))
    carteira_magic_sheet.set_dataframe(carteira_magic, (1,1))
    carteira_clube_sheet.set_dataframe(carteira_clube, (1,1))
    acoes_em_comum_sheet.set_dataframe(acoes_em_comum, (1,1))
    logger.info("Dados escritos com sucesso!")
except Exception as e:
    logger.exception(e)
