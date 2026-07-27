import { Img, interpolate, staticFile, useVideoConfig } from "remotion";
import { LOGO_BOTTOM, Theme } from "../theme";

/**
 * Logo —— 兩種出場方式:
 *
 *   stamp (預設)  鈐印:略大 + 微糊 → 收束定位 + 紙的回彈,像手蓋的印章
 *   fadeIn        單純淡入,不縮放不模糊 —— 用在跟書名一起出現的那一次,
 *                 因為書名本身已經在做壓印動畫,logo 再壓一次會太吵
 *
 * 三個關鍵細節(鈐印模式):
 *   1. multiply 混合 → 吃到紙紋,和文字同一個世界
 *   2. ±1.5° 微旋轉 → 「手蓋」與「貼圖」的分界線
 *   3. 落定後極小回彈 → 印章抬起時紙的回彈
 */

export const LogoStamp: React.FC<{
  theme: Theme;
  startFrame: number;
  absFrame: number;
  fadeIn?: boolean; // true = 純淡入,不做壓印動畫
  fadeInDur?: number; // 淡入時長(幀),預設 14 ≈ 0.47s
  emphasizeAt?: number; // 最後一幕補墨強調
  fadeOutAt?: number; // 到這一幀開始淡出
  fadeOutDur?: number;
  blend?: "multiply" | "normal"; // 深色底要改 normal 才看得到
  still?: boolean;
  seed?: number;
}> = ({
  theme,
  startFrame,
  absFrame,
  fadeIn = false,
  fadeInDur = 14,
  emphasizeAt,
  fadeOutAt,
  fadeOutDur = 10,
  blend = "multiply",
  still = false,
  seed = 0.42,
}) => {
  const tilt = (seed * 2 - 1) * 1.5;
  const bottomRatio = still ? LOGO_BOTTOM.still : LOGO_BOTTOM.video;
  // 元件開頭加上
  const { width } = useVideoConfig();

  // 出場進度
  const p = still
    ? 1
    : interpolate(
        absFrame,
        [startFrame, startFrame + (fadeIn ? fadeInDur : 7)],
        [0, 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
      );

  // 抬起時紙的回彈(僅鈐印模式)
  const rebound =
    still || fadeIn
      ? 1
      : interpolate(
          absFrame,
          [startFrame + 7, startFrame + 11, startFrame + 16],
          [1, 0.995, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        );

  // 最後一幕補墨(不重蓋)
  const emph =
    !still && emphasizeAt !== undefined
      ? interpolate(
          absFrame,
          [emphasizeAt, emphasizeAt + 8, emphasizeAt + 20],
          [0, 1, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        )
      : 0;

  const out =
    fadeOutAt !== undefined
      ? interpolate(absFrame, [fadeOutAt, fadeOutAt + fadeOutDur], [1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 1;

  // 淡入模式:不縮放、不模糊,只有補墨那 2% 起伏
  const scale = fadeIn
    ? 1 + emph * 0.02
    : (1.18 - 0.18 * p) * rebound * (1 + emph * 0.02);
  const blur = fadeIn ? 0 : (1 - p) * 2.5;

  return (
    <div
      style={{
        position: "absolute",
        bottom: `${bottomRatio * 100}%`, // 從底部定位,任何比例都不會被切
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        mixBlendMode: blend,
        opacity: p * (0.92 + emph * 0.08) * out,
      }}
    >
      <Img
        src={staticFile(theme.logo)}
        style={{
          width: width * 0.155, // 1080 → 167px
          transform: `scale(${scale}) rotate(${tilt}deg)`,
          filter: blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : undefined,
        }}
      />
    </div>
  );
};
