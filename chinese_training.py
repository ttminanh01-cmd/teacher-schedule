import random
import json
import re
import html
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


TERABOX_URL = "https://1024terabox.com/s/1blLvuQOMDPTNE-DLJu73YQ"
GRAMMAR_DRIVE_URL = "https://drive.google.com/drive/folders/1qDNrvYbB3ekCyFBZ9-sEq6YlKdBpoif5"
EXTRA_DRIVE_URL = "https://drive.google.com/drive/folders/1tGJ5HKK6un3XlVX5wFKI3jziBPre4xHt"
CHINESE_STANDARD_URL = "https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/s5987/202103/t20210329_523304.html"
FULL_VOCAB_PATH = Path(__file__).with_name("hsk_vocab_full.json")
MATERIALS_PATH = Path(__file__).with_name("chinese_materials_catalog.json")
LANGUAGE_RESOURCES_PATH = Path(__file__).with_name("language_resources.json")
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

GRAMMAR_LESSONS = {
    "Tổng hợp ngữ pháp": {
        "formula": "Thời gian + Chủ ngữ + Trạng ngữ + Động từ + Tân ngữ",
        "use": "Khung câu nền tảng để sắp xếp thành phần; từ chỉ thời gian thường đứng đầu câu hoặc sau chủ ngữ.",
        "branches": [
            ("Trật tự câu", "Ai · khi nào · ở đâu · làm gì", "我今天在公司学习。", "Wǒ jīntiān zài gōngsī xuéxí.", "Hôm nay tôi học ở công ty."),
            ("Phủ định", "不: hiện tại/thói quen · 没: đã không", "我不喝咖啡。昨天我没去。", "Wǒ bù hē kāfēi. Zuótiān wǒ méi qù.", "Tôi không uống cà phê. Hôm qua tôi đã không đi."),
            ("Câu hỏi", "吗 · 呢 · từ để hỏi giữ nguyên vị trí", "你什么时候下班？", "Nǐ shénme shíhou xiàbān?", "Khi nào bạn tan làm?"),
            ("Trợ từ", "了: thay đổi/hoàn thành · 过: trải nghiệm · 着: trạng thái", "我学过汉语。", "Wǒ xuéguo Hànyǔ.", "Tôi từng học tiếng Trung."),
        ],
        "mistakes": ["Không đảo từ để hỏi lên đầu câu như tiếng Việt/Anh.", "Không dùng 不 cho một hành động đã không xảy ra trong quá khứ; thường dùng 没(有)."],
        "quiz": ("Chọn câu đúng cho ‘Hôm qua tôi không đi làm’", "我昨天没上班。", ["我昨天不上班。", "我昨天没上班。", "没我昨天上班。"]),
    },
    "Câu chữ 被": {
        "formula": "Chủ thể chịu tác động + 被 + tác nhân + động từ + kết quả/bổ ngữ",
        "use": "Dùng khi muốn nhấn mạnh đối tượng bị tác động hoặc kết quả của hành động; tác nhân có thể được lược bỏ.",
        "branches": [
            ("Đối tượng", "Đứng trước 被", "我的手机被他拿走了。", "Wǒ de shǒujī bèi tā názǒu le.", "Điện thoại của tôi bị anh ấy cầm đi."),
            ("Tác nhân", "Đứng sau 被; có thể bỏ", "问题被解决了。", "Wèntí bèi jiějué le.", "Vấn đề đã được giải quyết."),
            ("Hành động", "Thường cần kết quả/hướng/了", "文件被同事发错了。", "Wénjiàn bèi tóngshì fācuò le.", "Tài liệu bị đồng nghiệp gửi nhầm."),
            ("Ngữ cảnh", "Hay dùng khi có thay đổi hoặc ảnh hưởng", "会议被取消了。", "Huìyì bèi qǔxiāo le.", "Cuộc họp đã bị hủy."),
        ],
        "mistakes": ["Không nói câu thiếu kết quả như 我的手机被他拿; nên nói 拿走了.", "Không dùng 被 chỉ để dịch máy móc mọi câu bị động tiếng Việt."],
        "quiz": ("Điền từ: 会议 ___ 取消了。", "被", ["把", "被", "在"]),
    },
    "Cấu trúc 是...的": {
        "formula": "Chủ ngữ + 是 + thành phần cần nhấn mạnh + động từ + 的",
        "use": "Nhấn mạnh thời gian, địa điểm, cách thức hoặc người thực hiện của một việc đã xảy ra.",
        "branches": [
            ("Thời gian", "是 + thời gian + V + 的", "我是昨天到的。", "Wǒ shì zuótiān dào de.", "Tôi đến hôm qua."),
            ("Địa điểm", "是 + nơi chốn + V + 的", "我们是在北京认识的。", "Wǒmen shì zài Běijīng rènshi de.", "Chúng tôi quen nhau ở Bắc Kinh."),
            ("Cách thức", "是 + bằng cách nào + V + 的", "他是坐地铁来的。", "Tā shì zuò dìtiě lái de.", "Anh ấy đến bằng tàu điện ngầm."),
            ("Chủ thể", "是 + người + V + 的", "这封邮件是经理写的。", "Zhè fēng yóujiàn shì jīnglǐ xiě de.", "Email này do quản lý viết."),
        ],
        "mistakes": ["Không dùng để kể một hành động chưa xảy ra.", "Trong câu phủ định, đặt 不 sau 是: 不是...的."],
        "quiz": ("Điền từ: 我 ___ 坐飞机来的。", "是", ["把", "是", "被"]),
    },
    "Động từ ly hợp": {
        "formula": "Động từ + (了/过/số lượng/thời lượng) + tân tố",
        "use": "Một số động từ hai âm tiết thực chất là động từ + tân ngữ, nên phải tách khi thêm lượng, thời gian hoặc trợ từ.",
        "branches": [
            ("Trợ từ", "V + 了/过 + O", "我已经吃了饭。", "Wǒ yǐjīng chī le fàn.", "Tôi ăn cơm rồi."),
            ("Số lần", "V + số + lượng từ + O", "我们见过两次面。", "Wǒmen jiànguo liǎng cì miàn.", "Chúng tôi từng gặp nhau hai lần."),
            ("Thời lượng", "V + thời lượng + O", "他睡了八个小时觉。", "Tā shuì le bā ge xiǎoshí jiào.", "Anh ấy ngủ tám tiếng."),
            ("Định ngữ", "V + người sở hữu + O", "我帮了他的忙。", "Wǒ bāng le tā de máng.", "Tôi đã giúp anh ấy."),
        ],
        "mistakes": ["Không nói 见面了两次; nói 见了两次面.", "Không thêm tân ngữ lần hai sau động từ ly hợp; dùng 跟/和 + người + 见面."],
        "quiz": ("Chọn câu đúng cho ‘Tôi ngủ tám tiếng’", "我睡了八个小时觉。", ["我睡觉了八个小时。", "我睡了八个小时觉。", "我八个小时了睡觉。"]),
    },
}

CLASSIFIER_GROUPS = [
    ("👤", "Người", "个 · 位 · 名", "gè · wèi · míng", "个 dùng chung; 位 lịch sự; 名 dùng trong danh sách/chính thức", "一个学生 · 一位老师 · 三名医生"),
    ("📚", "Sách & tác phẩm", "本 · 册 · 部", "běn · cè · bù", "本 cho sách; 册 nhấn từng tập; 部 cho tác phẩm/phim", "一本书 · 两册词典 · 一部电影"),
    ("📄", "Mặt phẳng", "张 · 面 · 幅", "zhāng · miàn · fú", "Liên tưởng vật có thể trải ra như một mặt phẳng", "一张纸 · 两面镜子 · 一幅画"),
    ("🛣️", "Dài & mềm", "条 · 根 · 道", "tiáo · gēn · dào", "条 như một dải; 根 như một que/thân; 道 như một đường", "一条路 · 两根筷子 · 一道门"),
    ("🐾", "Động vật", "只 · 匹 · 头", "zhī · pǐ · tóu", "只 dùng rộng; 匹 cho ngựa; 头 cho gia súc lớn", "一只猫 · 两匹马 · 三头牛"),
    ("🚗", "Phương tiện", "辆 · 列 · 架", "liàng · liè · jià", "辆 xe bánh lốp; 列 đoàn tàu; 架 máy bay/máy móc", "一辆车 · 一列火车 · 两架飞机"),
    ("🔁", "Lần & lượt", "次 · 遍 · 趟", "cì · biàn · tàng", "次 đếm lần; 遍 nhấn trọn quá trình; 趟 nhấn chuyến đi", "一次机会 · 读两遍 · 去一趟北京"),
    ("👟", "Cặp & bộ", "双 · 对 · 套", "shuāng · duì · tào", "双 hai món giống nhau; 对 một đôi; 套 một bộ hoàn chỉnh", "一双鞋 · 一对夫妻 · 一套衣服"),
]

CLASSIFIER_QUIZ = [
    ("___ 老师 (một giáo viên - cách nói lịch sự)", "位", ["个", "位", "本"]),
    ("读两 ___ (đọc trọn vẹn hai lượt)", "遍", ["次", "遍", "趟"]),
    ("一 ___ 火车 (một đoàn tàu)", "列", ["辆", "列", "架"]),
    ("三 ___ 牛 (ba con bò)", "头", ["只", "匹", "头"]),
    ("一 ___ 纸 (một tờ giấy)", "张", ["张", "条", "本"]),
]

MATERIAL_LESSON_TEMPLATES = {
    "grammar": {
        "icon": "🧩", "label": "Ngữ pháp",
        "branches": ["Công thức", "Ngữ cảnh dùng", "Ví dụ đúng", "Lỗi thường gặp"],
        "steps": ["Đọc công thức và xác định vị trí từng thành phần", "So sánh câu đúng với một lỗi dễ mắc", "Tự đặt 3 câu: khẳng định, phủ định, nghi vấn"],
        "tips": ["Tô cùng màu cho các thành phần có cùng chức năng", "Đổi chủ ngữ/thời gian nhưng giữ nguyên khung câu", "Không học công thức mà thiếu ngữ cảnh"],
    },
    "textbook": {
        "icon": "📘", "label": "Giáo trình",
        "branches": ["Từ mới", "Hội thoại", "Điểm ngữ pháp", "Bài tập ứng dụng"],
        "steps": ["Xem trước từ mới trong 5 phút", "Đọc/nghe hội thoại hai lượt", "Tóm tắt bài bằng 3 câu của chính bạn"],
        "tips": ["Học theo một bài, không đọc lướt cả quyển", "Che bản dịch khi đọc lượt hai", "Đánh dấu từ cần chuyển sang flashcard"],
    },
    "exercise": {
        "icon": "✍️", "label": "Bài tập",
        "branches": ["Nhận dạng dạng bài", "Làm không xem đáp án", "Đối chiếu", "Sổ lỗi sai"],
        "steps": ["Đặt đồng hồ và tự làm một lượt", "Ghi lý do cho từng câu sai", "Làm lại câu sai sau 24 giờ"],
        "tips": ["Không chỉ chép đáp án đúng", "Gắn mỗi lỗi với một quy tắc", "Ôn lại theo chu kỳ 1-3-7 ngày"],
    },
    "vocabulary": {
        "icon": "🃏", "label": "Từ vựng",
        "branches": ["Hán tự", "Pinyin", "Nghĩa", "Câu ngữ cảnh"],
        "steps": ["Nhìn Hán tự và tự đọc trước", "Nhớ từ theo cụm, không nhớ từ đơn", "Viết một câu liên hệ bản thân"],
        "tips": ["Gom từ theo chủ đề", "Ôn hai chiều Hán-Việt và Việt-Hán", "Đọc thành tiếng để nhớ cả âm"],
    },
    "pronunciation": {
        "icon": "🎧", "label": "Phiên âm & nghe",
        "branches": ["Thanh mẫu", "Vận mẫu", "Thanh điệu", "Nhại âm"],
        "steps": ["Nghe một câu không nhìn chữ", "Nghe lại và đánh dấu thanh điệu", "Nhại sát tốc độ, thu âm và so sánh"],
        "tips": ["Luyện cặp âm dễ nhầm", "Giữ đường nét của thanh điệu trong cả câu", "Mỗi lượt chỉ sửa một lỗi phát âm"],
    },
    "radical": {
        "icon": "🀄", "label": "Bộ thủ & chữ Hán",
        "branches": ["Hình dạng", "Nghĩa gốc", "Vị trí trong chữ", "Họ từ liên quan"],
        "steps": ["Nhìn bộ và đoán trường nghĩa", "Tách chữ thành các thành phần", "Viết theo đúng thứ tự nét"],
        "tips": ["Gắn bộ thủ với một hình ảnh", "Học theo họ chữ có chung bộ", "Ưu tiên bộ xuất hiện trong từ đang học"],
    },
    "exam": {
        "icon": "⏱️", "label": "Đề luyện HSK",
        "branches": ["Canh thời gian", "Làm đề", "Phân loại lỗi", "Ôn điểm yếu"],
        "steps": ["Làm trong điều kiện giống thi thật", "Chấm điểm theo từng kỹ năng", "Lập danh sách 5 lỗi cần sửa"],
        "tips": ["Không dừng quá lâu ở một câu", "Phân biệt thiếu kiến thức và thiếu thời gian", "Làm lại đề sau một tuần"],
    },
    "reference": {
        "icon": "🗂️", "label": "Tài liệu tham khảo",
        "branches": ["Mục tiêu", "Ý chính", "Ví dụ", "Ứng dụng"],
        "steps": ["Chọn một phần nhỏ cần học", "Ghi lại 3 ý quan trọng", "Áp dụng ngay bằng một ví dụ của bạn"],
        "tips": ["Không đọc liên tục mà không ghi chú", "Biến tiêu đề thành câu hỏi", "Kết thúc bằng phần tự nhớ lại"],
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

CHINESE_READINGS = {
    "HSK1": {
        "title": "我的新朋友 · Người bạn mới của tôi",
        "paragraphs": [
            ("今天我去学校学习汉语。老师介绍了一位新同学。她叫小美，今年二十岁。她是越南人，也是学生。",
             "Jīntiān wǒ qù xuéxiào xuéxí Hànyǔ. Lǎoshī jièshào le yí wèi xīn tóngxué. Tā jiào Xiǎoměi, jīnnián èrshí suì. Tā shì Yuènán rén, yě shì xuésheng.",
             "Hôm nay tôi đến trường học tiếng Trung. Giáo viên giới thiệu một bạn học mới. Cô ấy tên Tiểu Mỹ, năm nay hai mươi tuổi. Cô ấy là người Việt Nam và cũng là sinh viên."),
            ("小美喜欢喝茶，我喜欢喝咖啡。下课以后，我们一起吃米饭、说汉语。现在她是我的好朋友。明天我们还一起学习。",
             "Xiǎoměi xǐhuan hē chá, wǒ xǐhuan hē kāfēi. Xiàkè yǐhòu, wǒmen yìqǐ chī mǐfàn, shuō Hànyǔ. Xiànzài tā shì wǒ de hǎo péngyou. Míngtiān wǒmen hái yìqǐ xuéxí.",
             "Tiểu Mỹ thích uống trà, còn tôi thích uống cà phê. Sau giờ học, chúng tôi cùng ăn cơm và nói tiếng Trung. Bây giờ cô ấy là bạn tốt của tôi. Ngày mai chúng tôi lại học cùng nhau."),
        ],
        "vocab": [("新同学", "xīn tóngxué", "bạn học mới"), ("下课以后", "xiàkè yǐhòu", "sau giờ học"), ("一起", "yìqǐ", "cùng nhau")],
        "questions": [("小美是哪国人？", ["中国人", "越南人", "美国人"], 1), ("下课以后，他们做什么？", ["一起吃饭、说汉语", "一起回家", "一起喝咖啡"], 0)],
        "task": "Dịch lại đoạn hai mà chưa bật bản dịch, sau đó viết 3 câu giới thiệu một người bạn.",
    },
    "HSK2": {
        "title": "周末的计划 · Kế hoạch cuối tuần",
        "paragraphs": [
            ("这个周末我准备和两个朋友去杭州旅游。我们已经买好火车票，也在网上找了一家不贵的宾馆。火车星期六早上七点出发，所以我们六点半要到车站。",
             "Zhège zhōumò wǒ zhǔnbèi hé liǎng ge péngyou qù Hángzhōu lǚyóu. Wǒmen yǐjīng mǎi hǎo huǒchēpiào, yě zài wǎngshàng zhǎo le yì jiā bú guì de bīnguǎn. Huǒchē xīngqīliù zǎoshang qī diǎn chūfā, suǒyǐ wǒmen liù diǎn bàn yào dào chēzhàn.",
             "Cuối tuần này tôi định đi Hàng Châu với hai người bạn. Chúng tôi đã mua vé tàu và cũng tìm được một khách sạn không đắt trên mạng. Tàu khởi hành lúc bảy giờ sáng thứ Bảy nên chúng tôi phải đến ga lúc sáu giờ rưỡi."),
            ("天气预报说周末可能下雨，我们会带雨伞和一些暖和的衣服。星期六下午我们想去西湖，星期天上午去买东西。如果时间够，我们还想吃当地的小吃。我希望这次旅行很有意思。",
             "Tiānqì yùbào shuō zhōumò kěnéng xiàyǔ, wǒmen huì dài yǔsǎn hé yìxiē nuǎnhuo de yīfu. Xīngqīliù xiàwǔ wǒmen xiǎng qù Xīhú, xīngqītiān shàngwǔ qù mǎi dōngxi. Rúguǒ shíjiān gòu, wǒmen hái xiǎng chī dāngdì de xiǎochī. Wǒ xīwàng zhè cì lǚxíng hěn yǒuyìsi.",
             "Dự báo thời tiết nói cuối tuần có thể mưa nên chúng tôi sẽ mang ô và một ít quần áo ấm. Chiều thứ Bảy chúng tôi muốn đi Tây Hồ, sáng Chủ nhật đi mua sắm. Nếu đủ thời gian, chúng tôi còn muốn ăn món ăn vặt địa phương. Tôi hy vọng chuyến đi này thú vị."),
        ],
        "vocab": [("出发", "chūfā", "khởi hành"), ("天气预报", "tiānqì yùbào", "dự báo thời tiết"), ("当地", "dāngdì", "địa phương")],
        "questions": [("他们几点到车站？", ["六点半", "七点", "七点半"], 0), ("为什么要带雨伞？", ["天气很热", "可能下雨", "要去买东西"], 1)],
        "task": "Tóm tắt lịch trình theo thứ tự thời gian và tự viết kế hoạch cuối tuần của bạn.",
    },
    "HSK3": {
        "title": "改变一个习惯 · Thay đổi một thói quen",
        "paragraphs": [
            ("以前我常常睡得很晚，因为晚上喜欢看手机。第二天早上我总是起不来，上课的时候也没有精神。有一次考试，我把一个很简单的问题看错了。老师告诉我，休息不好会影响学习效率。",
             "Yǐqián wǒ chángcháng shuì de hěn wǎn, yīnwèi wǎnshang xǐhuan kàn shǒujī. Dì-èr tiān zǎoshang wǒ zǒngshì qǐbulái, shàngkè de shíhou yě méiyǒu jīngshen. Yǒu yí cì kǎoshì, wǒ bǎ yí ge hěn jiǎndān de wèntí kàncuò le. Lǎoshī gàosu wǒ, xiūxi bù hǎo huì yǐngxiǎng xuéxí xiàolǜ.",
             "Trước đây tôi thường ngủ rất muộn vì buổi tối thích xem điện thoại. Sáng hôm sau tôi luôn không dậy nổi và khi lên lớp cũng không có tinh thần. Trong một lần thi, tôi đọc nhầm một câu hỏi rất đơn giản. Giáo viên nói với tôi rằng nghỉ ngơi không tốt sẽ ảnh hưởng hiệu quả học tập."),
            ("后来我决定改变这个习惯。我每天晚上十点半关掉手机，十一点以前睡觉，早上起来运动二十分钟。刚开始很不容易，但是我坚持了一个月。现在我上课更认真，做作业也更快了。我发现，小小的改变也能带来很好的结果。",
             "Hòulái wǒ juédìng gǎibiàn zhège xíguàn. Wǒ měitiān wǎnshang shí diǎn bàn guāndiào shǒujī, shíyī diǎn yǐqián shuìjiào, zǎoshang qǐlái yùndòng èrshí fēnzhōng. Gāng kāishǐ hěn bù róngyì, dànshì wǒ jiānchí le yí ge yuè. Xiànzài wǒ shàngkè gèng rènzhēn, zuò zuòyè yě gèng kuài le. Wǒ fāxiàn, xiǎoxiǎo de gǎibiàn yě néng dàilái hěn hǎo de jiéguǒ.",
             "Sau đó tôi quyết định thay đổi thói quen này. Mỗi tối lúc mười giờ rưỡi tôi tắt điện thoại, ngủ trước mười một giờ và sáng dậy vận động hai mươi phút. Ban đầu không dễ, nhưng tôi kiên trì một tháng. Bây giờ tôi học chăm chú hơn và làm bài tập cũng nhanh hơn. Tôi nhận ra thay đổi nhỏ cũng có thể đem lại kết quả tốt."),
        ],
        "vocab": [("看错", "kàncuò", "đọc/nhìn nhầm"), ("影响", "yǐngxiǎng", "ảnh hưởng"), ("坚持", "jiānchí", "kiên trì")],
        "questions": [("老师认为学习效率为什么不高？", ["题目太难", "休息不好", "老师讲得太快"], 1), ("改变以后有什么结果？", ["作业更多了", "不再运动", "学习更认真、更快"], 2)],
        "task": "Tóm tắt quan hệ nguyên nhân–thay đổi–kết quả trong 4 câu tiếng Việt.",
    },
    "HSK4": {
        "title": "适应新的城市 · Thích nghi với thành phố mới",
        "paragraphs": [
            ("大学毕业以后，我到南方一个陌生的城市工作。刚开始，我不习惯这里的天气和生活节奏，也听不懂一些当地人说的话。下班后，我常常一个人回家，虽然工作很忙，却觉得生活有点儿无聊。",
             "Dàxué bìyè yǐhòu, wǒ dào nánfāng yí ge mòshēng de chéngshì gōngzuò. Gāng kāishǐ, wǒ bù xíguàn zhèlǐ de tiānqì hé shēnghuó jiézòu, yě tīngbudǒng yìxiē dāngdì rén shuō de huà. Xiàbān hòu, wǒ chángcháng yí ge rén huí jiā, suīrán gōngzuò hěn máng, què juéde shēnghuó yǒudiǎnr wúliáo.",
             "Sau khi tốt nghiệp đại học, tôi đến làm việc tại một thành phố xa lạ ở miền Nam. Ban đầu tôi không quen thời tiết và nhịp sống ở đây, cũng không hiểu một số cách nói của người địa phương. Sau giờ làm tôi thường về nhà một mình; dù công việc rất bận, tôi vẫn thấy cuộc sống hơi buồn tẻ."),
            ("一位同事建议我参加周末的文化活动。第一次去的时候，我认识了几个兴趣相同的朋友。我们一起参观博物馆、练习摄影，有时也去附近的小城市旅行。通过和别人交流，我不但了解了当地文化，而且慢慢找到了自己的生活方式。半年后，这座城市已经让我有了家的感觉。",
             "Yí wèi tóngshì jiànyì wǒ cānjiā zhōumò de wénhuà huódòng. Dì-yí cì qù de shíhou, wǒ rènshi le jǐ ge xìngqù xiāngtóng de péngyou. Wǒmen yìqǐ cānguān bówùguǎn, liànxí shèyǐng, yǒushí yě qù fùjìn de xiǎo chéngshì lǚxíng. Tōngguò hé biérén jiāoliú, wǒ búdàn liǎojiě le dāngdì wénhuà, érqiě mànmàn zhǎodào le zìjǐ de shēnghuó fāngshì. Bàn nián hòu, zhè zuò chéngshì yǐjīng ràng wǒ yǒu le jiā de gǎnjué.",
             "Một đồng nghiệp khuyên tôi tham gia hoạt động văn hóa cuối tuần. Lần đầu đi, tôi quen vài người bạn có cùng sở thích. Chúng tôi cùng tham quan bảo tàng, luyện chụp ảnh và đôi khi du lịch đến các thành phố nhỏ gần đó. Qua giao lưu, tôi không chỉ hiểu văn hóa địa phương mà còn dần tìm được cách sống của mình. Sau nửa năm, thành phố này đã cho tôi cảm giác như ở nhà."),
        ],
        "vocab": [("生活节奏", "shēnghuó jiézòu", "nhịp sống"), ("不但……而且……", "búdàn... érqiě...", "không những… mà còn…"), ("适应", "shìyìng", "thích nghi")],
        "questions": [("刚到新城市时，他有什么困难？", ["没有工作", "不适应环境并感到无聊", "不会坐地铁"], 1), ("什么帮助他适应了城市？", ["参加活动并与人交流", "换了一份工作", "每天在家休息"], 0)],
        "task": "Dịch đoạn hai và chỉ ra cấu trúc 不但……而且…… trong bản dịch.",
    },
    "HSK5": {
        "title": "远程工作的选择 · Lựa chọn làm việc từ xa",
        "paragraphs": [
            ("近年来，远程工作逐渐成为一种趋势。对员工来说，它减少了上下班所花的时间，也让人可以根据自己的情况安排工作。一些调查发现，安静的环境和灵活的时间有助于提高效率，特别是对于需要长时间集中注意力的任务。公司也能因此招聘不同地区的人才，并减少办公室成本。",
             "Jìnnián lái, yuǎnchéng gōngzuò zhújiàn chéngwéi yì zhǒng qūshì. Duì yuángōng lái shuō, tā jiǎnshǎo le shàngxiàbān suǒ huā de shíjiān, yě ràng rén kěyǐ gēnjù zìjǐ de qíngkuàng ānpái gōngzuò. Yìxiē diàochá fāxiàn, ānjìng de huánjìng hé línghuó de shíjiān yǒuzhùyú tígāo xiàolǜ, tèbié shì duìyú xūyào cháng shíjiān jízhōng zhùyìlì de rènwu. Gōngsī yě néng yīncǐ zhāopìn bùtóng dìqū de réncái, bìng jiǎnshǎo bàngōngshì chéngběn.",
             "Những năm gần đây, làm việc từ xa dần trở thành một xu hướng. Với nhân viên, nó giảm thời gian đi lại và cho phép sắp xếp công việc theo hoàn cảnh cá nhân. Một số khảo sát nhận thấy môi trường yên tĩnh và thời gian linh hoạt giúp nâng cao hiệu suất, nhất là với nhiệm vụ cần tập trung lâu. Công ty cũng có thể tuyển nhân tài ở nhiều khu vực và giảm chi phí văn phòng."),
            ("不过，远程工作并不适合所有人。缺少面对面的交流可能影响团队关系，新员工也比较难了解公司的工作方式。此外，如果工作和生活之间没有清楚的界限，有些人反而会工作更长时间。因此，与其在办公室和远程工作之间只选择一种，不如根据任务和员工的需要建立更灵活的制度。真正重要的不是在哪里工作，而是团队能否保持有效的沟通和明确的责任。",
             "Búguò, yuǎnchéng gōngzuò bìng bù shìhé suǒyǒu rén. Quēshǎo miànduìmiàn de jiāoliú kěnéng yǐngxiǎng tuánduì guānxì, xīn yuángōng yě bǐjiào nán liǎojiě gōngsī de gōngzuò fāngshì. Cǐwài, rúguǒ gōngzuò hé shēnghuó zhījiān méiyǒu qīngchu de jièxiàn, yǒuxiē rén fǎn'ér huì gōngzuò gèng cháng shíjiān. Yīncǐ, yǔqí zài bàngōngshì hé yuǎnchéng gōngzuò zhījiān zhǐ xuǎnzé yì zhǒng, bùrú gēnjù rènwu hé yuángōng de xūyào jiànlì gèng línghuó de zhìdù. Zhēnzhèng zhòngyào de bú shì zài nǎlǐ gōngzuò, ér shì tuánduì néngfǒu bǎochí yǒuxiào de gōutōng hé míngquè de zérèn.",
             "Tuy nhiên, làm việc từ xa không phù hợp với tất cả mọi người. Thiếu giao tiếp trực tiếp có thể ảnh hưởng quan hệ trong nhóm và nhân viên mới cũng khó hiểu cách làm việc của công ty. Ngoài ra, nếu không có ranh giới rõ ràng giữa công việc và cuộc sống, một số người lại làm lâu hơn. Vì vậy, thay vì chỉ chọn văn phòng hoặc từ xa, nên xây dựng chế độ linh hoạt theo nhiệm vụ và nhu cầu nhân viên. Điều thực sự quan trọng không phải nơi làm việc mà là nhóm có duy trì giao tiếp hiệu quả và trách nhiệm rõ ràng hay không."),
        ],
        "vocab": [("灵活", "línghuó", "linh hoạt"), ("界限", "jièxiàn", "ranh giới"), ("与其……不如……", "yǔqí... bùrú...", "thay vì… thì nên…")],
        "questions": [("远程工作的好处不包括什么？", ["减少通勤时间", "招聘更多地区的人才", "让所有员工关系更好"], 2), ("作者支持哪种办法？", ["完全远程", "完全回办公室", "根据需要采用灵活制度"], 2)],
        "task": "Lập bảng hai cột lợi ích–hạn chế, rồi tóm tắt quan điểm tác giả bằng 4–5 câu.",
    },
    "HSK6": {
        "title": "衡量成功的标准 · Tiêu chuẩn đánh giá thành công",
        "paragraphs": [
            ("在现代社会，人们往往用收入、职位和社会影响力来衡量一个人的成功。这些标准容易比较，也能在一定程度上反映个人取得的成果。然而，一旦把它们当成唯一答案，我们就可能忽略幸福感、健康、关系以及个人成长。一个人在别人眼中十分成功，却未必对自己的生活感到满意。",
             "Zài xiàndài shèhuì, rénmen wǎngwǎng yòng shōurù, zhíwèi hé shèhuì yǐngxiǎnglì lái héngliáng yí ge rén de chénggōng. Zhèxiē biāozhǔn róngyì bǐjiào, yě néng zài yídìng chéngdù shàng fǎnyìng gèrén qǔdé de chéngguǒ. Rán'ér, yídàn bǎ tāmen dàngchéng wéiyī dá'àn, wǒmen jiù kěnéng hūlüè xìngfúgǎn, jiànkāng, guānxì yǐjí gèrén chéngzhǎng. Yí ge rén zài biérén yǎnzhōng shífēn chénggōng, què wèibì duì zìjǐ de shēnghuó gǎndào mǎnyì.",
             "Trong xã hội hiện đại, người ta thường dùng thu nhập, chức vụ và ảnh hưởng xã hội để đo thành công. Các tiêu chuẩn này dễ so sánh và phần nào phản ánh thành quả cá nhân. Tuy nhiên, khi coi chúng là đáp án duy nhất, ta có thể bỏ qua hạnh phúc, sức khỏe, các mối quan hệ và sự trưởng thành. Một người rất thành công trong mắt người khác chưa chắc hài lòng với cuộc sống của mình."),
            ("真正的问题并不是物质成就是否重要，而是谁有权定义成功。如果一个人不断追求外界认可的目标，却很少思考这些目标是否符合自己的价值观，那么即使达到了目的，也可能感到空虚。相反，有人选择收入普通但有意义的工作，愿意花时间陪伴家人或为社会作出贡献，这同样可以被视为成功。",
             "Zhēnzhèng de wèntí bìng bú shì wùzhì chéngjiù shìfǒu zhòngyào, ér shì shéi yǒu quán dìngyì chénggōng. Rúguǒ yí ge rén búduàn zhuīqiú wàijiè rènkě de mùbiāo, què hěn shǎo sīkǎo zhèxiē mùbiāo shìfǒu fúhé zìjǐ de jiàzhíguān, nàme jíshǐ dádào le mùdì, yě kěnéng gǎndào kōngxū. Xiāngfǎn, yǒurén xuǎnzé shōurù pǔtōng dàn yǒuyìyì de gōngzuò, yuànyì huā shíjiān péibàn jiārén huò wèi shèhuì zuòchū gòngxiàn, zhè tóngyàng kěyǐ bèi shìwéi chénggōng.",
             "Vấn đề thật sự không phải thành tựu vật chất có quan trọng hay không mà là ai có quyền định nghĩa thành công. Nếu một người liên tục theo đuổi mục tiêu được bên ngoài công nhận nhưng ít suy nghĩ liệu chúng có phù hợp giá trị của mình, thì ngay cả khi đạt mục đích họ vẫn có thể thấy trống rỗng. Ngược lại, người chọn công việc thu nhập bình thường nhưng có ý nghĩa, dành thời gian cho gia đình hoặc đóng góp xã hội cũng có thể được xem là thành công."),
            ("因此，更合理的做法也许是建立多方面的标准：既关注能力和贡献，也考虑身心状态、选择的自由以及生活是否具有意义。这样的标准无法用一张简单的排名表来表示，却能提醒我们，成功不是一场所有人使用同一条跑道的比赛。每个人都需要在不同阶段重新思考自己愿意承担什么、珍惜什么，以及希望成为怎样的人。",
             "Yīncǐ, gèng hélǐ de zuòfǎ yěxǔ shì jiànlì duō fāngmiàn de biāozhǔn: jì guānzhù nénglì hé gòngxiàn, yě kǎolǜ shēnxīn zhuàngtài, xuǎnzé de zìyóu yǐjí shēnghuó shìfǒu jùyǒu yìyì. Zhèyàng de biāozhǔn wúfǎ yòng yì zhāng jiǎndān de páimíngbiǎo lái biǎoshì, què néng tíxǐng wǒmen, chénggōng bú shì yì chǎng suǒyǒu rén shǐyòng tóng yì tiáo pǎodào de bǐsài. Měi ge rén dōu xūyào zài bùtóng jiēduàn chóngxīn sīkǎo zìjǐ yuànyì chéngdān shénme, zhēnxī shénme, yǐjí xīwàng chéngwéi zěnyàng de rén.",
             "Vì vậy, cách hợp lý hơn có lẽ là xây dựng tiêu chuẩn đa chiều: vừa chú ý năng lực và đóng góp, vừa cân nhắc trạng thái thể chất–tinh thần, tự do lựa chọn và ý nghĩa cuộc sống. Tiêu chuẩn này không thể thể hiện bằng một bảng xếp hạng đơn giản, nhưng nhắc ta rằng thành công không phải cuộc đua nơi mọi người chạy cùng một đường. Ở mỗi giai đoạn, mỗi người cần suy nghĩ lại mình sẵn sàng gánh vác gì, trân trọng gì và muốn trở thành người thế nào."),
        ],
        "vocab": [("衡量", "héngliáng", "đo lường, đánh giá"), ("价值观", "jiàzhíguān", "hệ giá trị"), ("未必", "wèibì", "chưa chắc"), ("多方面", "duō fāngmiàn", "đa chiều")],
        "questions": [("作者主要反对什么？", ["取得物质成就", "用单一外在标准定义成功", "为社会作贡献"], 1), ("第三段的主要作用是什么？", ["提出更全面的衡量方式", "否定所有标准", "介绍收入排名"], 0)],
        "task": "Tóm tắt lập luận trong 100–120 từ tiếng Việt và viết một đoạn phản hồi ngắn bằng tiếng Trung.",
    },
}

# Ba bài bổ sung cho mỗi cấp; kết hợp với bài dài phía trên và STORIES để đủ 5 bài/HSK.
SUPPLEMENTARY_READINGS = {
    "HSK1": [
        ("在咖啡店 · Ở quán cà phê", "A：你好，你喝什么？B：我喝茶。你呢？A：我喝咖啡。B：这个咖啡好吗？A：很好，谢谢。", "A: Nǐ hǎo, nǐ hē shénme? B: Wǒ hē chá. Nǐ ne? A: Wǒ hē kāfēi. B: Zhège kāfēi hǎo ma? A: Hěn hǎo, xièxie.", "A: Xin chào, bạn uống gì? B: Tôi uống trà. Còn bạn? A: Tôi uống cà phê. B: Cà phê này ngon không? A: Rất ngon, cảm ơn."),
        ("我的一天 · Một ngày của tôi", "我早上六点起床，七点吃饭。八点我去学校。上午我学习汉语，下午我和朋友看书。晚上九点我回家。", "Wǒ zǎoshang liù diǎn qǐchuáng, qī diǎn chīfàn. Bā diǎn wǒ qù xuéxiào. Shàngwǔ wǒ xuéxí Hànyǔ, xiàwǔ wǒ hé péngyou kànshū. Wǎnshang jiǔ diǎn wǒ huí jiā.", "Tôi dậy lúc sáu giờ sáng và ăn lúc bảy giờ. Tám giờ tôi đến trường. Buổi sáng tôi học tiếng Trung, buổi chiều đọc sách với bạn. Chín giờ tối tôi về nhà."),
        ("你家有几个人？ · Nhà bạn có mấy người?", "A：你家有几个人？B：我家有四个人：爸爸、妈妈、姐姐和我。A：你姐姐是老师吗？B：不是，她是医生。", "A: Nǐ jiā yǒu jǐ ge rén? B: Wǒ jiā yǒu sì ge rén: bàba, māma, jiějie hé wǒ. A: Nǐ jiějie shì lǎoshī ma? B: Bú shì, tā shì yīshēng.", "A: Nhà bạn có mấy người? B: Nhà tôi có bốn người: bố, mẹ, chị gái và tôi. A: Chị bạn là giáo viên à? B: Không, chị ấy là bác sĩ."),
    ],
    "HSK2": [
        ("问路 · Hỏi đường", "A：请问，地铁站怎么走？B：一直往前走，到银行以后向左走。A：远吗？B：不远，走五分钟就到了。A：谢谢你！", "A: Qǐngwèn, dìtiězhàn zěnme zǒu? B: Yìzhí wǎng qián zǒu, dào yínháng yǐhòu xiàng zuǒ zǒu. A: Yuǎn ma? B: Bù yuǎn, zǒu wǔ fēnzhōng jiù dào le. A: Xièxie nǐ!", "A: Xin hỏi đi đến ga tàu điện thế nào? B: Cứ đi thẳng, đến ngân hàng thì rẽ trái. A: Có xa không? B: Không xa, đi năm phút là tới. A: Cảm ơn bạn!"),
        ("生日礼物 · Quà sinh nhật", "明天是妈妈的生日。我想给她买一件礼物。妈妈喜欢看书，也喜欢听音乐。最后我买了一本书，还写了一张生日卡。希望她会喜欢。", "Míngtiān shì māma de shēngrì. Wǒ xiǎng gěi tā mǎi yí jiàn lǐwù. Māma xǐhuan kànshū, yě xǐhuan tīng yīnyuè. Zuìhòu wǒ mǎi le yì běn shū, hái xiě le yì zhāng shēngrì kǎ. Xīwàng tā huì xǐhuan.", "Ngày mai là sinh nhật mẹ. Tôi muốn mua cho mẹ một món quà. Mẹ thích đọc sách và nghe nhạc. Cuối cùng tôi mua một quyển sách và viết một tấm thiệp sinh nhật. Hy vọng mẹ sẽ thích."),
        ("看医生 · Đi khám bệnh", "A：你怎么了？B：我头疼，还有一点儿发烧。A：什么时候开始的？B：昨天晚上。A：你要多喝水、好好休息，今天不要去上班。", "A: Nǐ zěnme le? B: Wǒ tóuténg, hái yǒu yìdiǎnr fāshāo. A: Shénme shíhou kāishǐ de? B: Zuótiān wǎnshang. A: Nǐ yào duō hē shuǐ, hǎohāo xiūxi, jīntiān búyào qù shàngbān.", "A: Bạn làm sao vậy? B: Tôi đau đầu và hơi sốt. A: Bắt đầu từ khi nào? B: Tối qua. A: Bạn cần uống nhiều nước, nghỉ ngơi cho tốt và hôm nay đừng đi làm."),
    ],
    "HSK3": [
        ("迟到的原因 · Lý do đến muộn", "A：你今天怎么迟到了？B：我本来七点出门，但是公共汽车一直没来。A：你为什么不坐地铁？B：地铁站离我家太远。下次我会早点儿出门。", "A: Nǐ jīntiān zěnme chídào le? B: Wǒ běnlái qī diǎn chūmén, dànshì gōnggòng qìchē yìzhí méi lái. A: Nǐ wèishénme bú zuò dìtiě? B: Dìtiězhàn lí wǒ jiā tài yuǎn. Xià cì wǒ huì zǎodiǎnr chūmén.", "A: Sao hôm nay bạn đến muộn? B: Ban đầu tôi ra khỏi nhà lúc bảy giờ nhưng xe buýt mãi không tới. A: Sao bạn không đi tàu điện? B: Ga tàu điện quá xa nhà tôi. Lần sau tôi sẽ đi sớm hơn."),
        ("第一次做饭 · Lần đầu nấu ăn", "上个星期天，我第一次给朋友做中国菜。我先在网上看了一个视频，然后去超市买菜。做饭的时候，我把盐放多了，但是朋友们还是吃得很开心。大家说下次可以一起做。", "Shàng ge xīngqītiān, wǒ dì-yí cì gěi péngyou zuò Zhōngguó cài. Wǒ xiān zài wǎngshàng kàn le yí ge shìpín, ránhòu qù chāoshì mǎicài. Zuòfàn de shíhou, wǒ bǎ yán fàng duō le, dànshì péngyoumen háishi chī de hěn kāixīn. Dàjiā shuō xià cì kěyǐ yìqǐ zuò.", "Chủ nhật tuần trước, lần đầu tôi nấu món Trung Quốc cho bạn bè. Trước tiên tôi xem một video trên mạng rồi đi siêu thị mua thức ăn. Khi nấu, tôi cho hơi nhiều muối nhưng mọi người vẫn ăn rất vui. Họ nói lần sau có thể cùng nấu."),
        ("换工作吗？ · Có đổi việc không?", "A：听说你想换工作，是真的吗？B：我还没决定。现在的工作离家近，但是没有什么学习机会。A：新工作怎么样？B：工资高一点儿，也能学到新东西，不过每天要坐一个小时的车。", "A: Tīngshuō nǐ xiǎng huàn gōngzuò, shì zhēn de ma? B: Wǒ hái méi juédìng. Xiànzài de gōngzuò lí jiā jìn, dànshì méiyǒu shénme xuéxí jīhuì. A: Xīn gōngzuò zěnmeyàng? B: Gōngzī gāo yìdiǎnr, yě néng xuédào xīn dōngxi, búguò měitiān yào zuò yí ge xiǎoshí de chē.", "A: Nghe nói bạn muốn đổi việc, thật không? B: Tôi chưa quyết định. Công việc hiện tại gần nhà nhưng không có nhiều cơ hội học hỏi. A: Công việc mới thế nào? B: Lương cao hơn và học được điều mới, nhưng mỗi ngày phải đi xe một tiếng."),
    ],
    "HSK4": [
        ("会议时间变了 · Thời gian họp thay đổi", "A：下午的会议改到三点了，你知道吗？B：我刚看到邮件。为什么突然改变？A：经理的飞机晚点了。B：那我先把报告再检查一遍。你能帮我看看最后一页的数据吗？", "A: Xiàwǔ de huìyì gǎi dào sān diǎn le, nǐ zhīdào ma? B: Wǒ gāng kàn dào yóujiàn. Wèishénme tūrán gǎibiàn? A: Jīnglǐ de fēijī wǎndiǎn le. B: Nà wǒ xiān bǎ bàogào zài jiǎnchá yí biàn. Nǐ néng bāng wǒ kànkan zuìhòu yí yè de shùjù ma?", "A: Cuộc họp chiều chuyển sang ba giờ, bạn biết chưa? B: Tôi vừa thấy email. Sao đột nhiên thay đổi? A: Máy bay của quản lý bị trễ. B: Vậy tôi kiểm tra lại báo cáo một lượt. Bạn giúp tôi xem dữ liệu trang cuối nhé?"),
        ("一次志愿活动 · Một hoạt động tình nguyện", "周末，公司组织员工去河边捡垃圾。开始时，有些人觉得这只是一次普通活动。两个小时后，大家看到干净的河岸，都很有成就感。负责人还介绍了减少塑料使用的方法。很多同事决定以后自带水杯。", "Zhōumò, gōngsī zǔzhī yuángōng qù hébiān jiǎn lājī. Kāishǐ shí, yǒuxiē rén juéde zhè zhǐshì yí cì pǔtōng huódòng. Liǎng ge xiǎoshí hòu, dàjiā kàn dào gānjìng de hé'àn, dōu hěn yǒu chéngjiùgǎn. Fùzérén hái jièshào le jiǎnshǎo sùliào shǐyòng de fāngfǎ. Hěn duō tóngshì juédìng yǐhòu zì dài shuǐbēi.", "Cuối tuần, công ty tổ chức cho nhân viên nhặt rác ven sông. Ban đầu một số người nghĩ đây chỉ là hoạt động bình thường. Hai giờ sau, thấy bờ sông sạch, mọi người đều có cảm giác thành tựu. Người phụ trách còn giới thiệu cách giảm dùng nhựa. Nhiều đồng nghiệp quyết định sau này tự mang cốc."),
        ("要不要接受邀请？ · Có nên nhận lời mời?", "A：北京的公司请我去工作，可是我有点儿担心。B：机会听起来不错，你担心什么？A：父母年纪大了，我不想离他们太远。B：你可以先了解能不能远程工作一部分时间，再跟家人商量。", "A: Běijīng de gōngsī qǐng wǒ qù gōngzuò, kěshì wǒ yǒudiǎnr dānxīn. B: Jīhuì tīng qǐlái búcuò, nǐ dānxīn shénme? A: Fùmǔ niánjì dà le, wǒ bù xiǎng lí tāmen tài yuǎn. B: Nǐ kěyǐ xiān liǎojiě néng bu néng yuǎnchéng gōngzuò yí bùfen shíjiān, zài gēn jiārén shāngliang.", "A: Một công ty Bắc Kinh mời tôi làm việc nhưng tôi hơi lo. B: Cơ hội nghe khá tốt, bạn lo gì? A: Bố mẹ đã lớn tuổi, tôi không muốn ở quá xa. B: Bạn có thể tìm hiểu xem có thể làm từ xa một phần thời gian không rồi bàn với gia đình."),
    ],
    "HSK5": [
        ("项目延期 · Dự án bị hoãn", "A：客户希望下周看到结果，可是测试还没完成。B：如果急着交付，出现问题的风险会更大。A：那我们应该怎么解释？B：把目前的进度、剩下的风险和新的时间表写清楚，同时先提供一个可以展示的版本。", "A: Kèhù xīwàng xià zhōu kàn dào jiéguǒ, kěshì cèshì hái méi wánchéng. B: Rúguǒ jízhe jiāofù, chūxiàn wèntí de fēngxiǎn huì gèng dà. A: Nà wǒmen yīnggāi zěnme jiěshì? B: Bǎ mùqián de jìndù, shèngxià de fēngxiǎn hé xīn de shíjiānbiǎo xiě qīngchu, tóngshí xiān tígōng yí ge kěyǐ zhǎnshì de bǎnběn.", "A: Khách muốn thấy kết quả tuần tới nhưng kiểm thử chưa xong. B: Nếu vội bàn giao, rủi ro xảy ra vấn đề sẽ lớn hơn. A: Ta nên giải thích thế nào? B: Viết rõ tiến độ hiện tại, rủi ro còn lại và lịch mới, đồng thời cung cấp trước một phiên bản có thể trình diễn."),
        ("共享单车的影响 · Ảnh hưởng của xe đạp chia sẻ", "共享单车给城市交通带来了方便，短距离出行的人不必开车，也减少了寻找停车位的时间。然而，车辆乱停会影响行人，有些损坏的车也没有及时修理。解决问题不能只靠限制数量，企业、政府和使用者都需要承担责任。", "Gòngxiǎng dānchē gěi chéngshì jiāotōng dàilái le fāngbiàn, duǎn jùlí chūxíng de rén búbì kāichē, yě jiǎnshǎo le xúnzhǎo tíngchēwèi de shíjiān. Rán'ér, chēliàng luàntíng huì yǐngxiǎng xíngrén, yǒuxiē sǔnhuài de chē yě méiyǒu jíshí xiūlǐ. Jiějué wèntí bùnéng zhǐ kào xiànzhì shùliàng, qǐyè, zhèngfǔ hé shǐyòngzhě dōu xūyào chéngdān zérèn.", "Xe đạp chia sẻ tạo thuận tiện cho giao thông đô thị; người đi quãng ngắn không cần lái xe và giảm thời gian tìm chỗ đỗ. Tuy nhiên, xe đỗ bừa ảnh hưởng người đi bộ và một số xe hỏng không được sửa kịp thời. Không thể giải quyết chỉ bằng giới hạn số lượng; doanh nghiệp, chính quyền và người dùng đều cần chịu trách nhiệm."),
        ("选择稳定还是挑战？ · Chọn ổn định hay thử thách?", "A：新公司给我的工资更高，可是现在的团队对我很好。B：除了工资，你最看重什么？A：我希望负责更有挑战的项目，也想有学习空间。B：那就比较两个职位未来三年的发展，而不只是眼前的条件。", "A: Xīn gōngsī gěi wǒ de gōngzī gèng gāo, kěshì xiànzài de tuánduì duì wǒ hěn hǎo. B: Chúle gōngzī, nǐ zuì kànzhòng shénme? A: Wǒ xīwàng fùzé gèng yǒu tiǎozhàn de xiàngmù, yě xiǎng yǒu xuéxí kōngjiān. B: Nà jiù bǐjiào liǎng ge zhíwèi wèilái sān nián de fāzhǎn, ér bù zhǐshì yǎnqián de tiáojiàn.", "A: Công ty mới trả lương cao hơn nhưng đội hiện tại đối xử với tôi rất tốt. B: Ngoài lương, bạn coi trọng gì nhất? A: Tôi muốn phụ trách dự án thử thách hơn và có không gian học hỏi. B: Vậy hãy so sánh sự phát triển ba năm tới của hai vị trí, không chỉ điều kiện trước mắt."),
    ],
    "HSK6": [
        ("人工智能与判断力 · AI và năng lực phán đoán", "A：有了人工智能，很多分析工作都能自动完成，管理者是不是更容易做决定？B：数据处理确实更快了，但模型给出的答案取决于训练数据和目标。A：所以人仍然要负责？B：不仅要负责，还要判断哪些问题不应该只交给技术。", "A: Yǒu le réngōng zhìnéng, hěn duō fēnxī gōngzuò dōu néng zìdòng wánchéng, guǎnlǐzhě shì bú shì gèng róngyì zuò juédìng? B: Shùjù chǔlǐ quèshí gèng kuài le, dàn móxíng gěichū de dá'àn qǔjuéyú xùnliàn shùjù hé mùbiāo. A: Suǒyǐ rén réngrán yào fùzé? B: Bùjǐn yào fùzé, hái yào pànduàn nǎxiē wèntí bù yīnggāi zhǐ jiāogěi jìshù.", "A: Có AI, nhiều việc phân tích được tự động hóa, quản lý có dễ quyết định hơn không? B: Xử lý dữ liệu quả thật nhanh hơn, nhưng đáp án của mô hình phụ thuộc dữ liệu huấn luyện và mục tiêu. A: Vậy con người vẫn phải chịu trách nhiệm? B: Không chỉ chịu trách nhiệm mà còn phải phán đoán vấn đề nào không nên chỉ giao cho công nghệ."),
        ("城市更新中的记忆 · Ký ức trong cải tạo đô thị", "旧街区改造能改善住房条件，也能带来新的公共空间。然而，如果只追求商业价值，熟悉的店铺、邻里关系和地方记忆可能迅速消失。城市更新不应把过去当成发展的障碍，而应让居民参与讨论，在安全、功能与文化延续之间寻找平衡。", "Jiù jiēqū gǎizào néng gǎishàn zhùfáng tiáojiàn, yě néng dàilái xīn de gōnggòng kōngjiān. Rán'ér, rúguǒ zhǐ zhuīqiú shāngyè jiàzhí, shúxī de diànpù, línlǐ guānxì hé dìfāng jìyì kěnéng xùnsù xiāoshī. Chéngshì gēngxīn bù yīng bǎ guòqù dàngchéng fāzhǎn de zhàng'ài, ér yīng ràng jūmín cānyù tǎolùn, zài ānquán, gōngnéng yǔ wénhuà yánxù zhījiān xúnzhǎo pínghéng.", "Cải tạo khu phố cũ có thể cải thiện nhà ở và tạo không gian công cộng mới. Tuy nhiên, nếu chỉ theo đuổi giá trị thương mại, cửa hàng quen thuộc, quan hệ láng giềng và ký ức địa phương có thể nhanh chóng biến mất. Cải tạo đô thị không nên coi quá khứ là trở ngại mà cần để cư dân tham gia thảo luận, tìm cân bằng giữa an toàn, công năng và tiếp nối văn hóa."),
        ("失败是否值得公开？ · Có nên công khai thất bại?", "A：公司希望各部门分享失败案例，可很多人担心这会影响评价。B：如果分享等于追究责任，当然没人愿意说。A：那怎样才能真正学习？B：先区分可以通过实验发现的错误和违反基本规则的行为，再讨论系统如何让错误更早被发现。", "A: Gōngsī xīwàng gè bùmén fēnxiǎng shībài ànlì, kě hěn duō rén dānxīn zhè huì yǐngxiǎng píngjià. B: Rúguǒ fēnxiǎng děngyú zhuījiū zérèn, dāngrán méi rén yuànyì shuō. A: Nà zěnyàng cái néng zhēnzhèng xuéxí? B: Xiān qūfēn kěyǐ tōngguò shíyàn fāxiàn de cuòwù hé wéifǎn jīběn guīzé de xíngwéi, zài tǎolùn xìtǒng rúhé ràng cuòwù gèng zǎo bèi fāxiàn.", "A: Công ty muốn các phòng ban chia sẻ thất bại nhưng nhiều người lo ảnh hưởng đánh giá. B: Nếu chia sẻ đồng nghĩa truy trách nhiệm thì đương nhiên không ai muốn nói. A: Làm sao mới thực sự học được? B: Trước hết phân biệt sai sót có thể phát hiện qua thử nghiệm với hành vi vi phạm nguyên tắc cơ bản, rồi bàn cách hệ thống giúp phát hiện lỗi sớm hơn."),
    ],
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


@st.cache_data
def _load_chinese_resources():
    if not LANGUAGE_RESOURCES_PATH.exists():
        return []
    return json.loads(LANGUAGE_RESOURCES_PATH.read_text(encoding="utf-8")).get("Tiếng Trung", [])


def _dict_to_tuple(word):
    return (
        word["hanzi"], word["pinyin"], word["meaning"],
        word["example"], word["example_vi"], word.get("example_pinyin", ""),
    )


@st.cache_data
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
    _render_chinese_audio([(hanzi, pinyin, meaning, example, translation)], height=62, compact=True)
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
    page_size = 100
    page_count = max(1, (len(rows) + page_size - 1) // page_size)
    page = st.selectbox(
        "Trang", range(page_count), format_func=lambda value: f"{value + 1}/{page_count}",
        key=f"zh_vocab_page_{len(words)}_{query.strip().casefold()}",
    )
    start = page * page_size
    st.caption(f"Hiển thị {start + 1 if rows else 0}–{min(start + page_size, len(rows))} trong {len(rows)} từ")
    page_rows = rows[start:start + page_size]
    display = st.radio("Cách xem", ["🔊 Thẻ có âm thanh", "📋 Bảng gọn"], horizontal=True, key="zh_vocab_display")
    if display.startswith("🔊"):
        audio_rows = [(row["Hán tự"], row["Pinyin"], row["Nghĩa"], row["Ví dụ / câu ghi nhớ"], row["Dịch ví dụ"]) for row in page_rows]
        _render_chinese_audio(audio_rows)
    else:
        st.dataframe(pd.DataFrame(page_rows), use_container_width=True, hide_index=True)


def _render_chinese_audio(rows, height=720, compact=False):
    cards = []
    for hanzi, pinyin, meaning, example, translation in rows:
        safe_hanzi = html.escape(hanzi, quote=True)
        safe_example = html.escape(example, quote=True)
        if compact:
            cards.append(
                f"<div class='actions compact'><button data-speak='{safe_hanzi}'>🔊 Nghe từ</button>"
                f"<button data-speak='{safe_example}'>🔊 Nghe ví dụ</button></div>"
            )
        else:
            cards.append(
                f"<article class='card'><div><span class='hanzi'>{safe_hanzi}</span> "
                f"<span class='pinyin'>{html.escape(pinyin)}</span></div>"
                f"<div><b>Nghĩa:</b> {html.escape(meaning)}</div>"
                f"<div class='example'><b>Ví dụ:</b> {safe_example}</div>"
                f"<div class='translation'>{html.escape(translation)}</div>"
                f"<div class='actions'><button data-speak='{safe_hanzi}'>🔊 Từ</button>"
                f"<button data-speak='{safe_example}'>🔊 Ví dụ</button></div></article>"
            )
    components.html(
        f"""<!doctype html><html><head><style>
        *{{box-sizing:border-box}} body{{margin:0;font-family:Arial,'Microsoft YaHei',sans-serif;color:#172033}}
        .card{{padding:14px 16px;border:1px solid #e5e7eb;border-radius:14px;margin:8px 2px;background:#fff}}
        .hanzi{{font-size:27px;font-weight:800;color:#b45309}} .pinyin{{color:#7c3aed;font-size:17px}}
        .example{{margin-top:7px;color:#334155}} .translation{{color:#64748b;margin-top:3px}}
        .actions{{display:flex;gap:8px;margin-top:10px}} .compact{{justify-content:center;margin:3px}}
        button{{border:0;border-radius:9px;padding:8px 13px;background:#fef3c7;color:#92400e;font-weight:700;cursor:pointer}}
        button:hover{{background:#fde68a}} button.playing{{background:#d97706;color:white}}
        </style></head><body>{''.join(cards)}<script>
        function speak(text, button){{
          window.speechSynthesis.cancel();
          document.querySelectorAll('button').forEach(b => b.classList.remove('playing'));
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = 'zh-CN'; utterance.rate = 0.64; utterance.pitch = 1.05;
          const voices = window.speechSynthesis.getVoices();
          const female = /xiaoxiao|xiaoyi|huihui|yaoyao|hanhan|ting.ting|meijia|lili|female|woman/i;
          const preferred = voices.find(v => v.lang.startsWith('zh') && female.test(v.name))
            || voices.find(v => v.lang === 'zh-CN') || voices.find(v => v.lang.startsWith('zh'));
          if (preferred) utterance.voice = preferred;
          button.classList.add('playing'); utterance.onend = () => button.classList.remove('playing');
          utterance.onerror = () => button.classList.remove('playing'); window.speechSynthesis.speak(utterance);
        }}
        document.querySelectorAll('[data-speak]').forEach(button => button.addEventListener('click', () => speak(button.dataset.speak, button)));
        </script></body></html>""",
        height=height, scrolling=not compact,
    )


def _render_textbook(level):
    book = HSK_BOOKS.get(level)
    if not book:
        st.info("Sách HSK4-HSK6 hiện được lưu ở TeraBox và chưa có liên kết PDF nhúng ổn định.")
        st.link_button("Mở giáo trình trên TeraBox ↗", TERABOX_URL)
        return
    st.markdown(f"### Sách giáo khoa {level}")
    st.caption(f"Bản đầy đủ {book['pages']} trang. Bài học trực quan được ưu tiên; sách gốc dùng để đối chiếu.")
    preview_url = f"https://drive.google.com/file/d/{book['id']}/preview"
    mode = st.radio(
        "Cách học", ["🧠 Sơ đồ bài học", "📄 Sách gốc"], horizontal=True,
        key=f"textbook_mode_{level}",
    )
    if mode.startswith("🧠"):
        _render_material_smart_lesson({
            "id": book["id"], "name": f"Sách giáo khoa chuẩn {level}",
            "path": ["Giáo trình", level, f"Sách giáo khoa chuẩn {level}"], "type": "pdf",
        }, level)
    else:
        components.iframe(preview_url, height=760, scrolling=True)
    st.link_button("Mở sách toàn màn hình ↗", f"https://drive.google.com/file/d/{book['id']}/view")


def _material_levels(item):
    text = " ".join([item.get("name", ""), *item.get("path", [])]).upper()
    found = set(re.findall(r"HSK\s*([1-6])", text))
    for start, end in re.findall(r"(?:HSK\s*)?([1-6])\s*[-–]\s*([1-6])", text):
        found.update(str(number) for number in range(int(start), int(end) + 1))
    return {f"HSK{value}" for value in found}


def _render_classifier_lesson():
    st.markdown("## 168 lượng từ - học theo hình ảnh")
    st.caption("Chọn lượng từ bằng hình dáng và ngữ cảnh, thay vì học thuộc một danh sách dài.")
    st.markdown(
        """
        <div style="padding:22px;border-radius:18px;background:linear-gradient(135deg,#fff7ed,#f5f3ff);border:1px solid #eadcff">
          <div style="text-align:center;font-size:26px;font-weight:800;color:#5b21b6">DANH TỪ</div>
          <div style="text-align:center;color:#7c3aed;font-size:22px;margin:4px">↓ nhìn hình dáng / chức năng ↓</div>
          <div style="display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;text-align:center">
            <div style="padding:12px;background:#fff;border-radius:12px">👤 Người</div>
            <div style="padding:12px;background:#fff;border-radius:12px">📄 Mặt phẳng</div>
            <div style="padding:12px;background:#fff;border-radius:12px">🛣️ Dài & mềm</div>
            <div style="padding:12px;background:#fff;border-radius:12px">🔁 Lần & lượt</div>
          </div>
          <div style="text-align:center;font-size:22px;margin:10px">↓</div>
          <div style="text-align:center;font-size:23px;font-weight:750;color:#9a3412">Số + LƯỢNG TỪ + Danh từ</div>
          <div style="text-align:center;margin-top:5px">三 + 本 + 书 &nbsp;→&nbsp; 三本书 · ba quyển sách</div>
        </div>
        """, unsafe_allow_html=True,
    )

    st.markdown("### Bản đồ ghi nhớ")
    for start in range(0, len(CLASSIFIER_GROUPS), 2):
        columns = st.columns(2)
        for column, group in zip(columns, CLASSIFIER_GROUPS[start:start + 2]):
            icon, title, words, pinyin, tip, example = group
            with column:
                st.markdown(
                    f"<div style='min-height:185px;padding:16px;border:1px solid #e5e7eb;border-radius:16px;margin-bottom:10px'>"
                    f"<div style='font-size:22px;font-weight:750'>{icon} {title}</div>"
                    f"<div style='font-size:25px;color:#7c3aed;font-weight:800;margin-top:6px'>{words}</div>"
                    f"<div style='color:#6b7280'>{pinyin}</div><hr style='border:none;border-top:1px solid #eee'>"
                    f"<div>💡 {tip}</div><div style='margin-top:8px;color:#9a3412'>{example}</div></div>",
                    unsafe_allow_html=True,
                )

    st.markdown("### 3 mẹo dùng đúng")
    tip1, tip2, tip3 = st.columns(3)
    tip1.info("**1. Nhìn hình**\n\nVật mỏng/phẳng thường nghĩ đến 张; vật dài như dải thường nghĩ đến 条.")
    tip2.info("**2. Nhìn hành động**\n\n次 chỉ số lần; 遍 là làm hết từ đầu đến cuối; 趟 là một chuyến đi-về.")
    tip3.info("**3. Nhìn sắc thái**\n\n个 an toàn và phổ thông; 位 thể hiện sự tôn trọng khi nói về người.")
    st.warning("**Mẹo từ tài liệu:** lượng từ lặp lại diễn tả hành động nối tiếp: 一遍一遍地读 = đọc hết lượt này đến lượt khác.")

    st.markdown("### Tự kiểm tra trong 60 giây")
    with st.form("classifier_quiz"):
        answers = [st.radio(question, options, horizontal=True, key=f"classifier_q_{index}") for index, (question, _, options) in enumerate(CLASSIFIER_QUIZ)]
        submitted = st.form_submit_button("Chấm điểm", use_container_width=True)
    if submitted:
        score = sum(answer == correct for answer, (_, correct, _) in zip(answers, CLASSIFIER_QUIZ))
        st.success(f"Bạn đúng {score}/{len(CLASSIFIER_QUIZ)} câu.")
        if score < len(CLASSIFIER_QUIZ):
            corrections = [f"{index + 1}. **{correct}**" for index, (answer, (_, correct, _)) in enumerate(zip(answers, CLASSIFIER_QUIZ)) if answer != correct]
            st.markdown("Câu cần xem lại: " + " · ".join(corrections))


def _material_lesson_type(item):
    text = " ".join(item.get("path", []) + [item.get("name", "")]).casefold()
    if any(word in text for word in ["ngữ pháp", "ngu phap", "sửa lỗi", "sua loi"]):
        return "grammar"
    if any(word in text for word in ["bài tập", "bai tap", "-bt", "đáp án", "dap an", "sắp xếp câu"]):
        return "exercise"
    if any(word in text for word in ["mp3", "audio", "phiên âm", ".jpg"]):
        return "pronunciation"
    if any(word in text for word in ["bộ thủ", "bo thu", "hán tự", "han tu", "tập viết"]):
        return "radical"
    if any(word in text for word in ["từ vựng", "tu vung", "đàm thoại", "dam thoai"]):
        return "vocabulary"
    if re.search(r"h1\d{4}", text) or "tổng hợp hsk1" in text:
        return "exam"
    if any(word in text for word in ["giáo trình", "giao trinh", "boya", "sách giáo khoa"]):
        return "textbook"
    return "reference"


def _render_material_smart_lesson(item, level):
    lesson_type = _material_lesson_type(item)
    template = MATERIAL_LESSON_TEMPLATES[lesson_type]
    detected_levels = sorted(_material_levels(item))
    level_label = ", ".join(detected_levels) if detected_levels else f"Có thể dùng bổ trợ cho {level}"
    title = item.get("name", "Tài liệu")

    st.markdown(f"## {template['icon']} {title.rsplit('.', 1)[0]}")
    st.caption(f"Dạng học: {template['label']} · Cấp độ: {level_label}")
    branch_html = "".join(
        f"<div style='padding:13px 8px;background:#fff;border:1px solid #e9d5ff;border-radius:12px;text-align:center;font-weight:650'>{branch}</div>"
        for branch in template["branches"]
    )
    st.markdown(
        f"<div style='padding:20px;border-radius:18px;background:linear-gradient(135deg,#faf5ff,#eff6ff);border:1px solid #ddd6fe'>"
        f"<div style='text-align:center;font-size:24px;font-weight:800;color:#6d28d9'>{template['label'].upper()}</div>"
        f"<div style='text-align:center;color:#8b5cf6;font-size:20px;margin:5px'>↓ học theo 4 nhánh ↓</div>"
        f"<div style='display:grid;grid-template-columns:repeat(4,minmax(110px,1fr));gap:9px'>{branch_html}</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Lộ trình học tài liệu này")
    cols = st.columns(3)
    for index, (column, step) in enumerate(zip(cols, template["steps"]), 1):
        column.markdown(
            f"<div style='min-height:130px;padding:15px;border-radius:14px;border:1px solid #e5e7eb'>"
            f"<div style='font-size:23px;font-weight:800;color:#7c3aed'>0{index}</div><div>{step}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("### Mẹo ghi nhớ & sử dụng")
    for tip in template["tips"]:
        st.markdown(f"- 💡 {tip}")

    with st.expander("📝 Phiếu học nhanh", expanded=True):
        st.text_area("Ba ý chính", placeholder="1. ...\n2. ...\n3. ...", key=f"notes_key_{item['id']}", height=100)
        left, right = st.columns(2)
        left.text_input("Một ví dụ tự đặt", key=f"example_key_{item['id']}")
        right.select_slider("Mức độ đã hiểu", ["Chưa rõ", "Nhận biết", "Hiểu", "Dùng được"], key=f"mastery_key_{item['id']}")
        st.checkbox("Tôi có thể giải thích lại mà không nhìn tài liệu", key=f"recall_key_{item['id']}")


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
    is_classifier_lesson = "168 luong tu" in selected["name"].casefold()
    display_mode = st.radio(
        "Cách học", ["🧠 Bài học trực quan", "📄 Tài liệu gốc"], horizontal=True,
        key=f"material_display_{selected['id']}",
    )
    if display_mode.startswith("🧠"):
        if is_classifier_lesson:
            _render_classifier_lesson()
        else:
            _render_material_smart_lesson(selected, level)
    else:
        if selected.get("type") == "pdf":
            components.iframe(f"https://drive.google.com/file/d/{selected['id']}/preview", height=760, scrolling=True)
        else:
            st.info("Định dạng này được mở bằng trình xem của Google Drive.")
    st.link_button("Mở toàn màn hình trên Drive ↗", file_url)


def _reading_lessons(level):
    primary = dict(CHINESE_READINGS[level])
    primary["kind"] = "Bài đọc dài"
    legacy = STORIES[level]
    story_lesson = {
        "title": legacy["title"], "kind": "Câu chuyện",
        "paragraphs": legacy["sentences"], "vocab": [], "questions": [],
        "task": "Kể lại câu chuyện bằng 3–5 câu mà không nhìn bản gốc.",
    }
    extras = []
    for title, text, pinyin, translation in SUPPLEMENTARY_READINGS[level]:
        extras.append({
            "title": title, "kind": "Hội thoại" if "A：" in text else "Đoạn văn",
            "paragraphs": [(text, pinyin, translation)], "vocab": [], "questions": [],
            "task": "Dịch bài, gạch các từ nối/cụm quan trọng và viết lại ý chính bằng lời của bạn.",
        })
    return [primary, story_lesson, *extras]


def _render_story(level):
    lessons = _reading_lessons(level)
    selected_index = st.selectbox(
        "Chọn bài đọc", range(len(lessons)),
        format_func=lambda index: f"Bài {index + 1} · {lessons[index]['kind']} · {lessons[index]['title']}",
        key=f"zh_reading_lesson_{level}",
    )
    story = lessons[selected_index]
    full_text = "".join(paragraph[0] for paragraph in story["paragraphs"])
    st.markdown(f"### {story['title']}")
    st.caption(f"Bài {selected_index + 1}/5 · {story['kind']} · {level} · {len(full_text)} chữ Hán")
    safe_text = html.escape(full_text, quote=True)
    rate = 0.58 if level in ("HSK1", "HSK2") else 0.64 if level in ("HSK3", "HSK4") else 0.7
    components.html(
        f"""<!doctype html><html><head><style>
        body{{margin:0;font-family:Arial,sans-serif}}button{{border:0;border-radius:10px;padding:9px 15px;
        background:#ede9fe;color:#5b21b6;font-weight:700;cursor:pointer}}button.playing{{background:#7c3aed;color:white}}
        </style></head><body><button id="read" data-text="{safe_text}">🔊 Giọng nữ · đọc chậm</button><script>
        const b=document.getElementById('read');b.onclick=()=>{{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(b.dataset.text);
        u.lang='zh-CN';u.rate={rate};u.pitch=1.05;const voices=speechSynthesis.getVoices();
        const female=/xiaoxiao|xiaoyi|huihui|yaoyao|hanhan|ting.ting|meijia|lili|female|woman/i;
        const preferred=voices.find(v=>v.lang.startsWith('zh')&&female.test(v.name))||voices.find(v=>v.lang==='zh-CN')||voices.find(v=>v.lang.startsWith('zh'));if(preferred)u.voice=preferred;
        b.classList.add('playing');u.onend=()=>b.classList.remove('playing');
        u.onerror=()=>b.classList.remove('playing');speechSynthesis.speak(u);}};</script></body></html>""", height=48,
    )
    lesson_key = f"{level}_{selected_index}"
    show_pinyin = st.toggle("Hiện pinyin", value=True, key=f"zh_story_pinyin_{lesson_key}")
    show_translation = st.toggle("Hiện bản dịch", value=False, key=f"zh_story_translation_{lesson_key}")
    for index, (paragraph, pinyin, translation) in enumerate(story["paragraphs"], 1):
        st.markdown(f"**Đoạn {index}**")
        st.markdown(
            f"<div style='font-size:22px;line-height:1.9;padding:16px 18px;background:#fafafa;"
            f"border-left:5px solid #7c3aed;border-radius:12px'>{html.escape(paragraph)}</div>",
            unsafe_allow_html=True,
        )
        if show_pinyin:
            st.caption(pinyin)
        if show_translation:
            st.info(translation)

    if story["vocab"]:
        st.markdown("#### Từ khóa trong ngữ cảnh")
        columns = st.columns(2)
        for index, (word, pinyin, meaning) in enumerate(story["vocab"]):
            columns[index % 2].markdown(f"- **{word}** · *{pinyin}* — {meaning}")

    st.markdown("#### Đọc hiểu")
    if story["questions"]:
        answers = [
            st.radio(question, options, index=None, key=f"zh_reading_question_{lesson_key}_{index}")
            for index, (question, options, _) in enumerate(story["questions"])
        ]
        if st.button("Chấm phần đọc hiểu", key=f"zh_reading_check_{lesson_key}"):
            if any(answer is None for answer in answers):
                st.warning("Bạn hãy trả lời đủ câu hỏi trước khi chấm.")
            else:
                score = sum(answer == options[correct] for answer, (_, options, correct) in zip(answers, story["questions"]))
                st.success(f"Bạn đúng {score}/{len(story['questions'])} câu.")
    else:
        st.text_area("Ý chính, nhân vật và kết quả của bài", key=f"zh_reading_comprehension_{lesson_key}", height=100)

    st.markdown("#### Thực hành dịch")
    st.caption(story["task"])
    st.text_area("Bản dịch/tóm tắt của bạn", placeholder="Tự làm trước khi bật bản dịch mẫu...",
                 key=f"zh_story_answer_{lesson_key}", height=160)
    with st.expander("Gợi ý quy trình đọc và dịch"):
        st.markdown("1. Đọc chữ Hán và đoán ý chính trước khi xem pinyin.  \n2. Tìm chủ ngữ, động từ và các từ nối.  \n3. Dịch theo cụm nghĩa, không ghép từng chữ.  \n4. Bật bản dịch mẫu để đối chiếu sau khi tự làm.")
    with st.expander("Nguồn đối chiếu cấp độ"):
        st.markdown(f"- [Chuẩn năng lực tiếng Trung trong giáo dục tiếng Trung quốc tế (Bộ Giáo dục Trung Quốc)]({CHINESE_STANDARD_URL})")


def _render_grammar_lesson(topic):
    lesson = GRAMMAR_LESSONS[topic]
    cards = "".join(
        f"<div style='padding:12px;background:white;border:1px solid #c4b5fd;border-radius:13px;min-height:92px'>"
        f"<b style='color:#6d28d9'>{html.escape(title)}</b>"
        f"<div style='font-size:13px;margin-top:5px'>{html.escape(rule)}</div></div>"
        for title, rule, *_ in lesson["branches"]
    )
    st.markdown(
        f"<div style='padding:20px;border-radius:18px;background:linear-gradient(135deg,#faf5ff,#eff6ff);border:1px solid #ddd6fe'>"
        f"<div style='text-align:center;font-size:13px;color:#7c3aed;font-weight:700'>SƠ ĐỒ TƯ DUY</div>"
        f"<div style='text-align:center;font-size:24px;font-weight:850;color:#4c1d95;margin:4px 0'>{html.escape(topic)}</div>"
        f"<div style='text-align:center;background:#7c3aed;color:white;border-radius:12px;padding:10px;margin:12px auto;max-width:720px'>"
        f"{html.escape(lesson['formula'])}</div>"
        f"<div style='display:grid;grid-template-columns:repeat(2,minmax(180px,1fr));gap:10px'>{cards}</div></div>",
        unsafe_allow_html=True,
    )
    st.info(f"**Khi dùng:** {lesson['use']}")

    st.markdown("#### Nội dung và ví dụ")
    for title, rule, example, pinyin, meaning in lesson["branches"]:
        with st.expander(f"🧩 {title} · {rule}", expanded=True):
            st.markdown(f"### {example}")
            st.caption(pinyin)
            st.success(meaning)

    st.markdown("#### Lỗi thường gặp")
    for mistake in lesson["mistakes"]:
        st.warning(mistake)

    question, answer, options = lesson["quiz"]
    st.markdown("#### Kiểm tra nhanh")
    choice = st.radio(question, options, index=None, key=f"grammar_quiz_{topic}")
    if choice:
        if choice == answer:
            st.success("Chính xác! Bạn đã nhận diện đúng cấu trúc.")
        else:
            st.error(f"Chưa đúng. Đáp án là: {answer}")
    st.text_area("Tự đặt 2 câu với cấu trúc này", key=f"grammar_practice_{topic}", height=100)


def _render_pdf_library():
    st.markdown("### Thư viện ngữ pháp")
    st.caption("Học nội dung và sơ đồ tư duy ngay trong ứng dụng; Drive chỉ còn là tài liệu đối chiếu.")
    topic = st.selectbox("Chọn chủ đề", list(PDF_LIBRARY), key="zh_pdf_topic")
    material = PDF_LIBRARY[topic]

    st.markdown(
        f"<div style='padding:16px 18px;border-radius:14px;background:#f7f3ff;"
        f"border-left:5px solid #7c3aed;margin:8px 0 14px'>"
        f"<div style='font-size:21px;font-weight:700'>{topic}</div>"
        f"<div style='color:#6b7280;margin:4px 0'>Phù hợp: {material['level']}</div>"
        f"<div>{material['summary']}</div></div>", unsafe_allow_html=True,
    )

    if topic in GRAMMAR_LESSONS:
        _render_grammar_lesson(topic)
    else:
        _render_material_smart_lesson({
            "id": material["file_id"], "name": topic,
            "path": ["Thư viện ngữ pháp", material["level"], topic], "type": "pdf",
        }, material["level"].split("-")[0])
        for index, step in enumerate(material["focus"], 1):
            st.markdown(f"- **{index}.** {step}")
    with st.expander("📎 Tài liệu Drive để đối chiếu"):
        st.link_button("Mở tài liệu gốc ↗", f"https://drive.google.com/file/d/{material['file_id']}/view")


def _render_sources(level):
    st.markdown(f"### Giáo trình chuẩn {level}")
    st.info("Từ vựng, pinyin, ví dụ và bài đọc của cấp độ này đã được chuẩn hóa trong các tab bên cạnh.")
    st.markdown("**Tài liệu tham khảo thêm:** sách giáo khoa, sách bài tập, tập viết và file nghe trên TeraBox.")
    st.link_button("Mở kho giáo trình HSK trên TeraBox ↗", TERABOX_URL)
    st.caption("TeraBox chưa cung cấp liên kết nhúng ổn định cho từng PDF, nên nút này được giữ làm nguồn đối chiếu.")
    st.markdown("**Kho bổ sung:** bài tập, giáo trình Hán ngữ/Boya, ngữ pháp HSK1-HSK6 và tài liệu người mới học.")
    st.link_button("Mở kho tài liệu tiếng Trung bổ sung ↗", EXTRA_DRIVE_URL)


def _render_extended_sources(level):
    resources = _load_chinese_resources()
    st.markdown("### Kho tiếng Trung mở rộng")
    st.caption(f"{len(resources)} nguồn duy nhất đã được phân loại từ danh mục Drive.")
    tags = sorted({tag for item in resources for tag in item["tags"]})
    col1, col2 = st.columns(2)
    scope = col1.selectbox("Cấp độ", [f"Gợi ý cho {level}", "Tất cả"], key="zh_extended_level")
    tag = col2.selectbox("Chủ đề", ["Tất cả"] + tags, key="zh_extended_tag")
    query = st.text_input("Tìm nguồn", placeholder="Ví dụ: HSK, giao tiếp, ngữ pháp...", key="zh_extended_query")
    filtered = resources
    if scope.startswith("Gợi ý"):
        filtered = [item for item in filtered if not item["levels"] or level in item["levels"]]
    if tag != "Tất cả":
        filtered = [item for item in filtered if tag in item["tags"]]
    if query.strip():
        needle = query.strip().casefold()
        filtered = [item for item in filtered if needle in item["name"].casefold()]
    st.caption(f"Tìm thấy {len(filtered)} nguồn")
    for item in filtered[:40]:
        with st.expander(f"📚 {item['name']}"):
            st.markdown(" · ".join(f"`{tag}`" for tag in item["tags"]))
            if item["levels"]:
                st.caption("Gợi ý cấp độ: " + ", ".join(item["levels"]))
            st.link_button("Mở tài liệu gốc ↗", item["url"])
    if len(filtered) > 40:
        st.info("Đang hiển thị 40 kết quả đầu. Hãy dùng tìm kiếm để thu hẹp danh sách.")


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
    views = ["🃏 Flashcard", "📋 Vocabulary List", "📖 Đọc & dịch", "📘 Sách đầy đủ", "🗂 Kho HSK1–6", "🌐 Kho mở rộng", "📕 Ngữ pháp PDF", "📚 Nguồn khác"]
    view = st.radio(
        "Chế độ học", views, horizontal=True, key="zh_training_view",
        help="Chỉ tải chế độ đang chọn để web phản hồi nhanh hơn.",
    )
    if view == views[0]:
        _render_flashcards(level, words)
    elif view == views[1]:
        _render_vocab_list(words)
    elif view == views[2]:
        _render_story(level)
    elif view == views[3]:
        _render_textbook(level)
    elif view == views[4]:
        _render_material_library(level)
    elif view == views[5]:
        _render_extended_sources(level)
    elif view == views[6]:
        _render_pdf_library()
    else:
        _render_sources(level)
