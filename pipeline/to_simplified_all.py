"""一次性腳本:把所有 quote json 的顯示字切回簡體。

    python3 to_simplified_all.py          # 執行
    python3 to_simplified_all.py --dry    # 只看會改哪些,不寫入

做的事只有一件:把 traditional 欄位設成 null。
convert_quote() 在這個欄位為假值時直接原樣回傳,於是顯示字維持簡體原文。

不動的東西:
  · segments / author / book —— 本來就是簡體原文,模型產出時就是
  · 配音 —— generate.py 一律 to_simplified() 之後才送 TTS,
    所以 .tts_cache 全部命中,重印不花額度
  · meta.py —— 本來就簡繁雙軌,不受影響

quotes/ 有進 git,出事就 `git checkout -- quotes/`,所以這裡不另外做備份。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUOTES = ROOT / "quotes"

# 用來偵測殘留繁體字的抽樣集合。不求完整,只要能提醒就夠。
TRAD_HINT = set("愛醒還遠響聲個裡溼爾書寫學國會來時無為與說給關開這")


def main():
    dry = "--dry" in sys.argv[1:]

    files = sorted(QUOTES.glob("*.json"))
    if not files:
        sys.exit(f"✗ {QUOTES} 裡沒有 json")

    changed, already, tts_trad = [], [], []

    for p in files:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ! {p.name} 讀取失敗:{e}")
            continue

        # title_tts_text 若殘留繁體只是不好看,不影響發音 ——
        # generate.py 送 TTS 之前一律轉簡體。這裡只提醒,不動它。
        if set(d.get("title_tts_text", "")) & TRAD_HINT:
            tts_trad.append(p.name)

        if not d.get("traditional"):
            already.append(p.name)
            continue

        old = d["traditional"]
        d["traditional"] = None
        if not dry:
            p.write_text(
                json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        changed.append((p.name, old))

    verb = "會改" if dry else "已改"
    for name, old in changed:
        print(f"  ✓ {name}  {old} → null")
    for name in already:
        print(f"  – {name}  本來就是簡體")

    print(f"\n{verb} {len(changed)} 份,{len(already)} 份無需變動。")

    if tts_trad:
        print(
            f"\n  註:{len(tts_trad)} 份的 title_tts_text 帶繁體字"
            f"({', '.join(tts_trad[:3])}{'…' if len(tts_trad) > 3 else ''})。"
        )
        print("     不影響發音(送 TTS 前一律轉簡體),不用管。")

    if dry:
        print("\n(--dry 模式,沒有寫入)")
    elif changed:
        print("\n下一步:重印卡片(配音走快取,不花額度)")
        print("  python3 publish.py quotes/<slug>.json --card-only")
        print("\n改壞了就 git checkout -- quotes/")


if __name__ == "__main__":
    main()
