import json
from groq import Groq
from config import config

client = Groq(api_key=config.GROQ_API_KEY)

PROMPT_CONFIRM = """你是金融趨勢分析師。判斷以下關鍵詞是否為值得關注的新興投資趨勢。

關鍵詞：{term}
本週出現次數：{count}
過去平均：{mean}
跨域來源：{sources}

請以 JSON 回答，欄位：
- is_trend: bool
- score: 1-5 分（5 = 強烈趨勢）
- concept: 一句話概念解釋（中文）
- reason: 評分理由
"""

PROMPT_BENEFICIARY = """關於趨勢「{term}」（{concept}），請列出受益標的。

請以 JSON 回答：
- us_stocks: [{{ticker, name, reason}}]（美股，最多 5 檔）
- tw_stocks: [{{ticker, name, reason}}]（台股概念股，最多 5 檔）
- time_window: 預期發酵時間窗口
- risks: 主要風險（list）
"""

def confirm_topic(signal: dict) -> dict:
    prompt = PROMPT_CONFIRM.format(
        term=signal["term"],
        count=signal["this_week"],
        mean=signal["mean"],
        sources=", ".join(signal["sources"]),
    )
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(resp.choices[0].message.content)


def find_beneficiaries(term: str, concept: str) -> dict:
    prompt = PROMPT_BENEFICIARY.format(term=term, concept=concept)
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(resp.choices[0].message.content)


def analyze_signal(signal: dict) -> dict | None:
    """兩段式分析。若評分 < 門檻則只回確認結果。"""
    confirm = confirm_topic(signal)
    if not confirm.get("is_trend") or confirm.get("score", 0) < config.MIN_SCORE_FOR_PUSH:
        return {"confirm": confirm, "beneficiaries": None, "should_push": False}
    
    beneficiaries = find_beneficiaries(signal["term"], confirm["concept"])
    return {"confirm": confirm, "beneficiaries": beneficiaries, "should_push": True}
