"""Đăng ký lịch rảnh theo tuần + tự xếp ca.

- Mỗi tuần (khoá = ngày thứ 2, VD "2026-11-23") CTV đăng ký các khung rảnh "thứ-ca" (VD "1-sang").
- Hạn đăng ký: 19:00 Chủ nhật trước tuần đó. 20:00 hệ thống tự xếp ca (bản nháp, CTV chưa thấy).
- Admin kiểm tra, sửa rồi duyệt → CTV thấy lịch + đẩy lên Google Sheet.

Thuật toán xếp (tham lam, công bằng):
  1. Mỗi ngày × nhóm ca (sáng / chiều / tối) có chỉ tiêu need_min–need_max và danh sách CTV đăng ký.
     Ca "tối gãy" (19–22h) được tính vào nhóm tối, chỉ dùng khi thiếu người ca tối đủ.
  2. Lượt 1 lấp đủ need_min, lượt 2 lấp tới need_max; ô khan hiếm (ít người đăng ký so với nhu cầu) xếp trước.
  3. Trong ô, ưu tiên người ít giờ nhất trong tuần → ít giờ nhất 4 tuần qua; không xếp trùng giờ.
  4. Ca tối: cố gắng có 1 người Monitor (người từng trực vị trí Monitor ca tối trong 90 ngày).
  5. Giữ nguyên các ca admin đã xếp tay trong tuần; chạy lại chỉ thay các ca tự xếp chưa duyệt.
"""
import hashlib
import json
from datetime import date, datetime, timedelta

from . import db

REG_DEADLINE = (19, 0)   # Chủ nhật 19:00
GEN_TIME = (20, 0)       # Chủ nhật 20:00
SOURCE = "auto"
MONITOR_POS = 2


def t2m(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def next_week(today: date | None = None) -> date:
    t = today or date.today()
    return monday(t) + timedelta(days=7)


def deadline(ws: date) -> datetime:
    return datetime.combine(ws - timedelta(days=1), datetime.min.time()).replace(hour=REG_DEADLINE[0], minute=REG_DEADLINE[1])


def gen_time(ws: date) -> datetime:
    return datetime.combine(ws - timedelta(days=1), datetime.min.time()).replace(hour=GEN_TIME[0], minute=GEN_TIME[1])


def is_week_key(key: str) -> bool:
    return len(key) == 10 and key[4] == "-" and key[7] == "-"


# ---------------------------------------------------------------- trạng thái tuần
def statuses(con) -> dict:
    return json.loads(db.get_setting(con, "week_status", "{}"))


def set_status(con, ws: str, **kv):
    st = statuses(con)
    st.setdefault(ws, {}).update(kv)
    db.set_setting(con, "week_status", json.dumps(st, ensure_ascii=False))


def draft_weeks(con) -> list[str]:
    """Tuần đã tự xếp nhưng chưa duyệt → CTV chưa được thấy."""
    return [k for k, v in statuses(con).items() if v.get("generated_at") and not v.get("approved_at")]


def hide_sql(con, col="s.date"):
    parts, args = [], []
    for k in draft_weeks(con):
        d0 = date.fromisoformat(k)
        parts.append(f" AND NOT ({col} BETWEEN ? AND ?)")
        args += [k, (d0 + timedelta(days=6)).isoformat()]
    return "".join(parts), args


def reg_open(con, key: str, now: datetime | None = None) -> bool:
    r = con.execute("SELECT open FROM reg_months WHERE ym=?", (key,)).fetchone()
    if r is not None:
        return bool(r[0])
    now = now or datetime.now()
    ws = date.fromisoformat(key)
    return now < deadline(ws) and ws <= now.date() + timedelta(days=21)


def week_regs(con, key: str) -> dict:
    """Đăng ký của tuần; CTV nào chưa đăng ký theo tuần thì dùng lịch rảnh theo tháng (cách cũ)
    của tháng chứa ngày thứ 2 — để giai đoạn chuyển đổi không bị mất dữ liệu đăng ký."""
    out = {}
    for r in con.execute("SELECT user_id, slots, status, updated_at FROM availability WHERE ym=?", (key,)).fetchall():
        out[r[0]] = {"slots": json.loads(r[1] or "{}"), "status": r[2], "updated_at": r[3], "source": "week"}
    for r in con.execute("SELECT user_id, slots, status, updated_at FROM availability WHERE ym=?", (key[:7],)).fetchall():
        if r[0] not in out and json.loads(r[1] or "{}"):
            out[r[0]] = {"slots": json.loads(r[1] or "{}"), "status": r[2], "updated_at": r[3], "source": "month"}
    return out


# ---------------------------------------------------------------- xếp ca
def group_of(code: str) -> str:
    c = code.lower()
    return "toi" if c.startswith("toi") else "chieu" if c.startswith("chieu") else "sang" if c.startswith("sang") else c


def generate(con, ws: date, actor: str = "Hệ thống") -> dict:
    we = ws + timedelta(days=6)
    key = ws.isoformat()
    shifts = {r["code"]: dict(r) for r in con.execute("SELECT * FROM shift_types")}
    mains = {g: shifts[g] for g in ("sang", "chieu", "toi") if g in shifts}
    users = {r["id"]: dict(r) for r in con.execute("SELECT id, username FROM users WHERE active=1")}
    regs = {uid: v["slots"] for uid, v in week_regs(con, key).items() if uid in users}

    removed = con.execute("DELETE FROM schedules WHERE date BETWEEN ? AND ? AND source=? AND approved_at IS NULL",
                          (key, we.isoformat(), SOURCE)).rowcount
    existing = [dict(r) for r in con.execute('SELECT * FROM schedules WHERE date BETWEEN ? AND ?', (key, we.isoformat()))]

    # lịch sử: giờ 4 tuần qua, vị trí quen thuộc, ai từng làm Monitor ca tối
    hist_hours, pos_count, monitor_ok = {}, {}, set()
    for r in con.execute('SELECT user_id, shift_code, start, "end", position_id, date FROM schedules WHERE date BETWEEN ? AND ?',
                         ((ws - timedelta(days=90)).isoformat(), (ws - timedelta(days=1)).isoformat())):
        g = group_of(r["shift_code"])
        if r["date"] >= (ws - timedelta(days=28)).isoformat():
            hist_hours[r["user_id"]] = hist_hours.get(r["user_id"], 0) + (t2m(r["end"]) - t2m(r["start"])) / 60
        pos_count.setdefault((r["user_id"], g), {}).setdefault(r["position_id"], 0)
        pos_count[(r["user_id"], g)][r["position_id"]] += 1
        if g == "toi" and r["position_id"] == MONITOR_POS:
            monitor_ok.add(r["user_id"])

    busy, week_hours = {}, {}

    def book(uid, d, a, b):
        busy.setdefault((uid, d), []).append((a, b))
        week_hours[uid] = week_hours.get(uid, 0) + (b - a) / 60

    def free(uid, d, a, b):
        return all(not (a < y and b > x) for x, y in busy.get((uid, d), []))

    cells = []
    for i in range(7):
        d = (ws + timedelta(days=i)).isoformat()
        dow = i + 1
        for g, main in mains.items():
            have = [e for e in existing if e["date"] == d and group_of(e["shift_code"]) == g]
            cands = []
            for uid, slots in regs.items():
                for k, v in slots.items():
                    kd, _, code = k.partition("-")
                    if kd == str(dow) and code in shifts and group_of(code) == g:
                        cands.append({"uid": uid, "code": code, "start": v.get("start") or shifts[code]["start"],
                                      "end": v.get("end") or shifts[code]["end"], "partial": code != g})
            cells.append({"date": d, "group": g, "lo": main["need_min"] or 0, "hi": max(main["need_min"] or 0, main["need_max"] or 0),
                          "have": have, "cands": cands, "new": []})
    for e in existing:
        book(e["user_id"], e["date"], t2m(e["start"]), t2m(e["end"]))

    def count(c):
        return len(c["have"]) + len(c["new"])

    def has_monitor(c):
        return any(e["position_id"] == MONITOR_POS for e in c["have"]) or any(n["position_id"] == MONITOR_POS for n in c["new"])

    def tie(uid, d):  # xáo trộn ổn định để không luôn ưu tiên cùng 1 người
        return hashlib.md5(f"{uid}-{d}".encode()).hexdigest()

    def pick(c):
        opts = [x for x in c["cands"] if x["uid"] not in {n["user_id"] for n in c["new"]} | {e["user_id"] for e in c["have"]}
                and free(x["uid"], c["date"], t2m(x["start"]), t2m(x["end"]))]
        if not opts:
            return None
        want_mon = c["group"] == "toi" and not has_monitor(c)
        opts.sort(key=lambda x: (x["partial"], not (want_mon and x["uid"] in monitor_ok),
                                 round(week_hours.get(x["uid"], 0), 2), round(hist_hours.get(x["uid"], 0), 2), tie(x["uid"], c["date"])))
        x = opts[0]
        if c["group"] == "toi":
            pos = MONITOR_POS if want_mon and x["uid"] in monitor_ok else 1
        else:
            pc = pos_count.get((x["uid"], c["group"]), {})
            pos = max(pc, key=pc.get) if pc else 1
        n = {"user_id": x["uid"], "code": x["code"], "start": x["start"], "end": x["end"], "position_id": pos}
        c["new"].append(n)
        book(x["uid"], c["date"], t2m(x["start"]), t2m(x["end"]))
        return n

    for target in ("lo", "hi"):
        while True:
            open_cells = [c for c in cells if count(c) < c[target]]
            progressed = False
            # ô khan hiếm trước: ít ứng viên còn trống so với số người còn thiếu
            open_cells.sort(key=lambda c: (len(c["cands"]) - count(c)) / max(1, c[target] - count(c)))
            for c in open_cells:
                if count(c) < c[target] and pick(c):
                    progressed = True
            if not progressed:
                break

    ts = db.now_str()
    added = 0
    for c in cells:
        for n in c["new"]:
            con.execute('INSERT INTO schedules(user_id, date, shift_code, start, "end", position_id, source) VALUES (?,?,?,?,?,?,?)',
                        (n["user_id"], c["date"], n["code"], n["start"], n["end"], n["position_id"], SOURCE))
            added += 1
    short = [{"date": c["date"], "group": c["group"], "have": count(c), "need": c["lo"], "registered": len(c["cands"])}
             for c in cells if count(c) < c["lo"]]
    no_monitor = [c["date"] for c in cells if c["group"] == "toi" and count(c) and not has_monitor(c)]
    report = {"week": key, "added": added, "replaced": removed, "kept_manual": len(existing), "registered_users": len(regs),
              "short": short, "no_monitor": no_monitor,
              "hours": {users[u]["username"]: round(h, 2) for u, h in sorted(week_hours.items(), key=lambda x: -x[1]) if u in users}}
    set_status(con, key, generated_at=ts, generated_by=actor, approved_at=None, approved_by=None,
               report={k: v for k, v in report.items() if k != "hours"})
    con.execute("INSERT INTO logs(user_id, actor, action, created_at) VALUES (NULL, ?, ?, ?)",
                (actor, f"Tự xếp ca tuần {ws.strftime('%d/%m')}: {added} ca, {len(short)} ô còn thiếu người", ts))
    return report


def tick(now: datetime | None = None):
    """Gọi định kỳ: từ 20:00 CN tới hết thứ 2, nếu tuần tới chưa được tự xếp thì xếp."""
    now = now or datetime.now()
    ws = monday(now.date()) + (timedelta(days=0) if now.weekday() == 0 else timedelta(days=7))
    if not (gen_time(ws) <= now < datetime.combine(ws + timedelta(days=1), datetime.min.time())):
        return None
    con = db.connect()
    try:
        st = statuses(con).get(ws.isoformat(), {})
        if st.get("generated_at") or st.get("approved_at"):
            return None
        # chưa ai đăng ký theo tuần (VD tuần xếp tay như trước) → không đụng tới, không ẩn lịch với CTV
        if not con.execute("SELECT 1 FROM availability WHERE ym=?", (ws.isoformat(),)).fetchone():
            return None
        rep = generate(con, ws)
        con.commit()
        return rep
    finally:
        con.close()
