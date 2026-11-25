"""Đẩy lịch trực đã duyệt lên tab "Lịch trực" của Google Sheet.

Bố cục tab (đọc trực tiếp từ sheet, không cố định cứng):
  - Hàng 8: ngày (dd/mm), mỗi cột 1 ngày.
  - Hàng 10–20: các ô điền CTV. Cột B = ca (Tối / Sáng / Chiều, để trống = cùng ca ở trên),
    cột C = vị trí ("Trực Page + Hotline" hoặc "Trực monitor").

Ghi sheet qua Google Apps Script web app (người dùng tự triển khai trong sheet, xem apps_script()),
portal gửi các vùng ô cần ghi + mã bảo mật.
"""
import csv
import io
import os
import json
import re
import urllib.request
from datetime import date, timedelta

from . import handbook

DEFAULT_SHEET = os.environ.get("PAYROLL_SHEET_ID", "")  # sheet có tab "Lịch trực"
TAB = "Lịch trực"
DATE_ROW = 8
FIRST_ROW, LAST_ROW = 10, 20
STD = {"sang": ("08:30", "12:00"), "chieu": ("13:30", "18:00"), "toi": ("18:00", "22:00")}


class SyncError(Exception):
    pass


def col_letter(i: int) -> str:
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def group_of(code: str) -> str:
    f = handbook.fold(code).strip()
    for g in ("toi", "chieu", "sang"):
        if f == g or re.search(rf"(^|[^a-z]){g}([^a-z]|$)", f):
            return g
    return f


def read_layout(sheet_id: str):
    tabs = handbook.list_tabs(sheet_id, refresh=True)[0]
    tab = next((t for t in tabs if handbook.fold(t["name"]).strip() == handbook.fold(TAB)), None)
    if not tab:
        raise SyncError(f"Không tìm thấy tab “{TAB}” trong sheet")
    rows = handbook.fetch_rows(sheet_id, tab["gid"])
    dates = {}
    for c, v in enumerate(rows[DATE_ROW - 1] if len(rows) >= DATE_ROW else []):
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", v.strip())
        if m:
            dates.setdefault((int(m.group(1)), int(m.group(2))), c)
    slots, shift = [], None
    for r in range(FIRST_ROW, LAST_ROW + 1):
        line = rows[r - 1] if r - 1 < len(rows) else []
        b = handbook.fold(line[1]).strip() if len(line) > 1 else ""
        if b:
            shift = group_of(b)
        kind = "monitor" if len(line) > 2 and "monitor" in handbook.fold(line[2]) else "ph"
        slots.append({"row": r, "shift": shift, "kind": kind})
    return tab["name"], rows, dates, slots


def _hm(t: str) -> str:
    h, m = t.split(":")
    return str(int(h)) if m == "00" else f"{int(h)}:{m}"


def label(s: dict, group: str, kind_in_sheet: str) -> str:
    out = s["username"]
    extra = []
    std = STD.get(group)
    if std and (s["start"], s["end"]) != std:
        extra.append(f"{_hm(s['start'])}-{_hm(s['end'])}h")
    if "kem" in handbook.fold(s.get("note") or ""):
        extra.append("kèm")
    return out + (f" ({', '.join(extra)})" if extra else "")


def build(schedules: list, start: date, sheet_id: str) -> dict:
    tab_name, rows, dates, slots = read_layout(sheet_id)
    groups = {}
    for sl in slots:
        groups.setdefault((sl["shift"], sl["kind"]), []).append(sl["row"])
    days, missing, unplaced = [], [], []
    for i in range(7):
        d = start + timedelta(days=i)
        col = dates.get((d.day, d.month))
        if col is None:
            missing.append(d.isoformat())
            continue
        buckets = {}
        for s in sorted((x for x in schedules if x["date"] == d.isoformat()), key=lambda x: (x["start"], x["username"])):
            g = group_of(s["shift_code"])
            kind = "monitor" if "monitor" in handbook.fold(s.get("position") or "") else "ph"
            key = (g, kind) if (g, kind) in groups else (g, "ph") if (g, "ph") in groups else None
            if not key:
                unplaced.append(f"{d.strftime('%d/%m')} {s['username']} ({s['start']}-{s['end']})")
                continue
            buckets.setdefault(key, []).append((s["username"].lower(), label(s, g, key[1])))
        current = [(rows[r - 1][col] if r - 1 < len(rows) and col < len(rows[r - 1]) else "") for r in range(FIRST_ROW, LAST_ROW + 1)]
        values = [""] * (LAST_ROW - FIRST_ROW + 1)
        overflow = []
        for key, rws in groups.items():
            items = buckets.get(key, [])
            if len(items) > len(rws):  # nhiều người hơn số ô → gộp vào ô cuối, như cách sheet đang ghi "a/b"
                overflow.append(f"{d.strftime('%d/%m')} {key[0]}: {len(items)} người / {len(rws)} ô")
                rest = items[len(rws) - 1:]
                items = items[:len(rws) - 1] + [(rest[0][0], "/".join(x[1] for x in rest))]
            # giữ nguyên ô của người đã có trong sheet, người mới vào ô trống → sheet không bị xáo thứ tự
            placed, left = {}, list(items)
            for rw in rws:
                who = re.split(r"[\s/(]", current[rw - FIRST_ROW].strip().lower())[0]
                hit = next((x for x in left if who and x[0] == who), None)
                if hit:
                    placed[rw] = hit[1]
                    left.remove(hit)
            for rw in rws:
                if rw not in placed and left:
                    placed[rw] = left.pop(0)[1]
            for rw in rws:
                values[rw - FIRST_ROW] = placed.get(rw, "")
        letter = col_letter(col)
        days.append({"date": d.isoformat(), "col": letter, "range": f"{letter}{FIRST_ROW}:{letter}{LAST_ROW}",
                     "values": values, "current": current, "overflow": overflow})
    return {"tab": tab_name, "slots": slots, "days": days, "missing": missing, "unplaced": unplaced,
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}"}


def push(url: str, token: str, tab: str, days: list) -> dict:
    payload = {"token": token, "sheet": tab, "updates": [{"range": d["range"], "values": [[v] for v in d["values"]]} for d in days]}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            text = r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        raise SyncError(f"Không gọi được Apps Script: {e}")
    try:
        res = json.loads(text)
    except ValueError:
        raise SyncError("Apps Script trả về không đúng định dạng — kiểm tra lại link triển khai (Web app, quyền truy cập: Bất kỳ ai)")
    if not res.get("ok"):
        raise SyncError(res.get("error") or "Apps Script báo lỗi")
    return res


def apps_script(token: str) -> str:
    return f"""// Cổng CTV → ghi lịch trực vào sheet. Dán vào Tiện ích mở rộng → Apps Script, rồi Triển khai → Ứng dụng web.
const TOKEN = '{token}';

function doPost(e) {{
  const body = JSON.parse(e.postData.contents);
  if (body.token !== TOKEN) return out({{ ok: false, error: 'Sai mã bảo mật' }});
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(body.sheet);
  if (!sh) return out({{ ok: false, error: 'Không thấy tab ' + body.sheet }});
  body.updates.forEach(u => sh.getRange(u.range).setValues(u.values));
  return out({{ ok: true, updated: body.updates.length }});
}}

function out(o) {{
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}}
"""
