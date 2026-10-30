# deck-video

給一個專案 repo，做出介紹它的簡報（套 PPT 模板）、配旁白、做成有字幕的影片。
PPT 與影片讀同一份 `deck.json` 與同一套版型，一頁對一頁。這個資料夾同時是 Claude Code 的 skill（`SKILL.md`）。

```bash
npm install                                   # Remotion（影片）
pip install python-pptx Pillow kaggle         # PPT、圖片、Kaggle
python scripts/deck.py example all            # 範例：PPT → 旁白 → 影片，產出在 projects/example/out/
```

| 資料夾 | 內容 |
|---|---|
| `templates/` | PPT 模板與做好的底圖、版型設定（見 templates/README.md） |
| `projects/` | 每個專案的 deck.json、截圖、旁白、產出（見 projects/README.md） |
| `scripts/` | `deck.py` 總指令、`deck_pptx.py` PPT、`deck_shots.mjs` 截圖、`theme_tools.py` 模板、`tts.ps1` Windows 語音 |
| `src/` | Remotion 影片版型（`src/deck/DeckVideo.tsx`） |
| `breezy/` | 本機跑 BreezyVoice 的修正（預設用 Kaggle，不需要） |

## 旁白：用 Kaggle 免費 GPU 跑 BreezyVoice

旁白用 BreezyVoice（聯發科，台灣口音）。它要 GPU，所以預設丟到 **你自己的** Kaggle 帳號的免費 T4 上跑：
`deck.py` 會自動建一份私人筆記本、送上去跑、等它跑完、把音檔下載回來。全程不用開 Kaggle 網頁。

> **隱私**：旁白文字會送到 Kaggle（Google）處理。內容有客戶資料或不能外流時，改用本機（`--local`，見 `breezy/README.md`）
> 或 Windows 語音（`"engine": "sapi"`），文字都不會離開你的電腦。

### 1. 第一次設定（每台電腦一次）

**(1) 註冊 Kaggle 並做手機驗證**

1. 到 https://www.kaggle.com 註冊或登入。
2. 右上角頭像 → **Settings** → **Phone Verification**，完成手機驗證。
   沒驗證的帳號不能開 GPU 和網路，筆記本會直接失敗。

**(2) 產生 API token，存到電腦上**

1. 到 https://www.kaggle.com/settings/api → 按 **Generate New Token**，複製畫面上那串 token。
2. 存成 `~/.kaggle/access_token`（一行、只有 token、**沒有副檔名**）：

   Windows PowerShell：
   ```powershell
   New-Item -ItemType Directory -Force "$HOME\.kaggle" | Out-Null
   Set-Content -NoNewline -Encoding ascii "$HOME\.kaggle\access_token" "貼上你的token"
   ```
   macOS／Linux：
   ```bash
   mkdir -p ~/.kaggle && printf '%s' '貼上你的token' > ~/.kaggle/access_token && chmod 600 ~/.kaggle/access_token
   ```
   也可以不存檔，改設環境變數 `KAGGLE_API_TOKEN`。舊版的 `~/.kaggle/kaggle.json` 也能用。

   token 等於你的帳號密碼：**不要放進這個 repo、不要貼給別人**。外洩了就回同一頁按 Expire 作廢再產一個。

**(3) 填你的 Kaggle 帳號名稱**

```bash
cp config.example.json config.json
```
打開 `config.json`，把 `kaggle_user` 改成你的帳號名稱（就是個人頁網址 `kaggle.com/<帳號>` 的那段，不是 token）。
`config.json` 已在 `.gitignore`，不會進 git。也可以改設環境變數 `KAGGLE_USERNAME`。

**(4) 裝 Kaggle 指令並確認登入**

```bash
pip install kaggle
kaggle kernels list --mine
```
第二行沒有報錯（列出你的筆記本，或空清單）就是設定好了。

### 2. 讓專案用 BreezyVoice + Kaggle

在 `projects/<name>/deck.json` 的 `voice` 這樣寫（`speaker: "example"` 是 BreezyVoice 內建的範例女聲，`speaker_text` 是那段錄音的逐字稿，照抄即可）：

```json
"voice": {
  "engine": "breezy",
  "tempo": 1.15,
  "breezy": {
    "runner": "kaggle",
    "speaker": "example",
    "speaker_text": "在密碼學中，加密是將明文資訊改變為難以讀取的密文內容，使之不可讀的方法。只有擁有解密方法的對象，經由解密過程，才能將密文還原為正常可讀的內容。"
  }
}
```

`projects/example` 預設用 Windows 語音（`sapi`），想用它試 Kaggle 就把上面這段換進去。

### 3. 跑

```bash
python scripts/deck.py <name> sample <頁 id>   # 先試聽一頁 → projects/<name>/out/sample-<id>.wav
python scripts/deck.py <name> voice            # 產全部旁白（只產文字有改的頁；加 --all 全部重產）
python scripts/deck.py <name> video            # 接著出影片
```

`voice` 執行時會發生這些事：

1. 在你的帳號下建立／更新私人筆記本 `<你的帳號>/deck-voice-<name>`（試聽是 `deck-sample-<name>`），設定 GPU T4、開網路。
2. 每 30 秒印一次狀態，例如 `[ 3.5 分] ... running`。最多等 90 分鐘。
3. 跑完自動下載 `vo.zip`，把音檔放進 `projects/<name>/raw/`，依 `tempo` 調速到 `vo/`。

大約時間：排隊＋安裝 5–10 分鐘，15 段（約 4 分鐘旁白）產生約 11 分鐘，總共約 15–20 分鐘。
終端機要開著等它跑完；中途關掉的話，Kaggle 那邊會繼續跑，重跑 `voice` 會重新送出一次。

**額度**：Kaggle 免費 GPU 每週約 30 小時，算在你自己的帳號。用量看 https://www.kaggle.com/settings 的 Quota。
跑完的筆記本會留在你的帳號（私人），不需要可以到 https://www.kaggle.com/work/code 刪掉。

### 4. 出錯時

| 訊息 | 原因與處理 |
|---|---|
| `找不到 kaggle 指令` | 還沒 `pip install kaggle`，或 Python 的 Scripts 資料夾不在 PATH |
| `Kaggle 還沒登入` | `~/.kaggle/access_token` 不存在；回到第 1 步 (2) |
| `不知道 Kaggle 帳號名稱` | 沒有 `config.json` 或 `kaggle_user` 沒填；回到第 1 步 (3) |
| `401 Unauthorized` | token 錯了或被作廢，重新 Generate 一個 |
| `Kaggle 執行失敗：... error` | 打開訊息裡的筆記本網址 → **Logs** 看哪一格壞了。常見是沒做手機驗證（拿不到 GPU）、GPU 週額度用完 |
| 安裝那格失敗 | Kaggle 環境改版。修 `scripts/deck.py` 的 `KAGGLE_REQUIREMENTS`／`KAGGLE_INSTALL`（2026-10 的修法寫在 `SKILL.md`） |
| `跑完了但沒有 vo.zip` | 產生那格出錯（通常是旁白裡有奇怪符號），看下載回來的 log |
| `還沒對上的頁面：...` | 有頁面沒產出音檔，再跑一次 `voice` 只會補那幾頁 |

### 備案：不用 API，手動在 Kaggle 網頁跑

1. 打開已修好的公開筆記本 https://www.kaggle.com/code/gtbmamb/breezyvoice-playground → **Copy & Edit** 複製到自己帳號。
   右側 Settings 確認 **Accelerator = GPU T4**、**Internet = On**。
2. `python scripts/deck.py <name> kaggle-cells` → 產出 `projects/<name>/out/kaggle-cells.txt`。
3. 把檔案裡「2. 旁白清單」那段，整格取代筆記本中開頭是 `csv_text = ` 的那格。
4. **Save Version** → **Save & Run All**，跑完到 **Output** 分頁下載 `vo.zip`。
5. `python scripts/deck.py <name> import <vo.zip 路徑> video`

## 授權

本專案僅供個人、非商業使用，見 [LICENSE](LICENSE)。
使用的第三方軟體與參考專案列在 [THIRD_PARTY.md](THIRD_PARTY.md)，各依其原授權。
