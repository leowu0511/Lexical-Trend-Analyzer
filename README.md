# 🔭 Lexical Trend Analyzer (Topic Radar)

> **Early signal detection system for US stock market topics** — catch emerging narratives before they hit mainstream media.

A real-time NLP pipeline that monitors financial RSS feeds, extracts key terms via spaCy, detects statistical anomalies with Z-Score, analyzes signals through Groq LLM, and delivers actionable alerts to Discord via slash commands.

---

## 📡 How It Works

```
RSS Feeds → spaCy NLP → Z-Score Detection → Groq Analysis → Discord Alert
  (collect)    (extract)      (anomaly)        (confirm)        (push)
```

### 5-Layer Pipeline

| Layer | Description |
|-------|-------------|
| **1. Collection** | Polls Seeking Alpha, Benzinga, and Hacker News RSS feeds every 30 min. Reddit support built-in (disabled by default). |
| **2. NLP Extraction** | spaCy `en_core_web_sm` extracts noun chunks and named entities (ORG, PRODUCT, TECH, GPE). HTML boilerplate stripped at source. |
| **3. Z-Score Detection** | Computes `Z = (this_week_freq − 8wk_avg) / 8wk_stddev`. Triggers when Z ≥ 3.0 and term appears across ≥ 2 domains. |
| **4. Groq Analysis** | Llama 3.3 70B confirms topic validity, classifies signal type (🌱 sprout / 🟡 fermenting / 🔴 public), and identifies beneficiary stocks. |
| **5. Discord Push** | Formatted embed cards with Z-Score, confidence rating, US/TW ticker suggestions, and time window. 24h dedup per signal. |

---

## 🤖 Discord Slash Commands

| Command | Description |
|---------|-------------|
| `/scan` | Manually trigger a full scan cycle |
| `/status` | System stats: article count, vocabulary size, Tavily usage |
| `/signals` | Last 10 triggered signals |
| `/lookup <term>` | Z-Score, weekly trend, cross-domain presence for any term |
| `/search <query>` | Real-time Tavily web search (consumes 1 API call) |
| `/trending` | Top 5 highest Z-Score terms this week |
| `/articles <term>` | 5 most recent articles containing the term |
| `/radar` | Command help overview |

Commands sync instantly to all joined servers via per-guild sync.

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| NLP | spaCy 3.7 (`en_core_web_sm`) |
| LLM Analysis | Groq API (Llama 3.3 70B) |
| Real-time Search | Tavily Search API |
| Bot Framework | discord.py 2.4 (`app_commands`) |
| Database | SQLite (articles, vocab, signals, usage_log) |
| RSS | feedparser |
| Containerization | Docker + docker-compose |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- spaCy model: `python -m spacy download en_core_web_sm`
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Groq API Key ([console.groq.com](https://console.groq.com))
- Tavily API Key (optional, for `/search`) ([tavily.com](https://tavily.com))

### 1. Clone & Setup

```bash
git clone https://github.com/leowu0511/Lexical-Trend-Analyzer.git
cd Lexical-Trend-Analyzer
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
GROQ_API_KEY=gsk_your_key_here
TAVILY_API_KEY=tvly-your-key-here
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_SIGNAL=123456789
DISCORD_CHANNEL_LOG=123456789
```

### 3. Run

```bash
python run.py
```

The bot will connect to Discord, sync `/` commands, and begin background scanning every 30 minutes.

### Docker (Alternative)

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
Lexical-Trend-Analyzer/
├── run.py                          # Entry launcher
├── requirements.txt                # Python dependencies
├── Dockerfile / docker-compose.yml # Container support
├── .env.example                    # Environment template (safe to commit)
├── code/
│   ├── main.py                     # Bot startup + scheduler
│   ├── config.py                   # All configuration
│   ├── core.py                     # Core scan pipeline
│   ├── analyzer/
│   │   └── groq_analyzer.py        # LLM signal confirmation
│   ├── collectors/
│   │   ├── base.py                 # Article data class
│   │   ├── rss_collector.py        # RSS feed fetcher
│   │   └── reddit_collector.py     # Reddit (disabled by default)
│   ├── database/
│   │   └── db.py                   # SQLite schema + CRUD
│   ├── detector/
│   │   ├── zscore.py               # Z-Score computation
│   │   └── trigger.py              # Signal trigger logic
│   ├── nlp/
│   │   └── extractor.py            # spaCy term extraction
│   ├── notifier/
│   │   └── discord_bot.py          # Discord slash commands
│   └── search/
│       └── tavily_search.py        # Tavily API integration
└── 計畫/                            # Design documents (Chinese)
    ├── 話題雷達計畫書.md
    └── 專案結構.md
```

---

## ⚙️ Key Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `ZSCORE_THRESHOLD` | 3.0 | Minimum Z-Score to trigger |
| `MIN_CROSS_DOMAIN` | 2 | Minimum source domains |
| `HISTORY_WEEKS` | 8 | Baseline window for Z-Score |
| `COLLECT_INTERVAL_MINUTES` | 30 | RSS polling interval |
| `TAVILY_MONTHLY_LIMIT` | 1000 | Monthly search quota |

---

## 📊 Quota Protection

Tavily API has a 1,000 calls/month limit:

- **Daily soft cap**: warns at 30 calls/day
- **Monthly warning**: alerts at 80% usage
- All `/search` usage logged to `usage_log` table
- Use `/status` to monitor current consumption

---

## ⚠️ Disclaimer

**This system does NOT constitute investment advice.** All signals are generated from statistical anomaly detection and LLM analysis of publicly available text. Always conduct your own research before making trading decisions.

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

---

# 🔭 詞彙趨勢分析器（話題雷達）

> **美股短線話題早期信號偵測系統** — 在大眾媒體報導之前捕捉正在醞釀的市場話題。

即時 NLP 管線：監控財經 RSS 來源 → spaCy 關鍵詞提取 → Z-Score 異常偵測 → Groq LLM 分析確認 → Discord 斜線指令推播。

## 五層架構

1. **採集層** — 每 30 分鐘輪詢 Seeking Alpha、Benzinga、Hacker News RSS（Reddit 內建支援，預設停用）
2. **NLP 層** — spaCy 提取名詞短語與專有名詞，源頭清除 HTML boilerplate
3. **Z-Score 偵測** — `Z = (本週次數 − 8 週平均) / 8 週標準差`，Z ≥ 3.0 且跨 ≥ 2 域時觸發
4. **Groq 分析** — Llama 3.3 70B 確認話題有效性、分類信號階段、辨識受益股票
5. **Discord 推播** — 格式化 Embed 卡片，含 Z-Score、信心評分、美股/台股代碼、時間窗口

## Discord 斜線指令

| 指令 | 說明 |
|------|------|
| `/scan` | 手動觸發一次完整掃描 |
| `/status` | 系統狀態：文章數、詞彙數、Tavily 用量 |
| `/signals` | 最近 10 筆觸發信號 |
| `/lookup <詞彙>` | 查詢任意詞彙的 Z-Score 與趨勢 |
| `/search <關鍵詞>` | Tavily 即時網路搜尋（耗用 1 次額度） |
| `/trending` | 本週 Z-Score 最高前 5 名 |
| `/articles <詞彙>` | 最近 5 篇包含該詞的文章 |
| `/radar` | 指令說明總覽 |

所有 `/` 指令透過 per-guild sync 即時同步到每個已加入的伺服器。

## 快速啟動

```bash
git clone https://github.com/leowu0511/Lexical-Trend-Analyzer.git
cd Lexical-Trend-Analyzer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env   # 編輯 .env 填入你的 API 金鑰
python run.py
```

## 技術棧

Python 3.11+ · spaCy 3.7 · Groq API (Llama 3.3 70B) · Tavily Search API · discord.py 2.4 · SQLite · Docker

## 免責聲明

**本系統不構成投資建議。** 所有信號來自統計異常偵測與 LLM 對公開文本的分析。進行任何交易決策前，請自行研究。
