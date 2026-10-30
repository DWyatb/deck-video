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

## 來源與授權

**本專案的授權：僅限個人、非商業使用**，見 [LICENSE](LICENSE)。本專案為作者個人使用，不販售、不提供商業服務。

這個專案自己的程式碼（`scripts/`、`src/`、`templates/default/`）是自己寫的，沒有複製其他專案的程式碼。
下面這些第三方軟體只在執行時安裝或下載，**沒有放進這個 repo**，各自依原授權使用；本專案的 LICENSE 不涵蓋它們。

### Remotion（影片渲染）

- 來源：https://www.remotion.dev ／ https://github.com/remotion-dev/remotion
- 版權：Copyright © Remotion
- 授權：[Remotion License](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)（原始碼公開，但**不是** OSI 開源授權）
- 用法：透過 npm 安裝為相依套件（`package.json`），本 repo 沒有複製或修改 Remotion 的原始碼。

Remotion License 的重點：

- **免費授權**適用於：個人、員工 3 人以內的營利組織、非營利組織，以及評估階段（尚未商用）。
  符合資格者可免費用來製作影片，商用也可以。
- 員工超過 3 人的營利組織使用，需要購買 [Company License](https://www.remotion.pro/license)。
- 不可以複製或修改 Remotion 的程式碼，拿去販售、出租或再授權成自己的衍生版本。

本專案以**個人**身分使用 Remotion 的免費授權。如果你要在員工超過 3 人的公司裡用它來做影片，
請由公司另外取得 Remotion Company License。

### BreezyVoice（旁白語音合成）

- 來源：MediaTek Research（聯發科創新基地）
  - 程式碼：https://github.com/mtkresearch/BreezyVoice
  - 模型：https://huggingface.co/MediaTek-Research/BreezyVoice
- 授權：程式碼與模型皆為 [Apache License 2.0](https://github.com/mtkresearch/BreezyVoice/blob/main/LICENSE)
- BreezyVoice 部分衍生自 [CosyVoice](https://github.com/FunAudioLLM/CosyVoice)（FunAudioLLM，Apache-2.0）。
- 用法：執行時才從上面的 GitHub 下載（Kaggle 筆記本裡 `git clone`，或本機自己 clone，見 `breezy/README.md`）；
  本 repo 沒有包含 BreezyVoice 的程式碼、模型或聲音檔。預設參考聲音 `example` 是 BreezyVoice 附的範例音檔。
- `scripts/deck.py` 的 Kaggle 安裝步驟與 `breezy/Dockerfile.fix`，是讓 BreezyVoice 在新環境跑起來的相容修正（套件版本），
  安裝流程參考了 BreezyVoice 官方的 Kaggle 範例筆記本 https://www.kaggle.com/code/a24998667/breezyvoice-playground 。

引用（BreezyVoice 作者要求的格式）：

```bibtex
@article{hsu2025breezyvoice,
  title={BreezyVoice: Adapting TTS for Taiwanese Mandarin with Enhanced Polyphone Disambiguation--Challenges and Insights},
  author={Hsu, Chan-Jan and Lin, Yi-Cheng and Lin, Chia-Chun and Chen, Wei-Chih and Chung, Ho Lam and Li, Chen-An and Chen, Yi-Chang and Yu, Chien-Yu and Lee, Ming-Ji and Chen, Chien-Cheng and others},
  journal={arXiv preprint arXiv:2501.17790},
  year={2025}
}
@article{hsu2025breeze,
  title={The Breeze 2 Herd of Models: Traditional Chinese LLMs Based on Llama with Vision-Aware and Function-Calling Capabilities},
  author={Hsu, Chan-Jan and Liu, Chia-Sheng and Chen, Meng-Hsi and Chen, Muxi and Hsu, Po-Chun and Chen, Yi-Chang and Shiu, Da-Shan},
  journal={arXiv preprint arXiv:2501.13921},
  year={2025}
}
@article{du2024cosyvoice,
  title={Cosyvoice: A scalable multilingual zero-shot text-to-speech synthesizer based on supervised semantic tokens},
  author={Du, Zhihao and Chen, Qian and Zhang, Shiliang and Hu, Kai and Lu, Heng and Yang, Yexin and Hu, Hangrui and Zheng, Siqi and Gu, Yue and Ma, Ziyang and others},
  journal={arXiv preprint arXiv:2407.05407},
  year={2024}
}
```

### 其他相依套件

| 套件 | 用途 | 授權 |
|---|---|---|
| [React](https://github.com/facebook/react)、React DOM | Remotion 的畫面元件 | MIT |
| [Zod](https://github.com/colinhacks/zod) | Remotion 的參數驗證 | MIT |
| [TypeScript](https://github.com/microsoft/TypeScript) | 型別檢查（開發用） | Apache-2.0 |
| [@types/react](https://github.com/DefinitelyTyped/DefinitelyTyped)、@types/react-dom | 型別定義（開發用） | MIT |
| [Chrome Headless Shell](https://developer.chrome.com/blog/chrome-headless-shell) | Remotion 渲染與 `deck_shots.mjs` 截圖，第一次執行時由 Remotion 下載 | Chromium 授權（BSD-3-Clause 等） |
| [FFmpeg](https://ffmpeg.org) | 影片編碼、旁白調速，隨 Remotion 安裝 | LGPL-2.1+ |
| [python-pptx](https://github.com/scanny/python-pptx) | 產生 PPT | MIT |
| [Pillow](https://github.com/python-pillow/Pillow) | 圖片處理 | MIT-CMU（HPND） |
| [Kaggle API](https://github.com/Kaggle/kaggle-api) | 送出 Kaggle 筆記本 | Apache-2.0 |
| Windows SAPI（Microsoft Hanhan） | 選用的本機語音 | Windows 內建，依 Windows 授權 |
| 微軟正黑體（Microsoft JhengHei） | PPT 與影片字型；本 repo 只寫字型名稱，沒有附字型檔 | Windows 內建，依 Windows 授權 |

BreezyVoice 執行時（Kaggle 或本機 Docker）另外安裝的套件，如 openai-whisper（MIT）、onnxruntime-gpu（MIT）、g2pw（Apache-2.0）、
ttsfrd（ModelScope），各依其授權；清單見 `scripts/deck.py` 的 `KAGGLE_REQUIREMENTS`。

### Kaggle 筆記本

| 筆記本 | 關係 |
|---|---|
| [a24998667/breezyvoice-playground](https://www.kaggle.com/code/a24998667/breezyvoice-playground) | BreezyVoice 官方 Kaggle 範例，`deck.py` 自動產生的筆記本照它的安裝與執行流程寫 |
| [gtbmamb/breezyvoice-playground](https://www.kaggle.com/code/gtbmamb/breezyvoice-playground) | 從上面那份複製後修好相依版本的公開版本，手動備案時使用 |

### 構想時參考過的專案（只參考做法，沒有使用其程式碼）

| 專案 | 參考了什麼 | 授權 |
|---|---|---|
| [repo-explainer](https://github.com/johnpsasser/repo-explainer) | 「讀 repo → 產腳本 → 影片」的整體流程 | MIT |
| [code-video-generator](https://github.com/sleuth-io/code-video-generator) | 用程式產生程式碼講解影片 | Apache-2.0 |
| [OpenMontage](https://github.com/calesthio/OpenMontage) | 由 AI agent 驅動的影片產線 | AGPL-3.0 |
| [Remotion Agent Skills](https://www.remotion.dev/docs/ai/skills) | 讓 Claude Code 寫 Remotion 影片 | Remotion License |
