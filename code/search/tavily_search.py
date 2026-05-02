"""
Tavily API 搜尋模組 — 即時網路搜尋 + 配額追蹤
每月 1000 次免費額度，需謹慎使用
"""
from datetime import datetime, timedelta
from config import config
from database.db import get_conn

_client = None


def _get_client():
    """延遲初始化 Tavily client"""
    global _client
    if _client is None:
        from tavily import TavilyClient
        _client = TavilyClient(api_key=config.TAVILY_API_KEY)
    return _client


def _log_usage(query: str, result_count: int):
    """紀錄 Tavily 呼叫到 usage_log 表"""
    try:
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO usage_log (service, query, result_count)
                VALUES ('tavily', ?, ?)
            """, (query[:200], result_count))
    except Exception:
        pass


def get_usage_stats() -> dict:
    """取得本月與今日用量"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    with get_conn() as conn:
        today = conn.execute(
            "SELECT COUNT(*) FROM usage_log WHERE service='tavily' AND created_at >= ?",
            (today_start,)
        ).fetchone()[0]

        month = conn.execute(
            "SELECT COUNT(*) FROM usage_log WHERE service='tavily' AND created_at >= ?",
            (month_start,)
        ).fetchone()[0]

    return {
        "today": today,
        "month": month,
        "monthly_limit": config.TAVILY_MONTHLY_LIMIT,
        "daily_warning": config.TAVILY_DAILY_WARNING,
        "remaining": config.TAVILY_MONTHLY_LIMIT - month,
        "usage_pct": round(month / config.TAVILY_MONTHLY_LIMIT * 100, 1),
    }


def check_quota() -> tuple[bool, str]:
    """
    檢查配額是否允許呼叫。
    回傳 (allowed, reason)
    """
    stats = get_usage_stats()

    if stats["today"] >= config.TAVILY_DAILY_WARNING:
        return False, f"今日已達 {config.TAVILY_DAILY_WARNING} 次上限，請明天再試"

    if stats["usage_pct"] >= config.TAVILY_MONTHLY_WARNING_PCT:
        return False, f"本月用量已達 {stats['usage_pct']}%，為保護配額暫停服務"

    return True, "ok"


def search_topic(term: str, max_results: int = 5) -> dict:
    """
    搜尋特定主題的最新資訊。

    回傳:
        {
            "ok": bool,
            "results": [{"title", "url", "snippet", "source", "date"}],
            "usage": {...},
            "error": str | None,
        }
    """
    # 配額檢查
    allowed, reason = check_quota()
    if not allowed:
        return {"ok": False, "results": [], "usage": get_usage_stats(), "error": reason}

    try:
        client = _get_client()

        # 附加投資相關關鍵詞提高精準度
        query = f"{term} investing stock latest news"

        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=False,
            include_raw_content=False,
        )

        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": (r.get("content", "") or "")[:300],
                "source": r.get("url", "").split("/")[2] if r.get("url") else "unknown",
                "date": r.get("published_date", ""),
            })

        _log_usage(term, len(results))
        return {"ok": True, "results": results, "usage": get_usage_stats(), "error": None}

    except Exception as e:
        return {"ok": False, "results": [], "usage": get_usage_stats(), "error": str(e)}
