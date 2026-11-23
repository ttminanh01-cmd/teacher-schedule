"""Document: các tab tài liệu do admin tự thêm (Tên tab + 1 link YouTube / Google Drive).

Link được nhận dạng và chuyển thành danh sách mục xem được ngay trên web:
- Drive thư mục  → mọi video/tệp trong thư mục (dùng lại crm_videos)
- Drive tệp      → trình phát /preview của Drive
- Google Docs / Sheets / Slides → bản /preview
- YouTube video, Shorts, playlist → trình phát nhúng
- YouTube kênh   → danh sách video của kênh (dùng lại yt_videos)
"""
import re
import secrets
from urllib.parse import parse_qs, urlparse

from . import crm_videos, yt_videos


class DocError(Exception):
    pass


def new_id() -> str:
    return secrets.token_hex(4)


def classify(url: str) -> tuple[str, str]:
    """→ (loại, id). Loại: drive_folder | drive_file | gdoc:<document|spreadsheets|presentation|forms>
    | yt_video | yt_playlist | yt_channel"""
    t = (url or "").strip()
    if not t:
        raise DocError("Chưa nhập link")
    m = re.search(r"docs\.google\.com/(document|spreadsheets|presentation|forms)/d/(?:e/)?([\w-]{10,})", t)
    if m:
        return f"gdoc:{m.group(1)}", m.group(2)
    if "drive.google.com" in t:
        try:
            typ, fid = crm_videos.parse_link(t)
        except crm_videos.DriveError as e:
            raise DocError(str(e))
        return f"drive_{typ}", fid
    if re.search(r"(youtube\.com|youtu\.be)", t):
        p = urlparse(t if "://" in t else "https://" + t)
        q = parse_qs(p.query)
        m = re.match(r"^/(?:shorts|embed|live)/([\w-]{11})", p.path)
        vid = (q.get("v") or [None])[0] or (m and m.group(1)) or \
            (p.netloc.endswith("youtu.be") and p.path.strip("/")[:11]) or None
        if vid and re.fullmatch(r"[\w-]{11}", vid):
            return "yt_video", vid
        if q.get("list"):
            return "yt_playlist", q["list"][0]
        try:
            return "yt_channel", yt_videos.normalize(t)
        except yt_videos.YTError:
            pass
        raise DocError("Link YouTube không hợp lệ (cần link video, playlist hoặc kênh)")
    raise DocError("Chỉ hỗ trợ link YouTube hoặc Google Drive / Docs")


def _drive_item(fid, title, kind="video"):
    return {"id": fid, "title": title, "kind": kind,
            "embed": f"https://drive.google.com/file/d/{fid}/preview",
            "open": f"https://drive.google.com/file/d/{fid}/view"}


def _yt_item(vid, title, url=None):
    return {"id": vid, "title": title, "kind": "video",
            "embed": f"https://www.youtube-nocookie.com/embed/{vid}?rel=0",
            "open": url or f"https://www.youtube.com/watch?v={vid}", "copy": True}


def resolve(tab: dict, refresh: bool = False) -> dict:
    """tab {id, name, url} → {groups: [{title, items: [{id, title, kind, embed, open, copy?}]}], error, warning}"""
    name, url = tab.get("name") or "Tài liệu", tab.get("url") or ""
    try:
        typ, key = classify(url)
    except DocError as e:
        return {"groups": [], "error": str(e)}
    if typ.startswith("gdoc:"):
        kind = typ[5:]
        base = f"https://docs.google.com/{kind}/d/{key}"
        embed = f"{base}/viewform?embedded=true" if kind == "forms" else f"{base}/preview"
        return {"groups": [{"title": name, "items": [
            {"id": key, "title": name, "kind": "doc", "embed": embed, "open": url}]}], "single": True}
    if typ == "drive_file":
        return {"groups": [{"title": name, "items": [_drive_item(key, name)]}], "single": True}
    if typ == "yt_video":
        return {"groups": [{"title": name, "items": [_yt_item(key, name, url)]}], "single": True}
    if typ == "yt_playlist":
        return {"groups": [{"title": name, "items": [
            {"id": key, "title": name, "kind": "video", "copy": True, "open": url,
             "embed": f"https://www.youtube-nocookie.com/embed/videoseries?list={key}&rel=0"}]}], "single": True}
    if typ == "drive_folder":
        groups = crm_videos.build([{"url": url, "title": ""}], refresh=refresh)
        err = next((g["error"] for g in groups if g.get("error")), None)
        out = [{"title": g["title"] if g["title"] != "Video hướng dẫn" else "",
                "items": [_drive_item(it["id"], it["title"], it["kind"]) for it in g["items"]]} for g in groups]
        out = [g for g in out if g["items"]]
        return {"groups": out, "error": err if not out else None, "warning": err if out else None}
    # yt_channel
    try:
        data = yt_videos.get(key, refresh=refresh)
    except yt_videos.YTError as e:
        return {"groups": [], "error": str(e)}
    groups = [{"title": g["title"], "items": [_yt_item(it["id"], it.get("short") or it["title"], it.get("url"))
                                               for it in g["items"]]} for g in data.get("groups", [])]
    return {"groups": groups, "warning": data.get("warning")}


def clean(tabs: list) -> list:
    """Kiểm tra & chuẩn hoá danh sách tab admin gửi lên."""
    out, seen = [], set()
    for t in tabs or []:
        name = str(t.get("name") or "").strip()[:60]
        url = str(t.get("url") or "").strip()[:500]
        if not name and not url:
            continue
        if not name:
            raise DocError("Tab chưa có tên")
        try:
            classify(url)
        except DocError as e:
            raise DocError(f"Tab “{name}”: {e}")
        tid = str(t.get("id") or "").strip()[:16]
        if not re.fullmatch(r"[0-9a-f]{8}", tid) or tid in seen:
            tid = new_id()
        seen.add(tid)
        out.append({"id": tid, "name": name, "url": url})
    return out
