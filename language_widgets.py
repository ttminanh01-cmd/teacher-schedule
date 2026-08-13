"""Helpers dùng chung giữa chinese_training.py và english_training.py."""

import streamlit as st

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
