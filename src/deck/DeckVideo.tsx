// 通用的「簡報式影片」：一份 deck.json → 一頁一個場景，旁白、字幕、截圖重點框。
//
// 版面與配色全部來自 templates/<name>/theme.json，跟 scripts/deck_pptx.py 的簡報讀同一份，所以影片與 PPT 一頁對一頁。
// 位置單位是英吋（1 英吋 = 1920 / 投影片寬），字級是 pt（1pt = 1 英吋 / 72）。
// 要輸出哪一份 deck 由 src/deck/active.ts 決定（scripts/deck.py timing 產生）。
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { active } from "./active";

/* eslint-disable @typescript-eslint/no-explicit-any */
const A: any = active;
const T = A.theme;
const L = T.layout;
const C = T.colors;
const IN = Math.round(1920 / T.slide.w);   // 13.333 英吋寬 → 144px；取整數避免次像素位移
const PT = IN / 72;
const FONT = `${T.font}, PingFang TC, Segoe UI, sans-serif`;
const SLIDES: any[] = A.deck.slides;
const TOTAL = SLIDES.length;
// 素材由 scripts/deck.py timing 同步到 public/_active/（bg、shots、vo）
const asset = (p: string) => staticFile(`_active/${p}`);
const tone = (t?: string) => C[t || "accent"] ?? C.accent;

const useIn = (delay = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping: 200 } });
};
/** 把 n 個項目攤在場景前 fraction 段：講到哪，字出到哪 */
const useSpread = (n: number, fraction = 0.6) => {
  const { durationInFrames } = useVideoConfig();
  return n <= 1 ? 0 : Math.max(8, Math.round((durationInFrames * fraction) / n));
};
const At: React.FC<{ x: number; y: number; w?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ x, y, w, style, children }) => (
  <div style={{ position: "absolute", left: x * IN, top: y * IN, width: w ? w * IN : undefined, ...style }}>{children}</div>
);
const Dot: React.FC<{ x: number; y: number; d: number; c: string }> = ({ x, y, d, c }) => (
  <div style={{ position: "absolute", left: x * IN, top: y * IN, width: d * IN, height: d * IN, borderRadius: "50%", background: c }} />
);

/** 每頁的底：模板底圖＋分類標＋標題＋頁碼，內容前後淡入淡出 */
const Page: React.FC<{ n: number; bg: "cover" | "content"; kicker?: string; title?: string; children: React.ReactNode }> = ({ n, bg, kicker, title, children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const op = interpolate(frame, [0, 10, durationInFrames - 8, durationInFrames], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const h = useIn(0);
  const p = L.page;
  return (
    <AbsoluteFill style={{ fontFamily: FONT, color: C.body }}>
      <Img src={asset(`bg/${T.backgrounds[bg]}`)} style={{ position: "absolute", width: 1920, height: 1080 }} />
      <AbsoluteFill style={{ opacity: op }}>
        {kicker ? <At x={p.kicker.x} y={p.kicker.y} style={{ fontSize: p.kicker.size * PT, color: C.accent, letterSpacing: (p.kicker.spacing / 100) * 2, opacity: h }}>{kicker}</At> : null}
        {title ? <At x={p.title.x} y={p.title.y} w={p.title.w} style={{ fontSize: p.title.size * PT, color: C.white, fontWeight: 700, opacity: h, transform: `translateY(${interpolate(h, [0, 1], [16, 0])}px)` }}>{title}</At> : null}
        {children}
        <At x={p.pageNo.x} y={p.pageNo.y} w={p.pageNo.w} style={{ fontSize: p.pageNo.size * PT, textAlign: "right" }}>{n} / {TOTAL}</At>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------- cover ----------
const Cover: React.FC<{ n: number; s: any }> = ({ n, s }) => {
  const a = useIn(4), b = useIn(30);
  const c = L.cover;
  return (
    <Page n={n} bg="cover">
      {s.year ? <At x={c.year.x} y={c.year.y} style={{ fontSize: c.year.size * PT, lineHeight: 1, color: C.digits, fontWeight: 700, fontStyle: "italic" }}>{s.year}</At> : null}
      <div style={{ opacity: a, transform: `translateY(${interpolate(a, [0, 1], [24, 0])}px)` }}>
        <At x={c.org.x} y={c.org.y} style={{ fontSize: c.org.size * PT }}>{s.org}</At>
        <At x={c.title.x} y={c.title.y} w={c.title.w} style={{ fontSize: c.title.size * PT, color: C.coral, fontWeight: 700 }}>{s.title}</At>
        <div style={{ position: "absolute", left: c.rule.x * IN, top: c.rule.y * IN, width: c.rule.w * IN * a, height: 5, background: C.coral }} />
      </div>
      <At x={c.subtitle.x} y={c.subtitle.y} w={c.subtitle.w} style={{ fontSize: c.subtitle.size * PT, lineHeight: 1.5, opacity: b }}>
        {(s.subtitle || []).map((x: any, i: number) => <div key={i} style={x.strong ? { color: C.white } : undefined}>{x.text}</div>)}
      </At>
    </Page>
  );
};

// ---------- bullets ----------
const BulletRow: React.FC<{ i: number; sp: number; t: string; c: string }> = ({ i, sp, t, c }) => {
  const e = useIn((i + 1) * sp);
  const b = L.bullets;
  const y = b.y + i * b.gap;
  return (
    <div style={{ opacity: e, transform: `translateX(${interpolate(e, [0, 1], [-30, 0])}px)` }}>
      <Dot x={b.x} y={y + b.dotDy} d={b.dot} c={c} />
      <At x={b.x + b.textDx} y={y} w={b.w - b.textDx} style={{ fontSize: b.size * PT }}>{t}</At>
    </div>
  );
};
const Bullets: React.FC<{ n: number; s: any }> = ({ n, s }) => {
  const sp = useSpread(s.items.length + 1);
  const note = useIn(80);
  const b = L.bullets;
  return (
    <Page n={n} bg="content" kicker={s.kicker} title={s.title}>
      {s.items.map((t: string, i: number) => <BulletRow key={i} i={i} sp={sp} t={t} c={tone(s.tone)} />)}
      {s.note ? <At x={b.x} y={b.note.y} style={{ fontSize: b.note.size * PT, color: C.label, opacity: note }}>{s.note}</At> : null}
    </Page>
  );
};

// ---------- boxes ----------
const Box: React.FC<{ i: number; sp: number; bx: any; last: boolean }> = ({ i, sp, bx, last }) => {
  const e = useIn((i + 1) * sp);
  const b = L.boxes;
  const x = b.x + i * b.step;
  return (
    <div style={{ opacity: e, transform: `translateY(${interpolate(e, [0, 1], [30, 0])}px)` }}>
      <div style={{ position: "absolute", left: x * IN, top: b.y * IN, width: b.w * IN, height: b.h * IN, background: C.box, border: `2px solid ${C.boxLine}` }} />
      <At x={x + b.padX} y={b.headY} style={{ fontSize: b.headSize * PT, color: C.white, fontWeight: 700 }}>{bx.head}</At>
      <At x={x + b.padX} y={b.linesY} style={{ fontSize: b.linesSize * PT, lineHeight: 1.45 }}>{bx.lines.map((l: string) => <div key={l}>{l}</div>)}</At>
      {last ? null : <At x={x + b.w} y={b.arrowY} w={b.arrowW} style={{ fontSize: b.arrowSize * PT, color: C.accent, textAlign: "center" }}>→</At>}
    </div>
  );
};
const Boxes: React.FC<{ n: number; s: any }> = ({ n, s }) => {
  const sp = useSpread(s.boxes.length + 1, 0.7);
  return (
    <Page n={n} bg="content" kicker={s.kicker} title={s.title}>
      {s.boxes.map((bx: any, i: number) => <Box key={i} i={i} sp={sp} bx={bx} last={i === s.boxes.length - 1} />)}
    </Page>
  );
};

// ---------- steps ----------
const StepRow: React.FC<{ i: number; sp: number; r: any }> = ({ i, sp, r }) => {
  const e = useIn(i * sp);
  const st = L.steps;
  const y = st.y + i * st.gap;
  const c = r.human ? C.coral : C.accent;
  return (
    <div style={{ opacity: e, transform: `translateX(${interpolate(e, [0, 1], [-30, 0])}px)` }}>
      <div style={{ position: "absolute", left: st.circleX * IN, top: (y + st.circleDy) * IN, width: st.circle * IN, height: st.circle * IN, borderRadius: "50%", background: c, color: C.white, fontSize: st.numSize * PT, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>{i + 1}</div>
      <At x={st.whoX} y={y + st.whoDy} style={{ fontSize: st.whoSize * PT, color: c, fontWeight: r.human ? 700 : 400 }}>{r.who}</At>
      <At x={st.textX} y={y + st.textDy} style={{ fontSize: st.textSize * PT, color: C.white, fontWeight: r.human ? 700 : 400 }}>{r.text}</At>
      <At x={st.descX} y={y + st.descDy} w={st.descW} style={{ fontSize: st.descSize * PT }}>{r.desc}</At>
      <div style={{ position: "absolute", left: st.circleX * IN, top: (y + st.ruleDy) * IN, width: (st.ruleX2 - st.circleX) * IN, height: 1, background: C.rule }} />
    </div>
  );
};
const Steps: React.FC<{ n: number; s: any }> = ({ n, s }) => {
  const sp = useSpread(s.steps.length, 0.8);
  const h = useIn(0);
  const st = L.steps;
  const legend = Object.entries(s.legend || {});
  return (
    <Page n={n} bg="content" kicker={s.kicker} title={s.title}>
      <div style={{ opacity: h }}>
        {legend.map(([k, label], i) => (
          <div key={k}>
            <Dot x={st.legendX[i]} y={st.legendDotY} d={st.legendDot} c={tone(k)} />
            <At x={st.legendX[i] + st.legendTextDx} y={st.legendY} style={{ fontSize: st.legendSize * PT }}>{label as string}</At>
          </div>
        ))}
      </div>
      {s.steps.map((r: any, i: number) => <StepRow key={i} i={i} sp={sp} r={r} />)}
    </Page>
  );
};

// ---------- screen ----------
const Mark: React.FC<{ i: number; sp: number; r: number[]; c: string; k: number }> = ({ i, sp, r, c, k }) => {
  const e = useIn(12 + (i + 1) * sp);
  const pad = 6;
  const h = Math.min(r[1] + r[3], L.screen.shotH - 6) - r[1];
  return (
    <div style={{ position: "absolute", left: r[0] * k - pad, top: r[1] * k - pad, width: r[2] * k + pad * 2, height: h * k + pad * 2,
      border: `4px solid ${c}`, opacity: e, transform: `scale(${interpolate(e, [0, 1], [1.05, 1])})` }} />
  );
};
const Point: React.FC<{ i: number; sp: number; t: string; c: string }> = ({ i, sp, t, c }) => {
  const e = useIn(12 + (i + 1) * sp);
  const sc = L.screen;
  const bx = sc.imgX + sc.imgW + sc.gap;
  const y = sc.pointY + i * sc.pointGap;
  return (
    <div style={{ opacity: e, transform: `translateX(${interpolate(e, [0, 1], [24, 0])}px)` }}>
      <Dot x={bx} y={y + sc.dotDy} d={sc.dot} c={c} />
      <At x={bx + sc.textDx} y={y} w={sc.rightEdge - bx - sc.textDx} style={{ fontSize: sc.pointSize * PT, lineHeight: 1.35 }}>{t}</At>
    </div>
  );
};
const SHOTS: Record<string, number[][]> = A.shots || {};
const Screen: React.FC<{ n: number; s: any }> = ({ n, s }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const sc = L.screen;
  const marks = SHOTS[s.shot] || [];
  const sp = useSpread(Math.max(marks.length, s.items.length) + 1, 0.7);
  const imgW = sc.imgW * IN, imgH = (imgW * sc.shotH) / sc.shotW, k = imgW / sc.shotW;
  const m0 = marks[0] || [0, 0, sc.shotW, sc.shotH];
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.025]);
  const img = useIn(4);
  const tones: string[] = s.tones || [];
  return (
    <Page n={n} bg="content" kicker={s.kicker} title={s.title}>
      <div style={{ position: "absolute", left: sc.imgX * IN, top: sc.imgY * IN, width: imgW, height: imgH, overflow: "hidden", border: `2px solid ${C.boxLine}`, background: "#fff", opacity: img }}>
        <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})`, transformOrigin: `${(m0[0] + m0[2] / 2) * k}px ${(m0[1] + m0[3] / 2) * k}px` }}>
          <Img src={asset(`shots/${s.shot}.png`)} style={{ width: "100%", height: "100%" }} />
          {marks.map((r, i) => <Mark key={i} i={i} sp={sp} r={r} c={tone(tones[i])} k={k} />)}
        </div>
      </div>
      {s.items.map((t: string, i: number) => <Point key={i} i={i} sp={sp} t={t} c={tone(tones[i])} />)}
    </Page>
  );
};

const KINDS: Record<string, React.FC<{ n: number; s: any }>> = { cover: Cover, bullets: Bullets, boxes: Boxes, steps: Steps, screen: Screen };

/** 字幕放在頁尾色帶正中間，避開右邊的頁碼 */
const Subtitles: React.FC = () => {
  const frame = useCurrentFrame();
  const cue = (A.subs as any[]).find((c) => frame >= c.from && frame < c.to);
  if (!cue) return null;
  const st = T.subtitle;
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: st.top_px, display: "flex", justifyContent: "center" }}>
        <div style={{ background: st.bg, color: "#fff", fontSize: st.size_px, lineHeight: 1.4, padding: "4px 22px", borderRadius: 6, maxWidth: st.maxw_px }}>{cue.text}</div>
      </div>
    </AbsoluteFill>
  );
};

export const DECK_FRAMES: number = SLIDES.reduce((a, s) => a + A.frames[s.id], 0);

export const DeckVideo: React.FC = () => {
  let at = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: C.bg }}>
      {SLIDES.map((s, i) => {
        const from = at;
        const d = A.frames[s.id];
        at += d;
        const Comp = KINDS[s.type];
        return (
          <Sequence key={s.id} from={from} durationInFrames={d}>
            <Comp n={i + 1} s={s} />
            <Audio src={asset(`vo/${s.id}.wav`)} />
          </Sequence>
        );
      })}
      <Subtitles />
    </AbsoluteFill>
  );
};
