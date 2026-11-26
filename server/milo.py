"""Tra cứu tài khoản Milo (tab "TK Milo" trong Tài liệu).

3 file Google Sheet chỉ chia sẻ trong công ty → Apps Script (chạy bằng tài khoản công ty của admin) đọc và GỬI sang:
  - Nguồn 1 "ICC_Bàn giao học viên" / tab Format: dòng có Trình độ (G) hoặc Sản phẩm (H) chứa "English Adventure with Milo"
  - Nguồn 2 "data_handover" / tab ICC_15052024: dòng có Curriculum (S) chứa "English Adventure with Milo"
  - File VH "File làm việc Milo": họ tên, email, SĐT, ngày TT, UsernameIms, PasswordIms, tình trạng cấp TK, mail
Dòng cũ gửi 1 lần và lưu DB (nén, chỉ ghi khi có thêm dòng cũ); mỗi 10 phút Apps Script chỉ đọc ~200 dòng cuối mỗi file
(phần đang được thêm / sửa) và gửi khi đổi — phần này chỉ giữ trong bộ nhớ.
Khớp học viên giữa các file theo email / SĐT (chuẩn hoá giống script đồng bộ Milo: email chữ thường, SĐT 84… → 0…).
"""
import re
import threading
import time
import unicodedata

_lock = threading.Lock()
_state = {"data": None, "hash": None, "at": None, "seen": None, "token": None, "archive": None, "live": None}


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


KEYS = ("s1", "s2", "vh")


def _make(src: str, r) -> dict:
    if src == "s1":    # [dòng, ngày bàn giao, tên, SĐT, email]
        return _rec("s1", r[0], r[2], r[4], r[3], date=str(r[1]))
    if src == "s2":    # [dòng, CreatedAt, PaymentDate, tên, email, SĐT]
        return _rec("s2", r[0], r[3], r[4], r[5], created=str(r[1]), paid=str(r[2]))
    # vh: [dòng, tên, email, SĐT, ngày TT, username, password, cấp TK, mail]
    return _rec("vh", r[0], r[1], r[2], r[3], paid=str(r[4]), username=str(r[5]).strip(), password=str(r[6]).strip(),
                granted=str(r[7]).strip().upper() == "TRUE", mail=str(r[8]).strip())


# Dòng cũ (bản lưu): gửi 1 lần, lưu DB (nén) — chỉ ghi lại khi thêm dòng cũ (hiếm).
# Dòng mới (live): ~200 dòng cuối mỗi file, Apps Script gửi khi đổi, chỉ giữ trong bộ nhớ.
def _archive(con=None) -> dict:
    if _state.get("archive") is None:
        import base64, json, zlib
        from . import db
        own = con is None
        con = con or db.connect()
        try:
            raw = db.get_setting(con, "milo_archive")
        finally:
            if own:
                con.close()
        arc = None
        if raw:
            try:
                arc = json.loads(zlib.decompress(base64.b64decode(raw)).decode("utf-8"))
            except Exception:  # noqa: BLE001
                arc = None
        _state["archive"] = arc or {"cursor": {k: 0 for k in KEYS}, "rows": {k: [] for k in KEYS}}
    return _state["archive"]


def _save_archive(con):
    import base64, json, zlib
    from . import db
    _state["archive"]["at"] = time.time()
    raw = base64.b64encode(zlib.compress(json.dumps(_state["archive"], ensure_ascii=False).encode("utf-8"), 9)).decode()
    db.set_setting(con, "milo_archive", raw)


def _rebuild():
    arc, live = _state["archive"], _state.get("live") or {k: [] for k in KEYS}
    recs = []
    try:
        for k in KEYS:
            cur = arc["cursor"].get(k, 0)
            recs += [_make(k, r) for r in arc["rows"].get(k, [])]
            recs += [_make(k, r) for r in live.get(k, []) if int(r[0]) >= cur]
    except (IndexError, TypeError, ValueError) as e:
        raise MiloError(f"Dữ liệu không hợp lệ ({e.__class__.__name__})")
    by_e, by_p = {}, {}
    for i, r in enumerate(recs):
        if r["e"]:
            by_e.setdefault(r["e"], []).append(i)
        if r["p"]:
            by_p.setdefault(r["p"], []).append(i)
    with _lock:
        _state["data"] = {"recs": recs, "by_e": by_e, "by_p": by_p}


def receive(con, body: dict) -> dict:
    """Apps Script gọi vào, body.op:
      state   → {archive: {nguồn: dòng đã lưu tới (không gồm)}, hash: mã bản live đang có}
      reset   → xoá bản lưu (chạy lại miloSetup)
      archive → {src, from, to, rows}: lưu các dòng Milo trong [from, to) của 1 nguồn
      live    → {hash, s1, s2, vh}: các dòng từ chỗ đã lưu tới cuối file"""
    tok = _token(con)
    if not tok or body.get("token") != tok:
        raise MiloError("Sai mã bảo mật")
    now = time.time()
    _state["seen"] = now
    op = body.get("op")
    arc = _archive(con)
    if op == "state":
        return {"ok": True, "archive": arc["cursor"], "hash": _state["hash"] if _state.get("live") is not None else None}
    if op == "reset":
        _state["archive"] = {"cursor": {k: 0 for k in KEYS}, "rows": {k: [] for k in KEYS}}
        _save_archive(con)
        _state.update(live=None, hash=None)
        _rebuild()
        return {"ok": True}
    if op == "archive":
        src = body.get("src")
        if src not in KEYS:
            raise MiloError("Nguồn không hợp lệ")
        try:
            lo, hi = int(body["from"]), int(body["to"])
            rows = [list(r) for r in body.get("rows") or [] if lo <= int(r[0]) < hi]
            for r in rows:
                _make(src, r)  # kiểm tra định dạng
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise MiloError(f"Dữ liệu không hợp lệ ({e.__class__.__name__})")
        arc["rows"][src] = [r for r in arc["rows"][src] if not lo <= int(r[0]) < hi] + rows
        arc["cursor"][src] = max(arc["cursor"].get(src, 0), hi)
        _save_archive(con)
        _state["at"] = now
        _rebuild()
        return {"ok": True, "archive": arc["cursor"]}
    if op == "live":
        _state["live"] = {k: [list(r) for r in body.get(k) or []] for k in KEYS}
        _state["hash"] = str(body.get("hash") or "")
        _state["at"] = now
        _rebuild()
        return {"ok": True, "count": status()["count"]}
    raise MiloError("Thao tác không hợp lệ — sao chép lại code Apps Script mới ở trang Quản trị")


def _ensure_loaded():
    """Sau khi server khởi động lại: nạp bản lưu từ DB (dòng cũ) để tra cứu được ngay."""
    if _state["data"] is None and _state.get("archive") is None:
        try:
            _archive()
            if any(_state["archive"]["cursor"].values()):
                _rebuild()
        except Exception:  # noqa: BLE001
            pass


def status() -> dict:
    _ensure_loaded()
    d = _state["data"]
    at = _state["at"] or ((_state.get("archive") or {}).get("at") if d else None)
    return {"data_at": at, "seen_at": _state["seen"],
            "count": {s: sum(r["src"] == s for r in d["recs"]) for s in ("s1", "s2", "vh")} if d else None}


def search(q: str, limit: int = 20) -> dict:
    _ensure_loaded()
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
// Cài: dán vào project Apps Script (có thể chung project với script Cẩm nang) → 💾 Lưu → chọn hàm "miloSetup" → ▶ Chạy → cho phép quyền.
// Mọi tên đều có tiền tố MILO_/milo để không trùng với code Cẩm nang trong cùng project.
// Chỉ lấy dòng có khoá "English Adventure with Milo" (Format: cột G/H · data_handover: cột S); file VH lấy mọi dòng có tên/email/SĐT.
// Dòng cũ gửi 1 lần rồi portal lưu lại; mỗi 10 phút chỉ đọc ~200 dòng cuối mỗi file (dòng mới / đang sửa), đổi mới gửi.
// Lần đầu đọc toàn bộ lịch sử theo từng đợt (mỗi lần chạy tối đa ~4 phút, chưa xong thì lần sau làm tiếp).
const MILO_PORTAL = '{portal}/api/milo/push';
const MILO_TOKEN = '{token}';
const MILO_PRODUCT = 'english adventure with milo';
const MILO_KEEP = 200, MILO_CHUNK = 5000, MILO_BUDGET_MS = 4 * 60 * 1000;
const MILO_SRC = {{
  s1: {{ id: '{ids["s1"]}', sheet: 'Format', start: 4 }},               // ICC_Bàn giao học viên
  s2: {{ id: '{ids["s2"]}', sheet: 'ICC_15052024', start: 2 }},         // data_handover
  vh: {{ id: '{ids["vh"]}', sheet: 'File làm việc Milo', start: 2 }},   // File làm việc Milo (VH)
}};

// Chạy 1 lần (hoặc chạy lại để gửi lại toàn bộ lịch sử nếu dòng cũ có sửa)
function miloSetup() {{
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'miloSync').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('miloSync').timeBased().everyMinutes(10).create();
  const p = PropertiesService.getScriptProperties();
  ['milo_hash', 'milo_t_s1', 'milo_t_s2', 'milo_t_vh'].forEach(k => p.deleteProperty(k));
  miloPost_({{ op: 'reset' }});
  miloSync();
}}

function miloSheet_(k) {{
  const sh = SpreadsheetApp.openById(MILO_SRC[k].id).getSheetByName(MILO_SRC[k].sheet);
  if (!sh) throw new Error('Không thấy tab ' + MILO_SRC[k].sheet);
  return sh;
}}

function miloCol_(sh, from, c, n) {{ return sh.getRange(from, c, n, 1).getDisplayValues().map(r => r[0]); }}

// Đọc các dòng [from, to) của 1 nguồn → mảng dòng đã lọc
function miloRead_(k, sh, from, to) {{
  const n = to - from, out = [];
  if (n <= 0) return out;
  if (k === 's1') {{  // A ngày bàn giao, D tên, E SĐT, F email, G trình độ, H sản phẩm
    sh.getRange(from, 1, n, 8).getDisplayValues().forEach((r, i) => {{
      if ((r[6] + ' ' + r[7]).toLowerCase().indexOf(MILO_PRODUCT) < 0) return;
      if (!r[3] && !r[4] && !r[5]) return;
      out.push([from + i, r[0], r[3], r[4], r[5]]);
    }});
  }} else if (k === 's2') {{  // S curriculum (lọc trước), B CreatedAt, K tên, N email, O SĐT, AH PaymentDate
    const cur = miloCol_(sh, from, 19, n), idx = [];
    cur.forEach((c, i) => {{ if (String(c).toLowerCase().indexOf(MILO_PRODUCT) >= 0) idx.push(i); }});
    if (!idx.length) return out;
    const b = miloCol_(sh, from, 2, n), k2 = miloCol_(sh, from, 11, n), nn = miloCol_(sh, from, 14, n),
          o = miloCol_(sh, from, 15, n), ah = miloCol_(sh, from, 34, n);
    idx.forEach(i => {{ if (k2[i] || nn[i] || o[i]) out.push([from + i, b[i], ah[i], k2[i], nn[i], o[i]]); }});
  }} else {{  // VH: F tên, G email, H SĐT, J ngày TT, L UsernameIms, M PasswordIms, N cấp TK, O mail
    sh.getRange(from, 6, n, 10).getDisplayValues().forEach((r, i) => {{
      if (!r[0] && !r[1] && !r[2]) return;
      out.push([from + i, r[0], r[1], r[2], r[4], r[6], r[7], r[8], r[9]]);
    }});
  }}
  return out;
}}

function miloPost_(body) {{
  body.token = MILO_TOKEN;
  const res = UrlFetchApp.fetch(MILO_PORTAL, {{ method: 'post', contentType: 'application/json', payload: JSON.stringify(body), muteHttpExceptions: true }});
  if (res.getResponseCode() !== 200) throw new Error('Portal báo lỗi ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 300));
  return JSON.parse(res.getContentText());
}}

function miloSync() {{
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return;
  const t0 = Date.now();
  try {{
    const p = PropertiesService.getScriptProperties();
    const st = miloPost_({{ op: 'state' }});
    const sheets = {{}}, last = {{}}, target = {{}};
    let done = true;
    Object.keys(MILO_SRC).forEach(k => {{
      sheets[k] = miloSheet_(k);
      last[k] = sheets[k].getLastRow() + 1;  // dòng sau dòng cuối
      // mốc lưu: giữ ~MILO_KEEP dòng cuối là "đang làm"; dồn mốc khi phần đang làm dài gấp đôi
      let tg = Number(p.getProperty('milo_t_' + k) || MILO_SRC[k].start);
      if (last[k] - tg > 2 * MILO_KEEP) tg = last[k] - MILO_KEEP;
      target[k] = Math.max(tg, MILO_SRC[k].start);
      p.setProperty('milo_t_' + k, String(target[k]));
      // gửi phần lưu còn thiếu theo từng đợt
      let from = Math.max(Number(st.archive[k] || 0), MILO_SRC[k].start);
      while (from < target[k]) {{
        if (Date.now() - t0 > MILO_BUDGET_MS) {{ done = false; break; }}
        const to = Math.min(from + MILO_CHUNK, target[k]);
        miloPost_({{ op: 'archive', src: k, from: from, to: to, rows: miloRead_(k, sheets[k], from, to) }});
        Logger.log('Đã lưu ' + MILO_SRC[k].sheet + ' dòng ' + from + '–' + (to - 1));
        from = to;
      }}
    }});
    if (!done) {{ Logger.log('Chưa lưu hết lịch sử, lần chạy sau (10 phút) làm tiếp'); return; }}
    // phần đang làm: từ mốc lưu tới cuối file
    const live = {{}};
    Object.keys(MILO_SRC).forEach(k => {{ live[k] = miloRead_(k, sheets[k], target[k], last[k]); }});
    const hash = Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, JSON.stringify([target, live]), Utilities.Charset.UTF_8));
    if (hash === st.hash) {{ Logger.log('Không đổi (' + Math.round((Date.now() - t0) / 1000) + 's)'); return; }}
    const r = miloPost_(Object.assign({{ op: 'live', hash: hash }}, live));
    const c = r.count || {{}};
    Logger.log('Đã gửi sang portal: nguồn 1 ' + c.s1 + ' · nguồn 2 ' + c.s2 + ' · file VH ' + c.vh + ' dòng (' + Math.round((Date.now() - t0) / 1000) + 's)');
  }} finally {{
    lock.releaseLock();
  }}
}}
"""
