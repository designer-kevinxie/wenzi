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
 *   行數     = 用貪婪換行實際數一遍(不是 ⌈總字數 ÷ 每行字數⌉)
 *   總高     = 行數 × 字級 × 行高
 * 由大而小取第一個放得下的字級。
 */

const LINE_H = 1.52;
const MARGIN_R = 0.085; // 左右留白佔寬度比例(影片與靜圖共用)

/**
 * 版心比例:影片與靜圖**分開**設定。
 *
 * 影片最下方有常駐 logo(theme.ts 的 LOGO_BOTTOM.video = 0.135),
 * 所以底部得留 30% 淨空。靜圖版沒有 logo,只有右下角一行小小的
 * @文字紀(QuoteCard.tsx,距底 4.5%),留 30% 會讓正文整塊被推到上半部、
 * 落款孤零零吊在畫面中間 —— 底下近半張紙是空的。
 *
 * textH  正文可用高度佔畫布比例(調大 → 字變大)
 * bottom 底部保留高度佔畫布比例(調小 → 整塊往下走、字也變大)
 * maxR   字級上限佔寬度比例(短句時才會碰到這個天花板)
 */
const LAYOUT = {
  video: { textH: 0.53, bottom: 0.3, maxR: 0.13 },
  still: { textH: 0.66, bottom: 0.1, maxR: 0.15 },
};

/**
 * 行首禁則(避頭點)—— 這些標點不能出現在行首。
 *
 * 每個字都是獨立的 inline-block,瀏覽器把它們當成互不相干的行內盒子,
 * 於是可以在任意兩個之間斷行,CJK 的禁則處理完全失效。
 * 實際後果:整行以「。」開頭。對一個做印刷質感的帳號,這比字級更傷。
 *
 * 解法是把標點和前一個字綁成一個不可拆的 cluster。
 * 順帶好處:壓印動畫裡標點會跟著它所屬的字一起落下,比單獨蹦出來自然。
 */
const NO_LINE_START = "。，、；：！？）〕】》」』〉·…‧・%℃";

type Cluster = { text: string; at: number }; // at = 首字在原文中的序號,動畫計時用

const clusterize = (text: string): Cluster[] => {
  const out: Cluster[] = [];
  Array.from(text).forEach((c, i) => {
    if (out.length && NO_LINE_START.includes(c)) {
      out[out.length - 1].text += c; // 黏到前一個字上
    } else {
      out.push({ text: c, at: i });
    }
  });
  return out;
};

/**
 * 貪婪換行實際數行數。
 *
 * 不用 ⌈總字數 ÷ 每行字數⌉ —— 那個公式假設可以在任意字之間斷行,
 * 有了 cluster 之後就不成立了:一個 2 字寬的 cluster 塞不進行末剩的 1 格,
 * 整個推到下一行。估少了會溢出版心。
 */
const countLines = (clusters: Cluster[], perLine: number): number => {
  let lines = 1;
  let used = 0;
  for (const c of clusters) {
    const w = c.text.length;
    if (used > 0 && used + w > perLine) {
      lines += 1;
      used = w;
    } else {
      used += w;
    }
  }
  return lines;
};

/**
 * 字級下限有兩道:
 *
 * MIN_R  美觀下限。正常引文不該小於這個,再小就不像「一張可以截圖收藏的卡」了。
 * HARD_R 物理下限。超長引文(3:4 約 125 字以上)連 MIN_R 都裝不下時才會用到。
 *
 * 分兩道的原因:舊版只有一道,而且是無條件 `return min` ——
 * 裝不下也照樣回傳,正文就靜靜地溢出版心、壓到落款上、長到出畫,
 * 全程不報錯。字太小是難看,字被切掉是壞掉,寧可難看。
 */
const MIN_R = 0.055;
const HARD_R = 0.032;

export const autoFontSize = (
  text: string,
  width: number,
  height: number,
  still = false
): number => {
  const L = still ? LAYOUT.still : LAYOUT.video;
  const boxW = width * (1 - MARGIN_R * 2);
  const availH = height * L.textH;
  const tracking = Math.round(width * 0.0028);
  const clusters = clusterize(text.replace(/\s/g, ""));

  const fits = (size: number): boolean => {
    const perLine = Math.floor(boxW / (size + tracking));
    if (perLine < 2) return false; // 一行放不下一個 cluster
    return countLines(clusters, perLine) * size * LINE_H <= availH;
  };

  const max = Math.round(width * L.maxR);
  const min = Math.round(width * MIN_R);
  const hard = Math.round(width * HARD_R);

  for (let size = max; size >= min; size -= 2) {
    if (fits(size)) return size;
  }
  // 走到這裡代表引文超長。繼續縮,至少要讓它完整顯示 —— 步進改 1,
  // 因為這個區間每一級都很珍貴,能大一點是一點。
  for (let size = min - 1; size >= hard; size -= 1) {
    if (fits(size)) return size;
  }
  return hard;
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
  const L = still ? LAYOUT.still : LAYOUT.video;
  const size = autoFontSize(text, width, height, still);
  const tracking = Math.round(width * 0.0028);
  const clusters = clusterize(text);
  const perChar = still ? 0 : 1.6;

  // 計時仍以「字」為單位,不是 cluster —— 動畫節奏和以前完全一致
  const totalChars = Array.from(text).length;
  const attrAt = startFrame + totalChars * perChar + 10;
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
        paddingBottom: height * L.bottom,
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
        {clusters.map((c) => (
          <span
            key={c.at}
            style={{
              display: "inline-block",
              whiteSpace: "nowrap", // cluster 內部絕不斷行 —— 這就是禁則本身
              ...(still
                ? { opacity: 1 }
                : pressStyle(absFrame, startFrame + c.at * perChar, 5)),
            }}
          >
            {c.text}
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
