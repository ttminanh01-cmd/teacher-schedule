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


def teachers(refresh: bool = False) -> list:
    """Danh sách GV (cache TTL; refresh chỉ tải lại nếu bản cũ hơn 10 phút). Lỗi mạng → dùng bản cũ / []."""
    with _lock:
        age = time.time() - _cache["at"]
        if _cache["list"] is not None and (age < TTL and not (refresh and age > 600)):
            return _cache["list"]
    try:
        lst, err = _fetch(), None
    except Exception as e:  # noqa: BLE001
        lst, err = None, f"Không tải được danh sách GV từ icanconnect.vn ({e.__class__.__name__})"
    with _lock:
        if lst is not None:
            _cache.update(at=time.time(), list=lst, error=None)
        else:
            _cache.update(at=time.time() - TTL + 600, error=err)  # thử lại sau 10 phút
            if _cache["list"] is None:
                return []
        return _cache["list"]


def last_error():
    return _cache["error"]


def find(name: str, brand: str, lst: list):
    """Khớp tên: đúng chữ (không phân biệt hoa thường) trong đúng trung tâm → đúng chữ ở mọi trung tâm (nếu chỉ 1 link)
    → bỏ dấu, cùng các bước trên. Trả về url hoặc None."""
    if not name.strip():
        return None
    for norm in (_exact, _fold):
        key = norm(name)
        hits = [t for t in lst if norm(t["name"]) == key]
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
