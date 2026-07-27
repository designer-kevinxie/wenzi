import { Audio, staticFile } from "remotion";

/**
 * 背景音樂 —— 固定輕音量,全程墊在旁白底下。
 * 0.12 幾乎聽不見但拿掉會覺得空;覺得糊住旁白就降到 0.09。
 */
export const BgMusic: React.FC<{ src: string; fullFrom?: number }> = ({
  src,
}) => {
  return <Audio src={staticFile(src)} volume={2} loop />;
};
