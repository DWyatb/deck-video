"""一個專案的 deck.json → PPT ＋ 旁白 ＋ 影片（含字幕）＋ .srt。版型在 templates/<name>/theme.json，PPT 與影片共用。

    python scripts/deck.py <project> <步驟...> [--adopt] [--all] [--local]

<project> 是 projects/ 底下的資料夾名，或 deck.json 的路徑。產出都在 projects/<project>/out/。步驟：
    shots          用 headless Chrome 截 deck.json 的 screenshots（網頁要先開著，見 screenshots.serve）
    pptx           輸出 PPT
    voice          產旁白：只重產文字改過的頁。engine=breezy 預設在 Kaggle 跑（--local 改用本機 Docker），sapi 是 Windows 內建
    sample <id>    只產一頁旁白當試聽（輸出 out/sample-<id>.wav，不影響正式音檔）
    timing         依音檔長度算每頁秒數、排字幕，寫 src/deck/active.ts、out/<project>.srt，並把素材同步到 public/_active
    video          timing ＋ Remotion 輸出 out/<project>.mp4
    all            pptx voice video（不含 shots）
    kaggle-cells   不用 API 時：產出要手動貼到 Kaggle 的兩格程式碼（out/kaggle-cells.txt）
    import <zip>   裝回 Kaggle 下載的 vo.zip：只收這份 deck 的 <id>.wav，登記後調語速
--adopt  把現有音檔登記成「對應目前的文字」，不重產   --all  全部重產
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import wave

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS = 30
TAIL = 18        # 每段唸完留 0.6 秒
MAXLEN = 22      # 字幕一行最多幾個字
BREEZY_DIR = pathlib.Path(os.environ.get("BREEZY_DIR", pathlib.Path.home() / "Documents" / "GitHub" / "BreezyVoice"))


def load(arg):
    p = pathlib.Path(arg)
    if not p.suffix:
        p = ROOT / "projects" / arg / "deck.json"
    deck = json.loads(p.read_text(encoding="utf-8"))
    name = p.parent.name
    theme = json.loads((template_dir(deck) / "theme.json").read_text(encoding="utf-8"))
    return deck, theme, name


def template_dir(deck):
    return ROOT / "templates" / deck.get("theme", "default")


def pdir(name):
    d = ROOT / "projects" / name
    for sub in ("shots", "raw", "vo", "out"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def spoken(deck, text):
    for a, b in deck.get("pronounce", {}).items():
        text = text.replace(a, b)
    return text


def fingerprint(deck, s):
    """音檔對應哪一段文字。runner（kaggle／local）不算進來：同一個模型、同一個參考聲音，在哪裡跑都算同一份。"""
    v = deck["voice"]
    eng = v["engine"]
    cfg = {k: x for k, x in v.get(eng, {}).items() if k != "runner"}
    key = json.dumps([eng, cfg, spoken(deck, s["narration"])], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def manifest(name):
    p = pdir(name) / "raw" / "manifest.json"
    return p, (json.loads(p.read_text(encoding="utf-8")) if p.exists() else {})


def todo_slides(deck, name, everything=False):
    """文字（或讀音、語音設定）跟現有音檔對不上的頁面。"""
    d = pdir(name)
    _, man = manifest(name)
    return [s for s in deck["slides"]
            if everything or man.get(s["id"]) != fingerprint(deck, s) or not (d / "raw" / f"{s['id']}.wav").exists()]


# ---------- shots ----------
def step_shots(deck, theme, name):
    run(["node", str(ROOT / "scripts" / "deck_shots.mjs"), str(ROOT / "projects" / name / "deck.json"), str(pdir(name) / "shots")], cwd=ROOT)


# ---------- pptx ----------
def step_pptx(deck, theme, name):
    out = pdir(name) / "out" / f"{name}.pptx"
    run([sys.executable, str(ROOT / "scripts" / "deck_pptx.py"), name, str(out)])
    copy_out(deck, "pptx", out)


def copy_out(deck, kind, src):
    dst = deck.get("copy_to", {}).get(kind)
    if dst:
        shutil.copyfile(src, (ROOT / dst).resolve())
        print(f"copied {kind} -> {dst}")


# ---------- voice ----------
def step_voice(deck, theme, name, adopt=False, everything=False, local=False):
    d = pdir(name)
    man_p, man = manifest(name)
    if adopt:
        for s in deck["slides"]:
            if (d / "raw" / f"{s['id']}.wav").exists():
                man[s["id"]] = fingerprint(deck, s)
        man_p.write_text(json.dumps(man, indent=1), encoding="utf-8")
        print("adopted", len(man), "clips")
    todo = todo_slides(deck, name, everything)
    print(f"voice: {len(deck['slides']) - len(todo)} up to date, {len(todo)} to generate", flush=True)
    if todo:
        eng = deck["voice"]["engine"]
        if eng == "breezy" and not local and deck["voice"]["breezy"].get("runner", "kaggle") == "kaggle":
            zip_path = kaggle_run(deck, name, todo)
            install_zip(deck, name, zip_path)
        else:
            tmp = d / "raw_new"
            tmp.mkdir(exist_ok=True)
            if eng == "breezy":
                _breezy_local(deck, todo, d, tmp)
            elif eng == "sapi":
                _sapi(deck, todo, tmp)
            else:
                raise SystemExit(f"unknown voice engine {eng}")
            for s in todo:
                src = tmp / f"{s['id']}.wav"
                if not src.exists():
                    raise SystemExit(f"{s['id']}: 沒有產出音檔")
                shutil.move(str(src), str(d / "raw" / f"{s['id']}.wav"))
                man[s["id"]] = fingerprint(deck, s)
                man_p.write_text(json.dumps(man, indent=1), encoding="utf-8")
            tmp.rmdir()
    apply_tempo(deck, name)


def apply_tempo(deck, name):
    """語速：atempo 只加快不變調。raw/ 是原始音檔，vo/ 是影片用的。"""
    d = pdir(name)
    tempo = float(deck["voice"].get("tempo", 1.0))
    for s in deck["slides"]:
        src, dst = d / "raw" / f"{s['id']}.wav", d / "vo" / f"{s['id']}.wav"
        if not src.exists():
            continue
        if tempo == 1.0:
            shutil.copyfile(src, dst)
        else:
            run(["npx", "remotion", "ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter:a", f"atempo={tempo}", str(dst)],
                cwd=ROOT, shell=True)


def step_sample(deck, theme, name, sid, local=False):
    """只產一頁當試聽，放 out/sample-<id>.wav，不動正式音檔。"""
    by_id = {s["id"]: s for s in deck["slides"]}
    if sid not in by_id:
        raise SystemExit(f"沒有 id={sid} 的頁面")
    s = by_id[sid]
    d = pdir(name)
    out = d / "out" / f"sample-{sid}.wav"
    eng = deck["voice"]["engine"]
    if eng == "breezy" and not local and deck["voice"]["breezy"].get("runner", "kaggle") == "kaggle":
        zip_path = kaggle_run(deck, name, [s], tag="sample")
        import zipfile
        with zipfile.ZipFile(zip_path) as z:
            info = next(i for i in z.infolist() if pathlib.PurePosixPath(i.filename).name == f"{sid}.wav")
            out.write_bytes(z.read(info))
    else:
        tmp = d / "raw_new"
        tmp.mkdir(exist_ok=True)
        (_breezy_local(deck, [s], d, tmp) if eng == "breezy" else _sapi(deck, [s], tmp))
        shutil.move(str(tmp / f"{sid}.wav"), str(out))
        tmp.rmdir()
    print("sample:", out)


def breezy_csv_text(deck, slides):
    import csv
    import io
    b = deck["voice"]["breezy"]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["speaker_prompt_audio_filename", "speaker", "speaker_prompt_text_transcription", "content_to_synthesize", "output_audio_filename"])
    for s in slides:
        w.writerow([b["speaker"], "女", b["speaker_text"], spoken(deck, s["narration"]), s["id"]])
    return buf.getvalue()


# ---------- Kaggle：免費 GPU（T4）上跑 BreezyVoice ----------
# 官方筆記本 https://www.kaggle.com/code/a24998667/breezyvoice-playground 直接跑會失敗，這些是 2026-10 修好的版本：
# whisper 要舊 setuptools 編譯、onnxruntime-gpu 1.20.1 已下架、g2pw 會帶進 CPU 版 onnxruntime、
# HyperPyYAML 不吃新 ruamel.yaml、g2pw 建 InferenceSession 沒指定 providers。
# 已套好這些修正的公開筆記本（手動備案時讓使用者 Copy & Edit 到自己帳號）：
KAGGLE_NOTEBOOK = "https://www.kaggle.com/code/gtbmamb/breezyvoice-playground"
KAGGLE_REQUIREMENTS = """conformer==0.3.2
openai-whisper==20231117
HyperPyYAML==1.2.2
hydra-core==1.3.2
lightning==2.2.4
wget==3.2
onnxruntime-gpu==1.20.2
opencc-python-reimplemented
g2pw
https://www.modelscope.cn/models/speech_tts/speech_kantts_ttsfrd/resolve/master/ttsfrd_dependency-0.1-py3-none-any.whl
https://www.modelscope.cn/models/speech_tts/speech_kantts_ttsfrd/resolve/master/ttsfrd-0.3.9-cp310-cp310-linux_x86_64.whl
"""
KAGGLE_INSTALL = r'''!pip install -q "setuptools<70" wheel
!pip install -q --no-build-isolation openai-whisper==20231117
!pip install -q -r requirements.txt
!pip uninstall -q -y onnxruntime onnxruntime-gpu
!pip install -q onnxruntime-gpu==1.20.2
!pip install -q "ruamel.yaml==0.17.40"
!sed -i 's|sess_options=sess_options)|sess_options=sess_options, providers=["CPUExecutionProvider"])|' $(python -c "import g2pw,os;print(os.path.join(os.path.dirname(g2pw.__file__),'api.py'))")
'''


def kaggle_generate_cell(deck, slides):
    csv_text = breezy_csv_text(deck, slides)
    if '"""' in csv_text:
        raise SystemExit('旁白裡有 """，請改掉再產')
    return ('csv_text = """' + csv_text + '"""\n'
            'open("/kaggle/working/batch.csv", "w", encoding="utf-8").write(csv_text)\n'
            '!rm -rf /kaggle/working/vo /kaggle/working/vo.zip\n'
            '!python batch_inference.py --csv_file /kaggle/working/batch.csv --speaker_prompt_audio_folder data --output_audio_folder /kaggle/working/vo\n'
            '!cd /kaggle/working && zip -q -r vo.zip vo && ls -la vo\n')


def kaggle_cli():
    exe = shutil.which("kaggle")
    if not exe:
        raise SystemExit("找不到 kaggle 指令：先 `pip install kaggle`，再把 API token 放好（步驟見 README 的「旁白：用 Kaggle 免費 GPU 跑 BreezyVoice」）")
    return exe


def kaggle_username():
    """帳號名稱（不是金鑰）：環境變數 KAGGLE_USERNAME，或 config.json 的 kaggle_user。"""
    token = pathlib.Path.home() / ".kaggle" / "access_token"
    if not (os.environ.get("KAGGLE_API_TOKEN") or token.exists() or (pathlib.Path.home() / ".kaggle" / "kaggle.json").exists()):
        raise SystemExit("Kaggle 還沒登入：到 https://www.kaggle.com/settings/api 按「Generate New Token」，"
                         "把那串 token 存成 ~/.kaggle/access_token（步驟見 README 的「旁白：用 Kaggle 免費 GPU 跑 BreezyVoice」）")
    user = os.environ.get("KAGGLE_USERNAME")
    cfg = ROOT / "config.json"
    if not user and cfg.exists():
        user = json.loads(cfg.read_text(encoding="utf-8")).get("kaggle_user")
    if not user:
        raise SystemExit("不知道 Kaggle 帳號名稱：把 config.example.json 複製成 config.json，填你自己的 kaggle_user")
    return user


def kaggle_run(deck, name, slides, tag="voice"):
    """把要產的頁寫成一份私人 Kaggle 筆記本、送上去在 GPU 上跑、等它跑完、下載 vo.zip。回傳 zip 路徑。
    筆記本是另外開的（<user>/deck-<tag>-<project>），不會動到使用者自己的筆記本。旁白文字會在 Kaggle（Google）上處理。"""
    user = kaggle_username()
    slug = re.sub(r"[^a-z0-9-]+", "-", f"deck-{tag}-{name}".lower()).strip("-")
    kdir = pdir(name) / "kaggle" / tag
    if kdir.exists():
        shutil.rmtree(kdir)
    kdir.mkdir(parents=True)

    def code(src):
        return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}
    cells = [
        code("!nvidia-smi --query-gpu=name,memory.total --format=csv\n"),
        code("!git clone -q https://github.com/mtkresearch/BreezyVoice.git\n"),
        code("%cd /kaggle/working/BreezyVoice\n"),
        code("!pip uninstall -q -y onnxruntime\n!sudo apt-get -y -q install cudnn9-cuda-12 > /dev/null\n"),
        code("%%writefile requirements.txt\n" + KAGGLE_REQUIREMENTS),
        code(KAGGLE_INSTALL),
        code("import time; _t0 = time.time()\n" + kaggle_generate_cell(deck, slides) + "print(f'GENERATE_SECONDS={time.time()-_t0:.0f}')\n"),
        # 只留 vo.zip 當輸出，其他（BreezyVoice 原始碼、模型快取）不帶回來
        code("%cd /kaggle/working\n!rm -rf BreezyVoice vo batch.csv\n!ls -la\n"),
    ]
    nb = {"cells": cells, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                                        "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 4}
    (kdir / "voice.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    meta = {"id": f"{user}/{slug}", "title": slug, "code_file": "voice.ipynb", "language": "python", "kernel_type": "notebook",
            "is_private": True, "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
            "dataset_sources": [], "competition_sources": [], "kernel_sources": [], "model_sources": []}
    (kdir / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    print(f"kaggle: 送出 {len(slides)} 頁到 {user}/{slug}（旁白文字會在 Kaggle 上處理）", flush=True)
    run([kaggle_cli(), "kernels", "push", "-p", str(kdir)])
    t0 = time.time()
    status = ""
    while time.time() - t0 < 90 * 60:
        time.sleep(30)
        r = subprocess.run([kaggle_cli(), "kernels", "status", f"{user}/{slug}"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        status = (r.stdout + r.stderr).strip()
        low = status.lower()
        print(f"  [{(time.time() - t0) / 60:4.1f} 分] {status[-80:]}", flush=True)
        if "complete" in low:
            break
        if "error" in low or "cancel" in low:
            raise SystemExit(f"Kaggle 執行失敗：{status}\n到 https://www.kaggle.com/code/{user}/{slug} 的 Logs 看原因")
    else:
        raise SystemExit(f"等了 90 分鐘還沒跑完：{status}")
    outdir = kdir / "output"
    outdir.mkdir()
    run([kaggle_cli(), "kernels", "output", f"{user}/{slug}", "-p", str(outdir)])
    zip_path = outdir / "vo.zip"
    if not zip_path.exists():
        raise SystemExit(f"Kaggle 跑完了但沒有 vo.zip；看 {outdir} 裡的 log 或 https://www.kaggle.com/code/{user}/{slug}")
    log = next(outdir.glob("*.log"), None)
    if log:
        m = re.search(r"GENERATE_SECONDS=(\d+)", log.read_text(encoding="utf-8", errors="replace"))
        gpu = re.search(r"(Tesla [A-Z0-9]+|NVIDIA [A-Za-z0-9 ]+?),", log.read_text(encoding="utf-8", errors="replace"))
        print(f"kaggle: 產生 {m.group(1) if m else '?'} 秒，GPU {gpu.group(1) if gpu else '?'}，全程 {(time.time() - t0) / 60:.1f} 分")
    return zip_path


def install_zip(deck, name, zip_path):
    """vo.zip 裝回來：只收這份 deck 有的 <id>.wav，登記成對應目前文字。不照壓縮檔裡的路徑解開。"""
    import zipfile
    d = pdir(name)
    by_id = {s["id"]: s for s in deck["slides"]}
    man_p, man = manifest(name)
    got = []
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            stem = pathlib.PurePosixPath(info.filename).name
            if not stem.endswith(".wav") or stem[:-4] not in by_id:
                continue
            sid = stem[:-4]
            (d / "raw" / stem).write_bytes(z.read(info))
            man[sid] = fingerprint(deck, by_id[sid])
            got.append(sid)
    man_p.write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(f"import: 裝了 {len(got)} 段（{', '.join(sorted(got))}）")
    missing = [s["id"] for s in todo_slides(deck, name)]
    if missing:
        print("還沒對上的頁面：", ", ".join(missing))


def step_import(deck, theme, name, zip_path):
    install_zip(deck, name, zip_path)
    apply_tempo(deck, name)


def step_kaggle_cells(deck, theme, name, everything=False):
    """不用 API 時的手動版：兩格程式碼，貼到 Kaggle 筆記本。"""
    todo = todo_slides(deck, name, everything)
    if not todo:
        print("每一頁的音檔都對得上目前的文字，不用產。要全部重產加 --all。")
        return
    out = pdir(name) / "out" / "kaggle-cells.txt"
    out.write_text("# 先把已修好的筆記本複製到自己的 Kaggle：打開 " + KAGGLE_NOTEBOOK + " → Copy & Edit\n"
                   "# 複製來的筆記本只要換第 2 段那一格（開頭是 csv_text =）→ Save Version → Save & Run All → Output 下載 vo.zip\n"
                   "# 改從官方筆記本複製時才需要第 1 段：接在 %%writefile requirements.txt 那格後面，取代 pip install 那格\n\n"
                   "# ==== 1. 安裝與相容修正 ====\n!sed -i 's/onnxruntime-gpu==1.20.1/onnxruntime-gpu==1.20.2/' requirements.txt\n" + KAGGLE_INSTALL +
                   "\n# ==== 2. 旁白清單＋產生聲音＋打包 ====\n" + kaggle_generate_cell(deck, todo), encoding="utf-8")
    print(f"kaggle-cells: {len(todo)} 頁，寫在 {out}")


# ---------- 本機跑 ----------
def _breezy_local(deck, todo, d, tmp):
    import csv
    b = deck["voice"]["breezy"]
    with (d / "batch.csv").open("w", encoding="utf-8", newline="") as f:
        f.write(breezy_csv_text(deck, todo))
    if not BREEZY_DIR.exists():
        raise SystemExit(f"本機沒有 BreezyVoice（{BREEZY_DIR}）；見 breezy/README.md，或改用 Kaggle")
    shutil.copyfile(ROOT / "breezy" / "Dockerfile.fix", BREEZY_DIR / "Dockerfile.fix")
    run(["docker", "build", "-q", "-f", "Dockerfile.fix", "-t", "breezyvoice:fixed", "."], cwd=BREEZY_DIR)
    vol = str(d).replace("\\", "/")
    prompt = []
    if b.get("speaker_dir"):   # 自訂參考聲音：放在這個資料夾，檔名 = speaker.wav
        prompt = ["-v", f"{(ROOT / b['speaker_dir']).as_posix()}:/prompt"]
    run(["docker", "run", "--rm", "--gpus", "all", "-e", "PYTHONUTF8=1",
         "-v", "breezyvoice_hf-cache:/root/.cache/huggingface", "-v", f"{vol}:/work", *prompt,
         "breezyvoice:fixed", "batch_inference.py", "--csv_file", "/work/batch.csv",
         "--speaker_prompt_audio_folder", "/prompt" if prompt else "data", "--output_audio_folder", f"/work/{tmp.name}"])


def _sapi(deck, todo, tmp):
    v = deck["voice"]["sapi"]
    spec = tmp / "spec.json"
    spec.write_text(json.dumps({"voice": v["voice"], "rate": v.get("rate", 0),
                                "lines": [{"id": s["id"], "text": spoken(deck, s["narration"])} for s in todo]},
                               ensure_ascii=False), encoding="utf-8")
    # -ExecutionPolicy Bypass 只對這一次執行有效，不改系統設定（從 Python 呼叫未簽署的本機 .ps1 會被預設原則擋下）
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "tts.ps1"),
         "-SpecPath", str(spec.relative_to(ROOT)), "-OutDir", str(tmp.relative_to(ROOT))])
    spec.unlink()


# ---------- timing + subtitles ----------
def chunks(text):
    out = []
    for sent in re.findall(r"[^。？！]+[。？！]?", text):
        sent = sent.strip()
        if not sent:
            continue
        if len(sent) <= MAXLEN:
            out.append(sent)
            continue
        cur = ""
        for part in re.findall(r"[^，、]+[，、]?", sent):
            if cur and len(cur) + len(part) > MAXLEN:
                out.append(cur)
                cur = part
            else:
                cur += part
        if cur:
            out.append(cur)
    return [re.sub(r"[。，、]$", "", c) for c in out]


def srt_ts(f):
    ms = round(f / FPS * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def sync_public(deck, name):
    """Remotion 只讀得到 public/，所以把這次要用的底圖、截圖、旁白同步到 public/_active/（產生物，不進 git）。"""
    act = ROOT / "public" / "_active"
    if act.exists():
        shutil.rmtree(act)
    for sub in ("bg", "shots", "vo"):
        (act / sub).mkdir(parents=True)
    for f in set(json.loads((template_dir(deck) / "theme.json").read_text(encoding="utf-8"))["backgrounds"].values()):
        shutil.copyfile(template_dir(deck) / f, act / "bg" / f)
    d = pdir(name)
    for f in (d / "shots").glob("*.png"):
        shutil.copyfile(f, act / "shots" / f.name)
    for f in (d / "vo").glob("*.wav"):
        shutil.copyfile(f, act / "vo" / f.name)


def step_timing(deck, theme, name):
    d = pdir(name)
    frames, cues, at = {}, [], 0
    for s in deck["slides"]:
        with wave.open(str(d / "vo" / f"{s['id']}.wav"), "rb") as w:
            sec = w.getnframes() / w.getframerate()
        speak = sec * FPS
        parts = chunks(s["narration"])
        total = sum(len(p) for p in parts)
        t = 0.0
        for p in parts:
            dur = speak * len(p) / total
            cues.append({"from": at + round(t), "to": at + round(t + dur), "text": p})
            t += dur
        frames[s["id"]] = int(sec * FPS + 0.999) + TAIL
        at += frames[s["id"]]
    shots_p = d / "shots" / "shots.json"
    shots = json.loads(shots_p.read_text(encoding="utf-8")) if shots_p.exists() else {}
    active = {"name": name, "deck": deck, "theme": theme, "frames": frames, "subs": cues, "shots": shots}
    (ROOT / "src" / "deck" / "active.ts").write_text(
        "// 由 scripts/deck.py timing 產生 —— 不要手改。目前要輸出的那份 deck。\n"
        f"export const active = {json.dumps(active, ensure_ascii=False)} as const;\n", encoding="utf-8")
    sync_public(deck, name)
    srt = "\n".join(f"{i}\n{srt_ts(c['from'])} --> {srt_ts(c['to'])}\n{c['text']}\n" for i, c in enumerate(cues, 1))
    (d / "out" / f"{name}.srt").write_text(srt, encoding="utf-8")
    print(f"timing: {len(frames)} slides, {at} frames = {at / FPS:.1f}s, {len(cues)} subtitle cues")


def step_video(deck, theme, name):
    step_timing(deck, theme, name)
    mp4 = pdir(name) / "out" / f"{name}.mp4"
    run(["npx", "remotion", "render", "DeckVideo", str(mp4), "--log=error"], cwd=ROOT, shell=True)
    copy_out(deck, "video", mp4)
    copy_out(deck, "srt", pdir(name) / "out" / f"{name}.srt")
    print("video:", mp4)


STEPS = {"shots": step_shots, "pptx": step_pptx, "timing": step_timing, "video": step_video}

if __name__ == "__main__":
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        raise SystemExit(__doc__)
    deck, theme, name = load(args[0])
    steps = ["pptx", "voice", "video"] if args[1:] == ["all"] else args[1:]
    i = 0
    while i < len(steps):
        st = steps[i]
        if st == "voice":
            step_voice(deck, theme, name, adopt="--adopt" in flags, everything="--all" in flags, local="--local" in flags)
        elif st == "kaggle-cells":
            step_kaggle_cells(deck, theme, name, everything="--all" in flags)
        elif st in ("import", "sample"):
            i += 1
            if i >= len(steps):
                raise SystemExit(f"{st} 後面要接參數")
            if st == "import":
                step_import(deck, theme, name, steps[i])
            else:
                step_sample(deck, theme, name, steps[i], local="--local" in flags)
        else:
            STEPS[st](deck, theme, name)
        i += 1
