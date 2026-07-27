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


def fetch_pending():
    r = requests.get(URL, params={"token": TOKEN}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        sys.exit(f"✗ Web App 回應錯誤:{data['error']}(檢查 token)")
    return data.get("pending", [])


def write_back(updates):
    """updates = [{'row':3,'status':'done','note':'...'}]"""
    if not updates:
        return
    try:
        requests.post(URL, json={"token": TOKEN, "updates": updates}, timeout=30)
    except Exception as e:
        print(f"  ! 回寫 Sheet 失敗(不影響出片):{e}")


def build_quote_arg(item):
    """把 sheet 的一行組成 new.py 能吃的引文字串。
    Sheet 欄位裡可能夾帶多餘的書名號、破折號、或詩歌換行,先清掉。
    書名號由程式加;換行收成單一空格再交給模型斷句。"""
    # 保留詩歌換行(收成單一換行),只清掉行首行尾多餘空白
    text = "\n".join(line.strip() for line in item["text"].strip().splitlines() if line.strip())
    author = item.get("author", "").strip().lstrip("—–-").strip()
    book = item.get("book", "").strip().strip("《》「」『』").strip()

    if book:
        return f"{text}——{author}《{book}》"
    if author:
        return f"{text}——{author}"
    return text


def run_one(item, want_meta: bool) -> tuple[bool, str]:
    """跑 new.py(不 --go)拿到 slug,再跑 publish.py。回傳 (成功, 訊息)。"""
    # 顯式傳 --author/--book,text 原樣傳入 —— 這樣詩歌內部的破折號、換行
    # 不會被當成作者分隔符,也不會有書名號重複問題。
    text = "\n".join(l.strip() for l in item["text"].strip().splitlines() if l.strip())
    author = item.get("author", "").strip().lstrip("—–-").strip()
    book = item.get("book", "").strip().strip("《》「」『』").strip()

    cmd = [sys.executable, "new.py", text]
    if author:
        cmd += ["--author", author]
    if book:
        cmd += ["--book", book]

    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(p.stdout)
    if p.returncode != 0:
        return False, (p.stderr or p.stdout)[-200:]

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
        return False, (p2.stderr or p2.stdout)[-200:]

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
        tag = f"《{it['book']}》" if it.get("book") else (it.get("author") or "")
        print(f"  [{it['row']}] {it['text'][:30]}  {tag}")

    if dry:
        print("\n(--dry 模式,不出片)")
        return

    print()
    ok_count = 0
    for it in pending:
        row = it["row"]
        print(f"\n{'='*50}\n▶ 第 {row} 行:{it['text'][:30]}…")
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
            write_back([{"row": row, "status": "error", "note": msg}])
            print(f"  ✗ {msg}")

    print(f"\n{'='*50}\n✓ 完成 {ok_count}/{len(pending)}  → {RELEASES}")


if __name__ == "__main__":
    main()
