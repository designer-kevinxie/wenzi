"""一次性腳本:給現有 quote json 補上 music 欄位。

    python3 add_music.py            # 預設 bgm.mp3
    python3 add_music.py other.mp3  # 指定別的檔名
"""
import glob
import json
import sys
from pathlib import Path

name = sys.argv[1] if len(sys.argv) > 1 else "bgm.mp3"

for f in sorted(glob.glob("quotes/*.json")):
    p = Path(f)
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("music"):
        print(f"  – {p.name}: 已有 {d['music']}")
        continue
    # 插在 theme 後面,保持欄位順序好讀
    out = {}
    for k, v in d.items():
        out[k] = v
        if k == "theme":
            out["music"] = name
    if "music" not in out:
        out["music"] = name
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ {p.name}: 加入 music = {name}")
