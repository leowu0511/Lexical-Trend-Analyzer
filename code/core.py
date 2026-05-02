"""
話題雷達 - 核心掃描邏輯
供排程與 Discord 指令共用
"""
import json
from datetime import datetime
from database.db import insert_article, get_conn
from collectors.rss_collector import RSSCollector
from nlp.extractor import extract_terms, update_vocab
from detector.trigger import scan_all_terms
from analyzer.groq_analyzer import analyze_signal
from config import config


async def collect_and_process(push_to=None):
    """
    完整資料流：採集 → NLP → 詞表 → Z-Score → 觸發 → Groq → 推播
    
    push_to: 可選的 Discord 頻道物件，若有則推播到該頻道（指令觸發用）
    """
    print(f"\n[{datetime.utcnow()}] === 開始採集 ===")

    collectors = []
    
    # Reddit 採集器：僅在有 API key 時啟用
    reddit_enabled = bool(config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_ID != "xxx"
                          and config.REDDIT_CLIENT_SECRET and config.REDDIT_CLIENT_SECRET != "xxx")
    if reddit_enabled:
        try:
            from collectors.reddit_collector import RedditCollector
            collectors.append(RedditCollector())
            print("[Collect] Reddit 採集器已啟用")
        except Exception as e:
            print(f"[Collect] Reddit 採集器載入失敗: {e}")
    else:
        print("[Collect] Reddit 採集器已停用（未設定 API key）")

    # RSS 採集器
    collectors.append(RSSCollector())

    total = 0
    fetched = 0
    for collector in collectors:
        articles = collector.fetch()
        for art in articles:
            fetched += 1
            article_id = insert_article(art.to_dict())
            if not article_id:
                continue  # URL 重複（已存在於 DB），跳過 NLP
            text = f"{art.title} {art.summary}"
            terms = extract_terms(text)
            update_vocab(article_id, art.source, terms)
            total += 1

    skipped = fetched - total
    status_msg = f"擷取 {fetched} 篇，新增 {total} 篇"
    if skipped:
        status_msg += f"，跳過 {skipped} 篇（重複）"
    print(f"[Collect] {status_msg}")
    from notifier.discord_bot import push_log
    await push_log(status_msg, channel=push_to)

    # 評估觸發
    signals = scan_all_terms()
    print(f"[Detect] 觸發 {len(signals)} 個信號")

    for sig in signals:
        # 去重：同一詞 24 小時內不重複推播
        with get_conn() as conn:
            recent = conn.execute("""
                SELECT 1 FROM signals
                WHERE term = ? AND pushed = 1
                  AND triggered_at > datetime('now', '-1 day')
            """, (sig["term"],)).fetchone()
            if recent:
                continue

        # Groq 分析
        try:
            analysis = analyze_signal(sig)
        except Exception as e:
            print(f"[Groq] error on {sig['term']}: {e}")
            continue

        # 寫入 signals 表
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO signals (term, zscore, cross_domain_count, signal_type,
                                     groq_score, pushed, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                sig["term"], sig["zscore"], sig["cross_domain"],
                sig["signal_type"], analysis["confirm"].get("score"),
                1 if analysis["should_push"] else 0,
                json.dumps(analysis, ensure_ascii=False),
            ))

        if analysis["should_push"]:
            from notifier.discord_bot import push_signal
            await push_signal(sig, analysis, channel=push_to)
            print(f"[Push] {sig['term']} → Discord")

    return total, len(signals)
