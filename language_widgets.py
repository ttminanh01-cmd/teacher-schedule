"""Helpers dùng chung giữa chinese_training.py và english_training.py."""

from datetime import date

import streamlit as st

_PROGRESS_KEY = "_training_progress_api"


def set_progress_api(progress):
    """Gọi 1 lần ở đầu render_english_training/render_chinese_training để các
    hàm con lấy được API tiến độ qua get_progress_api() mà không cần truyền
    tham số xuyên suốt qua nhiều tầng hàm lồng nhau."""
    st.session_state[_PROGRESS_KEY] = progress


def get_progress_api():
    return st.session_state.get(_PROGRESS_KEY)


def record_quiz_if_progress(ngon_ngu: str, ma_muc: str, score: int, total: int):
    """Ghi kết quả quiz vào sổ tiến độ nếu người dùng hiện tại đã đăng nhập
    hợp lệ; im lặng bỏ qua nếu chưa (vd. xem thử/chưa cấp quyền ghi)."""
    progress = get_progress_api()
    if progress is not None and progress.email:
        progress.submit_quiz(ngon_ngu, ma_muc, score, total)


def render_vocab_review(ngon_ngu: str, items: list, word_id, render_front, render_back, namespace: str):
    """Ôn từ vựng kiểu Leitner: ưu tiên từ đã đến hạn ôn lại, xen thêm từ chưa
    ôn lần nào; bấm Nhớ/Quên để ghi kết quả và tự tính lịch ôn tiếp theo.
    - `word_id(item) -> str`: khoá ổn định của từ (chữ Hán hoặc từ tiếng Anh).
    - `render_front(item)` / `render_back(item)`: tự vẽ mặt trước/sau bằng st.*.
    - `namespace`: tiền tố khoá session_state, cần riêng theo ngôn ngữ+cấp độ.
    """
    progress = get_progress_api()
    if progress is None or not progress.email:
        st.info("Đăng nhập bằng email được cấp quyền dùng khu vực training để bật chế độ ôn ngắt quãng có lưu tiến độ.")
        return
    if not items:
        st.info("Chưa có từ nào trong phạm vi đang chọn.")
        return

    state = progress.vocab_state(ngon_ngu)
    today = date.today()
    due, new, later = [], [], []
    for item in items:
        info = state.get(word_id(item))
        if info is None:
            new.append(item)
        elif not info["next_review"] or info["next_review"] <= today:
            due.append(item)
        else:
            later.append(item)
    queue = due + new
    st.caption(f"Đến hạn ôn: {len(due)} · Từ mới: {len(new)} · Đã lên lịch ôn sau: {len(later)}")
    if not queue:
        st.success("Không còn từ nào cần ôn trong phạm vi này hôm nay. Quay lại vào ngày mai hoặc đổi phạm vi/cấp độ.")
        return

    idx_key = f"{namespace}_review_idx"
    idx = st.session_state.get(idx_key, 0) % len(queue)
    item = queue[idx]
    wid = word_id(item)
    box = state.get(wid, {}).get("box", 1)

    render_front(item)
    is_new = wid not in state
    st.caption(f"Box {box}/5" + (" · Từ mới" if is_new else "") + f" · Còn {len(queue) - idx}/{len(queue)} từ trong lượt ôn")

    show_key = f"{namespace}_review_show_{idx}"
    if not st.session_state.get(show_key):
        if st.button("👁 Hiện đáp án", key=f"{namespace}_reveal_{idx}", use_container_width=True):
            st.session_state[show_key] = True
            st.rerun()
        return

    render_back(item)
    col_forget, col_know = st.columns(2)
    if col_forget.button("❌ Quên", key=f"{namespace}_forget_{idx}", use_container_width=True):
        progress.review_word(ngon_ngu, wid, False, box)
        st.session_state[idx_key] = idx + 1
        st.rerun()
    if col_know.button("✅ Nhớ", key=f"{namespace}_know_{idx}", use_container_width=True):
        progress.review_word(ngon_ngu, wid, True, box)
        st.session_state[idx_key] = idx + 1
        st.rerun()


def render_progress_summary(ngon_ngu: str):
    """Tóm tắt tiến độ: số từ theo từng box Leitner + các lần làm quiz gần nhất.
    Dùng chung cho cả 2 ngôn ngữ, hiển thị trong 1 expander gọn ở đầu trang."""
    progress = get_progress_api()
    if progress is None or not progress.email:
        return
    with st.expander("📊 Tiến độ học của tôi"):
        state = progress.vocab_state(ngon_ngu)
        if state:
            box_counts = {box: 0 for box in range(1, 6)}
            for info in state.values():
                box_counts[info["box"]] = box_counts.get(info["box"], 0) + 1
            st.caption(f"Đã ôn {len(state)} từ · Box 5 (thuộc chắc): {box_counts.get(5, 0)} từ")
            columns = st.columns(5)
            for box, column in zip(range(1, 6), columns):
                column.metric(f"Box {box}", box_counts.get(box, 0))
        else:
            st.caption("Chưa có từ nào được ôn theo chế độ ngắt quãng.")

        recent = progress.recent_quizzes(ngon_ngu)
        if not recent.empty:
            st.caption("Các lần làm quiz gần nhất")
            st.dataframe(recent, use_container_width=True, hide_index=True)


_FEMALE_VOICE_PATTERNS = {
    "zh": "xiaoxiao|xiaoyi|huihui|yaoyao|hanhan|ting.ting|meijia|lili|female|woman",
    "en": "samantha|zira|aria|jenny|ava|susan|hazel|female|woman",
}


def tts_speak_fn(lang: str, rate: float = 0.7) -> str:
    """Thân hàm JS `speak(text, button)` dùng speechSynthesis, ưu tiên giọng
    nữ theo `lang` ('zh' hoặc 'en'). `button` không bắt buộc — nếu truyền vào
    thì thêm hiệu ứng highlight nút đang phát. Nhúng thẳng vào <script> của
    components.html (mỗi lần gọi là 1 iframe riêng nên vẫn cần nhúng lại JS,
    nhưng chỉ có 1 nơi trong code Python định nghĩa nội dung này)."""
    voice_lang = "zh-CN" if lang == "zh" else "en-US"
    female = _FEMALE_VOICE_PATTERNS[lang]
    return (
        "function speak(text, button) {"
        "window.speechSynthesis.cancel();"
        "if (button) { document.querySelectorAll('button').forEach(b => b.classList.remove('playing')); }"
        "const utterance = new SpeechSynthesisUtterance(text);"
        f"utterance.lang = '{voice_lang}'; utterance.rate = {rate}; utterance.pitch = 1.05;"
        "const voices = window.speechSynthesis.getVoices();"
        f"const female = /{female}/i;"
        f"const preferred = voices.find(v => v.lang.startsWith('{lang}') && female.test(v.name))"
        f" || voices.find(v => v.lang === '{voice_lang}') || voices.find(v => v.lang.startsWith('{lang}'));"
        "if (preferred) utterance.voice = preferred;"
        "if (button) { button.classList.add('playing'); utterance.onend = () => button.classList.remove('playing');"
        " utterance.onerror = () => button.classList.remove('playing'); }"
        "window.speechSynthesis.speak(utterance);"
        "}"
    )


def render_resource_results(resources: list, level_ok, tag: str, query: str, no_more_msg: str):
    """Lọc + hiển thị danh sách tài nguyên (dùng chung cho kho tiếng Anh/Trung).
    `level_ok(item) -> bool`: bộ lọc cấp độ, do caller tự định nghĩa vì mỗi
    ngôn ngữ có kiểu widget chọn cấp độ khác nhau. `tag`/`query` là giá trị đã
    chọn từ widget của caller."""
    filtered = [item for item in resources if level_ok(item)]
    if tag != "Tất cả":
        filtered = [item for item in filtered if tag in item["tags"]]
    if query.strip():
        needle = query.strip().casefold()
        filtered = [item for item in filtered if needle in item["name"].casefold()]

    st.caption(f"Tìm thấy {len(filtered)} nguồn")
    for item in filtered[:40]:
        with st.expander(f"📚 {item['name']}"):
            st.markdown(" · ".join(f"`{t}`" for t in item["tags"]))
            if item["levels"]:
                st.caption("Gợi ý cấp độ: " + ", ".join(item["levels"]))
            st.link_button("Mở tài liệu gốc ↗", item["url"])
    if len(filtered) > 40:
        st.info(no_more_msg)
