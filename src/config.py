import os
from dotenv import load_dotenv

load_dotenv()

def get_tushare_token() -> str:
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError(
            "TUSHARE_TOKEN not found. "
            "Create a .env file with TUSHARE_TOKEN=*** token>."
        )
    return token

PRICE_DB_PATH = "data/price.duckdb"
FACTOR_DB_PATH = "data/factor.duckdb"
FINANCIAL_DB_PATH = "data/quant_data.duckdb"