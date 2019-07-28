import re
import pandas as pd
import pygsheets
from tqdm import tqdm
import math
from logzero import logger
import logzero
logzero.logfile("logfile_updater.log", maxBytes=1e6, backupCount=3)


url_fundamentus = "http://www.fundamentus.com.br/resultado.php"
url_papel = "http://www.fundamentus.com.br/detalhes.php?papel="
filtro_setores = ["Financeiros", "Holdings Diversificadas", "Previdência e Seguros", "Serviços Financeiros Diversos"]


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
        print(info)
        tipos.append(info[1][1])
        empresas.append(info[1][2])
        setores.append(info[1][3])
    except Exception as e:
        logger.exception(e)
logger.info("Informações sobre os papéis obtidas.")

stocks["Tipo"] = tipos
stocks["Empresa"] = empresas
stocks["Setor"] = setores

logger.debug("Atualizando base de dados...")
try:
    stocks_info = stocks[['Papel', 'Tipo', 'Empresa', 'Setor']]
    stocks_info.to_json(r'stocks_info.json')
    logger.info("Base de dados atualizada!")
except Exception as e:
    logger.exception(e)