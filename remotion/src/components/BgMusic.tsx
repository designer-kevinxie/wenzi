import { Audio, staticFile } from "remotion";

/**
 * 背景音樂 —— 固定輕音量,全程墊在旁白底下。
 *
 */
export const BgMusic: React.FC<{ src: string; fullFrom?: number }> = ({
  src,
}) => {
  return <Audio src={staticFile(src)} volume={0.5} loop />;
};
