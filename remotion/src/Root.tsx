import { Composition, Still } from "remotion";
import { LiteraryQuote } from "./LiteraryQuote";
import { QuoteCard } from "./QuoteCard";
import manifest from "../public/manifest.json";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="LiteraryQuote"
        component={LiteraryQuote}
        durationInFrames={manifest.durationInFrames}
        fps={manifest.fps}
        width={1080}
        height={1920}
        defaultProps={{ manifest }}
      />
      {/* 小紅書 3:4 卡片 */}
      <Still
        id="QuoteCard"
        component={QuoteCard}
        width={1080}
        height={1440}
        defaultProps={{ manifest }}
      />
      {/* 直式 9:16 卡片(同影片比例) */}
      <Still
        id="QuoteCardTall"
        component={QuoteCard}
        width={1080}
        height={1920}
        defaultProps={{ manifest }}
      />
    </>
  );
};
