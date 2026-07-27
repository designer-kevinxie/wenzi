"""一次性腳本:清掉舊 quote json 裡「書名,作者」並存的朗讀文本。

刪掉 title_tts_text 之後,generate.py 會自動組成「[somber] 書名。」
(沒有書名則用作者名),這是新的規則:有書名就只讀書名。

比對時統一轉簡體 —— json 裡的 author/book 是簡體原文,
但 title_tts_text 可能是繁體,直接比對會漏判。

    python3 fix_title_tts.py
"""
import glob
import json
from pathlib import Path

from traditional import to_simplified

for f in sorted(glob.glob("quotes/*.json")):
    p = Path(f)
    d = json.loads(p.read_text(encoding="utf-8"))
    old = d.get("title_tts_text", "")
    book, author = d.get("book", ""), d.get("author", "")
    spoken = book if book else author

    old_s = to_simplified(old)
    has_both = bool(
        old and book and author
        and to_simplified(author) in old_s
        and to_simplified(book) in old_s
    )

    if has_both:
        d.pop("title_tts_text")
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ {p.name}: 移除「{old}」→ 自動讀「[somber] {spoken}。」")
    else:
        print(f"  – {p.name}: 不變（{old or '自動: [somber] ' + spoken + '。'}）")
