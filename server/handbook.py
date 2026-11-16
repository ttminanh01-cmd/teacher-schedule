"""Cẩm nang: đọc trực tiếp Google Sheet công khai (chế độ "Bất kỳ ai có link đều xem được").

Mỗi tab của sheet là một mục. Dữ liệu được cache CACHE_TTL giây nên khi sheet
thay đổi, web sẽ tự cập nhật theo sau tối đa CACHE_TTL giây (hoặc bấm "Làm mới").
"""
import os
import csv
import io
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
        raise HandbookError("Sheet chưa được chia sẻ công khai (Bất kỳ ai có link đều xem được)")
    return body


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
    def load():
        html = _get(f"https://docs.google.com/spreadsheets/d/{sheet_id}/htmlview")
        tabs = [{"gid": gid, "name": _unescape(name)}
                for name, gid in re.findall(r'\{name: "((?:[^"\\]|\\.)*)", pageUrl: "[^"]*", gid: "(\d+)"', html)]
        if not tabs:
            raise HandbookError("Không đọc được danh sách tab — kiểm tra quyền chia sẻ của sheet")
        return tabs
    return _cached(f"tabs:{sheet_id}", load, refresh)


def get_tab(sheet_id: str, gid: str, refresh: bool = False):
    def load():
        text = _get(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}")
        rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text))]
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
