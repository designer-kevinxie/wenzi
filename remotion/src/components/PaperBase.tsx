import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Theme } from "../theme";

/**
 * 紙面 —— 直接使用紙紋原圖,不做任何調色。
 *
 * 若紙紋是從 hook.mp4 抽的最後一幀,這裡必須零加工,
 * 否則和鉤子影片接在一起會有色差,硬切的接縫就會被看出來。
 *
 * 唯一保留的處理:極慢的位移(全片約 10px),
 * 用來避開平台對「完全靜止畫面」的低質判定。
 * 不想要的話把 DRIFT 設成 0。
 */

const DRIFT = 0; // px,全片位移總量;設 0 則完全靜止

/**
 * 紙紋輪換池。全部放在 remotion/public/。
 *
 * 版式、墨色、印章都固定,是刻意的 —— 帳號的識別度靠這些維持。
 * 但一天兩條、連刷三十張全同一張紙,讀者會判定「這個我看過了」而滑走。
 * 換紙是成本最低的變化:遠看仍是同一個帳號,連刷不膩。
 *
 * 只有一張紙時填一個元素即可,行為和以前完全一樣。
 * 紙紋要同源(同一批掃描、同樣色溫),否則帳號會看起來像換了主人。
 */
const PAPERS = ["paper.jpg"];

/** theme.ts 裡 texture 的預設值。等於這個值代表「沒有特別指定」→ 自動輪換。 */
const DEFAULT_TEXTURE = "paper.jpg";

/**
 * 用引文 id 決定用哪張紙,而不是 Math.random()。
 *
 * 理由:同一則引文每次渲染都必須拿到同一張紙。
 * 用隨機的話,重印一次卡片就換了張紙,和已發布的影片對不上;
 * 影片本身逐幀渲染時甚至可能每幀都不同。
 */
const pickPaper = (seed: string): string => {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) {
    h = (h * 31 + seed.charCodeAt(i)) | 0;
  }
  return PAPERS[Math.abs(h) % PAPERS.length];
};

export const PaperBase: React.FC<{
  theme: Theme;
  still?: boolean;
  /** 引文 id。給了才會輪換;沒給就用 PAPERS[0],行為與舊版一致。 */
  seed?: string;
}> = ({ theme, still = false, seed }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const p =
    still || DRIFT === 0
      ? 0
      : interpolate(frame, [0, durationInFrames], [0, 1]);
  const shift = p * -DRIFT;
  const scale = DRIFT === 0 ? 1 : 1.03; // 位移時放大一點,避免露出邊緣

  // texture 為假 → 完全不鋪紙紋(純色底),維持舊行為
  // texture 被明確改成別的檔名 → 尊重指定,不輪換
  // texture 是預設值 → 按 id 輪換
  const src = !theme.texture
    ? null
    : theme.texture !== DEFAULT_TEXTURE
      ? theme.texture
      : seed
        ? pickPaper(seed)
        : PAPERS[0];

  return (
    <AbsoluteFill style={{ backgroundColor: theme.paper }}>
      {src ? (
        <AbsoluteFill
          style={{
            transform: `translate(${shift}px, ${shift * 0.6}px) scale(${scale})`,
          }}
        >
          <Img
            src={staticFile(src)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
            from={-21}
          />
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * 壓印曲線 —— 所有「印上紙」的動作共用同一套物理:
 * 略大 + 微糊 → 收束定位。回傳 CSS 片段。
 *
 *   frame     目前絕對幀
 *   at        這個元素開始壓印的幀
 *   dur       壓印時長(幀),越小越「啪」,越大越「渗」
 *   scaleFrom 起始縮放
 *   blurFrom  起始模糊(px)
 */
export const pressStyle = (
  frame: number,
  at: number,
  dur = 5,
  scaleFrom = 1.035,
  blurFrom = 1.6,
): React.CSSProperties => {
  const p = interpolate(frame, [at, at + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const blur = (1 - p) * blurFrom;
  return {
    opacity: p,
    transform: `scale(${scaleFrom - (scaleFrom - 1) * p})`,
    filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined,
  };
};
