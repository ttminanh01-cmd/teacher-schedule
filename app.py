import re

import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Tra cứu Giáo Viên", page_icon="📚", layout="wide")

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
        ngay_kg = r[base_idx["Ngày dự kiến KG"]].strip() if "Ngày dự kiến KG" in base_idx else ""
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

# ===== HELPERS =====

def _time_sort_key(slot: str):
    """Sắp xếp khung giờ theo thời gian thực (hỗ trợ cả '8h30' và '08:30')."""
    m = re.search(r"(\d{1,2})[h:](\d{2})", slot)
    return (int(m.group(1)), int(m.group(2))) if m else (99, 99)


def get_time_slots(df_gv: pd.DataFrame) -> list:
    slots = set(df_gv["Khung giờ 1"]) | set(df_gv["Khung giờ 2"])
    slots = {s.strip() for s in slots if s.strip()}
    return sorted(slots, key=_time_sort_key)


def _day_sort_key(thu: str) -> int:
    return DAYS.index(thu) if thu in DAYS else 99


def class_sessions_table(g: pd.DataFrame) -> pd.DataFrame:
    """Bảng các buổi học (Thứ/Giờ học/Giáo viên) của 1 lớp, sắp theo thứ tự Thứ."""
    gg = g.sort_values(by="Thứ", key=lambda col: col.map(_day_sort_key))
    return gg[["Thứ", "Giờ học", "Giáo viên"]].reset_index(drop=True)


def get_classes_of_teacher(program: str, ma_gv: str, df_sessions: pd.DataFrame,
                            thu_filter: str = None) -> pd.DataFrame:
    """Các lớp 1 GV đang dạy, kèm lịch học + ngày KG (tra từ data lớp học).
    Nếu có thu_filter, chỉ giữ các buổi rơi vào đúng Thứ đó."""
    if df_sessions.empty or not ma_gv:
        return pd.DataFrame()

    ma_gv = ma_gv.strip()
    g = df_sessions[
        (df_sessions["Chương trình"] == program) &
        (df_sessions["Mã GV"].str.strip() == ma_gv)
    ]
    if thu_filter:
        g = g[g["Thứ"].str.strip() == thu_filter]
    if g.empty:
        return pd.DataFrame()

    out = []
    for ma_lop, gg in g.groupby("Mã lớp", sort=False):
        first = gg.iloc[0]
        lich = "; ".join(f"{row['Thứ']} {row['Giờ học']}".strip() for _, row in gg.iterrows())
        out.append({
            "Mã lớp": ma_lop,
            "Trình độ": first["Trình độ"],
            "Ngày dự kiến KG": first["Ngày dự kiến KG"],
            "Trạng thái lớp": first["Trạng thái lớp"],
            "Lịch học": lich,
        })
    return pd.DataFrame(out)

# ===== UI =====

st.title("📚 Tra cứu Giáo Viên")

tab1, tab2, tab3 = st.tabs(["🔍 Tìm GV rảnh theo ca", "👤 Tra cứu theo tên GV", "🏫 Tra cứu Lớp học"])

# ── Tab 1: Tìm GV rảnh ──────────────────────────────────────────────────────
with tab1:
    st.subheader("Tìm giáo viên rảnh theo Thứ và Khung giờ")

    with st.spinner("Đang tải dữ liệu..."):
        df_gv_all = load_gv()

    time_options = ["Tất cả khung giờ"] + get_time_slots(df_gv_all) if not df_gv_all.empty else ["Tất cả khung giờ"]

    col1, col2 = st.columns(2)
    with col1:
        selected_day = st.selectbox("Chọn Thứ", DAYS)
    with col2:
        selected_time = st.selectbox("Chọn khung giờ", time_options)

    if st.button("Tìm kiếm", key="btn_find_free"):
        df_gv = df_gv_all

        if df_gv.empty:
            st.error("Không tải được dữ liệu. Kiểm tra lại kết nối sheet.")
        elif selected_day not in df_gv.columns:
            st.error(f"Không tìm thấy cột '{selected_day}' trong sheet.")
        else:
            mask_avail = df_gv[selected_day].str.strip().str.lower() == "available"

            if selected_time != "Tất cả khung giờ":
                mask_time = (
                    (df_gv["Khung giờ 1"].str.strip() == selected_time) |
                    (df_gv["Khung giờ 2"].str.strip() == selected_time)
                )
                result = df_gv[mask_avail & mask_time]
            else:
                result = df_gv[mask_avail]

            st.markdown(f"**{len(result)} khung giờ trống** — {selected_day}"
                        + (f" | {selected_time}" if selected_time != "Tất cả khung giờ" else ""))

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

    col_a, col_b = st.columns(2)
    with col_a:
        filter_thu = st.selectbox("Lọc lớp theo Thứ (tuỳ chọn)", ["Tất cả"] + DAYS, key="gv_filter_thu")
    with col_b:
        filter_date = st.date_input("Hoặc chọn ngày cụ thể (tuỳ chọn)", value=None, key="gv_filter_date")

    effective_thu = None
    if filter_date:
        effective_thu = WEEKDAY_TO_THU[filter_date.weekday()]
    elif filter_thu != "Tất cả":
        effective_thu = filter_thu

    if st.button("Tra cứu", key="btn_search_gv"):
        with st.spinner("Đang tải dữ liệu..."):
            df_gv = load_gv()
            df_lop = load_lophoc()

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
                    with st.expander(f"👤 {t['Giáo viên']}  ({t['Mã GV']} — {t['Chương trình']})", expanded=True):
                        st.markdown(f"**Quốc tịch:** {t['Quốc tịch']}")
                        st.markdown(f"**Trình độ giảng dạy:** {t['Trình độ giảng dạy']}")

                        label = "🏫 Các lớp giảng dạy"
                        if effective_thu:
                            label += f" — {effective_thu}" + (f" ({filter_date.strftime('%d/%m/%Y')})" if filter_date else "")
                        st.markdown(f"**{label}:**")

                        classes = get_classes_of_teacher(t["Chương trình"], t["Mã GV"], df_lop, effective_thu)
                        if classes.empty:
                            st.info("Không có lớp nào trong hệ thống.")
                        else:
                            st.dataframe(classes, use_container_width=True)

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

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Cài đặt")
    if st.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.success("Đã xóa cache, dữ liệu sẽ được tải lại.")
    st.caption("Dữ liệu tự cập nhật mỗi 5 phút.")
