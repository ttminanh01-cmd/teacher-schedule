"""Schema, kết nối (SQLite khi chạy máy cá nhân, Postgres khi có DATABASE_URL) và dữ liệu khởi tạo."""
import hashlib
import json
import os
import secrets
import sqlite3
import time
from datetime import date, datetime, timedelta

os.environ.setdefault("TZ", "Asia/Ho_Chi_Minh")
if hasattr(time, "tzset"):  # Linux / macOS (Render); Windows dùng giờ máy
    time.tzset()

DB_PATH = os.environ.get("CTV_DB", os.path.join(os.path.dirname(__file__), "..", "data", "ctv.db"))
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, team_id INTEGER REFERENCES teams(id),
  hourly_rate INTEGER NOT NULL DEFAULT 25000);
CREATE TABLE IF NOT EXISTS shift_types (
  code TEXT PRIMARY KEY, name TEXT NOT NULL, start TEXT NOT NULL, "end" TEXT NOT NULL,
  reg_min TEXT NOT NULL, reg_max TEXT NOT NULL, sort INTEGER NOT NULL DEFAULT 0,
  need_min INTEGER NOT NULL DEFAULT 0, need_max INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL,
  name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'ctv', team_id INTEGER REFERENCES teams(id),
  phone TEXT DEFAULT '', email TEXT DEFAULT '', code TEXT DEFAULT '',
  active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, must_change_pw INTEGER NOT NULL DEFAULT 0,
  hourly_rate INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reg_months (ym TEXT PRIMARY KEY, open INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS availability (
  user_id INTEGER NOT NULL, ym TEXT NOT NULL, slots TEXT NOT NULL, status TEXT NOT NULL,
  updated_at TEXT NOT NULL, PRIMARY KEY (user_id, ym));
CREATE TABLE IF NOT EXISTS schedules (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), date TEXT NOT NULL,
  shift_code TEXT NOT NULL, start TEXT NOT NULL, "end" TEXT NOT NULL,
  position_id INTEGER REFERENCES positions(id),
  note TEXT DEFAULT '', plan TEXT, approved_at TEXT, approved_by TEXT, source TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS ix_sched_date ON schedules(date);
CREATE INDEX IF NOT EXISTS ix_sched_user ON schedules(user_id, date);
CREATE TABLE IF NOT EXISTS attendance (
  schedule_id INTEGER PRIMARY KEY REFERENCES schedules(id) ON DELETE CASCADE,
  check_in TEXT, check_out TEXT, late_min INTEGER NOT NULL DEFAULT 0, note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS swaps (
  id INTEGER PRIMARY KEY, schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
  from_user INTEGER NOT NULL, to_user INTEGER NOT NULL, reason TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL,
  handled_by TEXT, handled_at TEXT, swap_schedule_id INTEGER);
CREATE TABLE IF NOT EXISTS salaries (
  user_id INTEGER NOT NULL, ym TEXT NOT NULL, bonus INTEGER NOT NULL DEFAULT 0,
  deduction INTEGER NOT NULL DEFAULT 0, note TEXT DEFAULT '', PRIMARY KEY (user_id, ym));
CREATE TABLE IF NOT EXISTS salary_months (ym TEXT PRIMARY KEY, published INTEGER NOT NULL DEFAULT 0, published_at TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS qc_errors (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), ym TEXT NOT NULL, date TEXT NOT NULL,
  ticket TEXT DEFAULT '', error TEXT DEFAULT '', note TEXT DEFAULT '', penalty TEXT DEFAULT '',
  amount INTEGER NOT NULL DEFAULT 0, category TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_qc_ym ON qc_errors(ym, user_id);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notification_reads (user_id INTEGER NOT NULL, notification_id INTEGER NOT NULL,
  PRIMARY KEY (user_id, notification_id));
CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY, user_id INTEGER, actor TEXT NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pip_plans (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), status TEXT NOT NULL DEFAULT 'active',
  reason TEXT DEFAULT '', goals TEXT DEFAULT '', start_date TEXT NOT NULL, end_date TEXT NOT NULL,
  owner TEXT DEFAULT '', conclusion TEXT DEFAULT '', created_at TEXT NOT NULL, closed_at TEXT);
CREATE INDEX IF NOT EXISTS ix_pip_user ON pip_plans(user_id);
CREATE TABLE IF NOT EXISTS pip_reviews (
  id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES pip_plans(id) ON DELETE CASCADE, user_id INTEGER NOT NULL,
  schedule_ids TEXT DEFAULT '', shifts_text TEXT DEFAULT '', rating TEXT DEFAULT '', content TEXT DEFAULT '',
  author TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  last_admin_at TEXT, last_ctv_at TEXT, ctv_seen_at TEXT, admin_seen_at TEXT);
CREATE INDEX IF NOT EXISTS ix_pipr_plan ON pip_reviews(plan_id);
CREATE TABLE IF NOT EXISTS pip_comments (
  id INTEGER PRIMARY KEY, review_id INTEGER NOT NULL REFERENCES pip_reviews(id) ON DELETE CASCADE,
  user_id INTEGER, author TEXT NOT NULL, role TEXT NOT NULL, body TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_pipc_review ON pip_comments(review_id);
CREATE TABLE IF NOT EXISTS pip_images (
  id INTEGER PRIMARY KEY, review_id INTEGER NOT NULL REFERENCES pip_reviews(id) ON DELETE CASCADE,
  comment_id INTEGER, mime TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_pipi_review ON pip_images(review_id);
CREATE TABLE IF NOT EXISTS hb_edits (
  id INTEGER PRIMARY KEY, sheet TEXT NOT NULL, gid TEXT NOT NULL, op TEXT NOT NULL, rown INTEGER NOT NULL,
  old TEXT, vals TEXT, status TEXT NOT NULL DEFAULT 'pending', msg TEXT, user_name TEXT, created_at TEXT NOT NULL, done_at TEXT);
CREATE INDEX IF NOT EXISTS ix_hbe_status ON hb_edits(status);
CREATE TABLE IF NOT EXISTS qc_comments (
  id INTEGER PRIMARY KEY, qc_id INTEGER NOT NULL REFERENCES qc_errors(id) ON DELETE CASCADE,
  user_id INTEGER, author TEXT NOT NULL, role TEXT NOT NULL, body TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_qcc_qc ON qc_comments(qc_id);
CREATE TABLE IF NOT EXISTS qc_images (
  id INTEGER PRIMARY KEY, qc_id INTEGER NOT NULL, comment_id INTEGER NOT NULL, mime TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_qci_c ON qc_images(comment_id);
CREATE TABLE IF NOT EXISTS milo_mails (
  id TEXT PRIMARY KEY, at INTEGER NOT NULL, addrs TEXT NOT NULL, sender TEXT DEFAULT '', subject TEXT DEFAULT '', body TEXT NOT NULL);
"""

# Đi muộn quá số phút này được đánh dấu "muộn" (chỉ để theo dõi, không tự trừ lương —
# tiền phạt được ghi ở mục Lỗi QC)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_pw(pw: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${h}"


def check_pw(pw: str, stored: str) -> bool:
    salt, _ = stored.split("$", 1)
    return secrets.compare_digest(hash_pw(pw, salt), stored)


def connect():
    if DATABASE_URL:
        from .pg import PgConnection
        return PgConnection(DATABASE_URL)
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    con = connect()
    if DATABASE_URL:
        from .pg import schema
        con.executescript(schema(SCHEMA))
    else:
        con.executescript(SCHEMA)
    migrate(con)
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed(con)
    con.commit()
    con.close()


def migrate(con):
    """Thêm cột cho DB cũ. Ca nhập từ sheet (đã có bản ghi attendance) coi như đã duyệt."""
    qcols = {r[1] for r in con.execute("PRAGMA table_info(qc_errors)")}
    for c in ("last_ctv_at", "last_admin_at", "ctv_seen_at", "admin_seen_at"):  # phản hồi lỗi QC: dấu "mới" cho 2 phía
        if c not in qcols:
            con.execute(f"ALTER TABLE qc_errors ADD COLUMN {c} TEXT")
    if "viewer_id" not in {r[1] for r in con.execute("PRAGMA table_info(sessions)")}:
        con.execute("ALTER TABLE sessions ADD COLUMN viewer_id INTEGER")  # phiên "xem như CTV" do admin mở (chỉ xem)
    if "must_change_pw" not in {r[1] for r in con.execute("PRAGMA table_info(users)")}:
        con.execute("ALTER TABLE users ADD COLUMN must_change_pw INTEGER NOT NULL DEFAULT 0")
        # ai còn dùng mật khẩu mặc định thì bắt đổi ở lần đăng nhập tới
        for r in con.execute("SELECT id, password_hash FROM users").fetchall():
            if check_pw("123456", r[1]) or check_pw("admin123", r[1]):
                con.execute("UPDATE users SET must_change_pw=1 WHERE id=?", (r[0],))
    if "hourly_rate" not in {r[1] for r in con.execute("PRAGMA table_info(users)")}:  # mức lương / giờ riêng; 0 = theo đơn giá vị trí
        con.execute("ALTER TABLE users ADD COLUMN hourly_rate INTEGER NOT NULL DEFAULT 0")
    if "cccd" not in {r[1] for r in con.execute("PRAGMA table_info(users)")}:  # số CCCD
        con.execute("ALTER TABLE users ADD COLUMN cccd TEXT DEFAULT ''")
    if "source" not in {r[1] for r in con.execute("PRAGMA table_info(schedules)")}:
        con.execute("ALTER TABLE schedules ADD COLUMN source TEXT DEFAULT ''")  # 'auto' = hệ thống tự xếp
    scols = {r[1] for r in con.execute("PRAGMA table_info(shift_types)")}
    if "need_min" not in scols:  # chỉ tiêu số CTV mỗi ca: sáng 2, chiều 3, tối 5–6
        con.execute("ALTER TABLE shift_types ADD COLUMN need_min INTEGER NOT NULL DEFAULT 0")
        con.execute("ALTER TABLE shift_types ADD COLUMN need_max INTEGER NOT NULL DEFAULT 0")
        for code, lo, hi in (("sang", 2, 2), ("chieu", 3, 3), ("toi", 5, 6)):
            con.execute("UPDATE shift_types SET need_min=?, need_max=? WHERE code=?", (lo, hi, code))
    if "swap_schedule_id" not in {r[1] for r in con.execute("PRAGMA table_info(swaps)")}:
        con.execute("ALTER TABLE swaps ADD COLUMN swap_schedule_id INTEGER")  # đổi chéo: ca của người nhận chuyển lại cho người xin
    cols = {r[1] for r in con.execute("PRAGMA table_info(schedules)")}
    if "approved_at" not in cols:
        for c in ("note TEXT DEFAULT ''", "plan TEXT", "approved_at TEXT", "approved_by TEXT"):
            if c.split()[0] not in cols:
                con.execute(f"ALTER TABLE schedules ADD COLUMN {c}")
        con.execute("""UPDATE schedules SET approved_at=?, approved_by='Nhập từ Google Sheet'
                       WHERE id IN (SELECT schedule_id FROM attendance)""", (now_str(),))


def seed(con):
    """Cấu hình ban đầu + tài khoản admin. Dữ liệu CTV thật nhập bằng server/import_sheet.py."""
    ts = now_str()
    con.execute("INSERT INTO teams(id, name) VALUES (1, 'QS'), (2, 'ĐP')")
    con.executemany("INSERT INTO positions(id, name, team_id, hourly_rate) VALUES (?,?,?,?)", [
        (1, "Page Hotline", 1, 25000),
        (2, "Page Hotline Monitor", 1, 25000)])
    con.executemany('INSERT INTO shift_types(code, name, start, "end", reg_min, reg_max, sort) VALUES (?,?,?,?,?,?,?)', [
        ("sang", "Ca Sáng", "08:30", "12:00", "08:30", "12:00", 1),
        ("chieu", "Ca Chiều", "13:30", "18:00", "13:30", "18:00", 2),
        ("toi", "Ca Tối", "18:00", "22:00", "18:00", "22:00", 3)])
    for code, lo, hi in (("sang", 2, 2), ("chieu", 3, 3), ("toi", 5, 6)):
        con.execute("UPDATE shift_types SET need_min=?, need_max=? WHERE code=?", (lo, hi, code))
    pw = os.environ.get("ADMIN_PASSWORD") or "admin123"
    con.execute("INSERT INTO users(username, password_hash, name, role, created_at, must_change_pw) VALUES (?,?,?,?,?,?)",
                ("admin", hash_pw(pw), "Quản trị viên", "admin", ts, 0 if os.environ.get("ADMIN_PASSWORD") else 1))
    if DATABASE_URL:
        from .pg import fix_sequences
        fix_sequences(con)
    con.execute("INSERT INTO logs(user_id, actor, action, created_at) VALUES (NULL, 'Hệ thống', 'Khởi tạo hệ thống', ?)", (ts,))


def get_setting(con, key: str, default: str = "") -> str:
    r = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r[0] if r else default


def set_setting(con, key: str, value: str):
    con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", (key, value))


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def row(cur) -> dict | None:
    r = cur.fetchone()
    return dict(r) if r else None


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False)
