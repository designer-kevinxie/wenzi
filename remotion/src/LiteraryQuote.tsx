import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { PaperBase } from "./components/PaperBase";
import { TitleStamp } from "./components/TitleStamp";
import { SegmentReveal } from "./components/SegmentReveal";
import { FullQuoteCard } from "./components/FullQuoteCard";
import { LogoStamp } from "./components/LogoStamp";
import { mergeTheme } from "./theme";
import { BgMusic } from "./components/BgMusic";

/**
 * 圖層順序(由下而上):
 *   1. 紙面        —— 永遠存在,當地板。不用 opacity 開關,不可能有透明幀。
 *   2. 鉤子影片    —— 疊在紙上播,播完自動卸載,自然露出紙
 *   3. 內容        —— 書名 / 正文 / 完整句
 *   4. Logo        —— 最上層,全程不被遮
 */
export const LiteraryQuote: React.FC<{ manifest: any }> = ({ manifest }) => {
  const frame = useCurrentFrame();
  const theme = mergeTheme(manifest.theme);
  const { acts, segments, header, audio, hook } = manifest;

  // Logo 與書名同時出現,純淡入不做壓印(書名本身已在壓印,再壓一次會太吵)
  const logoAt = acts.title.from;

  // 鉤子段的短暫露出:0 → 1 秒 20 幀,之後淡出
  const INTRO_LOGO = { from: 0, to: 40 };

  return (
    <AbsoluteFill style={{ backgroundColor: theme.paper }}>
      <PaperBase theme={theme} />

      {hook ? (
        <Sequence from={0} durationInFrames={hook.toFrame}>
          <OffthreadVideo
            src={staticFile(hook.src)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </Sequence>
      ) : null}

      {frame >= acts.body.from - 10 && frame < acts.full.from ? (
        <SegmentReveal segments={segments} theme={theme} absFrame={frame} />
      ) : null}

      {frame >= acts.full.from ? (
        <FullQuoteCard
          text={manifest.fullText}
          attribution={manifest.attribution}
          theme={theme}
          startFrame={acts.full.from}
          absFrame={frame}
        />
      ) : null}

      {/* 書名:壓在鉤子影片尾巴上,鉤子播完後位置不動,銜接無縫 */}
      {frame >= acts.title.from && frame < acts.full.from ? (
        <TitleStamp
          book={header.book}
          author={header.author}
          theme={theme}
          startFrame={acts.title.from}
          absFrame={frame}
        />
      ) : null}

      {/* 鉤子段的 logo */}
      {frame <= INTRO_LOGO.to + 14 ? (
        <LogoStamp
          theme={theme}
          startFrame={INTRO_LOGO.from}
          absFrame={frame}
          fadeOutAt={INTRO_LOGO.to}
          fadeOutDur={12}
        />
      ) : null}

      {/* Logo:與書名同時淡入,之後常駐;最後一幕補墨強調 */}
      {frame >= logoAt ? (
        <LogoStamp
          theme={theme}
          startFrame={logoAt}
          absFrame={frame}
          fadeIn
          emphasizeAt={acts.full.from + 40}
        />
      ) : null}

      <Sequence from={audio.title.startFrame}>
        <Audio src={staticFile(audio.title.src)} />
      </Sequence>
      <Sequence from={audio.body.startFrame}>
        <Audio src={staticFile(audio.body.src)} />
      </Sequence>
      {manifest.music ? (
        <BgMusic src={manifest.music} fullFrom={acts.full.from} />
      ) : null}
    </AbsoluteFill>
  );
};
