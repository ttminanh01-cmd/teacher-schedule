"""Video hướng dẫn PH thao tác: lấy danh sách video từ 1 kênh YouTube công khai (không cần API key).

- RSS của kênh (youtube.com/feeds/videos.xml?channel_id=…) — ổn định, tối đa 15 video mới nhất.
- Trang /videos của kênh (đọc ytInitialData) — bổ sung khi kênh có nhiều hơn 15 video.
Gộp 2 nguồn theo videoId; nguồn nào lỗi thì dùng nguồn còn lại. Cache 10 phút.
Nhóm theo nhãn trong ngoặc vuông ở tiêu đề, VD "[3] - [ICANCONNECT] - Hướng dẫn xin nghỉ học" → nhóm ICANCONNECT.
"""
import html
import json
import re
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET

DEFAULT_CHANNEL = "https://www.youtube.com/@CustomercareICC"
CACHE_TTL = 600
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
      "Accept-Language": "vi,en;q=0.8"}

_lock = threading.Lock()
_cache: dict = {}  # channel url -> (ts, data)


class YTError(Exception):
    pass


def normalize(url: str) -> str:
    """Nhận link kênh dạng @handle, /channel/UC…, /c/…, /user/… → link gốc của kênh."""
    t = (url or "").strip().rstrip("/")
    if re.fullmatch(r"@[\w.-]+", t):
        t = "https://www.youtube.com/" + t
    m = re.match(r"^(?:https?://)?(?:www\.|m\.)?youtube\.com/(@[\w.-]+|channel/UC[\w-]{22}|c/[\w.-]+|user/[\w.-]+)", t)
    if not m:
        raise YTError("Link kênh YouTube không hợp lệ (VD: https://www.youtube.com/@TenKenh)")
    return "https://www.youtube.com/" + m.group(1)


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def _from_page(channel: str) -> tuple[str | None, str, list]:
    """→ (channel_id, tên kênh, [video]) từ trang /videos."""
    body = _get(channel + "/videos")
    cid = (re.search(r'"externalId":"(UC[\w-]{22})"', body) or re.search(r'channel_id=(UC[\w-]{22})', body))
    name = re.search(r'<meta property="og:title" content="([^"]*)"', body)
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", body, re.S)
    out = []
    if m:
        def walk(o):
            if isinstance(o, dict):
                v = o.get("lockupViewModel")
                if v and v.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO" and v.get("contentId"):
                    try:
                        title = v["metadata"]["lockupMetadataViewModel"]["title"]["content"]
                    except (KeyError, TypeError):
                        title = ""
                    out.append({"id": v["contentId"], "title": title})
                r = o.get("videoRenderer") or o.get("gridVideoRenderer")
                if r and r.get("videoId"):
                    t = r.get("title", {})
                    out.append({"id": r["videoId"], "title": "".join(x.get("text", "") for x in t.get("runs", [])) or t.get("simpleText", "")})
                for x in o.values():
                    walk(x)
            elif isinstance(o, list):
                for x in o:
                    walk(x)
        try:
            walk(json.loads(m.group(1)))
        except ValueError:
            pass
    return (cid.group(1) if cid else None), (html.unescape(name.group(1)) if name else ""), out


def _from_rss(cid: str) -> list:
    root = ET.fromstring(_get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    out = []
    for e in root.findall("a:entry", ns):
        vid = e.findtext("yt:videoId", "", ns)
        if vid:
            out.append({"id": vid, "title": e.findtext("a:title", "", ns), "published": e.findtext("a:published", "", ns)[:10]})
    return out


def _natkey(s: str):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", s)]


def _group(title: str) -> tuple[str, str]:
    """"[3] - [ICANCONNECT] - Hướng dẫn xin nghỉ học" → ("ICANCONNECT", "Hướng dẫn xin nghỉ học")."""
    tags = re.findall(r"\[([^\]]+)\]", title)
    group = next((t.strip() for t in tags if not t.strip().isdigit()), "Video hướng dẫn")
    short = re.sub(r"^(\s*\[[^\]]*\]\s*-?\s*)+", "", title).strip(" -") or title
    return group, short


def fetch(channel: str) -> dict:
    channel = normalize(channel)
    errors, cid, name, page = [], None, "", []
    try:
        cid, name, page = _from_page(channel)
    except Exception as e:  # noqa: BLE001 — trang kênh lỗi thì vẫn thử RSS
        errors.append(f"trang kênh: {e.__class__.__name__}")
    m = re.search(r"/channel/(UC[\w-]{22})", channel)
    cid = cid or (m.group(1) if m else None)
    rss = []
    if cid:
        try:
            rss = _from_rss(cid)
        except Exception as e:  # noqa: BLE001
            errors.append(f"RSS: {e.__class__.__name__}")
    vids, seen = [], {}
    for v in rss + page:
        if v["id"] in seen:
            seen[v["id"]].setdefault("published", v.get("published"))
            if not seen[v["id"]]["title"]:
                seen[v["id"]]["title"] = v["title"]
            continue
        seen[v["id"]] = dict(v)
        vids.append(seen[v["id"]])
    if not vids:
        raise YTError("Không đọc được danh sách video của kênh YouTube" + (f" ({', '.join(errors)})" if errors else ""))
    groups: dict = {}
    for v in vids:
        g, short = _group(v["title"])
        groups.setdefault(g, []).append({"id": v["id"], "title": v["title"], "short": short,
                                         "published": v.get("published") or "", "url": f"https://youtu.be/{v['id']}"})
    out = [{"title": g, "items": sorted(items, key=lambda x: _natkey(x["title"]))} for g, items in groups.items()]
    out.sort(key=lambda g: -len(g["items"]))  # nhóm nhiều video lên trước
    return {"channel": channel, "name": name, "groups": out}


def get(channel: str, refresh: bool = False) -> dict:
    key = normalize(channel)
    with _lock:
        hit = _cache.get(key)
    if hit and not refresh and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    try:
        data = fetch(key)
    except YTError as e:
        if hit:  # lỗi tạm thời → dùng bản cũ
            return {**hit[1], "warning": str(e)}
        raise
    with _lock:
        _cache[key] = (time.time(), data)
    return data
