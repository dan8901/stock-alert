import json
import os
import pathlib
import smtplib
import ssl
import typing

import httpx
import pydantic
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import jinja2
import datetime

FMP_API_URL = 'https://financialmodelingprep.com/api/v3'
API_KEY_PARAM = {'apikey': os.environ['API_KEY']}
GMAIL_PASSWORD = os.environ['GMAIL_PASSWORD']
CONFIG_PATH = pathlib.Path('./src/config.json')
SMTP_PORT = 465
GMAIL_SMPT_SERVER_ADDRESS = 'smtp.gmail.com'
APP_EMAIL_ADDRESS = 'thestockalertapp@gmail.com'
LOGO_PATH = pathlib.Path('./images/logo.png')
EMAIL_SUBJECT = 'Stock price alert'
HTML_PATH = pathlib.Path('./src/index.html')
READABLE_DATETIME_FORMAT = '%B %d, %Y, %H:%M'

class Quote(pydantic.BaseModel):
    symbol: str
    name: str
    price: float
    priceAvg200: float
    timestamp: int


class ContactInfo(pydantic.BaseModel):
    name: str
    email: str


class Config(pydantic.BaseModel):
    tickers: typing.List[str]
    contact_info: ContactInfo
    price_drop_percentage_threshold: float


async def stock_alert():
    config = _load_config()
    quotes = await _get_all_quotes(config.tickers)
    for quote in quotes:
        if _should_notify(quote, config.price_drop_percentage_threshold):
            _notify(quote, config.contact_info)

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


def _should_notify(quote: Quote, price_drop_percentage_threshold: float) -> bool:
    return quote.price <= price_drop_percentage_threshold * quote.priceAvg200


def _notify(quote: Quote, contact_info: ContactInfo):
    html = _generate_html(contact_info.name, quote)
    _send_email(contact_info.email, html)


def _generate_html(name: str, quote: Quote) -> str:
    unformatted_html = HTML_PATH.read_text()
    html_data = {
        'name': name,
        'symbol': quote.symbol,
        'stock_name': quote.name,
        'datetime': datetime.datetime.fromtimestamp(quote.timestamp).strftime(READABLE_DATETIME_FORMAT),
        'price': quote.price,
        'price_200_day_avg': quote.priceAvg200
    }
    return jinja2.Template(unformatted_html).render(html_data)

def _send_email(email_address: str, html: str):
    message = MIMEMultipart()
    message['Subject'] = EMAIL_SUBJECT
    message['From'] = APP_EMAIL_ADDRESS
    message['To'] = email_address
    image_part = MIMEImage(LOGO_PATH.read_bytes())
    image_part.add_header('Content-ID', '<0>')
    message.attach(image_part)
    html_part = MIMEText(html, 'html')
    message.attach(html_part)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(GMAIL_SMPT_SERVER_ADDRESS, SMTP_PORT, context=context) as smtp_connection:
        smtp_connection.login(APP_EMAIL_ADDRESS, GMAIL_PASSWORD)
        smtp_connection.sendmail(APP_EMAIL_ADDRESS, email_address, message.as_string())
