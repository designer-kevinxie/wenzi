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
 * 紙面 —— 直接使用 paper.jpg 原圖,不做任何調色。
 *
 * 若 paper.jpg 是從 hook.mp4 抽的最後一幀,這裡必須零加工,
 * 否則和鉤子影片接在一起會有色差,硬切的接縫就會被看出來。
 *
 * 唯一保留的處理:極慢的位移(全片約 10px),
 * 用來避開平台對「完全靜止畫面」的低質判定。
 * 不想要的話把 DRIFT 設成 0。
 */

const DRIFT = 0; // px,全片位移總量;設 0 則完全靜止

export const PaperBase: React.FC<{ theme: Theme; still?: boolean }> = ({
  theme,
  still = false,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const p =
    still || DRIFT === 0
      ? 0
      : interpolate(frame, [0, durationInFrames], [0, 1]);
  const shift = p * -DRIFT;
  const scale = DRIFT === 0 ? 1 : 1.03; // 位移時放大一點,避免露出邊緣

  return (
    <AbsoluteFill style={{ backgroundColor: theme.paper }}>
      {theme.texture ? (
        <AbsoluteFill
          style={{
            transform: `translate(${shift}px, ${shift * 0.6}px) scale(${scale})`,
          }}
        >
          <Img
            src={staticFile(theme.texture)}
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
