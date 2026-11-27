"""Mail đã gửi cho học viên Milo (hộp mail chung VH) → hiện trong tab "TK Milo", CTV xem và sao chép ảnh chụp mail.

Apps Script chạy bằng CHÍNH tài khoản mail chung, đọc thư mục Đã gửi và đẩy mail sang /api/milo/mail:
  - mail mới: mỗi lần chạy tìm mail gửi sau mốc trước, chỉ gửi mail chưa gửi (không có mail mới → không ghi DB)
  - lịch sử cũ: gửi dần từng trang tới hết
Lưu bảng milo_mails (nội dung nén zlib+base64). Trong bộ nhớ chỉ giữ danh mục (id, lúc gửi, người nhận, tiêu đề)
để tra theo email không phải hỏi DB; nội dung mail chỉ đọc DB khi CTV bấm xem.
Ảnh dán trong mail (cid:) được Apps Script thay bằng data URI (≤ 300KB / ảnh) để ảnh chụp đủ như mail thật.
"""
import base64
import json
import re
import secrets
import threading
import time
import zlib
from datetime import datetime

from . import db

_lock = threading.Lock()
_st = {"index": None, "token": None, "seen": None, "at": None}
FORMAT = 1
HTML_MAX = 3_000_000  # ký tự / mail (đã gồm ảnh dán trong mail)
# chỉ nhận / giữ mail thông báo khoá Milo: tiêu đề kiểu "[Speakwell - MILO] - THÔNG BÁO KHÓA HỌC MỚI - Học viên …"
SUBJECT_RE = re.compile(r"speakwell\W*milo", re.I)
SUBJECT_SQL = "lower(subject) LIKE '%speakwell%milo%'"


class MailError(Exception):
    pass


def token(con=None) -> str:
    if _st["token"] is None:
        own = con is None
        con = con or db.connect()
        try:
            _st["token"] = db.get_setting(con, "milo_mail_token") or ""
        finally:
            if own:
                con.close()
    return _st["token"]


def ensure_token(con) -> str:
    tok = token(con)
    if not tok:
        tok = secrets.token_urlsafe(18)
        db.set_setting(con, "milo_mail_token", tok)
        _st["token"] = tok
    return tok


ADDR = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")


def addrs(*fields) -> list[str]:
    return sorted({a.lower() for f in fields for a in ADDR.findall(str(f or ""))})


def _pack(o) -> str:
    return base64.b64encode(zlib.compress(json.dumps(o, ensure_ascii=False).encode("utf-8"), 6)).decode()


def _unpack(s: str):
    return json.loads(zlib.decompress(base64.b64decode(s)).decode("utf-8"))


def clean_html(h: str) -> str:
    """Mail hiển thị trong iframe sandbox không cho chạy script; vẫn bỏ script / handler cho chắc."""
    h = re.sub(r"(?is)<script\b.*?</script\s*>", "", h)
    h = re.sub(r"(?is)</?(script|iframe|frame|frameset|object|embed|form)\b[^>]*>", "", h)
    h = re.sub(r"(?i)<meta\b[^>]*http-equiv[^>]*>", "", h)
    h = re.sub(r"""(?i)\s+on[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", "", h)
    h = re.sub(r"""(?i)(href|src)\s*=\s*(["']?)\s*javascript:""", r"\1=\2#", h)
    return h


def _fmt(at: int) -> str:
    return datetime.fromtimestamp(at).strftime("%Y-%m-%d %H:%M:%S")


def _meta(mid, at, ads, sender, subject) -> dict:
    return {"id": mid, "at": int(at), "addrs": ads, "from": sender or "", "subject": subject or ""}


def _index() -> dict:
    """{"items": {id: meta}, "by": {email: set(id)}} — nạp 1 lần từ DB sau khi server khởi động."""
    if _st["index"] is None:
        con = db.connect()
        try:
            # mail khác lọt vào trước khi có bộ lọc tiêu đề → xoá 1 lần lúc nạp
            con.execute(f"DELETE FROM milo_mails WHERE NOT ({SUBJECT_SQL})")
            con.commit()
            rs = con.execute("SELECT id, at, addrs, sender, subject FROM milo_mails").fetchall()
        finally:
            con.close()
        idx = {"items": {}, "by": {}}
        for r in rs:
            _add(idx, _meta(r[0], r[1], [a for a in str(r[2]).split(",") if a], r[3], r[4]))
        with _lock:
            if _st["index"] is None:
                _st["index"] = idx
    return _st["index"]


def _add(idx, m):
    old = idx["items"].get(m["id"])
    if old:
        for a in old["addrs"]:
            idx["by"].get(a, set()).discard(m["id"])
    idx["items"][m["id"]] = m
    for a in m["addrs"]:
        idx["by"].setdefault(a, set()).add(m["id"])


def receive(body: dict) -> dict:
    """Apps Script gọi vào, body.op:
      ping  → chỉ báo còn chạy (không chạm DB)
      reset → xoá toàn bộ mail đã lưu (chạy lại miloMailSetup)
      push  → {mails: [{id, at, from, to, cc, bcc, subject, html, atts}]}"""
    tok = token()
    if not tok or body.get("token") != tok:
        raise MailError("Sai mã bảo mật")
    op = body.get("op")
    _st["seen"] = time.time()
    if op == "ping":
        return {"ok": True}
    if body.get("v") != FORMAT:
        raise MailError("Code Apps Script đã cũ — sao chép lại code mới ở trang Quản trị → Document → TK Milo")
    if op == "reset":
        con = db.connect()
        try:
            con.execute("DELETE FROM milo_mails")
            con.commit()
        finally:
            con.close()
        with _lock:
            _st["index"] = {"items": {}, "by": {}}
        return {"ok": True}
    if op != "push":
        raise MailError("Thao tác không hợp lệ")
    idx = _index()
    rows, metas = [], []
    for m in body.get("mails") or []:
        try:
            mid, at = str(m["id"]).strip(), int(m["at"])
        except (KeyError, TypeError, ValueError):
            raise MailError("Dữ liệu mail không hợp lệ")
        ads = addrs(m.get("to"), m.get("cc"), m.get("bcc"))
        if not mid or not ads or not SUBJECT_RE.search(str(m.get("subject") or "")):
            continue
        html = str(m.get("html") or "")[:HTML_MAX]
        atts = [a for a in (m.get("atts") or []) if isinstance(a, dict)]
        full = {"from": str(m.get("from") or ""), "to": str(m.get("to") or ""), "cc": str(m.get("cc") or ""),
                "subject": str(m.get("subject") or ""), "html": html, "atts": atts}
        meta = _meta(mid, at, ads, full["from"], full["subject"])
        rows.append((mid, at, "," + ",".join(ads) + ",", meta["from"][:500], meta["subject"][:500], _pack(full)))
        metas.append(meta)
    if rows:
        con = db.connect()
        try:
            con.executemany("INSERT OR REPLACE INTO milo_mails(id, at, addrs, sender, subject, body) VALUES (?,?,?,?,?,?)", rows)
            con.commit()
        finally:
            con.close()
        with _lock:
            for meta in metas:
                _add(idx, meta)
        _st["at"] = time.time()
    return {"ok": True, "saved": len(rows), "count": len(idx["items"])}


def for_emails(emails, limit: int = 30) -> list[dict]:
    """Danh sách mail đã gửi tới các email này (mới nhất trước) — chỉ danh mục, chưa có nội dung."""
    try:
        idx = _index()
    except Exception:  # noqa: BLE001  — bảng chưa có / DB lỗi: tab vẫn tra cứu được phần sheet
        return []
    ids = set()
    for e in emails:
        ids |= idx["by"].get(str(e or "").strip().lower(), set())
    ms = sorted((idx["items"][i] for i in ids if i in idx["items"]), key=lambda m: -m["at"])[:limit]
    return [{"id": m["id"], "at": _fmt(m["at"]), "from": m["from"], "subject": m["subject"]} for m in ms]


def get(mid: str) -> dict | None:
    con = db.connect()
    try:
        r = con.execute("SELECT id, at, body FROM milo_mails WHERE id=?", (mid,)).fetchone()
    finally:
        con.close()
    if not r:
        return None
    full = _unpack(r[2])
    full["html"] = clean_html(full.get("html") or "")
    atts = []
    for a in full.get("atts") or []:
        t = str(a.get("type") or "")
        atts.append({"name": str(a.get("name") or ""), "type": t, "size": int(a.get("size") or 0),
                     "data": str(a["data"]) if a.get("data") and t.startswith("image/") else ""})
    full["atts"] = atts
    return {"id": r[0], "at": _fmt(int(r[1])), **full}


def status() -> dict:
    try:
        items = _index()["items"]
        n = len(items)
        oldest = min((m["at"] for m in items.values()), default=None)
    except Exception:  # noqa: BLE001
        n = oldest = None
    return {"count": n, "seen_at": _st["seen"], "data_at": _st["at"], "oldest": _fmt(oldest) if oldest else None}


APPS_SCRIPT = r"""// Cổng CTV ← mail đã gửi cho học viên Milo. Chạy bằng CHÍNH tài khoản mail chung (hộp mail gửi TK cho học viên).
// Cài: đăng nhập Google bằng tài khoản mail chung → script.google.com → Dự án mới → xoá code mẫu, dán code này → 💾 Lưu
//      → ô chọn hàm chọn "miloMailSetup" → ▶ Chạy → Xem xét quyền → chọn tài khoản mail chung → Cho phép.
// Đọc thư mục "Đã gửi": mail mới gửi ngay ở lần chạy kế tiếp, lịch sử cũ gửi dần (mỗi lần chạy tối đa ~4 phút, chưa xong lần sau làm tiếp).
// Kiểm tra 2 phút/lần trong giờ làm (7h–23h), 15 phút/lần ban đêm. Không có mail mới thì không gửi gì.
// Ảnh dán trong mail ≤ 300KB được gửi kèm để CTV chụp lại đủ như mail thật.
const MM_PORTAL = '__PORTAL__/api/milo/mail';
const MM_TOKEN = '__TOKEN__';
const MM_FILTER = 'subject:"Speakwell - MILO"';   // chỉ lấy mail có tiêu đề chứa [Speakwell - MILO] (portal cũng chỉ nhận mail này)
const MM_SINCE = '';    // chỉ lấy lịch sử từ ngày này, VD: '2024/01/01' (để trống = toàn bộ)
const MM_PAGE = 30, MM_BATCH_CHARS = 4 * 1024 * 1024, MM_BUDGET_MS = 4 * 60 * 1000, MM_IMG_MAX = 300 * 1024;
const MM_EVERY_DAY_MIN = 2, MM_EVERY_NIGHT_MIN = 15, MM_DAY_FROM = 7, MM_DAY_TO = 23;

// Chạy 1 lần (chạy lại = xoá mail đã lưu trên portal và gửi lại toàn bộ)
function miloMailSetup() {
  miloMailTriggers();
  const p = PropertiesService.getScriptProperties(), now = Math.floor(Date.now() / 1000);
  p.setProperties({ mm_new: String(now), mm_old: String(now), mm_start: '0', mm_done: '', mm_ids: '{}', mm_last: '0' });
  mmPost_({ op: 'reset' });
  miloMailSync();
}

// Chỉ đặt lại lịch chạy, không gửi lại lịch sử
function miloMailTriggers() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'miloMailSync').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('miloMailSync').timeBased().everyMinutes(1).create();  // thức mỗi phút, tự bỏ qua nếu chưa tới lượt
}

function mmPost_(body) {
  body.token = MM_TOKEN;
  body.v = 1;
  const res = UrlFetchApp.fetch(MM_PORTAL, { method: 'post', contentType: 'application/json', payload: JSON.stringify(body), muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) throw new Error('Portal báo lỗi ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 300));
  return JSON.parse(res.getContentText());
}

function mmMe_() {
  return [Session.getEffectiveUser().getEmail()].concat(GmailApp.getAliases()).map(s => String(s || '').toLowerCase()).filter(String);
}

function mmFromMe_(m, me) {
  const f = String(m.getFrom()).toLowerCase();
  return me.some(a => f.indexOf(a) >= 0);
}

function mmImg_(a) {
  return a && /^image\//.test(a.getContentType()) && a.getSize() <= MM_IMG_MAX;
}

function mmPack_(m) {
  let html = m.getBody() || '';
  const files = m.getAttachments({ includeInlineImages: false, includeAttachments: true });
  const all = m.getAttachments({ includeInlineImages: true, includeAttachments: true });
  const left = {};
  files.forEach(a => { const k = a.getName() + '|' + a.getSize(); left[k] = (left[k] || 0) + 1; });
  const inline = all.filter(a => { const k = a.getName() + '|' + a.getSize(); if (left[k]) { left[k]--; return false; } return true; });
  // ảnh dán trong mail (src="cid:…"): Gmail không cho biết cid của từng ảnh → ghép theo thứ tự xuất hiện
  const cids = [];
  html.replace(/src\s*=\s*["']?cid:([^"'\s>]+)/gi, (s, c) => { if (cids.indexOf(c) < 0) cids.push(c); return s; });
  cids.forEach((c, i) => {
    const a = inline[i];
    const src = mmImg_(a) ? 'data:' + a.getContentType() + ';base64,' + Utilities.base64Encode(a.getBytes()) : '';
    html = html.split('cid:' + c).join(src);
  });
  const atts = files.map(a => {
    const o = { name: a.getName(), type: a.getContentType(), size: a.getSize() };
    if (mmImg_(a)) o.data = Utilities.base64Encode(a.getBytes());
    return o;
  });
  return { id: m.getId(), at: Math.floor(m.getDate().getTime() / 1000), from: m.getFrom(), to: m.getTo(), cc: m.getCc(),
           bcc: m.getBcc(), subject: m.getSubject(), html: html, atts: atts };
}

// Kiểm tra 1 email (khi CTV báo có mail mà portal không thấy): điền email vào MM_CHECK_EMAIL → 💾 Lưu → chọn hàm
// miloMailCheck → ▶ Chạy. Nhật ký ghi từng mail tìm được + tiến độ gửi lịch sử; mail tìm được gửi luôn sang portal.
const MM_CHECK_EMAIL = '';
function miloMailCheck() {
  const email = String(MM_CHECK_EMAIL).trim().toLowerCase();
  if (!email) throw new Error('Điền email học viên vào dòng MM_CHECK_EMAIL = \'\' rồi chạy lại');
  const p = PropertiesService.getScriptProperties(), me = mmMe_();
  Logger.log('Tài khoản đang chạy + bí danh: ' + me.join(', '));
  Logger.log('Lịch sử: ' + (p.getProperty('mm_done') ? 'đã gửi xong' : 'đang gửi — đã qua ' + (p.getProperty('mm_start') || 0) + ' cuộc thư')
             + ' · mail mới tính từ ' + new Date(Number(p.getProperty('mm_new') || 0) * 1000));
  const out = [];
  GmailApp.search(['in:sent', MM_FILTER, email].filter(String).join(' '), 0, 20).forEach(t => t.getMessages().forEach(m => {
    const rcpt = [m.getTo(), m.getCc(), m.getBcc()].join(',').toLowerCase();
    if (rcpt.indexOf(email) < 0) return;
    Logger.log(Utilities.formatDate(m.getDate(), 'Asia/Ho_Chi_Minh', 'dd/MM/yyyy HH:mm') + ' · From: ' + m.getFrom()
               + ' · ' + m.getSubject() + (mmFromMe_(m, me) ? '' : '  ⚠ From không phải tài khoản/bí danh ở trên → lần đồng bộ thường đang bỏ qua'));
    out.push(mmPack_(m));
  }));
  if (!out.length) { Logger.log('Không thấy mail nào trong Đã gửi gửi tới ' + email); return; }
  const r = mmPost_({ op: 'push', mails: out });
  Logger.log('Đã gửi ' + out.length + ' mail sang portal (portal đang có ' + r.count + ' mail) → tìm lại trên portal');
}

function miloMailSync(e) {
  const p = PropertiesService.getScriptProperties();
  if (e && e.triggerUid) {  // trigger 1 phút/lần → chỉ chạy thật khi đủ 2 phút (giờ làm) / 15 phút (ban đêm)
    const h = Number(Utilities.formatDate(new Date(), 'Asia/Ho_Chi_Minh', 'H')), day = h >= MM_DAY_FROM && h < MM_DAY_TO;
    const every = (day ? MM_EVERY_DAY_MIN : MM_EVERY_NIGHT_MIN) * 60 * 1000;
    if (Date.now() - Number(p.getProperty('mm_last') || 0) < every - 20 * 1000) return;
  }
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return;
  const t0 = Date.now();
  p.setProperty('mm_last', String(t0));
  const me = mmMe_(), q = s => ['in:sent', MM_FILTER, s].filter(String).join(' ');
  let buf = [], size = 0, sent = 0;
  const flush = () => { if (!buf.length) return; mmPost_({ op: 'push', mails: buf }); sent += buf.length; buf = []; size = 0; };
  const add = m => { const o = mmPack_(m), n = JSON.stringify(o).length; if (size + n > MM_BATCH_CHARS) flush(); buf.push(o); size += n; };
  try {
    // 1) mail mới: tìm lùi 15 phút so với mốc (Gmail đánh chỉ mục chậm), bỏ qua mail đã gửi (mm_ids)
    const mark = Number(p.getProperty('mm_new') || Math.floor(t0 / 1000)), since = mark - 900;
    const ids = JSON.parse(p.getProperty('mm_ids') || '{}');
    let newest = mark;
    for (let start = 0; ; start += MM_PAGE) {
      const th = GmailApp.search(q('after:' + since), start, MM_PAGE);
      th.forEach(t => t.getMessages().forEach(m => {
        const at = Math.floor(m.getDate().getTime() / 1000);
        if (at < since || ids[m.getId()] || !mmFromMe_(m, me)) return;
        add(m);
        ids[m.getId()] = at;
        newest = Math.max(newest, at);
      }));
      if (th.length < MM_PAGE) break;
    }
    flush();
    Object.keys(ids).forEach(k => { if (ids[k] < newest - 3600) delete ids[k]; });
    p.setProperties({ mm_new: String(newest), mm_ids: JSON.stringify(ids) });
    if (sent) Logger.log('Đã gửi ' + sent + ' mail mới sang portal');
    // 2) lịch sử cũ (trước lúc chạy miloMailSetup): từng trang, nhớ vị trí để lần sau làm tiếp
    if (!p.getProperty('mm_done')) {
      const before = Number(p.getProperty('mm_old'));
      let start = Number(p.getProperty('mm_start') || 0), old = 0;
      while (Date.now() - t0 < MM_BUDGET_MS) {
        const th = GmailApp.search(q('before:' + before + (MM_SINCE ? ' after:' + MM_SINCE : '')), start, MM_PAGE);
        if (!th.length) { p.setProperty('mm_done', '1'); Logger.log('Đã gửi xong lịch sử mail'); break; }
        th.forEach(t => t.getMessages().forEach(m => {
          if (m.getDate().getTime() / 1000 >= before || !mmFromMe_(m, me)) return;
          add(m);
          old++;
        }));
        flush();
        start += th.length;
        p.setProperty('mm_start', String(start));
      }
      if (old) Logger.log('Đã gửi ' + old + ' mail cũ (tới cuộc thư thứ ' + p.getProperty('mm_start') + ')' + (p.getProperty('mm_done') ? '' : ' — lần chạy sau làm tiếp'));
    }
    if (!sent) mmPost_({ op: 'ping' });
  } finally {
    lock.releaseLock();
  }
}
"""


def apps_script(tok: str, portal: str) -> str:
    return APPS_SCRIPT.replace("__PORTAL__", portal).replace("__TOKEN__", tok)
