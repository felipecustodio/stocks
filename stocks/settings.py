import copy

import scrapy.utils.log
from colorlog import ColoredFormatter

BOT_NAME = "stocks"
SPIDER_MODULES = ["stocks.spiders"]
NEWSPIDER_MODULE = "stocks.spiders"

SPIDERMON_ENABLED = True
EXTENSIONS = {
    "spidermon.contrib.scrapy.extensions.Spidermon": 500,
}

color_formatter = ColoredFormatter(
    (
        "%(log_color)s%(levelname)-5s%(reset)s "
        "%(yellow)s[%(asctime)s]%(reset)s"
        "%(white)s %(name)s %(funcName)s %(bold_purple)s:%(lineno)d%(reset)s "
        "%(log_color)s%(message)s%(reset)s"
    ),
    datefmt="%y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "blue",
        "INFO": "bold_cyan",
        "WARNING": "red",
        "ERROR": "bg_bold_red",
        "CRITICAL": "red,bg_white",
    },
)

_get_handler = copy.copy(scrapy.utils.log._get_handler)


def _get_handler_custom(*args, **kwargs):
    handler = _get_handler(*args, **kwargs)
    handler.setFormatter(color_formatter)
    return handler


scrapy.utils.log._get_handler = _get_handler_custom

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "stocks (+http://www.yourdomain.com)"

ROBOTSTXT_OBEY = True

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
}

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
