import json
import os
import pathlib
import smtplib
import ssl
import typing

import httpx
import pydantic

FMP_API_URL = 'https://financialmodelingprep.com/api/v3'
API_KEY_PARAM = {'apikey': os.environ['API_KEY']}
CONFIG_PATH = pathlib.Path('./src/config.json')


class Quote(pydantic.BaseModel):
    symbol: str
    name: str
    price: float
    priceAvg200: float
    timestamp: int


class ContactInfo(pydantic.BaseModel):
    email: str


class Config(pydantic.BaseModel):
    tickers: typing.List[str]
    contact_info: ContactInfo


async def stock_alert():
    config = _load_config()
    # quotes = await _get_all_quotes(config.tickers)
    # for quote in quotes:
    # if _should_notify(quote):
    #     await _notify(quote, config.contact_info)
    if True:
        _send_email('bla', 'bla')


def _load_config() -> Config:
    return Config.parse_obj(json.loads(CONFIG_PATH.read_text()))


async def _get_all_quotes(tickers: typing.List[str]) -> typing.List[Quote]:
    quotes = list()
    async with httpx.AsyncClient(base_url=FMP_API_URL) as fmp_client:
        for ticker in tickers:
            raw_response = await fmp_client.get(f'/quote/{ticker}', params=API_KEY_PARAM)
            raw_response.raise_for_status()
            quotes.append(Quote.parse_obj(raw_response.json()[0]))
    return quotes


async def _should_notify(quote: Quote) -> bool:
    return quote.price <= 0.8 * quote.priceAvg200


async def _notify(quote: Quote, contact_info: ContactInfo):
    pass


def _send_email(email_address: str, content: str):
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp_connection:
        smtp_connection.login("thestockalertapp@gmail.com", 'Dann12345!')
        smtp_connection.sendmail(
            'thestockalertapp@gmail.com', 'thestockalertapp@gmail.com', """
                                 Subject: Stock Alert
                                 
                                 Notice! this is an alert""")
