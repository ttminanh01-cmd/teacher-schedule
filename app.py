import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Tra cứu Giáo Viên", page_icon="📚", layout="wide")

SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "")
SHEET_GV      = "Data lịch GV"
SHEET_LOPHOC  = "Data lớp học"
DAYS          = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

# ===== GOOGLE SHEETS =====

def get_gc():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def load_gv():
    ws = get_gc().open_by_key(SPREADSHEET_ID).worksheet(SHEET_GV)
    rows = ws.get_all_values()
    if len(rows) < 2:
        return pd.DataFrame()

    headers = rows[0]
    df = pd.DataFrame(rows[1:], columns=headers)
    df.columns = df.columns.str.strip()
    df = df[df["Mã GV"].str.strip() != ""]
    return df

@st.cache_data(ttl=300)
def load_lophoc():
    ws = get_gc().open_by_key(SPREADSHEET_ID).worksheet(SHEET_LOPHOC)
    rows = ws.get_all_values()
    if len(rows) < 3:
        return pd.DataFrame()

    # Row 0 = category (Buổi 1, Buổi 2...), Row 1 = column names
    cat_row = rows[0]
    col_row = rows[1]

    headers = []
    current_cat = ""
    for i, col in enumerate(col_row):
        if i < len(cat_row) and cat_row[i].strip():
            current_cat = cat_row[i].strip()
        prefix = f"{current_cat}_" if current_cat and i >= 5 else ""
        headers.append(f"{prefix}{col.strip()}" if col.strip() else f"col_{i}")

    df = pd.DataFrame(rows[2:], columns=headers)
    df = df[df.iloc[:, 0].str.strip() != ""]
    return df

# ===== HELPERS =====

def get_classes_of_teacher(ma_gv: str, df_lop: pd.DataFrame) -> pd.DataFrame:
    """Lấy các lớp mà GV đang dạy (tìm theo Mã GV trong tất cả cột)."""
    if df_lop.empty or not ma_gv:
        return pd.DataFrame()

    ma_gv = ma_gv.strip()
    gv_cols = [c for c in df_lop.columns if "Mã GV" in c]
    mask = pd.Series([False] * len(df_lop), index=df_lop.index)
    for col in gv_cols:
        mask |= df_lop[col].str.strip() == ma_gv

    base_cols = ["Mã lớp", "Sản phẩm", "Trình độ", "Ngày dự kiến KG"]
    buoi_cols = [c for c in df_lop.columns if any(
        x in c for x in ["Thứ", "Giờ học", "Giáo viên"]
    )]
    show_cols = [c for c in base_cols + buoi_cols if c in df_lop.columns]
    return df_lop[mask][show_cols].reset_index(drop=True)

# ===== UI =====

st.title("📚 Tra cứu Giáo Viên")

tab1, tab2 = st.tabs(["🔍 Tìm GV rảnh theo ca", "👤 Tra cứu theo tên GV"])

# ── Tab 1: Tìm GV rảnh ──────────────────────────────────────────────────────
with tab1:
    st.subheader("Tìm giáo viên rảnh theo Thứ và Khung giờ")

    col1, col2 = st.columns(2)
    with col1:
        selected_day = st.selectbox("Chọn Thứ", DAYS)
    with col2:
        search_time = st.text_input("Nhập giờ cần tìm (ví dụ: 8h30, 14h00)", placeholder="8h30")

    if st.button("Tìm kiếm", key="btn_find_free"):
        with st.spinner("Đang tải dữ liệu..."):
            df_gv = load_gv()

        if df_gv.empty:
            st.error("Không tải được dữ liệu. Kiểm tra lại kết nối sheet.")
        elif selected_day not in df_gv.columns:
            st.error(f"Không tìm thấy cột '{selected_day}' trong sheet.")
        else:
            # Lọc dòng Available theo ngày
            mask_avail = df_gv[selected_day].str.strip().str.lower() == "available"

            # Lọc thêm theo giờ nếu có nhập
            if search_time.strip():
                t = search_time.strip().lower().replace(" ", "")
                mask_time = (
                    df_gv["Khung giờ (S)"].str.lower().str.replace(" ", "").str.contains(t, na=False) |
                    df_gv["Khung giờ (1:x)"].str.lower().str.replace(" ", "").str.contains(t, na=False)
                )
                result = df_gv[mask_avail & mask_time]
            else:
                result = df_gv[mask_avail]

            st.markdown(f"**{len(result)} khung giờ trống** — {selected_day}"
                        + (f" | giờ chứa '{search_time}'" if search_time.strip() else ""))

            if result.empty:
                st.info("Không có giáo viên nào rảnh trong khung giờ này.")
            else:
                show = ["Mã GV", "Giáo viên", "Quốc tịch", "Trình độ giảng dạy",
                        "Khung giờ (S)", "Khung giờ (1:x)"]
                show = [c for c in show if c in result.columns]
                st.dataframe(result[show].reset_index(drop=True), use_container_width=True)

# ── Tab 2: Tra cứu theo GV ──────────────────────────────────────────────────
with tab2:
    st.subheader("Tra cứu lịch và lớp theo tên Giáo Viên")

    search_name = st.text_input("Nhập tên hoặc mã GV", placeholder="Nguyễn Thị Hồng Hạnh / GV0001")

    if st.button("Tra cứu", key="btn_search_gv"):
        with st.spinner("Đang tải dữ liệu..."):
            df_gv   = load_gv()
            df_lop  = load_lophoc()

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
                # Lấy danh sách GV tìm được
                teachers = result[["Mã GV", "Giáo viên"]].drop_duplicates("Mã GV")

                for _, t in teachers.iterrows():
                    ma_gv  = t["Mã GV"].strip()
                    ten_gv = t["Giáo viên"].strip()

                    with st.expander(f"👤 {ten_gv}  ({ma_gv})", expanded=True):
                        gv_rows = result[result["Mã GV"].str.strip() == ma_gv]

                        # Lịch theo tuần
                        st.markdown("**📅 Lịch theo tuần:**")
                        schedule_cols = ["Khung giờ (S)", "Khung giờ (1:x)"] + DAYS
                        show_sched = [c for c in schedule_cols if c in gv_rows.columns]
                        st.dataframe(gv_rows[show_sched].reset_index(drop=True),
                                     use_container_width=True)

                        # Các lớp đang dạy
                        st.markdown("**🏫 Các lớp đang dạy:**")
                        classes = get_classes_of_teacher(ma_gv, df_lop)
                        if classes.empty:
                            st.info("Không có lớp nào trong hệ thống.")
                        else:
                            st.dataframe(classes, use_container_width=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Cài đặt")
    if st.button("🔄 Làm mới dữ liệu"):
        st.cache_data.clear()
        st.success("Đã xóa cache, dữ liệu sẽ được tải lại.")
    st.caption("Dữ liệu tự cập nhật mỗi 5 phút.")
