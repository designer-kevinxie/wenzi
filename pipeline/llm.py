"""
llm.py — 文字生成的統一入口。

meta.py 和 new.py 都只呼叫這裡的 ask(),換供應商只改這一個檔案。

.env 設定:
    LLM_PROVIDER=openrouter          # 或 gemini
    OPENROUTER_API_KEY=sk-or-v1-xxx
    OPENROUTER_MODEL=google/gemini-2.5-flash    # 可留空,預設如右
    GEMINI_API_KEY=xxx               # 用 gemini 時才需要

OpenRouter 是 OpenAI 相容格式,所以用 requests 直接打即可,不必裝額外套件。
"""

import json
import os
import re
import sys

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OR_MODEL = "google/gemini-2.5-flash"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def _strip_fence(s: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", s.strip()).strip()


def _ask_openrouter(prompt: str, model: str | None) -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("✗ .env 裡沒有 OPENROUTER_API_KEY")

    r = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            # 這兩個是 OpenRouter 的選填欄位,填了會出現在他們的排行榜
            "HTTP-Referer": "https://wenziji.local",
            "X-Title": "wenziji",
        },
        json={
            "model": model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_OR_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        },
        timeout=180,
    )
    if not r.ok:
        sys.exit(f"✗ OpenRouter {r.status_code}: {r.text[:300]}")
    data = r.json()
    if "choices" not in data:
        sys.exit(f"✗ OpenRouter 回傳異常: {json.dumps(data, ensure_ascii=False)[:300]}")
    return data["choices"][0]["message"]["content"]


def _ask_gemini(prompt: str, model: str | None) -> str:
    try:
        from google import genai
    except ImportError:
        sys.exit("✗ 缺套件:pip install google-genai(或把 LLM_PROVIDER 設成 openrouter)")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("✗ .env 裡沒有 GEMINI_API_KEY")
    client = genai.Client(api_key=key)
    resp = client.models.generate_content(
        model=model or DEFAULT_GEMINI_MODEL, contents=prompt
    )
    return resp.text


def ask(prompt: str, model: str | None = None) -> str:
    """回傳純文字。"""
    provider = (os.environ.get("LLM_PROVIDER") or "openrouter").lower()
    if provider == "gemini":
        return _ask_gemini(prompt, model)
    return _ask_openrouter(prompt, model)


def ask_json(prompt: str, model: str | None = None) -> dict:
    """回傳解析後的 JSON;模型偶爾會加上 markdown 圍欄,這裡一併清掉。"""
    raw = _strip_fence(ask(prompt, model))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(f"✗ 模型回傳的不是合法 JSON:\n{raw[:400]}")


if __name__ == "__main__":
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    provider = os.environ.get("LLM_PROVIDER", "openrouter")
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_OR_MODEL)
    print(f"provider={provider}  model={model}")
    print(ask("用一句話說明什麼是排版的留白。只回一句,不要開場白。"))
