"""Chạy trên Postgres (Neon / Supabase…) với cùng câu SQL kiểu SQLite của app.

Khi có biến môi trường DATABASE_URL, db.connect() trả về PgConnection thay vì sqlite3:
  - '?'                      → '%s'
  - INSERT OR REPLACE        → INSERT … ON CONFLICT (khoá) DO UPDATE
  - INSERT OR IGNORE         → INSERT … ON CONFLICT DO NOTHING
  - INSERT vào bảng có id    → thêm RETURNING id để có cursor.lastrowid
  - username = ?             → lower(username) = lower(?)   (SQLite đang dùng COLLATE NOCASE)
  - PRAGMA table_info(t)     → information_schema.columns
Hàng trả về hỗ trợ cả r[0] lẫn r["cột"] và dict(r), giống sqlite3.Row.
"""
import re
import threading
import time

import psycopg

UPSERT_KEYS = {"availability": ["user_id", "ym"], "reg_months": ["ym"], "salaries": ["user_id", "ym"],
               "salary_months": ["ym"], "settings": ["key"], "attendance": ["schedule_id"],
               "notification_reads": ["user_id", "notification_id"], "sessions": ["token"], "milo_mails": ["id"]}
ID_TABLES = {"teams", "positions", "users", "schedules", "swaps", "qc_errors", "notifications", "logs",
             "pip_plans", "pip_reviews", "pip_comments", "pip_images"}

_cache: dict = {}


def translate(sql: str) -> str | None:
    hit = _cache.get(sql)
    if hit is not None:
        return hit
    s = sql
    m = re.match(r"\s*PRAGMA\s+table_info\((\w+)\)\s*$", s, re.I)
    if m:
        out = ("SELECT ordinal_position - 1 AS cid, column_name AS name FROM information_schema.columns "
               f"WHERE table_schema = current_schema() AND table_name = '{m.group(1).lower()}' ORDER BY ordinal_position")
        _cache[sql] = out
        return out
    if re.match(r"\s*PRAGMA\b", s, re.I):
        _cache[sql] = ""
        return ""
    s = s.replace("%", "%%")
    s = re.sub(r"\b((?:\w+\.)?username)\s*=\s*\?", r"lower(\1) = lower(?)", s)
    m = re.match(r"\s*INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]*)\)", s, re.I)
    if m:
        table, cols = m.group(1), [c.strip() for c in m.group(2).split(",")]
        keys = UPSERT_KEYS[table]
        upd = [c for c in cols if c.strip('"') not in keys]
        s = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", s, count=1, flags=re.I).rstrip().rstrip(";")
        s += f" ON CONFLICT ({', '.join(keys)}) " + (f"DO UPDATE SET {', '.join(f'{c} = EXCLUDED.{c}' for c in upd)}" if upd else "DO NOTHING")
    elif re.match(r"\s*INSERT\s+OR\s+IGNORE\s+INTO", s, re.I):
        s = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s, count=1, flags=re.I).rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    s = s.replace("?", "%s")
    m = re.match(r"\s*INSERT\s+INTO\s+(\w+)", s, re.I)
    if m and m.group(1).lower() in ID_TABLES and not re.search(r"\bRETURNING\b", s, re.I):
        s = s.rstrip().rstrip(";") + " RETURNING id"
    _cache[sql] = s
    return s


def schema(sqlite_schema: str) -> str:
    s = re.sub(r"\bid INTEGER PRIMARY KEY\b", "id SERIAL PRIMARY KEY", sqlite_schema)
    s = s.replace(" COLLATE NOCASE", "")
    return s + "\nCREATE UNIQUE INDEX IF NOT EXISTS ux_users_username_lower ON users (lower(username));\n"


class Row(tuple):
    __slots__ = ()
    _idx: dict = {}

    def __getitem__(self, k):
        if isinstance(k, str):
            return tuple.__getitem__(self, self._idx[k])
        return tuple.__getitem__(self, k)

    def keys(self):
        return list(self._idx)


def _row_class(names):
    return type("Row", (Row,), {"__slots__": (), "_idx": {n: i for i, n in enumerate(names)}})


class Cursor:
    def __init__(self, cur, returning_id: bool):
        self._cur = cur
        self.rowcount = cur.rowcount
        self.lastrowid = None
        self._cls = _row_class([d.name for d in cur.description]) if cur.description else None
        if returning_id and cur.description:
            r = cur.fetchone()
            self.lastrowid = r[0] if r else None
            self._cls = None

    def fetchone(self):
        if not self._cls:
            return None
        r = self._cur.fetchone()
        return self._cls(r) if r is not None else None

    def fetchall(self):
        if not self._cls:
            return []
        return [self._cls(r) for r in self._cur.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


IDLE_MAX = 60  # giây: kết nối rảnh lâu hơn thì đóng → Neon tự ngủ (scale to zero), tiết kiệm giờ chạy gói free


class _Pool:
    def __init__(self, url: str, size: int = 5):
        self.url, self.size, self.idle, self.lock = url, size, [], threading.Lock()
        threading.Thread(target=self._reaper, daemon=True).start()

    def _reaper(self):
        while True:
            time.sleep(30)
            now, stale = time.time(), []
            with self.lock:
                keep = []
                for c, t in self.idle:
                    (stale if now - t > IDLE_MAX else keep).append((c, t))
                self.idle = keep
            for c, _ in stale:
                try:
                    c.close()
                except Exception:  # noqa: BLE001
                    pass

    def get(self):
        with self.lock:
            while self.idle:
                c, t = self.idle.pop()
                if not c.closed and time.time() - t <= IDLE_MAX:
                    return c
                try:
                    c.close()
                except Exception:  # noqa: BLE001
                    pass
        return psycopg.connect(self.url, autocommit=False, connect_timeout=15)

    def put(self, c):
        try:
            if c.closed:
                return
            c.rollback()
            with self.lock:
                if len(self.idle) < self.size:
                    self.idle.append((c, time.time()))
                    return
            c.close()
        except Exception:  # noqa: BLE001
            pass


_pools: dict = {}


class PgConnection:
    """Giống sqlite3.Connection ở những gì app dùng: execute / executemany / executescript / commit / close."""
    is_pg = True

    def __init__(self, url: str):
        self.pool = _pools.setdefault(url, _Pool(url))
        self.c = self.pool.get()
        self.fresh = True  # chưa chạy lệnh nào trong giao dịch → được phép kết nối lại nếu kết nối cũ đã chết

    def execute(self, sql: str, params=()):
        q = translate(sql)
        if q == "":
            return Cursor(self.c.cursor(), False)
        try:
            cur = self.c.cursor()
            cur.execute(q, tuple(params) if params else None)
        except psycopg.OperationalError:
            if not self.fresh:
                raise
            try:
                self.c.close()
            except Exception:  # noqa: BLE001
                pass
            self.c = psycopg.connect(self.pool.url, autocommit=False, connect_timeout=15)
            cur = self.c.cursor()
            cur.execute(q, tuple(params) if params else None)
        self.fresh = False
        return Cursor(cur, q.rstrip().endswith("RETURNING id") and "RETURNING id" not in sql)

    def executemany(self, sql: str, seq):
        q = translate(sql)
        if q.endswith(" RETURNING id"):
            q = q[: -len(" RETURNING id")]
        cur = self.c.cursor()
        cur.executemany(q, [tuple(p) for p in seq])
        self.fresh = False
        return Cursor(cur, False)

    def executescript(self, script: str):
        with self.c.cursor() as cur:
            for stmt in [x.strip() for x in script.split(";")]:
                if stmt:
                    cur.execute(stmt)
        self.fresh = False

    def commit(self):
        self.c.commit()
        self.fresh = True

    def rollback(self):
        self.c.rollback()
        self.fresh = True

    def close(self):
        self.pool.put(self.c)


def fix_sequences(con):
    """Sau khi chèn dữ liệu có sẵn id (seed / chuyển từ SQLite) → đẩy sequence lên id lớn nhất."""
    for t in sorted(ID_TABLES):
        con.execute(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE((SELECT MAX(id) FROM {t}), 0) + 1, false)")
