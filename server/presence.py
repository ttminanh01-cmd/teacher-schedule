"""Ai đang mở web: mỗi tab gửi tín hiệu 1 phút/lần (+ khi đổi mục / ẩn hiện tab / đóng tab).

Chỉ giữ trong bộ nhớ (server khởi động lại thì mất, ~1 phút sau tự có lại) và tra token → người dùng
từ bộ nhớ đệm 30 phút, nên tín hiệu không đánh thức DB (Neon được ngủ khi không ai thao tác).
"""
import threading
import time

from . import db

ONLINE_SEC = 150        # quá 2,5 phút không có tín hiệu → coi như đã rời
KEEP_SEC = 24 * 3600    # nhớ "rời lúc" trong 24 giờ
TOKEN_TTL = 30 * 60

_lock = threading.Lock()
_tabs: dict = {}        # tab id → {uid, at, page, portal, visible}
_users: dict = {}       # uid → {name, username, role, since, last}
_tok: dict = {}         # token → (user | None, lúc tra)


def user_for(token: str) -> dict | None:
    if not token:
        return None
    hit = _tok.get(token)
    if hit and time.time() - hit[1] < TOKEN_TTL:
        return hit[0]
    con = db.connect()
    try:
        r = con.execute("SELECT u.id, u.name, u.username, u.role FROM sessions s JOIN users u ON u.id=s.user_id "
                        "WHERE s.token=? AND s.expires>? AND u.active=1 AND s.viewer_id IS NULL", (token, db.now_str())).fetchone()
    finally:
        con.close()
    u = {"id": r[0], "name": r[1], "username": r[2], "role": r[3]} if r else None
    _tok[token] = (u, time.time())
    return u


def forget(token: str):
    _tok.pop(token, None)


def beat(u: dict, tab: str, page: str, portal: str, visible: bool, bye: bool = False):
    now = time.time()
    tab = str(tab or "")[:40] or f"u{u['id']}"
    with _lock:
        info = _users.get(u["id"])
        online_before = info and any(t["uid"] == u["id"] and now - t["at"] < ONLINE_SEC for t in _tabs.values())
        if not info:
            info = _users[u["id"]] = {}
        info.update(name=u["name"], username=u["username"], role=u["role"], last=now)
        if not online_before:
            info["since"] = now
        if bye:
            _tabs.pop(tab, None)
        else:
            _tabs[tab] = {"uid": u["id"], "at": now, "page": str(page or "")[:60],
                          "portal": "admin" if portal == "admin" else "ctv", "visible": bool(visible)}
        for k in [k for k, t in _tabs.items() if now - t["at"] > ONLINE_SEC]:
            del _tabs[k]
        for k in [k for k, v in _users.items() if now - v["last"] > KEEP_SEC]:
            del _users[k]
        if len(_tok) > 5000:
            _tok.clear()


def snapshot() -> dict:
    now = time.time()
    online, left = [], []
    with _lock:
        for uid, v in _users.items():
            tabs = [t for t in _tabs.values() if t["uid"] == uid and now - t["at"] < ONLINE_SEC]
            base = {"id": uid, "name": v["name"], "username": v["username"], "role": v["role"]}
            if tabs:
                t = max(tabs, key=lambda t: (t["visible"], t["at"]))  # tab đang xem, không thì tab mới nhất
                online.append({**base, "page": t["page"], "portal": t["portal"], "visible": any(x["visible"] for x in tabs),
                               "tabs": len(tabs), "since": int(now - v.get("since", now)), "ago": int(now - max(x["at"] for x in tabs))})
            else:
                left.append({**base, "ago": int(now - v["last"])})
    online.sort(key=lambda x: (not x["visible"], x["name"].lower()))
    left.sort(key=lambda x: x["ago"])
    return {"online": online, "left": left[:30]}
