import { useVideoConfig } from "remotion";
import { Theme } from "../theme";
import { pressStyle } from "./PaperBase";

/**
 * 完整句版 —— 給人截圖收藏的一幕,也是靜圖輸出的畫面。
 * 這一幕刻意撤掉頂部書名頁眉與英文:底部已有落款,乾淨最重要。
 *
 * 所有尺寸都按畫布比例計算,所以 9:16 影片和 3:4 卡片共用同一個組件,
 * 各自重新排版(不是把 9:16 裁一刀)。
 *
 * 字級自動計算(中文全形等寬,可精確推算,不需 DOM 量測):
 *   每行字數 = 框寬 ÷ (字級 + 字距)
 *   行數     = ⌈總字數 ÷ 每行字數⌉
 *   總高     = 行數 × 字級 × 行高
 * 由大而小取第一個放得下的字級。
 */

const LINE_H = 1.52;
const MARGIN_R = 0.085;   // 左右留白佔寬度比例
const TEXT_H_R = 0.53;    // 正文可用高度佔畫布比例
const BOTTOM_R = 0.30;    // 底部保留給落款 + logo

export const autoFontSize = (
  text: string,
  width: number,
  height: number
): number => {
  const boxW = width * (1 - MARGIN_R * 2);
  const availH = height * TEXT_H_R;
  const tracking = Math.round(width * 0.0028);
  const n = Array.from(text.replace(/\s/g, "")).length;
  const max = Math.round(width * 0.13);
  const min = Math.round(width * 0.055);

  for (let size = max; size >= min; size -= 2) {
    const perLine = Math.floor(boxW / (size + tracking));
    if (perLine < 1) continue;
    const lines = Math.ceil(n / perLine);
    if (lines * size * LINE_H <= availH) return size;
  }
  return min;
};

export const FullQuoteCard: React.FC<{
  text: string;
  attribution: string;
  theme: Theme;
  startFrame: number;
  absFrame: number;
  still?: boolean;
}> = ({ text, attribution, theme, startFrame, absFrame, still = false }) => {
  const { width, height } = useVideoConfig();
  const size = autoFontSize(text, width, height);
  const tracking = Math.round(width * 0.0028);
  const chars = Array.from(text);
  const perChar = still ? 0 : 1.6;

  const attrAt = startFrame + chars.length * perChar + 10;
  const attrStyle = still ? { opacity: 1 } : pressStyle(absFrame, attrAt, 8);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: `0 ${width * MARGIN_R}px`,
        paddingBottom: height * BOTTOM_R,
        mixBlendMode: "multiply",
      }}
    >
      <div
        style={{
          fontFamily: theme.font,
          fontSize: size,
          lineHeight: LINE_H,
          letterSpacing: tracking,
          color: theme.ink,
          textAlign: "left",
        }}
      >
        {chars.map((c, i) => (
          <span
            key={i}
            style={{
              display: "inline-block",
              ...(still
                ? { opacity: 1 }
                : pressStyle(absFrame, startFrame + i * perChar, 5)),
            }}
          >
            {c}
          </span>
        ))}
      </div>

      <div
        style={{
          marginTop: height * 0.033,
          textAlign: "right",
          fontFamily: theme.font,
          fontSize: Math.round(width * 0.037),
          letterSpacing: 2,
          color: theme.inkDeep,
          ...attrStyle,
        }}
      >
        {attribution}
      </div>
    </div>
  );
};
