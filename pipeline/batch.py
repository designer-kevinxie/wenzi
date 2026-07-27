"""
batch.py — 從 Google Sheet 佇列批次出片。

    python3 batch.py                # 處理所有待做的句子
    python3 batch.py --limit 5      # 只處理前 5 句
    python3 batch.py --no-meta      # 不生成文案(更快)
    python3 batch.py --dry          # 只列出待做,不出片

.env 需要:
    SHEET_WEBAPP_URL=https://script.google.com/macros/s/XXXX/exec
    SHEET_TOKEN=和 Apps Script 裡 TOKEN 一致的字串

流程:抓待做行 → 標記 processing → new.py 生成 quote json →
      publish.py 出片 → 回寫 done(附成品檔名)或 error(附原因)。
狀態即時回寫,所以你手機打開 Sheet 就能看到進度。
"""

import json
import os
import re
import subprocess
import sys
import traceback
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")

URL = os.environ.get("SHEET_WEBAPP_URL", "")
TOKEN = os.environ.get("SHEET_TOKEN", "")
RELEASES = ROOT.parent / "releases"


def clean_item(item: dict) -> dict:
    """把 Sheet 一行清成乾淨的欄位。

    在**入口清一次**,列印和出片就共用同一份結果 ——
    否則會出現顯示《《自爱》》、實際傳的卻是「自爱」這種不一致。

    text 保留詩歌換行(收成單一換行),只清行首行尾空白:
    斷句要參考原本的分行,不能壓成一行。
    """
    return {
        **item,
        "text": "\n".join(
            l.strip() for l in (item.get("text") or "").strip().splitlines() if l.strip()
        ),
        "author": (item.get("author") or "").strip().lstrip("—–-").strip(),
        "book": (item.get("book") or "").strip().strip("《》「」『』").strip(),
    }


def fetch_pending():
    r = requests.get(URL, params={"token": TOKEN}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        sys.exit(f"✗ Web App 回應錯誤:{data['error']}(檢查 token)")
    return [clean_item(x) for x in data.get("pending", [])]


def write_back(updates):
    """updates = [{'row':3,'status':'done','note':'...'}]"""
    if not updates:
        return
    try:
        requests.post(URL, json={"token": TOKEN, "updates": updates}, timeout=30)
    except Exception as e:
        print(f"  ! 回寫 Sheet 失敗(不影響出片):{e}")


def run_one(item, want_meta: bool) -> tuple[bool, str]:
    """跑 new.py(不 --go)拿到 slug,再跑 publish.py。回傳 (成功, 訊息)。"""
    # text 原樣傳入,author / book 走獨立參數 —— new.py 收到明確的
    # --author / --book 就不會再從句尾猜署名,詩歌末行(「——对自己的爱」
    # 這種)才不會被當成署名剝掉。
    cmd = [sys.executable, "new.py", item["text"]]
    if item["author"]:
        cmd += ["--author", item["author"]]
    if item["book"]:
        cmd += ["--book", item["book"]]

    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(p.stdout)
    if p.returncode != 0:
        # new.py 拼回校驗失敗時是 exit 2,錯誤原因印在 stdout 尾巴
        return False, (p.stderr or p.stdout)[-200:].strip()

    m = re.search(r"quotes/[\w\-]+\.json", p.stdout)
    if not m:
        return False, "找不到生成的 quote json(new.py 可能校驗失敗)"
    qpath = m.group(0)

    # publish
    cmd = [sys.executable, "publish.py", qpath]
    if want_meta:
        cmd.append("--meta")
    p2 = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(p2.stdout[-500:])
    if p2.returncode != 0:
        return False, (p2.stderr or p2.stdout)[-200:].strip()

    slug = Path(qpath).stem
    stamp = date.today().strftime("%Y%m%d")
    return True, f"{stamp}_{slug}_001.mp4"


def main():
    if not URL or not TOKEN:
        sys.exit("✗ .env 缺 SHEET_WEBAPP_URL 或 SHEET_TOKEN")

    args = sys.argv[1:]
    want_meta = "--no-meta" not in args
    dry = "--dry" in args
    limit = None
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])

    pending = fetch_pending()
    if limit:
        pending = pending[:limit]

    if not pending:
        print("✓ 佇列是空的,沒有待做的句子。")
        return

    print(f"▶ 待做 {len(pending)} 句:\n")
    for it in pending:
        # 多行的詩收成一行顯示,清單才看得清楚(實際傳給 new.py 的仍是多行)
        preview = " / ".join(it["text"].splitlines())[:36]
        tag = f"《{it['book']}》" if it["book"] else (it["author"] or "")
        print(f"  [{it['row']}] {preview}  {tag}")

    if dry:
        print("\n(--dry 模式,不出片)")
        return

    print()
    ok_count = 0
    failed = []
    for it in pending:
        row = it["row"]
        preview = " / ".join(it["text"].splitlines())[:36]
        print(f"\n{'='*50}\n▶ 第 {row} 行:{preview}…")
        write_back([{"row": row, "status": "processing"}])
        try:
            ok, msg = run_one(it, want_meta)
        except Exception:
            ok, msg = False, traceback.format_exc()[-200:]

        if ok:
            ok_count += 1
            write_back([{"row": row, "status": "done", "note": msg}])
            print(f"  ✓ {msg}")
        else:
            failed.append(row)
            write_back([{"row": row, "status": "error", "note": msg}])
            print(f"  ✗ {msg}")

    print(f"\n{'='*50}\n✓ 完成 {ok_count}/{len(pending)}  → {RELEASES}")
    if failed:
        print(f"✗ 失敗的行:{', '.join(str(r) for r in failed)}(Sheet 的 note 欄有原因)")


if __name__ == "__main__":
    main()
