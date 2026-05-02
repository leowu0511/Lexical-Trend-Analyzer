import json
import statistics
from datetime import datetime, timedelta
from database.db import get_conn
from config import config

def compute_zscore(term: str) -> dict:
    """計算指定詞的 Z-Score 與跨域出現數"""
    now = datetime.utcnow()
    this_week_start = (now - timedelta(days=now.weekday())).date()
    history_start = this_week_start - timedelta(weeks=config.HISTORY_WEEKS)
    
    with get_conn() as conn:
        # 本週數據
        this_week = conn.execute("""
            SELECT count, sources FROM vocab_history
            WHERE term = ? AND week_start = ?
        """, (term, this_week_start)).fetchone()
        
        if not this_week:
            return {"term": term, "zscore": 0, "cross_domain": 0, "this_week": 0}
        
        # 過去 8 週
        past = conn.execute("""
            SELECT count FROM vocab_history
            WHERE term = ? AND week_start >= ? AND week_start < ?
        """, (term, history_start, this_week_start)).fetchall()
        
        past_counts = [r["count"] for r in past]
        # 補齊 0（沒出現的週也要算）
        while len(past_counts) < config.HISTORY_WEEKS:
            past_counts.append(0)
        
        if len(past_counts) < 2:
            return {"term": term, "zscore": 0, "cross_domain": 0, "this_week": this_week["count"]}
        
        mean = statistics.mean(past_counts)
        stdev = statistics.stdev(past_counts) or 1.0  # 避免除以 0
        zscore = (this_week["count"] - mean) / stdev
        
        sources = json.loads(this_week["sources"] or "[]")
        # 跨域：以 source_type 區分（reddit / rss / sec / arxiv）
        domains = set(s.split(":")[0] for s in sources)
        
        # 第一次出現時間
        first_seen = conn.execute(
            "SELECT first_seen_at FROM vocab WHERE term = ?", (term,)
        ).fetchone()
        
        return {
            "term": term,
            "zscore": round(zscore, 2),
            "cross_domain": len(domains),
            "this_week": this_week["count"],
            "mean": round(mean, 2),
            "first_seen": first_seen["first_seen_at"] if first_seen else None,
            "sources": sources,
        }
