import { interpolate, useCurrentFrame } from "remotion";
import { Theme } from "../theme";
import { pressStyle } from "./PaperBase";

export type Segment = {
  zh: string;
  en: string;
  fromFrame: number;
  toFrame: number;
  words: { text: string; startFrame: number }[];
};

/**
 * 正文 —— 逐段替換(不累積)。
 * 中文逐字壓印,段末停頓後整段淡出 6 幀,下一段壓入。
 */

/**
 * 英譯是否上畫面。
 *
 * 關掉了,但 quote json 與 manifest 裡的 en 欄位**照常生成、照常保留** ——
 * 英譯和分段是同一次模型呼叫的產物,關掉顯示一分錢也省不了,
 * 而留著資料代表以後要做英文帳號時,存量引文不必重跑。
 *
 * 要開回來就把這裡改成 true,排版與淡入時序都原封不動。
 */
const SHOW_EN = false;

export const SegmentReveal: React.FC<{
  segments: Segment[];
  theme: Theme;
  absFrame: number;
}> = ({ segments, theme, absFrame }) => {
  return (
    <>
      {segments.map((seg, si) => {
        const fadeOutAt = seg.toFrame - 6;
        // 嚴格窗口:上一段淡出結束的那一幀,正好是下一段第一個字出現的時刻,
        // 所以任何時候畫面上都只有一段。
        const alive = absFrame >= seg.fromFrame && absFrame < seg.toFrame;
        if (!alive) return null;

        const segOpacity = interpolate(
          absFrame,
          [fadeOutAt, seg.toFrame],
          [1, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );
        const enAt = (seg.words.at(-1)?.startFrame ?? seg.fromFrame) - 6;

        return (
          <div
            key={si}
            style={{
              position: "absolute",
              top: 780,
              left: 0,
              right: 0,
              padding: "0 92px",
              opacity: segOpacity,
              mixBlendMode: "multiply",
            }}
          >
            <div
              style={{
                fontFamily: theme.font,
                fontSize: 82,
                lineHeight: 1.5,
                letterSpacing: 2,
                color: theme.ink,
              }}
            >
              {seg.words.map((w, i) => (
                <span
                  key={i}
                  style={{
                    display: "inline-block",
                    ...pressStyle(absFrame, w.startFrame),
                  }}
                >
                  {w.text}
                </span>
              ))}
            </div>

            {SHOW_EN && seg.en ? (
              <div
                style={{
                  fontFamily: theme.fontEn,
                  fontSize: 46,
                  lineHeight: 1.45,
                  letterSpacing: 1,
                  color: theme.ink,
                  opacity:
                    0.75 *
                    interpolate(absFrame, [enAt, enAt + 12], [0, 1], {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                    }),
                  marginTop: 10,
                }}
              >
                {seg.en}
              </div>
            ) : null}
          </div>
        );
      })}
    </>
  );
};
