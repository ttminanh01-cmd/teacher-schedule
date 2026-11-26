"""Cổng CTV — API (FastAPI; SQLite khi chạy máy cá nhân, Postgres khi có DATABASE_URL).

Chạy:  python -m uvicorn server.app:app --reload --port 8000
"""
import json
import re
import os
import secrets
import threading
import time
from datetime import date, datetime, timedelta

from fastapi.middleware.gzip import GZipMiddleware
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import autoschedule, crm_videos, db, docs, handbook, ican, milo, notify, sheet_sync, yt_videos
from .db import dumps, now_str, row, rows

STATIC = os.path.join(os.path.dirname(__file__), "..", "static")
app = FastAPI(title="Cổng CTV")
app.add_middleware(GZipMiddleware, minimum_size=2000)  # bảng Tài liệu vài trăm dòng → nén cho tải nhanh
db.init_db()


# ---------------------------------------------------------------- helpers
def get_con():
    con = db.connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


def err(msg: str, code: int = 400):
    raise HTTPException(code, msg)


def t2m(t: str) -> int:
    h, m = map(int, t.split(":")[:2])
    return h * 60 + m


def log(con, user, action: str):
    con.execute("INSERT INTO logs(user_id, actor, action, created_at) VALUES (?,?,?,?)",
                (user["id"] if user else None, user["name"] if user else "Hệ thống", action, now_str()))


def month_range(ym: str):
    y, m = map(int, ym.split("-"))
    first = date(y, m, 1)
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return first.isoformat(), (nxt - timedelta(days=1)).isoformat()


def current_user(authorization: str = Header(default=""), con=Depends(get_con)):
    token = authorization.removeprefix("Bearer ").strip()
    u = row(con.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.active=1",
        (token, now_str())))
    if not u:
        err("Phiên đăng nhập đã hết hạn", 401)
    return u


def admin_user(u=Depends(current_user)):
    if u["role"] != "admin":
        err("Bạn không có quyền quản trị", 403)
    return u


SCHED_SQL = """
SELECT s.id, s.user_id, s.date, s.shift_code, s.start, s."end", s.position_id,
       u.username, u.name, u.team_id, p.name AS position,
       COALESCE(NULLIF(u.hourly_rate, 0), p.hourly_rate) AS hourly_rate, t.name AS team,
       st.name AS shift_name, s.note, s.plan, s.approved_at, s.approved_by, s.source
FROM schedules s
JOIN users u ON u.id = s.user_id
LEFT JOIN positions p ON p.id = s.position_id
LEFT JOIN teams t ON t.id = p.team_id
LEFT JOIN shift_types st ON st.code = s.shift_code
"""


def public_user(u):
    return {k: u[k] for k in ("id", "username", "name", "role", "team_id", "must_change_pw") if k in u.keys()}


# ---------------------------------------------------------------- auth
@app.post("/api/login")
def login(body: dict = Body(...), con=Depends(get_con)):
    name = body.get("username", "").strip()
    u = row(con.execute("SELECT * FROM users WHERE username=?", (name,)))
    if not u and name and "." not in name:  # CTV gõ "haott" thay vì "ctv.haott"
        u = row(con.execute("SELECT * FROM users WHERE username=?", ("ctv." + name,)))
    if not u or not db.check_pw(body.get("password", ""), u["password_hash"]):
        err("Sai tên đăng nhập hoặc mật khẩu", 401)
    if not u["active"]:
        err("Tài khoản đã bị khoá", 403)
    token = secrets.token_urlsafe(32)
    exp = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
    con.execute("INSERT INTO sessions(token, user_id, expires) VALUES (?,?,?)", (token, u["id"], exp))
    log(con, u, "Đăng nhập")
    return {"token": token, "user": public_user(u)}


@app.post("/api/logout")
def logout(authorization: str = Header(default=""), u=Depends(current_user), con=Depends(get_con)):
    con.execute("DELETE FROM sessions WHERE token=?", (authorization.removeprefix("Bearer ").strip(),))
    log(con, u, "Đăng xuất")
    return {"ok": True}


@app.get("/api/me")
def me(u=Depends(current_user)):
    return public_user(u)


@app.post("/api/me/password")
def change_password(body: dict = Body(...), u=Depends(current_user), con=Depends(get_con)):
    if not db.check_pw(body.get("old", ""), u["password_hash"]):
        err("Mật khẩu hiện tại không đúng")
    new = body.get("new", "")
    if len(new) < 6:
        err("Mật khẩu mới tối thiểu 6 ký tự")
    if new in ("123456", "admin123", "12345678") or new == body.get("old"):
        err("Vui lòng chọn mật khẩu khác (không dùng mật khẩu mặc định / mật khẩu cũ)")
    con.execute("UPDATE users SET password_hash=?, must_change_pw=0 WHERE id=?", (db.hash_pw(new), u["id"]))
    log(con, u, "Đổi mật khẩu")
    return {"ok": True}


@app.get("/api/meta")
def meta(u=Depends(current_user), con=Depends(get_con)):
    return {
        "teams": rows(con.execute("SELECT * FROM teams ORDER BY id")),
        "positions": rows(con.execute("SELECT * FROM positions ORDER BY team_id, id")),
        "shifts": rows(con.execute("SELECT * FROM shift_types ORDER BY sort")),
        "reg_mode": autoschedule.reg_mode(con),
        "now": now_str(),
    }


@app.get("/api/notifications")
def notifications(u=Depends(current_user), con=Depends(get_con)):
    return rows(con.execute("""SELECT n.*, (r.user_id IS NULL) AS unread FROM notifications n
        LEFT JOIN notification_reads r ON r.notification_id=n.id AND r.user_id=?
        ORDER BY n.id DESC LIMIT 30""", (u["id"],)))


@app.post("/api/notifications/read")
def notifications_read(u=Depends(current_user), con=Depends(get_con)):
    con.execute("INSERT OR IGNORE INTO notification_reads SELECT ?, id FROM notifications", (u["id"],))
    return {"ok": True}



# ================================================================ CTV
def shift_ended(s, today, now_m) -> bool:
    d = today.isoformat()
    return s["date"] < d or (s["date"] == d and t2m(s["end"]) <= now_m)


@app.get("/api/ctv/dashboard")
def ctv_dashboard(u=Depends(current_user), con=Depends(get_con)):
    today = date.today()
    f, l = month_range(today.strftime("%Y-%m"))
    hide, hargs = autoschedule.hide_sql(con)
    sched = rows(con.execute(SCHED_SQL + " WHERE s.user_id=? AND s.date BETWEEN ? AND ?" + hide + " ORDER BY s.date, s.start",
                             (u["id"], f, l, *hargs)))
    now = datetime.now()
    now_m = now.hour * 60 + now.minute
    # không có check-in: ca đã kết thúc theo lịch được tính là đã làm
    done = [s for s in sched if s["approved_at"]]
    waiting = [s for s in sched if not s["approved_at"] and shift_ended(s, today, now_m)]
    minutes = sum(t2m(s["end"]) - t2m(s["start"]) for s in done)
    weeks = {}
    for s in done:
        d = date.fromisoformat(s["date"])
        monday = d - timedelta(days=d.weekday())
        label = f"{monday.strftime('%d/%m')}–{(monday + timedelta(days=6)).strftime('%d/%m')}"
        weeks[label] = weeks.get(label, 0) + (t2m(s["end"]) - t2m(s["start"])) / 60
    upcoming = [s for s in sched if not shift_ended(s, today, now_m)][:5]
    return {
        "hours": round(minutes / 60, 1), "shifts": len(sched), "done": len(done), "waiting": len(waiting),
        "planned_hours": round(sum(t2m(s["end"]) - t2m(s["start"]) for s in sched) / 60, 1),
        "weeks": [{"label": k, "hours": round(v, 1)} for k, v in weeks.items()],
        "upcoming": upcoming,
    }


# ----- lịch rảnh
def reg_open(con, ym: str) -> bool:
    if autoschedule.is_week_key(ym):  # đăng ký theo tuần: tự đóng 19:00 CN
        return autoschedule.reg_open(con, ym)
    r = row(con.execute("SELECT open FROM reg_months WHERE ym=?", (ym,)))
    if r is not None:
        return bool(r["open"])
    return autoschedule.month_reg_open(ym)  # mặc định: tự chốt 19:00 ngày 29 của tháng trước


@app.get("/api/ctv/availability")
def get_availability(ym: str, u=Depends(current_user), con=Depends(get_con)):
    r = row(con.execute("SELECT * FROM availability WHERE user_id=? AND ym=?", (u["id"], ym)))
    # số CTV khác đã đăng ký từng khung (đã chốt + nháp) để CTV biết ca nào còn thiếu người
    counts = {}
    if autoschedule.is_week_key(ym):
        others = [v["slots"] for uid, v in autoschedule.week_regs(con, ym).items() if uid != u["id"]]
    else:
        others = [json.loads(s or "{}") for (s,) in con.execute("SELECT slots FROM availability WHERE ym=? AND user_id<>?", (ym, u["id"]))]
    for slots in others:
        for k in slots:
            counts[k] = counts.get(k, 0) + 1
        # theo nhóm ca (VD Tối = Ca full + Ca gãy), mỗi CTV tính 1 lần
        for gk in {f"g:{k.partition('-')[0]}-{autoschedule.group_of(k.partition('-')[2])}" for k in slots}:
            counts[gk] = counts.get(gk, 0) + 1
    return {"ym": ym, "open": reg_open(con, ym), "status": r["status"] if r else "empty",
            "deadline": None if autoschedule.is_week_key(ym) else autoschedule.month_deadline(ym).strftime("%Y-%m-%d %H:%M"),
            "slots": json.loads(r["slots"]) if r else {}, "updated_at": r["updated_at"] if r else None, "counts": counts}


@app.put("/api/ctv/availability")
def save_availability(body: dict = Body(...), u=Depends(current_user), con=Depends(get_con)):
    ym, slots, submit = body["ym"], body.get("slots", {}), bool(body.get("submit"))
    mode = autoschedule.reg_mode(con)
    if autoschedule.is_week_key(ym) != (mode == "week"):
        err(f"Quản lý đã chuyển sang đăng ký theo {'tuần' if mode == 'week' else 'tháng'}. Bạn tải lại trang rồi đăng ký lại nhé.")
    if not reg_open(con, ym):
        err(f"{'Tuần' if mode == 'week' else 'Tháng'} này đã đóng đăng ký")
    cur = row(con.execute("SELECT status FROM availability WHERE user_id=? AND ym=?", (u["id"], ym)))
    if cur and cur["status"] == "submitted" and not autoschedule.is_week_key(ym):  # tuần: sửa được tới hạn chót
        err("Lịch tháng này đã chốt. Liên hệ quản lý nếu cần sửa.")
    for key, v in slots.items():
        if t2m(v["end"]) - t2m(v["start"]) < 120:
            err("Mỗi ca rảnh tối thiểu 2 giờ")
    if submit and not slots:
        err("Bạn chưa chọn ca rảnh nào")
    con.execute("INSERT OR REPLACE INTO availability(user_id, ym, slots, status, updated_at) VALUES (?,?,?,?,?)",
                (u["id"], ym, dumps(slots), "submitted" if submit else "draft", now_str()))
    log(con, u, f"{'Gửi' if submit else 'Lưu nháp'} đăng ký lịch rảnh {'tuần ' + ym if autoschedule.is_week_key(ym) else 'tháng ' + ym}")
    return {"ok": True}


# ----- lịch làm
@app.get("/api/ctv/schedule")
def my_schedule(start: str, end: str, u=Depends(current_user), con=Depends(get_con)):
    hide, hargs = autoschedule.hide_sql(con)
    return rows(con.execute(SCHED_SQL + " WHERE s.user_id=? AND s.date BETWEEN ? AND ?" + hide + " ORDER BY s.date, s.start",
                            (u["id"], start, end, *hargs)))


def own_schedule(con, u, sid: int):
    s = row(con.execute(SCHED_SQL + " WHERE s.id=?", (sid,)))
    if not s or s["user_id"] != u["id"]:
        err("Không tìm thấy ca", 404)
    return s


@app.get("/api/team-week")
def team_week(start: str, u=Depends(current_user), con=Depends(get_con)):
    """Lịch cả team trong 7 ngày bắt đầu từ `start` (tuần nháp chưa duyệt vẫn ẩn với CTV)."""
    try:
        d0 = date.fromisoformat(start)
    except ValueError:
        err("Ngày không hợp lệ")
    hide, hargs = autoschedule.hide_sql(con)
    return rows(con.execute(SCHED_SQL + " WHERE s.date BETWEEN ? AND ?" + hide + " ORDER BY s.date, s.start, u.username",
                            (d0.isoformat(), (d0 + timedelta(days=6)).isoformat(), *hargs)))


@app.get("/api/team-day")
def team_day(day: str, team_id: int | None = None, u=Depends(current_user), con=Depends(get_con)):
    hide, hargs = autoschedule.hide_sql(con)
    q, args = SCHED_SQL + " WHERE s.date=?" + hide, [day, *hargs]
    if team_id:
        q += " AND p.team_id=?"
        args.append(team_id)
    return rows(con.execute(q + " ORDER BY s.start, p.id, u.username", args))


# ----- đổi ca
SWAP_SQL = """
SELECT w.*, s.date, s.start, s."end", s.shift_code, p.name AS position,
       fu.username AS from_username, fu.name AS from_name, tu.username AS to_username, tu.name AS to_name,
       s2.start AS swap_start, s2."end" AS swap_end, p2.name AS swap_position
FROM swaps w JOIN schedules s ON s.id=w.schedule_id
LEFT JOIN positions p ON p.id=s.position_id
LEFT JOIN schedules s2 ON s2.id=w.swap_schedule_id
LEFT JOIN positions p2 ON p2.id=s2.position_id
JOIN users fu ON fu.id=w.from_user JOIN users tu ON tu.id=w.to_user
"""


@app.get("/api/ctv/swaps")
def my_swaps(u=Depends(current_user), con=Depends(get_con)):
    return rows(con.execute(SWAP_SQL + " WHERE w.from_user=? OR w.to_user=? ORDER BY w.id DESC", (u["id"], u["id"])))


def _overlap(a, b):
    return a["start"] < b["end"] and b["start"] < a["end"]


def _in_pending_swap(con, sched_id: int) -> bool:
    return bool(con.execute("SELECT 1 FROM swaps WHERE status='pending' AND (schedule_id=? OR swap_schedule_id=?)",
                            (sched_id, sched_id)).fetchone())


def swap_problem(con, s, to_user: int, t=None, from_name="Bạn", to_name="Người nhận"):
    """Lý do không đổi được (None = hợp lệ). s = ca của người xin; t = ca của người nhận khi đổi chéo (None = làm thay)."""
    day = rows(con.execute(SCHED_SQL + " WHERE s.date=? AND s.user_id IN (?,?)", (s["date"], s["user_id"], to_user)))
    if any(x["user_id"] == to_user and (not t or x["id"] != t["id"]) and _overlap(x, s) for x in day):
        return f"{to_name} đã có ca khác trùng giờ"
    if t:
        if t["approved_at"]:
            return f"Ca của {to_name} đã được chấm công"
        if any(x["user_id"] == s["user_id"] and x["id"] != s["id"] and _overlap(x, t) for x in day):
            return f"{from_name} đã có ca khác trùng giờ với ca nhận về"
    return None


@app.get("/api/ctv/swap-candidates")
def swap_candidates(schedule_id: int, u=Depends(current_user), con=Depends(get_con)):
    """Người làm thay (rảnh khung giờ này) + người có ca cùng ngày để đổi chéo (VD ca full <-> ca gãy)."""
    s = own_schedule(con, u, schedule_id)
    cands = rows(con.execute("SELECT id, username, name FROM users WHERE role='ctv' AND active=1 AND id<>? ORDER BY username",
                             (u["id"],)))
    day = {}
    for x in rows(con.execute(SCHED_SQL + " WHERE s.date=? ORDER BY s.start", (s["date"],))):
        day.setdefault(x["user_id"], []).append(x)
    mine = [x for x in day.get(u["id"], []) if x["id"] != s["id"]]
    pending = {r[0] for r in con.execute("SELECT schedule_id FROM swaps WHERE status='pending'")} | \
              {r[0] for r in con.execute("SELECT swap_schedule_id FROM swaps WHERE status='pending' AND swap_schedule_id IS NOT NULL")}
    out = []
    for c in cands:
        theirs = day.get(c["id"], [])
        if not any(_overlap(x, s) for x in theirs):
            out.append({**c, "swap_schedule_id": None})
        for t in theirs:
            if (t["start"], t["end"], t["position_id"]) == (s["start"], s["end"], s["position_id"]):
                continue  # ca y hệt, đổi cũng như không
            if t["approved_at"] or t["id"] in pending:
                continue
            if any(_overlap(x, s) for x in theirs if x["id"] != t["id"]) or any(_overlap(x, t) for x in mine):
                continue
            out.append({**c, "swap_schedule_id": t["id"], "start": t["start"], "end": t["end"],
                        "shift_name": t["shift_name"], "position": t["position"]})
    return out


@app.post("/api/ctv/swaps")
def create_swap(body: dict = Body(...), u=Depends(current_user), con=Depends(get_con)):
    s = own_schedule(con, u, int(body["schedule_id"]))
    if s["date"] < date.today().isoformat() or s["approved_at"]:
        err("Không thể đổi ca đã qua hoặc đã chấm công")
    if _in_pending_swap(con, s["id"]):
        err("Ca này đã có phiếu đang chờ duyệt")
    to = row(con.execute("SELECT * FROM users WHERE id=? AND role='ctv' AND active=1", (body.get("to_user"),)))
    if not to or to["id"] == u["id"]:
        err("Vui lòng chọn người làm thay")
    t = None
    if body.get("swap_schedule_id"):
        t = row(con.execute(SCHED_SQL + " WHERE s.id=?", (int(body["swap_schedule_id"]),)))
        if not t or t["user_id"] != to["id"] or t["date"] != s["date"]:
            err("Không tìm thấy ca muốn đổi")
        if _in_pending_swap(con, t["id"]):
            err(f"Ca của {to['username']} đã có phiếu đang chờ duyệt")
    p = swap_problem(con, s, to["id"], t, "Bạn", to["username"])
    if p:
        err(p)
    reason = body.get("reason", "").strip()
    con.execute("INSERT INTO swaps(schedule_id, from_user, to_user, reason, created_at, swap_schedule_id) VALUES (?,?,?,?,?,?)",
                (s["id"], u["id"], to["id"], reason, now_str(), t["id"] if t else None))
    sw_id = con.execute("SELECT id FROM swaps WHERE schedule_id=? AND status='pending'", (s["id"],)).fetchone()[0]
    log(con, u, f"Gửi phiếu đổi ca {s['date']} ({s['start']}-{s['end']}) cho {to['username']}"
                + (f", nhận lại ca {t['start']}-{t['end']}" if t else ""))
    d = date.fromisoformat(s["date"])
    dow = "CN" if d.weekday() == 6 else f"T{d.weekday() + 2}"
    e = notify.esc
    notify.send_async("\n".join(filter(None, [
        "🔄 <b>Phiếu đổi ca mới</b>",
        f"<b>{e(u['name'])}</b> ({e(u['username'])}) → <b>{e(to['name'])}</b> ({e(to['username'])})",
        f"Ca: {dow} {d:%d/%m/%Y}, {e(s['start'])}–{e(s['end'])}" + (f" · {e(s['position'])}" if s["position"] else ""),
        (f"🔁 Đổi chéo: {e(u['username'])} nhận lại ca {e(t['start'])}–{e(t['end'])}"
         + (f" · {e(t['position'])}" if t["position"] else "") + f" của {e(to['username'])}") if t else "",
        f"Lý do: {e(reason)}" if reason else "",
        f"Web: {notify.PUBLIC_URL}/admin#swaps",
    ])), buttons=[[{"text": "✅ Duyệt", "callback_data": f"sw:{sw_id}:approve"},
                   {"text": "❌ Từ chối", "callback_data": f"sw:{sw_id}:reject"}]])
    return {"ok": True}


@app.delete("/api/ctv/swaps/{sid}")
def cancel_swap(sid: int, u=Depends(current_user), con=Depends(get_con)):
    n = con.execute("DELETE FROM swaps WHERE id=? AND from_user=? AND status='pending'", (sid, u["id"])).rowcount
    if not n:
        err("Không thể huỷ phiếu này")
    log(con, u, f"Huỷ phiếu đổi ca #{sid}")
    return {"ok": True}


# ----- lương
def compute_salary(con, user_id: int, ym: str) -> dict:
    f, l = month_range(ym)
    sched = rows(con.execute(SCHED_SQL + " WHERE s.user_id=? AND s.date BETWEEN ? AND ? AND s.approved_at IS NOT NULL"
                             " ORDER BY s.date, s.start", (user_id, f, l)))
    base, minutes = 0, 0
    for s in sched:
        mins = t2m(s["end"]) - t2m(s["start"])
        minutes += mins
        base += round(mins / 60 * (s["hourly_rate"] or 0))
    adj = row(con.execute("SELECT * FROM salaries WHERE user_id=? AND ym=?", (user_id, ym))) or {}
    bonus, deduction = adj.get("bonus", 0), adj.get("deduction", 0)
    qc = rows(con.execute("SELECT * FROM qc_errors WHERE user_id=? AND ym=? ORDER BY date", (user_id, ym)))
    qc_fine = sum(e["amount"] for e in qc)
    return {"ym": ym, "shifts": len(sched), "hours": round(minutes / 60, 2), "base": base,
            "qc_fine": qc_fine, "qc_count": len(qc), "qc": qc,
            "bonus": bonus, "deduction": deduction, "note": adj.get("note", ""),
            "total": base + bonus - qc_fine - deduction, "rows": sched}


@app.get("/api/ctv/salary/months")
def salary_months(u=Depends(current_user), con=Depends(get_con)):
    return [r["ym"] for r in con.execute("SELECT ym FROM salary_months WHERE published=1 ORDER BY ym DESC")]


@app.get("/api/ctv/salary")
def my_salary(ym: str, u=Depends(current_user), con=Depends(get_con)):
    if not con.execute("SELECT 1 FROM salary_months WHERE ym=? AND published=1", (ym,)).fetchone():
        err("Bảng lương tháng này chưa được công bố")
    return compute_salary(con, u["id"], ym)


@app.get("/api/ctv/qc")
def my_qc(u=Depends(current_user), con=Depends(get_con)):
    return rows(con.execute("SELECT * FROM qc_errors WHERE user_id=? ORDER BY date DESC, id DESC", (u["id"],)))


@app.get("/api/ctv/history")
def history(ym: str, u=Depends(current_user), con=Depends(get_con)):
    f, l = month_range(ym)
    return rows(con.execute(SCHED_SQL + " WHERE s.user_id=? AND s.date BETWEEN ? AND ? AND s.date<=? ORDER BY s.date DESC, s.start DESC",
                            (u["id"], f, l, date.today().isoformat())))


@app.get("/api/ctv/logs")
def my_logs(u=Depends(current_user), con=Depends(get_con)):
    return rows(con.execute("SELECT * FROM logs WHERE user_id=? ORDER BY id DESC LIMIT 500", (u["id"],)))


# ================================================================ ADMIN
@app.get("/api/admin/dashboard")
def admin_dashboard(day: str | None = None, u=Depends(admin_user), con=Depends(get_con)):
    day = day or date.today().isoformat()
    sched = rows(con.execute(SCHED_SQL + " WHERE s.date=? ORDER BY s.start", (day,)))
    now_m = datetime.now().hour * 60 + datetime.now().minute if day == date.today().isoformat() else (0 if day > date.today().isoformat() else 24 * 60)
    nxt = (date.today().replace(day=28) + timedelta(days=4)).strftime("%Y-%m")
    rk = nxt if autoschedule.reg_mode(con) == "month" else autoschedule.next_week().isoformat()  # kỳ đang nhận đăng ký
    return {
        "day": day,
        "total": len(sched),
        "done": sum(1 for s in sched if t2m(s["end"]) <= now_m),
        "working": sum(1 for s in sched if t2m(s["start"]) <= now_m < t2m(s["end"])),
        "pending_swaps": con.execute("SELECT COUNT(*) FROM swaps WHERE status='pending'").fetchone()[0],
        "pending_days": len(pending_days(con)),
        "active_ctv": con.execute("SELECT COUNT(*) FROM users WHERE role='ctv' AND active=1").fetchone()[0],
        "next_month": nxt,
        "availability_submitted": con.execute("SELECT COUNT(*) FROM availability WHERE ym=?", (rk,)).fetchone()[0],
        "reg_week": autoschedule.next_week().isoformat(),
        "reg_key": rk,
        "schedule": sched,
    }


# ----- nhân sự
@app.get("/api/admin/users")
def list_users(u=Depends(admin_user), con=Depends(get_con)):
    return rows(con.execute("""SELECT u.id, u.username, u.name, u.role, u.team_id, u.phone, u.email, u.code, u.active, u.created_at, u.hourly_rate, t.name AS team
        FROM users u LEFT JOIN teams t ON t.id=u.team_id ORDER BY u.role, u.username"""))


@app.post("/api/admin/users")
def save_user(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    fields = (body.get("name", "").strip(), body.get("role", "ctv"), body.get("team_id") or None,
              body.get("phone", "").strip(), body.get("email", "").strip(), body.get("code", "").strip(),
              1 if body.get("active", True) else 0)
    try:
        rate = max(0, int(float(body.get("hourly_rate") or 0)))
    except (TypeError, ValueError):
        err("Mức lương không hợp lệ")
    if not fields[0]:
        err("Vui lòng nhập họ tên")
    if body.get("id"):
        if int(body["id"]) == u["id"] and (fields[1] != "admin" or not fields[6]):
            err("Không thể tự khoá hoặc hạ quyền chính mình")
        con.execute("UPDATE users SET name=?, role=?, team_id=?, phone=?, email=?, code=?, active=?, hourly_rate=? WHERE id=?", (*fields, rate, body["id"]))
        if not fields[6]:
            con.execute("DELETE FROM sessions WHERE user_id=?", (body["id"],))
        log(con, u, f"Cập nhật tài khoản {body.get('username')}")
    else:
        username = body.get("username", "").strip()
        pw = body.get("password") or "123456"
        if not username:
            err("Vui lòng nhập tên đăng nhập")
        if con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            err("Tên đăng nhập đã tồn tại")
        con.execute("INSERT INTO users(username, password_hash, name, role, team_id, phone, email, code, active, created_at, hourly_rate) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (username, db.hash_pw(pw), *fields, now_str(), rate))
        log(con, u, f"Tạo tài khoản {username}")
    return {"ok": True}


@app.post("/api/admin/users/{uid}/reset-password")
def reset_password(uid: int, body: dict = Body(default={}), u=Depends(admin_user), con=Depends(get_con)):
    pw = body.get("password") or "123456"
    t = row(con.execute("SELECT username FROM users WHERE id=?", (uid,)))
    if not t:
        err("Không tìm thấy tài khoản", 404)
    con.execute("UPDATE users SET password_hash=?, must_change_pw=1 WHERE id=?", (db.hash_pw(pw), uid))
    con.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
    log(con, u, f"Đặt lại mật khẩu cho {t['username']}")
    return {"ok": True, "password": pw}


# ----- danh mục chung
CATALOG = {
    "teams": ("teams", "id", ["name"]),
    "positions": ("positions", "id", ["name", "team_id", "hourly_rate"]),
    "shifts": ("shift_types", "code", ["code", "name", "start", "end", "reg_min", "reg_max", "sort", "need_min", "need_max"]),
}


@app.get("/api/admin/catalog/{kind}")
def catalog_list(kind: str, u=Depends(admin_user), con=Depends(get_con)):
    table, pk, _ = CATALOG.get(kind) or err("Danh mục không hợp lệ", 404)
    return rows(con.execute(f"SELECT * FROM {table} ORDER BY {'sort' if kind == 'shifts' else pk}"))


@app.post("/api/admin/catalog/{kind}")
def catalog_save(kind: str, body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    table, pk, cols = CATALOG.get(kind) or err("Danh mục không hợp lệ", 404)
    vals = [body.get(c) for c in cols]
    if any(v in (None, "") for c, v in zip(cols, vals) if c != "team_id"):
        err("Vui lòng nhập đủ thông tin")
    qcols = ", ".join(f'"{c}"' for c in cols)
    original = body.get("_key")
    if original not in (None, ""):
        set_clause = ", ".join(f'"{c}"=?' for c in cols)
        con.execute(f"UPDATE {table} SET {set_clause} WHERE {pk}=?", (*vals, original))
    else:
        try:
            con.execute(f"INSERT INTO {table}({qcols}) VALUES ({', '.join('?' * len(cols))})", vals)
        except Exception:
            err("Mã đã tồn tại")
    log(con, u, f"Cập nhật danh mục {kind}: {vals[0]}")
    return {"ok": True}


@app.delete("/api/admin/catalog/{kind}/{key}")
def catalog_delete(kind: str, key: str, u=Depends(admin_user), con=Depends(get_con)):
    table, pk, _ = CATALOG.get(kind) or err("Danh mục không hợp lệ", 404)
    try:
        con.execute(f"DELETE FROM {table} WHERE {pk}=?", (key,))
    except Exception:
        err("Mục này đang được sử dụng, không thể xoá")
    log(con, u, f"Xoá danh mục {kind}: {key}")
    return {"ok": True}


# ----- lịch rảnh tổng hợp
@app.get("/api/admin/availability")
def admin_availability(ym: str, u=Depends(admin_user), con=Depends(get_con)):
    users = rows(con.execute("""SELECT u.id, u.username, u.name, t.name AS team, a.status, a.slots, a.updated_at
        FROM users u LEFT JOIN teams t ON t.id=u.team_id
        LEFT JOIN availability a ON a.user_id=u.id AND a.ym=?
        WHERE u.role='ctv' AND u.active=1 ORDER BY u.username""", (ym,)))
    regs = autoschedule.week_regs(con, ym) if autoschedule.is_week_key(ym) else {}
    for x in users:
        x["slots"] = json.loads(x["slots"]) if x["slots"] else {}
        x["status"] = x["status"] or "empty"
        x["source"] = "week" if x["slots"] else ""
        g = regs.get(x["id"])
        if g and g["source"] == "month":  # chưa đăng ký tuần → hiện lịch rảnh tháng
            x.update(slots=g["slots"], status=g["status"], updated_at=g["updated_at"], source="month")
    return {"ym": ym, "open": reg_open(con, ym), "users": users,
            "deadline": None if autoschedule.is_week_key(ym) else autoschedule.month_deadline(ym).strftime("%Y-%m-%d %H:%M")}


@app.put("/api/admin/reg-month")
def set_reg_month(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    con.execute("INSERT OR REPLACE INTO reg_months(ym, open) VALUES (?,?)", (body["ym"], 1 if body.get("open") else 0))
    log(con, u, f"{'Mở' if body.get('open') else 'Đóng'} đăng ký lịch rảnh {'tuần' if autoschedule.is_week_key(body['ym']) else 'tháng'} {body['ym']}")
    return {"ok": True}


@app.put("/api/admin/reg-mode")
def set_reg_mode(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    mode = body.get("mode")
    if mode not in ("week", "month"):
        err("Chế độ không hợp lệ")
    db.set_setting(con, "reg_mode", mode)
    log(con, u, f"Chuyển đăng ký lịch rảnh sang theo {'tuần' if mode == 'week' else 'tháng'}")
    return {"ok": True, "mode": mode}


@app.post("/api/admin/availability/unlock")
def unlock_availability(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    con.execute("UPDATE availability SET status='draft' WHERE user_id=? AND ym=?", (body["user_id"], body["ym"]))
    log(con, u, f"Mở khoá lịch rảnh tháng {body['ym']} cho CTV #{body['user_id']}")
    return {"ok": True}


# ----- xếp lịch
@app.get("/api/admin/schedules")
def admin_schedules(start: str, end: str, u=Depends(admin_user), con=Depends(get_con)):
    return rows(con.execute(SCHED_SQL + " WHERE s.date BETWEEN ? AND ? ORDER BY s.date, s.start, u.username", (start, end)))


@app.post("/api/admin/schedules")
def add_schedule(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    uid, d, code = body.get("user_id"), body.get("date"), body.get("shift_code")
    st = row(con.execute('SELECT * FROM shift_types WHERE code=?', (code,)))
    if not (uid and d and st):
        err("Thiếu thông tin ca")
    start, end = body.get("start") or st["start"], body.get("end") or st["end"]
    if t2m(end) <= t2m(start):
        err("Giờ kết thúc phải sau giờ bắt đầu")
    if con.execute('SELECT 1 FROM schedules WHERE user_id=? AND date=? AND start < ? AND "end" > ?', (uid, d, end, start)).fetchone():
        err("CTV này đã có ca trùng giờ trong ngày")
    con.execute('INSERT INTO schedules(user_id, date, shift_code, start, "end", position_id) VALUES (?,?,?,?,?,?)',
                (uid, d, code, start, end, body.get("position_id")))
    name = con.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()[0]
    log(con, u, f"Xếp ca {d} {start}-{end} cho {name}")
    return {"ok": True, **resync_sheet_day(con, d)}


@app.put("/api/admin/schedules/{sid}")
def update_schedule(sid: int, body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    """Sửa 1 ca trên bảng Xếp lịch: ca, giờ vào / ra, vị trí, ghi chú."""
    s = row(con.execute(SCHED_SQL + " WHERE s.id=?", (sid,)))
    if not s:
        err("Không tìm thấy ca", 404)
    if s["approved_at"]:
        err("Ca đã được chấm công. Sửa ở mục Chấm công (bỏ duyệt ngày đó trước).")
    code = body.get("shift_code") or s["shift_code"]
    if not con.execute("SELECT 1 FROM shift_types WHERE code=?", (code,)).fetchone():
        err("Ca không hợp lệ")
    start, end = (body.get("start") or s["start"]).strip(), (body.get("end") or s["end"]).strip()
    if not re.fullmatch(r"\d{2}:\d{2}", start) or not re.fullmatch(r"\d{2}:\d{2}", end) or t2m(end) <= t2m(start):
        err("Giờ vào / ra không hợp lệ")
    note = (body.get("note") if body.get("note") is not None else s["note"] or "").strip()
    clash = con.execute('SELECT note FROM schedules WHERE user_id=? AND date=? AND id<>? AND start < ? AND "end" > ?',
                        (s["user_id"], s["date"], sid, end, start)).fetchone()
    if clash and not (note or clash[0]):
        err(f"{s['username']} đã có ca khác trùng giờ trong ngày. Nếu là ca kèm CTV, ghi chú vào ca này.")
    pos = body.get("position_id") or s["position_id"]
    uid, plan = s["user_id"], s["plan"]
    new_uid = body.get("user_id")
    if new_uid and int(new_uid) != s["user_id"]:  # đổi ca ngoài web: admin chuyển ca sang người khác
        to = row(con.execute("SELECT id, username FROM users WHERE id=? AND active=1", (new_uid,)))
        if not to:
            err("CTV nhận ca không hợp lệ")
        c2 = con.execute('SELECT note FROM schedules WHERE user_id=? AND date=? AND id<>? AND start < ? AND "end" > ?',
                         (to["id"], s["date"], sid, end, start)).fetchone()
        if c2 and not (note or c2[0]):
            err(f"{to['username']} đã có ca khác trùng giờ trong ngày")
        uid = to["id"]
        plan = plan or dumps({"user_id": s["user_id"], "username": s["username"], "start": s["start"], "end": s["end"],
                              "position_id": s["position_id"], "position": s["position"]})
        if "Đổi ca" not in note:
            note = f"Đổi ca: {s['username']} → {to['username']}" + (f" · {note}" if note else "")
    con.execute('UPDATE schedules SET user_id=?, shift_code=?, start=?, "end"=?, position_id=?, note=?, plan=? WHERE id=?',
                (uid, code, start, end, pos, note, plan, sid))
    log(con, u, f"Sửa ca {s['date']} của {s['username']}: {s['start']}-{s['end']} → {start}-{end}"
        + (f", chuyển cho user #{uid}" if uid != s["user_id"] else ""))
    return {"ok": True, **resync_sheet_day(con, s["date"])}


@app.delete("/api/admin/schedules/{sid}")
def delete_schedule(sid: int, u=Depends(admin_user), con=Depends(get_con)):
    s = row(con.execute(SCHED_SQL + " WHERE s.id=?", (sid,)))
    if not s:
        err("Không tìm thấy ca", 404)
    if s["approved_at"]:
        err("Ca đã được chấm công. Bỏ duyệt ngày đó ở mục Chấm công trước khi xoá.")
    con.execute("DELETE FROM schedules WHERE id=?", (sid,))
    log(con, u, f"Xoá ca {s['date']} {s['start']}-{s['end']} của {s['username']}")
    return {"ok": True, **resync_sheet_day(con, s["date"])}


@app.post("/api/admin/schedules/copy-week")
def copy_week(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    src, dst = date.fromisoformat(body["from"]), date.fromisoformat(body["to"])
    offset = (dst - src).days
    items = rows(con.execute('SELECT * FROM schedules WHERE date BETWEEN ? AND ?',
                             (src.isoformat(), (src + timedelta(days=6)).isoformat())))
    added = 0
    for s in items:
        nd = (date.fromisoformat(s["date"]) + timedelta(days=offset)).isoformat()
        if con.execute('SELECT 1 FROM schedules WHERE user_id=? AND date=? AND start < ? AND "end" > ?',
                       (s["user_id"], nd, s["end"], s["start"])).fetchone():
            continue
        con.execute('INSERT INTO schedules(user_id, date, shift_code, start, "end", position_id) VALUES (?,?,?,?,?,?)',
                    (s["user_id"], nd, s["shift_code"], s["start"], s["end"], s["position_id"]))
        added += 1
    log(con, u, f"Sao chép lịch tuần {src} sang tuần {dst} ({added} ca)")
    return {"ok": True, "added": added}


# ----- chấm công: bản raw từ lịch xếp → admin sửa (PIC, vị trí, giờ) → duyệt
def pending_days(con) -> list[str]:
    """Các ngày (tới hôm nay) còn ca chưa duyệt chấm công."""
    return [r[0] for r in con.execute(
        "SELECT DISTINCT date FROM schedules WHERE approved_at IS NULL AND date<=? ORDER BY date",
        (date.today().isoformat(),))]


@app.get("/api/admin/timesheet")
def get_timesheet(day: str, u=Depends(admin_user), con=Depends(get_con)):
    items = rows(con.execute(SCHED_SQL + " WHERE s.date=? ORDER BY st.sort, s.start, p.id, u.username", (day,)))
    approved = bool(items) and all(s["approved_at"] for s in items)
    return {"day": day, "rows": items, "approved": approved,
            "approved_by": items[0]["approved_by"] if approved else None,
            "approved_at": items[0]["approved_at"] if approved else None,
            "pending_days": pending_days(con)}


@app.put("/api/admin/timesheet")
def save_timesheet(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    day = body.get("day") or ""
    try:
        date.fromisoformat(day)
    except ValueError:
        err("Ngày không hợp lệ")
    current = {s["id"]: s for s in rows(con.execute(SCHED_SQL + " WHERE s.date=?", (day,)))}
    if current and all(s["approved_at"] for s in current.values()):
        err("Ngày này đã duyệt. Bấm “Bỏ duyệt” trước khi sửa.")
    shifts = {r["code"]: dict(r) for r in con.execute("SELECT * FROM shift_types")}
    users = {r["id"]: r["username"] for r in con.execute("SELECT id, username FROM users")}
    keep, seen = [], {}
    for r in body.get("rows", []):
        sid = r.get("id")
        if sid and sid not in current:
            err("Có dòng không thuộc ngày này, vui lòng tải lại trang")
        if r.get("delete"):
            if sid:
                con.execute("DELETE FROM schedules WHERE id=?", (sid,))
            continue
        uid, start, end = r.get("user_id"), (r.get("start") or "").strip(), (r.get("end") or "").strip()
        code = r.get("shift_code") or (current[sid]["shift_code"] if sid else "")
        if uid not in users:
            err("Mỗi dòng cần chọn PIC")
        if code not in shifts:
            err("Ca không hợp lệ")
        if not re.fullmatch(r"\d{2}:\d{2}", start) or not re.fullmatch(r"\d{2}:\d{2}", end) or t2m(end) <= t2m(start):
            err(f"Giờ vào / ra của {users[uid]} không hợp lệ")
        note = (r.get("note") or "").strip()
        # trùng giờ chỉ hợp lệ khi có ghi chú (VD ca kèm CTV vẫn được chấm công)
        for (a, b, n) in seen.get(uid, []):
            if t2m(start) < b and t2m(end) > a and not (note or n):
                err(f"{users[uid]} có 2 dòng trùng giờ. Nếu là ca kèm CTV, ghi chú vào dòng đó (VD: Kèm CTV)")
        seen.setdefault(uid, []).append((t2m(start), t2m(end), note))
        keep.append((sid, uid, code, start, end, r.get("position_id"), note))
    changed = 0
    for sid, uid, code, start, end, pos, note in keep:
        if sid:
            o = current[sid]
            if (o["user_id"], o["start"], o["end"], o["position_id"], o["note"] or "") == (uid, start, end, pos, note):
                continue
            plan = o["plan"]
            if not plan:  # lưu bản lịch gốc ở lần sửa đầu tiên
                plan = dumps({"user_id": o["user_id"], "username": o["username"], "start": o["start"], "end": o["end"],
                              "position_id": o["position_id"], "position": o["position"]})
            con.execute('UPDATE schedules SET user_id=?, start=?, "end"=?, position_id=?, note=?, plan=? WHERE id=?',
                        (uid, start, end, pos, note, plan, sid))
        else:
            con.execute('INSERT INTO schedules(user_id, date, shift_code, start, "end", position_id, note, plan) VALUES (?,?,?,?,?,?,?,?)',
                        (uid, day, code, start, end, pos, note, dumps({"added": True})))
        changed += 1
    approve = bool(body.get("approve"))
    if approve:
        if day > date.today().isoformat():
            err("Chưa đến ngày này, chưa thể duyệt chấm công")
        con.execute("UPDATE schedules SET approved_at=?, approved_by=? WHERE date=?", (now_str(), u["name"], day))
    log(con, u, f"{'Duyệt' if approve else 'Lưu'} chấm công ngày {day}" + (f" ({changed} dòng thay đổi)" if changed else ""))
    return {"ok": True, "changed": changed}


@app.post("/api/admin/timesheet/unapprove")
def unapprove_timesheet(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    day = body.get("day")
    con.execute("UPDATE schedules SET approved_at=NULL, approved_by=NULL WHERE date=?", (day,))
    log(con, u, f"Bỏ duyệt chấm công ngày {day}")
    return {"ok": True}


# ----- duyệt lịch tuần → Google Sheet "Lịch trực"
def sync_cfg(con) -> dict:
    tok = db.get_setting(con, "sync_token")
    if not tok:
        tok = secrets.token_urlsafe(18)
        db.set_setting(con, "sync_token", tok)
    return {"url": db.get_setting(con, "sync_url"), "sheet": db.get_setting(con, "sync_sheet", sheet_sync.DEFAULT_SHEET), "token": tok}


def week_build(con, start: str) -> dict:
    try:
        d0 = date.fromisoformat(start)
    except ValueError:
        err("Ngày không hợp lệ")
    sched = rows(con.execute(SCHED_SQL + " WHERE s.date BETWEEN ? AND ?", (d0.isoformat(), (d0 + timedelta(days=6)).isoformat())))
    try:
        b = sheet_sync.build(sched, d0, sync_cfg(con)["sheet"])
    except sheet_sync.SyncError as e:
        err(str(e))
    except Exception as e:  # noqa: BLE001 — sheet không công khai / mất mạng
        err(f"Không đọc được Google Sheet: {e}")
    b["approved"] = json.loads(db.get_setting(con, "week_sync", "{}")).get(start)
    return b


@app.get("/api/admin/sheet-sync/config")
def sheet_sync_config(u=Depends(admin_user), con=Depends(get_con)):
    c = sync_cfg(con)
    return {"url": c["url"], "sheet": f"https://docs.google.com/spreadsheets/d/{c['sheet']}", "script": sheet_sync.apps_script(c["token"])}


@app.put("/api/admin/sheet-sync/config")
def sheet_sync_save(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    url = (body.get("url") or "").strip()
    if url and not re.match(r"^https://script\.google\.com/", url):
        err("URL phải là link ứng dụng web Apps Script (https://script.google.com/…/exec)")
    db.set_setting(con, "sync_url", url)
    if body.get("sheet"):
        db.set_setting(con, "sync_sheet", handbook.parse_sheet_id(body["sheet"]))
    log(con, u, "Cập nhật cài đặt đồng bộ Google Sheet lịch trực")
    return {"ok": True}


@app.get("/api/admin/sheet-sync/preview")
def sheet_sync_preview(start: str, u=Depends(admin_user), con=Depends(get_con)):
    return week_build(con, start)


@app.post("/api/admin/sheet-sync/push")
def sheet_sync_push(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    start = body.get("start") or ""
    cfg = sync_cfg(con)
    if not cfg["url"]:
        err("Chưa cài đặt Apps Script để ghi vào sheet")
    b = week_build(con, start)
    if not b["days"]:
        err("Sheet chưa có cột cho các ngày của tuần này")
    try:
        sheet_sync.push(cfg["url"], cfg["token"], b["tab"], b["days"])
    except sheet_sync.SyncError as e:
        err(str(e))
    done = json.loads(db.get_setting(con, "week_sync", "{}"))
    done[start] = {"at": now_str(), "by": u["name"], "days": len(b["days"])}
    db.set_setting(con, "week_sync", dumps(done))
    d0 = date.fromisoformat(start)
    log(con, u, f"Đẩy lịch tuần {d0.strftime('%d/%m')} lên Google Sheet ({len(b['days'])} ngày)")
    return {"ok": True, "days": len(b["days"])}


# ----- tuần: tự xếp ca → duyệt
def week_info(con, start: str) -> dict:
    try:
        ws = autoschedule.monday(date.fromisoformat(start))
    except ValueError:
        err("Ngày không hợp lệ")
    key = ws.isoformat()
    rk = autoschedule.reg_key(con, ws)
    st = autoschedule.statuses(con).get(key, {})
    return {"week": key, "reg_mode": autoschedule.reg_mode(con), "reg_key": rk, "deadline": autoschedule.deadline(ws).strftime("%Y-%m-%d %H:%M"),
            "gen_time": autoschedule.gen_time(ws).strftime("%Y-%m-%d %H:%M"),
            "reg_open": reg_open(con, rk),
            "registered": len(autoschedule.week_regs(con, key)),
            "registered_week": con.execute("SELECT COUNT(*) FROM availability WHERE ym=?", (rk,)).fetchone()[0],
            "active_ctv": con.execute("SELECT COUNT(*) FROM users WHERE role='ctv' AND active=1").fetchone()[0],
            "auto_rows": con.execute("SELECT COUNT(*) FROM schedules WHERE date BETWEEN ? AND ? AND source='auto'",
                                     (key, (ws + timedelta(days=6)).isoformat())).fetchone()[0],
            "sync": json.loads(db.get_setting(con, "week_sync", "{}")).get(key),
            "sheet_ready": bool(db.get_setting(con, "sync_url")), **st}


@app.get("/api/admin/week")
def admin_week(start: str, u=Depends(admin_user), con=Depends(get_con)):
    return week_info(con, start)


@app.post("/api/admin/week/auto")
def admin_week_auto(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    ws = autoschedule.monday(date.fromisoformat(body["start"]))
    if autoschedule.statuses(con).get(ws.isoformat(), {}).get("approved_at"):
        err("Tuần này đã duyệt. Bỏ duyệt trước khi tự xếp lại.")
    if not autoschedule.has_regs(con, ws):
        err("Chưa có CTV nào đăng ký lịch rảnh cho tuần này nên chưa tự xếp được")
    rep = autoschedule.generate(con, ws, u["name"])
    return rep


@app.post("/api/admin/week/approve")
def admin_week_approve(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    ws = autoschedule.monday(date.fromisoformat(body["start"]))
    key = ws.isoformat()
    if not con.execute("SELECT 1 FROM schedules WHERE date BETWEEN ? AND ?", (key, (ws + timedelta(days=6)).isoformat())).fetchone():
        err("Tuần này chưa có ca nào")
    autoschedule.set_status(con, key, approved_at=now_str(), approved_by=u["name"])
    rng = f"{ws.strftime('%d/%m')} – {(ws + timedelta(days=6)).strftime('%d/%m')}"
    con.execute("INSERT INTO notifications(title, body, created_at) VALUES (?,?,?)",
                (f"Lịch trực tuần {rng} đã chốt", "Xem ca của bạn ở mục Lịch làm việc.", now_str()))
    log(con, u, f"Duyệt lịch tuần {rng}")
    out = {"ok": True, "pushed": False}
    if body.get("push") and db.get_setting(con, "sync_url"):
        try:
            out["pushed"] = sheet_sync_push({"start": key}, u, con)["ok"]
        except HTTPException as e:  # đã duyệt; chỉ báo lỗi ghi sheet
            out["push_error"] = e.detail
    return out


@app.post("/api/admin/week/unapprove")
def admin_week_unapprove(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    ws = autoschedule.monday(date.fromisoformat(body["start"]))
    autoschedule.set_status(con, ws.isoformat(), approved_at=None, approved_by=None)
    log(con, u, f"Bỏ duyệt lịch tuần {ws.strftime('%d/%m')}")
    return {"ok": True}


# ----- duyệt đổi ca
@app.get("/api/admin/swaps")
def admin_swaps(u=Depends(admin_user), con=Depends(get_con)):
    return rows(con.execute(SWAP_SQL + " ORDER BY (w.status='pending') DESC, w.id DESC LIMIT 500"))


@app.post("/api/admin/swaps/{sid}/{action}")
def handle_swap(sid: int, action: str, u=Depends(admin_user), con=Depends(get_con)):
    w = row(con.execute(SWAP_SQL + " WHERE w.id=?", (sid,)))
    if not w or w["status"] != "pending":
        err("Phiếu không còn chờ duyệt")
    if action == "approve" and con.execute("SELECT approved_at FROM schedules WHERE id=?", (w["schedule_id"],)).fetchone()[0]:
        err("Ca này đã được chấm công, sửa PIC ở mục Chấm công")
    if action == "approve":
        sc = row(con.execute(SCHED_SQL + " WHERE s.id=?", (w["schedule_id"],)))
        if sc["user_id"] != w["from_user"]:
            err("Ca này đã đổi người, không thể duyệt")
        t = None
        if w["swap_schedule_id"]:
            t = row(con.execute(SCHED_SQL + " WHERE s.id=?", (w["swap_schedule_id"],)))
            if not t or t["user_id"] != w["to_user"]:
                err(f"Ca của {w['to_username']} đã thay đổi, không thể duyệt")
        p = swap_problem(con, sc, w["to_user"], t, w["from_username"], w["to_username"])
        if p:
            err(f"{p}, không thể duyệt")

        def move(x, to_id, frm, to):
            plan = x["plan"] or dumps({"user_id": x["user_id"], "username": x["username"], "start": x["start"], "end": x["end"],
                                       "position_id": x["position_id"], "position": x["position"]})
            note = f"Đổi ca: {frm} → {to}" + (f" · {x['note']}" if x["note"] else "")
            con.execute("UPDATE schedules SET user_id=?, plan=?, note=? WHERE id=?", (to_id, plan, note, x["id"]))
        move(sc, w["to_user"], w["from_username"], w["to_username"])
        if t:  # đổi chéo: ca của người nhận chuyển về người xin
            move(t, w["from_user"], w["to_username"], w["from_username"])
        status = "approved"
    elif action == "reject":
        status = "rejected"
    else:
        err("Hành động không hợp lệ")
    con.execute("UPDATE swaps SET status=?, handled_by=?, handled_at=? WHERE id=?", (status, u["name"], now_str(), sid))
    log(con, u, f"{'Duyệt' if status == 'approved' else 'Từ chối'} phiếu đổi ca #{sid} ({w['from_username']} → {w['to_username']})")
    out = {"ok": True}
    if status == "approved":
        out.update(resync_sheet_day(con, w["date"]))
    return out


@app.post("/api/telegram/webhook")
def telegram_webhook(body: dict = Body(...), x_telegram_bot_api_secret_token: str = Header(default=""),
                     con=Depends(get_con)):
    """Bấm nút Duyệt/Từ chối trong tin Telegram."""
    token, chats = notify.config(con)
    if not token or not secrets.compare_digest(x_telegram_bot_api_secret_token, notify.webhook_secret(token)):
        err("Forbidden", 403)
    msg = body.get("message") or {}
    if msg.get("text", "").startswith("/start"):
        notify.call(con, "sendMessage", {"chat_id": msg["chat"]["id"], "text": f"Chat ID của bạn: {msg['chat']['id']}"})
        return {"ok": True}
    cq = body.get("callback_query")
    if not cq:
        return {"ok": True}
    sender = cq.get("from") or {}
    reply = lambda text: notify.call(con, "answerCallbackQuery",
                                     {"callback_query_id": cq["id"], "text": text, "show_alert": "true"})
    m = re.fullmatch(r"sw:(\d+):(approve|reject)", cq.get("data", ""))
    if not m:
        return {"ok": True}
    if str(sender.get("id")) not in chats:
        reply("Bạn không có quyền duyệt")
        return {"ok": True}
    admin = row(con.execute("SELECT * FROM users WHERE role='admin' AND active=1 ORDER BY id LIMIT 1"))
    actor = {**admin, "name": f"{admin['name']} (Telegram)"}
    sid, action = int(m.group(1)), m.group(2)
    try:
        handle_swap(sid, action, u=actor, con=con)
        con.commit()
        result = "✅ Đã duyệt" if action == "approve" else "❌ Đã từ chối"
    except HTTPException as e:
        con.rollback()
        reply(str(e.detail))
        result = f"⚠️ {e.detail}"
    else:
        reply(result)
    cm = cq.get("message") or {}
    if cm:
        notify.call(con, "editMessageText", {
            "chat_id": cm["chat"]["id"], "message_id": cm["message_id"], "parse_mode": "HTML",
            "disable_web_page_preview": "true",
            "text": notify.esc(cm.get("text", "")) + f"\n\n<b>{notify.esc(result)}</b> · {now_str()[:16]}"})
    return {"ok": True}


def resync_sheet_day(con, day: str) -> dict:
    """Tuần đã từng đẩy lên sheet "Lịch trực" → ghi lại cột của ngày vừa đổi ca (giữ nguyên các ngày khác)."""
    ws = autoschedule.monday(date.fromisoformat(day)).isoformat()
    cfg = sync_cfg(con)
    if not cfg["url"] or ws not in json.loads(db.get_setting(con, "week_sync", "{}")):
        return {}
    try:
        b = week_build(con, ws)
        days = [d for d in b["days"] if d["date"] == day]
        if days:
            sheet_sync.push(cfg["url"], cfg["token"], b["tab"], days)
            return {"sheet": "updated"}
    except HTTPException as e:
        return {"sheet_error": e.detail}
    except sheet_sync.SyncError as e:
        return {"sheet_error": str(e)}
    return {}


# ----- bảng lương
@app.get("/api/admin/salary")
def admin_salary(ym: str, u=Depends(admin_user), con=Depends(get_con)):
    users = rows(con.execute("SELECT id, username, name FROM users ORDER BY username"))
    out = []
    for x in users:
        s = compute_salary(con, x["id"], ym)
        s.pop("rows")
        s.pop("qc")
        if s["shifts"] or s["bonus"] or s["deduction"] or s["qc_count"]:
            out.append({**x, **s})
    pub = row(con.execute("SELECT * FROM salary_months WHERE ym=?", (ym,))) or {"published": 0}
    f, l = month_range(ym)
    return {"ym": ym, "published": bool(pub["published"]), "rows": out,
            "pending_days": [d for d in pending_days(con) if f <= d <= l]}


@app.get("/api/admin/salary/daily")
def admin_salary_daily(ym: str, u=Depends(admin_user), con=Depends(get_con)):
    """Tổng hợp theo ngày: giờ / lương giờ của các ca đã duyệt, số ca còn chờ duyệt."""
    f, l = month_range(ym)
    out = {}
    for s in rows(con.execute(SCHED_SQL + " WHERE s.date BETWEEN ? AND ? ORDER BY s.date", (f, l))):
        d = out.setdefault(s["date"], {"date": s["date"], "shifts": 0, "people": set(), "hours": 0.0, "amount": 0, "pending": 0})
        d["shifts"] += 1
        if s["approved_at"]:
            h = (t2m(s["end"]) - t2m(s["start"])) / 60
            d["people"].add(s["user_id"])
            d["hours"] += h
            d["amount"] += round(h * (s["hourly_rate"] or 0))
        else:
            d["pending"] += 1
    for d in out.values():
        d["people"] = len(d["people"])
        d["hours"] = round(d["hours"], 2)
    return list(out.values())


@app.get("/api/admin/salary/user")
def admin_salary_user(ym: str, user_id: int, u=Depends(admin_user), con=Depends(get_con)):
    """Chi tiết lương 1 nhân sự: các ca đã duyệt (được tính) + ca chờ duyệt (chưa tính)."""
    user = row(con.execute("SELECT id, username, name, hourly_rate FROM users WHERE id=?", (user_id,)))
    if not user:
        err("Không tìm thấy nhân sự", 404)
    f, l = month_range(ym)
    s = compute_salary(con, user_id, ym)
    s["pending_rows"] = rows(con.execute(SCHED_SQL + " WHERE s.user_id=? AND s.date BETWEEN ? AND ? AND s.approved_at IS NULL"
                                         " ORDER BY s.date, s.start", (user_id, f, l)))
    s["user"] = user
    return s


@app.put("/api/admin/salary/month-sheet")
def save_month_sheet(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    """Điều chỉnh bảng công cả tháng của 1 nhân sự (ngày nào, ca nào, giờ nào) + thưởng / khấu trừ.
    Ca của ngày đã qua được lưu ở trạng thái đã duyệt chấm công."""
    ym, uid = body.get("ym") or "", body.get("user_id")
    user = row(con.execute("SELECT id, username FROM users WHERE id=?", (uid,)))
    if not user or not re.fullmatch(r"\d{4}-\d{2}", ym):
        err("Thiếu nhân sự hoặc tháng")
    f, l = month_range(ym)
    current = {s["id"]: s for s in rows(con.execute(SCHED_SQL + " WHERE s.user_id=? AND s.date BETWEEN ? AND ?", (uid, f, l)))}
    shifts = {r["code"]: dict(r) for r in con.execute("SELECT * FROM shift_types")}
    today = date.today().isoformat()
    keep_ids, seen, items = set(), {}, []
    for r in body.get("rows", []):
        sid, d, code = r.get("id"), r.get("date") or "", r.get("shift_code")
        start, end = (r.get("start") or "").strip(), (r.get("end") or "").strip()
        if sid and sid not in current:
            err("Dữ liệu đã thay đổi, vui lòng tải lại trang")
        if not (f <= d <= l) or code not in shifts:
            err("Ngày hoặc ca không hợp lệ")
        if not re.fullmatch(r"\d{2}:\d{2}", start) or not re.fullmatch(r"\d{2}:\d{2}", end) or t2m(end) <= t2m(start):
            err(f"Giờ vào / ra ngày {d[8:]}/{d[5:7]} không hợp lệ")
        note = (r.get("note") or "").strip()
        for a, b, n in seen.get(d, []):
            if t2m(start) < b and t2m(end) > a and not (note or n):
                err(f"Ngày {d[8:]}/{d[5:7]} có 2 ca trùng giờ. Nếu là ca kèm CTV, ghi chú vào dòng đó (VD: Kèm CTV)")
        seen.setdefault(d, []).append((t2m(start), t2m(end), note))
        if sid:
            keep_ids.add(sid)
        items.append((sid, d, code, start, end, r.get("position_id") or 1, (r.get("note") or "").strip()))
    # người khác đã có ca trùng giờ? (cảnh báo nhẹ: không chặn, vì 2 người có thể cùng trực 1 ca)
    removed = [s for i, s in current.items() if i not in keep_ids]
    for s in removed:
        con.execute("DELETE FROM schedules WHERE id=?", (s["id"],))
    ts, changed = now_str(), len(removed)
    for sid, d, code, start, end, pos, note in items:
        appr = (ts, u["name"]) if d < today else (None, None)  # ca hôm nay duyệt ở mục Chấm công
        if sid:
            o = current[sid]
            same = (o["start"], o["end"], o["position_id"], o["note"] or "", o["shift_code"]) == (start, end, pos, note, code)
            if same and (o["approved_at"] or d >= today):
                continue
            plan = o["plan"]
            if not plan and (o["start"], o["end"], o["position_id"]) != (start, end, pos):
                plan = dumps({"user_id": o["user_id"], "username": o["username"], "start": o["start"], "end": o["end"],
                              "position_id": o["position_id"], "position": o["position"]})
            con.execute('UPDATE schedules SET shift_code=?, start=?, "end"=?, position_id=?, note=?, plan=?, '
                        'approved_at=COALESCE(approved_at, ?), approved_by=COALESCE(approved_by, ?) WHERE id=?',
                        (code, start, end, pos, note, plan, appr[0], appr[1], sid))
        else:
            con.execute('INSERT INTO schedules(user_id, date, shift_code, start, "end", position_id, note, plan, approved_at, approved_by) '
                        'VALUES (?,?,?,?,?,?,?,?,?,?)', (uid, d, code, start, end, pos, note, dumps({"added": True}), appr[0], appr[1]))
        changed += 1
    if "bonus" in body:
        con.execute("INSERT OR REPLACE INTO salaries(user_id, ym, bonus, deduction, note) VALUES (?,?,?,?,?)",
                    (uid, ym, int(body.get("bonus") or 0), int(body.get("deduction") or 0), body.get("note", "")))
    log(con, u, f"Điều chỉnh bảng công tháng {ym} của {user['username']} ({changed} ca thay đổi)")
    return {"ok": True, "changed": changed}


@app.put("/api/admin/salary")
def adjust_salary(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    con.execute("INSERT OR REPLACE INTO salaries(user_id, ym, bonus, deduction, note) VALUES (?,?,?,?,?)",
                (body["user_id"], body["ym"], int(body.get("bonus") or 0), int(body.get("deduction") or 0), body.get("note", "")))
    log(con, u, f"Điều chỉnh lương tháng {body['ym']} cho CTV #{body['user_id']}")
    return {"ok": True}


@app.post("/api/admin/salary/publish")
def publish_salary(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    pub = 1 if body.get("published") else 0
    con.execute("INSERT OR REPLACE INTO salary_months(ym, published, published_at) VALUES (?,?,?)", (body["ym"], pub, now_str()))
    if pub:
        con.execute("INSERT INTO notifications(title, body, created_at) VALUES (?,?,?)",
                    (f"Đã có bảng lương tháng {body['ym'][5:]}/{body['ym'][:4]}", "Vào mục Tra cứu lương để xem chi tiết.", now_str()))
    log(con, u, f"{'Công bố' if pub else 'Thu hồi'} bảng lương tháng {body['ym']}")
    return {"ok": True}


# ----- lỗi QC
QC_SQL = "SELECT q.*, u.username, u.name FROM qc_errors q JOIN users u ON u.id=q.user_id"


@app.get("/api/admin/qc")
def admin_qc(ym: str | None = None, u=Depends(admin_user), con=Depends(get_con)):
    if ym:
        return rows(con.execute(QC_SQL + " WHERE q.ym=? ORDER BY q.date DESC, q.id DESC", (ym,)))
    return rows(con.execute(QC_SQL + " ORDER BY q.date DESC, q.id DESC LIMIT 1000"))


@app.post("/api/admin/qc")
def save_qc(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    uid, d = body.get("user_id"), (body.get("date") or "").strip()
    if not uid or not d:
        err("Vui lòng chọn CTV và ngày ghi lỗi")
    ym = (body.get("ym") or d[:7]).strip()
    vals = (int(uid), ym, d, body.get("ticket", "").strip(), body.get("error", "").strip(), body.get("note", "").strip(),
            body.get("penalty", "").strip(), int(body.get("amount") or 0), body.get("category", "").strip())
    if body.get("id"):
        con.execute("UPDATE qc_errors SET user_id=?, ym=?, date=?, ticket=?, error=?, note=?, penalty=?, amount=?, category=? WHERE id=?",
                    (*vals, body["id"]))
    else:
        con.execute("INSERT INTO qc_errors(user_id, ym, date, ticket, error, note, penalty, amount, category, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (*vals, now_str()))
    name = con.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()[0]
    log(con, u, f"{'Sửa' if body.get('id') else 'Ghi'} lỗi QC cho {name} ({vals[7]:,}đ)")
    return {"ok": True}


@app.delete("/api/admin/qc/{qid}")
def delete_qc(qid: int, u=Depends(admin_user), con=Depends(get_con)):
    con.execute("DELETE FROM qc_errors WHERE id=?", (qid,))
    log(con, u, f"Xoá lỗi QC #{qid}")
    return {"ok": True}


# ----- thông báo & nhật ký
@app.post("/api/admin/notifications")
def create_notification(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    if not body.get("title", "").strip():
        err("Vui lòng nhập tiêu đề")
    con.execute("INSERT INTO notifications(title, body, created_at) VALUES (?,?,?)",
                (body["title"].strip(), body.get("body", "").strip(), now_str()))
    log(con, u, f"Gửi thông báo: {body['title']}")
    return {"ok": True}


@app.delete("/api/admin/notifications/{nid}")
def delete_notification(nid: int, u=Depends(admin_user), con=Depends(get_con)):
    con.execute("DELETE FROM notification_reads WHERE notification_id=?", (nid,))
    con.execute("DELETE FROM notifications WHERE id=?", (nid,))
    return {"ok": True}


@app.get("/api/admin/logs")
def admin_logs(u=Depends(admin_user), con=Depends(get_con)):
    return rows(con.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 1000"))


# ================================================================ CẨM NANG
def handbook_settings(con):
    sid = db.get_setting(con, "handbook_sheet_id", handbook.DEFAULT_SHEET_ID)
    modes = json.loads(db.get_setting(con, "handbook_modes", "{}"))
    hidden = {g for g, m in modes.items() if m == "hidden"} | set(json.loads(db.get_setting(con, "handbook_hidden", "[]")))
    return sid, hidden


def tab_mode(con, t) -> str:
    modes = json.loads(db.get_setting(con, "handbook_modes", "{}"))
    return modes.get(t["gid"]) or handbook.default_mode(t["name"])


def hb_call(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except handbook.HandbookError as e:
        err(str(e), 502)


def fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


@app.get("/api/handbook")
def handbook_index(refresh: bool = False, u=Depends(current_user), con=Depends(get_con)):
    sid, hidden = handbook_settings(con)
    tabs, ts, warn = hb_call(handbook.list_tabs, sid, refresh)
    return {"sheet_url": f"https://docs.google.com/spreadsheets/d/{sid}", "fetched_at": fmt_ts(ts), "warning": warn,
            "tabs": [{**t, "mode": tab_mode(con, t)} for t in handbook.sort_tabs(tabs) if t["gid"] not in hidden]}


@app.get("/api/handbook/tab/{gid}")
def handbook_tab(gid: str, refresh: bool = False, u=Depends(current_user), con=Depends(get_con)):
    sid, hidden = handbook_settings(con)
    if gid in hidden or not gid.isdigit():
        err("Không tìm thấy mục này", 404)
    rows, ts, warn = hb_call(handbook.get_tab, sid, gid, refresh)
    return {"gid": gid, "rows": rows, "fetched_at": fmt_ts(ts), "warning": warn}


# ----- tra cứu học viên theo SĐT / email
# SĐT: quy mọi kiểu ghi về 0xxxxxxxxx rồi so — "967705605", "0967705605", "84967705605", "+84 967 705 605" đều khớp
PHONE_COL = re.compile(r"dien thoai|\bsdt\b|so dt|phone|mobile")
MAIL_COL = re.compile(r"e-?mail|\bmail\b")


def norm_phone(s: str) -> str:
    d = re.sub(r"\D", "", s or "")
    if d.startswith("84") and len(d) >= 11:
        d = "0" + d[2:]
    if len(d) == 9:
        d = "0" + d
    return d


def mask_contact(q: str) -> str:
    if "@" in q:
        name, _, dom = q.partition("@")
        return name[:2] + "***@" + dom
    d = norm_phone(q)
    return d[:4] + "***" + d[-3:]


@app.get("/api/handbook/lookup")
def handbook_lookup(q: str, u=Depends(current_user), con=Depends(get_con)):
    q = q.strip()
    is_mail = "@" in q
    if is_mail:
        key = q.lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", key):
            err("Nhập đủ địa chỉ email để tra cứu học viên")
    else:
        key = norm_phone(q)
        if not 10 <= len(key) <= 11:
            err("Nhập đủ số điện thoại để tra cứu học viên")
    sid, hidden = handbook_settings(con)
    tabs, _, _ = hb_call(handbook.list_tabs, sid)
    col_re = MAIL_COL if is_mail else PHONE_COL
    match = (lambda v: v.strip().lower() == key) if is_mail else (lambda v: norm_phone(v) == key)
    results = []
    for t in handbook.sort_tabs(tabs):
        if t["gid"] in hidden:
            continue
        try:
            rows, _, _ = handbook.get_tab(sid, t["gid"])
        except handbook.HandbookError:
            continue
        h = handbook.header_index(rows)
        if h < 0:
            continue
        cols = [i for i, c in enumerate(rows[h]) if col_re.search(handbook.fold(c))]
        if not cols:
            continue
        hits = [r for r in rows[h + 1:] if any(i < len(r) and r[i].strip() and match(r[i]) for i in cols)]
        if hits:
            results.append({"gid": t["gid"], "tab": t["name"], "header": rows[h], "rows": hits[:50], "more": len(hits) > 50})
    log(con, u, f"Tra cứu học viên {mask_contact(q)} ({sum(len(r['rows']) for r in results)} dòng)")
    return {"type": "email" if is_mail else "phone", "results": results}


@app.get("/api/handbook/search")
def handbook_search(q: str, u=Depends(current_user), con=Depends(get_con)):
    """Tìm trên tất cả mục. Trả về theo từng mục có kết quả.
    Mục nhỏ (<= 400 dòng) trả nguyên dữ liệu để giao diện gom dòng nối tiếp đúng;
    mục lớn chỉ trả dòng tiêu đề cột + các dòng khớp (tối đa 30)."""
    words = handbook.fold(q).split()
    if not words or len(" ".join(words)) < 2:
        err("Nhập ít nhất 2 ký tự để tìm")
    sid, hidden = handbook_settings(con)
    tabs, _, _ = hb_call(handbook.list_tabs, sid)
    out = []
    order = {"show": 0, "suggest": 1, "other": 2}
    visible = [t for t in handbook.sort_tabs(tabs) if t["gid"] not in hidden]
    visible.sort(key=lambda t: (order.get(tab_mode(con, t), 2), handbook.search_rank(t["name"]) if tab_mode(con, t) == "show" else 0))
    for t in visible:
        try:
            rows, _, _ = handbook.get_tab(sid, t["gid"])
        except handbook.HandbookError:
            continue
        hit = [i for i, r in enumerate(rows) if all(w in handbook.fold(" ".join(r)) for w in words)]
        if not hit:
            continue
        if len(rows) <= 400:
            out.append({"gid": t["gid"], "tab": t["name"], "rows": rows, "truncated": False})
        else:
            h = handbook.header_index(rows)
            keep = ([h] if h >= 0 else []) + [i for i in hit if i != h][:30]
            out.append({"gid": t["gid"], "tab": t["name"], "rows": [rows[i] for i in keep], "truncated": len(hit) > 30})
    return out


def _handbook_warmer():
    """Chạy nền: tải trước và làm mới toàn bộ sheet định kỳ để Cẩm nang luôn mới và tìm kiếm nhanh."""
    cfg, cfg_at = None, 0.0
    while True:
        try:
            if cfg is None or time.time() - cfg_at > 1800:  # đọc cài đặt 30 phút/lần để database (Neon) được ngủ
                con = db.connect()
                cfg = handbook_settings(con)
                con.close()
                cfg_at = time.time()
            sid, hidden = cfg
            if not sid:
                time.sleep(300)
                continue
            tabs, _, _ = handbook.list_tabs(sid, refresh=True)
            for t in tabs:
                if t["gid"] not in hidden:
                    try:
                        handbook.get_tab(sid, t["gid"], refresh=True)
                    except handbook.HandbookError:
                        pass
        except Exception:
            pass
        time.sleep(max(60, handbook.CACHE_TTL - 30))


# ----- cho máy chủ miễn phí hay "ngủ" (Render free): dịch vụ cron bên ngoài gọi vào
@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/cron/tick")
def cron_tick(key: str = ""):
    """cron-job.org gọi mỗi 10 phút (giữ web thức) — từ 20:00 CN sẽ tự xếp ca tuần tới."""
    want = os.environ.get("CRON_KEY", "")
    key = key.replace(" ", "+")  # dấu "+" trong khoá bị hiểu thành dấu cách khi dán thẳng vào URL
    if not want or not secrets.compare_digest(key, want):
        err("Sai khoá", 403)
    rep = autoschedule.tick()
    return {"ok": True, "generated": bool(rep), "week": rep and rep.get("week")}


def _week_scheduler():
    """Chạy nền mỗi phút: 20:00 CN tự xếp ca tuần tới (nếu chưa xếp)."""
    while True:
        try:
            autoschedule.tick()
        except Exception:
            pass
        time.sleep(60)


@app.on_event("startup")
def start_week_scheduler():
    if os.environ.get("AUTO_SCHEDULE", "1") == "1":
        threading.Thread(target=_week_scheduler, daemon=True).start()


@app.on_event("startup")
def start_telegram_webhook():
    if os.environ.get("TELEGRAM_WEBHOOK", "1") == "1":
        notify.ensure_webhook_async()


@app.on_event("startup")
def start_ican_warmer():
    if os.environ.get("HANDBOOK_WARM", "1") == "1":
        ican.warm()


@app.on_event("startup")
def start_handbook_warmer():
    if os.environ.get("HANDBOOK_WARM", "1") == "1":
        threading.Thread(target=_handbook_warmer, daemon=True).start()


@app.get("/api/admin/handbook")
def admin_handbook(request: Request, u=Depends(admin_user), con=Depends(get_con)):
    sid, hidden = handbook_settings(con)
    try:
        tabs, ts, warn = handbook.list_tabs(sid, refresh=True)
        error = warn
    except handbook.HandbookError as e:
        tabs, ts, error = [], None, str(e)
    tok = db.get_setting(con, "hb_gas_token")
    if not tok:
        tok = secrets.token_urlsafe(18)
        db.set_setting(con, "hb_gas_token", tok)
        handbook.set_push_token(tok)
    st = handbook.push_status()
    portal = f"{request.headers.get('x-forwarded-proto') or request.url.scheme}://{request.headers.get('host') or request.url.netloc}"
    return {"sheet_url": f"https://docs.google.com/spreadsheets/d/{sid}", "error": error,
            "gas_script": handbook.apps_script(tok, sid, portal),
            "push": {"data_at": fmt_ts(st["data_at"]) if st["data_at"] else None,
                     "seen_at": fmt_ts(st["seen_at"]) if st["seen_at"] else None,
                     "other_sheet": bool(st["data_sheet"] and st["data_sheet"] != sid)},
            "fetched_at": fmt_ts(ts) if ts else None,
            "tabs": [{**t, "mode": "hidden" if t["gid"] in hidden else tab_mode(con, t)} for t in handbook.sort_tabs(tabs)]}


@app.post("/api/handbook/push")
def handbook_push(body: dict = Body(...), con=Depends(get_con)):
    """Apps Script (chạy bằng tài khoản công ty của admin) gửi nội dung sheet Cẩm nang sang."""
    try:
        return handbook.receive(con, body)
    except handbook.HandbookError as e:
        err(str(e), 403 if "mã bảo mật" in str(e) else 400)


@app.put("/api/admin/handbook")
def save_handbook(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    try:
        sid = handbook.parse_sheet_id(body.get("sheet", ""))
    except handbook.HandbookError as e:
        err(str(e))
    db.set_setting(con, "handbook_sheet_id", sid)
    modes = {str(g): m for g, m in (body.get("modes") or {}).items() if m in handbook.MODES}
    db.set_setting(con, "handbook_modes", dumps(modes))
    db.set_setting(con, "handbook_hidden", "[]")
    handbook.clear_cache()
    log(con, u, "Cập nhật cấu hình Cẩm nang")
    return {"ok": True}


# ----- thao tác ở CRM: video hướng dẫn trên Google Drive
def crm_sources(con) -> list:
    try:
        return json.loads(db.get_setting(con, "crm_videos", "[]")) or []
    except ValueError:
        return []


@app.get("/api/crm-videos")
def crm_video_list(refresh: bool = False, u=Depends(current_user), con=Depends(get_con)):
    return {"groups": crm_videos.build(crm_sources(con), refresh=refresh), "fetched_at": now_str()}


@app.get("/api/admin/crm-videos")
def admin_crm_videos(u=Depends(admin_user), con=Depends(get_con)):
    src = crm_sources(con)
    return {"sources": src, "groups": crm_videos.build(src, refresh=True)}


@app.put("/api/admin/crm-videos")
def save_crm_videos(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    out = []
    for s in body.get("sources") or []:
        url, title = str(s.get("url") or "").strip(), str(s.get("title") or "").strip()[:120]
        if not url:
            continue
        try:
            crm_videos.parse_link(url)
        except crm_videos.DriveError as e:
            err(f"{e}: {url[:80]}")
        out.append({"url": url, "title": title})
    db.set_setting(con, "crm_videos", dumps(out))
    log(con, u, f"Cập nhật video Thao tác ở CRM ({len(out)} link)")
    return {"ok": True}


# ----- Document: tab tài liệu admin tự thêm (Tên tab + link YouTube / Drive)
def doc_tabs(con) -> list:
    try:
        return json.loads(db.get_setting(con, "doc_tabs", "[]")) or []
    except ValueError:
        return []


@app.get("/api/docs")
def doc_list(u=Depends(current_user), con=Depends(get_con)):
    out = [{"id": t["id"], "name": t["name"]} for t in doc_tabs(con)]
    if milo.enabled(con):
        out.append({"id": "milo", "name": "TK Milo"})
    return out


# ----- tab "TK Milo": tra học viên đã bàn giao / đã có trong file VH / tài khoản được tạo
MILO_KEYS = ("s1", "s2", "vh")


def milo_sources(con) -> dict:
    try:
        d = json.loads(db.get_setting(con, "milo_sources", "{}")) or {}
    except ValueError:
        d = {}
    return {k: d.get(k, "") for k in MILO_KEYS}


@app.post("/api/milo/push")
def milo_push(body: dict = Body(...), con=Depends(get_con)):
    """Apps Script (tài khoản công ty của admin) gửi các dòng Milo của 3 file sang."""
    try:
        return milo.receive(con, body)
    except milo.MiloError as e:
        err(str(e), 403 if "mã bảo mật" in str(e) else 400)


@app.get("/api/milo/search")
def milo_search(q: str = "", u=Depends(current_user)):
    if len(q.strip()) < 2:
        return {"ready": milo.status()["data_at"] is not None, "students": []}
    return milo.search(q)


@app.get("/api/admin/milo")
def admin_milo(request: Request, u=Depends(admin_user), con=Depends(get_con)):
    tok = milo.ensure_token(con)
    src = milo_sources(con)
    portal = f"{request.headers.get('x-forwarded-proto') or request.url.scheme}://{request.headers.get('host') or request.url.netloc}"
    st = milo.status()
    return {"sources": {k: f"https://docs.google.com/spreadsheets/d/{v}" if v else "" for k, v in src.items()},
            "ready": all(src.values()),
            "gas_script": milo.apps_script(tok, portal, src) if all(src.values()) else "",
            "data_at": fmt_ts(st["data_at"]) if st["data_at"] else None,
            "seen_at": fmt_ts(st["seen_at"]) if st["seen_at"] else None, "count": st["count"]}


@app.put("/api/admin/milo")
def save_admin_milo(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    src = {}
    for k in MILO_KEYS:
        try:
            src[k] = handbook.parse_sheet_id(str(body.get(k, "")))
        except handbook.HandbookError:
            err("Link Google Sheet không hợp lệ")
    db.set_setting(con, "milo_sources", dumps(src))
    log(con, u, "Cập nhật nguồn dữ liệu TK Milo")
    return {"ok": True}


@app.get("/api/docs/{tid}")
def doc_view(tid: str, refresh: bool = False, u=Depends(current_user), con=Depends(get_con)):
    if tid == "milo" and milo.enabled(con):
        st = milo.status()
        return {"id": "milo", "name": "TK Milo", "milo": True, "ready": st["data_at"] is not None, "partial": st["partial"],
                "data_at": fmt_ts(st["data_at"]) if st["data_at"] else None}
    t = next((t for t in doc_tabs(con) if t["id"] == tid), None)
    if not t:
        err("Không tìm thấy tab tài liệu", 404)
    base = {"id": t["id"], "name": t["name"], "url": t["url"]}
    # link tới 1 tab trong file Cẩm nang → hiện bảng từ dữ liệu Cẩm nang (CTV không cần quyền mở sheet)
    hb = docs.sheet_tab(t["url"])
    sid, _ = handbook_settings(con)
    if hb and hb[0] == sid:
        try:
            blocks, ts, warn = handbook.get_blocks(sid, hb[1], refresh)
        except handbook.HandbookError as e:
            return {**base, "groups": [], "error": str(e)}
        # cột "Link teacher site" của bảng GV: lấy link theo tên từ icanconnect.vn (sheet có thể ghi sai)
        blocks, ican_stat = ican.apply(blocks, t["name"], refresh)
        blocks = ican.add_spw_schedule(blocks, t["name"])  # cột link xem lịch rảnh GV trên speakwell.ican.vn
        out = {**base, "groups": [], "table": {"blocks": blocks, "fetched_at": fmt_ts(ts)}, "warning": warn}
        if ican_stat and u["role"] == "admin":
            out["ican"] = ican_stat
        return out
    return {**docs.resolve(t, refresh=refresh), **base}


@app.get("/api/admin/docs")
def admin_docs(u=Depends(admin_user), con=Depends(get_con)):
    return doc_tabs(con)


@app.put("/api/admin/docs")
def save_docs(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    try:
        tabs = docs.clean(body.get("tabs"))
    except docs.DocError as e:
        err(str(e))
    db.set_setting(con, "doc_tabs", dumps(tabs))
    log(con, u, f"Cập nhật tab Document ({len(tabs)} tab)")
    return tabs


# ----- Video hướng dẫn PH thao tác (kênh YouTube)
def ph_channel(con) -> str:
    return db.get_setting(con, "ph_youtube_channel", "") or yt_videos.DEFAULT_CHANNEL


@app.get("/api/ph-videos")
def ph_video_list(refresh: bool = False, u=Depends(current_user), con=Depends(get_con)):
    ch = ph_channel(con)
    try:
        return yt_videos.get(ch, refresh=refresh)
    except yt_videos.YTError as e:
        return {"channel": ch, "name": "", "groups": [], "error": str(e)}


@app.get("/api/admin/ph-videos")
def admin_ph_videos(u=Depends(admin_user), con=Depends(get_con)):
    return {"channel": ph_channel(con)}


@app.put("/api/admin/ph-videos")
def save_ph_videos(body: dict = Body(...), u=Depends(admin_user), con=Depends(get_con)):
    try:
        ch = yt_videos.normalize(str(body.get("channel") or ""))
        data = yt_videos.get(ch, refresh=True)
    except yt_videos.YTError as e:
        err(str(e))
    db.set_setting(con, "ph_youtube_channel", ch)
    log(con, u, f"Đổi kênh YouTube video hướng dẫn PH: {ch}")
    return {"ok": True, "count": sum(len(g["items"]) for g in data["groups"])}


# ================================================================ pages
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def root():
    return RedirectResponse("/ctv")


@app.get("/ctv")
def ctv_page():
    return FileResponse(os.path.join(STATIC, "ctv.html"))


@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(STATIC, "admin.html"))
