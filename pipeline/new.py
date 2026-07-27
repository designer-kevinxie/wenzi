"""
new.py — 一句話 → 可直接出片的 quote json。

    python3 new.py "不被爱仅是时运不济，而无力去爱才是真正的灾难。" --author 加缪 --book 重返提帕萨

作者出處也可以直接黏在句子後面,會自動解析:
    python3 new.py "不被爱仅是时运不济，而无力去爱才是真正的灾难。——加缪《重返提帕萨》"

但**明確傳了 --author / --book 時就不會再猜**,句尾原樣保留 ——
詩歌的末行常常長得像署名(如「——对自己的爱」),猜錯會把正文吃掉一行。

模型負責三件事:
    1. 斷句分段(每段一屏,依語氣停頓而非字數硬切)
    2. 逐段英譯(必須與中文分段語意對應)
    3. 生成檔名 slug

產出 quotes/<slug>.json,印出來讓你過目。斷句是編輯決策,
覺得不對就直接改 json 裡的 segments,那是最該由人決定的部分。

拼回校驗不通過時**以 exit code 2 結束**,好讓 batch.py 判定為失敗、
不會拿著錯的 segments 繼續出片。json 仍會寫出來供你手動修。

選項:
    --go        生成後立刻跑 publish.py 出片
    --voice ID  指定 voice_id(預設沿用 quotes/ 裡最近一份的設定)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from llm import ask_json

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")
QUOTES = ROOT / "quotes"

PROMPT = """把下面這則引文整理成短視頻用的資料。

引文:{text}
作者:{author}
出處:{book}

任務:
1. segments — 把引文切成 2-4 段,每段一屏顯示。
   斷句依「語氣停頓與呼吸」,不是按字數硬切。優先在逗號、分號、轉折處斷。
   每段中文控制在 22 字以內;若原句很短(20 字以內)就只切 1-2 段。
   標點保留在該段末尾。

   **只能切,不能改。** 所有段落拼起來必須與原句完全一致,一字不差,
   標點也一個不差。特別注意這三點:
   - 原句末尾沒有句號時,不要補句號。詩歌尤其常常沒有句末標點。
   - 原句最後一行看起來像署名或題獻(例如「——对自己的爱」)時,
     那也是正文的一部分,要照樣切進 segments,不可以丟掉。
   - 不要把簡體改成繁體,也不要順手改錯字。

2. 每段附英譯 en,必須與該段中文語意對應(不是整句英譯後亂切)。
   英譯要有文學感,不要直譯腔。分段處用逗號或分號銜接,讀起來像完整一句。
3. author / book — 若上面已給就照用;沒給而你確定知道出處,就補上;
   不確定就留空字串,不要編造。
4. slug — 英文小寫檔名,格式 <作者姓氏拼音或英文>_<關鍵詞>,例如 camus_tipasa、hesse_summer。
5. title_tts — 給語音朗讀用。**有書名就只寫書名,沒有書名才寫作者名**,
   兩者不要同時出現(連讀囉嗦,且音譯名容易讀錯)。格式「[somber] 書名。」

只回傳 JSON,不要任何說明文字、不要 markdown 圍欄:
{{
  "slug": "",
  "author": "",
  "book": "",
  "segments": [{{"zh": "", "en": ""}}],
  "title_tts": ""
}}"""


QUOTE_MARKS = "「」『』“”\"\u2018\u2019''"

# 模型最愛多補的尾部標點。只有「多出來的全是這些字元」時才自動修,
# 少一個字、改一個字都不在自動修復範圍內 —— 那種要人看。
TRAILING_PUNCT = "。．.！!？?、,，；;：:…"


def _looks_like_name(s: str) -> bool:
    """作者名通常很短且不含句內標點 —— 用來避免把句中的破折號誤判成署名分隔。"""
    return 0 < len(s) <= 10 and not re.search(r"[，。、；：！？]", s)


def strip_quotes(s: str) -> str:
    """剝掉包住整句的引號。引號是引用標記,不是句子的一部分,
    留著會讓模型分段時無所適從,也會讓拼回校驗誤判。"""
    s = s.strip()
    while s and s[0] in QUOTE_MARKS:
        s = s[1:].strip()
    while s and s[-1] in QUOTE_MARKS:
        s = s[:-1].strip()
    return s


def normalize(s: str) -> str:
    """校驗用:去掉空白與所有引號後再比對。"""
    s = re.sub(r"\s", "", s)
    return "".join(c for c in s if c not in QUOTE_MARKS)


def parse_inline(text: str, want_author: bool = True, want_book: bool = True):
    """把黏在句子後面的作者出處拆出來。

    want_author / want_book 為 False,代表呼叫端已經明確給了該欄位。
    這時**絕不能再從句尾猜** —— 詩歌的末行常常長得像署名
    (例如「——对自己的爱」),一猜錯就把正文悄悄吃掉一行,而且不報錯。
    """
    # 先把可能重複的書名號收斂成單層:《《X》》 → 《X》
    text = re.sub(r"《+\s*([^《》]+?)\s*》+", r"《\1》", text)
    author = book = ""

    # 「——作者《書名》」一次吃掉,只有兩者都要猜時才適用
    if want_author and want_book:
        m = re.search(r"[—–\-]{1,2}\s*([^《》\n]+?)\s*《([^》]+)》\s*$", text)
        if m and _looks_like_name(m.group(1).strip()):
            author, book = m.group(1).strip(), m.group(2).strip()
            return strip_quotes(text[: m.start()].strip()), author, book

    if want_book:
        m = re.search(r"《([^》]+)》\s*$", text)
        if m:
            book = m.group(1).strip()
            text = text[: m.start()].strip()

    if want_author:
        m = re.search(r"[—–\-]{1,2}\s*([^\n]+?)\s*$", text)
        if m and _looks_like_name(m.group(1).strip()):
            author = m.group(1).strip()
            text = text[: m.start()].strip()
        else:
            # 沒有破折號,但作者直接黏在收尾引號後面:「…消失。」于堅
            m = re.search(r"[」』”\u2019\"]\s*([^」』”\u2019\"\n]{1,10})\s*$", text)
            if m and _looks_like_name(m.group(1).strip()):
                author = m.group(1).strip()
                text = text[: m.start() + 1].strip()

    return strip_quotes(text), author, book


def last_tts_config():
    """沿用最近一份 quote json 的 tts 設定,免得每次重填 voice_id。"""
    files = sorted(QUOTES.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if d.get("tts", {}).get("voice_id"):
                return d["tts"], d.get("theme", {}), d.get("timing", {})
        except Exception:
            continue
    return (
        {"provider": "elevenlabs", "voice_id": "REPLACE_WITH_YOUR_VOICE_ID",
         "model_id": "eleven_v3", "stability": 0.0},
        {}, {},
    )


def ask_llm(text, author, book) -> dict:
    return ask_json(
        PROMPT.format(text=text, author=author or "(未提供)",
                      book=book or "(未提供)")
    )


def repair_trailing_punct(original: str, segments: list) -> str:
    """模型偶爾會在最後一段補上原句沒有的句末標點 —— 詩歌尤其常見,
    因為訓練語料裡的句子多半有句號。

    這一種偏差是可以確定性修復的:從最後一段的尾巴逐個刪標點,
    刪到拼回結果與原句完全相符為止。刪不到相符就整個放棄(不留半殘狀態),
    交給 verify 報錯讓人看。少字、改字一律不碰。

    回傳被刪掉的字串(沒改動則回傳空字串)。
    """
    if not segments:
        return ""

    target = normalize(original)
    head = "".join(s["zh"] for s in segments[:-1])
    last = segments[-1]["zh"]

    if normalize(head + last) == target:
        return ""                       # 本來就對,不用修

    trimmed, removed = last, ""
    while trimmed and (trimmed[-1] in TRAILING_PUNCT or trimmed[-1].isspace()):
        removed = trimmed[-1] + removed
        trimmed = trimmed[:-1]
        if normalize(head + trimmed) == target:
            segments[-1]["zh"] = trimmed
            return removed
    return ""                           # 刪光標點還是不符 → 不是這種問題


def verify(original: str, segments: list) -> bool:
    """分段拼回去必須與原句一致 —— 這是最容易出錯也最該檢查的一點。"""
    a = normalize("".join(s["zh"] for s in segments))
    b = normalize(original)
    if a != b:
        print("  ! 分段拼回與原句不符,請檢查 segments:")
        print(f"    原句: {b}")
        print(f"    拼回: {a}")
        # 指出第一個分歧的位置,比自己用眼睛對兩行字快得多
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                print(f"    第 {i + 1} 字起分歧: 拼回「{a[i:i+8]}」 vs 原句「{b[i:i+8]}」")
                break
        else:
            longer, label = (a, "拼回") if len(a) > len(b) else (b, "原句")
            print(f"    長度不同,{label}多出: 「{longer[min(len(a), len(b)):]}」")
        return False
    return True


def main():
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return

    flags = {a for a in args if a.startswith("--")}
    vals = {}
    positional = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--author", "--book", "--voice"):
            vals[a.lstrip("-")] = args[i + 1] if i + 1 < len(args) else ""
            i += 2
            continue
        if not a.startswith("--"):
            positional.append(a)
        i += 1

    raw_text = " ".join(positional).strip()
    if not raw_text:
        sys.exit("✗ 請提供引文")

    # 已經明確給的欄位就不要再猜,避免把正文末行當成署名剝掉
    text, in_author, in_book = parse_inline(
        raw_text,
        want_author=not vals.get("author"),
        want_book=not vals.get("book"),
    )
    author = vals.get("author") or in_author
    book = vals.get("book") or in_book

    print(f"▶ 引文: {text}")
    print(f"  作者: {author or '(交給模型判斷)'}  出處: {book or '(交給模型判斷)'}")
    print("\n▶ 分段與英譯中…")
    g = ask_llm(text, author, book)

    segments = g.get("segments", [])
    removed = repair_trailing_punct(text, segments)
    if removed:
        print(f"  · 已自動移除模型多加的句末標點「{removed}」")
    ok = verify(text, segments)

    tts, theme, timing = last_tts_config()
    if vals.get("voice"):
        tts = {**tts, "voice_id": vals["voice"]}

    slug = g.get("slug") or "untitled"
    quote = {
        "id": f"{slug}_001",
        "lang": "zh",
        "book": g.get("book", book),
        "author": g.get("author", author),
        "segments": segments,
        "traditional": None,
        "hook_video": "hook.mp4",
        "tts": tts,
        "title_tts_text": g.get("title_tts", ""),
        "timing": timing or {"hook_sec": 4.0, "title_overlap_sec": 1.0,
                             "seg_gap_sec": 0.45, "full_sec": 6.0},
        "theme": theme,
        "music": "bgm.mp3",
        "safeMode": True,
    }

    out = QUOTES / f"{slug}.json"
    n = 2
    while out.exists():
        out = QUOTES / f"{slug}-{n}.json"
        n += 1
    out.write_text(json.dumps(quote, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✓ {out.relative_to(ROOT)}\n")
    for i, s in enumerate(segments, 1):
        print(f"  {i}. {s['zh']}")
        print(f"     {s.get('en','')}")
    print(f"\n  朗讀: {quote['title_tts_text']}")

    if not ok:
        # exit code 2 —— json 已寫出供手動修,但呼叫端(batch.py)要知道這次失敗了,
        # 不能拿著錯的 segments 繼續出片。
        print("\n  先修好 segments 再出片。")
        sys.exit(2)

    if "--go" in flags:
        print()
        subprocess.run([sys.executable, "publish.py", str(out.relative_to(ROOT)),
                        "--meta", "--open"], cwd=ROOT)
    else:
        print(f"\n  下一步: python3 publish.py {out.relative_to(ROOT)} --meta --open")


if __name__ == "__main__":
    main()
