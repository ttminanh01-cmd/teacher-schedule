"""Cẩm nang: đọc trực tiếp Google Sheet.

Hai cách đọc:
  - Đã cài Apps Script (Quản trị → Cẩm nang): đọc qua web app chạy bằng tài khoản Google
    của người triển khai → đọc được cả sheet KHÔNG công khai mà tài khoản đó xem được.
  - Chưa cài: đọc sheet công khai ("Bất kỳ ai có link đều xem được").
Nếu Apps Script lỗi thì thử lại kiểu công khai.

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


# ----- Apps Script: đọc bằng quyền tài khoản Google của người triển khai
_bridge_cache: tuple = (0.0, None)


def bridge():
    """(url, token) của Apps Script nếu đã cài. Lấy từ biến môi trường GAS_URL/GAS_TOKEN hoặc cài đặt trong DB."""
    global _bridge_cache
    ts, val = _bridge_cache
    if time.time() - ts < 1800:  # đọc DB 30 phút/lần để Neon được ngủ; lưu cài đặt thì reset_bridge() ngay
        return val
    url, tok = os.environ.get("GAS_URL", ""), os.environ.get("GAS_TOKEN", "")
    if not url:
        try:
            from . import db
            con = db.connect()
            try:
                url, tok = db.get_setting(con, "hb_gas_url"), db.get_setting(con, "hb_gas_token")
            finally:
                con.close()
        except Exception:  # noqa: BLE001 — không đọc được DB thì coi như chưa cài
            url = ""
    val = (url, tok) if url and tok else None
    _bridge_cache = (time.time(), val)
    return val


def reset_bridge():
    global _bridge_cache
    _bridge_cache = (0.0, None)


def apps_script(token: str) -> str:
    return f"""// Cổng CTV → đọc Cẩm nang bằng quyền tài khoản Google của bạn (sheet không cần công khai).
// Tạo tại script.google.com → Dự án mới, dán code này, Triển khai → Ứng dụng web (Thực thi: Tôi, Truy cập: Bất kỳ ai).
const TOKEN = '{token}';

function doGet(e) {{
  const p = e.parameter;
  if (p.token !== TOKEN) return out({{ ok: false, error: 'Sai mã bảo mật' }});
  try {{
    const ss = SpreadsheetApp.openById(p.id);
    if (p.action === 'tabs') {{
      return out({{ ok: true, tabs: ss.getSheets().map(s => ({{ gid: String(s.getSheetId()), name: s.getName() }})) }});
    }}
    if (p.action === 'values') {{
      const sh = ss.getSheets().find(s => String(s.getSheetId()) === String(p.gid));
      if (!sh) return out({{ ok: false, error: 'Không thấy tab gid ' + p.gid }});
      const rg = sh.getDataRange(), rows = rg.getDisplayValues(), links = [];
      if (rows.length <= Number(p.links || 0)) {{
        rg.getRichTextValues().forEach((r, i) => r.forEach((c, j) => {{
          if (!c) return;
          const a = c.getRuns().filter(x => x.getLinkUrl()).map(x => [x.getText().trim(), x.getLinkUrl()]);
          if (!a.length && c.getLinkUrl()) a.push([c.getText().trim(), c.getLinkUrl()]);
          if (a.length) links.push([i, j, a]);
        }}));
      }}
      return out({{ ok: true, rows: rows, links: links }});
    }}
    return out({{ ok: false, error: 'Thao tác không hợp lệ' }});
  }} catch (err) {{
    return out({{ ok: false, error: 'Tài khoản chạy Apps Script không mở được sheet: ' + err.message }});
  }}
}}

function out(o) {{
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}}
"""


def gas(action: str, **params) -> dict:
    url, tok = bridge() or ("", "")
    if not url:
        raise HandbookError("Chưa cài Apps Script")
    q = urllib.parse.urlencode({"action": action, "token": tok, **params})
    req = urllib.request.Request(f"{url}?{q}", headers={"User-Agent": "ctv-portal"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        raise HandbookError(f"Không gọi được Apps Script ({e.__class__.__name__})")
    try:
        res = json.loads(body)
    except ValueError:
        raise HandbookError("Apps Script trả về không đúng — kiểm tra URL (…/exec), code đã dán đúng và triển khai Truy cập: Bất kỳ ai")
    if not res.get("ok"):
        raise HandbookError(res.get("error") or "Apps Script báo lỗi")
    return res


def _via(bridged, public):
    """Ưu tiên Apps Script; lỗi thì thử kiểu công khai, vẫn lỗi thì báo lỗi của Apps Script."""
    if not bridge():
        return public()
    try:
        return bridged()
    except HandbookError as e:
        try:
            return public()
        except HandbookError:
            raise e


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

    def bridged():
        return [{"gid": str(t["gid"]), "name": t["name"]} for t in gas("tabs", id=sheet_id)["tabs"]]
    return _cached(f"tabs:{sheet_id}", lambda: _via(bridged, public), refresh)


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

    def bridged():
        res = gas("values", id=sheet_id, gid=gid, links=LINK_MAX_ROWS if links else 0)
        rows = [[str(c) for c in r] for r in res["rows"]]
        for r, c, anchors in res.get("links") or []:
            if r < len(rows) and c < len(rows[r]):
                rows[r][c] = wrap_links(rows[r][c].strip(), anchors)
        return rows
    return _via(bridged, public)


def get_tab(sheet_id: str, gid: str, refresh: bool = False):
    def load():
        rows = [[c.strip() for c in r] for r in fetch_rows(sheet_id, gid, links=True)]
        rows = [r for r in rows if any(r)]
        width = max((max((i + 1 for i, c in enumerate(r) if c), default=0) for r in rows), default=0)
        # bỏ các cột trống hoàn toàn
        keep = [i for i in range(width) if any(i < len(r) and r[i] for r in rows)]
        return [[r[i] if i < len(r) else "" for i in keep] for r in rows]
    return _cached(f"tab:{sheet_id}:{gid}", load, refresh)


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
