---
name: deck-video
description: "給一個專案 repo，做出介紹它的簡報（套 PPT 模板）、配旁白、做成有字幕的影片。內容寫在一份 deck.json，PPT 與影片共用同一套版型、一頁對一頁；旁白用 BreezyVoice（台灣口音，預設在 Kaggle 免費 GPU 自動跑）。每個階段停下來給使用者確認，或一開始選一路跑完。Trigger: /deck-video <repo 路徑或專案名>，或「把這個 repo 做成簡報／影片」「幫這個專案做介紹影片」「重配旁白」「重出影片」「加一個 PPT 模板」。"
---

# deck-video：專案 repo → 簡報 → 旁白 → 影片

以下路徑都相對於**這個 skill 的資料夾**（SKILL.md 所在處），它本身就是一個專案：
`templates/`（PPT 模板）、`projects/<name>/`（每個專案的內容與產出，產出在 `out/`）、`scripts/`、`src/`。
欄位與頁型的正本：`projects/README.md`；模板：`templates/README.md`。指令都在 skill 資料夾裡跑。

## 開始前

1. **問模式**（用 AskUserQuestion）：
   - 「每個階段停下來確認」（預設）：停三次，見下面的 A／B／C。
   - 「一路跑完」：中間不停，最後一次給全部成果。試聽也略過。
2. **環境**（第一次或換電腦時）：`node_modules` 不在就 `npm install`；Python 要有 `python-pptx`、`Pillow`、`kaggle`。
   Kaggle 金鑰見下面「Kaggle 設定」。缺什麼就停下來說，不要自己繞過。
3. **專案名**：從 repo 資料夾名取（小寫、連字號），已存在就問要覆蓋還是另開。

## 階段 A：讀 repo → 大綱 → 套模板 → PPT（做完停一次）

1. **讀 repo**：README、docs/、設定檔、主要程式進入點、git log 近期重點；有 demo 網頁或截圖就記下來。
   寫 `projects/<name>/deck.json`（從 `projects/example/deck.json` 複製結構）：
   - 頁數 8–15 頁：封面 → 為什麼／解決什麼 → 怎麼做（架構或流程）→ 重點功能（有畫面就用 screen 頁）→ 總結。
   - 每頁都要有 `narration`；寫的是畫面上的意思，不是照念條列。
   - **只寫 repo 裡查得到的事**。數字只能用 repo 裡寫的或量得到的，不要為了版面編；查不到就不寫，或在大綱裡標「待確認」。
   - 用使用者的口吻：短句、名詞標籤、動詞按鈕，不寫「AI 幫你…」這類宣傳句。
   - 縮寫唸不對的放 `pronounce`（例如 `"SYS.1": "SYS 點一"`）。
2. **模板**：列出 `templates/` 給使用者選（預設 `default`）。使用者給了新的 .pptx → 照 `templates/README.md` 做一個新模板。
3. **有截圖頁**：網頁要先開著（`screenshots.serve`），`python scripts/deck.py <name> shots`，用 Read 看每張圖和框。
4. **PPT**：`python scripts/deck.py <name> pptx`；用 PowerPoint 匯出圖片抽看封面、一張內頁、一張截圖頁（字有沒有超出、框對不對）。
5. **停**：給使用者大綱（每頁標題＋旁白）、用的模板、PPT 檔（SendUserFile）。改完再進 B。

## 階段 B：試聽（停一次；一路跑完模式略過）

`python scripts/deck.py <name> sample <第一頁 id>` → `out/sample-<id>.wav` 給使用者聽。
不滿意的常見調整：`voice.tempo`（BreezyVoice 用 1.15）、`pronounce`、換參考聲音（`voice.breezy.speaker`）。
預設用 BreezyVoice 附的範例女聲；要換成別人的聲音（需要那個人 5–10 秒錄音＋逐字稿）先問使用者。
半精度（fp16）實測快 2–6 倍但會漏字，不要用。

## 階段 C：配旁白 → 影片（做完停一次）

1. `python scripts/deck.py <name> voice`：只產文字改過的頁。Kaggle 會自動送出、等、下載、裝回（約 15–20 分鐘），放背景跑，跑完前不要說完成。
2. `python scripts/deck.py <name> video`：輸出 `out/<name>.mp4` 與 `.srt`（字幕已燒進畫面，.srt 是附加的）。
3. 驗收：`npx remotion still DeckVideo out/check.png --frame=<n>` 抽 3–4 格用 Read 看（字幕有沒有壓到頁碼、條列有沒有超出）。
4. **停**：給影片（SendUserFile）、總長度、旁白花了多久。

之後改內容：改 `deck.json` → `pptx`／`voice`／`video`，旁白只會重產改過的頁。

## 旁白在哪裡跑

| `voice.breezy.runner` | 速度（15 段、約 4 分鐘旁白） | 文字去哪 |
|---|---|---|
| `kaggle`（預設） | 約 11 分鐘＋排隊安裝 5–10 分鐘 | **送到 Kaggle（Google）**：只用在沒有客戶資料的內容；不確定先問 |
| `local`（或 `--local`） | 約 63 分鐘（4GB 筆電顯卡） | 不出這台電腦；要 Docker 與 BreezyVoice，見 `breezy/README.md` |

`engine: sapi`（Windows Hanhan）最快、完全本機，但機器感重，使用者嫌不自然。不要改用 edge-tts 等雲端語音。

## Kaggle 設定（每個人用自己的帳號，設定一次；給使用者看的完整教學在 README）

每個使用者用**自己的** Kaggle 帳號與金鑰，免費 GPU 時數（每週約 30 小時）也是各算各的。
第一次跑 `voice` 或 `sample` 時發現沒設定，就停下來帶使用者做：

1. 註冊／登入 https://www.kaggle.com ，到 Settings 做**手機驗證**（沒驗證不能用 GPU 與網路）。
2. 到 https://www.kaggle.com/settings/api 按「Generate New Token」，自己把那串 token 存成 `~/.kaggle/access_token`
   （Windows：`C:\Users\<你>\.kaggle\access_token`，沒有副檔名；或設環境變數 `KAGGLE_API_TOKEN`）。
   **金鑰由使用者自己放，不要經手、不要寫進這個專案。**
3. 把 `config.example.json` 複製成 `config.json`（不進 git），`kaggle_user` 填自己的帳號名稱（網址 kaggle.com/<帳號>）。
4. `pip install kaggle`。

之後 deck.py 會在**使用者自己的帳號**下另開一份私人筆記本 `<user>/deck-voice-<name>`（試聽用 `deck-sample-<name>`），
設定 GPU T4、開網路，跑完只帶回 `vo.zip`。不需要先複製任何筆記本。
4. 失敗時：deck.py 會印出筆記本網址，去 Logs 看。Kaggle 環境改版造成安裝失敗時，修 `scripts/deck.py` 的
   `KAGGLE_REQUIREMENTS`／`KAGGLE_INSTALL`（2026-10 的修法：whisper 要 `setuptools<70`＋`--no-build-isolation`、
   onnxruntime-gpu 1.20.1 已下架改 1.20.2 並移除 CPU 版、`ruamel.yaml==0.17.40`、g2pw 指定 CPU）。
5. 不想用 API 時的手動備案：
   1. 打開已修好的公開筆記本 https://www.kaggle.com/code/gtbmamb/breezyvoice-playground →「**Copy & Edit**」複製到自己帳號
      （Settings 確認 Accelerator 是 GPU T4、Internet 開著）
   2. `python scripts/deck.py <name> kaggle-cells` → `out/kaggle-cells.txt`；把第 2 段貼給使用者，
      換掉複製來那份裡開頭是 `csv_text = ` 的那格 → Save Version → Save & Run All
   3. 跑完到筆記本的 Output 分頁下載 `vo.zip` → `python scripts/deck.py <name> import <vo.zip> video`

## 地雷

- `timing`／`video` 會把 `.srt`／`.mp4` 複製到 `copy_to`；要試新版本時先拿掉 `copy_to` 或另存檔名，不要蓋掉交付檔。
- Remotion 只讀 `public/`：deck.py timing 會把底圖、截圖、旁白同步到 `public/_active/`，不要手動放東西進去。
- 從 Python 呼叫 PowerShell 腳本會被執行原則擋，deck.py 已用 `-ExecutionPolicy Bypass`（只對那一次執行有效）。
  `.ps1` 有中文註解時要存成 UTF-8 **含 BOM**，不然 PowerShell 5.1 會讀壞參數。
- 本機 BreezyVoice 很佔空間（約 22 GB），重建前看 C 槽剩多少，低於 20 GB 先說。
- 永久刪除一律給使用者指令自己跑；他說「刪掉重複的」時，可以移到資源回收筒（可救回）並列出移了什麼。
- Remotion 是原始碼公開但非 OSS，公司商用前要確認 company license。
