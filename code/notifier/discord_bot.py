"""
話題雷達 - Discord Bot 模組
使用 app_commands（/ 斜線指令），全域同步到所有已加入伺服器
"""
import discord
from discord import app_commands
from discord.ext import commands
from config import config

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)


def build_embed(signal: dict, analysis: dict) -> discord.Embed:
    """建立信號通知的 Embed 卡片"""
    confirm = analysis["confirm"]
    bene = analysis.get("beneficiaries")

    color_map = {"sprout": 0x00FF00, "fermenting": 0xFFFF00, "public": 0xFF0000}
    embed = discord.Embed(
        title=f"{'🟢' if signal.get('signal_type') == 'sprout' else '🟡' if signal.get('signal_type') == 'fermenting' else '🔴'} 話題信號：{signal['term']}",
        description=confirm.get("concept", ""),
        color=color_map.get(signal.get("signal_type"), 0x808080),
    )
    embed.add_field(
        name="信號強度",
        value=f"Z-Score {signal['zscore']} | 評分 {confirm.get('score')}/5",
        inline=False,
    )
    embed.add_field(
        name="來源統計",
        value=f"本週出現 {signal.get('this_week', '?')} 次（過去平均 {signal.get('mean', '?')}）\n跨域：{signal.get('cross_domain', '?')} 個",
        inline=False,
    )

    if bene:
        us = "\n".join(
            [f"`{s['ticker']}` {s['name']} - {s['reason']}" for s in bene.get("us_stocks", [])[:3]]
        )
        tw = "\n".join(
            [f"`{s['ticker']}` {s['name']} - {s['reason']}" for s in bene.get("tw_stocks", [])[:3]]
        )
        if us:
            embed.add_field(name="🇺🇸 美股受益", value=us[:1024], inline=False)
        if tw:
            embed.add_field(name="🇹🇼 台股概念", value=tw[:1024], inline=False)
        embed.add_field(name="時間窗口", value=bene.get("time_window", "—"), inline=True)

    embed.set_footer(text="本系統不構成投資建議，請自行研究")
    return embed


async def push_signal(signal: dict, analysis: dict, channel=None):
    """推播信號到指定頻道，若未指定則使用設定的預設頻道"""
    target = channel
    if not target and config.DISCORD_CHANNEL_SIGNAL:
        target = bot.get_channel(config.DISCORD_CHANNEL_SIGNAL)
    if target:
        await target.send(embed=build_embed(signal, analysis))


async def push_log(message: str, channel=None):
    """推播日誌訊息"""
    target = channel
    if not target and config.DISCORD_CHANNEL_LOG:
        target = bot.get_channel(config.DISCORD_CHANNEL_LOG)
    if target:
        await target.send(f"```{message}```")


# ==============================
# / 斜線指令定義 (Tree Commands)
# ==============================

@bot.tree.command(name='scan', description='手動觸發一次話題掃描')
async def cmd_scan(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        from core import collect_and_process
        await collect_and_process(push_to=interaction.channel)
        await interaction.followup.send("✅ 掃描完成")
    except Exception as e:
        await interaction.followup.send(f"❌ 掃描失敗：{e}")


@bot.tree.command(name='status', description='查看話題雷達系統狀態')
async def cmd_status(interaction: discord.Interaction):
    await interaction.response.defer()
    from database.db import get_conn
    with get_conn() as conn:
        article_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        vocab_count = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
        signal_count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]

    embed = discord.Embed(title="📊 話題雷達系統狀態", color=0x3498DB)
    embed.add_field(name="已採集文章", value=str(article_count), inline=True)
    embed.add_field(name="詞彙庫", value=str(vocab_count), inline=True)
    embed.add_field(name="歷史信號", value=str(signal_count), inline=True)
    embed.add_field(name="採集間隔", value=f"{config.COLLECT_INTERVAL_MINUTES} 分鐘", inline=True)

    reddit_enabled = bool(config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_ID != "xxx")
    embed.add_field(name="Reddit 採集", value="🟢 啟用" if reddit_enabled else "🔴 停用", inline=True)
    embed.add_field(name="RSS 採集", value="🟢 啟用", inline=True)

    tavily_enabled = bool(config.TAVILY_API_KEY)
    if tavily_enabled:
        try:
            from search.tavily_search import get_usage_stats
            usage = get_usage_stats()
            embed.add_field(
                name="🌐 Tavily 搜尋用量",
                value=f"本月 {usage['month']}/{usage['monthly_limit']}（{usage['usage_pct']}%）\n"
                      f"今日 {usage['today']} 次",
                inline=False,
            )
        except Exception:
            embed.add_field(name="🌐 Tavily 搜尋", value="⚠️ 用量讀取失敗", inline=False)
    else:
        embed.add_field(name="🌐 Tavily 搜尋", value="🔴 未設定 API key", inline=False)

    await interaction.followup.send(embed=embed)


@bot.tree.command(name='signals', description='查看最近 10 筆信號紀錄')
async def cmd_signals(interaction: discord.Interaction):
    await interaction.response.defer()
    from database.db import get_conn
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT term, zscore, signal_type, triggered_at, groq_score
            FROM signals ORDER BY triggered_at DESC LIMIT 10
        """).fetchall()

    if not rows:
        await interaction.followup.send("尚無信號紀錄", ephemeral=True)
        return

    embed = discord.Embed(title="📡 最近信號紀錄", color=0xE67E22)
    type_emoji = {"sprout": "🟢", "fermenting": "🟡", "public": "🔴"}
    for r in rows:
        emoji = type_emoji.get(r["signal_type"], "⚪")
        embed.add_field(
            name=f"{emoji} {r['term']}",
            value=f"Z: {r['zscore']} | 評分: {r['groq_score']} | {r['triggered_at'][:19]}",
            inline=False,
        )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name='lookup', description='查詢特定詞彙的 Z-Score、歷史趨勢、中文圈狀態')
@app_commands.describe(term='要查詢的關鍵詞，例如 SMR、nuclear reactor')
async def cmd_lookup(interaction: discord.Interaction, term: str):
    await interaction.response.defer()
    term = term.strip().lower()
    from detector.zscore import compute_zscore
    from detector.trigger import check_chinese_mention
    from database.db import get_conn

    stats = compute_zscore(term)
    zh_count = check_chinese_mention(term)

    with get_conn() as conn:
        vocab = conn.execute(
            "SELECT first_seen_at, last_seen_at, total_count, status FROM vocab WHERE term = ?",
            (term,)
        ).fetchone()

    if not stats["this_week"] and not vocab:
        await interaction.followup.send(f"❌ 找不到詞彙 `{term}`", ephemeral=True)
        return

    if stats["zscore"] >= 5.0:
        level = "🚨 強烈信號"
    elif stats["zscore"] >= 3.0:
        level = "⚠️ 注意信號"
    elif stats["zscore"] >= 2.0:
        level = "👀 值得觀察"
    else:
        level = "💤 正常水位"

    embed = discord.Embed(title=f"🔎 詞彙查詢：{term}", description=f"**{level}**", color=0x9B59B6)
    embed.add_field(name="📊 Z-Score", value=f"{stats['zscore']}", inline=True)
    embed.add_field(name="📈 本週出現", value=f"{stats['this_week']} 次", inline=True)
    embed.add_field(name="📉 過去 8 週平均", value=f"{stats.get('mean', '?')} 次/週", inline=True)
    embed.add_field(name="🌐 跨域來源數", value=f"{stats['cross_domain']} 個", inline=True)

    if stats.get("sources"):
        sources = ", ".join(stats["sources"][:5])
        embed.add_field(name="📡 本週來源", value=sources[:1024] if sources else "—", inline=False)

    if zh_count > 0:
        embed.add_field(name="🀄 中文圈狀態", value=f"⚠️ 已出現 {zh_count} 次（可能已是公開信號）", inline=False)
    else:
        embed.add_field(name="🀄 中文圈狀態", value="✅ 尚未出現", inline=False)

    if vocab:
        embed.add_field(name="⏱ 首次出現", value=str(vocab["first_seen_at"])[:19], inline=True)
        embed.add_field(name="📦 累計出現", value=f"{vocab['total_count']} 次", inline=True)
        embed.add_field(name="🏷 狀態", value=vocab["status"], inline=True)

    if config.TAVILY_API_KEY:
        embed.set_footer(text="💡 使用 /search 搜尋網路最新資訊")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name='search', description='Tavily 即時搜尋網路最新資訊（耗用 1 次額度）')
@app_commands.describe(query='要搜尋的關鍵詞，例如 "nuclear reactor investing"')
async def cmd_search(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)

    if not config.TAVILY_API_KEY:
        await interaction.followup.send("❌ Tavily API 未設定，請在 .env 中設定 TAVILY_API_KEY", ephemeral=True)
        return

    from search.tavily_search import search_topic

    query = query.strip()[:200]

    result = search_topic(query)
    usage = result["usage"]

    if not result["ok"]:
        embed = discord.Embed(title="❌ 搜尋失敗", description=result.get("error", "未知錯誤"), color=0xE74C3C)
        embed.add_field(name="📊 本月用量", value=f"{usage['month']}/{usage['monthly_limit']}（{usage['usage_pct']}%）")
        await interaction.followup.send(embed=embed)
        return

    results = result["results"]
    if not results:
        await interaction.followup.send(f"📭 找不到「{query}」的相關結果")
        return

    embed = discord.Embed(title=f"🔍 Tavily 搜尋：{query[:100]}", description=f"找到 {len(results)} 筆結果", color=0x1ABC9C)
    for i, r in enumerate(results[:5], 1):
        title = r["title"][:256]
        snippet = r["snippet"][:200]
        url = r.get("url", "")
        date = r.get("date", "?")[:10] if r.get("date") else "?"
        embed.add_field(name=f"#{i} {title}", value=f"{snippet}\n{url} | {date}", inline=False)

    embed.add_field(
        name="📊 Tavily 配額",
        value=f"今日 {usage['today']} 次 | 本月 {usage['month']}/{usage['monthly_limit']}（{usage['usage_pct']}%）| 剩餘 {usage['remaining']}",
        inline=False,
    )
    embed.set_footer(text="Tavily 每月 1000 次額度，謹慎使用")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name='trending', description='顯示本週 Z-Score 最高的前 5 個熱門詞')
async def cmd_trending(interaction: discord.Interaction):
    await interaction.response.defer()
    from datetime import datetime, timedelta
    from detector.zscore import compute_zscore
    from database.db import get_conn

    now = datetime.utcnow()
    week_start = (now - timedelta(days=now.weekday())).date()

    with get_conn() as conn:
        terms = conn.execute(
            "SELECT DISTINCT term FROM vocab_history WHERE week_start = ?",
            (week_start,)
        ).fetchall()

    if not terms:
        await interaction.followup.send("📭 本週尚無任何詞彙資料", ephemeral=True)
        return

    scored = []
    for row in terms:
        s = compute_zscore(row["term"])
        if s["zscore"] > 0:
            scored.append(s)

    scored.sort(key=lambda x: x["zscore"], reverse=True)
    top5 = scored[:5]

    if not top5:
        await interaction.followup.send("📭 本週尚無任何詞彙資料", ephemeral=True)
        return

    embed = discord.Embed(title="🔥 本週熱門詞彙 TOP 5", color=0xE74C3C,
                          description=f"依據 Z-Score 排序（{week_start} 起）")
    for i, s in enumerate(top5, 1):
        zh_count = 0
        try:
            from detector.trigger import check_chinese_mention
            zh_count = check_chinese_mention(s["term"])
        except Exception:
            pass

        zh_tag = " 🀄" if zh_count > 0 else ""
        bar = "█" * min(int(s["zscore"]), 10) + "░" * max(0, 10 - min(int(s["zscore"]), 10))
        embed.add_field(
            name=f"#{i}  {s['term']}{zh_tag}",
            value=f"`{bar}` Z={s['zscore']} | 本週 {s['this_week']} 次 | 平均 {s.get('mean', '?')} | 跨域 {s['cross_domain']}",
            inline=False,
        )

    embed.set_footer(text="/lookup 詞彙 查看詳細資訊")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name='articles', description='查詢包含特定詞彙的最近文章（最多 5 篇）')
@app_commands.describe(term='要查詢的關鍵詞，例如 "AI"')
async def cmd_articles(interaction: discord.Interaction, term: str):
    await interaction.response.defer()
    term = term.strip()
    from database.db import get_conn

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT title, source, url, published_at
            FROM articles
            WHERE title LIKE ? OR summary LIKE ?
            ORDER BY published_at DESC
            LIMIT 5
        """, (f"%{term}%", f"%{term}%")).fetchall()

    if not rows:
        await interaction.followup.send(f"📭 找不到包含 `{term}` 的文章", ephemeral=True)
        return

    embed = discord.Embed(title=f"📰 包含「{term}」的最近文章", color=0x1ABC9C)
    for r in rows:
        pub = str(r["published_at"])[:19] if r["published_at"] else "?"
        title = r["title"][:256] if r["title"] else "(無標題)"
        source = r["source"]
        url = r["url"] or ""
        embed.add_field(name=f"{source} | {pub}", value=f"[{title}]({url})" if url else title, inline=False)

    embed.set_footer(text=f"共 {len(rows)} 篇")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name='radar', description='顯示話題雷達的指令說明')
async def cmd_help(interaction: discord.Interaction):
    embed = discord.Embed(title="🔭 話題雷達 - 指令說明", color=0x2ECC71,
                          description="美股短線話題偵測系統，幫你提早發現市場話題。")
    embed.add_field(name="/scan", value="手動觸發一次話題掃描", inline=False)
    embed.add_field(name="/status", value="查看系統狀態（文章數、詞彙數、信號數、Tavily 用量）", inline=False)
    embed.add_field(name="/signals", value="查看最近 10 筆信號紀錄", inline=False)
    embed.add_field(name="/lookup <詞彙>", value="查詢特定詞彙的 Z-Score、歷史趨勢、中文圈狀態", inline=False)
    embed.add_field(name="/search <關鍵詞>", value="Tavily 即時搜尋網路最新資訊（耗用 1 次額度）", inline=False)
    embed.add_field(name="/trending", value="顯示本週 Z-Score 最高的前 5 個熱門詞", inline=False)
    embed.add_field(name="/articles <詞彙>", value="查詢包含特定詞彙的最近 5 篇文章", inline=False)
    embed.add_field(name="/radar", value="顯示此幫助訊息", inline=False)
    embed.set_footer(text="自動掃描週期執行中，信號會推送至此頻道")
    await interaction.response.send_message(embed=embed)
