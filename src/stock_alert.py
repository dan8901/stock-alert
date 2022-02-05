import json
import os
import pathlib
import smtplib
import ssl
import typing
import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
import jinja2
import pydantic

FMP_API_URL = 'https://financialmodelingprep.com/api/v3'
API_KEY_PARAM = {'apikey': os.environ['API_KEY']}
GMAIL_PASSWORD = os.environ['GMAIL_PASSWORD']
CONFIG_PATH = pathlib.Path('./src/config.json')
SMTP_PORT = 465
GMAIL_SMPT_SERVER_ADDRESS = 'smtp.gmail.com'
APP_EMAIL_ADDRESS = 'thestockalertapp@gmail.com'
LOGO_PATH = pathlib.Path('./static/logo.png')
EMAIL_SUBJECT = 'Stock price alert'
HTML_PATH = pathlib.Path('./static/email_template.html')
READABLE_DATETIME_FORMAT = '%B %d, %Y, %H:%M'
NUMBER_OF_DIGITS_TO_ROUND = 2


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
    symbols: typing.List[str]
    contact_info: ContactInfo
    price_drop_percentage_threshold: float


async def stock_alert():
    config = _load_config()
    quotes = await _get_all_quotes(config.symbols)
    for quote in quotes:
        if _should_notify(quote, config.price_drop_percentage_threshold):
            _notify(quote, config.contact_info)


def _load_config() -> Config:
    return Config.parse_obj(json.loads(CONFIG_PATH.read_text()))


async def _get_all_quotes(symbols: typing.List[str]) -> typing.List[Quote]:
    quotes = list()
    async with httpx.AsyncClient(base_url=FMP_API_URL) as fmp_client:
        for symbol in symbols:
            raw_response = await fmp_client.get(f'/quote/{symbol}', params=API_KEY_PARAM)
            raw_response.raise_for_status()
            quotes.append(Quote.parse_obj(raw_response.json()[0]))
    return quotes


def _should_notify(quote: Quote, price_drop_percentage_threshold: float) -> bool:
    return quote.price <= (1 - price_drop_percentage_threshold) * quote.priceAvg200


def _notify(quote: Quote, contact_info: ContactInfo):
    html = _generate_html(contact_info.name, quote)
    _send_email(contact_info.email, html)


def _generate_html(name: str, quote: Quote) -> str:
    unformatted_html = HTML_PATH.read_text()
    html_data = dict(name=name,
                     symbol=quote.symbol,
                     stock_name=quote.name,
                     datetime=datetime.datetime.fromtimestamp(
                         quote.timestamp).strftime(READABLE_DATETIME_FORMAT),
                     price=round(quote.price, NUMBER_OF_DIGITS_TO_ROUND),
                     price_200_day_avg=round(quote.priceAvg200, NUMBER_OF_DIGITS_TO_ROUND))
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
