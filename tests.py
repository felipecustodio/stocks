import re
import pandas as pd
import pygsheets
from tqdm import tqdm
import math

from pprint import pprint

# from logzero import logger
# import logzero
# logzero.logfile("logfile_updater.log", maxBytes=1e6, backupCount=3)


url_fundamentus = "http://www.fundamentus.com.br/resultado.php"
url_papel = "http://www.fundamentus.com.br/detalhes.php?papel="
filtro_setores = ["Financeiros", "Holdings Diversificadas", "Previdência e Seguros", "Serviços Financeiros Diversos"]

papel = 'POSI3'
info = pd.read_html(url_papel + papel)

pprint(info[3])

# tipos.append(info[1][1])
# empresas.append(info[1][2])
# setores.append(info[1][3])