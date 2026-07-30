"""
generate.py — 一則引文 → manifest.json + 兩條配音.

用法:
    export ELEVENLABS_API_KEY=xxx      (或放 .env)
    python3 generate.py quotes/hesse_summer.json

產出至 ../remotion/public/:
    manifest.json   給 Remotion 讀的唯一契約
    vo_title.mp3    書名(或作者名)朗讀
    vo_body.mp3     正文朗讀(整段一次生成,事後按段切時間軸)

幕次:
    0        鉤子影片(你自己做的 hook.mp4,含人聲)
    title    書名鈐印 + 朗讀
    body     正文分段,逐段替換
    full     完整句版(自動字級) + logo 落印  ← 可導出成靜圖
"""

import hashlib
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from traditional import convert_quote, to_simplified
from tts_providers import PROVIDERS

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")

FPS = 30
PUBLIC_DIR = ROOT.parent / "remotion" / "public"
CACHE_DIR = ROOT / ".tts_cache"

DEFAULTS = {
    "hook_sec": 4.0,           # 你的 hook.mp4 實際長度
    "title_overlap_sec": 1.0,  # 書名提前壓在鉤子尾巴上的秒數
    "title_lead_sec": 0.5,     # 進入書名幕後,聲音起來前的靜默
    "title_tail_sec": 0.8,  # 書名讀完到正文開始
    "seg_gap_sec": 0.45,    # 每段讀完的停頓
    "body_tail_sec": 1.0,   # 正文讀完到完整句幕
    "full_sec": 6.0,        # 完整句幕停留(給人截圖)
}


def sec2f(sec: float) -> int:
    return int(round(sec * FPS))


# ---------------------------------------------------------------- TTS cache

def cached_tts(provider, text, lang, voice_config, out_path: Path):
    key = hashlib.md5(
        json.dumps([text, lang, voice_config], sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    CACHE_DIR.mkdir(exist_ok=True)
    audio_c, meta_c = CACHE_DIR / f"{key}.mp3", CACHE_DIR / f"{key}.json"

    if audio_c.exists() and meta_c.exists():
        out_path.write_bytes(audio_c.read_bytes())
        print(f"  cache hit {key}")
        return json.loads(meta_c.read_text(encoding="utf-8"))

    r = provider(text=text, lang=lang, voice_config=voice_config, out_path=out_path)
    meta = {"duration_sec": r["duration_sec"], "words": r["words"]}
    audio_c.write_bytes(out_path.read_bytes())
    meta_c.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta


# ---------------------------------------------------------------- segment split

# 顯示字串裡有、但時間戳流裡沒有的字元(主要是標點)。
# 「——」最常見:它會被上一段的最後一個 word 吃掉。
ORPHAN_PUNCT = set("—–－、，。！？；：…·,.!?;:")


def retag_display(ws, zh_display):
    """把時間戳上的簡體字換回繁體顯示字。

    朗讀送的是簡體(發音準),回傳的時間戳字元因此是簡體;
    但字幕要顯示繁體。繁簡逐字一對一、字數相同,所以能逐位對應。

    但**不能假設 ws 的字元數等於顯示字串**。標點(尤其開頭的「——」)
    常被 split_words_by_segment 併進上一段的最後一個 word,長度就對不上。
    盲目按位對應的後果是整段位移、尾巴憑空消失 —— 而且不報錯。

    所以這裡做兩件事:
      1. word 之前若還有顯示字串獨有的標點,先掛到這個 word 前面
      2. 掃完仍有剩字,補回最後一個 word
    保證顯示字串一個字都不會掉。
    """
    chars = [c for c in zh_display if not c.isspace()]
    out, i = [], 0

    for w in ws:
        # 這個 word 不是標點,但顯示字串當前位置是 —— 那是被吃掉的標點,先吐出來
        lead = ""
        while (i < len(chars) and chars[i] in ORPHAN_PUNCT
               and w["text"] and w["text"][0] not in ORPHAN_PUNCT):
            lead += chars[i]
            i += 1

        n = len(w["text"])
        disp = lead + "".join(chars[i:i + n])
        i += n
        out.append({**w, "text": disp or w["text"]})

    # 兜底:真的還有剩字就掛到最後一個 word,寧可時間略早也不要少字
    if i < len(chars) and out:
        out[-1] = {**out[-1], "text": out[-1]["text"] + "".join(chars[i:])}

    return out


def split_words_by_segment(words, segments):
    """
    正文是一次配音,這裡按 segment 的中文內容把逐字時間軸切開.
    以「累積字元比對」推進,標點被併進前一個 word 也能正確吃掉.
    """
    out = []
    idx = 0
    for seg in segments:
        target = "".join(seg["zh"].split())
        acc, taken = "", []
        while idx < len(words) and len(acc) < len(target):
            w = words[idx]
            acc += w["text"]
            taken.append(w)
            idx += 1
        if to_simplified(acc.replace(" ", "")) != to_simplified(target):
            print(f"  ! 對位偏差: 期望「{target}」實得「{acc}」(仍可渲染,建議檢查斷句)")
        out.append(taken)
    if idx < len(words):
        out[-1].extend(words[idx:])   # 殘餘掛到最後一段
    return out


# ---------------------------------------------------------------- main

def main(quote_path: str):
    raw = json.loads(Path(quote_path).read_text(encoding="utf-8"))
    quote = convert_quote(raw)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    provider = PROVIDERS[quote["tts"]["provider"]]
    t = {**DEFAULTS, **quote.get("timing", {})}

    segments = quote["segments"]  # 繁體,給字幕顯示用
    body_text = "".join(s["zh"] for s in segments)

    # ---- 1. 書名(無書名則讀作者)
    book = quote.get("book", "").strip()
    author = quote.get("author", "").strip()
    # 有書名就只讀書名,沒有才讀作者 —— 兩個專有名詞連讀囉嗦,
    # 而且音譯人名/地名本來就容易讀錯,少讀一個少一處風險。
    # 畫面上書名與作者都還在,只是聲音更簡潔。
    spoken_title = book if book else author
    # 朗讀直接吃 raw(quote json 原本的簡體欄位),不要「轉繁體(convert_quote)
    # 再轉回簡體(to_simplified)」—— s2tw 是有損轉換,部分字一對多,
    # 來回轉偶爾會變成另一個同形異音字,送進 TTS 就讀錯音(如「憶」被讀走音)。
    raw_book = raw.get("book", "").strip()
    raw_author = raw.get("author", "").strip()
    raw_spoken_title = raw_book if raw_book else raw_author
    title_read = raw.get("title_tts_text") or f"[somber] {raw_spoken_title}。"
    print("title:", spoken_title)
    tvo = cached_tts(provider, title_read, quote["lang"], quote["tts"], PUBLIC_DIR / "vo_title.mp3")

    # ---- 2. 正文(一次生成,保住朗讀氣口)
    raw_body_text = "".join(s["zh"] for s in raw["segments"])
    body_read = raw.get("body_tts_text", raw_body_text)
    print("body :", body_text[:24], "...")
    bvo = cached_tts(provider, body_read, quote["lang"], quote["tts"], PUBLIC_DIR / "vo_body.mp3")

    # ---- 3. 時間軸
    hook_end = t["hook_sec"]
    # 書名可提前壓在鉤子影片尾巴上(鉤子畫面與聲音都繼續播)
    title_start = hook_end - t.get("title_overlap_sec", 0)
    title_audio_at = title_start + t["title_lead_sec"]
    title_end = title_audio_at + tvo["duration_sec"] + t["title_tail_sec"]

    body_audio_at = title_end
    seg_words = split_words_by_segment(bvo["words"], segments)

    seg_out, cursor = [], body_audio_at
    for i, (seg, ws) in enumerate(zip(segments, seg_words)):
        if not ws:
            continue
        s0, s1 = ws[0]["start"], ws[-1]["end"]
        seg_from = body_audio_at + s0

        # 下台時間 = 下一段第一個字出現的那一刻。
        # 配音是連續的,若用「最後一字結束 + gap」會和下一段重疊,
        # 畫面上會看到兩段的字疊在同一個位置。
        nxt = next((w for w in seg_words[i + 1:] if w), None)
        if nxt:
            seg_to = body_audio_at + nxt[0]["start"]
        else:
            seg_to = body_audio_at + s1 + t["seg_gap_sec"]
        seg_to = max(seg_to, seg_from + 0.4)

        seg_out.append({
            "zh": seg["zh"],
            "en": seg.get("en", ""),
            "fromFrame": sec2f(seg_from),
            "toFrame": sec2f(seg_to),
            "words": [
                {"text": w["text"], "startFrame": sec2f(body_audio_at + w["start"])}
                for w in retag_display(ws, seg["zh"])
            ],
        })
        cursor = seg_to

    body_end = cursor + t["body_tail_sec"]
    full_end = body_end + t["full_sec"]

    attribution = f"－《{book}》{author}" if book else f"－{author}"

    manifest = {
        "fps": FPS, "width": 1080, "height": 1920,
        "durationInFrames": sec2f(full_end),
        "hook": {"src": quote.get("hook_video", "hook.mp4"),
                 "toFrame": sec2f(hook_end)} if quote.get("hook_video", "hook.mp4") else None,
        "acts": {
            "title": {"from": sec2f(title_start), "to": sec2f(title_end)},
            "body":  {"from": sec2f(body_audio_at), "to": sec2f(body_end)},
            "full":  {"from": sec2f(body_end), "to": sec2f(full_end)},
        },
        "audio": {
            "title": {"src": "vo_title.mp3", "startFrame": sec2f(title_audio_at)},
            "body":  {"src": "vo_body.mp3",  "startFrame": sec2f(body_audio_at)},
        },
        "header": {"book": book, "author": author},
        "segments": seg_out,
        "fullText": body_text,
        "attribution": attribution,
        "theme": quote.get("theme", {}),
        "music": quote.get("music"),
        "safeMode": quote.get("safeMode", True),
        "vertical": quote.get("vertical", False),
        "id": quote.get("id", ""),
    }

    out = PUBLIC_DIR / "manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ {out}  總長 {full_end:.1f}s / {manifest['durationInFrames']} frames"
          f"  段數 {len(seg_out)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "quotes/hesse_summer.json")
