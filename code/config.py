import os
from dataclasses import dataclass

# 自動載入 .env 檔案（從專案根目錄找，支援從 code/ 子目錄執行）
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore[import-untyped]
    _dotenv_path = find_dotenv()
    if _dotenv_path:
        load_dotenv(_dotenv_path)
except ImportError:
    # python-dotenv 未安裝；跳過 .env 載入，使用系統環境變數
    pass

@dataclass
class Config:
    # Database
    DB_PATH: str = "data/signals.db"
    
    # Reddit API
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = "EarlySignalBot/0.1"
    REDDIT_SUBREDDITS: tuple = ("wallstreetbets", "investing", "stocks")
    
    # RSS Sources
    RSS_FEEDS: tuple = (
        ("seeking_alpha", "https://seekingalpha.com/feed.xml"),
        ("benzinga", "https://www.benzinga.com/feed"),
        ("hackernews", "https://hnrss.org/frontpage"),
    )
    
    # Z-Score 觸發條件
    ZSCORE_THRESHOLD: float = 3.0
    MIN_CROSS_DOMAIN: int = 2
    MAX_HOURS_SINCE_FIRST: int = 72
    HISTORY_WEEKS: int = 8
    
    # Groq API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    MIN_SCORE_FOR_PUSH: int = 3

    # Tavily Search API
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    TAVILY_MONTHLY_LIMIT: int = 1000
    TAVILY_DAILY_WARNING: int = 30
    TAVILY_MONTHLY_WARNING_PCT: int = 80

    # Discord
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    DISCORD_CHANNEL_SIGNAL: int = int(os.getenv("DISCORD_CHANNEL_SIGNAL", "0"))
    DISCORD_CHANNEL_LOG: int = int(os.getenv("DISCORD_CHANNEL_LOG", "0"))
    
    # 採集週期
    COLLECT_INTERVAL_MINUTES: int = 30

config = Config()
