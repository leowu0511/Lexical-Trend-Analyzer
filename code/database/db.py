import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
from config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,  -- reddit / rss / sec / arxiv
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT UNIQUE,
    lang TEXT DEFAULT 'en',
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vocab (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT UNIQUE NOT NULL,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'new',  -- new / tracking / archived
    total_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vocab_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL,
    week_start DATE NOT NULL,
    count INTEGER DEFAULT 0,
    sources TEXT,  -- JSON list
    UNIQUE(term, week_start)
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL,
    zscore REAL,
    cross_domain_count INTEGER,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    signal_type TEXT,  -- sprout / fermenting / public
    pushed INTEGER DEFAULT 0,
    groq_score INTEGER,
    payload TEXT
);

CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service TEXT NOT NULL,  -- tavily / groq / etc
    query TEXT,
    result_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at);
CREATE INDEX IF NOT EXISTS idx_vocab_history_term ON vocab_history(term);
CREATE INDEX IF NOT EXISTS idx_usage_log_created ON usage_log(created_at);
"""

@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    import os
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    print("[DB] Initialized.")

def insert_article(article: dict) -> Optional[int]:
    try:
        with get_conn() as conn:
            cur = conn.execute("""
                INSERT OR IGNORE INTO articles
                (source, source_type, title, summary, url, lang, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                article["source"], article["source_type"],
                article["title"], article.get("summary", ""),
                article["url"], article.get("lang", "en"),
                article.get("published_at", datetime.utcnow())
            ))
            return cur.lastrowid
    except Exception as e:
        print(f"[DB] insert_article error: {e}")
        return None
