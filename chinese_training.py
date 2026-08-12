import random
import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


TERABOX_URL = "https://1024terabox.com/s/1blLvuQOMDPTNE-DLJu73YQ"
GRAMMAR_DRIVE_URL = "https://drive.google.com/drive/folders/1qDNrvYbB3ekCyFBZ9-sEq6YlKdBpoif5"
EXTRA_DRIVE_URL = "https://drive.google.com/drive/folders/1tGJ5HKK6un3XlVX5wFKI3jziBPre4xHt"
FULL_VOCAB_PATH = Path(__file__).with_name("hsk_vocab_full.json")
MATERIALS_PATH = Path(__file__).with_name("chinese_materials_catalog.json")
HSK_BOOKS = {
    "HSK1": {"id": "1sfJfPD5TGaBsRy0nVbidfW_J5Z2nxYzD", "pages": 143},
    "HSK2": {"id": "1Ai291o1SRtTJgcH86h0Rmgd8xQiqNO6M", "pages": 145},
    "HSK3": {"id": "1WrylZQ2wBjAaSphfELBA-deflitf4F2E", "pages": 207},
}

PDF_LIBRARY = {
    "Học 50 bộ thủ chữ Hán": {
        "file_id": "1P09QWOLtlUDMOCTzCRMTeHe306l93HNr",
        "level": "HSK1-HSK3",
        "summary": "Nhận diện 50 bộ thủ thông dụng để ghi nhớ mặt chữ và đoán nhóm nghĩa.",
        "focus": ["Nhìn hình dạng bộ thủ", "Ghi nhớ nghĩa gốc", "Tìm bộ thủ trong từ đang học"],
    },
    "Tập viết các nét cơ bản": {
        "file_id": "1Ndv7g7GYyqSoFy-4OhNqOo8G1-Cm3HLo",
        "level": "HSK1",
        "summary": "Luyện các nét nền tảng và quy tắc thứ tự nét trước khi viết chữ hoàn chỉnh.",
        "focus": ["Đọc tên nét", "Tô theo mẫu", "Tự viết lại không nhìn mẫu"],
    },
    "Vở kẻ ô luyện viết chữ Hán": {
        "file_id": "1j0utSAFYzZ8EYSbOg-9Z3CR4pN4hg2AC",
        "level": "HSK1-HSK3",
        "summary": "Mẫu ô luyện viết để cân đối tỷ lệ và vị trí các bộ phận trong chữ Hán.",
        "focus": ["Quan sát tâm ô", "Giữ đúng tỷ lệ trái-phải", "Viết mỗi chữ 5 lần"],
    },
    "Tổng hợp ngữ pháp": {
        "file_id": "1pi74nE7VhuSWKUxnFld0o7P9VfThyMcA",
        "level": "HSK2-HSK6",
        "summary": "Tài liệu tra cứu tổng hợp. Nên dùng sau mỗi bài để hệ thống lại cấu trúc và ví dụ.",
        "focus": ["Đọc phần công thức", "Tự đặt 2 câu", "So sánh với ví dụ trong tài liệu"],
    },
    "Câu chữ 被": {
        "file_id": "1-ACfN7FxRYMaSGC7tvCN5xu_1KU6vlED",
        "level": "HSK4-HSK5",
        "summary": "Câu bị động với 被: vị trí thành phần, điều kiện sử dụng và lỗi thường gặp.",
        "focus": ["Xác định chủ thể chịu tác động", "Đặt 被 trước tác nhân", "Giữ kết quả sau động từ"],
    },
    "Cấu trúc 是...的": {
        "file_id": "1W61uACPIQuekyDid5An33BpnmJGDilGJ",
        "level": "HSK2-HSK3",
        "summary": "Nhấn mạnh thời gian, địa điểm, cách thức hoặc người thực hiện một hành động đã xảy ra.",
        "focus": ["Tìm thông tin cần nhấn mạnh", "Đặt sau 是", "Đặt 的 ở cuối cụm"],
    },
    "Động từ ly hợp": {
        "file_id": "1JPAhQ8FpkcgvzmVgvRik0trEZxy8laaC",
        "level": "HSK3-HSK5",
        "summary": "Cách tách động từ ly hợp khi thêm số lượng, thời lượng, bổ ngữ và trợ từ động thái.",
        "focus": ["Nhận diện phần động từ và tân ngữ", "Chèn thành phần vào giữa", "Tránh thêm tân ngữ lần hai"],
    },
}


VOCABULARY = {
    "HSK1": [
        ("你好", "nǐ hǎo", "xin chào", "你好！很高兴认识你。", "Xin chào! Rất vui được gặp bạn."),
        ("谢谢", "xièxie", "cảm ơn", "谢谢你的帮助。", "Cảm ơn sự giúp đỡ của bạn."),
        ("学习", "xuéxí", "học tập", "我每天学习汉语。", "Tôi học tiếng Trung mỗi ngày."),
        ("朋友", "péngyou", "bạn bè", "她是我的好朋友。", "Cô ấy là bạn tốt của tôi."),
        ("老师", "lǎoshī", "giáo viên", "王老师教我们汉语。", "Giáo viên Vương dạy chúng tôi tiếng Trung."),
        ("学校", "xuéxiào", "trường học", "我的学校很大。", "Trường của tôi rất lớn."),
        ("喜欢", "xǐhuan", "thích", "我喜欢喝茶。", "Tôi thích uống trà."),
        ("今天", "jīntiān", "hôm nay", "今天天气很好。", "Hôm nay thời tiết rất đẹp."),
        ("吃", "chī", "ăn", "我们一起吃米饭吧。", "Chúng ta cùng ăn cơm nhé."),
        ("家", "jiā", "nhà, gia đình", "我家有三个人。", "Gia đình tôi có ba người."),
    ],
    "HSK2": [
        ("开始", "kāishǐ", "bắt đầu", "电影八点开始。", "Bộ phim bắt đầu lúc tám giờ."),
        ("希望", "xīwàng", "hy vọng", "我希望明天不下雨。", "Tôi hy vọng ngày mai không mưa."),
        ("问题", "wèntí", "vấn đề, câu hỏi", "这个问题不难。", "Câu hỏi này không khó."),
        ("准备", "zhǔnbèi", "chuẩn bị", "我在准备明天的考试。", "Tôi đang chuẩn bị cho bài thi ngày mai."),
        ("旅游", "lǚyóu", "du lịch", "暑假我们去北京旅游。", "Nghỉ hè chúng tôi đi Bắc Kinh du lịch."),
        ("因为", "yīnwèi", "bởi vì", "因为下雨，所以我没出去。", "Vì trời mưa nên tôi không ra ngoài."),
        ("运动", "yùndòng", "vận động", "每天运动对身体很好。", "Vận động mỗi ngày rất tốt cho cơ thể."),
        ("已经", "yǐjīng", "đã", "我已经做完作业了。", "Tôi đã làm xong bài tập rồi."),
        ("一起", "yìqǐ", "cùng nhau", "周末我们一起去看电影。", "Cuối tuần chúng ta cùng đi xem phim."),
        ("告诉", "gàosu", "nói, cho biết", "请告诉我你的名字。", "Hãy cho tôi biết tên của bạn."),
    ],
    "HSK3": [
        ("影响", "yǐngxiǎng", "ảnh hưởng", "睡眠会影响学习效率。", "Giấc ngủ ảnh hưởng đến hiệu quả học tập."),
        ("习惯", "xíguàn", "thói quen", "早起是一个好习惯。", "Dậy sớm là một thói quen tốt."),
        ("环境", "huánjìng", "môi trường", "我们应该保护环境。", "Chúng ta nên bảo vệ môi trường."),
        ("选择", "xuǎnzé", "lựa chọn", "你可以选择坐地铁。", "Bạn có thể chọn đi tàu điện ngầm."),
        ("提高", "tígāo", "nâng cao", "阅读能提高汉语水平。", "Đọc sách có thể nâng cao trình độ tiếng Trung."),
        ("机会", "jīhuì", "cơ hội", "这是一次很好的机会。", "Đây là một cơ hội rất tốt."),
        ("认真", "rènzhēn", "nghiêm túc", "她学习得很认真。", "Cô ấy học rất nghiêm túc."),
        ("解决", "jiějué", "giải quyết", "我们一起解决这个问题。", "Chúng ta cùng giải quyết vấn đề này."),
        ("经验", "jīngyàn", "kinh nghiệm", "他有丰富的工作经验。", "Anh ấy có kinh nghiệm làm việc phong phú."),
        ("文化", "wénhuà", "văn hóa", "我对中国文化很感兴趣。", "Tôi rất hứng thú với văn hóa Trung Quốc."),
    ],
    "HSK4": [
        ("适应", "shìyìng", "thích nghi", "我慢慢适应了这里的生活。", "Tôi dần thích nghi với cuộc sống ở đây."),
        ("交流", "jiāoliú", "giao lưu, trao đổi", "学习语言需要多跟别人交流。", "Học ngôn ngữ cần giao tiếp nhiều với người khác."),
        ("坚持", "jiānchí", "kiên trì", "只要坚持，就会看到进步。", "Chỉ cần kiên trì sẽ thấy tiến bộ."),
        ("责任", "zérèn", "trách nhiệm", "每个人都应该对自己的选择负责。", "Mỗi người nên chịu trách nhiệm với lựa chọn của mình."),
        ("计划", "jìhuà", "kế hoạch", "我们正在计划一次旅行。", "Chúng tôi đang lên kế hoạch cho một chuyến đi."),
        ("结果", "jiéguǒ", "kết quả", "考试结果比我想的好。", "Kết quả thi tốt hơn tôi nghĩ."),
        ("理解", "lǐjiě", "hiểu", "谢谢你对我的理解。", "Cảm ơn bạn đã thấu hiểu tôi."),
        ("发展", "fāzhǎn", "phát triển", "这个城市发展得很快。", "Thành phố này phát triển rất nhanh."),
        ("建议", "jiànyì", "đề nghị", "医生建议我多休息。", "Bác sĩ khuyên tôi nghỉ ngơi nhiều hơn."),
        ("成功", "chénggōng", "thành công", "努力是成功的重要条件。", "Nỗ lực là điều kiện quan trọng của thành công."),
    ],
    "HSK5": [
        ("挑战", "tiǎozhàn", "thử thách", "这份工作对我来说是新的挑战。", "Công việc này là thử thách mới đối với tôi."),
        ("效率", "xiàolǜ", "hiệu suất", "合理安排时间能提高效率。", "Sắp xếp thời gian hợp lý có thể nâng cao hiệu suất."),
        ("独立", "dúlì", "độc lập", "大学生应该学会独立生活。", "Sinh viên nên học cách sống độc lập."),
        ("资源", "zīyuán", "tài nguyên", "我们要节约自然资源。", "Chúng ta cần tiết kiệm tài nguyên thiên nhiên."),
        ("趋势", "qūshì", "xu hướng", "网上学习已经成为一种趋势。", "Học trực tuyến đã trở thành một xu hướng."),
        ("贡献", "gòngxiàn", "cống hiến", "他为团队做出了很大贡献。", "Anh ấy đã đóng góp rất lớn cho đội."),
        ("改善", "gǎishàn", "cải thiện", "运动可以改善睡眠质量。", "Vận động có thể cải thiện chất lượng giấc ngủ."),
        ("观点", "guāndiǎn", "quan điểm", "我同意你的观点。", "Tôi đồng ý với quan điểm của bạn."),
        ("承担", "chéngdān", "đảm nhận, gánh vác", "他愿意承担更多责任。", "Anh ấy sẵn lòng đảm nhận thêm trách nhiệm."),
        ("珍惜", "zhēnxī", "trân trọng", "我们应该珍惜学习的机会。", "Chúng ta nên trân trọng cơ hội học tập."),
    ],
    "HSK6": [
        ("潜力", "qiánlì", "tiềm năng", "每个孩子都有巨大的潜力。", "Mỗi đứa trẻ đều có tiềm năng to lớn."),
        ("协调", "xiétiáo", "phối hợp", "经理负责协调各部门的工作。", "Quản lý chịu trách nhiệm phối hợp công việc các phòng ban."),
        ("缓解", "huǎnjiě", "giảm nhẹ", "运动有助于缓解压力。", "Vận động giúp giảm căng thẳng."),
        ("倡导", "chàngdǎo", "đề xướng", "政府倡导绿色出行。", "Chính phủ đề xướng giao thông xanh."),
        ("维持", "wéichí", "duy trì", "双方一直维持着良好的关系。", "Hai bên luôn duy trì quan hệ tốt đẹp."),
        ("局限", "júxiàn", "hạn chế", "我们不能把思考局限在一个角度。", "Không nên giới hạn suy nghĩ trong một góc nhìn."),
        ("衡量", "héngliáng", "đánh giá, đo lường", "金钱不是衡量成功的唯一标准。", "Tiền không phải tiêu chuẩn duy nhất đánh giá thành công."),
        ("忽略", "hūlüè", "bỏ qua", "不要忽略生活中的小细节。", "Đừng bỏ qua những chi tiết nhỏ trong cuộc sống."),
        ("实施", "shíshī", "thực hiện", "新计划将从下个月开始实施。", "Kế hoạch mới sẽ được thực hiện từ tháng sau."),
        ("突破", "tūpò", "đột phá", "研究团队取得了重大突破。", "Nhóm nghiên cứu đã đạt được đột phá lớn."),
    ],
}


STORIES = {
    "HSK1": {
        "title": "我的新朋友 - Người bạn mới của tôi",
        "sentences": [
            ("今天我去学校学习汉语。", "Jīntiān wǒ qù xuéxiào xuéxí Hànyǔ.", "Hôm nay tôi đến trường học tiếng Trung."),
            ("老师介绍了一位新同学。", "Lǎoshī jièshào le yí wèi xīn tóngxué.", "Giáo viên giới thiệu một bạn học mới."),
            ("她叫小美，她喜欢喝茶。", "Tā jiào Xiǎoměi, tā xǐhuan hē chá.", "Cô ấy tên Tiểu Mỹ và thích uống trà."),
            ("下课以后，我们一起吃饭。", "Xiàkè yǐhòu, wǒmen yìqǐ chīfàn.", "Sau giờ học, chúng tôi cùng ăn cơm."),
            ("现在她是我的好朋友。", "Xiànzài tā shì wǒ de hǎo péngyou.", "Bây giờ cô ấy là bạn tốt của tôi."),
        ],
    },
    "HSK2": {
        "title": "周末的计划 - Kế hoạch cuối tuần",
        "sentences": [
            ("这个周末我准备和朋友去旅游。", "Zhège zhōumò wǒ zhǔnbèi hé péngyou qù lǚyóu.", "Cuối tuần này tôi chuẩn bị đi du lịch với bạn."),
            ("我们已经买好火车票了。", "Wǒmen yǐjīng mǎi hǎo huǒchēpiào le.", "Chúng tôi đã mua xong vé tàu."),
            ("因为天气可能很冷，所以我要多带衣服。", "Yīnwèi tiānqì kěnéng hěn lěng, suǒyǐ wǒ yào duō dài yīfu.", "Vì trời có thể lạnh nên tôi sẽ mang thêm quần áo."),
            ("我希望这次旅行很有意思。", "Wǒ xīwàng zhè cì lǚxíng hěn yǒuyìsi.", "Tôi hy vọng chuyến đi này thú vị."),
        ],
    },
    "HSK3": {
        "title": "改变一个习惯 - Thay đổi một thói quen",
        "sentences": [
            ("以前我常常睡得很晚，早上没有精神。", "Yǐqián wǒ chángcháng shuì de hěn wǎn, zǎoshang méiyǒu jīngshen.", "Trước đây tôi thường ngủ muộn và buổi sáng không có tinh thần."),
            ("后来我决定改变这个习惯。", "Hòulái wǒ juédìng gǎibiàn zhège xíguàn.", "Sau đó tôi quyết định thay đổi thói quen này."),
            ("我每天晚上十一点以前睡觉，早上起来运动。", "Wǒ měitiān wǎnshang shíyī diǎn yǐqián shuìjiào, zǎoshang qǐlái yùndòng.", "Mỗi tối tôi ngủ trước 11 giờ và sáng dậy vận động."),
            ("一个月以后，我的学习效率提高了。", "Yí ge yuè yǐhòu, wǒ de xuéxí xiàolǜ tígāo le.", "Một tháng sau, hiệu quả học tập của tôi đã tăng."),
        ],
    },
    "HSK4": {
        "title": "适应新的城市 - Thích nghi với thành phố mới",
        "sentences": [
            ("毕业以后，我到一个陌生的城市工作。", "Bìyè yǐhòu, wǒ dào yí ge mòshēng de chéngshì gōngzuò.", "Sau khi tốt nghiệp, tôi đến một thành phố xa lạ làm việc."),
            ("刚开始，我不习惯这里的生活节奏。", "Gāng kāishǐ, wǒ bù xíguàn zhèlǐ de shēnghuó jiézòu.", "Lúc đầu tôi chưa quen nhịp sống nơi đây."),
            ("同事建议我参加周末的文化活动。", "Tóngshì jiànyì wǒ cānjiā zhōumò de wénhuà huódòng.", "Đồng nghiệp khuyên tôi tham gia hoạt động văn hóa cuối tuần."),
            ("通过和别人交流，我慢慢适应了新环境。", "Tōngguò hé biérén jiāoliú, wǒ mànmàn shìyìng le xīn huánjìng.", "Qua giao tiếp với người khác, tôi dần thích nghi với môi trường mới."),
        ],
    },
    "HSK5": {
        "title": "远程工作的选择 - Lựa chọn làm việc từ xa",
        "sentences": [
            ("近年来，远程工作逐渐成为一种趋势。", "Jìnnián lái, yuǎnchéng gōngzuò zhújiàn chéngwéi yì zhǒng qūshì.", "Những năm gần đây, làm việc từ xa dần trở thành một xu hướng."),
            ("它给员工带来自由，也对自我管理提出了挑战。", "Tā gěi yuángōng dàilái zìyóu, yě duì zìwǒ guǎnlǐ tíchū le tiǎozhàn.", "Nó mang lại tự do nhưng cũng đặt ra thách thức về tự quản lý."),
            ("合理安排时间能够提高效率，改善生活质量。", "Hélǐ ānpái shíjiān nénggòu tígāo xiàolǜ, gǎishàn shēnghuó zhìliàng.", "Sắp xếp thời gian hợp lý giúp tăng hiệu suất và cải thiện chất lượng sống."),
            ("不过，面对面交流仍然有不可替代的价值。", "Búguò, miànduìmiàn jiāoliú réngrán yǒu bùkě tìdài de jiàzhí.", "Tuy nhiên, giao tiếp trực tiếp vẫn có giá trị không thể thay thế."),
        ],
    },
    "HSK6": {
        "title": "衡量成功的标准 - Tiêu chuẩn đánh giá thành công",
        "sentences": [
            ("人们往往用收入和地位来衡量一个人的成功。", "Rénmen wǎngwǎng yòng shōurù hé dìwèi lái héngliáng yí ge rén de chénggōng.", "Người ta thường dùng thu nhập và địa vị để đánh giá thành công."),
            ("然而，这种标准忽略了幸福感和个人成长。", "Rán'ér, zhè zhǒng biāozhǔn hūlüè le xìngfúgǎn hé gèrén chéngzhǎng.", "Tuy nhiên, tiêu chuẩn này bỏ qua hạnh phúc và trưởng thành cá nhân."),
            ("真正的成功不应局限于外界的评价。", "Zhēnzhèng de chénggōng bù yīng júxiàn yú wàijiè de píngjià.", "Thành công thực sự không nên giới hạn trong đánh giá bên ngoài."),
            ("发挥自己的潜力并为社会作出贡献，同样值得珍惜。", "Fāhuī zìjǐ de qiánlì bìng wèi shèhuì zuòchū gòngxiàn, tóngyàng zhíde zhēnxī.", "Phát huy tiềm năng và đóng góp cho xã hội cũng đáng được trân trọng."),
        ],
    },
}


@st.cache_data
def _load_full_vocabulary():
    if not FULL_VOCAB_PATH.exists():
        return {}
    return json.loads(FULL_VOCAB_PATH.read_text(encoding="utf-8"))


@st.cache_data
def _load_materials():
    if not MATERIALS_PATH.exists():
        return []
    raw = json.loads(MATERIALS_PATH.read_text(encoding="utf-8"))
    unique = {}
    for item in raw.get("items", []):
        if item.get("type") == "folder":
            continue
        key = (item.get("name", "").casefold(), item.get("type", "file"))
        unique.setdefault(key, item)
    return list(unique.values())


def _dict_to_tuple(word):
    return (
        word["hanzi"], word["pinyin"], word["meaning"],
        word["example"], word["example_vi"], word.get("example_pinyin", ""),
    )


def _get_words(level, cumulative=False):
    full_data = _load_full_vocabulary()
    if level in full_data:
        levels = list(full_data)[:int(level[-1])] if cumulative else [level]
        return [_dict_to_tuple(word) for item in levels for word in full_data[item]]
    return VOCABULARY[level]


def _render_flashcards(level, words):
    key = f"zh_card_index_{level}"
    if key not in st.session_state:
        st.session_state[key] = 0
    index = st.session_state[key] % len(words)
    hanzi, pinyin, meaning, example, translation, *extra = words[index]
    example_pinyin = extra[0] if extra else ""

    st.markdown(
        f"<div style='text-align:center;padding:35px 15px;border:1px solid #ddd;border-radius:16px;'>"
        f"<div style='font-size:52px;font-weight:700'>{hanzi}</div>"
        f"<div style='font-size:22px;color:#d97706;margin:8px'>{pinyin}</div>"
        f"<div style='font-size:20px'>{meaning}</div></div>", unsafe_allow_html=True,
    )
    with st.expander("Xem ví dụ"):
        st.markdown(f"**{example}**")
        if example_pinyin:
            st.caption(example_pinyin)
        st.caption(translation)
    prev_col, random_col, next_col = st.columns(3)
    if prev_col.button("← Từ trước", use_container_width=True, key=f"zh_prev_{level}"):
        st.session_state[key] = (index - 1) % len(words)
        st.rerun()
    if random_col.button("🔀 Ngẫu nhiên", use_container_width=True, key=f"zh_random_{level}"):
        st.session_state[key] = random.randrange(len(words))
        st.rerun()
    if next_col.button("Từ tiếp →", use_container_width=True, key=f"zh_next_{level}"):
        st.session_state[key] = (index + 1) % len(words)
        st.rerun()
    st.progress((index + 1) / len(words), text=f"Thẻ {index + 1}/{len(words)}")


def _render_vocab_list(words):
    query = st.text_input("Tìm từ", placeholder="Nhập chữ Hán, pinyin hoặc nghĩa Việt...", key="zh_vocab_search")
    rows = []
    for word in words:
        h, p, m, e, t, *extra = word
        rows.append({
            "Hán tự": h, "Pinyin": p, "Nghĩa": m, "Ví dụ / câu ghi nhớ": e,
            "Pinyin ví dụ": extra[0] if extra else "", "Dịch ví dụ": t,
        })
    if query.strip():
        needle = query.strip().lower()
        rows = [row for row in rows if any(needle in str(value).lower() for value in row.values())]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_textbook(level):
    book = HSK_BOOKS.get(level)
    if not book:
        st.info("Sách HSK4-HSK6 hiện được lưu ở TeraBox và chưa có liên kết PDF nhúng ổn định.")
        st.link_button("Mở giáo trình trên TeraBox ↗", TERABOX_URL)
        return
    st.markdown(f"### Sách giáo khoa {level}")
    st.caption(f"Bản đầy đủ {book['pages']} trang. Có thể đọc ngay trong web hoặc mở toàn màn hình.")
    preview_url = f"https://drive.google.com/file/d/{book['id']}/preview"
    components.iframe(preview_url, height=760, scrolling=True)
    st.link_button("Mở sách toàn màn hình ↗", f"https://drive.google.com/file/d/{book['id']}/view")


def _material_levels(item):
    text = " ".join([item.get("name", ""), *item.get("path", [])]).upper()
    found = set(re.findall(r"HSK\s*([1-6])", text))
    for start, end in re.findall(r"(?:HSK\s*)?([1-6])\s*[-–]\s*([1-6])", text):
        found.update(str(number) for number in range(int(start), int(end) + 1))
    return {f"HSK{value}" for value in found}


def _render_material_library(level):
    materials = _load_materials()
    st.markdown("### Kho tài liệu HSK 1–6")
    st.caption(f"Đã lập chỉ mục {len(materials)} tài liệu từ Drive; PDF có thể đọc ngay trong web.")
    filter_col, type_col = st.columns(2)
    scope = filter_col.selectbox(
        "Phạm vi", [f"Gợi ý cho {level}", "Tất cả tài liệu", "Ngữ pháp", "Giáo trình", "Bài tập"],
        key="zh_material_scope",
    )
    kind = type_col.selectbox("Định dạng", ["Tất cả", "PDF", "File khác"], key="zh_material_type")
    query = st.text_input("Tìm tài liệu", placeholder="Ví dụ: HSK 4, ngữ pháp, Boya...", key="zh_material_search")

    filtered = materials
    if scope.startswith("Gợi ý"):
        filtered = [item for item in filtered if not _material_levels(item) or level in _material_levels(item)]
    elif scope != "Tất cả tài liệu":
        needle = scope.casefold()
        filtered = [item for item in filtered if needle in " ".join(item.get("path", []) + [item.get("name", "")]).casefold()]
    if kind == "PDF":
        filtered = [item for item in filtered if item.get("type") == "pdf"]
    elif kind == "File khác":
        filtered = [item for item in filtered if item.get("type") != "pdf"]
    if query.strip():
        needle = query.strip().casefold()
        filtered = [item for item in filtered if needle in " / ".join(item.get("path", [])).casefold()]

    st.caption(f"Tìm thấy {len(filtered)} tài liệu")
    if not filtered:
        st.info("Không có tài liệu khớp bộ lọc này.")
        return
    labels = [f"{item['name']}  ·  {' / '.join(item.get('path', [])[:-1])}" for item in filtered]
    selected = filtered[st.selectbox("Chọn tài liệu", range(len(labels)), format_func=labels.__getitem__, key="zh_material_selected")]
    st.markdown(f"**{selected['name']}**")
    st.caption(" › ".join(selected.get("path", [])))
    file_url = f"https://drive.google.com/file/d/{selected['id']}/view"
    if selected.get("type") == "pdf":
        components.iframe(f"https://drive.google.com/file/d/{selected['id']}/preview", height=760, scrolling=True)
    else:
        st.info("Định dạng này được mở bằng trình xem của Google Drive.")
    st.link_button("Mở toàn màn hình trên Drive ↗", file_url)


def _render_story(level):
    story = STORIES[level]
    st.markdown(f"### {story['title']}")
    show_pinyin = st.toggle("Hiện pinyin", value=True, key=f"zh_story_pinyin_{level}")
    show_translation = st.toggle("Hiện bản dịch", value=False, key=f"zh_story_translation_{level}")
    for index, (sentence, pinyin, translation) in enumerate(story["sentences"], 1):
        st.markdown(f"**{index}. {sentence}**")
        if show_pinyin:
            st.caption(pinyin)
        if show_translation:
            st.info(translation)
    st.text_area("Tự dịch lại câu chuyện", placeholder="Viết bản dịch của bạn trước khi bật đáp án...",
                 key=f"zh_story_answer_{level}", height=150)


def _render_pdf_library():
    st.markdown("### Thư viện ngữ pháp")
    st.caption("Đọc tài liệu ngay tại đây, không cần chuyển sang Google Drive.")
    topic = st.selectbox("Chọn chủ đề", list(PDF_LIBRARY), key="zh_pdf_topic")
    material = PDF_LIBRARY[topic]

    st.markdown(
        f"<div style='padding:16px 18px;border-radius:14px;background:#f7f3ff;"
        f"border-left:5px solid #7c3aed;margin:8px 0 14px'>"
        f"<div style='font-size:21px;font-weight:700'>{topic}</div>"
        f"<div style='color:#6b7280;margin:4px 0'>Phù hợp: {material['level']}</div>"
        f"<div>{material['summary']}</div></div>", unsafe_allow_html=True,
    )

    st.markdown("**Cách học nhanh:**")
    for index, step in enumerate(material["focus"], 1):
        st.markdown(f"{index}. {step}")

    preview_url = f"https://drive.google.com/file/d/{material['file_id']}/preview"
    components.iframe(preview_url, height=720, scrolling=True)
    st.link_button("Mở toàn màn hình ↗", f"https://drive.google.com/file/d/{material['file_id']}/view")


def _render_sources(level):
    st.markdown(f"### Giáo trình chuẩn {level}")
    st.info("Từ vựng, pinyin, ví dụ và bài đọc của cấp độ này đã được chuẩn hóa trong các tab bên cạnh.")
    st.markdown("**Tài liệu tham khảo thêm:** sách giáo khoa, sách bài tập, tập viết và file nghe trên TeraBox.")
    st.link_button("Mở kho giáo trình HSK trên TeraBox ↗", TERABOX_URL)
    st.caption("TeraBox chưa cung cấp liên kết nhúng ổn định cho từng PDF, nên nút này được giữ làm nguồn đối chiếu.")
    st.markdown("**Kho bổ sung:** bài tập, giáo trình Hán ngữ/Boya, ngữ pháp HSK1-HSK6 và tài liệu người mới học.")
    st.link_button("Mở kho tài liệu tiếng Trung bổ sung ↗", EXTRA_DRIVE_URL)


def render_chinese_training():
    st.subheader("Training tiếng Trung")
    st.caption("Học từ vựng và luyện đọc theo lộ trình HSK1-HSK6.")
    level = st.selectbox("Cấp độ", list(VOCABULARY), key="zh_level")
    cumulative = False
    if level in _load_full_vocabulary():
        scope = st.radio(
            "Phạm vi từ vựng", ["Từ mới riêng cấp", "Lũy kế đến cấp này"],
            horizontal=True, key="zh_vocab_scope",
        )
        cumulative = scope == "Lũy kế đến cấp này"
    words = _get_words(level, cumulative=cumulative)
    st.caption(f"Đang học {len(words)} từ")
    flash_tab, list_tab, story_tab, book_tab, materials_tab, grammar_tab, source_tab = st.tabs(
        ["🃏 Flashcard", "📋 Vocabulary List", "📖 Đọc & dịch", "📘 Sách đầy đủ", "🗂 Kho HSK1–6", "📕 Ngữ pháp PDF", "📚 Nguồn khác"]
    )
    with flash_tab:
        _render_flashcards(level, words)
    with list_tab:
        _render_vocab_list(words)
    with story_tab:
        _render_story(level)
    with book_tab:
        _render_textbook(level)
    with materials_tab:
        _render_material_library(level)
    with grammar_tab:
        _render_pdf_library()
    with source_tab:
        _render_sources(level)
