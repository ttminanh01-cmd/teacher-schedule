import html
import re

import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Tra cứu thông tin", page_icon="📚", layout="wide")

SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "")
DAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
WEEKDAY_TO_THU = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5",
                  4: "Thứ 6", 5: "Thứ 7", 6: "Chủ nhật"}

# Mỗi chương trình có 1 sheet lịch GV + 1 sheet lớp học riêng.
PROGRAMS = {
    "EZP": {"sheet_gv": "Data lịch GV EZP", "sheet_lop": "Data lớp học EZP"},
    "IE": {"sheet_gv": "Data lịch GV IE", "sheet_lop": "Data lớp học IE"},
}

# 13 cột đầu của cả 2 sheet lịch GV theo cùng thứ tự (chỉ khác nhãn cột).
GV_COLS = ["Quốc tịch", "Mã GV", "Giáo viên", "Trình độ giảng dạy",
           "Khung giờ 1", "Khung giờ 2"] + DAYS

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


def format_date(raw: str, dayfirst: bool = True) -> str:
    """Chuẩn hoá ngày về dd/mm/yyyy. dayfirst=True nếu nguồn đã là d/m/y
    (VD sheet lớp học), False nếu nguồn là m/d/y (VD sheet học viên)."""
    raw = (raw or "").strip()
    m = _DATE_RE.match(raw)
    if not m:
        return raw
    a, b, c = m.groups()
    if len(a) == 4:
        year, month, day = a, b, c
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
        return pd.DataFrame(columns=["Chương trình"] + GV_COLS)

    data = _pad_rows(rows[1:], len(GV_COLS))
    df = pd.DataFrame(data, columns=GV_COLS)
    df = df[df["Mã GV"].str.strip() != ""]
    df.insert(0, "Chương trình", program)
    return df.reset_index(drop=True)


@st.cache_data(ttl=300)
def load_gv() -> pd.DataFrame:
    frames = [_load_gv_program(p) for p in PROGRAMS]
    return pd.concat(frames, ignore_index=True)


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
        ngay_kg = format_date(r[base_idx["Ngày dự kiến KG"]], dayfirst=True) if "Ngày dự kiến KG" in base_idx else ""
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
    for col in ["Ngày khai giảng", "Ngày kết thúc dự kiến"]:
        df[col] = df[col].apply(lambda v: format_date(v, dayfirst=False))
    return df.reset_index(drop=True)

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


def build_avail_mask(day_col: pd.Series, ended_classes: set) -> pd.Series:
    """Rảnh nếu ô ghi 'Available', hoặc ô đang ghi mã lớp nhưng lớp đó đã kết thúc."""
    def _is_free(cell: str) -> bool:
        c = cell.strip()
        if not c:
            return False
        if c.lower() == "available":
            return True
        m = _CLASS_CODE_RE.match(c)
        return bool(m and m.group(1) in ended_classes)

    return day_col.apply(_is_free)


def _extract_times(s: str) -> tuple:
    return tuple((int(h), int(m)) for h, m in re.findall(r"(\d{1,2})[h:](\d{2})", s or ""))


def times_match(a: str, b: str) -> bool:
    """So khớp khung giờ bất kể định dạng ('18h45-20h15' so với '18:45 - 20:15')."""
    ta, tb = _extract_times(a), _extract_times(b)
    return bool(ta) and ta == tb


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
        g = g[g["Thứ"].str.strip() == thu_filter]
    if trang_thai_filter:
        g = g[g["Trạng thái lớp"].str.strip() == trang_thai_filter]
    return g


def build_schedule_grid(sessions: pd.DataFrame) -> pd.DataFrame:
    """Bảng lịch dạng lưới: hàng = ca học (Giờ học), cột = Thứ, ô = Mã lớp (mỗi mã 1 dòng)."""
    if sessions.empty:
        return pd.DataFrame()

    pivot = sessions.pivot_table(
        index="Giờ học", columns="Thứ", values="Mã lớp",
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


def render_class_info(ma_lop: str, ngay_kg: str, ngay_kt: str, trang_thai: str, schedule: str):
    """Bảng thông tin lớp nằm ngang (Mã lớp/Ngày KG/Ngày KT/Trạng thái),
    hàng dưới cùng gộp cả 4 cột hiển thị Lịch học & Giáo viên."""
    labels = ["Mã lớp", "Ngày khai giảng", "Ngày kết thúc dự kiến", "Trạng thái lớp"]
    values = [ma_lop, ngay_kg, ngay_kt, trang_thai]
    header_cells = "".join(
        f"<th style='text-align:left;padding:6px;border:1px solid #444;'>{html.escape(l)}</th>" for l in labels
    )
    value_cells = "".join(
        f"<td style='padding:6px;border:1px solid #333;'>{html.escape(str(v))}</td>" for v in values
    )
    schedule_html = "<br>".join(html.escape(line) for line in schedule.split("\n") if line)
    table_html = (
        "<table style='width:100%; border-collapse:collapse; margin-bottom:8px;'>"
        f"<tr>{header_cells}</tr>"
        f"<tr>{value_cells}</tr>"
        f"<tr><td colspan='4' style='padding:6px;border:1px solid #333;'>"
        f"<strong>Lịch học & Giáo viên:</strong><br>{schedule_html}</td></tr>"
        "</table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


_SESSION_RE = re.compile(r"(Thứ\s*\d+|Chủ\s*nhật)\s*:\s*(.*?)(?=Thứ\s*\d+\s*:|Chủ\s*nhật\s*:|$)", re.S)


def _parse_sessions(text: str) -> list:
    return [(thu.strip(), val.strip()) for thu, val in _SESSION_RE.findall(text or "")]


def format_hocvien_schedule(lich_hoc: str, giao_vien: str) -> str:
    """Ghép 'Lịch học' + 'Giáo viên' (mỗi ô đang dồn nhiều buổi liền nhau,
    không dấu ngăn cách) thành các dòng riêng: 'Thứ X: giờ - GV'."""
    lich_parts = _parse_sessions(lich_hoc)
    if not lich_parts:
        return lich_hoc or ""
    gv_map = dict(_parse_sessions(giao_vien))

    lines = []
    for thu, gio in lich_parts:
        gv = gv_map.get(thu, "")
        lines.append(f"{thu}: {gio} - {gv}" if gv else f"{thu}: {gio}")
    return "\n".join(lines)


def render_teacher_schedule(sessions: pd.DataFrame):
    """Hiển thị lịch dạy dạng lưới: hàng ca học, cột Thứ."""
    if sessions.empty:
        st.info("Không có lớp nào trong hệ thống.")
        return
    render_html_table(build_schedule_grid(sessions))

# ===== UI =====

st.title("📚 Tra cứu thông tin")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Tìm GV rảnh theo ca", "👤 Tra cứu theo tên GV",
                                        "🏫 Tra cứu Lớp học", "🎓 Tra cứu Học viên",
                                        "🔄 Tìm GV Cover"])

# ── Tab 1: Tìm GV rảnh ──────────────────────────────────────────────────────
with tab1:
    st.subheader("Tìm giáo viên rảnh theo Thứ và Khung giờ")

    with st.spinner("Đang tải dữ liệu..."):
        df_gv_all = load_gv()

    col0, col1, col2 = st.columns(3)
    with col0:
        selected_program = st.selectbox("Chương trình", ["Tất cả"] + list(PROGRAMS.keys()))

    df_gv_scoped = df_gv_all if selected_program == "Tất cả" else df_gv_all[df_gv_all["Chương trình"] == selected_program]
    time_options = ["Tất cả khung giờ"] + get_time_slots(df_gv_scoped) if not df_gv_scoped.empty else ["Tất cả khung giờ"]
    level_options = get_level_options(df_gv_scoped) if not df_gv_scoped.empty else []

    with col1:
        selected_day = st.selectbox("Chọn Thứ", DAYS)
    with col2:
        selected_time = st.selectbox("Chọn khung giờ", time_options)

    selected_date = st.date_input("Hoặc chọn ngày cụ thể (tuỳ chọn, sẽ tự suy ra Thứ)",
                                   value=None, key="find_free_date")
    effective_day = WEEKDAY_TO_THU[selected_date.weekday()] if selected_date else selected_day

    selected_levels = st.multiselect("Lọc theo trình độ giảng dạy (tuỳ chọn)", level_options)

    if st.button("Tìm kiếm", key="btn_find_free"):
        df_gv = df_gv_scoped

        if df_gv.empty:
            st.error("Không tải được dữ liệu. Kiểm tra lại kết nối sheet.")
        elif effective_day not in df_gv.columns:
            st.error(f"Không tìm thấy cột '{effective_day}' trong sheet.")
        else:
            with st.spinner("Đang tải dữ liệu..."):
                ended_classes = get_ended_classes(load_lophoc())
            mask_avail = build_avail_mask(df_gv[effective_day], ended_classes)

            if selected_time != "Tất cả khung giờ":
                mask_time = (
                    (df_gv["Khung giờ 1"].str.strip() == selected_time) |
                    (df_gv["Khung giờ 2"].str.strip() == selected_time)
                )
                result = df_gv[mask_avail & mask_time]
            else:
                result = df_gv[mask_avail]

            if selected_levels:
                mask_level = result["Trình độ giảng dạy"].apply(
                    lambda cell: any(lv in cell for lv in selected_levels)
                )
                result = result[mask_level]

            st.markdown(f"**{len(result)} khung giờ trống** — {effective_day}"
                        + (f" ({selected_date.strftime('%d/%m/%Y')})" if selected_date else "")
                        + (f" | {selected_time}" if selected_time != "Tất cả khung giờ" else "")
                        + (f" | {selected_program}" if selected_program != "Tất cả" else ""))

            if result.empty:
                st.info("Không có giáo viên nào rảnh trong khung giờ này.")
            else:
                show = ["Chương trình", "Mã GV", "Giáo viên", "Quốc tịch", "Trình độ giảng dạy",
                        "Khung giờ 1", "Khung giờ 2"]
                st.dataframe(result[show].reset_index(drop=True), use_container_width=True)

# ── Tab 2: Tra cứu theo GV ──────────────────────────────────────────────────
with tab2:
    st.subheader("Tra cứu theo tên hoặc mã Giáo Viên")

    search_name = st.text_input("Nhập tên hoặc mã GV", placeholder="Nguyễn Thị Hồng Hạnh / GV0001")

    with st.spinner("Đang tải dữ liệu..."):
        df_lop_all = load_lophoc()
    status_options = ["Tất cả"] + sorted({s.strip() for s in df_lop_all["Trạng thái lớp"] if s.strip()}) \
        if not df_lop_all.empty else ["Tất cả"]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        filter_thu = st.selectbox("Lọc lớp theo Thứ (tuỳ chọn)", ["Tất cả"] + DAYS, key="gv_filter_thu")
    with col_b:
        filter_date = st.date_input("Hoặc chọn ngày cụ thể (tuỳ chọn)", value=None, key="gv_filter_date")
    with col_c:
        filter_status = st.selectbox("Lọc theo tình trạng lớp (tuỳ chọn)", status_options, key="gv_filter_status")

    effective_thu = None
    if filter_date:
        effective_thu = WEEKDAY_TO_THU[filter_date.weekday()]
    elif filter_thu != "Tất cả":
        effective_thu = filter_thu

    effective_status = filter_status if filter_status != "Tất cả" else None

    if st.button("Tra cứu", key="btn_search_gv"):
        with st.spinner("Đang tải dữ liệu..."):
            df_gv = load_gv()
            df_lop = df_lop_all

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
                            label += f" — {effective_thu}" + (f" ({filter_date.strftime('%d/%m/%Y')})" if filter_date else "")
                        if effective_status:
                            label += f" — {effective_status}"
                        st.markdown(f"**{label}:**")

                        sessions = get_teacher_sessions(t["Chương trình"], t["Mã GV"], df_lop,
                                                         effective_thu, effective_status)
                        render_teacher_schedule(sessions)

# ── Tab 3: Tra cứu Lớp học ──────────────────────────────────────────────────
with tab3:
    st.subheader("Tra cứu theo mã Lớp học")

    search_class = st.text_input("Nhập mã lớp (hoặc một phần mã lớp)", placeholder="EPP-0715")

    if st.button("Tra cứu", key="btn_search_class"):
        with st.spinner("Đang tải dữ liệu..."):
            df_lop = load_lophoc()

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
                        st.markdown("**Lịch học:**")
                        st.dataframe(class_sessions_table(g), use_container_width=True)

# ── Tab 4: Tra cứu Học viên ──────────────────────────────────────────────────
with tab4:
    st.subheader("Tra cứu theo Học viên")

    search_hv = st.text_input("Nhập tên, ID, ID BOS, SĐT hoặc mã lớp",
                               placeholder="Nguyễn Văn A / HV-0065 / ID-0006", key="hv_search")

    if st.button("Tra cứu", key="btn_search_hv"):
        with st.spinner("Đang tải dữ liệu..."):
            df_hv = load_hocvien()

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
                groups = list(result.groupby(["Sản phẩm", "Mã lớp"], sort=False))
                st.markdown(f"**{len(groups)} lớp** — **{len(result)} học viên**")

                student_cols = ["Sản phẩm", "ID", "ID BOS", "Tên", "Email",
                                 "Số điện thoại", "Trạng thái hv", "Tổng buổi", "Buổi còn lại"]

                for (sp, ma_lop), g in groups:
                    first = g.iloc[0]
                    with st.expander(f"🏫 {ma_lop} — {sp}", expanded=True):
                        schedule = format_hocvien_schedule(first["Lịch học"], first["Giáo viên"])
                        render_class_info(ma_lop, first["Ngày khai giảng"], first["Ngày kết thúc dự kiến"],
                                           first["Trạng thái lớp"], schedule)

                        st.markdown("**Học viên:**")
                        st.dataframe(g[student_cols].reset_index(drop=True),
                                     use_container_width=True, hide_index=True)

# ── Tab 5: Tìm GV Cover ──────────────────────────────────────────────────────
with tab5:
    st.subheader("Tìm GV Cover cho 1 lớp")

    col_x, col_y = st.columns(2)
    with col_x:
        cover_class = st.text_input("Mã lớp cần cover", placeholder="EPP-0715", key="cover_class")
    with col_y:
        cover_date = st.date_input("Ngày cần cover", value=None, key="cover_date")

    if st.button("Tìm GV Cover", key="btn_find_cover"):
        if not cover_class.strip():
            st.warning("Nhập mã lớp cần cover.")
        elif not cover_date:
            st.warning("Chọn ngày cần cover.")
        else:
            with st.spinner("Đang tải dữ liệu..."):
                df_lop = load_lophoc()
                df_gv_all = load_gv()

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
                    thu_needed = WEEKDAY_TO_THU[cover_date.weekday()]
                    day_sessions = class_sessions[class_sessions["Thứ"].str.strip() == thu_needed]

                    if day_sessions.empty:
                        st.info(f"Lớp '{cover_class}' không có buổi học vào {thu_needed} "
                                f"({cover_date.strftime('%d/%m/%Y')}).")
                    else:
                        ended_classes = get_ended_classes(df_lop)

                        for _, sess in day_sessions.iterrows():
                            ctr = sess["Chương trình"]
                            trinh_do = sess["Trình độ"]
                            gio_hoc = sess["Giờ học"]
                            gv_hien_tai = sess["Giáo viên"]

                            st.markdown(
                                f"**Lớp {sess['Mã lớp']}** ({ctr}) — Trình độ lớp: **{trinh_do}** — "
                                f"{thu_needed} {gio_hoc} — GV hiện tại: {gv_hien_tai or '(chưa có)'}"
                            )

                            df_gv_ct = df_gv_all[df_gv_all["Chương trình"] == ctr]
                            if df_gv_ct.empty or thu_needed not in df_gv_ct.columns:
                                st.info("Không có dữ liệu lịch GV cho chương trình này.")
                                st.divider()
                                continue

                            mask_avail = build_avail_mask(df_gv_ct[thu_needed], ended_classes)
                            mask_time = (
                                df_gv_ct["Khung giờ 1"].apply(lambda v: times_match(v, gio_hoc)) |
                                df_gv_ct["Khung giờ 2"].apply(lambda v: times_match(v, gio_hoc))
                            )
                            candidates = df_gv_ct[mask_avail & mask_time]

                            if candidates.empty:
                                st.warning("Không tìm thấy GV nào rảnh đúng khung giờ này.")
                            else:
                                st.caption("Đối chiếu cột 'Trình độ giảng dạy' bên dưới với Trình độ lớp ở trên để chọn GV phù hợp.")
                                show = ["Mã GV", "Giáo viên", "Quốc tịch", "Trình độ giảng dạy"]
                                st.dataframe(candidates[show].reset_index(drop=True), use_container_width=True)

                            st.divider()

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Cài đặt")
    if st.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.success("Đã xóa cache, dữ liệu sẽ được tải lại.")
    st.caption("Dữ liệu tự cập nhật mỗi 5 phút.")
