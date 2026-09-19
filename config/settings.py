import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fcpo_trading.db")
    
    NEWS_RSS_FEEDS: list[str] = [
        "https://news.google.com/rss/search?q=FCPO+palm+oil&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=soybean+oil+cbot&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=malaysia+palm+oil+exports&hl=en-US&gl=US&ceid=US:en"
    ]

settings = Settings()