import re
import feedparser
from datetime import datetime
from time import mktime
from typing import List
from collectors.base import BaseCollector, Article
from config import config

# 清除 HTML 標籤，只保留純文字
_HTML_RE = re.compile(r'<[^>]*>')
_MULTISPACE_RE = re.compile(r'\s+')

# Benzinga boilerplate 模式（每篇文章都重複出現的宣傳文案）
_BENZINGA_BOILERPLATE = [
    re.compile(r'The post .+? appeared first on Benzinga\s*\.?\s*', re.IGNORECASE),
    re.compile(r'Visit Benzinga to get more great content like this\.?', re.IGNORECASE),
    re.compile(r'©\s*\d{4}\s+Benzinga\.com\s*\.?\s*All rights reserved\.?', re.IGNORECASE),
    re.compile(r'Benzinga does not provide investment advice\.?\s*All rights reserved\.?', re.IGNORECASE),
    # 「You can buy/trade TOKEN through/on PLATFORM」（結尾到逗號、句號或字串結束）
    re.compile(r'You can (trade|buy) [A-Za-z0-9 ().]+ (through|on) [A-Za-z0-9 .]+[,.]?\s*', re.IGNORECASE),
    # 「Analysts are saying/forecasting that TOKEN could hit/reach [$]X by YYYY」
    re.compile(r'Analysts are (saying|forecasting) that .+? could (hit|reach) \$?[\d,.]+ by \d{4}\.?\s*', re.IGNORECASE),
    # 「Feeling bullish/confident about TOKEN already?」
    re.compile(r'Feeling (bullish|confident) about .+?\?\s*', re.IGNORECASE),
    # 留言數
    re.compile(r'\d+ #\s*Comments?\s*', re.IGNORECASE),
    re.compile(r'article url\s*', re.IGNORECASE),
]

# Benzinga title boilerplate
_BENZINGA_TITLE_BOILERPLATE = [
    re.compile(r'Price Prediction\s*\d{4}[,\d\s\-]*$', re.IGNORECASE),
]

def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = _HTML_RE.sub(' ', text)
    text = _MULTISPACE_RE.sub(' ', text).strip()
    return text

def _strip_benzinga_boilerplate(text: str, source_name: str) -> str:
    """移除 Benzinga 來源中每篇都重複的宣傳/範本文字"""
    if source_name != "benzinga" or not text:
        return text
    for pat in _BENZINGA_BOILERPLATE:
        text = pat.sub(' ', text)
    text = _MULTISPACE_RE.sub(' ', text).strip()
    return text

def _clean_benzinga_title(title: str, source_name: str) -> str:
    """移除 Benzinga 標題中的 boilerplate 後綴"""
    if source_name != "benzinga" or not title:
        return title
    for pat in _BENZINGA_TITLE_BOILERPLATE:
        title = pat.sub('', title)
    return title.strip()

class RSSCollector(BaseCollector):
    name = "rss"
    
    def fetch(self) -> List[Article]:
        articles = []
        for source_name, url in config.RSS_FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:30]:
                    pub = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    raw_title = _strip_html(entry.get("title", ""))
                    raw_summary = _strip_html(entry.get("summary", ""))
                    
                    # Benzinga 專屬 boilerplate 清除
                    clean_title = _clean_benzinga_title(raw_title, source_name)
                    clean_summary = _strip_benzinga_boilerplate(raw_summary, source_name)
                    
                    articles.append(Article(
                        source=f"rss:{source_name}",
                        source_type="rss",
                        title=clean_title,
                        summary=clean_summary[:500],
                        url=entry.get("link", ""),
                        published_at=pub or datetime.utcnow(),
                    ))
            except Exception as e:
                print(f"[RSS] fetch error on {source_name}: {e}")
        return articles
