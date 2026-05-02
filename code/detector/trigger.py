from datetime import datetime
from database.db import get_conn
from detector.zscore import compute_zscore
from config import config

def check_chinese_mention(term: str) -> int:
    """檢查中文來源是否已提到此詞（出場訊號）"""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS cnt FROM articles
            WHERE lang = 'zh' AND (title LIKE ? OR summary LIKE ?)
        """, (f"%{term}%", f"%{term}%")).fetchone()
    return row["cnt"]


def evaluate_term(term: str) -> dict | None:
    """判斷某詞是否符合萌芽信號條件"""
    stats = compute_zscore(term)
    
    if stats["zscore"] < config.ZSCORE_THRESHOLD:
        return None
    if stats["cross_domain"] < config.MIN_CROSS_DOMAIN:
        return None
    
    zh_count = check_chinese_mention(term)
    if zh_count > 0:
        return {**stats, "signal_type": "public", "zh_count": zh_count}
    
    if stats["first_seen"]:
        first = datetime.fromisoformat(str(stats["first_seen"]))
        hours = (datetime.utcnow() - first).total_seconds() / 3600
        if hours > config.MAX_HOURS_SINCE_FIRST:
            return None
    
    return {**stats, "signal_type": "sprout", "zh_count": 0}


def scan_all_terms() -> list[dict]:
    """掃描本週所有出現過的詞並評估"""
    from datetime import timedelta
    now = datetime.utcnow()
    week_start = (now - timedelta(days=now.weekday())).date()
    
    with get_conn() as conn:
        terms = conn.execute(
            "SELECT DISTINCT term FROM vocab_history WHERE week_start = ?",
            (week_start,)
        ).fetchall()
    
    signals = []
    for row in terms:
        result = evaluate_term(row["term"])
        if result:
            signals.append(result)
    return signals
