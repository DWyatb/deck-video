"""從一份 PPT 模板做出 templates/<name>/（theme.json ＋ 封面／內頁底圖）。

    python scripts/theme_tools.py scan  <template.pptx> <name>      # 匯出候選圖、取色、建 theme.json 草稿
    python scripts/theme_tools.py clean <in.png> <out.png> x0,y0,x1,y1 [x0,y0,x1,y1 ...] [--fill #rrggbb]
    python scripts/theme_tools.py use   <name> <cover.png> <content.png>   # 指定封面／內頁底圖

scan 之後的判斷要人（或 Claude 看圖）做：
- 模板有真的版面（layoutNN_*.png 是乾淨的空白頁）→ 直接 use 那兩張。
- 模板每頁都是整張圖→ 挑一張，用 clean 把圖上原本的字塗掉，再 use。
  clean 的座標用 1920 寬的像素；--fill 不給就取框左上角外面一點的顏色。邊緣有抗鋸齒殘影時把框放大幾像素再塗一次。
最後依取到的顏色改 theme.json 的 colors（accent／coral／body…），版面位置先沿用 default 的。
"""
import json
import pathlib
import shutil
import subprocess
import sys
from collections import Counter

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent


def scan(src, name):
    tdir = ROOT / "templates" / name
    cand = tdir / "candidates"
    cand.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, tdir / "source.pptx")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "pptx_export.ps1"),
                    "-Src", str(tdir / "source.pptx"), "-OutDir", str(cand)], check=True)
    lines = []
    for png in sorted(cand.glob("*.png")):
        im = Image.open(png).convert("RGB").resize((480, 270))
        top = Counter(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()).most_common(6)
        lines.append(png.name + "  " + "  ".join("#%02x%02x%02x(%d%%)" % (c + (n * 100 // (480 * 270),)) for c, n in top))
    (cand / "palette.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    theme_p = tdir / "theme.json"
    if not theme_p.exists():
        t = json.loads((ROOT / "templates" / "default" / "theme.json").read_text(encoding="utf-8"))
        t["_comment"] = f"{name} 模板（草稿）：colors 與 backgrounds 要依 candidates/ 的圖改；版面位置沿用 default。"
        t["backgrounds"] = {"cover": "cover_bg.png", "content": "content_bg.png"}
        theme_p.write_text(json.dumps(t, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"scan: {len(lines)} 張候選圖在 {cand}，顏色在 palette.txt，theme.json 草稿在 {theme_p}")


def clean(src, dst, rects, fill=None):
    im = Image.open(src).convert("RGB")
    k = im.width / 1920
    px = im.load()
    for r in rects:
        x0, y0, x1, y1 = [int(int(v) * k) for v in r.split(",")]
        if fill:
            c = tuple(int(fill.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        else:
            c = px[max(0, x0 - 4), max(0, y0 - 4)]
        for y in range(y0, min(y1, im.height)):
            for x in range(x0, min(x1, im.width)):
                px[x, y] = c
    im.save(dst)
    print("clean:", dst)


def use(name, cover, content):
    tdir = ROOT / "templates" / name
    for src, dst in ((cover, "cover_bg.png"), (content, "content_bg.png")):
        Image.open(src).convert("RGB").resize((3840, 2160)).save(tdir / dst)
    print(f"use: {tdir / 'cover_bg.png'}、{tdir / 'content_bg.png'}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "scan" and len(a) == 3:
        scan(a[1], a[2])
    elif a[0] == "clean" and len(a) >= 4:
        fill = a[a.index("--fill") + 1] if "--fill" in a else None
        clean(a[1], a[2], [r for r in a[3:] if "," in r], fill)
    elif a[0] == "use" and len(a) == 4:
        use(a[1], a[2], a[3])
    else:
        raise SystemExit(__doc__)
