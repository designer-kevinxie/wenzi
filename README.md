# 文字紀 — 文學短片自動化管線

一句引文 → 配音、逐字壓印動畫、成片、靜圖卡片、三平台發布文案。

```bash
python3 new.py "不被爱仅是时运不济，而无力去爱才是真正的灾难。——加缪《重返提帕萨》" --go
```

---

## 目錄

- [核心概念](#核心概念)
- [首次安裝](#首次安裝)
- [素材準備](#素材準備)
- [日常出片](#日常出片)
- [批次出片](#批次出片)
- [七個腳本](#七個腳本)
- [quote json 欄位](#quote-json-欄位)
- [常見調整](#常見調整)
- [設計決策備忘](#設計決策備忘)
- [疑難排解](#疑難排解)
- [成本](#成本)
- [檔案結構](#檔案結構)

---

## 核心概念

整條管線分兩半,中間靠 `manifest.json` 這份契約溝通:

```
pipeline/  (Python)                    remotion/  (React)
─────────────────────                  ─────────────────────
quote json                             讀 manifest.json
   │  new.py 生成                          │
分段 + 英譯                                 │
   │  generate.py                          ▼
配音 + 逐字時間戳  ──→ manifest.json ──→ 渲染四幕 → 影片 + 靜圖
```

**這個分界的意義**:改排版只動 React,改內容只動 Python,兩邊互不干擾。
配音有快取,所以調動畫時重跑幾十次也不花一分錢。

### 幕次結構

| 幕       | 內容                             | 動畫                                                 |
| -------- | -------------------------------- | ---------------------------------------------------- |
| 0 鉤子   | 你自己做的 `hook.mp4`(含人聲)    | —                                                    |
| 1 書名   | 書名 + 作者;無書名則只有作者     | 書名逐字鈐印 → 停 0.4s → 作者整體壓上,之後常駐為頁眉 |
| 2 正文   | 逐段替換,中文逐字 + 英文延遲淡入 | 逐字壓印,下一段開始時上一段淡出                      |
| 3 完整句 | 全文 + 落款 + Logo               | 字級自動計算;這一幕可導出成靜圖                      |

---

## 首次安裝

```bash
# Python 端
pip3 install requests python-dotenv opencc-python-reimplemented

# Remotion 端
cd remotion && npm install
```

在專案根目錄(`wenziji/`,**不是** `pipeline/`)建立 `.env`:

```bash
cp .env.example .env
```

填入:

```
ELEVENLABS_API_KEY=sk_xxx

LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-xxx
OPENROUTER_MODEL=google/gemini-2.5-flash

# 批次出片才需要(見「批次出片」章節)
SHEET_WEBAPP_URL=https://script.google.com/macros/s/XXXX/exec
SHEET_TOKEN=和 Apps Script 裡 TOKEN 一致的字串
```

`.env` 已在 `.gitignore` 裡,不會被推上 git。

測試連通:

```bash
cd pipeline
python3 llm.py          # 印出 provider、model 和一句試答
```

---

## 素材準備

全部放進 `remotion/public/`:

| 檔名                  | 說明                                                                        |
| --------------------- | --------------------------------------------------------------------------- |
| `paper.jpg`           | 乾淨紙紋底圖。**建議從 `hook.mp4` 抽最後一幀**,接縫才會像素級一致           |
| `logo.png`            | 去背透明 PNG,單色墨綠(走 multiply 印在紙上)                                 |
| `hook.mp4`            | 你做好的鉤子開場,含人聲                                                     |
| `fonts/your-font.otf` | 繁體字體                                                                    |
| `bgm.mp3`             | 背景音樂,全程墊在旁白底下。不放這個檔就把 quote json 的 `music` 設成 `null` |

從鉤子影片抽紙紋:

```bash
ffmpeg -sseof -0.1 -i remotion/public/hook.mp4 -frames:v 1 remotion/public/paper.jpg -y
```

字體要改兩個地方:`src/fonts.ts` 的檔名、`src/theme.ts` 的 `font` / `fontEn`。
查 macOS 字體全名:字體簿 → 選中字體 → 右側資訊面板。

> 確認字體授權允許商用嵌入。免費可商用的繁體襯線:思源宋體(Noto Serif TC)、芫荽、全字庫正楷體。

---

## 日常出片

**一句話到成品:**

```bash
cd pipeline
python3 new.py "引文。——作者《書名》"
```

會印出分段和英譯給你過目。斷句是編輯決策,不滿意就直接改
`quotes/<slug>.json` 裡的 `segments`。確認後:

```bash
python3 publish.py quotes/<slug>.json --meta --open
```

熟了之後一條命令跑完:

```bash
python3 new.py "引文。——作者《書名》" --go
```

**產出在 `releases/`:**

```
20260724_camus_love_001.mp4              影片
20260724_camus_love_001_card.png         3:4 靜圖(小紅書)
20260724_camus_love_001_card-tall.png    9:16 靜圖
20260724_camus_love_001.json             引文資訊
20260724_camus_love_001_meta.md          三平台發布文案
```

同一天重出不會覆蓋,自動加序號。

**預覽動畫**(調排版時開著):

```bash
cd remotion && npm run dev
```

存檔即熱更新。左側三個 composition:`LiteraryQuote`(影片)、
`QuoteCard`(3:4)、`QuoteCardTall`(9:16)。看 logo 和排版直接點 `QuoteCard` 最快。

> Studio 會佔用終端,跑 Python 要另開一個分頁(`Cmd + T`)。

---

## 批次出片

`new.py` 一次一句,適合精修。累積了一批句子想一口氣跑完時用 `batch.py`——
句子存在 Google Sheet 裡,手機隨手記,回到電腦一條命令跑完整批。

### 運作方式

```
Google Sheet          batch.py                      releases/
──────────────        ──────────────────────        ─────────
待做的句子      ──→   抓待做行                          │
                      標記 processing  ──回寫──→   你在手機上看得到進度
                      new.py     → quote json
                      publish.py → 出片                ▼
                      回寫 done / error  ──→        成品
```

狀態即時回寫,所以跑的時候手機打開 Sheet 就能看到每一句的進度。
中途出錯不會中斷整批,該行標成 `error` 並附上原因,繼續跑下一句。

### Sheet 欄位

| 欄位     | 說明                                                    |
| -------- | ------------------------------------------------------- |
| `text`   | 引文本體。詩歌可以直接換行,不會被當成分隔符             |
| `author` | 作者,可留空                                             |
| `book`   | 書名,不用加書名號,程式會加                              |
| `status` | 留空 = 待做。程式會寫入 `processing` / `done` / `error` |
| `note`   | 程式回寫:成功寫成品檔名,失敗寫錯誤原因                  |

> `text` / `author` / `book` 是分開傳給 `new.py` 的(`--author` / `--book`),
> 不是拼成一句再解析。這樣詩歌內部的破折號、換行不會被誤判成署名分隔符,
> 也不會出現書名號重複。

### 後端設定

Sheet 那邊靠一支 Apps Script Web App 提供介面,契約如下:

- **GET** `?token=<TOKEN>` → `{"pending": [{"row": 3, "text": "...", "author": "...", "book": "..."}]}`
- **POST** `{"token": "<TOKEN>", "updates": [{"row": 3, "status": "done", "note": "..."}]}`

部署時「執行身分」選自己、「存取權」選任何人,拿到的 `/exec` 網址填進 `.env` 的
`SHEET_WEBAPP_URL`。`TOKEN` 兩邊要一致,是唯一的存取控制。

### 用法

```bash
cd pipeline
python3 batch.py              # 處理所有待做的句子
python3 batch.py --dry        # 只列出待做,不出片(先確認清單)
python3 batch.py --limit 5    # 只跑前 5 句
python3 batch.py --no-meta    # 不生成文案,更快
```

建議先 `--dry` 看一眼清單再正式跑。一批跑下來配音是實際消耗,不像調排版那樣免費。

---

## 七個腳本

### `new.py` — 一句話 → quote json

```bash
python3 new.py "引文" --author 加缪 --book 重返提帕萨
python3 new.py "引文。——加缪《重返提帕萨》"     # 作者出處可黏在句尾
python3 new.py "引文" --voice <voice_id>         # 指定音色
python3 new.py "引文" --go                       # 生成後直接出片
```

模型負責:分段(依語氣停頓,不按字數硬切)、逐段英譯、生成 slug、朗讀用書名句。
包住整句的引號會自動剝掉,作者名黏在引號後面也認得(`。」于堅`)。

**拼回校驗**:分段拼回去必須與原句一字不差,不符就拒絕出片並印出差異。
這道關卡擋的是「渲染完才發現少了一個字」。

### `generate.py` — 配音 + manifest

```bash
python3 generate.py quotes/<slug>.json
```

呼叫兩次 TTS(書名一次、正文一次),拿逐字時間戳,轉繁體,寫 `manifest.json`。

正文**一次生成、事後按段切時間軸**——分段配音會讓每段都是獨立起句語氣,
連起來一頓一頓,失去朗讀氣口。

有快取(`pipeline/.tts_cache/`):同樣文字 + 音色 + 模型直接複用,零 API 消耗,
而且滿意的那次 v3 生成會被鎖住,不會被隨機性換掉。想重抽就刪掉快取檔。

### `publish.py` — 渲染 + 歸檔 + 文案

```bash
python3 publish.py quotes/<slug>.json --meta --open
```

| 旗標         | 作用                                   |
| ------------ | -------------------------------------- |
| `--meta`     | 生成三平台文案                         |
| `--copy tw`  | 剪貼簿取繁體海外版(預設取小紅書簡體版) |
| `--skip-gen` | 跳過配音步驟(只改了排版時用)           |
| `--no-card`  | 不出靜圖                               |
| `--open`     | 完成後打開 releases 資料夾             |

### `meta.py` — 只生成文案

```bash
python3 meta.py quotes/<slug>.json        # 小紅書版進剪貼簿
python3 meta.py quotes/<slug>.json tw     # 繁體海外版進剪貼簿
```

文案不滿意想換角度重生成時用,不必重新渲染影片。

三個平台各一區:小紅書(簡體,100–150 字)、抖音(簡體,40–60 字)、
海外(繁體,IG / Threads / YouTube,另附英文標籤)。

**標籤庫 `tags.json` 要你維護**。每月花十分鐘:在各平台搜尋框輸入關鍵詞,
下拉聯想詞就是真實搜尋量排序,抄進去。庫越準文案越準。

### `llm.py` — 文字生成的統一入口

`meta.py` 和 `new.py` 都只呼叫這裡,換供應商只改這一個檔案。
支援 OpenRouter(預設)和 Gemini,在 `.env` 用 `LLM_PROVIDER` 切換。

### `batch.py` — Google Sheet 佇列批次出片

見上面的「批次出片」章節。內部就是對每一行依序跑 `new.py` → `publish.py`,
加上狀態回寫與錯誤隔離。

### `add_music.py` — 一次性補欄位

```bash
python3 add_music.py            # 給所有 quotes/*.json 補上 music: "bgm.mp3"
python3 add_music.py other.mp3  # 指定別的檔名
```

已經有 `music` 欄位的檔案會跳過。加入背景音樂功能之前建立的舊 quote json
用這支補一次就好,之後 `new.py` 生成的都會自帶。

---

## quote json 欄位

```jsonc
{
  "id": "camus_love_001",
  "lang": "zh",
  "book": "重返提帕萨",              // 可留空,留空則語音只讀作者名
  "author": "加缪",
  "segments": [                      // 斷句是編輯決策,中英手動對應
    { "zh": "不被爱仅是时运不济，",
      "en": "To be unloved is merely a stroke of misfortune," },
    { "zh": "而无力去爱才是真正的灾难。",
      "en": "but the inability to love is the true catastrophe." }
  ],
  "traditional": "s2tw",             // 見下方
  "hook_video": "hook.mp4",
  "tts": {
    "provider": "elevenlabs",
    "voice_id": "你的 voice_id",
    "model_id": "eleven_v3",         // 或 eleven_multilingual_v2(較穩定)
    "stability": 0.0                 // v3 只吃 0.0 / 0.5 / 1.0
  },
  "title_tts_text": "[somber] 重返提帕薩，加繆。",   // 朗讀專用,可加 v3 標籤
  "timing": {
    "hook_sec": 4.0,                 // hook.mp4 的實際長度
    "title_overlap_sec": 1.0,        // 書名提前壓在鉤子尾巴上的秒數
    "seg_gap_sec": 0.45,             // 只影響最後一段的停留
    "full_sec": 6.0                  // 完整句幕停留(給人截圖)
  },
  "theme": { "paper": "#f3ede1", "ink": "#0e5d2d" },
  "music": "bgm.mp3",                // 見下方;不要背景音樂就設成 null
  "safeMode": true
}
```

> 上面是 JSONC(帶註解)方便閱讀。實際的 `quotes/*.json` 是純 JSON,
> **不能有註解,也不能有結尾逗號**——`json.loads` 會直接拒絕。
> 用 Prettier 之類的工具格式化 README 時要留意這一段。

### 繁體轉換模式

| 模式       | 行為                                 | 適用                |
| ---------- | ------------------------------------ | ------------------- |
| `s2t`      | 純字形,但保留 裏 / 爲 / 着 等異體字  | 不建議              |
| **`s2tw`** | **加上台港字形:裏→裡、爲→為、着→著** | **預設,文學句最佳** |
| `s2twp`    | 再換詞彙:信息→資訊、軟件→軟體        | 現代口語內容        |
| `null`     | 不轉換                               | 原文即繁體時        |

文學引文用 `s2tw`:拿到全部字形修正,又不會把譯者的用詞換掉。

> 轉換必須在 TTS **之前**。時間戳對應的是輸入字元,事後轉繁會因一對多轉換
> (裡/里、乾/幹)導致逐字動畫整體錯位。

### v3 音頻標籤

`title_tts_text` 和 `body_tts_text` 可以寫 `[somber]`、`[pause]`、
`[whispers]`、`[slowly]` 等標籤控制演繹。標籤不會被讀出來,也不會出現在字幕上
(對齊階段有狀態機跳過方括號內容)。

### 背景音樂

`music` 指向 `remotion/public/` 裡的檔名,全程 loop 墊在旁白底下。
音量在 `BgMusic.tsx` 裡調——這是刻意寫死的,不放進 quote json,
因為音量是整個帳號的聽感統一設定,不該一則一則調。

設成 `null` 則完全沒有背景音樂,只有旁白與鉤子影片的原聲。

---

## 常見調整

| 想改什麼     | 改哪裡                                                   |
| ------------ | -------------------------------------------------------- |
| 正文字級     | `SegmentReveal.tsx` → `fontSize: 82`                     |
| 正文起始高度 | `SegmentReveal.tsx` → `top: 780`                         |
| 英文透明度   | `SegmentReveal.tsx` → `0.75`                             |
| 壓印速度     | `PaperBase.tsx` → `pressStyle` 的 `dur = 5`(小=啪,大=渗) |
| Logo 大小    | `LogoStamp.tsx` → `width`                                |
| Logo 高度    | `theme.ts` → `LOGO_BOTTOM`(距底部比例,影片 / 靜圖各一)   |
| 紙面微動     | `PaperBase.tsx` → `DRIFT`(設 0 完全靜止)                 |
| 完整句留白   | `FullQuoteCard.tsx` → `BOTTOM_R`                         |
| 顏色         | `theme.ts` → `paper` / `ink` / `inkDeep`                 |

**顏色是帳號的視覺簽名,由成品圖取樣而得,別隨手改。**

---

## 設計決策備忘

寫下來是為了半年後的自己不會誤改。

- **紙面永遠在最底層**,鉤子影片疊在上面播,播完自動卸載露出紙。
  不用 opacity 開關,所以不可能出現透明幀。
- **書名與 Logo 渲染在紙面之上**,才能壓在鉤子影片尾巴上;
  鉤子播完後位置不動,銜接無縫。
- **段落下台時間 = 下一段第一個字出現的時刻**。配音是連續的,
  若用「最後一字結束 + gap」會和下一段重疊,畫面上兩段的字會疊在一起。
- **段間呼吸由配音裡標點的自然停頓決定**,不是由 `seg_gap_sec`。
  想要更長的停頓,在 `body_tts_text` 用 `[pause]` 標籤。
- **完整句幕撤掉頁眉與英文**:底部已有落款,這一幕是給人截圖的,乾淨最重要。
- **靜圖是獨立 composition,不是抽幀**。3:4 卡片會按新框高重新排版,
  純向量重排,零畫質損失。
- **字級自動計算用純數學,不量 DOM**。中文全形等寬,
  `每行字數 = 框寬 ÷ (字級 + 字距)`,由大而小取第一個放得下的。
- **Logo 從底部定位**,不是從頂部——否則換比例時會被切掉。
- **Logo 微旋轉 ±1.5°**:「手蓋」與「貼圖」的分界線。
- **Logo 與書名同時淡入,不做壓印**:書名本身已在壓印,再壓一次會太吵。
- **壓印是同一套物理**:`pressStyle()` 被書名、正文、完整句共用,
  整片只有一種動畫語言。

---

## 疑難排解

| 症狀                                        | 原因                                                                          |
| ------------------------------------------- | ----------------------------------------------------------------------------- |
| `ModuleNotFoundError: opencc`               | 套件名是 `opencc-python-reimplemented`,不是 `opencc`                          |
| `KeyError: 'ELEVENLABS_API_KEY'`            | `.env` 沒建,或建在 `pipeline/` 而不是專案根目錄                               |
| `404 .../REPLACE_WITH_YOUR_VOICE_ID`        | quote json 裡的 voice_id 佔位符沒換                                           |
| `404` 但 voice_id 是真的                    | 改用 `eleven_multilingual_v2` 測試,分辨是音色不存在還是方案未開放 v3          |
| 沒有 `_meta.md`                             | 忘了加 `--meta`;或 `publish.py` 是舊版(`grep -c want_meta publish.py` 應為 2) |
| Studio 一片空白                             | 看終端的紅色編譯錯誤;或瀏覽器 Console(`Cmd+Option+I`)看執行期錯誤             |
| 兩段文字疊在一起                            | `generate.py` 是舊版,段落下台時間沒有 clamp 到下一段起點                      |
| 字幕出現 `[pause]`                          | `tts_providers.py` 是舊版,`_chars_to_words` 缺少方括號狀態機                  |
| 交接處紙面「跳」一下                        | `PaperBase.tsx` 的 `DRIFT` 設成 0                                             |
| 靜圖 Logo 被切                              | 確認用的是 `LOGO_BOTTOM`(距底部)而非舊版的 `LOGO_Y`(距頂部)                   |
| `ENOENT: package.json`                      | 在專案根目錄跑了 npm,要先 `cd remotion`                                       |
| `✗ .env 缺 SHEET_WEBAPP_URL 或 SHEET_TOKEN` | 批次出片的兩個變數沒填,見「批次出片」章節                                     |
| `Web App 回應錯誤`(跑 batch.py 時)          | `.env` 的 `SHEET_TOKEN` 和 Apps Script 裡的 TOKEN 不一致                      |
| 背景音樂蓋過旁白                            | `BgMusic.tsx` 的 `volume` 值                                                  |

列出可用音色:

```bash
curl -s https://api.elevenlabs.io/v1/voices \
  -H "xi-api-key: $(grep ELEVENLABS_API_KEY ../.env | cut -d= -f2)" \
  | python3 -c "import json,sys; [print(v['voice_id'], v['name']) for v in json.load(sys.stdin)['voices']]"
```

---

## 成本

| 項目       | 說明                                                               |
| ---------- | ------------------------------------------------------------------ |
| ElevenLabs | 每則約兩次呼叫(書名 + 正文),一則 100 字上下。有快取,重跑不重複計費 |
| OpenRouter | 每則兩次(分段英譯 + 文案),`gemini-2.5-flash` 極便宜                |
| Remotion   | 本機渲染,免費。`--concurrency=2` 是為 8GB 記憶體設的               |

省額度的習慣:調排版時用 `--skip-gen`,調文案時單獨跑 `meta.py`,
兩者都不會重新配音。

---

## 檔案結構

```
wenziji/
├── .env                    API keys(不進 git)
├── pipeline/
│   ├── new.py              一句話 → quote json
│   ├── generate.py         配音 + manifest
│   ├── publish.py          渲染 + 歸檔 + 文案
│   ├── batch.py            Google Sheet 佇列批次出片
│   ├── meta.py             三平台發布文案
│   ├── llm.py              文字生成統一入口
│   ├── traditional.py      繁體轉換
│   ├── tts_providers.py    TTS 供應商介面
│   ├── add_music.py        一次性:給舊 quote json 補 music 欄位
│   ├── tags.json           標籤庫(手動維護)
│   ├── quotes/             每則一份 json
│   └── .tts_cache/         配音快取(不進 git)
├── remotion/
│   ├── src/
│   │   ├── theme.ts        顏色、字體、Logo 位置
│   │   ├── LiteraryQuote.tsx   影片主 composition
│   │   ├── QuoteCard.tsx       靜圖 composition
│   │   └── components/     PaperBase / TitleStamp / SegmentReveal
│   │                       / FullQuoteCard / LogoStamp / BgMusic
│   └── public/             paper.jpg / logo.png / hook.mp4 / bgm.mp3 /
│                           fonts / manifest.json / vo_*.mp3
└── releases/               成品(不進 git)
```
