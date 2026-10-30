# templates：PPT 模板

每個模板一個資料夾 `templates/<name>/`：

```
templates/<name>/
├─ source.pptx       原始模板（使用者給的）
├─ theme.json        顏色、底圖檔名、每種頁型的位置與字級（PPT 與影片共用）
├─ cover_bg.png      封面底圖（3840x2160）
├─ content_bg.png    內頁底圖
└─ candidates/       scan 匯出的候選圖與取色結果（做完可刪）
```

## 加一個新模板

1. 把模板放進來，掃描：
   `python scripts/theme_tools.py scan <模板.pptx> <name>`
   會用 PowerPoint 把每張投影片、每種版面（空白套一次）匯出成 `candidates/*.png`，主要顏色寫在 `candidates/palette.txt`，
   並從 default 複製一份 `theme.json` 草稿。
2. 看圖挑封面與內頁底圖：
   - 模板有真的版面：`layoutNN_*.png` 是乾淨的空白頁，直接用。
   - 模板每頁都是整張圖：挑一張，把圖上原本的字塗掉：
     `python scripts/theme_tools.py clean <in.png> <out.png> x0,y0,x1,y1 [...]`（1920 寬的座標；`--fill #rrggbb` 指定顏色）。
     塗完用 Read 看一次，邊緣有殘影就把框放大幾像素再塗。
3. `python scripts/theme_tools.py use <name> <封面.png> <內頁.png>`
4. 依 palette.txt 改 `theme.json` 的 `colors`（底色 `bg`、強調 `accent`、第二強調 `coral`、內文 `body`、標題 `white`…），
   字型 `font`。版面位置先沿用；模板的 Logo、頁碼區如果擋到內容，再調 `layout` 的座標。
5. 用 `projects/example` 換成這個 theme 出一次 PPT 和一格影片，看過再用。

## default

通用深藍模板，沒有 Logo、沒有 source.pptx。`cover_bg.png`／`content_bg.png` 是純色底加頁尾漸層色帶，封面左下多一條強調色細線。
主色：底 #14213D、強調青 #2EC4B6、橘 #FF7F51、內文 #C9D1D9。
