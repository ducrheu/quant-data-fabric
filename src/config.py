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