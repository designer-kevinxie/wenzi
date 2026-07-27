/**
 * 文字紀 — design tokens
 * 顏色由成品圖取樣而得,勿隨意改動,這是帳號的視覺簽名。
 */

export const THEME = {
  paper: "#f3ede1", // 紙底
  ink: "#0e5d2d", // 墨綠(正文)
  inkDeep: "#0a462a", // 深墨(標題/落款)
  texture: "paper.jpg",
  logo: "logo.png",
  font: "'Huiwen-mincho', 'Noto Serif TC', serif",
  fontEn: "'Huiwen-mincho', Georgia, serif",
};

export type Theme = typeof THEME;

/**
 * Logo 距離「底部」的比例(不是距離頂部!)
 * 從底部定位,任何畫布比例都不會被切。
 * 影片版留多一點,避開抖音右下的 UI 區。
 */
export const LOGO_BOTTOM = { video: 0.135, still: 0.045 };

export const mergeTheme = (override?: Partial<Theme>): Theme => ({
  ...THEME,
  ...(override ?? {}),
});
