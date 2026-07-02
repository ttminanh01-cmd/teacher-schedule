import html
import re
from datetime import date, datetime, timedelta

import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Tra cứu thông tin", page_icon="📚", layout="wide")

st.markdown("""
<style>
.stSelectbox, .stTextInput, .stDateInput, .stMultiSelect { max-width: 320px; }
</style>
""", unsafe_allow_html=True)

SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "")
DAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
WEEKDAY_TO_THU = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5",
                  4: "Thứ 6", 5: "Thứ 7", 6: "Chủ nhật"}

# Mỗi chương trình có 1 sheet lịch GV + 1 sheet lớp học + 1 sheet xử lý phát sinh riêng.
PROGRAMS = {
    "EZP": {"sheet_gv": "Data lịch GV EZP", "sheet_lop": "Data lớp học EZP",
            "sheet_xuly": "Xử lý phát sinh EZP"},
    "IE": {"sheet_gv": "Data lịch GV IE", "sheet_lop": "Data lớp học IE",
           "sheet_xuly": "Xử lý phát sinh IE"},
}

# 13 cột đầu của cả 2 sheet lịch GV theo cùng thứ tự (chỉ khác nhãn cột).
GV_COLS = ["Quốc tịch", "Mã GV", "Giáo viên", "Trình độ giảng dạy",
           "Khung giờ 1", "Khung giờ 2"] + DAYS

# Data GV EZP/IE đã được lọc sẵn chỉ còn GV đang làm việc — có mặt trong
# sheet này = đang làm việc, không có mặt = đã nghỉ việc.
GV_STATUS_CONFIG = {
    "EZP": {"sheet": "Data GV EZP", "code_col": "ID"},
    "IE": {"sheet": "Data GV IE", "code_col": "Mã GV"},
}

# 2 sheet đơn nghỉ (chung cho cả EZP+IE, nối với GV qua Mã BOS GV <-> ID BOS).
LEAVE_SHEETS = ["Đơn nghỉ ngắn", "Đơn nghỉ dài"]
LEAVE_NEEDED_COLS = ["Tên giáo viên", "ID BOS", "Loại đơn", "Ngày bắt đầu",
                      "Ngày kết thúc", "VHGV xử lý"]

SHEET_HOCVIEN = "Tra cứu thông tin HV"
HOCVIEN_COLS = ["Sản phẩm", "ID", "ID BOS", "Tên", "Email", "Số điện thoại",
                "Trạng thái hv", "Mã lớp", "Ngày khai giảng", "Ngày kết thúc dự kiến",
                "Trạng thái lớp", "Lịch học", "Giáo viên", "Tổng buổi", "Buổi còn lại"]

# ===== GOOGLE SHEETS =====

def get_gc():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scopes)
    return gspread.authorize(creds)


def _pad_rows(rows, width):
    """Chuẩn hoá độ dài mỗi dòng về đúng `width` cột."""
    out = []
    for r in rows:
        if len(r) < width:
            r = r + [""] * (width - len(r))
        else:
            r = r[:width]
        out.append(r)
    return out


_DATE_RE = re.compile(r"^(\d{1,4})[/\-](\d{1,2})[/\-](\d{1,4})$")


def format_date(raw: str, dayfirst=True) -> str:
    """Chuẩn hoá ngày về dd/mm/yyyy.
    dayfirst=True: nguồn là d/m/y. dayfirst=False: nguồn là m/d/y.
    dayfirst=None: tự đoán — nếu 1 trong 2 số > 12 thì số đó chắc chắn là
    ngày (chỉ có 1 cách hợp lệ để đọc), còn mơ hồ (cả 2 số ≤12) thì mặc
    định coi là m/d/y. Dùng khi 1 sheet lẫn cả 2 định dạng ngày tháng."""
    raw = (raw or "").strip()
    m = _DATE_RE.match(raw)
    if not m:
        return raw
    a, b, c = m.groups()
    if len(a) == 4:
        year, month, day = a, b, c
    elif dayfirst is None:
        if int(a) > 12:
            day, month, year = a, b, c
        elif int(b) > 12:
            month, day, year = a, b, c
        else:
            month, day, year = a, b, c
    elif dayfirst:
        day, month, year = a, b, c
    else:
        month, day, year = a, b, c
    try:
        return f"{int(day):02d}/{int(month):02d}/{int(year):04d}"
    except ValueError:
        return raw


def _load_gv_program(program: str) -> pd.DataFrame:
    ws = get_gc().open_by_key(SPREADSHEET_ID).worksheet(PROGRAMS[program]["sheet_gv"])
    rows = ws.get_all_values()
    if len(rows) < 2:
        return pd.DataFrame(columns=["Chương trình"] + GV_COLS + ["Mã BOS GV"])

    header = rows[0]
    bos_idx = next((i for i, h in enumerate(header) if "bos" in h.strip().lower()), None)
    width = max(len(GV_COLS), (bos_idx + 1) if bos_idx is not None else 0)

    data = _pad_rows(rows[1:], width)
    df = pd.DataFrame([r[:len(GV_COLS)] for r in data], columns=GV_COLS)
    df["Mã BOS GV"] = [r[bos_idx].strip() if bos_idx is not None else "" for r in data]
    df = df[df["Mã GV"].str.strip() != ""]
    df.insert(0, "Chương trình", program)
    return df.reset_index(drop=True)


@st.cache_data(ttl=300)
def load_gv() -> pd.DataFrame:
    frames = [_load_gv_program(p) for p in PROGRAMS]
    return pd.concat(frames, ignore_index=True)


def _load_gv_status_program(program: str) -> set:
    """Tập hợp Mã GV còn đang làm việc, theo Data GV EZP/IE (đã lọc sẵn).
    2 sheet có cấu trúc cột khác nhau nên dò cột mã theo tên."""
    cfg = GV_STATUS_CONFIG[program]
    ws = get_gc().open_by_key(SPREADSHEET_ID).worksheet(cfg["sheet"])
    rows = ws.get_all_values()
    if len(rows) < 2:
        return set()

    header = [h.strip() for h in rows[0]]
    try:
        code_idx = header.index(cfg["code_col"])
    except ValueError:
        return set()

    return {r[code_idx].strip() for r in rows[1:] if code_idx < len(r) and r[code_idx].strip()}


@st.cache_data(ttl=300)
def load_active_gv_codes() -> dict:
    """{Chương trình: set(Mã GV đang làm việc)}."""
    return {p: _load_gv_status_program(p) for p in GV_STATUS_CONFIG}


def _load_leave_sheet(sheet_name: str) -> pd.DataFrame:
    """Đơn nghỉ ngắn / Đơn nghỉ dài: chung 1 danh sách cột cần, dò theo tên cột."""
    ws = get_gc().open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
    rows = ws.get_all_values()
    if len(rows) < 2:
        return pd.DataFrame(columns=LEAVE_NEEDED_COLS)

    header = [h.strip() for h in rows[0]]
    idx = {col: (header.index(col) if col in header else None) for col in LEAVE_NEEDED_COLS}
    width = max((i for i in idx.values() if i is not None), default=-1) + 1
    if width == 0:
        return pd.DataFrame(columns=LEAVE_NEEDED_COLS)

    out = []
    for r in _pad_rows(rows[1:], width):
        row = {col: (r[i].strip() if i is not None else "") for col, i in idx.items()}
        if row["ID BOS"] or row["Tên giáo viên"]:
            out.append(row)
    return pd.DataFrame(out, columns=LEAVE_NEEDED_COLS)


@st.cache_data(ttl=300)
def load_leave_requests() -> pd.DataFrame:
    frames = [_load_leave_sheet(s) for s in LEAVE_SHEETS]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=LEAVE_NEEDED_COLS)
    for col in ["Ngày bắt đầu", "Ngày kết thúc"]:
        df[col] = df[col].apply(lambda v: format_date(v, dayfirst=True))
    return df


def get_leave_note(ma_bos_gv: str, ten_gv: str, as_of: date, df_leave: pd.DataFrame) -> str:
    """Trả về '' nếu không có đơn nghỉ nào trùng ngày as_of, 'done' nếu có
    đơn đã xử lý (Done) trùng ngày (cần loại GV này), hoặc 1 câu ghi chú nếu
    có đơn nhưng chưa note trạng thái (vẫn giữ GV, chỉ cảnh báo)."""
    if df_leave.empty or as_of is None:
        return ""

    if ma_bos_gv:
        rows = df_leave[df_leave["ID BOS"].str.strip().str.lower() == ma_bos_gv.strip().lower()]
    else:
        rows = df_leave[df_leave["Tên giáo viên"].str.strip().str.lower() == ten_gv.strip().lower()]
    if rows.empty:
        return ""

    for _, r in rows.iterrows():
        start = _parse_ddmmyyyy(r["Ngày bắt đầu"])
        end = _parse_ddmmyyyy(r["Ngày kết thúc"]) or start
        if not start or not (start <= as_of <= end):
            continue
        trang_thai = r["VHGV xử lý"].strip().lower()
        if trang_thai == "cancel":
            continue
        if trang_thai == "done":
            return "done"
        return f"⚠️ GV có đơn nghỉ ({r['Loại đơn'] or 'chưa rõ loại'}) chưa xử lý: {r['Ngày bắt đầu']} → {r['Ngày kết thúc']}"
    return ""


def _detect_lophoc_layout(cat_row, col_row):
    """Xác định cột base (Mã lớp/Trình độ/Ngày dự kiến KG) và các nhóm 'Buổi X'
    dựa theo dòng danh mục (cat_row) + dòng tên cột (col_row), không phụ thuộc
    số lượng cột base hay tên cột GV khác nhau giữa các sheet."""
    n = len(col_row)
    marker_idxs = [i for i, c in enumerate(cat_row) if "Buổi" in c]
    first_group_start = marker_idxs[0] if marker_idxs else n

    base_idx = {}
    for i in range(first_group_start):
        name = col_row[i].strip()
        if name == "Mã lớp":
            base_idx["Mã lớp"] = i
        elif name == "Trình độ":
            base_idx["Trình độ"] = i

    # Cột "Ngày dự kiến KG" luôn nằm ngay sau cột "Trình độ" ở cả 2 sheet,
    # nhãn cột thực tế có thể khác chữ nên xác định theo vị trí cho chắc.
    if "Trình độ" in base_idx and base_idx["Trình độ"] + 1 < first_group_start:
        base_idx["Ngày dự kiến KG"] = base_idx["Trình độ"] + 1

    # "Trạng thái lớp" nằm sau tất cả các nhóm Buổi, dò theo tên trên toàn dòng.
    for i, name in enumerate(col_row):
        if "Trạng thái" in name:
            base_idx["Trạng thái lớp"] = i
            break

    bounds = marker_idxs + [n]
    groups = []
    for gi in range(len(marker_idxs)):
        start, end = bounds[gi], bounds[gi + 1]
        role = {"day": None, "time": None, "code": None, "name": None}
        for i in range(start, end):
            label = col_row[i].strip()
            if not label:
                continue
            if label == "Thứ":
                role["day"] = i
            elif label.startswith("Giờ"):
                role["time"] = i
            elif "Mã GV" in label:
                role["code"] = i
            elif role["name"] is None:
                role["name"] = i
        if role["day"] is not None:
            groups.append(role)
    return base_idx, groups


SESSION_COLS = ["Chương trình", "Mã lớp", "Trình độ", "Ngày dự kiến KG", "Trạng thái lớp",
                "Thứ", "Giờ học", "Mã GV", "Giáo viên"]


def _load_lophoc_program(program: str) -> pd.DataFrame:
    ws = get_gc().open_by_key(SPREADSHEET_ID).worksheet(PROGRAMS[program]["sheet_lop"])
    rows = ws.get_all_values()
    if len(rows) < 3:
        return pd.DataFrame(columns=SESSION_COLS)

    cat_row, col_row = rows[0], rows[1]
    width = len(col_row)
    data_rows = _pad_rows(rows[2:], width)
    base_idx, groups = _detect_lophoc_layout(cat_row, col_row)

    sessions = []
    for r in data_rows:
        ma_lop = r[base_idx["Mã lớp"]].strip() if "Mã lớp" in base_idx else ""
        if not ma_lop:
            continue
        trinh_do = r[base_idx["Trình độ"]].strip() if "Trình độ" in base_idx else ""
        # EZP ghi ngày kiểu d/m/y; IE lẫn cả d/m/y (dữ liệu cũ) và m/d/y (dữ liệu mới) -> tự đoán.
        kg_dayfirst = True if program == "EZP" else None
        ngay_kg = format_date(r[base_idx["Ngày dự kiến KG"]], dayfirst=kg_dayfirst) if "Ngày dự kiến KG" in base_idx else ""
        trang_thai = r[base_idx["Trạng thái lớp"]].strip() if "Trạng thái lớp" in base_idx else ""

        for role in groups:
            thu = r[role["day"]].strip() if role["day"] is not None else ""
            if not thu:
                continue
            gio = r[role["time"]].strip() if role["time"] is not None else ""
            ma_gv = r[role["code"]].strip() if role["code"] is not None else ""
            ten_gv = r[role["name"]].strip() if role["name"] is not None else ""
            sessions.append({
                "Chương trình": program,
                "Mã lớp": ma_lop,
                "Trình độ": trinh_do,
                "Ngày dự kiến KG": ngay_kg,
                "Trạng thái lớp": trang_thai,
                "Thứ": thu,
                "Giờ học": gio,
                "Mã GV": ma_gv,
                "Giáo viên": ten_gv,
            })

    return pd.DataFrame(sessions, columns=SESSION_COLS)


@st.cache_data(ttl=300)
def load_lophoc() -> pd.DataFrame:
    frames = [_load_lophoc_program(p) for p in PROGRAMS]
    return pd.concat(frames, ignore_index=True)


@st.cache_data(ttl=300)
def load_hocvien() -> pd.DataFrame:
    ws = get_gc().open_by_key(SPREADSHEET_ID).worksheet(SHEET_HOCVIEN)
    rows = ws.get_all_values()
    if len(rows) < 2:
        return pd.DataFrame(columns=HOCVIEN_COLS)

    data = _pad_rows(rows[1:], len(HOCVIEN_COLS))
    df = pd.DataFrame(data, columns=HOCVIEN_COLS)
    df = df[df["ID"].str.strip() != ""]
    # Sheet nguồn (đồng bộ từ Raw IE/EZP) đôi khi có dòng bị lặp cho cùng 1 HV + lớp
    df = df.drop_duplicates(subset=["ID", "Mã lớp"])
    for col in ["Ngày khai giảng", "Ngày kết thúc dự kiến"]:
        df[col] = df[col].apply(lambda v: format_date(v, dayfirst=False))
    return df.reset_index(drop=True)


XULY_COLS = ["Ngày/tháng", "Mã lớp", "Ca học", "Quốc tịch", "Mã Gv", "Tên Gv",
             "Loại đơn nghỉ", "Vấn đề cần xử lý", "Lý do", "Mã Gv cover",
             "Giáo viên cover", "Trình độ giảng dạy", "Note Gv"]


def _load_xuly_program(program: str) -> pd.DataFrame:
    ws = get_gc().open_by_key(SPREADSHEET_ID).worksheet(PROGRAMS[program]["sheet_xuly"])
    rows = ws.get_all_values()
    if len(rows) < 2:
        return pd.DataFrame(columns=["Chương trình"] + XULY_COLS)

    data = _pad_rows(rows[1:], len(XULY_COLS))
    df = pd.DataFrame(data, columns=XULY_COLS)
    df = df[(df["Mã lớp"].str.strip() != "") & (df["Loại đơn nghỉ"].str.strip() != "")]
    df["Ngày/tháng"] = df["Ngày/tháng"].apply(lambda v: format_date(v, dayfirst=True))
    df.insert(0, "Chương trình", program)
    return df.reset_index(drop=True)


@st.cache_data(ttl=300)
def load_xuly() -> pd.DataFrame:
    frames = [_load_xuly_program(p) for p in PROGRAMS]
    return pd.concat(frames, ignore_index=True)

# ===== HELPERS =====

def _time_sort_key(slot: str):
    """Sắp xếp khung giờ theo thời gian thực (hỗ trợ cả '8h30' và '08:30')."""
    m = re.search(r"(\d{1,2})[h:](\d{2})", slot)
    return (int(m.group(1)), int(m.group(2))) if m else (99, 99)


def get_time_slots(df_gv: pd.DataFrame) -> list:
    slots = set(df_gv["Khung giờ 1"]) | set(df_gv["Khung giờ 2"])
    slots = {s.strip() for s in slots if s.strip()}
    return sorted(slots, key=_time_sort_key)


def get_level_options(df_gv: pd.DataFrame) -> list:
    levels = set()
    for cell in df_gv["Trình độ giảng dạy"]:
        for part in cell.split(","):
            part = part.strip()
            if part:
                levels.add(part)
    return sorted(levels)


_CLASS_CODE_RE = re.compile(r"^([A-Za-z0-9]+-[A-Za-z0-9]+)")


def get_ended_classes(df_lop: pd.DataFrame) -> set:
    if df_lop.empty:
        return set()
    ended = df_lop[df_lop["Trạng thái lớp"].str.contains("Ngừng|Ngưng", na=False)]
    return set(ended["Mã lớp"])


def _parse_ddmmyyyy(s: str):
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        return None


def get_not_started_classes(df_lop: pd.DataFrame, as_of: date) -> set:
    """Lớp có Ngày dự kiến KG sau ngày as_of (chưa khai giảng nên vẫn rảnh).
    Bỏ qua nếu Trạng thái lớp đã ghi 'Đã khai giảng' — ngày dự kiến KG chỉ là
    ước tính và có thể chưa cập nhật, không đáng tin bằng Trạng thái lớp."""
    if df_lop.empty or as_of is None:
        return set()
    not_already_started = ~df_lop["Trạng thái lớp"].str.contains("Đã khai giảng", na=False)
    parsed = df_lop["Ngày dự kiến KG"].apply(_parse_ddmmyyyy)
    mask = not_already_started & parsed.apply(lambda d: d is not None and d > as_of)
    return set(df_lop[mask]["Mã lớp"])


def classify_slot(day_col: pd.Series, free_classes: set) -> pd.Series:
    """Phân loại từng ô lịch GV:
    - 'available': ghi đúng chữ 'Available', hoặc ghi mã lớp nhưng lớp đó
      nằm trong free_classes (đã kết thúc / chưa tới ngày khai giảng).
    - 'no_shift': ô để trống (không xếp ca làm ở khung này) — chưa chắc rảnh.
    - 'busy': đang bận 1 lớp khác đang hoạt động."""
    def _classify(cell: str) -> str:
        c = cell.strip()
        if not c:
            return "no_shift"
        if c.lower() == "available":
            return "available"
        m = _CLASS_CODE_RE.match(c)
        if m and m.group(1) in free_classes:
            return "available"
        return "busy"

    return day_col.apply(_classify)


def _extract_times(s: str) -> tuple:
    return tuple((int(h), int(m)) for h, m in re.findall(r"(\d{1,2})[h:](\d{2})", s or ""))


def times_match(a: str, b: str) -> bool:
    """So khớp khung giờ bất kể định dạng ('18h45-20h15' so với '18:45 - 20:15')."""
    ta, tb = _extract_times(a), _extract_times(b)
    return bool(ta) and ta == tb


def gv_loai(quoc_tich: str) -> str:
    """GVVN nếu Quốc tịch là Vietnamese/Vietnam (EZP và IE ghi khác nhau),
    còn lại tính là GVNN (nước ngoài)."""
    return "GVVN" if quoc_tich.strip().lower().startswith("vietnam") else "GVNN"


def get_all_class_incidents(ma_lop: str, program: str, df_xuly: pd.DataFrame) -> pd.DataFrame:
    """Toàn bộ sự vụ (Cover/Hủy đơn/Hủy lớp) của 1 mã lớp từ trước đến nay."""
    if df_xuly.empty or not ma_lop:
        return pd.DataFrame()
    rows = df_xuly[
        (df_xuly["Chương trình"] == program) &
        (df_xuly["Mã lớp"].str.strip().str.lower() == ma_lop.strip().lower())
    ]
    if rows.empty:
        return pd.DataFrame()
    out = rows.rename(columns={"Tên Gv": "Gv chính"})
    return out[["Ngày/tháng", "Mã lớp", "Ca học", "Gv chính", "Loại đơn nghỉ",
                "Vấn đề cần xử lý", "Giáo viên cover"]].reset_index(drop=True)


def get_gv_incidents(ten_gv: str, program: str, df_xuly: pd.DataFrame) -> pd.DataFrame:
    """Toàn bộ sự vụ (Cover/Hủy đơn/Hủy lớp) mà 1 GV là người chính đứng đơn.
    Khớp theo Tên Gv vì cột Mã Gv trong sheet Xử lý phát sinh dùng hệ mã khác
    (VD 'TC018xxx') với Mã GV bên Data lịch GV, không thể so khớp theo mã."""
    if df_xuly.empty or not ten_gv:
        return pd.DataFrame()
    rows = df_xuly[
        (df_xuly["Chương trình"] == program) &
        (df_xuly["Tên Gv"].str.strip().str.lower() == ten_gv.strip().lower())
    ]
    if rows.empty:
        return pd.DataFrame()
    return rows[["Ngày/tháng", "Mã lớp", "Ca học", "Loại đơn nghỉ",
                 "Vấn đề cần xử lý", "Giáo viên cover"]].reset_index(drop=True)


def get_class_incidents(ma_lop: str, program: str, df_xuly: pd.DataFrame) -> pd.DataFrame:
    """Như get_all_class_incidents, nhưng chỉ trả về nếu có từ 2 sự vụ trở lên
    (dùng để cảnh báo khi tìm cover)."""
    incidents = get_all_class_incidents(ma_lop, program, df_xuly)
    return incidents if len(incidents) >= 2 else pd.DataFrame()


def resolve_date_range(value):
    """Chuẩn hoá giá trị st.date_input (range-mode) về tuple (start, end) hoặc None."""
    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            return (value[0], value[0])
        if len(value) == 2:
            return tuple(value)
        return None
    if value:
        return (value, value)
    return None


def thu_date_map_from_range(date_range) -> dict:
    """Map mỗi Thứ xuất hiện trong khoảng ngày -> ngày cụ thể đầu tiên của Thứ đó."""
    mapping = {}
    if not date_range:
        return mapping
    cur = date_range[0]
    while cur <= date_range[1] and len(mapping) < 7:
        thu = WEEKDAY_TO_THU[cur.weekday()]
        if thu not in mapping:
            mapping[thu] = cur
        cur += timedelta(days=1)
    return mapping


def apply_gv_status_and_leave(df_gv_slice: pd.DataFrame, as_of: date,
                               active_gv_codes: dict, df_leave: pd.DataFrame) -> pd.DataFrame:
    """Loại GV không có mặt trong Data GV EZP/IE (đã nghỉ việc), loại GV có
    đơn nghỉ đã xử lý (Done) trùng ngày as_of, và gắn ghi chú cho GV có đơn
    nghỉ chưa note trạng thái."""
    df = df_gv_slice.copy()

    if df.empty:
        df["_leave_note"] = ""
        return df

    if active_gv_codes:
        def _is_active(r):
            codes = active_gv_codes.get(r["Chương trình"])
            if not codes:  # sheet trống/lỗi tải -> không lọc để tránh loại nhầm hết
                return True
            return r["Mã GV"].strip() in codes

        df = df[df.apply(_is_active, axis=1)]

    if df.empty:
        df["_leave_note"] = ""
        return df

    if df_leave is not None and not df_leave.empty and as_of is not None:
        df = df.assign(_leave_note=df.apply(
            lambda r: get_leave_note(r.get("Mã BOS GV", ""), r["Giáo viên"], as_of, df_leave),
            axis=1,
        ))
        df = df[df["_leave_note"] != "done"]
    else:
        df["_leave_note"] = ""

    return df


def find_cover_candidates(sess: pd.Series, df_gv_all: pd.DataFrame, df_lop: pd.DataFrame,
                           as_of: date, loai_gv_filter: str = "Tất cả",
                           active_gv_codes: dict = None, df_leave: pd.DataFrame = None) -> pd.DataFrame:
    """GV cùng chương trình, rảnh đúng Thứ + khung giờ của buổi `sess` cần cover."""
    ctr = sess["Chương trình"]
    thu = sess["Thứ"]
    gio_hoc = sess["Giờ học"]
    ma_lop = sess["Mã lớp"].strip().lower()

    df_gv_ct = df_gv_all[df_gv_all["Chương trình"] == ctr]
    if df_gv_ct.empty or thu not in df_gv_ct.columns:
        return pd.DataFrame()

    day_col = df_gv_ct[thu]
    free_classes = get_ended_classes(df_lop) | get_not_started_classes(df_lop, as_of)
    status = classify_slot(day_col, free_classes)

    # GV đang dạy chính lớp này ở đúng khung giờ này thì loại hẳn, bất kể lớp
    # có bị tính "rảnh" (đã kết thúc/chưa khai giảng) theo free_classes hay không —
    # tránh tự gợi ý GV cover cho đúng lớp họ đang dạy.
    def _is_own_class(cell: str) -> bool:
        m = _CLASS_CODE_RE.match(cell.strip())
        return bool(m and m.group(1).strip().lower() == ma_lop)

    own_class = day_col.apply(_is_own_class)

    mask_time = (
        df_gv_ct["Khung giờ 1"].apply(lambda v: times_match(v, gio_hoc)) |
        df_gv_ct["Khung giờ 2"].apply(lambda v: times_match(v, gio_hoc))
    )
    candidates = df_gv_ct[mask_time].copy()
    candidates["_status"] = status[mask_time]
    candidates = candidates[(candidates["_status"] != "busy") & (~own_class[mask_time])]
    # 1 khung giờ 90' trùng với 2 dòng khung giờ 45' liên tiếp trong sheet -> khử trùng theo GV
    candidates = candidates.drop_duplicates(["Chương trình", "Mã GV"])

    if loai_gv_filter != "Tất cả":
        candidates = candidates[candidates["Quốc tịch"].apply(lambda q: gv_loai(q) == loai_gv_filter)]

    return apply_gv_status_and_leave(candidates, as_of, active_gv_codes, df_leave)


def _show_cols_with_note(df: pd.DataFrame) -> pd.DataFrame:
    show = ["Mã GV", "Giáo viên", "Quốc tịch", "Trình độ giảng dạy"]
    if "_leave_note" in df.columns:
        out = df[show + ["_leave_note"]].rename(columns={"_leave_note": "Ghi chú"})
    else:
        out = df[show]
    return out.reset_index(drop=True)


def render_cover_candidates(candidates: pd.DataFrame):
    """Tách 2 tab: GV có ghi 'Available' rõ ràng, và GV chỉ đơn giản là không
    có ca làm ở khung này (chưa chắc chắn rảnh, cần xác nhận thêm). GV có đơn
    nghỉ chưa xử lý vẫn hiện nhưng kèm ghi chú ở cột 'Ghi chú'."""
    available = candidates[candidates["_status"] == "available"] if not candidates.empty else candidates
    no_shift = candidates[candidates["_status"] == "no_shift"] if not candidates.empty else candidates

    tab_a, tab_b = st.tabs([f"✅ GV available ({len(available)})", f"❔ GV không có ca ({len(no_shift)})"])
    with tab_a:
        if available.empty:
            st.info("Không có GV nào.")
        else:
            st.caption("Đối chiếu cột 'Trình độ giảng dạy' bên dưới với Trình độ lớp/buổi ở trên để chọn GV phù hợp.")
            st.dataframe(_show_cols_with_note(available), use_container_width=True)
    with tab_b:
        if no_shift.empty:
            st.info("Không có GV nào.")
        else:
            st.caption("GV không có ca làm việc ở khung giờ này trong lịch — chưa chắc chắn rảnh, cần xác nhận thêm trước khi xếp cover.")
            st.dataframe(_show_cols_with_note(no_shift), use_container_width=True)


def _day_sort_key(thu: str) -> int:
    return DAYS.index(thu) if thu in DAYS else 99


def class_sessions_table(g: pd.DataFrame) -> pd.DataFrame:
    """Bảng các buổi học (Thứ/Giờ học/Giáo viên) của 1 lớp, sắp theo thứ tự Thứ."""
    gg = g.sort_values(by="Thứ", key=lambda col: col.map(_day_sort_key))
    return gg[["Thứ", "Giờ học", "Giáo viên"]].reset_index(drop=True)


def get_teacher_sessions(program: str, ma_gv: str, df_sessions: pd.DataFrame,
                          thu_filter: str = None, trang_thai_filter: str = None) -> pd.DataFrame:
    """Các buổi dạy của 1 GV (tra từ data lớp học).
    Nếu có thu_filter, chỉ giữ các buổi rơi vào đúng Thứ đó.
    Nếu có trang_thai_filter, chỉ giữ các lớp đúng Trạng thái lớp đó."""
    if df_sessions.empty or not ma_gv:
        return pd.DataFrame()

    ma_gv = ma_gv.strip()
    g = df_sessions[
        (df_sessions["Chương trình"] == program) &
        (df_sessions["Mã GV"].str.strip() == ma_gv)
    ]
    if thu_filter:
        thu_set = [thu_filter] if isinstance(thu_filter, str) else list(thu_filter)
        g = g[g["Thứ"].str.strip().isin(thu_set)]
    if trang_thai_filter:
        g = g[g["Trạng thái lớp"].str.strip() == trang_thai_filter]
    return g


def build_schedule_grid(sessions: pd.DataFrame) -> pd.DataFrame:
    """Bảng lịch dạng lưới: hàng = ca học (Giờ học), cột = Thứ,
    ô = Mã lớp kèm Ngày dự kiến KG (mỗi lớp 1 dòng)."""
    if sessions.empty:
        return pd.DataFrame()

    sessions = sessions.copy()

    def _cell_label(r):
        label = r["Mã lớp"]
        if r["Ngày dự kiến KG"]:
            label += f" (KG: {r['Ngày dự kiến KG']})"
        if r["Trạng thái lớp"]:
            label += f" - {r['Trạng thái lớp']}"
        return label

    sessions["_label"] = sessions.apply(_cell_label, axis=1)

    pivot = sessions.pivot_table(
        index="Giờ học", columns="Thứ", values="_label",
        aggfunc=lambda s: "\n".join(s), fill_value="",
    )
    cols = [d for d in DAYS if d in pivot.columns]
    pivot = pivot[cols]
    pivot = pivot.reindex(sorted(pivot.index, key=_time_sort_key))
    pivot.index.name = "Ca học"
    return pivot.reset_index()


def render_html_table(df: pd.DataFrame):
    """Vẽ bảng bằng HTML để các ô nhiều dòng (chứa '\\n') xuống dòng thật,
    thay vì bị nối liền như trong st.dataframe."""
    if df.empty:
        return
    lines = ["<table style='width:100%; border-collapse:collapse;'>",
             "<tr>" + "".join(
                 f"<th style='text-align:left;padding:6px;border-bottom:1px solid #555;'>{html.escape(str(c))}</th>"
                 for c in df.columns
             ) + "</tr>"]
    for _, row in df.iterrows():
        lines.append("<tr>")
        for c in df.columns:
            cell = html.escape(str(row[c])).replace("\n", "<br>")
            lines.append(f"<td style='padding:6px;border-bottom:1px solid #333;vertical-align:top;'>{cell}</td>")
        lines.append("</tr>")
    lines.append("</table>")
    st.markdown("".join(lines), unsafe_allow_html=True)


_SESSION_RE = re.compile(r"(Thứ\s*\d+|Chủ\s*nhật)\s*:\s*(.*?)(?=Thứ\s*\d+\s*:|Chủ\s*nhật\s*:|$)", re.S)


def _parse_sessions(text: str) -> list:
    return [(thu.strip(), val.strip()) for thu, val in _SESSION_RE.findall(text or "")]


def render_teacher_schedule(sessions: pd.DataFrame):
    """Hiển thị lịch dạy dạng lưới: hàng ca học, cột Thứ."""
    if sessions.empty:
        st.info("Không có lớp nào trong hệ thống.")
        return
    render_html_table(build_schedule_grid(sessions))

# ===== UI =====

st.title("📚 Tra cứu thông tin")

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Tìm GV rảnh / Cover", "👤 Tra cứu theo tên GV",
                                  "🏫 Tra cứu Lớp học", "🎓 Tra cứu Học viên"])

# ── Tab 1: Tìm GV rảnh / Tìm GV Cover ────────────────────────────────────────
with tab1:
    st.subheader("Tìm GV rảnh / Tìm GV Cover")

    find_mode = st.radio("Chế độ tìm", ["Duyệt tự do", "Theo mã lớp", "Theo GV nghỉ"],
                          horizontal=True, key="find_mode")

    # ── Chế độ 1: duyệt tự do theo Thứ + khung giờ ──
    if find_mode == "Duyệt tự do":
        with st.spinner("Đang tải dữ liệu..."):
            df_gv_all = load_gv()

        col0, col1, col2, col3, col4 = st.columns(5)
        with col0:
            selected_program = st.selectbox("Chương trình", ["Tất cả"] + list(PROGRAMS.keys()))

        df_gv_scoped = df_gv_all if selected_program == "Tất cả" else df_gv_all[df_gv_all["Chương trình"] == selected_program]
        time_options = ["Tất cả khung giờ"] + get_time_slots(df_gv_scoped) if not df_gv_scoped.empty else ["Tất cả khung giờ"]
        level_options = get_level_options(df_gv_scoped) if not df_gv_scoped.empty else []

        with col1:
            selected_day = st.selectbox("Chọn Thứ", DAYS)
        with col2:
            selected_time = st.selectbox("Chọn khung giờ", time_options)
        with col3:
            date_input_val = st.date_input("Chọn ngày", value=(), key="find_free_date",
                                            help="Chọn 1 ngày, hoặc bấm ngày đầu rồi ngày cuối để chọn khoảng ngày")
        with col4:
            selected_levels = st.multiselect("Trình độ giảng dạy", level_options,
                                              help="Tuỳ chọn — lọc theo trình độ giảng dạy của GV")

        date_range = resolve_date_range(date_input_val)
        thu_list = list(thu_date_map_from_range(date_range).keys()) if date_range else [selected_day]

        if st.button("Tìm kiếm", key="btn_find_free"):
            df_gv = df_gv_scoped

            if df_gv.empty:
                st.error("Không tải được dữ liệu. Kiểm tra lại kết nối sheet.")
            else:
                with st.spinner("Đang tải dữ liệu..."):
                    df_lop_for_avail = load_lophoc()
                    active_gv_codes = load_active_gv_codes()
                    df_leave = load_leave_requests()
                as_of = date_range[0] if date_range else date.today()
                free_classes = get_ended_classes(df_lop_for_avail) | get_not_started_classes(df_lop_for_avail, as_of)

                frames = []
                for thu in thu_list:
                    if thu not in df_gv.columns:
                        continue
                    status = classify_slot(df_gv[thu], free_classes)
                    if selected_time != "Tất cả khung giờ":
                        mask_time = (
                            (df_gv["Khung giờ 1"].str.strip() == selected_time) |
                            (df_gv["Khung giờ 2"].str.strip() == selected_time)
                        )
                        sub = df_gv[mask_time].copy()
                        sub["_status"] = status[mask_time]
                        sub = sub[sub["_status"] != "busy"]
                        # 1 khung giờ 90' trùng với 2 dòng khung giờ 45' liên tiếp trong sheet -> khử trùng theo GV
                        sub = sub.drop_duplicates(["Chương trình", "Mã GV"])
                    else:
                        sub = df_gv.copy()
                        sub["_status"] = status
                        sub = sub[sub["_status"] != "busy"]
                    sub["Thứ"] = thu
                    frames.append(sub)

                result = pd.concat(frames, ignore_index=True) if frames else df_gv.iloc[0:0].copy()
                result = apply_gv_status_and_leave(result, as_of, active_gv_codes, df_leave)

                if selected_levels:
                    mask_level = result["Trình độ giảng dạy"].apply(
                        lambda cell: any(lv in cell for lv in selected_levels)
                    )
                    result = result[mask_level]

                def _group_by_teacher(df):
                    if df.empty or selected_time == "Tất cả khung giờ":
                        return df
                    # gộp lại 1 dòng / GV, liệt kê các Thứ rảnh trong khoảng đã chọn
                    return df.groupby(["Chương trình", "Mã GV"], sort=False).agg({
                        "Giáo viên": "first",
                        "Quốc tịch": "first",
                        "Trình độ giảng dạy": "first",
                        "Khung giờ 1": "first",
                        "Khung giờ 2": "first",
                        "Thứ": lambda s: ", ".join(dict.fromkeys(s)),
                        "_leave_note": "first",
                    }).reset_index()

                date_label = ""
                if date_range and date_range[0] == date_range[1]:
                    date_label = f" ({date_range[0].strftime('%d/%m/%Y')})"
                elif date_range:
                    date_label = f" ({date_range[0].strftime('%d/%m/%Y')} → {date_range[1].strftime('%d/%m/%Y')})"

                st.markdown(f"{', '.join(thu_list)}{date_label}"
                            + (f" | {selected_time}" if selected_time != "Tất cả khung giờ" else "")
                            + (f" | {selected_program}" if selected_program != "Tất cả" else ""))

                available = _group_by_teacher(result[result["_status"] == "available"])
                no_shift = _group_by_teacher(result[result["_status"] == "no_shift"])
                show = ["Chương trình", "Mã GV", "Giáo viên", "Quốc tịch", "Trình độ giảng dạy",
                        "Thứ", "Khung giờ 1", "Khung giờ 2"]

                def _with_note(df):
                    cols = show + ["_leave_note"] if "_leave_note" in df.columns else show
                    return df[cols].rename(columns={"_leave_note": "Ghi chú"}).reset_index(drop=True)

                tab_a, tab_b = st.tabs([f"✅ GV available ({len(available)})",
                                        f"❔ GV không có ca ({len(no_shift)})"])
                with tab_a:
                    if available.empty:
                        st.info("Không có giáo viên nào rảnh trong khung giờ này.")
                    else:
                        st.dataframe(_with_note(available), use_container_width=True)
                with tab_b:
                    if no_shift.empty:
                        st.info("Không có giáo viên nào.")
                    else:
                        st.caption("GV không có ca làm việc ở khung giờ này trong lịch — chưa chắc chắn rảnh, cần xác nhận thêm.")
                        st.dataframe(_with_note(no_shift), use_container_width=True)

    # ── Chế độ 2: theo mã lớp cần cover ──
    elif find_mode == "Theo mã lớp":
        col_x, col_y, col_z = st.columns(3)
        with col_x:
            cover_class = st.text_input("Mã lớp cần cover", placeholder="EPP-0715", key="cover_class")
        with col_y:
            cover_date_val = st.date_input("Ngày cần cover", value=(), key="cover_date",
                                            help="Chọn 1 ngày, hoặc bấm ngày đầu rồi ngày cuối để chọn khoảng ngày")
        with col_z:
            cover_loai_gv = st.selectbox("Loại GV", ["Tất cả", "GVVN", "GVNN"], key="cover_loai_gv")

        cover_range = resolve_date_range(cover_date_val)
        cover_thu_map = thu_date_map_from_range(cover_range)

        if st.button("Tìm GV Cover", key="btn_find_cover"):
            if not cover_class.strip():
                st.warning("Nhập mã lớp cần cover.")
            elif not cover_range:
                st.warning("Chọn ngày cần cover.")
            else:
                with st.spinner("Đang tải dữ liệu..."):
                    df_lop = load_lophoc()
                    df_gv_all = load_gv()
                    df_xuly = load_xuly()
                    active_gv_codes = load_active_gv_codes()
                    df_leave = load_leave_requests()

                if df_lop.empty:
                    st.error("Không tải được dữ liệu.")
                else:
                    kw = cover_class.strip().lower()
                    class_sessions = df_lop[df_lop["Mã lớp"].str.lower() == kw]
                    if class_sessions.empty:
                        class_sessions = df_lop[df_lop["Mã lớp"].str.lower().str.contains(kw, na=False)]

                    if class_sessions.empty:
                        st.info(f"Không tìm thấy lớp '{cover_class}'.")
                    else:
                        day_sessions = class_sessions[
                            class_sessions["Thứ"].str.strip().isin(cover_thu_map.keys())
                        ]

                        if day_sessions.empty:
                            st.info(f"Lớp '{cover_class}' không có buổi học vào "
                                    f"{', '.join(cover_thu_map.keys())} trong khoảng đã chọn.")
                        else:
                            for _, sess in day_sessions.iterrows():
                                as_of = cover_thu_map[sess["Thứ"].strip()]
                                st.markdown(
                                    f"**Lớp {sess['Mã lớp']}** ({sess['Chương trình']}) — "
                                    f"Trình độ lớp: **{sess['Trình độ']}** — "
                                    f"{sess['Thứ']} {sess['Giờ học']} ({as_of.strftime('%d/%m/%Y')}) — "
                                    f"GV hiện tại: {sess['Giáo viên'] or '(chưa có)'}"
                                )
                                incidents = get_class_incidents(sess["Mã lớp"], sess["Chương trình"], df_xuly)
                                if not incidents.empty:
                                    st.warning(f"⚠️ Lớp {sess['Mã lớp']} có {len(incidents)} phát sinh:")
                                    st.dataframe(incidents, use_container_width=True, hide_index=True)
                                candidates = find_cover_candidates(sess, df_gv_all, df_lop, as_of, cover_loai_gv,
                                                                    active_gv_codes, df_leave)
                                render_cover_candidates(candidates)
                                st.divider()

    # ── Chế độ 3: theo GV nghỉ ──
    else:
        with st.spinner("Đang tải dữ liệu..."):
            df_gv_all = load_gv()

        col_p, col_q, col_ca, col_loai = st.columns(4)
        with col_p:
            absent_query = st.text_input("Tên hoặc mã GV nghỉ",
                                          placeholder="Nguyễn Thị Hồng Hạnh / GV0001", key="absent_gv_query")
        with col_q:
            absent_date_val = st.date_input("Ngày nghỉ", value=(), key="absent_date",
                                             help="Chọn 1 ngày, hoặc bấm ngày đầu rồi ngày cuối để chọn khoảng ngày")
        absent_range = resolve_date_range(absent_date_val)
        absent_thu_map = thu_date_map_from_range(absent_range)

        teacher_key = None
        if absent_query.strip() and not df_gv_all.empty:
            kw = absent_query.strip().lower()
            matched = df_gv_all[
                df_gv_all["Giáo viên"].str.lower().str.contains(kw, na=False) |
                df_gv_all["Mã GV"].str.lower().str.contains(kw, na=False)
            ].drop_duplicates(["Chương trình", "Mã GV"])

            if matched.empty:
                st.info("Không tìm thấy GV.")
            else:
                options = {
                    f"{r['Giáo viên']} ({r['Mã GV']} — {r['Chương trình']})": (r["Chương trình"], r["Mã GV"])
                    for _, r in matched.iterrows()
                }
                picked_label = st.selectbox("Chọn đúng GV nghỉ", list(options.keys()), key="absent_gv_pick")
                teacher_key = options[picked_label]

        day_sessions_teacher = pd.DataFrame()
        if teacher_key and absent_thu_map:
            ctr_t, ma_gv_t = teacher_key
            with st.spinner("Đang tải dữ liệu..."):
                df_lop_t = load_lophoc()
            day_sessions_teacher = df_lop_t[
                (df_lop_t["Chương trình"] == ctr_t) &
                (df_lop_t["Mã GV"].str.strip() == ma_gv_t) &
                (df_lop_t["Thứ"].str.strip().isin(absent_thu_map.keys())) &
                (~df_lop_t["Trạng thái lớp"].str.contains("Ngừng|Ngưng", na=False))
            ]

        ca_labels = [f"{row['Thứ']} {row['Giờ học']} — {row['Mã lớp']}"
                     for _, row in day_sessions_teacher.iterrows()]
        with col_ca:
            selected_ca = st.selectbox("Ca dạy nghỉ", ["Tất cả"] + ca_labels, key="absent_ca")
        with col_loai:
            loai_gv_absent = st.selectbox("Loại GV", ["Tất cả", "GVVN", "GVNN"], key="absent_loai_gv")

        if st.button("Tìm GV Cover", key="btn_find_cover_absent"):
            if not teacher_key:
                st.warning("Nhập và chọn đúng GV nghỉ.")
            elif not absent_range:
                st.warning("Chọn ngày nghỉ.")
            elif day_sessions_teacher.empty:
                st.info(f"GV này không có ca dạy vào {', '.join(absent_thu_map.keys())} "
                        f"trong khoảng đã chọn.")
            else:
                with st.spinner("Đang tải dữ liệu..."):
                    df_lop_full = load_lophoc()
                    df_xuly = load_xuly()
                    active_gv_codes = load_active_gv_codes()
                    df_leave = load_leave_requests()

                sessions_to_cover = day_sessions_teacher if selected_ca == "Tất cả" else day_sessions_teacher[
                    day_sessions_teacher.apply(
                        lambda r: f"{r['Thứ']} {r['Giờ học']} — {r['Mã lớp']}" == selected_ca, axis=1)
                ]

                if sessions_to_cover.empty:
                    st.info("Không có ca dạy nào phù hợp (có thể đã bị loại vì lớp ngừng hoạt động).")

                session_tab_labels = [
                    f"{sess['Mã lớp']} - {sess['Thứ']} {sess['Giờ học']} "
                    f"({absent_thu_map[sess['Thứ'].strip()].strftime('%d/%m/%Y')})"
                    for _, sess in sessions_to_cover.iterrows()
                ]
                session_tabs = st.tabs(session_tab_labels) if session_tab_labels else []

                for session_tab, (_, sess) in zip(session_tabs, sessions_to_cover.iterrows()):
                    with session_tab:
                        as_of = absent_thu_map[sess["Thứ"].strip()]
                        st.markdown(
                            f"**Lớp {sess['Mã lớp']}** ({sess['Chương trình']}) — "
                            f"Trình độ lớp: **{sess['Trình độ']}** — "
                            f"{sess['Thứ']} {sess['Giờ học']} ({as_of.strftime('%d/%m/%Y')})"
                        )
                        incidents = get_class_incidents(sess["Mã lớp"], sess["Chương trình"], df_xuly)
                        if not incidents.empty:
                            st.warning(f"⚠️ Lớp {sess['Mã lớp']} có {len(incidents)} phát sinh:")
                            st.dataframe(incidents, use_container_width=True, hide_index=True)
                        candidates = find_cover_candidates(sess, df_gv_all, df_lop_full, as_of, loai_gv_absent,
                                                            active_gv_codes, df_leave)
                        render_cover_candidates(candidates)

# ── Tab 2: Tra cứu theo GV ──────────────────────────────────────────────────
with tab2:
    st.subheader("Tra cứu theo tên hoặc mã Giáo Viên")

    with st.spinner("Đang tải dữ liệu..."):
        df_lop_all = load_lophoc()
    status_options = ["Tất cả"] + sorted({s.strip() for s in df_lop_all["Trạng thái lớp"] if s.strip()}) \
        if not df_lop_all.empty else ["Tất cả"]

    col_n, col_a, col_b, col_c = st.columns(4)
    with col_n:
        search_name = st.text_input("Nhập tên hoặc mã GV", placeholder="Nguyễn Thị Hồng Hạnh / GV0001")
    with col_a:
        filter_thu = st.selectbox("Lọc theo Thứ", ["Tất cả"] + DAYS, key="gv_filter_thu",
                                   help="Tuỳ chọn — chỉ hiện lớp rơi vào đúng Thứ này")
    with col_b:
        filter_date_val = st.date_input("Chọn ngày", value=(), key="gv_filter_date",
                                         help="Chọn 1 ngày, hoặc bấm ngày đầu rồi ngày cuối để chọn khoảng ngày")
    with col_c:
        filter_status = st.selectbox("Trạng thái lớp", status_options, key="gv_filter_status",
                                      help="Tuỳ chọn — lọc theo trạng thái lớp")

    filter_date_range = resolve_date_range(filter_date_val)
    filter_thu_map = thu_date_map_from_range(filter_date_range)

    if filter_thu_map:
        effective_thu = list(filter_thu_map.keys())
    elif filter_thu != "Tất cả":
        effective_thu = filter_thu
    else:
        effective_thu = None

    effective_status = filter_status if filter_status != "Tất cả" else None

    if st.button("Tra cứu", key="btn_search_gv"):
        with st.spinner("Đang tải dữ liệu..."):
            df_gv = load_gv()
            df_lop = df_lop_all
            df_xuly = load_xuly()

        if df_gv.empty:
            st.error("Không tải được dữ liệu.")
        else:
            kw = search_name.strip().lower()
            mask = (
                df_gv["Giáo viên"].str.lower().str.contains(kw, na=False) |
                df_gv["Mã GV"].str.lower().str.contains(kw, na=False)
            )
            result = df_gv[mask]

            if result.empty:
                st.info("Không tìm thấy giáo viên nào.")
            else:
                teachers = result.drop_duplicates(["Chương trình", "Mã GV"])[
                    ["Chương trình", "Mã GV", "Giáo viên", "Quốc tịch", "Trình độ giảng dạy"]
                ]

                for _, t in teachers.iterrows():
                    title = (f"👤 {t['Giáo viên']} ({t['Mã GV']} — {t['Chương trình']}) — "
                             f"{t['Quốc tịch']} — {t['Trình độ giảng dạy']}")
                    with st.expander(title, expanded=True):
                        label = "🏫 Các lớp giảng dạy"
                        if effective_thu:
                            thu_text = effective_thu if isinstance(effective_thu, str) else ", ".join(effective_thu)
                            date_text = ""
                            if filter_date_range and filter_date_range[0] == filter_date_range[1]:
                                date_text = f" ({filter_date_range[0].strftime('%d/%m/%Y')})"
                            elif filter_date_range:
                                date_text = (f" ({filter_date_range[0].strftime('%d/%m/%Y')} → "
                                             f"{filter_date_range[1].strftime('%d/%m/%Y')})")
                            label += f" — {thu_text}{date_text}"
                        if effective_status:
                            label += f" — {effective_status}"

                        gv_incidents = get_gv_incidents(t["Giáo viên"], t["Chương trình"], df_xuly)
                        sub_tab1, sub_tab2 = st.tabs([label, f"Data phát sinh ({len(gv_incidents)})"])
                        with sub_tab1:
                            sessions = get_teacher_sessions(t["Chương trình"], t["Mã GV"], df_lop,
                                                             effective_thu, effective_status)
                            render_teacher_schedule(sessions)
                        with sub_tab2:
                            if gv_incidents.empty:
                                st.info("Chưa có sự vụ phát sinh nào.")
                            else:
                                st.dataframe(gv_incidents, use_container_width=True, hide_index=True)

# ── Tab 3: Tra cứu Lớp học ──────────────────────────────────────────────────
with tab3:
    st.subheader("Tra cứu theo mã Lớp học")

    search_class = st.text_input("Nhập mã lớp (hoặc một phần mã lớp)", placeholder="EPP-0715")

    if st.button("Tra cứu", key="btn_search_class"):
        with st.spinner("Đang tải dữ liệu..."):
            df_lop = load_lophoc()
            df_xuly = load_xuly()

        if df_lop.empty:
            st.error("Không tải được dữ liệu.")
        else:
            kw = search_class.strip().lower()
            if kw:
                mask = df_lop["Mã lớp"].str.lower().str.contains(kw, na=False)
                filtered = df_lop[mask]
            else:
                filtered = df_lop

            if filtered.empty:
                st.info("Không tìm thấy lớp học nào.")
            else:
                groups = list(filtered.groupby(["Chương trình", "Mã lớp"], sort=False))
                st.markdown(f"**{len(groups)} lớp học**")

                for (ctr, ma_lop), g in groups:
                    first = g.iloc[0]
                    with st.expander(f"🏫 {ma_lop} — {ctr}", expanded=True):
                        st.markdown(f"**Trình độ:** {first['Trình độ']}")
                        st.markdown(f"**Ngày dự kiến KG:** {first['Ngày dự kiến KG']}")
                        st.markdown(f"**Trạng thái lớp:** {first['Trạng thái lớp']}")

                        incidents = get_all_class_incidents(ma_lop, ctr, df_xuly)
                        sub_tab1, sub_tab2 = st.tabs(["Lịch học", f"Data phát sinh ({len(incidents)})"])
                        with sub_tab1:
                            st.dataframe(class_sessions_table(g), use_container_width=True)
                        with sub_tab2:
                            if incidents.empty:
                                st.info("Chưa có sự vụ phát sinh nào.")
                            else:
                                st.dataframe(incidents, use_container_width=True, hide_index=True)

# ── Tab 4: Tra cứu Học viên ──────────────────────────────────────────────────
with tab4:
    st.subheader("Tra cứu theo Học viên")

    search_hv = st.text_input("Nhập tên, ID, ID BOS, SĐT hoặc mã lớp",
                               placeholder="Nguyễn Văn A / HV-0065 / ID-0006", key="hv_search")

    if st.button("Tra cứu", key="btn_search_hv"):
        with st.spinner("Đang tải dữ liệu..."):
            df_hv = load_hocvien()
            df_xuly = load_xuly()

        if df_hv.empty:
            st.error("Không tải được dữ liệu.")
        else:
            kw = search_hv.strip().lower()
            if kw:
                mask = (
                    df_hv["Tên"].str.lower().str.contains(kw, na=False) |
                    df_hv["ID"].str.lower().str.contains(kw, na=False) |
                    df_hv["ID BOS"].str.lower().str.contains(kw, na=False) |
                    df_hv["Số điện thoại"].str.contains(kw, na=False) |
                    df_hv["Mã lớp"].str.lower().str.contains(kw, na=False)
                )
                result = df_hv[mask]
            else:
                result = df_hv

            if result.empty:
                st.info("Không tìm thấy học viên nào.")
            else:
                st.markdown(f"**{len(result)} học viên**")

                display = result.copy()
                display["Lịch học"] = display["Lịch học"].apply(
                    lambda v: "\n".join(f"{thu}: {gio}" for thu, gio in _parse_sessions(v)) or v
                )
                display["Giáo viên"] = display["Giáo viên"].apply(
                    lambda v: "\n".join(f"{thu}: {ten}" for thu, ten in _parse_sessions(v)) or v
                )
                show_cols = ["Sản phẩm", "ID", "ID BOS", "Tên", "Email", "Số điện thoại",
                             "Trạng thái hv", "Mã lớp", "Ngày khai giảng", "Ngày kết thúc dự kiến",
                             "Trạng thái lớp", "Lịch học", "Giáo viên", "Tổng buổi", "Buổi còn lại"]

                incident_frames = []
                for sp, ma_lop in result[["Sản phẩm", "Mã lớp"]].drop_duplicates().itertuples(index=False):
                    inc = get_all_class_incidents(ma_lop, sp, df_xuly)
                    if not inc.empty:
                        incident_frames.append(inc)
                all_incidents = pd.concat(incident_frames, ignore_index=True) if incident_frames else pd.DataFrame()

                sub_tab1, sub_tab2 = st.tabs(["Danh sách học viên", f"Data phát sinh ({len(all_incidents)})"])
                with sub_tab1:
                    render_html_table(display[show_cols])
                with sub_tab2:
                    if all_incidents.empty:
                        st.info("Chưa có sự vụ phát sinh nào.")
                    else:
                        st.dataframe(all_incidents, use_container_width=True, hide_index=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Cài đặt")
    if st.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.success("Đã xóa cache, dữ liệu sẽ được tải lại.")
    st.caption("Dữ liệu tự cập nhật mỗi 5 phút.")
