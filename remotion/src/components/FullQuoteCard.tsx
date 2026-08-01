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
 * 支援橫排與豎排。豎排的數學是橫排的轉置:
 *   橫排 —— 字沿「寬」流動,行沿「高」堆疊
 *   豎排 —— 字沿「高」流動,列沿「寬」堆疊
 * 所以下面用 along(順文字方向)/ across(垂直於文字方向)兩個中性名詞,
 * 一套公式同時服務兩種排法。
 */

const LINE_H = 1.52;
const MARGIN_R = 0.085; // 左右留白佔寬度比例

/**
 * 版心比例:影片 / 靜圖、橫排 / 豎排各一組。
 *
 * 影片最下方有常駐 logo(theme.ts 的 LOGO_BOTTOM.video = 0.135),
 * 所以底部得留 30% 淨空。靜圖版沒有 logo,只有右下角一行小小的
 * @文字紀(QuoteCard.tsx,距底 4.5%),留 30% 會讓正文整塊被推到上半部。
 *
 * along  順文字方向的可用長度佔比(橫排看寬、豎排看高)
 * bottom 底部保留高度佔比。豎排是垂直置中,這個值只用來微調整體位置
 * maxR   字級上限佔寬度比例(短句時才會碰到這個天花板)
 */
const LAYOUT = {
  video: { along: 0.53, bottom: 0.3, maxR: 0.13, marginR: MARGIN_R },
  still: { along: 0.66, bottom: 0.1, maxR: 0.15, marginR: MARGIN_R },
  videoV: { along: 0.62, bottom: 0.18, maxR: 0.13, marginR: MARGIN_R },
  stillV: { along: 0.74, bottom: 0.04, maxR: 0.15, marginR: MARGIN_R },
  // 鎖屏壁紙:頂部要讓開時鐘/日期、底部要讓開手電筒/相機那排圖示,
  // 左右邊距也要加大 —— 手機螢幕不是真的 9:16(新機型接近 9:19.5),
  // 系統會裁掉兩側一截才鋪滿。字多時可以頂到時鐘沒關係,但起始位置
  // 儘量從時鐘下方開始、落款儘量離底部圖示遠一點。
  wallpaper: { along: 0.5, bottom: 0.1, maxR: 0.13, marginR: 0.15 },
  wallpaperV: { along: 0.5, bottom: 0.1, maxR: 0.13, marginR: 0.15 },
};

const layoutOf = (still: boolean, vertical: boolean, wallpaper = false) =>
  wallpaper
    ? vertical
      ? LAYOUT.wallpaperV
      : LAYOUT.wallpaper
    : vertical
      ? still
        ? LAYOUT.stillV
        : LAYOUT.videoV
      : still
        ? LAYOUT.still
        : LAYOUT.video;

/**
 * 行首禁則(避頭點)—— 這些標點不能出現在行首 / 列首。
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
 * 貪婪換行實際數行數(豎排時是列數)。
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
 * HARD_R 物理下限。超長引文連 MIN_R 都裝不下時才會用到。
 *
 * 分兩道的原因:舊版只有一道,而且是無條件 `return min` ——
 * 裝不下也照樣回傳,正文就靜靜地溢出版心、壓到落款上、長到出畫,
 * 全程不報錯。字太小是難看,字被切掉是壞掉,寧可難看。
 */
const MIN_R = 0.055;
const HARD_R = 0.032;

/** 豎排時落款自成一列,要從正文可用寬度裡先扣掉。 */
const attrColumn = (width: number) =>
  Math.round(width * 0.037 * 1.6 + width * 0.03);

export const autoFontSize = (
  text: string,
  width: number,
  height: number,
  still = false,
  vertical = false,
  wallpaper = false,
): number => {
  const L = layoutOf(still, vertical, wallpaper);
  const tracking = Math.round(width * 0.0028);
  const clusters = clusterize(text.replace(/\s/g, ""));

  // along  = 文字流動方向上的可用長度
  // across = 行 / 列堆疊方向上的可用長度
  const along = vertical ? height * L.along : width * (1 - L.marginR * 2);
  const across = vertical
    ? width * (1 - L.marginR * 2) - attrColumn(width)
    : height * L.along;

  const fits = (size: number): boolean => {
    const per = Math.floor(along / (size + tracking));
    if (per < 2) return false; // 一行放不下一個 cluster
    return countLines(clusters, per) * size * LINE_H <= across;
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
  /** 豎排。由 quote json 的 vertical 欄位經 manifest 傳進來。 */
  vertical?: boolean;
  /** 鎖屏壁紙版面(見 LAYOUT.wallpaper / wallpaperV)。 */
  wallpaper?: boolean;
  /**
   * 暗色底(亮字印在深色底上)。multiply 只會把顏色往暗處疊,
   * 淺色字在深底上用 multiply 幾乎看不見,暗色版要換成 screen。
   */
  dark?: boolean;
}> = ({
  text,
  attribution,
  theme,
  startFrame,
  absFrame,
  still = false,
  vertical = false,
  wallpaper = false,
  dark = false,
}) => {
  const { width, height } = useVideoConfig();
  const L = layoutOf(still, vertical, wallpaper);
  const size = autoFontSize(text, width, height, still, vertical, wallpaper);
  const tracking = Math.round(width * 0.0028);
  const clusters = clusterize(text);
  const perChar = still ? 0 : 1.6;

  // 計時仍以「字」為單位,不是 cluster —— 動畫節奏和以前完全一致
  const totalChars = Array.from(text).length;
  const attrAt = startFrame + totalChars * perChar + 10;
  const attrStyle = still ? { opacity: 1 } : pressStyle(absFrame, attrAt, 8);

  const body = clusters.map((c) => (
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
  ));

  const textStyle: React.CSSProperties = {
    fontFamily: theme.font,
    fontSize: size,
    lineHeight: LINE_H,
    letterSpacing: tracking,
    color: theme.ink,
  };

  const attrTextStyle: React.CSSProperties = {
    fontFamily: theme.font,
    fontSize: Math.round(width * 0.037),
    letterSpacing: 2,
    color: theme.inkDeep,
    ...attrStyle,
  };

  if (vertical) {
    return (
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          // row-reverse:第一個 child 在最右邊。豎排由右向左讀,
          // 所以正文在右、落款在左,順序與閱讀方向一致。
          flexDirection: "row-reverse",
          justifyContent: "center",
          alignItems: "center",
          padding: `0 ${width * L.marginR}px`,
          paddingBottom: height * L.bottom,
          mixBlendMode: dark ? "normal" : "multiply",
        }}
      >
        <div
          style={{
            ...textStyle,
            writingMode: "vertical-rl",
            // 明確給高度才會自動折列 —— 少了這行整句會排成一長條衝出畫面
            height: height * L.along,
          }}
        >
          {body}
        </div>
        <div
          style={{
            ...attrTextStyle,
            writingMode: "vertical-rl",
            // 落款貼著正文下緣起排,像線裝書的牌記
            alignSelf: "flex-end",
            marginRight: width * 0.03,
          }}
        >
          {attribution}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: `0 ${width * L.marginR}px`,
        paddingBottom: height * L.bottom,
        mixBlendMode: dark ? "normal" : "multiply",
      }}
    >
      <div style={{ ...textStyle, textAlign: "left" }}>{body}</div>
      <div
        style={{
          ...attrTextStyle,
          marginTop: height * 0.033,
          textAlign: "right",
        }}
      >
        {attribution}
      </div>
    </div>
  );
};
