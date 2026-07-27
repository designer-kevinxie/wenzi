import { staticFile } from "remotion";

/**
 * 本機系統字體在雲端渲染會 fallback,所以一律從 public/fonts/ 載入。
 * 把字體檔複製到 remotion/public/fonts/ 並改成實際檔名。
 */
const face = new FontFace(
  "Huiwen-mincho",
  `url(${staticFile("fonts/Huiwenmincho-improved.otf")})`,
);
face
  .load()
  .then((f) => document.fonts.add(f))
  .catch(() => {
    console.warn("字體載入失敗,將 fallback 到系統襯線體");
  });
