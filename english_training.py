import json
from pathlib import Path

import streamlit as st


CATALOG_PATH = Path(__file__).with_name("course_catalog_raw.json")


def _drive_link(file_id, is_folder=False):
    kind = "folders" if is_folder else "file/d"
    suffix = "" if is_folder else "/view"
    return f"https://drive.google.com/drive/{kind}/{file_id}{suffix}"


@st.cache_data
def load_course_catalog():
    if not CATALOG_PATH.exists():
        return []
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


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
    st.caption("Học theo khóa IELTS trên Drive hoặc luyện giao tiếp nhanh.")
    course_tab, quick_tab = st.tabs(["🎓 Khóa IELTS đầy đủ", "⚡ Luyện giao tiếp nhanh"])
    with course_tab:
        render_full_course()
    with quick_tab:
        render_quick_training()


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
