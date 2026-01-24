import os
from dotenv import load_dotenv

load_dotenv()

def get_env_int(name: str) -> int:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"ENV variable {name} is not set")
    return int(value)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

TICKET_CATEGORY_ID = get_env_int("TICKET_CATEGORY_ID")
TICKET_ADMIN_ROLE_ID = get_env_int("TICKET_ADMIN_ROLE_ID")
# позже
# TICKET_LOG_CHANNEL_ID = get_env_int("TICKET_LOG_CHANNEL_ID")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

TICKET_LOG_CHANNEL_ID = int(
    os.getenv("TICKET_LOG_CHANNEL_ID", "0")
)
