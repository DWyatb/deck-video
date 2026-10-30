// 影片清單：只有一支 DeckVideo。要出哪個專案由 src/deck/active.ts 決定（python scripts/deck.py <project> timing 產生）。
import { Composition } from "remotion";
import { DeckVideo, DECK_FRAMES } from "./deck/DeckVideo";

export const RemotionRoot: React.FC = () => (
  <Composition id="DeckVideo" component={DeckVideo} durationInFrames={DECK_FRAMES} fps={30} width={1920} height={1080} />
);
