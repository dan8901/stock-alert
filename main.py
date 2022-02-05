import dotenv
dotenv.load_dotenv('./.env')

import asyncio

from src.stock_alert import stock_alert


if __name__ == '__main__':
    asyncio.run(stock_alert())
