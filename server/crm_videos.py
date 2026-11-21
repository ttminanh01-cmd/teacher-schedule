"""Thao tác ở CRM: video hướng dẫn lưu trên Google Drive.

Admin dán link thư mục hoặc link file Drive (chia sẻ "Bất kỳ ai có đường liên kết").
Thư mục công khai được đọc qua trang embeddedfolderview của Drive (không cần API key),
CTV xem video ngay trên web bằng trình phát /preview của Drive.
"""
import html
import re
import threading
import time
import urllib.request

CACHE_TTL = 300
MAX_DEPTH = 2  # đọc thêm tối đa 2 cấp thư mục con

_lock = threading.Lock()
_cache: dict = {}  # folder_id -> (ts, entries)


class DriveError(Exception):
    pass


def parse_link(text: str):
    """→ ("folder" | "file", id)"""
    t = (text or "").strip()
    m = re.search(r"/folders/([a-zA-Z0-9_-]{10,})", t)
    if m:
        return "folder", m.group(1)
    m = re.search(r"/file/d/([a-zA-Z0-9_-]{10,})", t) or re.search(r"[?&]id=([a-zA-Z0-9_-]{10,})", t) \
        or re.search(r"/d/([a-zA-Z0-9_-]{10,})", t)
    if m:
        return "file", m.group(1)
    raise DriveError("Link Google Drive không hợp lệ")


def _fetch_folder(fid: str) -> list:
    url = f"https://drive.google.com/embeddedfolderview?id={fid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ctv-portal)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", "replace")
    except Exception as e:
        raise DriveError(f"Không đọc được thư mục Drive ({e.__class__.__name__}) — kiểm tra đã chia sẻ công khai chưa")
    out = []
    for m in re.finditer(r'<div class="flip-entry" id="entry-([a-zA-Z0-9_-]+)".*?<a href="([^"]*)".*?flip-entry-title">([^<]*)<', body, re.S):
        eid, href, title = m.group(1), html.unescape(m.group(2)), html.unescape(m.group(3)).strip()
        out.append({"id": eid, "title": title, "folder": "/folders/" in href})
    if not out and "flip-entry" not in body and "folder-view" not in body:
        raise DriveError("Thư mục Drive chưa được chia sẻ công khai (Bất kỳ ai có đường liên kết)")
    return out


def _folder(fid: str, refresh: bool) -> tuple[list, str | None]:
    with _lock:
        hit = _cache.get(fid)
    if hit and not refresh and time.time() - hit[0] < CACHE_TTL:
        return hit[1], None
    try:
        val = _fetch_folder(fid)
    except DriveError as e:
        if hit:
            return hit[1], str(e)
        raise
    with _lock:
        _cache[fid] = (time.time(), val)
    return val, None


def _natkey(s: str):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", s)]


def clean_title(t: str) -> str:
    """bỏ đuôi .mp4, thay _ bằng khoảng trắng"""
    t = re.sub(r"\.(mp4|mov|m4v|webm|mkv|avi|wmv)$", "", t, flags=re.I)
    return t.replace("_", " ").strip()


def kind_of(title: str) -> str:
    ext = title.rsplit(".", 1)[-1].lower() if "." in title else ""
    if ext in ("mp4", "mov", "m4v", "webm", "mkv", "avi", "wmv", "3gp"):
        return "video"
    if ext in ("png", "jpg", "jpeg", "gif", "webp"):
        return "image"
    return "file" if ext else "video"


def build(sources: list, refresh: bool = False) -> list:
    """sources: [{url, title}] → nhóm: [{title, url, items: [{id, title, kind}], error}]"""
    groups = []
    for src in sources:
        url, label = (src.get("url") or "").strip(), (src.get("title") or "").strip()
        if not url:
            continue
        try:
            typ, fid = parse_link(url)
        except DriveError as e:
            groups.append({"title": label or url, "url": url, "items": [], "error": str(e)})
            continue
        if typ == "file":
            groups.append({"title": label or "Video", "url": url, "single": True,
                           "items": [{"id": fid, "title": label or "Video", "kind": "video"}], "error": None})
            continue
        warn = None

        def walk(folder_id, prefix, depth):
            nonlocal warn
            entries, w = _folder(folder_id, refresh)
            warn = warn or w
            files = [e for e in entries if not e["folder"]]
            subs = [e for e in entries if e["folder"]]
            items = [{"id": e["id"], "title": clean_title(e["title"]), "kind": kind_of(e["title"])}
                     for e in sorted(files, key=lambda e: _natkey(e["title"]))]
            res = [(prefix, items)] if items or (depth == 0 and not subs) else []
            if depth < MAX_DEPTH:
                for s in sorted(subs, key=lambda e: _natkey(e["title"])):
                    res += walk(s["id"], f"{prefix} › {s['title']}" if prefix else s["title"], depth + 1)
            return res

        try:
            parts = walk(fid, label, 0)
        except DriveError as e:
            groups.append({"title": label or "Thư mục Drive", "url": url, "items": [], "error": str(e)})
            continue
        for i, (title, items) in enumerate(parts):
            groups.append({"title": title or "Video hướng dẫn", "url": url if i == 0 else None, "items": items,
                           "error": warn if i == 0 else None})
    return groups
