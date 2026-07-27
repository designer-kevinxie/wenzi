"""
meta.py — 生成各平台的發布文案。

單獨執行:
    python3 meta.py quotes/hesse_summer.json

或由 publish.py 用 --meta 呼叫。

產出 releases/<base>_meta.md,分三區:
    小紅書(簡體)  標題 3 選 1 + 正文 + 標籤
    抖音(簡體)    標題 + 短文案 + 標籤
    海外(繁體)    IG / Threads / YouTube,標籤另成一套

供應商在 .env 裡切換(見 llm.py):
    LLM_PROVIDER=openrouter
    OPENROUTER_API_KEY=sk-or-v1-xxx
"""

import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from llm import ask_json
from traditional import to_traditional, to_simplified

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")

TAGS_FILE = ROOT / "tags.json"


PROMPT = """你是一個文學短視頻帳號「文字紀」的運營。帳號調性:安靜、克制、紙質印刷感,不煽情、不雞湯、不用感嘆號。

這一則的內容:
引文:{text}
作者:{author}
出處:{book}

可用標籤庫(從中挑選,也可自行補充更精準的):
{tags}

請為三個平台生成發布素材,規則如下。

【共通規則】
- 標題絕不包含帳號名。標題是搜尋與點擊的第一權重,要放鉤子或金句本身。
- 標題 20 字以內。不用問號句式以外的標點,不用 emoji。
- 正文開頭幾十字會顯示在信息流,那是第二個鉤子。
- 正文必須包含引文全文與出處(平台搜尋只索引文字,圖片裡的字讀不到)。
- 正文結尾放一個開放式提問,引導留言,但語氣要克制,不要「快來評論區告訴我」這種。
- 標籤大詞 4-5 個 + 精準詞 2-3 個(精準詞如作者名、書名)。

【小紅書】簡體中文。正文 100-150 字。搜尋驅動平台,關鍵詞要自然融入正文。
【抖音】簡體中文。文案 40-60 字,比小紅書更短更直接。
【海外】繁體中文,發 Instagram / Threads / YouTube Shorts,受眾為台港星馬。
      正文 80-120 字。標籤用繁體,並額外附 3-4 個英文標籤。
      注意:用台港慣用的詞彙與語感,不要只是把簡體字轉繁體。

只回傳 JSON,不要任何前後說明、不要 markdown 圍欄:
{{
  "xiaohongshu": {{"titles": ["", "", ""], "body": "", "tags": []}},
  "douyin": {{"titles": ["", ""], "body": "", "tags": []}},
  "overseas": {{"titles": ["", "", ""], "body": "", "tags": [], "tags_en": []}}
}}"""


def _strip_fence(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _sample_tags(broad_n: int = 8, niche_n: int = 6) -> dict:
    """從標籤庫隨機抽一批喂給模型,而不是全給。
    這樣每條的候選標籤都不同,產出的組合自然有變化,
    避免全用同一批標籤被平台判定為重複內容。
    庫可以持續變大,抽樣數不變。"""
    if not TAGS_FILE.exists():
        return {}
    full = json.loads(TAGS_FILE.read_text(encoding="utf-8"))
    out = {}
    for platform, groups in full.items():
        if not isinstance(groups, dict):
            continue
        picked = {}
        for name, items in groups.items():
            if name.startswith("_") or not isinstance(items, list):
                picked[name] = items
                continue
            n = broad_n if name == "broad" else niche_n
            picked[name] = random.sample(items, min(n, len(items)))
        out[platform] = picked
    return out


def generate(quote: dict) -> dict:
    raw_text = "".join(s["zh"] for s in quote.get("segments", [])) or quote.get("text", "")
    text = to_simplified(raw_text)   # quote 裡是繁體顯示字,轉回簡體再餵模型
    tags = _sample_tags()

    prompt = PROMPT.format(
        text=text,
        author=quote.get("author", ""),
        book=quote.get("book", "") or "(無書名)",
        tags=json.dumps(tags, ensure_ascii=False, indent=2),
    )

    data = ask_json(prompt)

    # 保險:簡體平台一律過一次簡體轉換,防止模型受繁體輸入影響而混入繁體字
    for k in ("xiaohongshu", "douyin"):
        d = data.get(k, {})
        d["titles"] = [to_simplified(t) for t in d.get("titles", [])]
        d["body"] = to_simplified(d.get("body", ""))
        d["tags"] = [to_simplified(t) for t in d.get("tags", [])]
        data[k] = d

    # 保險:海外版一律過一次繁體轉換,防止模型漏字
    ov = data.get("overseas", {})
    ov["titles"] = [to_traditional(t) for t in ov.get("titles", [])]
    ov["body"] = to_traditional(ov.get("body", ""))
    ov["tags"] = [to_traditional(t) for t in ov.get("tags", [])]
    data["overseas"] = ov
    return data


def _fmt_tags(tags, prefix="#"):
    return " ".join(f"{prefix}{t.lstrip('#')}" for t in tags)


def render(data: dict, quote: dict) -> str:
    text = "".join(s["zh"] for s in quote.get("segments", [])) or quote.get("text", "")
    L = []
    L.append(f"# {quote.get('book','')} — {quote.get('author','')}\n")
    L.append(f"> {text}\n")

    for key, label, note in [
        ("xiaohongshu", "小紅書(簡體)", "電腦版 creator.xiaohongshu.com 可定時發布,建議排晚上 8-11 點"),
        ("douyin", "抖音(簡體)", "創作者中心同樣支援定時發布"),
        ("overseas", "海外(繁體)", "Instagram / Threads / YouTube Shorts"),
    ]:
        d = data.get(key, {})
        L.append(f"\n---\n\n## {label}")
        L.append(f"_{note}_\n")
        L.append("**標題(擇一)**")
        for i, t in enumerate(d.get("titles", []), 1):
            L.append(f"{i}. {t}")
        L.append("\n**正文**\n")
        L.append(d.get("body", ""))
        L.append("\n**標籤**\n")
        line = _fmt_tags(d.get("tags", []))
        if d.get("tags_en"):
            line += "  " + _fmt_tags(d["tags_en"])
        L.append(line)
    return "\n".join(L) + "\n"


def section_for_clipboard(data: dict, market: str) -> str:
    d = data.get(market, {})
    parts = [d.get("titles", [""])[0], "", d.get("body", ""), "",
             _fmt_tags(d.get("tags", []))]
    if d.get("tags_en"):
        parts[-1] += "  " + _fmt_tags(d["tags_en"])
    return "\n".join(parts)


def copy_to_clipboard(s: str):
    if sys.platform != "darwin":
        return False
    try:
        subprocess.run(["pbcopy"], input=s.encode("utf-8"), check=True)
        return True
    except Exception:
        return False


def main():
    args = sys.argv[1:]
    flags = {a for a in args if a.startswith("--")}
    positional = [a for a in args if not a.startswith("--") and a != "tw"]
    qpath = ROOT / (positional[0] if positional else "quotes/hesse_summer.json")
    if not qpath.exists():
        sys.exit(f"✗ 找不到 {qpath}")

    quote = json.loads(qpath.read_text(encoding="utf-8"))
    data = generate(quote)
    md = render(data, quote)
    print(md)

    # 寫檔到 releases/,命名與影片一致
    from datetime import date

    releases = ROOT.parent / "releases"
    releases.mkdir(exist_ok=True)
    qid = quote.get("id") or qpath.stem
    base = f"{date.today().strftime('%Y%m%d')}_{qid}"
    out = releases / f"{base}_meta.md"
    out.write_text(md, encoding="utf-8")
    print(f"✓ {out}")

    market = "overseas" if ("tw" in args or "--copy=tw" in flags) else "xiaohongshu"
    if copy_to_clipboard(section_for_clipboard(data, market)):
        label = "繁體海外版" if market == "overseas" else "小紅書簡體版"
        print(f"✓ 已複製{label}到剪貼簿")


if __name__ == "__main__":
    main()
