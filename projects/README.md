# projects：一個專案 = 一份 deck.json

每個專案一個資料夾 `projects/<name>/`。內容只寫在 `deck.json`；版型在 `templates/<theme>/theme.json`，
PPT（`scripts/deck_pptx.py`）和影片（`src/deck/DeckVideo.tsx`）讀同一份，所以一頁對一頁。

```
projects/<name>/
├─ deck.json      內容：每頁文字、旁白、截圖設定、語音設定
├─ shots/         截圖＋shots.json（重點框位置）
├─ raw/           語音原檔＋manifest.json（記每段對應哪段文字）
├─ vo/            調過語速、影片用的
└─ out/           產出：<name>.pptx、<name>.mp4、<name>.srt、sample-<id>.wav
```

```bash
python scripts/deck.py <name> pptx              # PPT
python scripts/deck.py <name> sample <id>       # 一頁試聽
python scripts/deck.py <name> voice             # 旁白：只產文字改過的頁（--all 全部、--local 用本機）
python scripts/deck.py <name> video             # 影片＋字幕
python scripts/deck.py <name> all               # pptx → voice → video
```

範例：`projects/example/`（最小、Windows 語音、沒有截圖）。

## deck.json

| 欄位 | 說明 |
|---|---|
| `title` | 簡報名稱（只是標記） |
| `theme` | `templates/` 底下的資料夾名，例如 `default` |
| `copy_to` | 選填。`pptx`／`video`／`srt` 額外複製一份到哪（相對 skill 根目錄）。不寫就只放 `out/` |
| `voice.engine` | `breezy`（BreezyVoice，台灣口音，自然）或 `sapi`（Windows 內建 Hanhan，快，機器感） |
| `voice.tempo` | 語速倍率，1.0 原速；BreezyVoice 用 1.15 |
| `voice.breezy` | `runner`：`kaggle`（預設，Kaggle 免費 T4）或 `local`（本機 Docker）；`speaker`（參考聲音檔名，不含 .wav）；`speaker_text`（那段錄音的逐字稿）；選填 `speaker_dir`（本機自訂聲音的資料夾）。預設用 BreezyVoice 附的 `example`（女聲） |
| `voice.sapi` | `voice`（例如 `Microsoft Hanhan Desktop`）、`rate`（-10～10） |
| `pronounce` | 讀音表 `{"畫面上的字": "唸法"}`，只套在餵給語音的文字，字幕照原字顯示。例如 `"SYS.1": "SYS 點一"` |
| `screenshots` | 有 screen 頁才需要：`url`、`serve`（怎麼把網頁開起來）、`prepare`（每張截圖前先跑的 JS）、`ready`（頁面準備好的條件）、`shots: [{name, setup, marks}]` |
| `slides` | 頁面陣列，順序就是播放與頁碼順序 |

每一頁都有 `id`（不能重複，也是音檔名）、`type`、`narration`（旁白，寫畫面上要顯示的字）。

### 頁型

| type | 欄位 |
|---|---|
| `cover` | `year`（背景大字）、`org`、`title`、`subtitle: [{text, strong}]`（strong 為白字） |
| `bullets` | `kicker`、`title`、`items: [字串]`、選填 `tone`（`accent`／`coral`）、選填 `note`（底下一行小字） |
| `boxes` | `kicker`、`title`、`boxes: [{head, lines: [字串]}]`，建議 3 格，中間自動加箭頭 |
| `steps` | `kicker`、`title`、選填 `legend: {accent: "...", coral: "..."}`、`steps: [{who, text, human, desc}]`，human=true 用珊瑚色；建議 7 列以內 |
| `screen` | `kicker`、`title`、`shot`（screenshots.shots 的 name）、`items: [字串]`（右側重點，建議 3 條以內）、選填 `tones`（第 i 個框與第 i 條重點的顏色） |

篇幅參考：標題一行（約 20 字內）、條列每條一行（約 30 字內）、旁白每頁 10–30 秒（約 40–120 字）。

## 規則

- 改了某頁的 `narration`（或讀音表、語音設定），`voice` 只會重產那幾頁；不用手動刪音檔。
- 換音檔或搬資料夾時，用 `voice --adopt` 把現有音檔登記成對應目前的文字。
- `sapi` 與 `breezy --local` 在本機跑，文字不出這台電腦；`breezy` 預設的 Kaggle 會把旁白文字送到 Kaggle（Google）。
- 不要換成 edge-tts 或其他雲端語音，除非確認內容可以送出去。
