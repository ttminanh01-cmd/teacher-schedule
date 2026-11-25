"""Nhập bảng chấm công đã chốt (Google Sheet "Bảng lương CTV") vào hệ thống.

    python -m server.import_timesheet [--sheet <link>] [--months 102026,112026] [--dry-run]

- Tab "Bảng chấm công": mỗi dòng = CTV, ngày, giờ đến, giờ về, tổng giờ, tháng, note.
  Các ngày có trong sheet sẽ được THAY THẾ bằng dữ liệu sheet và đánh dấu đã duyệt chấm công.
  Ca dài vắt qua 18:00 (VD 13:30–22:00) được tách thành ca Chiều + ca Tối, tổng giờ giữ nguyên.
- Tab "QC lỗi CTV": bổ sung lỗi QC còn thiếu (không nhân đôi lỗi đã có).
- Người có công nhưng chưa có tài khoản (CTV đã nghỉ) được tạo ở trạng thái KHOÁ (không đăng nhập được)
  để vẫn có tên trong bảng lương.
- In bảng đối chiếu tổng giờ từng người với tab "[Bảng lương]".
"""
import argparse
import os
import csv
import io
import re
import secrets

from . import db, handbook
from .db import dumps, now_str

DEFAULT_SHEET = os.environ.get("PAYROLL_SHEET_ID", "")  # sheet bảng lương CTV
SOURCE = "Bảng chấm công (Google Sheet)"


def t2m(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def m2t(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def read_tab(sid, name_part):
    tab = next(t for t in handbook.list_tabs(sid)[0] if name_part in handbook.fold(t["name"]))
    return handbook.fetch_rows(sid, tab["gid"])


def norm_user(s: str) -> str:
    u = re.sub(r"\s+", "", (s or "").strip().lower())
    return re.sub(r"^ct\.", "ctv.", u)  # 'ct.haott' gõ nhầm


def split_shifts(start: int, end: int, shifts):
    """Tách khoảng giờ theo ranh giới ca (12:00 / 18:00) → [(code, start, end)]."""
    # chỉ cắt ở ranh giới giữa các ca chính (hết ca sáng 12:00, hết ca chiều 18:00) — phần sau 22:00 vẫn thuộc ca tối
    mains = sorted((s for s in shifts if s["code"] in ("sang", "chieu", "toi")), key=lambda s: t2m(s["end"]))
    bounds = sorted({t2m(s["end"]) for s in mains[:-1]})
    cuts = [start] + [b for b in bounds if start < b < end] + [end]
    out = []
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2
        # ca chứa đoạn giờ này; nhiều ca cùng chứa (Tối / Tối gãy) → ca có giờ vào/ra sát nhất, hoà thì ca dài hơn
        def score(s, a=a, b=b, mid=mid):
            inside = t2m(s["start"]) <= mid < t2m(s["end"])
            gap = 0 if inside else min(abs(mid - t2m(s["start"])), abs(mid - t2m(s["end"])))
            fit = abs(a - t2m(s["start"])) + abs(b - t2m(s["end"]))
            return (not inside, gap, fit, -(t2m(s["end"]) - t2m(s["start"])))
        code = min(shifts, key=score)["code"]
        out.append((code, a, b))
    return out


def run(sheet: str, months: list[str], dry: bool) -> dict:
    sid = handbook.parse_sheet_id(sheet)
    cc = [r for r in read_tab(sid, "bang cham cong")[1:] if len(r) > 6 and r[1].strip() and r[2].strip()]
    cc = [r for r in cc if r[6].strip() in months]
    con = db.connect()
    db.init_db()
    shifts = [dict(r) for r in con.execute("SELECT * FROM shift_types ORDER BY sort")]
    stats = {"rows": len(cc), "inserted": 0, "deleted": 0, "new_users": [], "qc": 0}

    # tên người từ tab bảng lương / thông tin CTV
    names = {}
    payroll = read_tab(sid, "[bang luong]")
    for r in payroll[3:]:
        if len(r) > 2 and r[1].strip():
            names[norm_user(r[1])] = r[2].strip()

    def uid_of(username):
        r = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if r:
            return r[0]
        stats["new_users"].append(username)
        return con.execute("INSERT INTO users(username, password_hash, name, role, team_id, active, created_at) VALUES (?,?,?,?,?,0,?)",
                           (username, db.hash_pw(secrets.token_hex(12)), names.get(username, username), "ctv", 1, now_str())).lastrowid

    # gom theo ngày
    by_date = {}
    for r in cc:
        d, mth, y = r[2].strip().split("/")
        iso = f"{y}-{int(mth):02d}-{int(d):02d}"
        by_date.setdefault(iso, []).append(r)
    if not by_date:
        return stats
    first, last = min(by_date), max(by_date)

    # lịch cũ trong khoảng ngày → để lấy vị trí + ghi "lịch gốc"
    old = {}
    for s in con.execute("SELECT s.*, u.username, p.name AS position FROM schedules s JOIN users u ON u.id=s.user_id "
                         "LEFT JOIN positions p ON p.id=s.position_id WHERE s.date BETWEEN ? AND ?", (first, last)):
        old.setdefault((s["user_id"], s["date"], s["shift_code"]), dict(s))
    stats["deleted"] = con.execute("DELETE FROM schedules WHERE date BETWEEN ? AND ?", (first, last)).rowcount

    ts = now_str()
    for iso, items in sorted(by_date.items()):
        seen = {}
        for r in items:
            uid = uid_of(norm_user(r[1]))
            a, b = t2m(r[3].strip()), t2m(r[4].strip())
            for code, x, y in split_shifts(a, b, shifts):
                note = r[7].strip() if len(r) > 7 else ""
                if any(x < q and y > p for p, q in seen.get(uid, [])) and not note:
                    note = "Kèm CTV"  # 2 dòng trùng giờ trong sheet = 1 ca làm kèm CTV, vẫn chấm công
                    stats.setdefault("overlap", []).append(f"{norm_user(r[1])} {iso} {m2t(x)}-{m2t(y)}")
                seen.setdefault(uid, []).append((x, y))
                o = old.get((uid, iso, code))
                st = next(s for s in shifts if s["code"] == code)
                plan_src = o or None
                plan = None
                if plan_src and (plan_src["start"], plan_src["end"]) != (m2t(x), m2t(y)):
                    plan = dumps({"user_id": uid, "username": plan_src["username"], "start": plan_src["start"], "end": plan_src["end"],
                                  "position_id": plan_src["position_id"], "position": plan_src["position"]})
                con.execute('INSERT INTO schedules(user_id, date, shift_code, start, "end", position_id, note, plan, approved_at, approved_by) '
                            'VALUES (?,?,?,?,?,?,?,?,?,?)',
                            (uid, iso, code, m2t(x), m2t(y), (o or {}).get("position_id") or 1, note,
                             plan, ts, SOURCE))
                stats["inserted"] += 1

    # lỗi QC
    try:
        qc = read_tab(sid, "qc loi")
    except StopIteration:
        qc = []
    for r in qc[1:]:
        if len(r) < 8 or not re.fullmatch(r"\d{5,6}", r[0].strip()) or not r[2].strip():
            continue
        m = re.fullmatch(r"(\d{1,2})(\d{4})", r[0].strip())
        ym = f"{m.group(2)}-{int(m.group(1)):02d}"
        if r[0].strip() not in months:
            continue
        dm = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", r[1].strip())
        d = f"{dm.group(3)}-{int(dm.group(2)):02d}-{int(dm.group(1)):02d}" if dm else f"{ym}-01"
        x = con.execute("SELECT id FROM users WHERE username=?", (norm_user(re.split(r"[\s(]", r[2].strip())[0]),)).fetchone()
        if not x:  # người không có công trong hệ thống → bỏ qua, báo lại
            stats.setdefault("qc_skipped", []).append(r[2].strip())
            continue
        uid = x[0]
        amount = int(re.sub(r"[^\d]", "", r[7]) or 0)
        if con.execute("SELECT 1 FROM qc_errors WHERE user_id=? AND ym=? AND error=? AND amount=?", (uid, ym, r[4], amount)).fetchone():
            continue
        con.execute("INSERT INTO qc_errors(user_id, ym, date, ticket, error, note, penalty, amount, category, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (uid, ym, d, r[3], r[4], r[5], r[6], amount, r[8] if len(r) > 8 else "", now_str()))
        stats["qc"] += 1

    # đối chiếu với tab [Bảng lương]
    head = payroll[0]
    cols = {head[i].strip(): i for i in range(len(head)) if head[i].strip() in months}
    diffs = []
    for r in payroll[3:]:
        if len(r) < 5 or not r[1].strip():
            continue
        u = norm_user(r[1])
        x = con.execute("SELECT id FROM users WHERE username=?", (u,)).fetchone()
        for mcode, i in cols.items():
            ym = f"{mcode[-4:]}-{int(mcode[:-4]):02d}"
            want_h = float((r[i] or "0").replace(",", "") or 0)
            want_fine = int(re.sub(r"[^\d]", "", r[i + 2] if len(r) > i + 2 else "") or 0)
            got_h, got_fine = 0.0, 0
            if x:
                f, l = f"{ym}-01", f"{ym}-31"
                got_h = sum((t2m(s[1]) - t2m(s[0])) / 60 for s in con.execute(
                    'SELECT start, "end" FROM schedules WHERE user_id=? AND date BETWEEN ? AND ? AND approved_at IS NOT NULL', (x[0], f, l)))
                got_fine = con.execute("SELECT COALESCE(SUM(amount),0) FROM qc_errors WHERE user_id=? AND ym=?", (x[0], ym)).fetchone()[0]
            if abs(got_h - want_h) > 0.02 or got_fine != want_fine:
                diffs.append((u, ym, want_h, round(got_h, 2), want_fine, got_fine))
    stats["diffs"] = diffs
    stats["range"] = (first, last)
    if dry:
        con.rollback()
    else:
        con.execute("INSERT INTO logs(user_id, actor, action, created_at) VALUES (NULL, 'Hệ thống', ?, ?)",
                    (f"Nhập bảng chấm công {', '.join(months)} từ Google Sheet ({stats['inserted']} ca)", now_str()))
        con.commit()
    con.close()
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", default=DEFAULT_SHEET)
    ap.add_argument("--months", default="102026,112026", help="Mã tháng như trong sheet, cách nhau dấu phẩy")
    ap.add_argument("--dry-run", action="store_true", help="Chạy thử, không ghi vào DB")
    a = ap.parse_args()
    s = run(a.sheet, [m.strip() for m in a.months.split(",")], a.dry_run)
    for k, v in s.items():
        if k != "diffs":
            print(f"{k}: {v}")
    print("Lệch so với tab [Bảng lương] (user, tháng, giờ sheet, giờ hệ thống, phạt sheet, phạt hệ thống):")
    for d in s["diffs"] or [("— không lệch —",)]:
        print("  ", d)
