/**
 * 文字紀 — Sheet 佇列 Web App
 *
 * 部署:Apps Script 編輯器 → 右上「部署」→「新增部署作業」→
 *   類型選「網頁應用程式」,執行身分「我」,存取權「任何人」→ 部署,
 *   複製產生的網址(https://script.google.com/macros/s/XXXX/exec)給 batch.py。
 *
 * 表格欄位(第一列為標題):
 *   A text | B author | C book | D status | E note
 *   status 空白 = 待做,processing = 生成中,done = 完成,error = 出錯
 *
 * 安全:網址帶一個 token,batch.py 要附上同一個 token 才能讀寫。
 *   把下面 TOKEN 改成你自己的隨機字串,別外流。
 */

const TOKEN = "換成你自己的隨機字串-8f3a";
const SHEET_NAME = "Sheet1"; // 若你的分頁名稱不同請改

function doGet(e) {
  if ((e.parameter.token || "") !== TOKEN) return _json({ error: "bad token" });
  const rows = _pending();
  return _json({ pending: rows });
}

function doPost(e) {
  const body = JSON.parse(e.postData.contents || "{}");
  if ((body.token || "") !== TOKEN) return _json({ error: "bad token" });

  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  // body.updates = [{row: 3, status: "done", note: "..."}, ...]
  (body.updates || []).forEach((u) => {
    if (u.status !== undefined) sheet.getRange(u.row, 4).setValue(u.status);
    if (u.note !== undefined) sheet.getRange(u.row, 5).setValue(u.note);
  });
  return _json({ ok: true, updated: (body.updates || []).length });
}

function _pending() {
  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  const out = [];
  for (let i = 1; i < data.length; i++) {
    const [text, author, book, status] = data[i];
    if (String(text).trim() && !String(status).trim()) {
      out.push({
        row: i + 1, // 1-indexed，含標題列
        text: String(text).trim(),
        author: String(author || "").trim(),
        book: String(book || "").trim(),
      });
    }
  }
  return out;
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(
    ContentService.MimeType.JSON,
  );
}
