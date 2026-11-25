"""Cẩm nang: đọc trực tiếp Google Sheet.

Hai cách đọc:
  - Đã cài Apps Script (Quản trị → Cẩm nang): script chạy bằng tài khoản công ty của admin tự GỬI sheet
    sang portal ngay khi sửa (dự phòng mỗi 1 phút) (dùng cho sheet chỉ chia sẻ trong công ty).
  - Chưa cài: đọc sheet công khai ("Bất kỳ ai có link đều xem được").

Mỗi tab của sheet là một mục. Dữ liệu được cache CACHE_TTL giây nên khi sheet
thay đổi, web sẽ tự cập nhật theo sau tối đa CACHE_TTL giây (hoặc bấm "Làm mới").
"""
import os
import csv
import io
import json
import urllib.parse
import html
import re
import threading
import time
import unicodedata
import urllib.request

CACHE_TTL = 300
DEFAULT_SHEET_ID = os.environ.get("HANDBOOK_SHEET_ID", "")  # đặt trong Quản trị → Cẩm nang hoặc biến môi trường

_lock = threading.Lock()
_cache: dict = {}  # key -> (fetched_ts, value)


class HandbookError(Exception):
    pass


def parse_sheet_id(text: str) -> str:
    text = (text or "").strip()
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]{20,})", text)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", text):
        return text
    raise HandbookError("Link Google Sheet không hợp lệ")


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ctv-portal"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            ctype = r.headers.get("Content-Type", "")
            body = r.read().decode("utf-8")
    except Exception as e:  # mạng lỗi / sheet bị khoá
        raise HandbookError(f"Không tải được Google Sheet ({e.__class__.__name__})")
    if "text/html" in ctype and "export" in url:
        raise HandbookError("Sheet không công khai — cài Apps Script (Quản trị → Cẩm nang) bằng tài khoản có quyền xem sheet")
    return body


# ----- Apps Script gửi dữ liệu sang (sheet chỉ chia sẻ trong công ty, portal không tự đọc được)
# Script chạy bằng tài khoản công ty của admin: trigger khi sửa sheet + mỗi 1 phút, chỉ gửi khi có thay đổi,
# không đổi thì 10 phút gửi "ping" nhẹ 1 lần. Bản nhận được lưu DB (settings.hb_snapshot) + giữ trong bộ nhớ, nên Neon chỉ bị
# đánh thức khi sheet thực sự đổi (và 1 lần lúc khởi động).
_snap: dict = {"loaded": False, "data": None, "token": "", "seen": None}


def _load_snapshot():
    if _snap["loaded"]:
        return
    try:
        from . import db
        con = db.connect()
        try:
            raw = db.get_setting(con, "hb_snapshot")
            _snap["token"] = db.get_setting(con, "hb_gas_token")
        finally:
            con.close()
        _snap["data"] = json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001 — không đọc được DB thì coi như chưa có
        _snap["data"] = None
    _snap["loaded"] = True


def snapshot(sheet_id: str | None = None):
    """Bản sheet do Apps Script gửi (nếu có, và đúng sheet đang cấu hình)."""
    _load_snapshot()
    d = _snap["data"]
    if d and (sheet_id is None or d.get("sheet") == sheet_id):
        return d
    return None


def push_token() -> str:
    _load_snapshot()
    return _snap["token"]


def set_push_token(tok: str):
    _snap["token"] = tok


def receive(con, body: dict) -> dict:
    """Apps Script gọi vào. body: {token, sheet, ping?} hoặc {token, sheet, tabs: [{gid, name, rows, links}]}."""
    from . import db
    tok = push_token()
    if not tok or body.get("token") != tok:
        raise HandbookError("Sai mã bảo mật")
    now = time.time()
    _snap["seen"] = now
    if body.get("ping"):
        return {"ok": True, "changed": False}
    tabs = body.get("tabs")
    if not isinstance(tabs, list) or not body.get("sheet"):
        raise HandbookError("Dữ liệu không hợp lệ")
    data = {"sheet": str(body["sheet"]), "at": now,
            "tabs": [{"gid": str(t["gid"]), "name": str(t["name"]), "rows": t.get("rows") or [],
                      "links": t.get("links") or []} for t in tabs]}
    db.set_setting(con, "hb_snapshot", json.dumps(data, ensure_ascii=False))
    _snap["data"] = data
    clear_cache()
    return {"ok": True, "changed": True, "tabs": len(data["tabs"])}


def push_status() -> dict:
    d = snapshot()
    return {"data_at": d["at"] if d else None, "data_sheet": d["sheet"] if d else None,
            "seen_at": _snap["seen"]}


def apps_script(token: str, sheet_id: str, portal: str) -> str:
    return f"""// Cổng CTV ← Cẩm nang. Chạy bằng tài khoản công ty của bạn (sheet không cần công khai).
// Cài: script.google.com → Dự án mới → dán code → 💾 Lưu → chọn hàm "setup" → ▶ Chạy → cho phép quyền.
// Sau đó: có người sửa sheet là gửi ngay (nếu Google cho gắn trigger "khi thay đổi"), và kiểm tra lại mỗi 1 phút.
const PORTAL = '{portal}/api/handbook/push';
const TOKEN = '{token}';
const SHEET_ID = '{sheet_id}';
const LINK_MAX_ROWS = {LINK_MAX_ROWS};

function setup() {{
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('sync').timeBased().everyMinutes(1).create();
  try {{
    ScriptApp.newTrigger('sync').forSpreadsheet(SHEET_ID).onChange().create();
    Logger.log('Đã bật cập nhật ngay khi sửa sheet + kiểm tra mỗi 1 phút');
  }} catch (err) {{
    Logger.log('Không gắn được trigger khi sửa sheet (' + err.message + ') → vẫn kiểm tra mỗi 1 phút');
  }}
  const p = PropertiesService.getScriptProperties();
  p.deleteProperty('hash'); p.deleteProperty('full'); p.deleteProperty('ping');
  sync();
}}

function sync() {{
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;  // đang gửi dở thì bỏ qua, lần sau sẽ bắt kịp
  try {{
    const p = PropertiesService.getScriptProperties(), now = Date.now();
    const sheets = SpreadsheetApp.openById(SHEET_ID).getSheets();
    const tabs = sheets.map(sh => ({{ gid: String(sh.getSheetId()), name: sh.getName(), rows: sh.getDataRange().getDisplayValues(), links: [] }}));
    // so nội dung chữ mỗi lần; 30 phút/lần so cả link gắn trong chữ (đọc link chậm hơn)
    const fullCheck = now - Number(p.getProperty('full') || 0) > 30 * 60 * 1000;
    let hash = md5(JSON.stringify(tabs.map(t => [t.gid, t.name, t.rows])));
    const changed = hash !== p.getProperty('hash');
    if (changed || fullCheck) {{
      sheets.forEach((sh, k) => {{
        if (tabs[k].rows.length > LINK_MAX_ROWS) return;
        const rg = sh.getDataRange(), formulas = rg.getFormulas();
        rg.getRichTextValues().forEach((r, i) => r.forEach((c, j) => {{
          let a = c ? c.getRuns().filter(x => x.getLinkUrl()).map(x => [x.getText().trim(), x.getLinkUrl()]) : [];
          if (!a.length && c && c.getLinkUrl()) a.push([c.getText().trim(), c.getLinkUrl()]);
          // ô dùng công thức =HYPERLINK("url"; "chữ") → lấy url từ công thức
          const m = !a.length && /HYPERLINK\\(\\s*"([^"]+)"/i.exec(formulas[i][j] || '');
          if (m) a.push([String(tabs[k].rows[i][j]).trim(), m[1]]);
          if (a.length) tabs[k].links.push([i, j, a]);
        }}));
      }});
      p.setProperty('full', String(now));
    }}
    const linksHash = (changed || fullCheck) ? md5(JSON.stringify(tabs.map(t => t.links))) : p.getProperty('links');
    const send = changed || linksHash !== p.getProperty('links');
    if (!send && now - Number(p.getProperty('ping') || 0) < 10 * 60 * 1000) return;  // không đổi: 10 phút báo "còn sống" 1 lần
    const body = send ? {{ token: TOKEN, sheet: SHEET_ID, tabs: tabs }} : {{ token: TOKEN, sheet: SHEET_ID, ping: true }};
    const res = UrlFetchApp.fetch(PORTAL, {{ method: 'post', contentType: 'application/json', payload: JSON.stringify(body), muteHttpExceptions: true }});
    if (res.getResponseCode() !== 200) throw new Error('Portal báo lỗi ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 300));
    p.setProperty('ping', String(now));
    if (send) {{ p.setProperty('hash', hash); p.setProperty('links', linksHash); }}
    Logger.log(send ? 'Đã gửi ' + tabs.length + ' tab sang portal' : 'Sheet không đổi');
  }} finally {{
    lock.releaseLock();
  }}
}}

function md5(s) {{
  return Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, s, Utilities.Charset.UTF_8));
}}
"""


def _cached(key: str, loader, refresh: bool):
    with _lock:
        hit = _cache.get(key)
    if hit and not refresh and time.time() - hit[0] < CACHE_TTL:
        return hit[1], hit[0], None
    try:
        val = loader()
    except HandbookError as e:
        if hit:  # dùng tạm bản cũ nếu Google lỗi
            return hit[1], hit[0], str(e)
        raise
    now = time.time()
    with _lock:
        _cache[key] = (now, val)
    return val, now, None


def clear_cache():
    with _lock:
        _cache.clear()


def _unescape(s: str) -> str:
    s = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), s)
    return s.replace("\\/", "/").replace('\\"', '"')


def list_tabs(sheet_id: str, refresh: bool = False):
    def public():
        html = _get(f"https://docs.google.com/spreadsheets/d/{sheet_id}/htmlview")
        tabs = [{"gid": gid, "name": _unescape(name)}
                for name, gid in re.findall(r'\{name: "((?:[^"\\]|\\.)*)", pageUrl: "[^"]*", gid: "(\d+)"', html)]
        if not tabs:
            raise HandbookError("Không đọc được danh sách tab — sheet không công khai và chưa cài Apps Script")
        return tabs

    def load():
        snap = snapshot(sheet_id)
        if snap:
            return [{"gid": t["gid"], "name": t["name"]} for t in snap["tabs"]]
        return public()
    return _cached(f"tabs:{sheet_id}", load, refresh)


LINK_MAX_ROWS = 2000  # sheet lớn hơn (VD CSS ~10k dòng) bỏ qua bước lấy link để không chậm


def _cell_text(h: str) -> str:
    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", h))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _real_url(href: str) -> str:
    href = html.unescape(href)
    m = re.match(r"https?://www\.google\.com/url\?(.*)", href)
    if m:
        q = urllib.parse.parse_qs(m.group(1)).get("q")
        if q:
            return q[0]
    return href


def attach_links(sheet_id: str, gid: str, rows: list) -> list:
    """Bản CSV làm mất link gắn trong chữ (VD chữ "LINK" trỏ tới 1 file). Đọc bản htmlview để lấy link
    theo từng ô rồi ghép vào đúng ô đó dạng ⟦chữ|url⟧ — giao diện hiển thị thành link bấm được."""
    try:
        page = _get(f"https://docs.google.com/spreadsheets/d/{sheet_id}/htmlview/sheet?headers=false&gid={gid}")
    except Exception:  # noqa: BLE001 — không lấy được link thì vẫn dùng dữ liệu CSV
        return rows
    page = page.decode("utf-8", "replace") if isinstance(page, bytes) else page
    used = set()
    for i, tr in enumerate(re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S)):
        for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S):
            anchors = re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', td, re.S)
            if not anchors:
                continue
            text = _norm(_cell_text(td))
            # tìm ô CSV có cùng nội dung: ưu tiên dòng gần vị trí tương ứng
            order = sorted(range(len(rows)), key=lambda r: abs(r - i))
            hit = next(((r, c) for r in order for c, v in enumerate(rows[r]) if (r, c) not in used and _norm(v) == text), None)
            if not hit:
                continue
            used.add(hit)
            r, c = hit
            rows[r][c] = wrap_links(rows[r][c], [(_cell_text(inner).strip(), _real_url(href)) for href, inner in anchors])
    return rows


def wrap_links(cell: str, anchors) -> str:
    """Gắn link vào phần chữ của ô: chữ "LINK" → ⟦LINK|url⟧."""
    for label, url in anchors:
        if not label or not url or label == url or url.startswith("#") or "⟦" in label:
            continue  # ô ghi thẳng URL: giao diện đã tự tạo link
        if label in cell:
            cell = cell.replace(label, f"⟦{label}|{url}⟧", 1)
    return cell


def fetch_rows(sheet_id: str, gid: str, links: bool = False) -> list[list[str]]:
    """Toàn bộ ô của 1 tab (giá trị hiển thị, như bản CSV). links=True: gắn link trong chữ (sheet ≤ LINK_MAX_ROWS dòng)."""
    def public():
        text = _get(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}")
        rows = list(csv.reader(io.StringIO(text)))
        if links and len(rows) <= LINK_MAX_ROWS:
            rows = attach_links(sheet_id, gid, [[c.strip() for c in r] for r in rows])
        return rows

    snap = snapshot(sheet_id)
    if not snap:
        return public()
    tab = next((t for t in snap["tabs"] if t["gid"] == str(gid)), None)
    if not tab:
        raise HandbookError("Không thấy tab này trong dữ liệu Apps Script gửi sang")
    rows = [[str(c) for c in r] for r in tab["rows"]]
    for r, c, anchors in (tab.get("links") or []) if links else []:
        if r < len(rows) and c < len(rows[r]):
            rows[r][c] = wrap_links(rows[r][c].strip(), anchors)
    return rows


def get_tab(sheet_id: str, gid: str, refresh: bool = False):
    def load():
        rows = [[c.strip() for c in r] for r in fetch_rows(sheet_id, gid, links=True)]
        rows = [r for r in rows if any(r)]
        width = max((max((i + 1 for i, c in enumerate(r) if c), default=0) for r in rows), default=0)
        # bỏ các cột trống hoàn toàn
        keep = [i for i in range(width) if any(i < len(r) and r[i] for r in rows)]
        return [[r[i] if i < len(r) else "" for i in keep] for r in rows]
    return _cached(f"tab:{sheet_id}:{gid}", load, refresh)


def get_blocks(sheet_id: str, gid: str, refresh: bool = False):
    """Tab có nhiều bảng đặt cạnh nhau (ngăn bởi cột trống) → [{title, header, rows}].
    VD "Danh sách Profile Giáo viên": bảng GV nước ngoài | cột trống | bảng GV Việt Nam."""
    def load():
        raw = [[c.strip() for c in r] for r in fetch_rows(sheet_id, gid, links=True)]
        width = max((len(r) for r in raw), default=0)
        filled = [any(i < len(r) and r[i] for r in raw) for i in range(width)]
        segs, start = [], None
        for i in range(width + 1):
            if i < width and filled[i]:
                start = i if start is None else start
            elif start is not None:
                segs.append((start, i))
                start = None
        blocks = []
        for a, b in segs:
            part = [r[a:b] + [""] * (b - a - len(r[a:b])) for r in raw]
            h = next((k for k, r in enumerate(part) if sum(1 for c in r if c) >= 2), -1)
            if h < 0:
                continue
            title = " · ".join(t for t in (next((c for c in r if c), "") for r in part[:h]) if t)
            rows = [r for r in part[h + 1:] if any(r)]
            if rows:
                blocks.append({"title": title, "header": part[h], "rows": rows})
        return blocks
    return _cached(f"blocks:{sheet_id}:{gid}", load, refresh)


def sort_tabs(tabs: list) -> list:
    """Tab tên bắt đầu bằng số ("1. ...", "2. ...", "3.SCRIPT") lên đầu theo thứ tự số, còn lại giữ thứ tự sheet."""
    def key(item):
        i, t = item
        m = re.match(r"\s*(\d+)", t["name"])
        return (0, int(m.group(1)), i) if m else (1, 0, i)
    return [t for _, t in sorted(enumerate(tabs), key=key)]


def fold(text: str) -> str:
    """Bỏ dấu tiếng Việt + chữ thường, để "doi lich" khớp "Đổi lịch"."""
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D").lower()


def header_index(rows: list) -> int:
    for i, r in enumerate(rows):
        if sum(1 for c in r if c) >= 2:
            return i
    return -1


MODES = ("show", "suggest", "other", "hidden")


def default_mode(name: str) -> str:
    """Vai trò mặc định khi tìm kiếm: Script/Template/Kho ticket hiện sẵn, Tra cứu nghiệp vụ gợi ý thu gọn."""
    n = fold(name)
    if "script" in n or "template" in n:
        return "show"
    if "nghiep vu" in n:
        return "suggest"
    return "other"


def search_rank(name: str) -> int:
    n = fold(name)
    for i, k in enumerate(("script", "template", "ticket")):
        if k in n:
            return i
    return 9
