import asyncio

import dotenv

dotenv.load_dotenv('./.env')

from src.stock_alert import stock_alert

if __name__ == '__main__':
    asyncio.run(stock_alert())
