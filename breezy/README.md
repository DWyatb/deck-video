# 本機跑 BreezyVoice（runner = local）

預設旁白在 Kaggle 跑，不需要這個。只有內容不能送到外部服務、或沒有 Kaggle 時才用本機。

需要：NVIDIA 顯示卡、Docker Desktop、約 25 GB 空間（映像約 19 GB＋模型約 3 GB）。
4GB 顯示記憶體的筆電顯卡實測：15 段（約 4 分鐘旁白）要 63 分鐘；Kaggle T4 約 11 分鐘。

```bash
git clone https://github.com/mtkresearch/BreezyVoice.git ~/Documents/GitHub/BreezyVoice   # 或設 BREEZY_DIR
cd ~/Documents/GitHub/BreezyVoice
docker compose build            # 建 breezyvoice:latest（原版 Dockerfile；第一次很久）
```

原版 Dockerfile 建得起來但跑不起來，`Dockerfile.fix` 是在它上面補的一層（deck.py 會自動複製過去、建 `breezyvoice:fixed`）：
libnvrtc 連結、`ruamel.yaml==0.17.40`、`setuptools<70`、g2pw 指定 CPU。
原版 Dockerfile 本身也要先改過才建得起來（2026-10 時）：`setuptools<70` 的 build constraint、
onnxruntime 一般版與 GPU 版互相覆蓋、`transformers==4.44.2`、`datasets==2.21.0`。

又冒出新錯誤時，先在暫時容器裡試對（`docker run --rm --entrypoint bash breezyvoice:fixed ...`），
確定能合成出聲音再寫回 `Dockerfile.fix`，不要每改一行就重建。半精度（fp16）快 2–6 倍但會漏字，不要用。
