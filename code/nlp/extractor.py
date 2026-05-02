import re
import spacy
import json
from datetime import datetime, timedelta
from collections import Counter
from typing import List
from database.db import get_conn

# python -m spacy download en_core_web_sm
nlp = spacy.load("en_core_web_sm", disable=["lexeme_norm"])

# 自訂停用詞（過於通用或來自 RSS boilerplate 的詞）
GENERIC_TERMS = {
    "company", "stock", "market", "price", "year", "time",
    "people", "thing", "way", "today", "week", "report",
    # Benzinga / RSS boilerplate 殘留
    "the post", "more great content", "the platform", "great content",
    "first qualifying trade", "your first qualifying trade",
    "article url", "comments", "# comments", "comment",
    "all rights reserved", "rights reserved",
    "investment advice", "the author", "the analyst",
    "this article", "the article", "a buying opportunity",
    "no problem", "new highs", "the new equilibrium",
    "the age", "the market",
}

# HTML 標籤與屬性的 regex（避免 RSS summary 中的 HTML 被當作名詞短語）
_HTML_RE = re.compile(r'<[^>]*>')
_ATTR_RE = re.compile(r'\b(href|src|alt|class|style|width|height|target|rel|title)\s*=\s*"[^"]*"', re.IGNORECASE)
_URLONLY_RE = re.compile(r'^https?://\S+$')


def _clean_text(text: str) -> str:
    """清除 HTML 標籤、屬性、URL 等雜訊，只保留純文字"""
    text = _HTML_RE.sub(' ', text)
    text = _ATTR_RE.sub('', text)
    # 移除單獨的 URL 行
    text = _URLONLY_RE.sub('', text)
    # 壓縮多餘空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_terms(text: str) -> List[str]:
    """從文本中提取名詞短語與專有名詞（先清除 HTML 雜訊）"""
    if not text:
        return []
    text = _clean_text(text)
    if len(text) < 10:
        return []
    doc = nlp(text)
    terms = set()
    
    # 名詞短語
    for chunk in doc.noun_chunks:
        term = chunk.text.lower().strip()
        # 過濾：1-4 個詞的短語，不含 HTML 殘留，不在通用詞表
        if term and 2 <= len(term.split()) <= 4 and term not in GENERIC_TERMS:
            # 額外過濾：排除含 URL 片段的詞
            if not re.search(r'https?://|www\.|\.html|\.xml|href|src=', term):
                terms.add(term)
    
    # 專有名詞
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT", "TECH", "GPE"):
            clean_ent = _clean_text(ent.text).lower().strip()
            if clean_ent and len(clean_ent) > 2 and not re.search(r'https?://|www\.|href|src=', clean_ent):
                terms.add(clean_ent)
    
    return [t for t in terms if len(t) > 2]


def update_vocab(article_id: int, source: str, terms: List[str]):
    """更新詞表與週頻歷史"""
    if not terms:
        return
    now = datetime.utcnow()
    week_start = (now - timedelta(days=now.weekday())).date()
    
    with get_conn() as conn:
        for term in terms:
            # vocab 主表
            conn.execute("""
                INSERT INTO vocab (term, first_seen_at, last_seen_at, total_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(term) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    total_count = total_count + 1
            """, (term, now, now))
            
            # 週頻歷史
            row = conn.execute(
                "SELECT count, sources FROM vocab_history WHERE term=? AND week_start=?",
                (term, week_start)
            ).fetchone()
            
            if row:
                sources = set(json.loads(row["sources"] or "[]"))
                sources.add(source)
                conn.execute("""
                    UPDATE vocab_history SET count = count + 1, sources = ?
                    WHERE term = ? AND week_start = ?
                """, (json.dumps(list(sources)), term, week_start))
            else:
                conn.execute("""
                    INSERT INTO vocab_history (term, week_start, count, sources)
                    VALUES (?, ?, 1, ?)
                """, (term, week_start, json.dumps([source])))
