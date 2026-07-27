import { AbsoluteFill } from "remotion";
import { PaperBase } from "./components/PaperBase";
import { FullQuoteCard } from "./components/FullQuoteCard";
import { mergeTheme } from "./theme";

/**
 * 靜圖版 —— 不是從影片抽一幀,而是獨立 composition。
 * 好處:可以有自己的尺寸(小紅書 3:4、IG 4:5),純向量重排,零畫質損失。
 *
 * 與影片版的差別:不放圓形 logo(那個在截圖用的卡片上太重),
 * 改成右下角一行小小的 @文字紀 署名,克制得像書的版權頁。
 */
export const QuoteCard: React.FC<{ manifest: any }> = ({ manifest }) => {
  const theme = mergeTheme(manifest.theme);
  const handle = manifest.branding?.handle || "@文字紀-小红书";

  return (
    <AbsoluteFill>
      <PaperBase theme={theme} still />
      <FullQuoteCard
        text={manifest.fullText}
        attribution={manifest.attribution}
        theme={theme}
        startFrame={0}
        absFrame={0}
        still
      />
      <div
        style={{
          position: "absolute",
          right: "6%",
          bottom: "4.5%",
          fontFamily: theme.font,
          fontSize: 30,
          letterSpacing: 2,
          color: theme.ink,
          opacity: 0.55,
          mixBlendMode: "multiply",
        }}
      >
        {handle}
      </div>
    </AbsoluteFill>
  );
};
