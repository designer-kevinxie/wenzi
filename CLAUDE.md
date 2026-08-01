# 文字紀 pipeline

一句引文 → 配音 + 影片(9:16)+ 靜圖卡片(3:4),發小紅書。
Python 產資料 → Remotion 渲染 → 歸檔到 `releases/`。
架構細節見 `README.md`,這裡只寫**每次會話都該記得的事**。

## 常用命令

```bash
cd pipeline

python3 new.py "引文" --author 加缪 --book 重返提帕萨   # 一句 → quote json
python3 publish.py quotes/<slug>.json --meta            # 完整出片
python3 publish.py quotes/<slug>.json --card-only --no-tw  # 只重印簡體卡片
python3 batch.py --dry                                  # Sheet 佇列,先看再跑
python3 set_traditional.py s2tw                         # 批量切繁簡
python3 meta.py quotes/<slug>.json                      # 只重出文案

cd remotion && npm run dev                              # Studio 預覽
```

## 讀這些檔案之前不要猜

- 排版數學 → `remotion/src/components/FullQuoteCard.tsx`
- 紙紋與壓印 → `remotion/src/components/PaperBase.tsx`
- 出片流程與歸檔 → `pipeline/publish.py`
- 繁簡轉換 → `pipeline/traditional.py` 的 `convert_quote()`

## 關鍵約定(從程式碼看不出來)

**兩個渲染入口,新的 prop 兩邊都要傳一次。**
影片走 `remotion/src/LiteraryQuote.tsx`,靜圖走 `remotion/src/QuoteCard.tsx`。
只改一邊的症狀是「影片對了但圖沒變」,不報錯。
`Root.tsx` 引用的才是真的 —— 改之前先 `grep QuoteCard src/Root.tsx`。

**`remotion/public/manifest.json` 是單一共享檔案。**
只裝得下最後一次 `generate.py` 的那一則。跳過 generate 直接渲染,
會渲出「上一則的文字 + 這一則的檔名」。`publish.py` 的
`manifest_matches()` 是防這個的,別繞過它。

**繁簡由 quote json 的 `traditional` 欄位決定,轉換發生在 generate.py。**
目前全站 `s2tw`(台灣字形,配台版字體)。
`segments` / `author` / `book` 一律存簡體原文,繁體只發生在渲染前。
送 TTS 前一律 `to_simplified()`,所以切繁簡不影響配音快取。

**排版數學假設中文全形等寬。**
`autoFontSize()` 用「每行字數 = 框寬 ÷ (字級 + 字距)」推算,不量 DOM。
換成英文等比例字體這套公式直接失效,要換成真正的文字量測。

**成本:TTS 有快取(`pipeline/.tts_cache/`),重跑不花額度。**
LLM 每則固定 2 次呼叫(分段英譯 + 文案),`--no-meta` 可省一次。
渲染是本機 CPU。所以重印卡片幾乎免費,放心重印。

## 不要做

- **不要用「失敗即空白」的機制。** `mask-image` 找不到檔案時 Chromium
  當成全透明,結果是整塊內容消失,只有 console 一條 404。
  同樣效果用疊加層(`mixBlendMode`)做,載入失敗只是沒效果。
- **不要往陣列裡加還不存在的檔名。** `PaperBase.tsx` 的 `PAPERS` 曾經
  預設三個檔名但只有一個檔案存在,三分之二的引文靜默失去紙紋。
  改素材相關的常數前先 `ls remotion/public/`。
- **不要複述引文。** `meta.py` 的文案是給搜尋和補充背景用的,
  讀者已經在圖上讀完了。作者名與書名要出現(搜尋只索引文字),
  但不要整句照抄。
- **不要在 quote json 之外硬編內容。** quote json 是唯一的資料來源,
  PNG/MP4 都是可重生的產物。
- 不要提交 `.env`、`releases/`、`.tts_cache/`、`remotion/out/`。

## 驗證方式

改了排版就實際渲一張出來看,不要只看程式碼是否合理:

```bash
cd pipeline && python3 publish.py quotes/<slug>.json --card-only --no-tw
open ../releases/          # 用眼睛確認
```

「編譯通過 + 邏輯自洽 + 結果是空白」發生過不只一次。

## 發布側的約定(會影響技術決策)

- 小紅書**發布後不要編輯** —— 會重新審核並退出初始流量池。
- 卡片繁體(視覺),文案與標題簡體(搜尋與互動)。
- 目前只發小紅書圖文。影片鏈路能跑但還沒鋪視頻號/抖音。
- 收藏率是這個品類的核心指標,不是點讚。

## 已知待決

- `safeMode` 欄位寫進 manifest 但沒有任何元件讀它 —— 補說明或刪掉。
- Google Sheet 的 Apps Script 沒進版本庫,`batch.py` 的後端別人裝不起來。
- `remotion/public/bgm.mp3` 的授權來源未確認,鋪海外平台前要查。
