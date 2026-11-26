"""Tra cứu tài khoản Milo (tab "TK Milo" trong Tài liệu).

3 file Google Sheet chỉ chia sẻ trong công ty → Apps Script (chạy bằng tài khoản công ty của admin) đọc và GỬI sang:
  - Nguồn 1 "ICC_Bàn giao học viên" / tab Format: dòng có Trình độ (G) hoặc Sản phẩm (H) chứa "English Adventure with Milo"
  - Nguồn 2 "data_handover" / tab ICC_15052024: dòng có Curriculum (S) chứa "English Adventure with Milo"
  - File VH "File làm việc Milo": họ tên, email, SĐT, ngày TT, UsernameIms, PasswordIms, tình trạng cấp TK, mail
Dữ liệu chỉ giữ trong bộ nhớ (không ghi DB → Neon không phải thức dậy). Server khởi động lại thì lần chạy kế tiếp của
Apps Script thấy server chưa có bản (so mã hash) và gửi lại toàn bộ.
Khớp học viên giữa các file theo email / SĐT (chuẩn hoá giống script đồng bộ Milo: email chữ thường, SĐT 84… → 0…).
"""
import re
import threading
import time
import unicodedata

_lock = threading.Lock()
_state = {"data": None, "hash": None, "at": None, "seen": None, "token": None}


class MiloError(Exception):
    pass


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", s).strip().lower()


def norm_email(s) -> str:
    return str(s or "").strip().lower()


def norm_phone(s) -> str:
    v = re.sub(r"\D", "", str(s or ""))
    if v.startswith("84") and len(v) >= 10:
        v = "0" + v[2:]
    elif v and not v.startswith("0") and len(v) == 9:  # ô số trong sheet mất số 0 đầu (VD 395517650)
        v = "0" + v
    return v


def _token(con) -> str:
    if _state["token"] is None:
        from . import db
        _state["token"] = db.get_setting(con, "milo_gas_token") or ""
    return _state["token"]


def ensure_token(con) -> str:
    import secrets
    from . import db
    tok = _token(con)
    if not tok:
        tok = secrets.token_urlsafe(18)
        db.set_setting(con, "milo_gas_token", tok)
        _state["token"] = tok
    return tok


def enabled(con) -> bool:
    return bool(_token(con))


def _rec(src: str, row, name, email, phone, **extra) -> dict:
    return {"src": src, "row": row, "name": str(name or "").strip(), "email": str(email or "").strip(),
            "phone": str(phone or "").strip(), "e": norm_email(email), "p": norm_phone(phone),
            "f": fold(f"{name} {email}"), **extra}


def receive(con, body: dict) -> dict:
    """body: {token, hash, ping: true} hoặc {token, hash, s1, s2, vh}. Trả need_full nếu server chưa có bản này."""
    tok = _token(con)
    if not tok or body.get("token") != tok:
        raise MiloError("Sai mã bảo mật")
    now = time.time()
    _state["seen"] = now
    h = str(body.get("hash") or "")
    if body.get("ping"):
        return {"ok": True, "need_full": h != _state["hash"]}
    try:
        recs = []
        for r in body.get("s1") or []:   # [dòng, ngày bàn giao, tên, SĐT, email]
            recs.append(_rec("s1", r[0], r[2], r[4], r[3], date=str(r[1])))
        for r in body.get("s2") or []:   # [dòng, CreatedAt, PaymentDate, tên, email, SĐT]
            recs.append(_rec("s2", r[0], r[3], r[4], r[5], created=str(r[1]), paid=str(r[2])))
        for r in body.get("vh") or []:   # [dòng, tên, email, SĐT, ngày TT, username, password, cấp TK, mail]
            recs.append(_rec("vh", r[0], r[1], r[2], r[3], paid=str(r[4]), username=str(r[5]).strip(),
                             password=str(r[6]).strip(), granted=str(r[7]).strip().upper() == "TRUE",
                             mail=str(r[8]).strip()))
    except (IndexError, TypeError) as e:
        raise MiloError(f"Dữ liệu không hợp lệ ({e.__class__.__name__})")
    by_e, by_p = {}, {}
    for i, r in enumerate(recs):
        if r["e"]:
            by_e.setdefault(r["e"], []).append(i)
        if r["p"]:
            by_p.setdefault(r["p"], []).append(i)
    with _lock:
        _state.update(data={"recs": recs, "by_e": by_e, "by_p": by_p}, hash=h, at=now)
    return {"ok": True, "need_full": False, "count": {s: sum(r["src"] == s for r in recs) for s in ("s1", "s2", "vh")}}


def status() -> dict:
    d = _state["data"]
    return {"data_at": _state["at"], "seen_at": _state["seen"],
            "count": {s: sum(r["src"] == s for r in d["recs"]) for s in ("s1", "s2", "vh")} if d else None}


def search(q: str, limit: int = 20) -> dict:
    d = _state["data"]
    if not d:
        return {"ready": False, "students": []}
    q = (q or "").strip()
    recs = d["recs"]
    digits = re.sub(r"\D", "", q)
    hits = set()
    if "@" in q:
        e = norm_email(q)
        hits = {i for i, r in enumerate(recs) if e in r["e"]}
    elif len(digits) >= 6 and len(digits) >= len(re.sub(r"\s", "", q)) - 2:  # gõ SĐT
        p = norm_phone(digits)
        p = p[1:] if p.startswith("0") else p  # khớp phần đuôi, không phụ thuộc số 0 / 84 đầu
        hits = {i for i, r in enumerate(recs) if p and p in r["p"]}
    else:
        ws = fold(q).split()
        if ws:
            hits = {i for i, r in enumerate(recs) if all(w in r["f"] for w in ws)}
    if not hits:
        return {"ready": True, "students": [], "more": False}
    # gom các bản ghi cùng email / SĐT thành 1 học viên (union-find)
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    todo, seen = list(hits), set()
    while todo:
        i = todo.pop()
        if i in seen:
            continue
        seen.add(i)
        find(i)
        r = recs[i]
        for j in (d["by_e"].get(r["e"], []) if r["e"] else []) + (d["by_p"].get(r["p"], []) if r["p"] else []):
            union(i, j)
            if j not in seen and len(seen) < 2000:
                todo.append(j)
    groups = {}
    for i in seen:
        groups.setdefault(find(i), []).append(i)
    students = []
    for idx in groups.values():
        rs = [recs[i] for i in sorted(idx, key=lambda i: (recs[i]["src"], recs[i]["row"]))]
        clean = lambda r: {k: v for k, v in r.items() if k not in ("e", "p", "f")}
        vh = [clean(r) for r in rs if r["src"] == "vh"]
        s1 = [clean(r) for r in rs if r["src"] == "s1"]
        s2 = [clean(r) for r in rs if r["src"] == "s2"]
        name = next((r["name"] for r in vh + s1 + s2 if r["name"]), "")
        if any(x["username"] and x["granted"] for x in vh):
            st = ("granted", "Đã cấp tài khoản")
        elif any(x["username"] for x in vh):
            st = ("created", "Đã có username, chưa tích cấp tài khoản")
        elif vh:
            st = ("in_vh", "Đã vào file VH, chưa tạo tài khoản")
        elif s1 or s2:
            st = ("handed", "Đã bàn giao, chưa có trong file VH")
        else:
            st = ("none", "Không thấy")
        students.append({"name": name, "emails": sorted({r["email"] for r in rs if r["email"]}, key=str.lower),
                         "phones": sorted({r["phone"] for r in rs if r["phone"]}), "status": st[0], "status_label": st[1],
                         "s1": s1, "s2": s2, "vh": vh, "direct": any(i in hits for i in idx)})
    students.sort(key=lambda s: (not s["direct"], fold(s["name"])))
    return {"ready": True, "students": students[:limit], "more": len(students) > limit}


def apps_script(token: str, portal: str, ids: dict) -> str:
    return f"""// Cổng CTV ← dữ liệu tài khoản Milo (tab "TK Milo" trong Tài liệu). Chạy bằng tài khoản công ty xem được 3 file.
// Cài: script.google.com → Dự án mới → dán code → 💾 Lưu → chọn hàm "setup" → ▶ Chạy → cho phép quyền.
// Sau đó script tự chạy 10 phút/lần: chỉ gửi khi dữ liệu đổi (hoặc portal vừa khởi động lại, chưa có dữ liệu).
const PORTAL = '{portal}/api/milo/push';
const TOKEN = '{token}';
const MILO = 'english adventure with milo';
const SRC1_ID = '{ids["s1"]}', SRC1_SHEET = 'Format', SRC1_START = 4;               // ICC_Bàn giao học viên
const SRC2_ID = '{ids["s2"]}', SRC2_SHEET = 'ICC_15052024', SRC2_START = 2;         // data_handover
const VH_ID = '{ids["vh"]}', VH_SHEET = 'File làm việc Milo', VH_START = 2;        // File làm việc Milo

function setup() {{
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'sync').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('sync').timeBased().everyMinutes(10).create();
  PropertiesService.getScriptProperties().deleteProperty('hash');
  sync(true);
}}

function col_(sh, start, c, n) {{ return sh.getRange(start, c, n, 1).getDisplayValues().map(r => r[0]); }}

function collect_() {{
  // Nguồn 1: A ngày bàn giao, D tên, E SĐT, F email, G trình độ, H sản phẩm
  const sh1 = SpreadsheetApp.openById(SRC1_ID).getSheetByName(SRC1_SHEET);
  if (!sh1) throw new Error('Không thấy tab ' + SRC1_SHEET);
  const s1 = [], n1 = sh1.getLastRow() - SRC1_START + 1;
  if (n1 > 0) sh1.getRange(SRC1_START, 1, n1, 8).getDisplayValues().forEach((r, i) => {{
    if ((r[6] + ' ' + r[7]).toLowerCase().indexOf(MILO) < 0) return;
    if (!r[3] && !r[4] && !r[5]) return;
    s1.push([SRC1_START + i, r[0], r[3], r[4], r[5]]);
  }});
  // Nguồn 2: B CreatedAt, K tên, N email, O SĐT, S curriculum, AH PaymentDate (đọc từng cột cho nhanh)
  const sh2 = SpreadsheetApp.openById(SRC2_ID).getSheetByName(SRC2_SHEET);
  if (!sh2) throw new Error('Không thấy tab ' + SRC2_SHEET);
  const s2 = [], n2 = sh2.getLastRow() - SRC2_START + 1;
  if (n2 > 0) {{
    const cur = col_(sh2, SRC2_START, 19, n2), b = col_(sh2, SRC2_START, 2, n2), k = col_(sh2, SRC2_START, 11, n2),
          nn = col_(sh2, SRC2_START, 14, n2), o = col_(sh2, SRC2_START, 15, n2), ah = col_(sh2, SRC2_START, 34, n2);
    cur.forEach((c, i) => {{
      if (String(c).toLowerCase().indexOf(MILO) < 0) return;
      if (!k[i] && !nn[i] && !o[i]) return;
      s2.push([SRC2_START + i, b[i], ah[i], k[i], nn[i], o[i]]);
    }});
  }}
  // File VH: F tên, G email, H SĐT, J ngày TT, L UsernameIms, M PasswordIms, N cấp TK (ô tích), O tình trạng mail
  const sh3 = SpreadsheetApp.openById(VH_ID).getSheetByName(VH_SHEET);
  if (!sh3) throw new Error('Không thấy tab ' + VH_SHEET);
  const vh = [], n3 = sh3.getLastRow() - VH_START + 1;
  if (n3 > 0) sh3.getRange(VH_START, 6, n3, 10).getDisplayValues().forEach((r, i) => {{
    if (!r[0] && !r[1] && !r[2]) return;
    vh.push([VH_START + i, r[0], r[1], r[2], r[4], r[6], r[7], r[8], r[9]]);
  }});
  return {{ s1: s1, s2: s2, vh: vh }};
}}

function post_(body) {{
  const res = UrlFetchApp.fetch(PORTAL, {{ method: 'post', contentType: 'application/json', payload: JSON.stringify(body), muteHttpExceptions: true }});
  if (res.getResponseCode() !== 200) throw new Error('Portal báo lỗi ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 300));
  return JSON.parse(res.getContentText());
}}

function sync(force) {{
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {{
    const p = PropertiesService.getScriptProperties();
    const data = collect_();
    const hash = Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, JSON.stringify(data), Utilities.Charset.UTF_8));
    let send = force === true || hash !== p.getProperty('hash');
    if (!send) send = post_({{ token: TOKEN, hash: hash, ping: true }}).need_full;  // portal khởi động lại → gửi lại
    if (!send) {{ Logger.log('Không đổi'); return; }}
    const r = post_(Object.assign({{ token: TOKEN, hash: hash }}, data));
    p.setProperty('hash', hash);
    Logger.log('Đã gửi sang portal: nguồn 1 ' + data.s1.length + ' · nguồn 2 ' + data.s2.length + ' · file VH ' + data.vh.length + ' dòng');
  }} finally {{
    lock.releaseLock();
  }}
}}
"""
