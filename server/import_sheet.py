"""Nhập dữ liệu vận hành từ Google Sheet (sheet chia sẻ công khai) vào cơ sở dữ liệu.

Đọc các tab:
  - "Tính lương CTV"        → danh sách CTV (username, họ tên, mã CTV, email, phòng ban).
                               KHÔNG nhập CCCD / ngày sinh.
  - "Lịch trực ..."          → lịch xếp ca theo ngày (ca × vị trí × ngày)
  - "Đăng ký lịch làm ..."   → lịch rảnh theo thứ × ca (ô tích TRUE/FALSE)
  - "QC lỗi CTV"             → lỗi QC và tiền phạt

Chạy:
  python -m server.import_sheet                       # nhập (bỏ qua bản ghi đã có)
  python -m server.import_sheet --reset               # xoá dữ liệu CTV cũ rồi nhập lại
  python -m server.import_sheet --sheet <link> --password <mật khẩu ban đầu>

Danh sách CTV (data/ctv_roster.csv, cột: name,username,position,hourly_rate,status):
chỉ tạo tài khoản cho CTV có status = Active. Dữ liệu (lịch, đăng ký, lỗi QC) của người
không nằm trong danh sách Active sẽ bị bỏ qua.
"""
import argparse
import csv
import io
import os
import re
from datetime import date

from . import db, handbook

DEFAULT_SHEET = os.environ.get("OPS_SHEET_ID", "")  # sheet vận hành (Đăng ký lịch, Lịch trực, QC, Tính lương)
DEFAULT_ROSTER = os.path.join(os.path.dirname(__file__), "..", "data", "ctv_roster.csv")
ALLOWED: set | None = None  # username (chữ thường) được phép có tài khoản; None = không giới hạn
SHIFT_BY_NAME = {"sang": "sang", "chieu": "chieu", "toi": "toi"}


def fetch_csv(sheet_id: str, gid: str) -> list[list[str]]:
    return [[c.strip() for c in r] for r in handbook.fetch_rows(sheet_id, gid)]


def norm_user(cell: str) -> str:
    """'ctv.abc (HV)\\n' → 'ctv.abc'"""
    m = re.search(r"[A-Za-z][A-Za-z0-9._]*", cell or "")
    return m.group(0).strip(".") if m else ""


def year_for(month: int) -> int:
    t = date.today()
    return t.year - 1 if month > t.month + 2 else t.year


def ensure_user(con, username: str, name: str = "", team_id: int = 1, email: str = "", code: str = "", pw_hash: str = ""):
    if ALLOWED is not None and username.lower() not in ALLOWED:
        return None
    r = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if r:
        if name or email or code:
            con.execute("UPDATE users SET name=COALESCE(NULLIF(?,''), name), email=COALESCE(NULLIF(?,''), email), "
                        "code=COALESCE(NULLIF(?,''), code), team_id=? WHERE id=?", (name, email, code, team_id, r[0]))
        return r[0]
    cur = con.execute("INSERT INTO users(username, password_hash, name, role, team_id, email, code, created_at) VALUES (?,?,?,?,?,?,?,?)",
                      (username, pw_hash, name or username, "ctv", team_id, email, code, db.now_str()))
    return cur.lastrowid


def import_users(con, rows, pw_hash, stats):
    head = rows[0]
    col = {handbook.fold(h).strip(): i for i, h in enumerate(head)}
    ci = {k: next((i for h, i in col.items() if k in h), None) for k in ("phong ban", "ctv", "ma ctv", "ho ten", "mail")}
    teams = {handbook.fold(r[1]): r[0] for r in con.execute("SELECT id, name FROM teams").fetchall()}
    for r in rows[1:]:
        g = lambda k: r[ci[k]] if ci[k] is not None and ci[k] < len(r) else ""
        username = norm_user(g("ctv"))
        if not username or not g("ho ten"):
            continue
        dept = g("phong ban")
        team_id = teams.get(handbook.fold(dept))
        if team_id is None and dept:
            team_id = con.execute("INSERT INTO teams(name) VALUES (?)", (dept,)).lastrowid
            teams[handbook.fold(dept)] = team_id
        # tên lấy theo danh sách CTV nếu có, sheet lương chỉ bổ sung email / mã CTV / phòng ban
        if ensure_user(con, username, "" if ALLOWED is not None else g("ho ten"), team_id or 1, g("mail"), g("ma ctv"), pw_hash):
            stats["users"] += 1


def import_schedule(con, rows, pw_hash, stats):
    shifts = {r["code"]: r for r in con.execute('SELECT * FROM shift_types').fetchall()}
    positions = con.execute("SELECT id, name FROM positions ORDER BY id").fetchall()
    pos_plain = positions[0]["id"]
    pos_monitor = next((p["id"] for p in positions if "monitor" in handbook.fold(p["name"])), pos_plain)
    # ngày của mỗi cột nằm ở dòng 1 hoặc dòng 2 (dạng dd/mm)
    dates = {}
    for c in range(2, max(len(rows[0]), len(rows[1]))):
        for r in rows[:2]:
            m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", r[c].strip()) if c < len(r) else None
            if m:
                d, mo = int(m.group(1)), int(m.group(2))
                dates[c] = date(year_for(mo), mo, d).isoformat()
    today = date.today().isoformat()
    shift = None
    for r in rows[2:]:
        if r[0]:
            shift = SHIFT_BY_NAME.get(handbook.fold(r[0]).strip())
        if not shift or shift not in shifts or len(r) < 2 or not r[1]:
            continue
        pos = pos_monitor if "monitor" in handbook.fold(r[1]) else pos_plain
        st = shifts[shift]
        for c, d in dates.items():
            username = norm_user(r[c]) if c < len(r) else ""
            if not username:
                continue
            uid = ensure_user(con, username, pw_hash=pw_hash)
            if not uid:
                stats["skipped"] += 1
                continue
            if con.execute("SELECT 1 FROM schedules WHERE user_id=? AND date=? AND shift_code=?", (uid, d, shift)).fetchone():
                continue
            sid = con.execute('INSERT INTO schedules(user_id, date, shift_code, start, "end", position_id) VALUES (?,?,?,?,?,?)',
                              (uid, d, shift, st["start"], st["end"], pos)).lastrowid
            stats["schedules"] += 1
            if d < today:  # ca đã qua trong sheet → coi như đã chấm công đủ giờ
                con.execute("UPDATE schedules SET approved_at=?, approved_by='Nhập từ Google Sheet' WHERE id=?", (db.now_str(), sid))


def import_availability(con, rows, ym, pw_hash, stats):
    days = {"thu 2": 1, "thu 3": 2, "thu 4": 3, "thu 5": 4, "thu 6": 5, "thu 7": 6, "chu nhat": 7, "cn": 7}
    shifts = {r["code"]: r for r in con.execute('SELECT * FROM shift_types').fetchall()}
    cols, cur_day = {}, None
    for c in range(1, len(rows[0])):
        h = handbook.fold(rows[0][c]).strip()
        if h in days:
            cur_day = days[h]
        sh = SHIFT_BY_NAME.get(handbook.fold(rows[1][c]).strip()) if c < len(rows[1]) else None
        if cur_day and sh:
            cols[c] = f"{cur_day}-{sh}"
    for r in rows[2:]:
        username = norm_user(r[0]) if r else ""
        if not username:
            continue
        slots = {}
        for c, key in cols.items():
            if c < len(r) and r[c].upper() == "TRUE":
                st = shifts[key.split("-")[1]]
                slots[key] = {"start": st["start"], "end": st["end"]}
        if not any(c < len(r) and r[c] for c in cols):
            continue  # dòng chưa điền
        uid = ensure_user(con, username, pw_hash=pw_hash)
        if not uid:
            continue
        con.execute("INSERT OR REPLACE INTO availability(user_id, ym, slots, status, updated_at) VALUES (?,?,?,?,?)",
                    (uid, ym, db.dumps(slots), "submitted", db.now_str()))
        stats["availability"] += 1


def import_qc(con, rows, pw_hash, stats):
    for r in rows[1:]:
        if len(r) < 8 or not re.fullmatch(r"\d{5,6}", r[0]) or not r[2]:
            continue
        m = re.fullmatch(r"(\d{1,2})(\d{4})", r[0])
        ym = f"{m.group(2)}-{int(m.group(1)):02d}"
        dm = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", r[1])
        d = f"{dm.group(3)}-{int(dm.group(2)):02d}-{int(dm.group(1)):02d}" if dm else f"{ym}-01"
        username = norm_user(r[2])
        if not username:
            continue
        uid = ensure_user(con, username, pw_hash=pw_hash)
        if not uid:
            continue
        amount = int(re.sub(r"[^\d]", "", r[7]) or 0)
        category = r[8] if len(r) > 8 else ""
        if con.execute("SELECT 1 FROM qc_errors WHERE user_id=? AND date=? AND error=? AND amount=?", (uid, d, r[4], amount)).fetchone():
            continue
        con.execute("INSERT INTO qc_errors(user_id, ym, date, ticket, error, note, penalty, amount, category, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (uid, ym, d, r[3], r[4], r[5], r[6], amount, category, db.now_str()))
        stats["qc"] += 1


def load_roster(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [{k.strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


def run(sheet: str, password: str, reset: bool, roster: str | None = None) -> dict:
    global ALLOWED
    sid = handbook.parse_sheet_id(sheet)
    tabs, _, _ = handbook.list_tabs(sid, refresh=True)
    db.init_db()
    con = db.connect()
    pw_hash = db.hash_pw(password)
    stats = {"users": 0, "schedules": 0, "availability": 0, "qc": 0, "skipped": 0}
    try:
        if reset:
            for t in ("qc_errors", "swaps", "attendance", "schedules", "availability", "salaries", "sessions", "notification_reads"):
                con.execute(f"DELETE FROM {t}")
            con.execute("DELETE FROM users WHERE role<>'admin'")
        if roster and os.path.exists(roster):
            people = load_roster(roster)
            active = [r for r in people if r.get("status", "").lower() == "active" and r.get("username")]
            ALLOWED = {r["username"].lower() for r in active}
            for r in active:
                ensure_user(con, r["username"], r.get("name", ""), 1, pw_hash=pw_hash)
            # người Inactive đã có tài khoản từ lần nhập trước → khoá lại
            for r in people:
                if r.get("status", "").lower() != "active" and r.get("username"):
                    con.execute("UPDATE users SET active=0 WHERE username=? AND role='ctv'", (r["username"],))
            stats["roster_active"] = len(active)
        by = lambda pat: [t for t in tabs if re.search(pat, handbook.fold(t["name"]))]
        for t in by(r"tinh luong"):
            import_users(con, fetch_csv(sid, t["gid"]), pw_hash, stats)
        for t in by(r"lich truc"):
            import_schedule(con, fetch_csv(sid, t["gid"]), pw_hash, stats)
        reg_tabs = by(r"dang ky lich")
        month_of = lambda t: (lambda m: int(m.group(1)) if m else None)(re.search(r"thang (\d{1,2})", handbook.fold(t["name"])))
        numbered = [month_of(t) for t in reg_tabs if month_of(t)]
        for t in reg_tabs:
            mo = month_of(t)
            if mo is None:  # tab không ghi tháng = bản cũ hơn → tháng liền trước tab có ghi tháng
                mo = (min(numbered) - 2) % 12 + 1 if numbered else date.today().month
            ym = f"{year_for(mo)}-{mo:02d}"
            import_availability(con, fetch_csv(sid, t["gid"]), ym, pw_hash, stats)
        for t in by(r"qc"):
            import_qc(con, fetch_csv(sid, t["gid"]), pw_hash, stats)
        con.execute("INSERT INTO logs(user_id, actor, action, created_at) VALUES (NULL, 'Hệ thống', ?, ?)",
                    (f"Nhập dữ liệu từ Google Sheet: {stats}", db.now_str()))
        con.commit()
    finally:
        con.close()
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", default=DEFAULT_SHEET, help="Link hoặc ID Google Sheet")
    ap.add_argument("--password", default="123456", help="Mật khẩu ban đầu cho tài khoản CTV mới")
    ap.add_argument("--reset", action="store_true", help="Xoá dữ liệu CTV hiện có trước khi nhập")
    ap.add_argument("--roster", default=DEFAULT_ROSTER, help="File CSV danh sách CTV (chỉ tạo tài khoản cho người Active)")
    a = ap.parse_args()
    print(run(a.sheet, a.password, a.reset, a.roster))
