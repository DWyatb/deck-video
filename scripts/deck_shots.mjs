// 依 deck.json 的 screenshots 截網頁畫面（1920x1080），並記下每張圖要框的元素位置。
//   node scripts/deck_shots.mjs <deck.json> <輸出資料夾>
// 一般由 `python scripts/deck.py <deck> shots` 呼叫。網頁要先開著（見 screenshots.serve）。
// 用 Remotion 自己下載的 chrome-headless-shell，透過 CDP 操作頁面，不另外裝 puppeteer。
//
// screenshots 欄位：
//   url      要截的網址
//   prepare  每張圖截之前先在頁面裡跑的 JS（例如關掉提示列、固定淺色主題）
//   ready    回傳 true 才開始操作的 JS 條件（例如頁面的函式載好了）
//   shots    [{ name, setup, marks }]：setup 是把畫面操作到要截的狀態的 JS（可 await，有 $ 與 sleep），
//            marks 是要框起來的元素 CSS selector，依序對應 slide 的 tones 與條列
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const [deckPath, OUT] = process.argv.slice(2);
if (!deckPath || !OUT) throw new Error("usage: node scripts/deck_shots.mjs <deck.json> <outdir>");
const cfg = JSON.parse(readFileSync(deckPath, "utf8")).screenshots;
if (!cfg) throw new Error("deck.json 沒有 screenshots");
const EXE = join(root, "node_modules", ".remotion", "chrome-headless-shell", "win64", "chrome-headless-shell-win64", "chrome-headless-shell.exe");
const W = 1600, H = 900, DPR = 1.2, PORT = 9333;
if (!existsSync(EXE)) throw new Error("找不到 chrome-headless-shell：" + EXE);
mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const proc = spawn(EXE, [`--remote-debugging-port=${PORT}`, "--no-first-run", "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
try {
  let ver;
  for (let i = 0; i < 40 && !ver; i++) { try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); } catch { await sleep(250); } }
  if (!ver) throw new Error("chrome-headless-shell 沒有起來");
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const ws = new WebSocket(list.find((t) => t.type === "page").webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0; const wait = new Map();
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && wait.has(d.id)) { wait.get(d.id)(d); wait.delete(d.id); } };
  const cdp = (method, params = {}) => new Promise((r, j) => { const i = ++id; wait.set(i, (d) => (d.error ? j(new Error(method + ": " + d.error.message)) : r(d.result))); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async (expr) => { const r = await cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || "eval error"); return r.result.value; };

  await cdp("Page.enable"); await cdp("Runtime.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: DPR, mobile: false });
  const meta = {};
  for (const s of cfg.shots) {
    await cdp("Page.navigate", { url: cfg.url });
    const ready = `document.readyState==='complete'` + (cfg.ready ? `&&(${cfg.ready})` : "");
    for (let i = 0; i < 40; i++) { await sleep(150); if (await evaluate(ready)) break; }
    const rects = await evaluate(`(async()=>{const $=id=>document.getElementById(id);const sleep=ms=>new Promise(r=>setTimeout(r,ms));
      ${cfg.prepare || ""};${s.setup};await sleep(400);
      return ${JSON.stringify(s.marks)}.map(q=>{const e=document.querySelector(q);if(!e)return null;const b=e.getBoundingClientRect();return[b.left,b.top,b.width,b.height].map(v=>Math.round(v*${DPR}))});})()`);
    if (rects.some((r) => !r)) throw new Error(`${s.name}: 有重點框找不到元素 ${JSON.stringify(s.marks)}`);
    const shot = await cdp("Page.captureScreenshot", { format: "png" });
    writeFileSync(join(OUT, s.name + ".png"), Buffer.from(shot.data, "base64"));
    meta[s.name] = rects;
    console.log(s.name.padEnd(11), JSON.stringify(rects));
  }
  writeFileSync(join(OUT, "shots.json"), JSON.stringify(meta, null, 1));
  ws.close();
} finally { proc.kill(); }
