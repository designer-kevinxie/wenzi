import { AbsoluteFill, Img, staticFile } from "remotion";
import { FullQuoteCard } from "./components/FullQuoteCard";
import { mergeTheme } from "./theme";

/**
 * 鎖屏壁紙版 —— 暗色。
 *
 * 背景是純色(#00442C)疊一層紙紋顆粒,不是走 PaperBase 那條路 ——
 * PaperBase 的紙紋是不透明整張蓋上去,色號會被紙紋本身的米色蓋掉。
 * 這裡把紙紋去色、調高對比,再用低透明度疊上去(只借它的顆粒明暗,
 * 不借它的顏色),色號才能保持接近 #00442C,同時還有一點紙感。
 *
 * 文字直接給一套米黃色的 ink,跟背景色各自獨立設定。
 * 背景變暗了,FullQuoteCard 原本的 mixBlendMode:multiply(淺紙上疊
 * 暗墨)會讓淺色字在暗底上幾乎隱形,所以這裡要傳 dark,換成一般疊色。
 *
 * 排版走 FullQuoteCard 的 wallpaper 檔位(見該檔 LAYOUT.wallpaper /
 * wallpaperV):邊距比一般靜圖大,因為手機螢幕不是真的 9:16,系統鋪滿
 * 鎖屏時會裁掉兩側一截;頂部也讓開時鐘/日期的位置。
 */
const BG_COLOR = "#003D1A";

export const Wallpaper: React.FC<{ manifest: any }> = ({ manifest }) => {
  const theme = mergeTheme(manifest.theme);
  const inkTheme = { ...theme, ink: "#f3ead2", inkDeep: "#f8f1de" };
  const handle = manifest.branding?.handle || "@文字紀";

  return (
    <AbsoluteFill style={{ backgroundColor: BG_COLOR }}>
      <Img
        src={staticFile("paper.jpg")}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: 0.5,
          mixBlendMode: "color-burn",
          filter: "grayscale(1) contrast(1)",
        }}
      />
      <FullQuoteCard
        text={manifest.fullText}
        attribution={manifest.attribution}
        theme={inkTheme}
        startFrame={0}
        absFrame={0}
        still
        vertical={manifest.vertical}
        wallpaper
        dark
      />
      <div
        style={{
          position: "absolute",
          right: "17%",
          bottom: "17%",
          fontFamily: theme.font,
          fontSize: 30,
          letterSpacing: 2,
          color: inkTheme.ink,
          opacity: 0.55,
        }}
      >
        {handle}
      </div>
    </AbsoluteFill>
  );
};
