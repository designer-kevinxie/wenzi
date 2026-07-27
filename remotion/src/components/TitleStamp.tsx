import { interpolate, useCurrentFrame } from "remotion";
import { Theme } from "../theme";
import { pressStyle } from "./PaperBase";

/**
 * 書名鈐印 —— 兩拍:
 *   1. 書名逐字壓印(每字間隔 3 幀,快而有節奏)
 *   2. 停 0.4s 後,作者名整體壓上(不逐字,一次落定)
 *
 * 印完就留在原地成為常駐頁眉 —— 不位移,像翻開書之後書眉一直在那裡。
 */
export const TitleStamp: React.FC<{
  book: string;
  author: string;
  theme: Theme;
  startFrame: number;   // 這一幕的絕對起始幀
  absFrame: number;     // 目前絕對幀
}> = ({ book, author, theme, startFrame, absFrame }) => {
  const chars = book ? Array.from(`《${book}》`) : [];
  const perChar = 3;
  const bookDone = startFrame + chars.length * perChar + 5;
  const authorAt = bookDone + 12; // 停 0.4s

  return (
    <div
      style={{
        position: "absolute",
        top: 380,
        width: "100%",
        textAlign: "center",
        mixBlendMode: "multiply",
        fontFamily: theme.font,
        color: theme.inkDeep,
      }}
    >
      {chars.length ? (
        <div style={{ fontSize: 76, letterSpacing: 6, lineHeight: 1.4 }}>
          {chars.map((c, i) => (
            <span
              key={i}
              style={{
                display: "inline-block",
                ...pressStyle(absFrame, startFrame + i * perChar),
              }}
            >
              {c}
            </span>
          ))}
        </div>
      ) : null}

      <div
        style={{
          fontSize: chars.length ? 50 : 76,
          letterSpacing: 4,
          marginTop: chars.length ? 18 : 0,
          ...pressStyle(absFrame, chars.length ? authorAt : startFrame, 6),
        }}
      >
        {author}
      </div>
    </div>
  );
};
