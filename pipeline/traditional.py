"""
繁體轉換 —— 必須在送進 TTS 之前執行.

理由: ElevenLabs 的字元級時間戳對應的是「輸入的字元」.
若先用簡體配音、事後才把字幕轉繁體,遇到一對多轉換(裡/里、乾/幹)
字數會對不上,逐字動畫整體錯位.

pip install opencc-python-reimplemented
"""

from opencc import OpenCC

# s2t   = 純字形轉換(文學引文建議用這個,不動譯者用詞)
# s2twp = 連詞彙一起換成台灣用語(軟件→軟體),適合口語內容
_CONVERTERS = {}


def to_traditional(text: str, config: str = "s2tw") -> str:
    if not text:
        return text
    if config not in _CONVERTERS:
        _CONVERTERS[config] = OpenCC(config)
    return _CONVERTERS[config].convert(text)


def to_simplified(text: str) -> str:
    """繁 → 簡。給小紅書/抖音文案用:quote 裡的 zh 已是繁體顯示字,
    餵給模型前要轉回簡體,否則簡體平台會輸出繁體字。"""
    if not text:
        return text
    if "t2s" not in _CONVERTERS:
        _CONVERTERS["t2s"] = OpenCC("t2s")
    return _CONVERTERS["t2s"].convert(text)


def convert_quote(quote: dict) -> dict:
    """把 quote json 裡所有中文欄位轉成繁體(原地回傳新 dict)."""
    cfg = quote.get("traditional", "s2tw")
    if not cfg:
        return quote

    q = {**quote}
    for key in ("text", "author", "source", "book", "title_tts_text", "body_tts_text"):
        if key in q and isinstance(q[key], str):
            q[key] = to_traditional(q[key], cfg)

    # 分段正文:只轉中文,英文原樣保留
    if "segments" in q and isinstance(q["segments"], list):
        q["segments"] = [
            {**s, "zh": to_traditional(s["zh"], cfg)} if isinstance(s, dict) and "zh" in s else s
            for s in q["segments"]
        ]

    if "hook" in q and isinstance(q["hook"], dict):
        hook = {**q["hook"]}
        for key in ("title", "line", "tts_text"):
            if key in hook and isinstance(hook[key], str):
                hook[key] = to_traditional(hook[key], cfg)
        q["hook"] = hook

    if "branding" in q and isinstance(q["branding"], dict):
        b = {**q["branding"]}
        if "watermark" in b:
            b["watermark"] = to_traditional(b["watermark"], cfg)
        q["branding"] = b

    return q


if __name__ == "__main__":
    demo = {
        "text": "不被爱仅是时运不济，而无力去爱才是真正的灾难。",
        "author": "加缪",
        "source": "《重返提帕萨》",
    }
    out = convert_quote(demo)
    for k, v in out.items():
        print(f"{k}: {v}")
