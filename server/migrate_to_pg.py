"""Chuyển toàn bộ dữ liệu từ SQLite (data/ctv.db) sang Postgres (Neon / Supabase).

    1. Ghi chuỗi kết nối vào file .env (không commit):   DATABASE_URL=postgresql://...?sslmode=require
    2. python -m server.migrate_to_pg            # chạy thử: chỉ kiểm tra kết nối + đếm dữ liệu
       python -m server.migrate_to_pg --go       # chuyển thật (Postgres phải đang trống)
       python -m server.migrate_to_pg --go --replace   # xoá dữ liệu đang có trên Postgres rồi chuyển lại
"""
import argparse
import os
import sqlite3
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
TABLES = ["teams", "positions", "shift_types", "users", "reg_months", "availability", "schedules", "attendance",
          "swaps", "salaries", "salary_months", "settings", "qc_errors", "notifications", "notification_reads", "logs"]


def load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.split("#", 1)[0].strip() if not line.lstrip().startswith("DATABASE_URL") else line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()
    load_env()
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgres"):
        sys.exit("Chưa có DATABASE_URL (postgresql://...) trong .env")

    # 1) SQLite: chạy migrate để có đủ cột mới (must_change_pw…)
    saved = os.environ.pop("DATABASE_URL")
    from server import db
    db.DATABASE_URL = ""
    db.init_db()
    src = sqlite3.connect(db.DB_PATH)
    src.row_factory = sqlite3.Row
    os.environ["DATABASE_URL"] = saved
    db.DATABASE_URL = saved

    from server.pg import PgConnection, fix_sequences, schema
    dst = PgConnection(saved)
    host = saved.split("@")[-1].split("/")[0]
    print(f"Kết nối Postgres OK: {host}")
    dst.executescript(schema(db.SCHEMA))
    dst.commit()

    counts = {t: src.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    existing = {t: dst.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    print("Bảng            SQLite   Postgres hiện có")
    for t in TABLES:
        print(f"  {t:<15}{counts[t]:>7}   {existing[t]:>7}")
    if not a.go:
        print("\nChạy thử xong. Thêm --go để chuyển thật.")
        return
    if any(existing.values()):
        if not a.replace:
            sys.exit("\nPostgres đã có dữ liệu. Dùng --go --replace nếu muốn xoá và chuyển lại.")
        dst.execute("TRUNCATE " + ", ".join(TABLES) + ", sessions RESTART IDENTITY CASCADE")

    for t in TABLES:
        cols_src = [r[1] for r in src.execute(f"PRAGMA table_info({t})")]
        cols_dst = {r[1] for r in dst.execute(f"PRAGMA table_info({t})")}
        cols = [c for c in cols_src if c in cols_dst]
        data = [tuple(r[c] for c in cols) for r in src.execute(f"SELECT * FROM {t}")]
        if data:
            qcols = ", ".join(f'"{c}"' for c in cols)
            dst.executemany(f"INSERT INTO {t}({qcols}) VALUES ({', '.join('?' * len(cols))})", data)
        print(f"  ✓ {t}: {len(data)} dòng")
    fix_sequences(dst)
    dst.commit()
    bad = [t for t in TABLES if dst.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] != counts[t]]
    print("\nHoàn tất." if not bad else f"\nCảnh báo: số dòng lệch ở {bad}")
    dst.close()


if __name__ == "__main__":
    main()
