# Cổng CTV

Web quản lý cộng tác viên: đăng ký lịch rảnh, xếp lịch, điểm danh, đổi ca, cẩm nang, tính lương.
Gồm 2 khu: **CTV** (`/ctv`) và **Quản trị** (`/admin`), dùng chung một backend.

## Chạy

```bat
pip install -r requirements.txt   :: chỉ cần lần đầu (fastapi, uvicorn)
run.bat                           :: hoặc: python -m uvicorn server.app:app --port 8765 --reload
```

Mở http://localhost:8765/ctv và http://localhost:8765/admin

Lần chạy đầu hệ thống tự tạo cấu hình (2 task: Trực Page + Hotline / + monitor; 3 ca: 08:30–12:00, 13:30–18:00, 18:00–22:00; 25.000đ/giờ)
và tài khoản `admin` / `admin123` (đặt biến môi trường `ADMIN_PASSWORD` để đổi mật khẩu ban đầu).

### Nhập dữ liệu CTV từ Google Sheet vận hành

```bat
python -m server.import_sheet --reset --password <mật khẩu ban đầu cho CTV>
```

- Danh sách CTV lấy từ `data/ctv_roster.csv` (cột `name,username,position,hourly_rate,status`). Chỉ người **Active** được tạo tài khoản; người Inactive bị khoá và dữ liệu của họ bị bỏ qua.
- Từ sheet: mã CTV, email, phòng ban (tab Tính lương — không nhập CCCD/ngày sinh), lịch trực, đăng ký lịch làm, lỗi QC.
- Ca đã qua trong lịch trực được coi là đã làm đủ (sheet không có giờ check-in).
- `--reset` xoá dữ liệu CTV cũ trước khi nhập (giữ admin và cấu hình).

## Tính năng

**CTV**
- Tổng quan: giờ đã làm, tỷ lệ đúng giờ, ca hôm nay (check-in nhanh), biểu đồ giờ/tuần, ca sắp tới
- Lịch làm việc: lịch theo tuần (trên điện thoại hiện dạng danh sách), check-in mở trước ca 5 phút, check-out kèm ghi chú, xin đổi ca, xuất Excel
- Đăng ký lịch rảnh: bấm chọn ca rảnh theo thứ × ca, lưu nháp / chốt, chép lịch tháng trước
- Lịch team theo ngày, phiếu đổi ca (gửi đi / nhận về)
- Cẩm nang: đọc trực tiếp Google Sheet (mỗi tab là một mục), tự cập nhật sau 5 phút hoặc bấm Làm mới; tìm trong mục hoặc tất cả mục; nút sao chép cho script dài
- Tra cứu lương (chỉ tháng đã công bố, kèm danh sách lỗi QC), lịch sử làm việc, nhật ký

**Quản trị**
- Tổng quan ngày: số ca, đã check-in, muộn, vắng, phiếu chờ duyệt, số CTV đã nộp lịch rảnh
- Xếp lịch theo tuần: gợi ý CTV đã đăng ký rảnh, chọn nhiều người một lúc, chặn trùng giờ, sao chép tuần trước
- Lịch rảnh CTV: mở/đóng đăng ký theo tháng, bản đồ mật độ rảnh, mở khoá lịch đã chốt, xuất Excel
- Chấm công: lọc theo trạng thái, sửa giờ vào/ra (tự tính lại phút muộn), xuất Excel tháng
- Duyệt đổi ca (duyệt xong ca tự chuyển sang người làm thay)
- Lỗi QC: ghi lỗi, hình thức phạt (chọn nhanh: Nhắc nhở / 1/2h làm / 1h làm / 50% buổi học), số tiền, phân loại; xuất Excel
- Bảng lương: giờ công × 25.000đ − phạt lỗi QC + lương CTV gọi − khấu trừ khác; công bố / thu hồi; xuất Excel
- Nhân sự (thêm/sửa/khoá, đặt lại mật khẩu), danh mục (team, vị trí & đơn giá, khung ca), thông báo, nhật ký hệ thống
- Cẩm nang: đổi link Google Sheet, chọn tab nào hiện cho CTV. Sheet phải chia sẻ “Bất kỳ ai có đường liên kết — Người xem”

## Cấu trúc

```
server/app.py     API (FastAPI)
server/db.py      Schema SQLite, dữ liệu mẫu, hằng số (phạt muộn, giờ mở check-in)
server/handbook.py Đọc Google Sheet cho Cẩm nang (cache 5 phút)
server/import_sheet.py Nhập CTV, lịch trực, đăng ký, lỗi QC từ sheet vận hành
static/ctv.html   + js/ctv.js     giao diện CTV
static/admin.html + js/admin.js   giao diện quản trị
static/js/common.js               khung giao diện, gọi API, modal, toast, bảng
static/css/styles.css             giao diện
data/ctv.db       cơ sở dữ liệu (tự tạo)
```

## Triển khai (Render free + Neon Postgres free)

1. **Neon** (neon.tech) → tạo project, region **Singapore** → copy *connection string* (`postgresql://…?sslmode=require`).
2. Chuyển dữ liệu hiện có: ghi `DATABASE_URL=…` vào file `.env` (không commit) rồi
   `python -m server.migrate_to_pg` (chạy thử) → `python -m server.migrate_to_pg --go`.
3. **Render** (render.com) → New → **Blueprint** → chọn repo này (đọc `render.yaml`), điền `DATABASE_URL`, `ADMIN_PASSWORD`.
   `CRON_KEY` được tạo tự động (xem trong tab Environment).
4. **cron-job.org** → tạo job gọi `https://<tên-app>.onrender.com/api/cron/tick?key=<CRON_KEY>` **mỗi 10 phút**:
   giữ web không "ngủ" và từ 20:00 Chủ nhật tự xếp ca tuần tới.

Biến môi trường: xem `.env.example`. Link các Google Sheet không để trong code (repo public) —
đặt trong Quản trị (Cẩm nang, Đẩy lịch lên Sheet) hoặc biến môi trường `HANDBOOK_SHEET_ID`, `PAYROLL_SHEET_ID`, `OPS_SHEET_ID`.
Người dùng còn mật khẩu mặc định sẽ bị yêu cầu đổi ở lần đăng nhập đầu.
