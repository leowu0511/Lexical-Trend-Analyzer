"""
話題雷達 - 主程式入口
啟動 Discord Bot（/ 斜線指令 + 全域同步）+ 背景排程掃描
"""
import asyncio
from database.db import init_db
from notifier.discord_bot import bot, push_log
from core import collect_and_process
from config import config


async def scheduler():
    """背景排程：定時執行掃描"""
    await bot.wait_until_ready()
    print("[Scheduler] Discord Bot 已就緒，開始背景排程")

    # 首次啟動時立即執行一次
    try:
        await collect_and_process()
    except Exception as e:
        print(f"[Scheduler] 首次掃描異常: {e}")

    while not bot.is_closed():
        await asyncio.sleep(config.COLLECT_INTERVAL_MINUTES * 60)
        try:
            await collect_and_process()
        except Exception as e:
            print(f"[Scheduler] 排程掃描異常: {e}")


@bot.event
async def on_ready():
    print(f"[Discord] 登入為 {bot.user} (ID: {bot.user.id})")

    # 列出所在的所有伺服器
    guild_names = ", ".join([g.name for g in bot.guilds])
    print(f"[Discord] 所在伺服器: {guild_names}")

    # 對每個伺服器立即同步 / 指令（per-guild sync 立即生效，不等全域快取）
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"[Discord] 伺服器「{guild.name}」已同步 {len(synced)} 個 / 指令")
        except Exception as e:
            print(f"[Discord] 伺服器「{guild.name}」同步失敗: {e}")

    # 也做一次全域同步（供未來新伺服器使用，但生效較慢）
    try:
        synced_all = await bot.tree.sync()
        print(f"[Discord] 全域同步 {len(synced_all)} 個 / 指令（新伺服器約 1 小時內生效）")
    except Exception as e:
        print(f"[Discord] 全域同步失敗: {e}")

    bot.loop.create_task(scheduler())


if __name__ == "__main__":
    init_db()
    try:
        bot.run(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n[Discord] 收到關閉訊號，正在安全退出...")
    finally:
        if not bot.is_closed():
            import asyncio as _asyncio
            _asyncio.get_event_loop().run_until_complete(bot.close())
        print("[Discord] 機器人已離線，系統關閉")
