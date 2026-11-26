"""Link profile giáo viên lấy trực tiếp từ trang công khai https://www.icanconnect.vn/giao-vien.

Trang (Next.js) nhúng sẵn toàn bộ danh sách GV trong __NEXT_DATA__: tên, slug, "Giáo viên giảng dạy tại …".
Link hồ sơ = https://www.icanconnect.vn/giao-vien/<slug>. Không có mã GV → khớp theo tên.
Dùng cho bảng tra cứu GV ở mục Tài liệu: cột "Link teacher site" lấy link từ đây (sheet có thể ghi sai),
không tìm thấy tên thì giữ link trong sheet. Cột "Link profile" giữ nguyên theo sheet.
"""
import json
import re
import threading
import time
import unicodedata
import urllib.request

URL = "https://www.icanconnect.vn/giao-vien"
TTL = 6 * 3600
_lock = threading.Lock()
_cache = {"at": 0.0, "list": None, "error": None}
_refreshing = threading.Event()


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", s).strip().lower()


def _exact(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "")).strip().lower()


def brand_of(text: str) -> str:
    f = _fold(text).replace(" ", "")
    if "speakwell" in f or "easyspeak" in f:
        return "spw"
    if "easypass" in f or "ezp" in f:
        return "ezp"
    if "ielts" in f:
        return "ielts"
    return ""


def _fetch() -> list:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (ctv-portal)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("không thấy dữ liệu giáo viên trên trang")
    items = json.loads(m.group(1))["props"]["pageProps"]["teacherProfileConfig"]
    out = []
    for it in items:
        a = it.get("attributes") or {}
        if a.get("name") and a.get("slug"):
            out.append({"name": a["name"].strip(), "url": f"{URL}/{a['slug']}", "brand": brand_of(a.get("subTitle") or "")})
    if not out:
        raise ValueError("danh sách giáo viên trống")
    return out


def _index(lst: list) -> dict:
    """Tra tên nhanh: {(cách chuẩn hoá, tên đã chuẩn hoá): [GV]} — khỏi so từng dòng với cả nghìn GV."""
    idx = {}
    for t in lst:
        for kind, norm in (("exact", _exact), ("fold", _fold)):
            idx.setdefault((kind, norm(t["name"])), []).append(t)
    return idx


def _load() -> list:
    try:
        lst, err = _fetch(), None
    except Exception as e:  # noqa: BLE001
        lst, err = None, f"Không tải được danh sách GV từ icanconnect.vn ({e.__class__.__name__})"
    with _lock:
        if lst is not None:
            _cache.update(at=time.time(), list=lst, index=_index(lst), error=None)
        else:
            _cache.update(at=time.time() - TTL + 600, error=err)  # thử lại sau 10 phút
        return _cache["list"] or []


def _refresh_bg():
    if _refreshing.is_set():
        return
    _refreshing.set()

    def run():
        try:
            _load()
        finally:
            _refreshing.clear()
    threading.Thread(target=run, daemon=True).start()


def warm():
    """Gọi lúc server khởi động: tải sẵn để người mở tab đầu tiên không phải chờ."""
    _refresh_bg()


def teachers(refresh: bool = False) -> list:
    """Danh sách GV. Có bản cũ thì trả ngay, hết hạn (TTL) / bấm Làm mới (bản > 10 phút) thì tải lại ngầm.
    Chưa có bản nào thì tải luôn. Lỗi mạng → dùng bản cũ / []."""
    with _lock:
        age = time.time() - _cache["at"]
        have = _cache["list"] is not None
    if have:
        if age >= TTL or (refresh and age > 600):
            _refresh_bg()
        return _cache["list"]
    return _load()


def last_error():
    return _cache["error"]


def find(name: str, brand: str, lst: list):
    """Khớp tên: đúng chữ (không phân biệt hoa thường) trong đúng trung tâm → đúng chữ ở mọi trung tâm (nếu chỉ 1 link)
    → bỏ dấu, cùng các bước trên. Trả về url hoặc None."""
    if not name.strip():
        return None
    idx = _cache.get("index") if lst is _cache["list"] else None
    if idx is None:
        idx = _index(lst)
    for kind, norm in (("exact", _exact), ("fold", _fold)):
        hits = idx.get((kind, norm(name)), [])
        if not hits:
            continue
        same = [t for t in hits if brand and t["brand"] == brand]
        for group in (same, hits):
            urls = {t["url"] for t in group}
            if len(urls) == 1:
                return urls.pop()
    return None


LINK = re.compile(r"⟦([^⟦⟧|]*)\|([^⟧]*)⟧")


def _label(cell: str) -> str:
    return LINK.sub(lambda m: m.group(1), cell or "").strip() or "Link"


def apply(blocks: list, tab_name: str, refresh: bool = False) -> tuple[list, dict]:
    """Bảng GV: cột "Link teacher site" = trang GV trên icanconnect khớp theo cột "Tên" (sheet có thể ghi sai);
    không thấy tên trên web thì giữ link sheet. Cột "Link profile" giữ nguyên theo sheet.
    Không sửa blocks gốc (đang cache). → (blocks mới, {matched, missing: [tên], error})"""
    targets = []
    for b in blocks:
        h = [_fold(c) for c in b["header"]]
        ti = next((i for i, c in enumerate(h) if "teacher site" in c), -1)
        ni = next((i for i, c in enumerate(h) if c in ("ten", "ten gv", "ho ten", "ten giao vien")), -1)
        targets.append((ti, ni))
    if all(ti < 0 or ni < 0 for ti, ni in targets):
        return blocks, {}
    lst = teachers(refresh)
    stat = {"matched": 0, "missing": [], "error": last_error()}
    if not lst:
        return blocks, stat
    out = []
    for b, (ti, ni) in zip(blocks, targets):
        if ti < 0 or ni < 0:
            out.append(b)
            continue
        brand = brand_of(b.get("title") or "") or brand_of(tab_name)
        rows = []
        for r in b["rows"]:
            r = list(r) + [""] * (max(ti, ni) + 1 - len(r))
            name = r[ni].strip()
            url = find(name, brand, lst)
            if url:
                r[ti] = f"⟦{_label(r[ti])}|{url}⟧"
                stat["matched"] += 1
            elif name:
                stat["missing"].append(name)
            rows.append(r)
        out.append({**b, "rows": rows})
    return out, stat


SPW_TEACHER = "https://speakwell.ican.vn/teachers/"
CODE = re.compile(r"\bTC[A-Z]*\d{4,}\b", re.I)  # TC015922, TCICL260080


def add_spw_schedule(blocks: list, tab_name: str) -> list:
    """Bảng GV SpeakWell: thêm cột "Check lịch rảnh GV" = trang GV trên speakwell.ican.vn/teachers/<Mã gv>
    (ở đó chọn "Đăng ký theo buổi" để xem lịch rảnh). Không sửa blocks gốc."""
    out = []
    for b in blocks:
        h = [_fold(c) for c in b["header"]]
        ci = next((i for i, c in enumerate(h) if c in ("ma gv", "ma giao vien", "ma")), -1)
        if ci < 0 or (brand_of(b.get("title") or "") or brand_of(tab_name)) != "spw" or "check lich ranh gv" in h:
            out.append(b)
            continue
        n = len(b["header"])
        rows = []
        for r in b["rows"]:
            r = list(r) + [""] * (n - len(r))
            m = CODE.search(LINK.sub(lambda x: x.group(1), r[ci] or ""))
            rows.append(r + ([f"⟦Check lịch|{SPW_TEACHER}{m.group(0).upper()}⟧"] if m else [""]))
        out.append({**b, "header": list(b["header"]) + ["Check lịch rảnh GV"], "rows": rows})
    return out
