"""一次性腳本:批量切換所有 quote json 的顯示字。

    python3 set_traditional.py s2tw     # 全部轉繁體(台灣字形,配台版字體)
    python3 set_traditional.py s2t      # 全部轉繁體(通用字形)
    python3 set_traditional.py none     # 全部維持簡體原文
    python3 set_traditional.py s2tw --dry   # 只看會改哪些,不寫入

改的只有 traditional 欄位。convert_quote() 在這個欄位為假值時
直接原樣回傳,於是顯示字維持簡體;給了模式就按該模式轉換。

**不動的東西:**
  · segments / author / book —— 一律是簡體原文,模型產出時就是。
    繁體只發生在渲染前的轉換,不進 quote json。
  · 配音 —— generate.py 送 TTS 之前一律 to_simplified(),
    所以 .tts_cache 全部命中,重印不花額度。
  · meta.py —— 本來就簡繁雙軌(小紅書簡體、海外繁體),不受影響。

quotes/ 有進 git,出事就 `git checkout -- quotes/`,所以不另外做備份。

改完記得重印:
    python3 publish.py quotes/<slug>.json --card-only
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUOTES = ROOT / "quotes"

MODES = {
    "s2tw": "繁體(台灣字形:裡、溼、麵)",
    "s2t": "繁體(通用字形)",
    "s2hk": "繁體(香港字形)",
    "none": "簡體(不轉換)",
}


def main():
    args = sys.argv[1:]
    dry = "--dry" in args
    positional = [a for a in args if not a.startswith("--")]

    if not positional or positional[0] not in MODES:
        print(__doc__)
        print("可用模式:")
        for k, v in MODES.items():
            print(f"    {k:<6} {v}")
        sys.exit(1)

    mode = positional[0]
    value = None if mode == "none" else mode

    files = sorted(QUOTES.glob("*.json"))
    if not files:
        sys.exit(f"✗ {QUOTES} 裡沒有 json")

    changed, same = [], []

    for p in files:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ! {p.name} 讀取失敗:{e}")
            continue

        old = d.get("traditional")
        if old == value:
            same.append(p.name)
            continue

        d["traditional"] = value
        if not dry:
            p.write_text(
                json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        changed.append((p.name, old))

    print(f"目標:{MODES[mode]}\n")
    for name, old in changed:
        print(f"  ✓ {name}  {old!r} → {value!r}")
    for name in same:
        print(f"  – {name}  已經是了")

    verb = "會改" if dry else "已改"
    print(f"\n{verb} {len(changed)} 份,{len(same)} 份無需變動。")

    if dry:
        print("\n(--dry 模式,沒有寫入)")
    elif changed:
        print("\n下一步:重印卡片(配音走快取,不花額度)")
        print("  python3 publish.py quotes/<slug>.json --card-only --no-tw")
        print("\n改壞了就 git checkout -- quotes/")


if __name__ == "__main__":
    main()
