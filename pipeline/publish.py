"""
publish.py — 一條命令出片。

    python3 publish.py quotes/hesse_summer.json

流程:
    1. generate.py  配音 + manifest(有快取,重跑不花額度)
    2. remotion     渲染影片
    3. remotion     導出靜圖卡片(3:4 給小紅書、9:16 給備用)
    4. 重命名歸檔到 releases/

選項:
    --meta          出片後用模型生成各平台文案(簡體 + 繁體海外版)
    --copy tw       文案複製到剪貼簿時取繁體海外版(預設取小紅書簡體版)
    --skip-gen      跳過步驟 1(只改了排版、配音沒變時用)
    --card-only     只出靜圖,不渲影片(改了卡片排版想重印時用)
    --no-card       不出靜圖
    --video-only    等同 --no-card
    --open          出片後用 Finder 打開 releases 資料夾

只想重印某一則的卡片:

    python3 publish.py quotes/<slug>.json --card-only

配音有快取,所以這條命令不花 TTS 額度;不加 --meta 就連 LLM 也不呼叫,
整條命令是純本機渲染。
"""

import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from traditional import to_simplified

ROOT = Path(__file__).resolve().parent          # …/wenziji/pipeline
PROJECT = ROOT.parent                            # …/wenziji
REMOTION = PROJECT / "remotion"
RELEASES = PROJECT / "releases"
MANIFEST = REMOTION / "public" / "manifest.json"


def run(cmd, cwd, label):
    print(f"\n▶ {label}")
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0:
        sys.exit(f"✗ {label} 失敗(exit {r.returncode})")


def manifest_matches(quote: dict) -> bool:
    """manifest.json 裡的正文是否就是這一則引文?

    manifest.json 是**單一共享檔案**,只裝得下最後一次 generate 的那一則。
    加了 --skip-gen 卻沒注意到 manifest 還停在上一條時,渲出來的成品
    會是「上一則的文字 + 這一則的檔名」—— 而且整個流程不會報任何錯。
    這道檢查就是擋這個。

    manifest 存的是繁體(convert_quote 轉過),quote json 是簡體原文,
    所以兩邊都轉成簡體再比。
    """
    if not MANIFEST.exists():
        return False
    try:
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return False
    want = "".join(s["zh"] for s in quote.get("segments", []))
    return to_simplified(m.get("fullText", "")) == to_simplified(want)


def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__)
        return
    flags = {a for a in args if a.startswith("--")}
    positional = [a for a in args if not a.startswith("--") and a != "tw"]
    quote_path = positional[0] if positional else "quotes/hesse_summer.json"

    skip_gen = "--skip-gen" in flags
    want_meta = "--meta" in flags
    copy_market = "overseas" if "tw" in args or "--copy=tw" in flags else "xiaohongshu"
    no_card = "--no-card" in flags or "--video-only" in flags
    card_only = "--card-only" in flags

    if card_only and no_card:
        sys.exit("✗ --card-only 和 --no-card 互相矛盾,只能挑一個")

    qfile = (ROOT / quote_path).resolve()
    if not qfile.exists():
        sys.exit(f"✗ 找不到 {qfile}")
    quote = json.loads(qfile.read_text(encoding="utf-8"))
    qid = quote.get("id") or qfile.stem

    # 1. 配音 + manifest
    if skip_gen:
        if not manifest_matches(quote):
            sys.exit(
                "✗ manifest.json 裡不是這一則引文,--skip-gen 會渲出錯的內容。\n"
                "  拿掉 --skip-gen 重跑即可(配音有快取,不花額度)。"
            )
        print("▶ 跳過 generate(--skip-gen,已確認 manifest 對得上)")
    else:
        run([sys.executable, "generate.py", str(qfile)], ROOT, "生成配音與 manifest")

    # 2. 影片
    if card_only:
        print("\n▶ 跳過影片渲染(--card-only)")
    else:
        run(["npm", "run", "render"], REMOTION, "渲染影片")

    # 3. 靜圖
    if not no_card:
        run(["npm", "run", "card"], REMOTION, "導出卡片 3:4")
        run(["npm", "run", "card:tall"], REMOTION, "導出卡片 9:16")

    # 4. 歸檔
    RELEASES.mkdir(exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    base = f"{stamp}_{qid}"

    moves = [] if card_only else [("out/video.mp4", f"{base}.mp4")]
    if not no_card:
        moves += [
            ("out/card.png", f"{base}_card.png"),
            ("out/card-tall.png", f"{base}_card-tall.png"),
        ]

    print("\n▶ 歸檔")
    done = []
    for src_rel, dst_name in moves:
        src = REMOTION / src_rel
        if not src.exists():
            print(f"  ! 找不到 {src_rel},跳過")
            continue
        dst = RELEASES / dst_name
        if dst.exists():                       # 同日重出,加序號不覆蓋
            n = 2
            while (RELEASES / f"{dst.stem}-{n}{dst.suffix}").exists():
                n += 1
            dst = RELEASES / f"{dst.stem}-{n}{dst.suffix}"
        shutil.move(str(src), str(dst))
        size = dst.stat().st_size / 1_048_576
        print(f"  ✓ {dst.name}  ({size:.1f} MB)")
        done.append(dst)

    # 附上引文資訊,發布時方便查。--card-only 是重印,不重寫這份。
    if done and not card_only:
        info = {
            "id": qid,
            "book": quote.get("book", ""),
            "author": quote.get("author", ""),
            "text": "".join(s["zh"] for s in quote.get("segments", [])),
            "files": [d.name for d in done],
            "date": stamp,
        }
        (RELEASES / f"{base}.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # 5. 各平台文案
    if want_meta:
        print("\n▶ 生成發布文案")
        import meta as meta_mod
        data = meta_mod.generate(quote)
        md = meta_mod.render(data, quote)
        mpath = RELEASES / f"{base}_meta.md"
        mpath.write_text(md, encoding="utf-8")
        print(f"  ✓ {mpath.name}")
        clip = meta_mod.section_for_clipboard(data, copy_market)
        if meta_mod.copy_to_clipboard(clip):
            label = "繁體海外版" if copy_market == "overseas" else "小紅書簡體版"
            print(f"  ✓ 已複製{label}到剪貼簿,貼上即可")

    print(f"\n✓ 完成 → {RELEASES}")

    if "--open" in flags and sys.platform == "darwin":
        subprocess.run(["open", str(RELEASES)])


if __name__ == "__main__":
    main()
