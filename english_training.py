import json
import html
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


CATALOG_PATH = Path(__file__).with_name("course_catalog_raw.json")
EXTENDED_VOCAB_PATH = Path(__file__).with_name("english_vocab_extended.json")

WORKPLACE_PATH = {
    "Pre-A1 · Khởi động": {
        "hours": "0–90 giờ", "outcome": "Đọc được âm cơ bản, giới thiệu bản thân và dùng câu sinh tồn.",
        "modules": ["Bảng chữ cái & đánh vần", "Âm cuối và trọng âm", "Be / đại từ / câu đơn", "Số, giờ và ngày tháng", "Chào hỏi", "Thông tin cá nhân"],
        "work": "Đánh vần email, giới thiệu tên - vai trò - công ty trong 30 giây.",
        "phrases": [("My name is Minh.", "Tên tôi là Minh."), ("I work in sales.", "Tôi làm bộ phận kinh doanh."), ("Could you repeat that?", "Bạn có thể nhắc lại không?"), ("How do you spell that?", "Từ đó đánh vần thế nào?")],
        "grammar": "S + be + danh từ/tính từ · S + V · Câu hỏi What/Where/How",
    },
    "A1 · Nền tảng": {
        "hours": "90–200 giờ", "outcome": "Xử lý hội thoại ngắn và đọc/viết thông tin quen thuộc.",
        "modules": ["Hiện tại đơn", "There is / are", "Can / can't", "Câu hỏi cơ bản", "Lịch làm việc", "Chỉ dẫn đơn giản"],
        "work": "Xác nhận lịch, hỏi thông tin và mô tả công việc thường ngày.",
        "phrases": [("I start work at eight.", "Tôi bắt đầu làm lúc 8 giờ."), ("Are you available tomorrow?", "Ngày mai bạn có rảnh không?"), ("I can send it today.", "Tôi có thể gửi hôm nay."), ("Where is the meeting room?", "Phòng họp ở đâu?")],
        "grammar": "Hiện tại đơn · do/does · can · giới từ thời gian và địa điểm",
    },
    "A2 · Giao tiếp chủ động": {
        "hours": "180–350 giờ", "outcome": "Trao đổi việc quen thuộc, viết email ngắn và xử lý yêu cầu đơn giản.",
        "modules": ["Quá khứ & tương lai", "So sánh", "Yêu cầu lịch sự", "Điện thoại", "Email cơ bản", "Vấn đề & giải pháp"],
        "work": "Viết email sắp lịch, cập nhật tiến độ và giải thích một vấn đề đơn giản.",
        "phrases": [("I'm writing to confirm our meeting.", "Tôi viết để xác nhận cuộc họp."), ("Could you send me the file?", "Bạn có thể gửi tôi tệp không?"), ("There was a delay.", "Đã có sự chậm trễ."), ("I'll update you by Friday.", "Tôi sẽ cập nhật trước thứ Sáu.")],
        "grammar": "Past simple · be going to / will · could · because / so",
    },
    "B1 · Làm việc độc lập": {
        "hours": "350–500 giờ", "outcome": "Tham gia họp, viết email rõ ràng và trình bày quan điểm có lý do.",
        "modules": ["Cập nhật dự án", "Họp & làm rõ", "Email có cấu trúc", "Phản hồi", "Báo cáo ngắn", "Social English"],
        "work": "Điều hành phần cập nhật 3 phút và viết email gồm bối cảnh - hành động - thời hạn.",
        "phrases": [("Here's a quick update.", "Đây là cập nhật nhanh."), ("Could you clarify what you mean?", "Bạn có thể làm rõ ý không?"), ("From my perspective...", "Theo góc nhìn của tôi..."), ("The next step is to...", "Bước tiếp theo là...")],
        "grammar": "Present perfect · conditionals 0/1 · relative clauses · linking words",
    },
    "B2 · Chuyên nghiệp": {
        "hours": "500–700 giờ", "outcome": "Giao tiếp tự tin trong tình huống phức tạp và viết tài liệu chuyên nghiệp.",
        "modules": ["Thuyết trình", "Đàm phán", "Họp khó", "Báo cáo & đề xuất", "Phỏng vấn", "Giao tiếp liên văn hóa"],
        "work": "Thuyết trình 8–10 phút, bảo vệ đề xuất và thương lượng giải pháp.",
        "phrases": [("The key takeaway is...", "Điểm chính cần nhớ là..."), ("I'd like to propose...", "Tôi muốn đề xuất..."), ("I see your point; however...", "Tôi hiểu ý bạn, tuy nhiên..."), ("Can we find a middle ground?", "Ta có thể tìm phương án dung hòa không?")],
        "grammar": "Conditionals 2/3 · passive · hedging · complex linking",
    },
    "C1 · Dẫn dắt": {
        "hours": "700–800+ giờ", "outcome": "Diễn đạt chính xác, linh hoạt và dẫn dắt giao tiếp chuyên môn.",
        "modules": ["Executive presence", "Thuyết phục", "Khủng hoảng", "Coaching", "Văn bản chiến lược", "Networking cấp cao"],
        "work": "Dẫn dắt họp, xử lý phản biện và viết executive summary cô đọng.",
        "phrases": [("Let me frame the issue differently.", "Để tôi đặt vấn đề theo góc khác."), ("The evidence suggests that...", "Bằng chứng cho thấy..."), ("A potential trade-off is...", "Một đánh đổi có thể có là..."), ("To put this into perspective...", "Để đặt điều này vào đúng bối cảnh...")],
        "grammar": "Register · nuance · nominalisation · advanced cohesion",
    },
}

ENGLISH_SOURCES = {
    "Khung CEFR": "https://www.coe.int/en/web/common-european-framework-reference-languages",
    "Business English - British Council": "https://learnenglish.britishcouncil.org/business-english",
    "English for emails": "https://learnenglish.britishcouncil.org/business/english-emails",
    "Thời lượng tham khảo": "https://support.cambridgeenglish.org/hc/en-gb/articles/202838506-Guided-learning-hours",
}

WORKPLACE_VOCAB = {
    "Pre-A1 · Khởi động": [
        ("name", "/neɪm/", "tên", "My name is Lan."), ("work", "/wɜːk/", "làm việc", "I work in Hanoi."),
        ("team", "/tiːm/", "đội, nhóm", "This is my team."), ("email", "/ˈiː.meɪl/", "email", "Please check your email."),
        ("repeat", "/rɪˈpiːt/", "nhắc lại", "Could you repeat that?"), ("spell", "/spel/", "đánh vần", "How do you spell your name?"),
    ],
    "A1 · Nền tảng": [
        ("available", "/əˈveɪ.lə.bəl/", "có thể tham gia, rảnh", "Are you available at two?"), ("schedule", "/ˈʃedʒ.uːl/", "lịch trình", "I checked the schedule."),
        ("meeting", "/ˈmiː.tɪŋ/", "cuộc họp", "The meeting starts at nine."), ("task", "/tɑːsk/", "nhiệm vụ", "This task is easy."),
        ("send", "/send/", "gửi", "I can send the file today."), ("finish", "/ˈfɪn.ɪʃ/", "hoàn thành", "I finish work at five."),
    ],
    "A2 · Giao tiếp chủ động": [
        ("confirm", "/kənˈfɜːm/", "xác nhận", "I'm writing to confirm our meeting."), ("delay", "/dɪˈleɪ/", "sự chậm trễ", "There was a short delay."),
        ("update", "/ˈʌp.deɪt/", "bản cập nhật", "Here is the latest update."), ("request", "/rɪˈkwest/", "yêu cầu", "We received your request."),
        ("deadline", "/ˈded.laɪn/", "hạn chót", "The deadline is Friday."), ("arrange", "/əˈreɪndʒ/", "sắp xếp", "Can we arrange a call?"),
    ],
    "B1 · Làm việc độc lập": [
        ("progress", "/ˈprəʊ.ɡres/", "tiến độ", "We've made good progress."), ("clarify", "/ˈklær.ɪ.faɪ/", "làm rõ", "Could you clarify the last point?"),
        ("priority", "/praɪˈɒr.ə.ti/", "ưu tiên", "Quality is our main priority."), ("feedback", "/ˈfiːd.bæk/", "phản hồi", "Thank you for your feedback."),
        ("solution", "/səˈluː.ʃən/", "giải pháp", "We found a practical solution."), ("follow up", "/ˈfɒl.əʊ ʌp/", "theo dõi, liên hệ tiếp", "I'll follow up tomorrow."),
    ],
    "B2 · Chuyên nghiệp": [
        ("proposal", "/prəˈpəʊ.zəl/", "đề xuất", "The board approved our proposal."), ("negotiate", "/nɪˈɡəʊ.ʃi.eɪt/", "đàm phán", "We need to negotiate the price."),
        ("stakeholder", "/ˈsteɪkˌhəʊl.dər/", "bên liên quan", "We consulted key stakeholders."), ("outcome", "/ˈaʊt.kʌm/", "kết quả", "The outcome exceeded expectations."),
        ("trade-off", "/ˈtreɪd.ɒf/", "sự đánh đổi", "There is a trade-off between speed and cost."), ("perspective", "/pəˈspek.tɪv/", "góc nhìn", "Let's consider the client's perspective."),
    ],
    "C1 · Dẫn dắt": [
        ("implication", "/ˌɪm.plɪˈkeɪ.ʃən/", "hệ quả, hàm ý", "We must consider the long-term implications."), ("alignment", "/əˈlaɪn.mənt/", "sự đồng thuận, liên kết", "We need alignment across teams."),
        ("compelling", "/kəmˈpel.ɪŋ/", "thuyết phục", "She presented a compelling argument."), ("mitigate", "/ˈmɪt.ɪ.ɡeɪt/", "giảm thiểu", "This plan will mitigate the risk."),
        ("viable", "/ˈvaɪ.ə.bəl/", "khả thi", "We need a viable alternative."), ("consensus", "/kənˈsen.səs/", "sự đồng thuận", "The group reached a consensus."),
    ],
}

GRAMMAR_MAPS = {
    "Pre-A1 · Khởi động": [
        ("S + be", "I am / You are / She is", "Giới thiệu và mô tả", "I am a teacher.", "Không bỏ am/is/are"),
        ("S + V", "I work / We study", "Nói hành động", "I work in sales.", "Không thêm to trước động từ chính"),
        ("Wh-question", "What/Where + be/do + S?", "Hỏi thông tin", "Where do you work?", "Đưa trợ động từ ra trước chủ ngữ"),
    ],
    "A1 · Nền tảng": [
        ("Present simple", "S + V(s/es)", "Thói quen, lịch cố định", "The meeting starts at nine.", "He/she/it cần s/es"),
        ("Can", "S + can + V", "Khả năng, đề nghị", "I can send it today.", "Sau can dùng động từ nguyên mẫu"),
        ("There is/are", "There is + số ít; There are + số nhiều", "Nói sự tồn tại", "There are two tasks.", "Chọn is/are theo danh từ sau"),
    ],
    "A2 · Giao tiếp chủ động": [
        ("Past simple", "S + V2/ed", "Việc đã kết thúc", "We received the file yesterday.", "Có thời gian quá khứ thì không dùng hiện tại"),
        ("Future", "will / be going to + V", "Quyết định hoặc kế hoạch", "I'll update you on Friday.", "Không dùng will sau when/if"),
        ("Polite request", "Could you + V...?", "Yêu cầu lịch sự", "Could you confirm the time?", "Dùng dấu hỏi và giọng mềm"),
    ],
    "B1 · Làm việc độc lập": [
        ("Present perfect", "have/has + V3", "Kết quả liên quan hiện tại", "We've completed the first phase.", "Không đi với thời điểm quá khứ đã kết thúc"),
        ("First conditional", "If + present, will + V", "Khả năng thực tế", "If we finish today, we'll send it tomorrow.", "Không dùng will trong mệnh đề if"),
        ("Relative clause", "who/which/that + clause", "Bổ sung thông tin", "The file that you sent is clear.", "Chọn who cho người, which cho vật"),
    ],
    "B2 · Chuyên nghiệp": [
        ("Passive", "be + V3", "Nhấn hành động/kết quả", "The proposal was approved.", "Chia be đúng thì"),
        ("Hedging", "may / might / tend to / appears to", "Làm nhận định thận trọng", "This may affect the timeline.", "Tránh khẳng định tuyệt đối khi thiếu dữ liệu"),
        ("Second conditional", "If + past, would + V", "Giả định hiện tại", "If we had more time, we would test it again.", "Dùng past sau if"),
    ],
    "C1 · Dẫn dắt": [
        ("Nominalisation", "verb/adjective → noun", "Văn phong cô đọng, trang trọng", "We evaluated it → Our evaluation...", "Không lạm dụng làm câu khó đọc"),
        ("Inversion", "Negative adverb + auxiliary + S", "Nhấn mạnh trang trọng", "Rarely have we faced such pressure.", "Phải đảo trợ động từ"),
        ("Advanced cohesion", "whereas / nevertheless / thereby", "Liên kết lập luận", "Costs fell, thereby improving margins.", "Chọn từ nối đúng quan hệ logic"),
    ],
}


def _drive_link(file_id, is_folder=False):
    kind = "folders" if is_folder else "file/d"
    suffix = "" if is_folder else "/view"
    return f"https://drive.google.com/drive/{kind}/{file_id}{suffix}"


@st.cache_data
def load_course_catalog():
    if not CATALOG_PATH.exists():
        return []
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@st.cache_data
def load_extended_vocabulary():
    if not EXTENDED_VOCAB_PATH.exists():
        return {}
    return json.loads(EXTENDED_VOCAB_PATH.read_text(encoding="utf-8"))


def _resource_type(name):
    suffix = Path(name).suffix.lower()
    return {".mp4": "Video", ".mp3": "Audio", ".pdf": "PDF"}.get(suffix, "Thư mục")


def render_full_course():
    catalog = load_course_catalog()
    if not catalog:
        st.warning("Chưa tải được danh mục khóa học.")
        return

    st.markdown("### Lộ trình IELTS Nguyễn Huyền")
    st.caption("Chọn kỹ năng và mở đúng video/tài liệu gốc trên Google Drive. Tiến độ được lưu trong phiên hiện tại.")
    modules = {entry["folder"]["name"]: entry for entry in catalog}
    module_name = st.selectbox("Kỹ năng / khóa học", list(modules), key="course_module")
    module = modules[module_name]
    resources = [item for item in module["items"] if item.get("name") and item["name"] != ".DS_Store"]

    type_options = ["Tất cả"] + sorted({_resource_type(item["name"]) for item in resources})
    col_type, col_search = st.columns([1, 2])
    with col_type:
        selected_type = st.selectbox("Loại nội dung", type_options, key="course_resource_type")
    with col_search:
        keyword = st.text_input("Tìm bài", placeholder="Ví dụ: câu bị động, map, environment...", key="course_search")

    if selected_type != "Tất cả":
        resources = [item for item in resources if _resource_type(item["name"]) == selected_type]
    if keyword.strip():
        resources = [item for item in resources if keyword.strip().lower() in item["name"].lower()]

    completed = sum(bool(st.session_state.get(f"course_done_{item['id']}")) for item in resources)
    st.progress(completed / len(resources) if resources else 0, text=f"Tiến độ danh sách đang xem: {completed}/{len(resources)}")
    st.link_button("📂 Mở thư mục khóa học", _drive_link(module["folder"]["id"], is_folder=True))

    if not resources:
        st.info("Không tìm thấy bài phù hợp với bộ lọc.")
        return

    icons = {"Video": "🎬", "Audio": "🎧", "PDF": "📄", "Thư mục": "📁"}
    for index, item in enumerate(resources, 1):
        resource_type = _resource_type(item["name"])
        with st.expander(f"{icons[resource_type]} {index}. {item['name']}"):
            st.markdown(f"**Loại:** {resource_type}")
            st.link_button(f"Mở {resource_type.lower()} trên Google Drive ↗", _drive_link(item["id"], is_folder=resource_type == "Thư mục"))
            st.checkbox("Đã học xong", key=f"course_done_{item['id']}")


LESSONS = {
    "Giao tiếp với học viên": {
        "Mới bắt đầu": {
            "goal": "Chào hỏi, kiểm tra âm thanh và hướng dẫn học viên bằng câu ngắn.",
            "words": [
                ("Can you hear me?", "Bạn có nghe thấy tôi không?", "Can you hear me clearly?"),
                ("Please repeat", "Vui lòng nhắc lại", "Please repeat after me."),
                ("Well done", "Làm tốt lắm", "Well done! Let's continue."),
                ("Any questions?", "Bạn có câu hỏi nào không?", "Do you have any questions?"),
            ],
            "dialogue": [("Teacher", "Hello! Can you hear me clearly?"), ("Student", "Yes, I can."),
                         ("Teacher", "Great. Please open your book to page ten."), ("Student", "Okay, teacher.")],
            "quiz": [
                ("Câu nào dùng để kiểm tra âm thanh?", ["Can you hear me?", "How old are you?", "Where do you live?"], 0),
                ("“Please repeat” có nghĩa là gì?", ["Vui lòng đợi", "Vui lòng nhắc lại", "Vui lòng ngồi xuống"], 1),
                ("Câu nào dùng để khen học viên?", ["Try tomorrow", "Be quiet", "Well done"], 2),
            ],
            "speaking": "Chào học viên, kiểm tra âm thanh và yêu cầu học viên mở sách.",
        },
        "Trung cấp": {
            "goal": "Đưa hướng dẫn rõ ràng, sửa lỗi tích cực và kiểm tra mức độ hiểu bài.",
            "words": [
                ("Let's go over it again", "Hãy xem lại lần nữa", "Let's go over the last example again."),
                ("You're on the right track", "Bạn đang đi đúng hướng", "You're on the right track; check the verb tense."),
                ("Could you elaborate?", "Bạn có thể nói rõ hơn không?", "Could you elaborate on your answer?"),
                ("Take your time", "Cứ từ từ", "Take your time and think about the question."),
            ],
            "dialogue": [("Student", "I don't understand this question."),
                         ("Teacher", "No problem. Let's go over it again."),
                         ("Teacher", "Look at the verb tense. What do you notice?"),
                         ("Student", "It should be in the past tense."),
                         ("Teacher", "Exactly. You're on the right track.")],
            "quiz": [
                ("Câu nào khuyến khích học viên suy nghĩ bình tĩnh?", ["Take your time", "Hurry up", "Skip it"], 0),
                ("“Elaborate” gần nghĩa nhất với từ nào?", ["Repeat", "Explain further", "Translate"], 1),
                ("Cách sửa lỗi tích cực là gì?", ["That's completely wrong", "You're on the right track", "Stop answering"], 1),
            ],
            "speaking": "Một học viên trả lời sai thì quá khứ. Hãy sửa lỗi tích cực và gợi ý để học viên tự sửa.",
        },
    },
    "Xử lý tình huống lớp học": {
        "Mới bắt đầu": {
            "goal": "Thông báo sự cố, xin học viên chờ và hướng dẫn kết nối lại.",
            "words": [
                ("connection issue", "sự cố kết nối", "There is a connection issue."),
                ("Please wait a moment", "Vui lòng chờ một lát", "Please wait a moment while I reconnect."),
                ("join the class again", "vào lại lớp", "Please join the class again."),
                ("I will be right back", "Tôi sẽ quay lại ngay", "I will be right back in one minute."),
            ],
            "dialogue": [("Teacher", "There is a connection issue. Please wait a moment."),
                         ("Student", "Okay."), ("Teacher", "Please join the class again using the same link.")],
            "quiz": [
                ("“Sự cố kết nối” là gì?", ["connection issue", "class issue", "homework issue"], 0),
                ("Câu lịch sự để yêu cầu chờ là gì?", ["Wait!", "Please wait a moment", "Don't move"], 1),
                ("“Join again” có nghĩa là gì?", ["Thoát ra", "Vào lại", "Tắt máy"], 1),
            ],
            "speaking": "Thông báo mạng có vấn đề, xin học viên chờ và hướng dẫn bạn ấy vào lại lớp.",
        },
        "Trung cấp": {
            "goal": "Giải thích thay đổi lịch học và đưa ra phương án xử lý chuyên nghiệp.",
            "words": [
                ("reschedule the lesson", "đổi lịch buổi học", "We need to reschedule the lesson."),
                ("make-up class", "buổi học bù", "We can arrange a make-up class."),
                ("available time slot", "khung giờ còn trống", "Which available time slot works for you?"),
                ("I apologize for the inconvenience", "Tôi xin lỗi vì sự bất tiện", "I apologize for the inconvenience caused."),
            ],
            "dialogue": [("Teacher", "I apologize, but we need to reschedule today's lesson."),
                         ("Student", "When can we have the make-up class?"),
                         ("Teacher", "I have a slot on Thursday at 7 p.m. Would that work for you?")],
            "quiz": [
                ("“Buổi học bù” trong tiếng Anh là gì?", ["extra homework", "make-up class", "free lesson"], 1),
                ("Câu nào hỏi lịch chuyên nghiệp?", ["Are you free or not?", "Would that work for you?", "You must come Thursday."], 1),
                ("“Reschedule” có nghĩa là gì?", ["Hủy vĩnh viễn", "Đổi lịch", "Bắt đầu sớm"], 1),
            ],
            "speaking": "Xin lỗi vì phải đổi lịch, đề xuất một buổi học bù và xác nhận thời gian với học viên.",
        },
    },
}


def render_english_training():
    st.subheader("Training tiếng Anh")
    st.caption("Lộ trình từ mất gốc đến giao tiếp, đọc và viết chuyên nghiệp trong công việc.")
    mode = st.radio(
        "Chương trình", ["🚀 Từ mất gốc đến công sở", "⚡ Luyện tình huống", "🎓 Video IELTS tham khảo"],
        horizontal=True, key="english_program_mode",
    )
    if mode.startswith("🚀"):
        render_workplace_path()
    elif mode.startswith("⚡"):
        render_quick_training()
    else:
        render_full_course()


def _roadmap_card(level, data, active=False):
    color = "#2563eb" if active else "#64748b"
    background = "#eff6ff" if active else "#f8fafc"
    st.markdown(
        f"<div style='min-height:150px;padding:15px;border-radius:15px;background:{background};border:2px solid {color}'>"
        f"<div style='font-size:19px;font-weight:800;color:{color}'>{level}</div>"
        f"<div style='font-size:13px;color:#64748b;margin:3px 0 8px'>{data['hours']}</div>"
        f"<div style='font-size:14px'>{data['outcome']}</div></div>", unsafe_allow_html=True,
    )


def render_workplace_path():
    st.markdown("### Bản đồ năng lực tiếng Anh công sở")
    st.caption("Đích đề xuất: B2 để làm việc độc lập; C1 để dẫn dắt và xử lý nội dung chuyên môn phức tạp.")
    levels = list(WORKPLACE_PATH)
    selected = st.selectbox("Chặng đang học", levels, key="workplace_level")
    for start in range(0, len(levels), 3):
        columns = st.columns(3)
        for column, level in zip(columns, levels[start:start + 3]):
            with column:
                _roadmap_card(level, WORKPLACE_PATH[level], active=level == selected)

    data = WORKPLACE_PATH[selected]
    st.info(f"🎯 **Kết quả chặng:** {data['outcome']}  \n💼 **Nhiệm vụ công việc:** {data['work']}")
    view = st.radio(
        "Cách học", ["🧭 Lộ trình", "📚 Từ vựng", "🧠 Ngữ pháp", "✍️ Luyện 4 kỹ năng", "📅 Kế hoạch tuần"],
        horizontal=True, key="workplace_view",
    )
    if view.startswith("🧭"):
        _render_workplace_map(selected, data)
    elif view.startswith("📚"):
        _render_workplace_vocab(selected, data)
    elif view.startswith("🧠"):
        _render_grammar_map(selected)
    elif view.startswith("✍️"):
        _render_four_skills(selected, data)
    else:
        _render_week_plan(selected, data)

    with st.expander("Nguồn xây dựng lộ trình"):
        st.caption("Nguồn dùng để đối chiếu cấp độ, thời lượng và các kỹ năng tiếng Anh công sở trọng tâm.")
        for label, url in ENGLISH_SOURCES.items():
            st.markdown(f"- [{label}]({url})")


def _render_workplace_map(level, data):
    branches = ["🔊 Nghe & phát âm", "🗣️ Nói & tương tác", "📖 Đọc", "✍️ Viết"]
    branch_html = "".join(
        f"<div style='padding:14px 8px;background:white;border-radius:12px;border:1px solid #bfdbfe;text-align:center;font-weight:700'>{item}</div>"
        for item in branches
    )
    st.markdown(
        f"<div style='padding:22px;border-radius:18px;background:linear-gradient(135deg,#eff6ff,#ecfeff);border:1px solid #bae6fd'>"
        f"<div style='text-align:center;font-size:25px;font-weight:850;color:#1d4ed8'>{level}</div>"
        f"<div style='text-align:center;font-size:20px;color:#0284c7;margin:6px'>↓ phát triển đồng thời ↓</div>"
        f"<div style='display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px'>{branch_html}</div>"
        f"<div style='text-align:center;margin-top:14px;font-weight:750;color:#0f766e'>→ {data['work']}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("#### Các mô-đun")
    columns = st.columns(3)
    completed = 0
    for index, module in enumerate(data["modules"]):
        done = columns[index % 3].checkbox(
            f"{index + 1}. {module}", key=f"workplace_module_{level}_{index}",
        )
        completed += int(done)
    st.progress(completed / len(data["modules"]), text=f"Tiến độ chặng: {completed}/{len(data['modules'])} mô-đun")
    st.markdown(f"**Ngữ pháp cốt lõi:** {data['grammar']}")
    st.success("Mẹo học: học một cấu trúc → nghe trong ngữ cảnh → nói lại → dùng trong email/tình huống thật trong cùng một tuần.")


def _render_workplace_vocab(level, data):
    st.markdown(f"### Từ vựng công việc · {level}")
    query = st.text_input("Tìm từ", placeholder="Nhập từ tiếng Anh hoặc nghĩa Việt...", key=f"workplace_vocab_search_{level}")
    words = list(WORKPLACE_VOCAB[level])
    words.extend((item["word"], item["ipa"], item["meaning"], item["example"]) for item in load_extended_vocabulary().get(level, []))
    if query.strip():
        needle = query.strip().casefold()
        words = [word for word in words if needle in " ".join(word).casefold()]
    st.caption(f"{len(words)} từ trong chặng này · Tổng chương trình có 144 từ và 24 cụm câu chủ lực")
    _render_speaking_vocabulary(words)
    st.markdown("#### Cụm câu chủ lực")
    phrase_rows = [(phrase, "", meaning, phrase) for phrase, meaning in data["phrases"]]
    _render_speaking_vocabulary(phrase_rows, height=330)
    for phrase, _ in data["phrases"]:
        st.text_input(f"Tự đặt câu với “{phrase}”", key=f"phrase_practice_{level}_{phrase}")
    st.warning("Mẹo: bấm 🔊 Từ, nghe và nhại ba lần; sau đó bấm 🔊 Ví dụ rồi tự tạo một câu liên quan trực tiếp tới công việc của bạn.")


def _render_speaking_vocabulary(words, height=680):
    cards = []
    for word, ipa, meaning, example in words:
        safe_word = html.escape(word, quote=True)
        safe_example = html.escape(example, quote=True)
        cards.append(
            f"<article class='card'><div><span class='word'>{safe_word}</span> "
            f"<span class='ipa'>{html.escape(ipa)}</span></div>"
            f"<div class='meaning'><b>Nghĩa:</b> {html.escape(meaning)}</div>"
            f"<div class='example'><b>Ví dụ:</b> {safe_example}</div>"
            f"<div class='actions'><button data-speak='{safe_word}'>🔊 Từ</button>"
            f"<button data-speak='{safe_example}'>🔊 Ví dụ</button></div></article>"
        )
    content = "".join(cards) or "<p>Không tìm thấy từ phù hợp.</p>"
    components.html(
        f"""<!doctype html><html><head><style>
        *{{box-sizing:border-box}} body{{margin:0;font-family:Arial,sans-serif;color:#172033}}
        .card{{padding:14px 16px;border:1px solid #e5e7eb;border-radius:14px;margin:8px 2px;background:#fff}}
        .word{{font-size:22px;font-weight:800;color:#1d4ed8}} .ipa{{color:#7c3aed}}
        .meaning,.example{{margin-top:6px;line-height:1.45}} .example{{color:#475569}}
        .actions{{display:flex;gap:8px;margin-top:10px}} button{{border:0;border-radius:9px;padding:7px 12px;
        background:#dbeafe;color:#1e40af;font-weight:700;cursor:pointer}} button:hover{{background:#bfdbfe}}
        button.playing{{background:#2563eb;color:white}}
        </style></head><body>{content}<script>
        function speak(text, button){{
          window.speechSynthesis.cancel();
          document.querySelectorAll('button').forEach(b => b.classList.remove('playing'));
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = 'en-US'; utterance.rate = 0.82; utterance.pitch = 1;
          const voices = window.speechSynthesis.getVoices();
          const preferred = voices.find(v => v.lang === 'en-US') || voices.find(v => v.lang.startsWith('en'));
          if (preferred) utterance.voice = preferred;
          button.classList.add('playing'); utterance.onend = () => button.classList.remove('playing');
          utterance.onerror = () => button.classList.remove('playing'); window.speechSynthesis.speak(utterance);
        }}
        document.querySelectorAll('[data-speak]').forEach(button => button.addEventListener('click', () => speak(button.dataset.speak, button)));
        </script></body></html>""",
        height=height, scrolling=True,
    )


def _render_grammar_map(level):
    st.markdown(f"### Sơ đồ tư duy ngữ pháp · {level}")
    points = GRAMMAR_MAPS[level]
    nodes = "".join(
        f"<div style='padding:13px;background:#fff;border:1px solid #c4b5fd;border-radius:13px;text-align:center'>"
        f"<b style='color:#6d28d9'>{name}</b><br><span style='font-size:13px'>{formula}</span></div>"
        for name, formula, _, _, _ in points
    )
    st.markdown(
        f"<div style='padding:21px;border-radius:18px;background:linear-gradient(135deg,#faf5ff,#eff6ff);border:1px solid #ddd6fe'>"
        f"<div style='text-align:center;font-size:24px;font-weight:850;color:#6d28d9'>NGỮ PHÁP {level.split(' · ')[0]}</div>"
        f"<div style='text-align:center;color:#8b5cf6;font-size:20px;margin:5px'>↓ ba cấu trúc trọng tâm ↓</div>"
        f"<div style='display:grid;grid-template-columns:repeat(3,minmax(150px,1fr));gap:10px'>{nodes}</div></div>",
        unsafe_allow_html=True,
    )
    for name, formula, use, example, mistake in points:
        with st.expander(f"🧩 {name}"):
            st.markdown(f"**Công thức:** `{formula}`")
            st.markdown(f"**Khi dùng:** {use}")
            st.success(f"Ví dụ: {example}")
            st.warning(f"Lỗi cần tránh: {mistake}")
            st.text_input("Tự đặt một câu", key=f"grammar_example_{level}_{name}")


def _render_four_skills(level, data):
    st.markdown("### Một nhiệm vụ - luyện đủ 4 kỹ năng")
    st.markdown(f"**Tình huống trung tâm:** {data['work']}")
    listen, speak, read, write = st.columns(4)
    listen.info("**🎧 NGHE**\n\nNghe một mẫu phù hợp cấp độ hai lượt; lượt đầu không nhìn transcript.")
    speak.info("**🎙️ NÓI**\n\nGhi âm 60–120 giây; ưu tiên rõ ý trước khi sửa ngữ pháp.")
    read.info("**📄 ĐỌC**\n\nĐọc email/đoạn ngắn; gạch mục tiêu, hành động và thời hạn.")
    write.info("**⌨️ VIẾT**\n\nViết phản hồi theo khung: mục đích → chi tiết → bước tiếp theo.")
    st.text_area("Bài viết thực hành", placeholder="Write your response here...", key=f"workplace_writing_{level}", height=160)
    st.checkbox("Tôi đã đọc bài viết thành tiếng", key=f"workplace_read_aloud_{level}")
    st.checkbox("Tôi đã sửa một lỗi phát âm và một lỗi viết", key=f"workplace_review_{level}")


def _render_week_plan(level, data):
    st.markdown("### Chu kỳ học 7 ngày")
    plan = [
        ("Thứ 2", "Phát âm + cụm câu", "20' nghe, 20' nhại âm, 20' flashcard"),
        ("Thứ 3", "Ngữ pháp trong ngữ cảnh", "Học 1 cấu trúc và tự đặt 8 câu"),
        ("Thứ 4", "Đọc công việc", "Đọc email/báo cáo ngắn và tóm tắt 3 ý"),
        ("Thứ 5", "Viết", "Viết một email hoặc cập nhật công việc"),
        ("Thứ 6", "Nói tình huống", "Ghi âm nhiệm vụ công việc của chặng"),
        ("Thứ 7", "Mô phỏng", "Kết hợp nghe - nói - đọc - viết trong một tình huống"),
        ("Chủ nhật", "Ôn & đo tiến bộ", "Làm lại lỗi sai, tự nhớ lại không nhìn tài liệu"),
    ]
    for day, focus, task in plan:
        st.markdown(f"**{day} · {focus}** — {task}")
    st.progress(0, text=f"Mục tiêu tuần: hoàn thành 1 mô-đun trong {len(data['modules'])} mô-đun của {level}")


def render_quick_training():
    left, right = st.columns(2)
    with left:
        topic = st.selectbox("Chủ đề", list(LESSONS), key="english_topic")
    with right:
        level = st.selectbox("Trình độ", list(LESSONS[topic]), key="english_level")
    lesson = LESSONS[topic][level]
    st.info(f"🎯 Mục tiêu: {lesson['goal']}")
    vocab_tab, dialogue_tab, quiz_tab, speaking_tab = st.tabs(["📚 Từ vựng", "💬 Hội thoại", "✅ Quiz", "🎙️ Luyện nói"])

    with vocab_tab:
        for phrase, meaning, example in lesson["words"]:
            with st.expander(phrase):
                st.markdown(f"**Nghĩa:** {meaning}")
                st.markdown(f"**Ví dụ:** {example}")
    with dialogue_tab:
        for speaker, sentence in lesson["dialogue"]:
            st.markdown(f"{'👩‍🏫' if speaker == 'Teacher' else '🎓'} **{speaker}:** {sentence}")
        st.caption("Đọc thành tiếng hai lần, sau đó đổi vai và đọc lại.")
    lesson_key = f"{topic}_{level}"
    with quiz_tab:
        with st.form(f"english_quiz_{lesson_key}"):
            answers = [st.radio(f"{i + 1}. {q}", options, index=None, key=f"english_{lesson_key}_{i}")
                       for i, (q, options, _) in enumerate(lesson["quiz"])]
            submitted = st.form_submit_button("Chấm điểm")
        if submitted:
            if any(answer is None for answer in answers):
                st.warning("Bạn hãy trả lời đủ các câu trước khi chấm điểm.")
            else:
                score = sum(answer == options[correct] for answer, (_, options, correct) in zip(answers, lesson["quiz"]))
                st.session_state[f"english_score_{lesson_key}"] = score
                message = "Xuất sắc!" if score == len(lesson["quiz"]) else "Kết quả"
                st.success(f"{message} Bạn đúng {score}/{len(lesson['quiz'])} câu.")
        score = st.session_state.get(f"english_score_{lesson_key}")
        if score is not None:
            st.progress(score / len(lesson["quiz"]), text=f"Kết quả gần nhất: {score}/{len(lesson['quiz'])}")
    with speaking_tab:
        st.markdown(f"**Tình huống:** {lesson['speaking']}")
        st.text_area("Soạn câu trả lời", placeholder="Viết phần bạn sẽ nói bằng tiếng Anh...",
                     key=f"english_speaking_{lesson_key}", height=140)
        st.caption("Sau khi viết, hãy đọc thành tiếng trong 30–60 giây và cố gắng không nhìn lại.")
