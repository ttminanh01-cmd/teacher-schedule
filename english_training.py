import json
import html
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from language_widgets import tts_speak_fn, render_resource_results


CATALOG_PATH = Path(__file__).with_name("course_catalog_raw.json")
EXTENDED_VOCAB_PATH = Path(__file__).with_name("english_vocab_extended.json")
LANGUAGE_RESOURCES_PATH = Path(__file__).with_name("language_resources.json")
VSTEP_DRIVE_FOLDER = "https://drive.google.com/drive/folders/1Gev0rkSGNqk22xZaOEuUQbSNYTzfgFGo?usp=sharing"

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
    "CEFR Companion Volume 2020": "https://rm.coe.int/common-european-framework-of-reference-for-languages-learning-teaching/16809ea0d4",
    "British Council - Reading by CEFR level": "https://learnenglish.britishcouncil.org/free-resources/reading",
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

READING_PASSAGES = {
    "Pre-A1 · Khởi động": {
        "title": "My first day",
        "type": "Thẻ giới thiệu cá nhân",
        "paragraphs": [
            "Hello. My name is Mai. I am new here. I work in the sales team. My manager is Mr Long. My desk is near the window. I start work at eight o'clock. My email is mai@sunrise.example.",
        ],
        "translations": [
            "Xin chào. Tôi tên là Mai. Tôi là người mới ở đây. Tôi làm trong nhóm kinh doanh. Quản lý của tôi là anh Long. Bàn làm việc của tôi ở gần cửa sổ. Tôi bắt đầu làm việc lúc tám giờ. Email của tôi là mai@sunrise.example.",
        ],
        "vocab": [("new", "mới"), ("sales team", "nhóm kinh doanh"), ("near", "gần")],
        "questions": [("Mai làm ở bộ phận nào?", ["Sales", "Finance", "IT"], 0), ("Cô ấy bắt đầu làm lúc mấy giờ?", ["7 giờ", "8 giờ", "9 giờ"], 1)],
        "task": "Điền tên, bộ phận, quản lý và giờ bắt đầu làm việc của Mai.",
    },
    "A1 · Nền tảng": {
        "title": "A change to Monday's meeting",
        "type": "Email công việc ngắn",
        "paragraphs": [
            "Hi everyone, our Monday meeting is now at 10:30, not 9:00. We will meet in Room 4 on the second floor. Please bring your weekly task list. Lan will show us the new work schedule, and I will answer questions. The meeting will finish at 11:15. Please tell me today if you cannot come. Thanks, Minh.",
        ],
        "translations": [
            "Chào mọi người, cuộc họp thứ Hai của chúng ta được chuyển sang 10 giờ 30, không phải 9 giờ. Chúng ta sẽ họp tại Phòng 4 ở tầng hai. Vui lòng mang theo danh sách công việc hằng tuần. Lan sẽ giới thiệu lịch làm việc mới và tôi sẽ trả lời câu hỏi. Cuộc họp sẽ kết thúc lúc 11 giờ 15. Hãy báo cho tôi trong hôm nay nếu bạn không thể tham dự. Cảm ơn, Minh.",
        ],
        "vocab": [("bring", "mang theo"), ("work schedule", "lịch làm việc"), ("finish", "kết thúc")],
        "questions": [("Cuộc họp bắt đầu lúc nào?", ["9:00", "10:30", "11:15"], 1), ("Mọi người cần mang theo gì?", ["Máy tính", "Báo cáo tháng", "Danh sách công việc tuần"], 2)],
        "task": "Tìm bốn chi tiết: ngày, giờ, địa điểm và vật cần mang theo.",
    },
    "A2 · Giao tiếp chủ động": {
        "title": "A delivery problem",
        "type": "Email cập nhật và đề xuất giải pháp",
        "paragraphs": [
            "Dear Ms Brown, I am writing about your order of twenty office chairs. The delivery was planned for Tuesday, but our driver had a problem with the van. We can deliver fifteen chairs on Wednesday morning and the other five on Friday afternoon.",
            "I am sorry for the delay. If this plan is not convenient, we can send all twenty chairs together on Friday. Please reply before 3 p.m. today and tell me which option you prefer. Kind regards, Nam.",
        ],
        "translations": [
            "Kính gửi bà Brown, tôi viết thư về đơn hàng hai mươi chiếc ghế văn phòng của bà. Việc giao hàng được dự kiến vào thứ Ba, nhưng tài xế của chúng tôi gặp vấn đề với xe tải. Chúng tôi có thể giao mười lăm chiếc vào sáng thứ Tư và năm chiếc còn lại vào chiều thứ Sáu.",
            "Tôi xin lỗi vì sự chậm trễ. Nếu phương án này không thuận tiện, chúng tôi có thể giao cả hai mươi chiếc cùng lúc vào thứ Sáu. Vui lòng phản hồi trước 3 giờ chiều hôm nay và cho tôi biết bà muốn chọn phương án nào. Trân trọng, Nam.",
        ],
        "vocab": [("delivery", "việc giao hàng"), ("delay", "sự chậm trễ"), ("convenient", "thuận tiện"), ("prefer", "thích/chọn hơn")],
        "questions": [("Vì sao giao hàng bị chậm?", ["Thiếu ghế", "Xe gặp sự cố", "Khách đổi địa chỉ"], 1), ("Khách phải phản hồi khi nào?", ["Trước 3 giờ hôm nay", "Sáng thứ Tư", "Chiều thứ Sáu"], 0)],
        "task": "Tóm tắt vấn đề và hai phương án giao hàng bằng 3–4 câu tiếng Việt.",
    },
    "B1 · Làm việc độc lập": {
        "title": "A small change that saved time",
        "type": "Bản cập nhật dự án",
        "paragraphs": [
            "Our support team used to hold a one-hour meeting every morning. Although the meeting helped people share information, it also interrupted the busiest part of the day. Last month, the team tested a different system. Everyone posted a short written update before 9 a.m., and the team only met when an issue needed discussion.",
            "After four weeks, the number of unresolved customer requests fell by 18 per cent. Staff also reported that they had more time for focused work. However, two new employees said they sometimes missed useful background information. The manager has therefore decided to keep the written updates and add a short question-and-answer meeting every Friday.",
        ],
        "translations": [
            "Trước đây, nhóm hỗ trợ của chúng tôi họp một giờ vào mỗi buổi sáng. Mặc dù cuộc họp giúp mọi người chia sẻ thông tin, nó cũng làm gián đoạn khoảng thời gian bận rộn nhất trong ngày. Tháng trước, nhóm thử một hệ thống khác. Mọi người đăng một bản cập nhật ngắn trước 9 giờ và nhóm chỉ họp khi có vấn đề cần thảo luận.",
            "Sau bốn tuần, số yêu cầu của khách hàng chưa được giải quyết giảm 18 phần trăm. Nhân viên cũng cho biết họ có thêm thời gian làm việc tập trung. Tuy nhiên, hai nhân viên mới nói rằng đôi khi họ bỏ lỡ thông tin nền hữu ích. Vì vậy, quản lý quyết định giữ các bản cập nhật bằng văn bản và bổ sung một cuộc họp hỏi đáp ngắn vào mỗi thứ Sáu.",
        ],
        "vocab": [("interrupt", "làm gián đoạn"), ("unresolved", "chưa được giải quyết"), ("focused work", "công việc cần tập trung"), ("background information", "thông tin nền")],
        "questions": [("Hệ thống mới thay cuộc họp sáng bằng gì?", ["Cuộc gọi khách hàng", "Bản cập nhật viết", "Báo cáo tháng"], 1), ("Vì sao vẫn cần buổi hỏi đáp thứ Sáu?", ["Nhân viên mới thiếu bối cảnh", "Khách hàng yêu cầu", "Quản lý muốn họp lâu hơn"], 0)],
        "task": "Viết 3 câu: thay đổi là gì, kết quả ra sao và điểm hạn chế nào còn tồn tại.",
    },
    "B2 · Chuyên nghiệp": {
        "title": "Should the company adopt a four-day week?",
        "type": "Tóm tắt đề xuất có nhiều quan điểm",
        "paragraphs": [
            "A six-month trial of a four-day working week has produced encouraging but mixed results. Output remained stable in most departments, while reported stress fell and sick leave decreased. Recruitment also became easier because the shorter week attracted experienced candidates. These findings suggest that performance does not always depend on the number of hours spent at a desk.",
            "Nevertheless, the customer service and logistics teams struggled to maintain coverage. Some employees worked longer days, which created new childcare difficulties. Managers also warned that the trial took place during a relatively quiet period. The proposal should therefore not be presented as a universal solution. A more practical next step would be to let each department choose between a shorter week, flexible hours or the existing schedule, then compare results over a full business cycle.",
        ],
        "translations": [
            "Một thử nghiệm kéo dài sáu tháng về tuần làm việc bốn ngày đã tạo ra kết quả đáng khích lệ nhưng không hoàn toàn đồng nhất. Sản lượng vẫn ổn định ở hầu hết các phòng ban, trong khi mức căng thẳng được ghi nhận giảm và số ngày nghỉ ốm ít đi. Việc tuyển dụng cũng dễ dàng hơn vì tuần làm việc ngắn thu hút ứng viên giàu kinh nghiệm. Những phát hiện này cho thấy hiệu suất không phải lúc nào cũng phụ thuộc vào số giờ ngồi tại bàn làm việc.",
            "Tuy vậy, các nhóm dịch vụ khách hàng và hậu cần gặp khó khăn trong việc duy trì nhân sự trực. Một số nhân viên phải làm những ngày dài hơn, tạo ra khó khăn mới về chăm sóc con cái. Quản lý cũng cảnh báo rằng thử nghiệm diễn ra trong giai đoạn tương đối ít việc. Vì thế, không nên xem đề xuất này là giải pháp áp dụng cho mọi nơi. Bước tiếp theo thực tế hơn là cho mỗi phòng ban chọn tuần làm việc ngắn, giờ linh hoạt hoặc lịch hiện tại, rồi so sánh kết quả trong một chu kỳ kinh doanh đầy đủ.",
        ],
        "vocab": [("coverage", "mức độ bố trí nhân sự/bao phủ"), ("mixed results", "kết quả trái chiều"), ("universal solution", "giải pháp áp dụng cho mọi trường hợp"), ("business cycle", "chu kỳ kinh doanh")],
        "questions": [("Thái độ chung của tác giả là gì?", ["Hoàn toàn ủng hộ", "Hoàn toàn phản đối", "Thận trọng và đề nghị thử linh hoạt"], 2), ("Điều gì làm kết quả thử nghiệm chưa chắc chắn?", ["Diễn ra lúc ít việc", "Không có ứng viên", "Sản lượng giảm ở mọi bộ phận"], 0)],
        "task": "Tách luận điểm thành ba nhóm: lợi ích, rủi ro và khuyến nghị của tác giả.",
    },
    "C1 · Dẫn dắt": {
        "title": "When efficiency hides organisational risk",
        "type": "Phân tích quản trị",
        "paragraphs": [
            "Efficiency programmes often reward teams for removing duplication and standardising decisions. In the short term, this can reduce costs and make performance easier to measure. Yet an organisation that optimises every process around normal conditions may also remove the spare capacity that helps it respond to disruption. What appears wasteful in a quarterly report—overlapping expertise, extra inventory or time reserved for reflection—may function as insurance when assumptions fail.",
            "The difficulty is that resilience has an uncertain return, whereas efficiency produces immediate figures. Leaders may therefore approve cuts whose benefits are visible and postpone investment whose value becomes clear only during a crisis. This does not mean that every redundancy should be protected. It means that decisions should distinguish accidental waste from deliberate buffers and should state which risks the organisation is choosing to accept.",
            "A balanced review would consequently measure more than unit cost. It would examine recovery time, dependency on individual suppliers, the ease with which staff can move between roles and the quality of decisions made under pressure. By treating resilience as a capability rather than an expense, leaders can pursue efficiency without quietly making the organisation more fragile.",
        ],
        "translations": [
            "Các chương trình nâng cao hiệu quả thường khen thưởng những nhóm loại bỏ công việc trùng lặp và chuẩn hóa quyết định. Trong ngắn hạn, việc này có thể giảm chi phí và giúp đo lường hiệu suất dễ hơn. Tuy nhiên, một tổ chức tối ưu mọi quy trình cho điều kiện bình thường cũng có thể loại bỏ năng lực dự phòng vốn giúp ứng phó với gián đoạn. Những gì có vẻ lãng phí trong báo cáo quý—chuyên môn chồng lấn, hàng tồn kho bổ sung hoặc thời gian dành cho suy ngẫm—có thể đóng vai trò như bảo hiểm khi các giả định không còn đúng.",
            "Khó khăn nằm ở chỗ khả năng chống chịu có lợi ích không chắc chắn, trong khi hiệu quả tạo ra con số tức thời. Vì vậy, lãnh đạo có thể phê duyệt các khoản cắt giảm với lợi ích dễ thấy và trì hoãn đầu tư chỉ bộc lộ giá trị khi khủng hoảng xảy ra. Điều này không có nghĩa mọi phần dư thừa đều cần được bảo vệ. Nó có nghĩa quyết định phải phân biệt lãng phí vô tình với vùng đệm có chủ đích và phải nêu rõ tổ chức đang lựa chọn chấp nhận rủi ro nào.",
            "Do đó, một cuộc rà soát cân bằng sẽ đo lường nhiều hơn chi phí đơn vị. Nó sẽ xem xét thời gian phục hồi, mức phụ thuộc vào từng nhà cung cấp, khả năng nhân viên chuyển đổi vai trò và chất lượng quyết định dưới áp lực. Khi coi khả năng chống chịu là một năng lực thay vì một khoản chi, lãnh đạo có thể theo đuổi hiệu quả mà không âm thầm khiến tổ chức trở nên mong manh hơn.",
        ],
        "vocab": [("spare capacity", "năng lực dự phòng"), ("resilience", "khả năng chống chịu/phục hồi"), ("deliberate buffer", "vùng đệm có chủ đích"), ("fragile", "mong manh, dễ tổn thương")],
        "questions": [("Nghịch lý trung tâm của bài là gì?", ["Hiệu quả luôn làm tăng chi phí", "Tối ưu hóa có thể làm giảm khả năng chống chịu", "Dự trữ luôn là lãng phí"], 1), ("Tác giả đề xuất đánh giá thêm yếu tố nào?", ["Chỉ chi phí đơn vị", "Số giờ họp", "Thời gian phục hồi và sự phụ thuộc"], 2)],
        "task": "Tóm tắt lập luận trong 80–100 từ tiếng Việt, sau đó nêu một phản biện bằng tiếng Anh.",
    },
}

ENGLISH_EXTRA_READINGS = {
    "Pre-A1 · Khởi động": {
        "title": "Welcome to Green Cafe", "type": "Thông báo nhân viên",
        "paragraphs": ["Welcome to Green Cafe. Anna is your team leader. Your work starts at 7:30. Please wear a black shirt and bring your name card. The staff room is next to the kitchen. Lunch is at twelve. If you need help, ask Anna or Ben."],
        "translations": ["Chào mừng đến Green Cafe. Anna là trưởng nhóm của bạn. Công việc bắt đầu lúc 7 giờ 30. Vui lòng mặc áo đen và mang thẻ tên. Phòng nhân viên ở cạnh bếp. Bữa trưa lúc mười hai giờ. Nếu cần giúp đỡ, hãy hỏi Anna hoặc Ben."],
        "vocab": [("team leader", "trưởng nhóm"), ("staff room", "phòng nhân viên"), ("next to", "ở cạnh")],
        "questions": [("Who is the team leader?", ["Anna", "Ben", "Green"], 0), ("What should the worker wear?", ["A blue coat", "A black shirt", "A white hat"], 1)],
        "task": "Ghi lại giờ bắt đầu, trang phục và người có thể hỗ trợ.",
    },
    "A1 · Nền tảng": {
        "title": "Printer instructions", "type": "Hướng dẫn ngắn",
        "paragraphs": ["The new printer is in the copy room. First, put your paper in the top tray. Then, touch the screen and choose Copy or Print. Use the blue button to start. Please do not use the red button; it stops the machine. If there is a problem, call Tom at extension 214. The copy room closes at 6 p.m."],
        "translations": ["Máy in mới ở phòng sao chép. Trước tiên, đặt giấy vào khay trên. Sau đó chạm màn hình và chọn Sao chép hoặc In. Dùng nút màu xanh để bắt đầu. Vui lòng không dùng nút đỏ; nó dừng máy. Nếu có vấn đề, hãy gọi Tom theo số máy lẻ 214. Phòng sao chép đóng cửa lúc 6 giờ tối."],
        "vocab": [("top tray", "khay trên"), ("touch the screen", "chạm màn hình"), ("extension", "số máy lẻ")],
        "questions": [("Which button starts the printer?", ["Blue", "Red", "Black"], 0), ("Who helps with a problem?", ["Anna", "Tom", "The manager"], 1)],
        "task": "Dịch các bước theo đúng thứ tự và khoanh thông tin liên hệ hỗ trợ.",
    },
    "A2 · Giao tiếp chủ động": {
        "title": "Training room confirmation", "type": "Email xác nhận",
        "paragraphs": ["Hi Duy, I have booked the third-floor training room for Thursday from 1:30 to 4:00 p.m. It has space for thirty people, but there are only twenty-four chairs at the moment. Facilities will bring six more chairs before noon. The projector works, although you need to collect the remote control from reception. Tea and coffee will arrive at 2:30. Please send me the final participant list by Wednesday morning. Best, Hoa."],
        "translations": ["Chào Duy, tôi đã đặt phòng đào tạo tầng ba vào thứ Năm từ 1 giờ 30 đến 4 giờ chiều. Phòng đủ chỗ cho ba mươi người nhưng hiện chỉ có hai mươi bốn ghế. Bộ phận cơ sở vật chất sẽ mang thêm sáu ghế trước buổi trưa. Máy chiếu hoạt động, tuy nhiên bạn cần lấy điều khiển tại lễ tân. Trà và cà phê sẽ đến lúc 2 giờ 30. Vui lòng gửi danh sách người tham dự cuối cùng trước sáng thứ Tư. Thân, Hoa."],
        "vocab": [("facilities", "bộ phận cơ sở vật chất"), ("remote control", "điều khiển từ xa"), ("participant list", "danh sách người tham dự")],
        "questions": [("Where is the remote control?", ["In the room", "At reception", "With Facilities"], 1), ("When is the list due?", ["Wednesday morning", "Thursday noon", "Thursday afternoon"], 0)],
        "task": "Liệt kê việc Duy cần làm trước và trong buổi đào tạo.",
    },
    "B1 · Làm việc độc lập": {
        "title": "Feedback on the new booking system", "type": "Báo cáo khảo sát ngắn",
        "paragraphs": ["Three months after the new booking system was introduced, 72 per cent of employees say that reserving a meeting room is faster. Double bookings have almost disappeared, and reception receives fewer calls. However, staff in the design department report that the mobile page is difficult to use because room photographs load slowly. Several employees also want a feature that automatically releases a room when the organiser cancels a meeting. The IT team will improve mobile performance this month and test automatic cancellation with two departments before making it available to everyone."],
        "translations": ["Ba tháng sau khi hệ thống đặt phòng mới được giới thiệu, 72% nhân viên cho rằng việc đặt phòng họp nhanh hơn. Tình trạng đặt trùng gần như biến mất và lễ tân nhận ít cuộc gọi hơn. Tuy nhiên, nhân viên phòng thiết kế cho biết trang di động khó dùng vì ảnh phòng tải chậm. Một số người cũng muốn tính năng tự giải phóng phòng khi người tổ chức hủy họp. Nhóm IT sẽ cải thiện hiệu suất di động trong tháng này và thử nghiệm chức năng hủy tự động với hai phòng ban trước khi mở cho tất cả mọi người."],
        "vocab": [("double booking", "đặt trùng lịch"), ("release a room", "giải phóng phòng đã đặt"), ("make available", "đưa vào sử dụng")],
        "questions": [("What problem has nearly disappeared?", ["Slow photographs", "Double bookings", "Cancelled meetings"], 1), ("What will IT test first?", ["Automatic cancellation", "A new reception desk", "More photographs"], 0)],
        "task": "Tóm tắt thành công, vấn đề còn lại và hành động tiếp theo.",
    },
    "B2 · Chuyên nghiệp": {
        "title": "Proposal to centralise purchasing", "type": "Đề xuất nội bộ",
        "paragraphs": ["The finance team has proposed that all equipment purchases be handled by a central unit. Supporters argue that combining orders would strengthen the company's negotiating position and reduce inconsistent pricing. A single approval process could also make spending easier to track. Department managers, however, are concerned that urgent requests may be delayed and that a central team may not understand specialist requirements. The proposal therefore recommends a standard route for routine purchases and an exception process for time-sensitive or technical items. Before approving the change, the board has requested a three-month pilot involving Finance, Marketing and Engineering."],
        "translations": ["Nhóm tài chính đề xuất để một đơn vị trung tâm xử lý toàn bộ việc mua thiết bị. Người ủng hộ cho rằng gộp đơn hàng sẽ tăng vị thế đàm phán và giảm giá không nhất quán. Một quy trình phê duyệt chung cũng giúp theo dõi chi tiêu dễ hơn. Tuy nhiên, quản lý các phòng ban lo yêu cầu khẩn cấp bị chậm và nhóm trung tâm không hiểu nhu cầu chuyên môn. Vì vậy, đề xuất đưa ra quy trình chuẩn cho mua sắm thường lệ và quy trình ngoại lệ cho mặt hàng khẩn cấp hoặc kỹ thuật. Trước khi phê duyệt, hội đồng yêu cầu thử nghiệm ba tháng với Tài chính, Marketing và Kỹ thuật."],
        "vocab": [("centralise", "tập trung hóa"), ("negotiating position", "vị thế đàm phán"), ("exception process", "quy trình ngoại lệ")],
        "questions": [("Why do supporters want combined orders?", ["To improve negotiation", "To hire managers", "To avoid tracking spending"], 0), ("What happens before approval?", ["A company-wide launch", "A three-department pilot", "An engineering purchase"], 1)],
        "task": "Phân loại lợi ích, rủi ro và biện pháp giảm rủi ro của đề xuất.",
    },
    "C1 · Dẫn dắt": {
        "title": "The hidden cost of constant availability", "type": "Bình luận về chính sách làm việc",
        "paragraphs": ["Digital communication has made collaboration faster, but it has also blurred the distinction between responsiveness and permanent availability. When every message appears urgent, employees interrupt demanding work to demonstrate commitment rather than to solve genuinely time-sensitive problems. The immediate cost is fragmented attention; the longer-term cost is a culture in which careful thought seems less valuable than visible activity. A useful communication policy should therefore define response windows, escalation routes and periods in which colleagues are not expected to monitor messages. Such boundaries do not weaken collaboration. On the contrary, they make urgent channels more credible while protecting the concentration required for complex decisions."],
        "translations": ["Giao tiếp số giúp cộng tác nhanh hơn nhưng cũng làm mờ ranh giới giữa phản hồi kịp thời và luôn luôn sẵn sàng. Khi mọi tin nhắn đều có vẻ khẩn cấp, nhân viên ngắt công việc khó để thể hiện sự tận tâm thay vì giải quyết vấn đề thật sự gấp. Chi phí tức thời là sự chú ý bị phân mảnh; chi phí dài hạn là văn hóa coi hoạt động hữu hình quan trọng hơn suy nghĩ cẩn trọng. Vì vậy, chính sách giao tiếp hữu ích cần xác định thời hạn phản hồi, tuyến xử lý khẩn và thời gian đồng nghiệp không phải theo dõi tin nhắn. Ranh giới như vậy không làm yếu hợp tác mà khiến kênh khẩn cấp đáng tin hơn và bảo vệ sự tập trung cần cho quyết định phức tạp."],
        "vocab": [("blur the distinction", "làm mờ sự phân biệt"), ("fragmented attention", "sự chú ý bị phân mảnh"), ("escalation route", "tuyến xử lý nâng cấp/khẩn cấp")],
        "questions": [("What contrast does the writer make?", ["Speed versus salary", "Responsiveness versus permanent availability", "Office versus remote work"], 1), ("Why define quiet periods?", ["To protect concentration", "To remove collaboration", "To delay every response"], 0)],
        "task": "Tóm tắt lập luận, tiền đề ngầm và khuyến nghị chính sách của tác giả.",
    },
}

GRAMMAR_CLOZE = {
    "Pre-A1 · Khởi động": {
        "text": "Hello, I ___ (1) Linh. I ___ (2) in the service team. My desk ___ (3) near the door.",
        "items": [("am", ["am", "is", "are"], "Chủ ngữ I đi với am."), ("work", ["works", "work", "working"], "Hiện tại đơn với I dùng động từ nguyên mẫu."), ("is", ["am", "are", "is"], "Chủ ngữ số ít My desk đi với is.")],
    },
    "A1 · Nền tảng": {
        "text": "The office ___ (1) at eight every day. Nina usually ___ (2) the first customer emails. She can ___ (3) simple requests without a manager.",
        "items": [("opens", ["open", "opens", "opening"], "The office là chủ ngữ số ít nên động từ thêm -s."), ("answers", ["answer", "answers", "answered"], "Usually chỉ thói quen; Nina là ngôi thứ ba số ít."), ("handle", ["handles", "handled", "handle"], "Sau can dùng động từ nguyên mẫu không to.")],
    },
    "A2 · Giao tiếp chủ động": {
        "text": "We ___ (1) the order yesterday, but the customer has not received it. I ___ (2) the courier this morning, and they said they ___ (3) deliver it tomorrow.",
        "items": [("sent", ["send", "sent", "have sent"], "Yesterday yêu cầu quá khứ đơn: sent."), ("called", ["call", "called", "am calling"], "This morning ở đây là thời điểm đã kết thúc trong mạch kể quá khứ."), ("would", ["will", "would", "are"], "Trong lời nói gián tiếp sau said, will thường lùi thành would.")],
    },
    "B1 · Làm việc độc lập": {
        "text": "The team ___ (1) three options so far. If the client ___ (2) the revised plan today, we ___ (3) the first phase on Monday.",
        "items": [("has tested", ["tested", "has tested", "tests"], "So far thường đi với hiện tại hoàn thành."), ("approves", ["will approve", "approves", "approved"], "Mệnh đề if loại 1 dùng hiện tại đơn, không dùng will."), ("will start", ["start", "started", "will start"], "Mệnh đề chính của điều kiện loại 1 dùng will + V.")],
    },
    "B2 · Chuyên nghiệp": {
        "text": "The proposal ___ (1) by the board last week. If the risks had been explained more clearly, managers ___ (2) fewer objections. The revised plan ___ (3) be more practical, although further testing is required.",
        "items": [("was reviewed", ["reviewed", "was reviewed", "has reviewing"], "Nhấn đối tượng chịu tác động trong quá khứ: was + V3."), ("might have raised", ["might raise", "might have raised", "will raise"], "Giả định trái quá khứ dùng modal + have + V3 ở mệnh đề kết quả."), ("may", ["must", "may", "did"], "May thể hiện nhận định thận trọng khi chưa đủ dữ liệu." )],
    },
    "C1 · Dẫn dắt": {
        "text": "Rarely ___ (1) the organisation faced such rapid change. The review recommends ___ (2) decision-making rather than merely adding controls. Had earlier warnings been considered, the disruption ___ (3) significantly reduced.",
        "items": [("has", ["the organisation has", "has", "did the organisation"], "Sau trạng từ phủ định Rarely ở đầu câu, đảo trợ động từ trước chủ ngữ."), ("strengthening", ["strengthen", "strengthening", "to strengthening"], "Recommend có thể đi với V-ing khi nói chung về hành động."), ("could have been", ["could be", "could have been", "will have"], "Đảo ngữ Had... diễn tả điều kiện trái quá khứ; kết quả dùng could have been + V3.")],
    },
}

VSTEP_FORMAT = [
    ("🎧", "Listening", "~40 phút", "3 phần · 35 câu", "Ý chính, chi tiết, mục đích, thái độ và suy luận"),
    ("📖", "Reading", "60 phút", "4 bài · 40 câu", "Ý chính, chi tiết, thái độ, suy luận và từ trong ngữ cảnh"),
    ("✍️", "Writing", "60 phút", "Email ~120 từ + Essay ~250 từ", "Task 1 chiếm 1/3; Task 2 chiếm 2/3 điểm Viết"),
    ("🎙️", "Speaking", "12 phút", "3 phần", "Tương tác xã hội · chọn giải pháp · phát triển chủ đề"),
]

VSTEP_8_WEEK_PLAN = [
    ("Tuần 1", "Chẩn đoán & dựng nền", ["Làm mini-test 4 kỹ năng", "Ôn thì cơ bản, câu đơn–ghép", "Lập sổ lỗi sai", "Nói Part 1: bản thân, học tập, công việc"]),
    ("Tuần 2", "Đọc nhanh & nghe thông tin", ["Reading: main idea + scan chi tiết", "Listening: đoạn ngắn/thông báo", "Học 15 cụm từ theo 3 chủ đề", "Viết email hỏi và cung cấp thông tin"]),
    ("Tuần 3", "Suy luận & từ trong ngữ cảnh", ["Reading: reference, inference, vocabulary", "Listening: mục đích và thái độ", "Ôn từ nối và mệnh đề quan hệ", "Speaking Part 1 dưới áp lực thời gian"]),
    ("Tuần 4", "Writing Task 1 & Speaking Part 2", ["Viết email đủ mở–thân–kết trong 20 phút", "Chọn giải pháp và bác bỏ 2 phương án", "Sửa lỗi chia thì, mạo từ, số ít/nhiều", "Làm 1 bài Reading 40 câu có bấm giờ"]),
    ("Tuần 5", "Writing Task 2 nền tảng", ["Lập dàn ý opinion/discussion essay", "Viết introduction + 2 body paragraphs", "Nghe hội thoại dài và ghi keyword", "Speaking Part 3 theo khung PREP"]),
    ("Tuần 6", "Tăng tốc & liên kết ý", ["Essay 250 từ trong 40 phút", "Reading 4 bài trong 60 phút", "Listening 35 câu gần đủ format", "Nói liền mạch 3–4 phút"]),
    ("Tuần 7", "Thi thử & vá điểm yếu", ["Làm 2 đề mô phỏng đủ 4 kỹ năng", "Phân loại lỗi: kiến thức/kỹ thuật/thời gian", "Viết lại 2 bài yếu nhất", "Ghi âm và tự chấm 3 bài Speaking"]),
    ("Tuần 8", "Ổn định phong độ", ["Làm 1 đề cuối tuần ở đầu tuần", "Ôn sổ lỗi và cụm diễn đạt", "Luyện chiến thuật bỏ qua–quay lại", "Hai ngày cuối giảm tải và ngủ đủ"]),
]

VSTEP_DAILY_TOPICS = [
    ["Chẩn đoán 4 kỹ năng", "Thì hiện tại & quá khứ", "Đọc ý chính", "Nghe thông báo ngắn", "Email giới thiệu", "Speaking Part 1", "Ôn tuần & mini-test"],
    ["Nghe giờ–địa điểm", "Scan tên và số liệu", "Từ vựng giáo dục", "Email hỏi thông tin", "Nghe hướng dẫn", "Nói về công việc", "Mini-test tuần 2"],
    ["Từ vựng trong ngữ cảnh", "Đại từ tham chiếu", "Nghe mục đích người nói", "Mệnh đề quan hệ", "Đọc suy luận", "Speaking Part 1 bấm giờ", "Mini-test tuần 3"],
    ["Cấu trúc email 120 từ", "Email yêu cầu", "Email phàn nàn", "Speaking Part 2: chọn giải pháp", "Bác bỏ hai phương án", "Reading 40 câu bấm giờ", "Viết lại & sửa lỗi"],
    ["Cấu trúc essay 250 từ", "Viết mở bài", "Đoạn thân bài PEEL", "Nghe hội thoại dài", "Speaking Part 3 theo PREP", "Viết essay đầu tiên", "Chấm và viết lại"],
    ["Từ nối & liên kết", "Essay opinion", "Reading 60 phút", "Listening 35 câu", "Nói liền mạch 3 phút", "Mô phỏng Writing", "Phân tích lỗi tuần 6"],
    ["Mock test 1: Listening", "Mock test 1: Reading", "Mock test 1: Writing", "Mock test 1: Speaking", "Vá kỹ năng yếu nhất", "Mock test 2 rút gọn", "So sánh hai lần thi"],
    ["Ôn sổ lỗi", "Ôn cụm diễn đạt", "Đề tổng duyệt", "Sửa đề tổng duyệt", "Chiến thuật phòng thi", "Ôn nhẹ & Speaking", "Day 56: sẵn sàng thi"],
]

VSTEP_DAY_SKILLS = ["Tổng hợp", "Grammar", "Reading", "Listening", "Writing", "Speaking", "Review"]

VSTEP_WEEK_MATERIALS = {
    1: ("Grammar for VSTEP", "Ôn các thì, cấu trúc câu và ghi lỗi ngữ pháp thường gặp."),
    2: ("1000 từ vựng tiếng Anh theo chủ đề", "Chọn từ đúng chủ đề đang học; ưu tiên cụm từ và câu ví dụ."),
    3: ("Tài liệu Speaking VSTEP", "Luyện Part 1 và xây khung trả lời tự nhiên, không học thuộc cả đoạn."),
    4: ("Bộ đề VSTEP 1", "Làm Writing Task 1 và Speaking Part 2; đối chiếu bài mẫu sau khi tự làm."),
    5: ("Bộ đề VSTEP 2", "Làm Writing Task 2 và Speaking Part 3; phân tích cách triển khai ý."),
    6: ("Bộ đề VSTEP 3", "Làm Reading và Listening đúng thời gian; ghi bằng chứng cho câu sai."),
    7: ("Bộ đề VSTEP 4", "Thi thử đủ bốn kỹ năng và lập bảng lỗi theo nguyên nhân."),
    8: ("Bộ đề VSTEP 5", "Tổng duyệt như thi thật; chỉ xem đáp án sau khi hoàn thành toàn bộ."),
}

VSTEP_EMBEDDED_MATERIALS = {
    1: {
        "title": "Ngữ pháp nền B1",
        "sections": [
            ("Thì trong bài thi", "Present simple cho sự thật/thói quen; past simple cho sự việc đã kết thúc; present perfect cho trải nghiệm hoặc kết quả còn liên quan hiện tại."),
            ("Câu điều kiện loại 1", "If + present simple, will/can + V. Không dùng will trong mệnh đề if."),
            ("Mệnh đề quan hệ", "who cho người; which cho vật; that có thể thay who/which trong mệnh đề xác định."),
            ("Bị động", "be + past participle; chia động từ be theo đúng thì và dùng khi hành động/kết quả quan trọng hơn người thực hiện."),
        ],
    },
    2: {
        "title": "Từ vựng theo chủ đề B1",
        "sections": [
            ("Education", "assignment · attend · improve · qualification · practical experience"),
            ("Work", "apply for · colleague · deadline · responsibility · working conditions"),
            ("Environment", "public transport · reduce waste · protect resources · pollution · sustainable"),
            ("Health & lifestyle", "balanced diet · regular exercise · mental health · prevent · recover"),
        ],
    },
    3: {
        "title": "Speaking VSTEP Part 1–3",
        "sections": [
            ("Part 1 · Social interaction", "Answer → Reason → Example. Trả lời trực tiếp, sau đó thêm lý do và một chi tiết cá nhân."),
            ("Part 2 · Solution discussion", "Choose one option → give two reasons → reject option 2 → reject option 3 → conclude."),
            ("Part 3 · Topic development", "Point → Reason → Example → Point. Phát triển 2–3 ý và chuẩn bị câu hỏi mở rộng."),
            ("Cụm cứu nguy", "In my opinion… · The main reason is… · For example… · Compared with… · To sum up…"),
        ],
    },
    4: {
        "title": "Bộ đề 1 · Email & chọn giải pháp",
        "sections": [("Writing Task 1", "Email cho bạn sắp đến thành phố: phương tiện, nơi ở, hai địa điểm và một câu hỏi."), ("Speaking Part 2", "Chọn hoạt động cuối tuần: picnic, bảo tàng hoặc tình nguyện; bác bỏ hai lựa chọn còn lại."), ("Mục tiêu", "Viết khoảng 120 từ trong 20 phút; nói 2–3 phút sau 1 phút chuẩn bị.")],
    },
    5: {
        "title": "Bộ đề 2 · Essay & phát triển chủ đề",
        "sections": [("Writing Task 2", "Some people think university students should have part-time jobs. Discuss the benefits and drawbacks and give your opinion."), ("Speaking Part 3", "Topic: The benefits of learning a foreign language—work, travel, knowledge and your own idea."), ("Mục tiêu", "Essay khoảng 250 từ; mỗi đoạn thân bài có câu chủ đề, giải thích và ví dụ.")],
    },
    6: {
        "title": "Bộ đề 3 · Reading & Listening bấm giờ",
        "sections": [("Reading", "4 passages/40 questions/60 minutes: main idea, detail, inference, attitude and vocabulary in context."), ("Listening", "3 parts/35 questions/~40 minutes: short exchanges, conversations and talks."), ("Mục tiêu", "Ghi bằng chứng cho từng câu sai và phân biệt lỗi nghe/đọc với lỗi quản lý thời gian.")],
    },
    7: {
        "title": "Bộ đề 4 · Mock test đủ kỹ năng",
        "sections": [("Buổi 1", "Listening + Reading đúng thời gian, không dừng đồng hồ."), ("Buổi 2", "Writing 60 phút: Task 1 tối đa 20 phút, Task 2 khoảng 40 phút."), ("Buổi 3", "Speaking 12 phút; ghi âm và tự chấm độ trôi chảy, từ vựng, ngữ pháp, phát âm.")],
    },
    8: {
        "title": "Bộ đề 5 · Tổng duyệt",
        "sections": [("Thi như thật", "Làm đủ 4 kỹ năng trong điều kiện ít gián đoạn nhất có thể."), ("Chữa đề", "Chỉ xem đáp án sau khi hoàn thành; viết lý do cho mọi câu sai."), ("Chốt chiến thuật", "Xác định thứ tự làm, mốc thời gian, mẫu dàn ý và cách xử lý khi bỏ lỡ một câu nghe.")],
    },
}


def _build_vstep_days():
    days = []
    for week_index, topics in enumerate(VSTEP_DAILY_TOPICS, 1):
        for day_in_week, topic in enumerate(topics, 1):
            day_number = (week_index - 1) * 7 + day_in_week
            skill = VSTEP_DAY_SKILLS[day_in_week - 1]
            tasks = [
                f"Học trọng tâm: {topic}",
                f"Luyện {30 if week_index < 3 else 40 if week_index < 6 else 50} phút có bấm giờ",
                "Ghi ít nhất 3 lỗi/cụm mới vào sổ ôn tập",
            ]
            if skill == "Listening":
                practice = "Làm bài nghe 5 câu bên dưới: lượt 1 bắt ý chính, lượt 2 tìm bằng chứng."
            elif skill == "Reading":
                practice = "Làm bài đọc 5 câu bên dưới và gạch câu chứa bằng chứng cho từng đáp án."
            elif skill == "Writing":
                practice = "Viết theo đề bên dưới; dành 5 phút lập dàn ý và 5 phút cuối để soát lỗi."
            elif skill == "Speaking":
                practice = "Chuẩn bị 1 phút, nói 2–3 phút theo đề bên dưới và nghe lại bản ghi âm."
            elif skill == "Grammar":
                practice = "Ôn cấu trúc trong tab Ngữ pháp B1, sau đó tự viết 8 câu liên quan chủ đề hôm nay."
            elif skill == "Review":
                practice = "Làm lại các câu sai trong tuần mà không xem đáp án; chỉ kết thúc khi giải thích được lỗi."
            else:
                practice = "Làm mini-test mỗi kỹ năng 10–15 phút và ghi điểm ban đầu vào bảng theo dõi."
            days.append({"day": day_number, "week": week_index, "skill": skill, "topic": topic, "tasks": tasks, "practice": practice})
    return days


VSTEP_56_DAYS = _build_vstep_days()

VSTEP_PRACTICE = {
    "🎧 Listening": {
        "strategy": ["Đọc câu hỏi trước khi nghe", "Gạch từ phân biệt các lựa chọn", "Không dừng lại ở một câu đã lỡ", "Lượt nghe sau tập trung vào bằng chứng"],
        "task": "Nghe một thông báo 60–100 từ và ghi: người nói, mục đích, thời gian, hành động cần làm.",
    },
    "📖 Reading": {
        "strategy": ["Khoanh từ khóa trong câu hỏi", "Tìm đoạn chứa bằng chứng", "Phân biệt thông tin đúng với thông tin chỉ có vẻ liên quan", "Giới hạn khoảng 15 phút mỗi bài"],
        "task": "Đọc một bài B1 trong tab Đọc & Dịch; trả lời câu hỏi trước khi bật bản dịch và ghi bằng chứng cho từng đáp án.",
    },
    "✍️ Writing": {
        "strategy": ["Task 1: trả lời đủ mọi gạch đầu dòng", "Task 2: nêu quan điểm nhất quán", "Mỗi đoạn chỉ có một ý chính", "Dành 5 phút cuối kiểm tra động từ, số nhiều và chính tả"],
        "task": "Task 1: A friend will visit your city. Write about transport, accommodation and two places to visit (about 120 words).",
    },
    "🎙️ Speaking": {
        "strategy": ["Trả lời trực tiếp rồi mới giải thích", "Part 2: chọn một phương án và so sánh cả ba", "Part 3: dùng Point–Reason–Example–Point", "Nếu thiếu từ, diễn đạt lại thay vì im lặng"],
        "task": "Part 2: Your class wants a weekend activity. Choose the best option: a picnic, a museum visit, or volunteer work. Reject the other two options.",
    },
}

VSTEP_LISTENING_TEST = {
    "script": "Good morning, everyone. This is a reminder about Saturday's community clean-up. We will meet outside the public library at eight thirty, not at the town hall as stated in the first email. Gloves and rubbish bags will be provided, but please bring your own water and wear comfortable shoes. The activity should finish by eleven thirty. If heavy rain is expected, we will post a cancellation notice on the community website by seven o'clock that morning. Volunteers under sixteen must come with an adult.",
    "questions": [
        ("Where will the volunteers meet?", ["At the town hall", "Outside the public library", "On the community website"], 1, "The speaker corrects the first email and says they will meet outside the public library."),
        ("What should volunteers bring?", ["Gloves", "Rubbish bags", "Water"], 2, "Gloves and bags are provided; volunteers need to bring their own water."),
        ("When should the activity end?", ["7:00", "8:30", "11:30"], 2, "The announcement says the activity should finish by eleven thirty."),
        ("How will people learn about a cancellation?", ["Through the website", "By telephone", "At the library"], 0, "A notice will be posted on the community website."),
        ("Who must be accompanied by an adult?", ["New volunteers", "People under sixteen", "Library staff"], 1, "The final sentence states that volunteers under sixteen must come with an adult."),
    ],
}

VSTEP_READING_TEST = {
    "title": "Why a local library changed its opening hours",
    "passage": [
        "Last year, Westbridge Library noticed that fewer people were visiting on weekday mornings, while demand for evening study space had increased. Many local residents worked until five or six o'clock, and college students often needed a quiet place after their classes. The library therefore tested a new timetable for three months: it opened two hours later on Tuesdays and Thursdays but remained open until nine in the evening.",
        "The trial attracted 38 per cent more evening visitors without reducing the total number of weekly visits. Nevertheless, some retired residents objected because they had previously attended a Tuesday morning reading group. In response, the library moved that group to Wednesday and asked a nearby community centre to host an additional monthly session.",
        "Following the trial, the library made the later hours permanent. Its manager stressed that the decision was not simply about attracting larger numbers. The aim was to make limited staff time match the periods when the building was most useful. The library will review attendance again after six months and may extend the timetable to another weekday if sufficient demand exists.",
    ],
    "questions": [
        ("Why was the new timetable tested?", ["Morning visits were increasing", "More people needed evening access", "The library had hired more staff"], 1, "The first paragraph identifies increasing demand for evening study space."),
        ("What happened during the trial?", ["Weekly visits declined", "Evening attendance rose", "The reading group ended"], 1, "Evening visitors increased by 38%, while total weekly visits did not fall."),
        ("The word ‘objected’ is closest in meaning to…", ["disagreed", "forgot", "participated"], 0, "The retired residents opposed the change because it affected their group."),
        ("How did the library respond to retired residents?", ["It reopened every Tuesday morning", "It moved their group and added a monthly session", "It gave them access to staff offices"], 1, "Both actions are stated in the second paragraph."),
        ("What is the manager's main point?", ["Visitor numbers are the only measure", "Staff should work fewer hours", "Opening hours should match actual community need"], 2, "The manager focuses on using limited staff time when the building is most useful."),
    ],
}

VSTEP_WRITING_SAMPLE = "Dear Alex,\n\nI'm delighted that you're coming to visit my city next month. The easiest way to get around is by bus because it is inexpensive and most tourist attractions are near a bus stop. I suggest staying at the Riverside Hotel. It is reasonably priced and only a ten-minute walk from the city centre.\n\nYou should definitely visit the History Museum, where you can learn about the region, and the night market, which is famous for local food. Bring comfortable shoes because we will do quite a lot of walking. Please send me your arrival time when you book your ticket.\n\nBest wishes,\nMinh"

VSTEP_SPEAKING_SAMPLE = "I would choose volunteer work. First, it gives the whole class a clear purpose and allows us to help the local community. For example, we could clean a park or collect books for children. It is also inexpensive, so everyone can join. A picnic would be relaxing, but bad weather could ruin it and some students might not enjoy outdoor activities. A museum visit would be educational; however, tickets and transport may cost more. For these reasons, volunteer work is the most practical and meaningful option."

VSTEP_PRACTICE_SETS = {
    "listening": [
        VSTEP_LISTENING_TEST,
        {"script": "Attention passengers. The ten fifteen train to Brighton will leave from platform six instead of platform four. The train is delayed by approximately twenty minutes because of a technical problem. Passengers for Eastbourne should still use platform two. The cafe near platform five is closed today, but drinks and snacks are available from the shop beside the main entrance.",
         "questions": [("Which train is delayed?", ["Brighton", "Eastbourne", "London"], 0, "The announcement identifies the Brighton train."), ("Where will it leave from?", ["Platform 2", "Platform 4", "Platform 6"], 2, "It has moved from platform four to platform six."), ("How long is the delay?", ["10 minutes", "20 minutes", "50 minutes"], 1, "The delay is approximately twenty minutes."), ("Why is it delayed?", ["Bad weather", "A technical problem", "Staff illness"], 1, "A technical problem caused the delay."), ("Where can passengers buy drinks?", ["At the cafe", "Beside the main entrance", "On platform two"], 1, "The shop beside the main entrance is open.")]},
        {"script": "Hello Ms Tran, this is David from City Dental Clinic. I am calling about your appointment on Friday at two o'clock. Dr Lee will be attending a conference, so we need to move your appointment. We can see you at four thirty on Friday or at nine o'clock on Monday morning. Please call us before five today to confirm which time you prefer. Our telephone number is 0186 440 725.",
         "questions": [("Who is calling?", ["A conference organiser", "A clinic employee", "A patient"], 1, "David says he is calling from City Dental Clinic."), ("What was the original appointment time?", ["Friday at 2:00", "Friday at 4:30", "Monday at 9:00"], 0, "The original appointment was Friday at two."), ("Why must it change?", ["The clinic is closed", "The patient is away", "The doctor has a conference"], 2, "Dr Lee will attend a conference."), ("How many new times are offered?", ["One", "Two", "Three"], 1, "Friday 4:30 and Monday 9:00 are offered."), ("When should Ms Tran reply?", ["Before five today", "On Friday", "On Monday"], 0, "She is asked to call before five today.")]},
    ],
    "reading": [
        VSTEP_READING_TEST,
        {"title": "A workplace mentoring programme", "passage": ["A software company introduced a mentoring programme after a staff survey showed that new employees often felt uncertain during their first months. Each new employee was matched with an experienced colleague from a different team. The mentors did not evaluate performance; instead, they answered practical questions and helped newcomers understand how the company worked.", "After six months, new employees reported greater confidence and managers noticed that routine questions reached them less often. However, some mentors found it difficult to arrange meetings during busy periods. The company now gives mentors two hours of protected time each month and offers a short training session on giving useful feedback.", "The programme will continue for another year. Rather than expanding it immediately, the company plans to compare employee retention and satisfaction with figures from previous years."],
         "questions": [("Why was the programme introduced?", ["Managers requested promotion", "New staff lacked confidence", "The company hired fewer people"], 1, "The staff survey revealed uncertainty among new employees."), ("What did mentors NOT do?", ["Answer practical questions", "Explain company practices", "Evaluate performance"], 2, "The passage explicitly says mentors did not evaluate performance."), ("What benefit did managers notice?", ["They received fewer routine questions", "Meetings became longer", "Training costs disappeared"], 0, "Routine questions reached managers less often."), ("What problem did mentors experience?", ["Insufficient knowledge", "Difficulty scheduling meetings", "Negative evaluations"], 1, "Busy periods made meetings hard to arrange."), ("Why will the company wait before expanding?", ["To compare longer-term results", "To replace all mentors", "To reduce satisfaction"], 0, "It plans to compare retention and satisfaction figures.")]},
        {"title": "Repairing rather than replacing", "passage": ["Many household appliances are thrown away because a single part has failed. Repair cafes aim to change this pattern. At these community events, volunteers with practical skills help visitors examine broken items such as lamps, fans and small kitchen machines. Visitors remain involved in the repair, so they learn how the product works rather than simply receiving a free service.", "Not every item can be saved. Replacement parts may be unavailable, and some electrical repairs are unsafe without specialist equipment. Even so, organisers argue that an unsuccessful repair can still teach people why products fail and what to consider when buying a replacement.", "Several local councils now provide venues for repair cafes because the events reduce waste and encourage neighbours to share knowledge. Critics point out that volunteer events cannot replace professional repair businesses. Organisers agree, saying their goal is to make repair a normal first choice, not to compete with trained technicians."],
         "questions": [("What happens at a repair cafe?", ["Visitors buy new products", "Volunteers help examine broken items", "Factories sell spare parts"], 1, "Volunteers help visitors inspect and repair items."), ("Why do visitors stay involved?", ["To learn how products work", "To pay the volunteers", "To receive qualifications"], 0, "Participation helps them learn."), ("Why can some items not be repaired?", ["Events are too popular", "Parts or equipment may be unavailable", "Councils forbid repairs"], 1, "The second paragraph gives both reasons."), ("Why do councils support the events?", ["They create professional jobs", "They reduce waste and share knowledge", "They increase appliance sales"], 1, "These are the benefits named in paragraph three."), ("What is the organisers' goal?", ["Replace professional businesses", "Make repair the first option", "Offer every repair free"], 1, "They want repair to become a normal first choice.")]},
    ],
    "writing": [
        ("Task 1 · Course information", "You want to join an evening English course. Write an email asking about the timetable, class size, fees and learning materials.", "120 từ · 20 phút"),
        ("Task 1 · Complaint", "You stayed at a hotel and experienced two problems. Write to the manager describing the problems and stating what action you expect.", "120 từ · 20 phút"),
        ("Task 2 · Online learning", "Some people believe online learning is more effective than classroom learning. Discuss both views and give your opinion.", "250 từ · 40 phút"),
    ],
    "speaking": [
        ("Part 1 · Free time", "What do you usually do in your free time? Why? Do you prefer spending it alone or with friends?", "Trả lời 3 câu · 2 phút"),
        ("Part 2 · Travel", "Choose the best way for a class trip: coach, train or private cars. Explain your choice and reject the other options.", "Chuẩn bị 1 phút · nói 2–3 phút"),
        ("Part 3 · Exercise", "Develop the topic: Regular exercise is important. Discuss health, stress, social connection and your own idea.", "Chuẩn bị 1 phút · nói 3 phút"),
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


@st.cache_data
def load_english_resources():
    if not LANGUAGE_RESOURCES_PATH.exists():
        return []
    return json.loads(LANGUAGE_RESOURCES_PATH.read_text(encoding="utf-8")).get("Tiếng Anh", [])


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
        "Chương trình", ["🚀 Từ mất gốc đến công sở", "🎯 Ôn VSTEP B1", "⚡ Luyện tình huống", "🗂 Kho tiếng Anh", "🎓 Video IELTS tham khảo"],
        horizontal=True, key="english_program_mode",
    )
    if mode.startswith("🚀"):
        render_workplace_path()
    elif mode.startswith("🎯"):
        render_vstep_b1_path()
    elif mode.startswith("⚡"):
        render_quick_training()
    elif mode.startswith("🗂"):
        render_english_resource_library()
    else:
        render_full_course()


def render_vstep_b1_path():
    st.markdown("### Lộ trình ôn VSTEP B1 · 8 tuần")
    st.caption("Mục tiêu bậc 3: 4.0–5.5/10 · Khuyến nghị học 7–10 giờ/tuần")
    tab_daily, tab_format, tab_plan, tab_practice, tab_progress = st.tabs([
        "▶️ Học Day 1–56", "🧭 Cấu trúc đề", "📅 Tổng quan 8 tuần", "🧪 Luyện theo kỹ năng", "📊 Theo dõi tiến độ",
    ])

    with tab_daily:
        _render_vstep_daily_path()

    with tab_format:
        st.info("Mục tiêu an toàn nên đặt từ 5.0 thay vì chỉ chạm ngưỡng 4.0, để có khoảng đệm khi một kỹ năng làm chưa tốt.")
        columns = st.columns(2)
        for index, (icon, skill, duration, format_text, focus) in enumerate(VSTEP_FORMAT):
            columns[index % 2].markdown(
                f"<div style='min-height:165px;padding:16px;border:1px solid #bfdbfe;border-radius:15px;margin-bottom:10px'>"
                f"<div style='font-size:21px;font-weight:800;color:#1d4ed8'>{icon} {skill}</div>"
                f"<div style='font-weight:700;margin:6px 0'>{duration} · {format_text}</div>"
                f"<div style='color:#475569'>{focus}</div></div>", unsafe_allow_html=True,
            )
        st.warning("Điểm tổng là trung bình của 4 kỹ năng, làm tròn đến 0.5. Không nên bỏ hẳn một kỹ năng dù mục tiêu chỉ là B1.")

    with tab_plan:
        hours = st.select_slider("Thời gian học mỗi tuần", [5, 7, 10, 12, 15], value=10, format_func=lambda value: f"{value} giờ")
        st.caption(f"Gợi ý phân bổ: Listening {hours * 0.25:.1f}h · Reading {hours * 0.25:.1f}h · Writing {hours * 0.3:.1f}h · Speaking {hours * 0.2:.1f}h")
        for week_index, (week, focus, tasks) in enumerate(VSTEP_8_WEEK_PLAN, 1):
            with st.expander(f"{week} · {focus}", expanded=week_index == 1):
                completed = 0
                for task_index, task in enumerate(tasks):
                    completed += int(st.checkbox(task, key=f"vstep_week_{week_index}_{task_index}"))
                st.progress(completed / len(tasks), text=f"{completed}/{len(tasks)} nhiệm vụ")

    with tab_practice:
        selected_skill = st.radio("Kỹ năng", list(VSTEP_PRACTICE), horizontal=True, key="vstep_practice_skill")
        content = VSTEP_PRACTICE[selected_skill]
        st.markdown("#### Chiến thuật")
        for item in content["strategy"]:
            st.markdown(f"- {item}")
        _render_vstep_skill_practice(selected_skill)

    with tab_progress:
        st.markdown("#### Chẩn đoán nhanh hiện tại")
        scores = {}
        columns = st.columns(2)
        for index, skill in enumerate(["Listening", "Reading", "Writing", "Speaking"]):
            scores[skill] = columns[index % 2].slider(skill, 0.0, 10.0, 4.0, 0.5, key=f"vstep_score_{skill}")
        average = sum(scores.values()) / len(scores)
        weakest = min(scores, key=scores.get)
        st.metric("Điểm trung bình tự đánh giá", f"{average:.1f}/10")
        st.progress(min(average / 10, 1.0), text=f"Kỹ năng cần ưu tiên: {weakest} ({scores[weakest]:.1f})")
        if average < 4:
            st.warning("Chưa đạt ngưỡng B1 mô phỏng. Dành 40% thời gian tuần tới cho kỹ năng yếu nhất.")
        elif average < 5:
            st.info("Đã gần/đạt ngưỡng nhưng khoảng đệm còn thấp. Mục tiêu tiếp theo: duy trì trung bình từ 5.0.")
        else:
            st.success("Đang có khoảng đệm tốt cho mục tiêu B1. Tiếp tục luyện đề có bấm giờ để ổn định phong độ.")

    with st.expander("Nguồn chính thức"):
        st.markdown("- [Định dạng đề thi VSTEP.3-5 – ULIS, ĐHQGHN](https://vstep.vnu.edu.vn/files/uploads/2020/12/Dinh-dang-VSTEP.3-5.pdf)")
        st.markdown("- [Bảng điểm và cấp độ VSTEP.3-5 – ULIS, ĐHQGHN](https://vstep.vnu.edu.vn/scores-levels/)")
        st.markdown(f"- [Kho tài liệu VSTEP cá nhân dùng để luyện đề]({VSTEP_DRIVE_FOLDER})")


def _change_vstep_day(delta):
    current = st.session_state.get("vstep_current_day", 1)
    st.session_state["vstep_current_day"] = max(1, min(56, current + delta))


def _complete_and_next_vstep_day():
    current = st.session_state.get("vstep_current_day", 1)
    st.session_state[f"vstep_day_complete_{current}"] = True
    st.session_state["vstep_current_day"] = min(56, current + 1)


def _change_practice_set(skill, delta):
    key = f"vstep_{skill}_set_index"
    count = len(VSTEP_PRACTICE_SETS[skill])
    st.session_state[key] = (st.session_state.get(key, 0) + delta) % count


def _render_vstep_skill_practice(selected_skill):
    skill = "listening" if selected_skill.startswith("🎧") else "reading" if selected_skill.startswith("📖") else "writing" if selected_skill.startswith("✍️") else "speaking"
    sets = VSTEP_PRACTICE_SETS[skill]
    key = f"vstep_{skill}_set_index"
    index = st.session_state.get(key, 0) % len(sets)
    previous, label, following = st.columns([1, 2, 1])
    previous.button("← Bài trước", on_click=_change_practice_set, args=(skill, -1), key=f"vstep_{skill}_previous", use_container_width=True)
    label.markdown(f"<div style='text-align:center;font-weight:800;padding:9px'>Bài {index + 1}/{len(sets)}</div>", unsafe_allow_html=True)
    following.button("Bài tiếp →", on_click=_change_practice_set, args=(skill, 1), key=f"vstep_{skill}_next", use_container_width=True)
    if skill in ("listening", "reading"):
        _render_vstep_objective_test(skill, sets[index], key_suffix=f"skill_{index}")
    elif skill == "writing":
        title, prompt, timing = sets[index]
        _render_vstep_writing_test(key_suffix=f"skill_{index}", title=title, prompt=prompt, timing=timing)
    else:
        title, prompt, timing = sets[index]
        _render_vstep_speaking_test(key_suffix=f"skill_{index}", title=title, prompt=prompt, timing=timing)


def _render_vstep_daily_path():
    completed_days = sum(bool(st.session_state.get(f"vstep_day_complete_{day}")) for day in range(1, 57))
    st.progress(completed_days / 56, text=f"Đã hoàn thành {completed_days}/56 ngày")

    week_filter = st.selectbox("Chọn tuần", range(1, 9), format_func=lambda value: f"Tuần {value}", key="vstep_daily_week")
    week_days = VSTEP_56_DAYS[(week_filter - 1) * 7:week_filter * 7]
    st.markdown("**Chọn ngày học:**")
    day_columns = st.columns(7)
    for column, item in zip(day_columns, week_days):
        done = bool(st.session_state.get(f"vstep_day_complete_{item['day']}"))
        if column.button(f"{'✅' if done else 'Day'} {item['day']}", key=f"vstep_pick_day_{item['day']}", use_container_width=True):
            st.session_state["vstep_current_day"] = item["day"]
            st.rerun()

    if "vstep_current_day" not in st.session_state:
        st.session_state["vstep_current_day"] = 1
    selected_day = st.selectbox(
        "Ngày đang học", range(1, 57),
        format_func=lambda value: f"Day {value} · Tuần {((value - 1) // 7) + 1} · {VSTEP_56_DAYS[value - 1]['topic']}",
        key="vstep_current_day",
    )
    lesson = VSTEP_56_DAYS[selected_day - 1]
    st.markdown(
        f"<div style='padding:18px;border-radius:16px;background:linear-gradient(135deg,#eff6ff,#ecfeff);border:1px solid #bfdbfe'>"
        f"<div style='font-size:13px;color:#2563eb;font-weight:800'>TUẦN {lesson['week']} · DAY {lesson['day']} · {lesson['skill'].upper()}</div>"
        f"<div style='font-size:25px;font-weight:850;margin-top:5px'>{html.escape(lesson['topic'])}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("#### Việc cần hoàn thành hôm nay")
    task_results = [
        st.checkbox(task, key=f"vstep_day_{selected_day}_task_{index}")
        for index, task in enumerate(lesson["tasks"])
    ]
    st.info(f"**Bài thực hành:** {lesson['practice']}")
    material_name, material_use = VSTEP_WEEK_MATERIALS[lesson["week"]]
    with st.expander(f"📚 Tài liệu sát đề tuần này · {material_name}", expanded=selected_day % 7 == 1):
        st.write(material_use)
        embedded = VSTEP_EMBEDDED_MATERIALS[lesson["week"]]
        st.markdown(f"#### {embedded['title']}")
        for heading, body in embedded["sections"]:
            st.markdown(f"**{heading}**  \n{body}")
        if lesson["week"] == 1 and lesson["skill"] == "Grammar":
            st.markdown("**Kiểm tra nhanh:** If the weather ___ good tomorrow, we will go out.")
            grammar_answer = st.radio("Chọn đáp án", ["is", "will be", "was"], index=None, key=f"vstep_embedded_grammar_{selected_day}")
            if grammar_answer:
                if grammar_answer == "is":
                    st.success("Đúng. Điều kiện loại 1 dùng hiện tại đơn trong mệnh đề if.")
                else:
                    st.error("Đáp án là ‘is’: If + present simple, will + V.")
        elif lesson["week"] == 2:
            st.text_input("Viết một câu dùng ít nhất 2 cụm từ phía trên", key=f"vstep_embedded_vocab_{selected_day}")
        elif lesson["week"] == 3:
            st.text_area("Soạn câu trả lời theo khung phù hợp", key=f"vstep_embedded_speaking_{selected_day}", height=100)
        elif lesson["week"] >= 4:
            st.warning("Làm bài trực tiếp phía dưới trước khi mở bài mẫu/đáp án. Không cần rời khỏi website.")

    set_index = (selected_day - 1) % 3
    if lesson["skill"] == "Listening":
        _render_vstep_objective_test("listening", VSTEP_PRACTICE_SETS["listening"][set_index], key_suffix=f"day_{selected_day}")
    elif lesson["skill"] == "Reading":
        _render_vstep_objective_test("reading", VSTEP_PRACTICE_SETS["reading"][set_index], key_suffix=f"day_{selected_day}")
    elif lesson["skill"] == "Writing":
        title, prompt, timing = VSTEP_PRACTICE_SETS["writing"][set_index]
        _render_vstep_writing_test(key_suffix=f"day_{selected_day}", title=title, prompt=prompt, timing=timing)
    elif lesson["skill"] == "Speaking":
        title, prompt, timing = VSTEP_PRACTICE_SETS["speaking"][set_index]
        _render_vstep_speaking_test(key_suffix=f"day_{selected_day}", title=title, prompt=prompt, timing=timing)
    elif lesson["skill"] == "Grammar":
        _render_grammar_cloze("B1 · Làm việc độc lập", key_suffix=f"day_{selected_day}")
    elif lesson["skill"] == "Tổng hợp":
        st.markdown("#### Mini-test chẩn đoán hôm nay")
        _render_vstep_objective_test("reading", VSTEP_PRACTICE_SETS["reading"][set_index], key_suffix=f"diagnostic_{selected_day}")
        title, prompt, timing = VSTEP_PRACTICE_SETS["speaking"][set_index]
        _render_vstep_speaking_test(key_suffix=f"diagnostic_{selected_day}", title=title, prompt=prompt, timing=timing)
    elif lesson["skill"] == "Review":
        st.markdown("#### Bài ôn cuối tuần")
        _render_grammar_cloze("B1 · Làm việc độc lập", key_suffix=f"review_{selected_day}")
        st.text_area("Viết lại 3 câu từng làm sai và giải thích quy tắc", key=f"vstep_review_errors_{selected_day}", height=130)
    else:
        st.text_area("Bài làm / sổ lỗi hôm nay", key=f"vstep_daily_notes_{selected_day}", height=150)

    previous, finish, following = st.columns([1, 2, 1])
    previous.button("← Day trước", disabled=selected_day == 1, on_click=_change_vstep_day, args=(-1,), use_container_width=True)
    finish.button(
        "✅ Hoàn thành & sang Day tiếp theo" if selected_day < 56 else "🏁 Hoàn thành lộ trình",
        on_click=_complete_and_next_vstep_day, use_container_width=True,
        type="primary", disabled=not all(task_results),
    )
    following.button("Day tiếp →", disabled=selected_day == 56, on_click=_change_vstep_day, args=(1,), use_container_width=True)
    if not all(task_results):
        st.caption("Hoàn thành ba mục checklist để mở nút chuyển sang ngày tiếp theo.")


def _render_vstep_objective_test(kind, test, key_suffix="skill"):
    st.markdown(f"#### Bài luyện {'Listening' if kind == 'listening' else 'Reading'} B1 · 5 câu")
    if kind == "listening":
        safe_script = html.escape(test["script"], quote=True)
        components.html(
            f"""<!doctype html><html><head><style>body{{margin:0;font-family:Arial}}button{{padding:10px 16px;border:0;border-radius:10px;background:#dbeafe;color:#1d4ed8;font-weight:700;cursor:pointer}}</style></head>
            <body><button id="play" data-text="{safe_script}">🔊 Phát bài nghe · giọng nữ chậm</button><script>
            {tts_speak_fn('en', .76)}
            document.getElementById('play').onclick=()=>speak(document.getElementById('play').dataset.text);</script></body></html>""",
            height=50,
        )
        st.caption("Nghe tối đa 2 lượt trước khi mở transcript.")
        with st.expander("Transcript · chỉ mở sau khi làm"):
            st.write(test["script"])
    else:
        st.markdown(f"**{test['title']}**")
        for paragraph in test["passage"]:
            st.markdown(paragraph)

    with st.form(f"vstep_{kind}_test_{key_suffix}"):
        answers = [
            st.radio(f"{index}. {question}", options, index=None, key=f"vstep_{kind}_{key_suffix}_q_{index}")
            for index, (question, options, _, _) in enumerate(test["questions"], 1)
        ]
        submitted = st.form_submit_button("Chấm bài và xem giải thích")
    if submitted:
        if any(answer is None for answer in answers):
            st.warning("Bạn cần trả lời đủ 5 câu trước khi chấm.")
        else:
            score = sum(answer == options[correct] for answer, (_, options, correct, _) in zip(answers, test["questions"]))
            st.success(f"Kết quả: {score}/5 câu đúng.")
            for index, (choice, (_, options, correct, explanation)) in enumerate(zip(answers, test["questions"]), 1):
                icon = "✅" if choice == options[correct] else "❌"
                st.markdown(f"{icon} **Câu {index}: {options[correct]}** — {explanation}")


def _render_vstep_writing_test(key_suffix="skill", title="Task 1 · Visit your city", prompt=None, timing="120 từ · 20 phút"):
    prompt = prompt or "A friend will visit your city. Write an email suggesting transport, accommodation and two places to visit. Ask for one piece of information about the trip."
    st.markdown(f"#### Writing {title}")
    st.info(prompt)
    answer = st.text_area("Viết bài tại đây", key=f"vstep_writing_task_1_{key_suffix}", height=260)
    word_count = len(answer.split())
    st.caption(f"Số từ hiện tại: {word_count} · Mục tiêu: {timing}")
    checks = [
        ("Có lời chào và câu kết phù hợp", "Dear/Hi… và Best wishes/Regards"),
        ("Đủ 4 ý nội dung", "transport · accommodation · two places · one question"),
        ("Có lý do hoặc ví dụ", "Không chỉ liệt kê; giải thích vì sao đề xuất phù hợp"),
        ("Đã kiểm tra ngôn ngữ", "thì, chia động từ, số nhiều, chính tả và dấu câu"),
    ]
    st.markdown("**Tự kiểm theo tiêu chí:**")
    for index, (label, help_text) in enumerate(checks):
        st.checkbox(label, help=help_text, key=f"vstep_writing_check_{key_suffix}_{index}")
    with st.expander("Gợi ý cấu trúc / bài mẫu"):
        if title.startswith("Task 1"):
            st.text(VSTEP_WRITING_SAMPLE)
            st.success("Bài mẫu trả lời đủ yêu cầu, tổ chức theo đoạn và dùng từ nối đơn giản. Hãy đối chiếu cấu trúc, không chép nguyên văn.")
        else:
            st.markdown("**Introduction:** paraphrase đề + nêu quan điểm.  \n**Body 1:** quan điểm/lợi ích thứ nhất + giải thích + ví dụ.  \n**Body 2:** quan điểm/hạn chế còn lại + giải thích + ví dụ.  \n**Conclusion:** tóm tắt và khẳng định lại quan điểm.")


def _render_vstep_speaking_test(key_suffix="skill", title="Part 2 · Thảo luận giải pháp", prompt=None, timing="Chuẩn bị 1 phút · nói 2–3 phút"):
    prompt = prompt or "Your class wants a weekend activity. Choose the best option: a picnic, a museum visit, or volunteer work. Explain your choice and reject the other two options."
    st.markdown(f"#### Speaking {title}")
    st.info(prompt)
    st.caption(timing)
    st.markdown("**Khung trả lời 2–3 phút:** lựa chọn → 2 lý do → ví dụ → hạn chế của phương án 2 → hạn chế của phương án 3 → kết luận.")
    st.text_area("Dàn ý nhanh trong 1 phút", key=f"vstep_speaking_outline_{key_suffix}", height=120)
    components.html(
        """<!doctype html><html><head><style>body{margin:0;font-family:Arial}.row{display:flex;gap:8px;align-items:center}button{padding:9px 14px;border:0;border-radius:9px;background:#ede9fe;color:#5b21b6;font-weight:700}#time{font-size:22px;font-weight:800}</style></head><body><div class='row'><button id='start'>⏱ Bắt đầu 3 phút</button><button id='reset'>Làm lại</button><span id='time'>03:00</span></div><script>let left=180,timer=null;const out=document.getElementById('time');function draw(){out.textContent=String(Math.floor(left/60)).padStart(2,'0')+':'+String(left%60).padStart(2,'0')}document.getElementById('start').onclick=()=>{if(timer)return;timer=setInterval(()=>{if(left>0){left--;draw()}else{clearInterval(timer);timer=null;out.textContent='HẾT GIỜ'}},1000)};document.getElementById('reset').onclick=()=>{clearInterval(timer);timer=null;left=180;draw()};</script></body></html>""",
        height=50,
    )
    st.caption("Bấm giờ rồi nói thành tiếng hoặc ghi âm bằng điện thoại để nghe lại.")
    with st.expander("Gợi ý triển khai / bài mẫu"):
        if title.startswith("Part 2"):
            st.write(VSTEP_SPEAKING_SAMPLE)
            st.success("Mẫu chọn rõ một phương án, nêu hai lợi ích, bác bỏ cả hai lựa chọn còn lại và kết luận nhất quán.")
        else:
            st.markdown("Dùng khung **Answer/Point → Reason → Example → Closing point**. Mỗi ý nên có ít nhất một lý do hoặc ví dụ cụ thể.")


def render_english_resource_library():
    resources = load_english_resources()
    st.markdown("### Kho tài liệu tiếng Anh mở rộng")
    st.caption(f"{len(resources)} nguồn duy nhất đã được lọc từ danh mục Drive; dùng làm nguồn bổ trợ, không thay thế lộ trình chính.")
    tags = sorted({tag for item in resources for tag in item["tags"]})
    levels = ["Tất cả", "Pre-A1", "A1", "A2", "B1", "B2", "C1"]
    col1, col2 = st.columns(2)
    level = col1.selectbox("Cấp độ", levels, key="english_resource_level")
    tag = col2.selectbox("Kỹ năng", ["Tất cả"] + tags, key="english_resource_tag")
    query = st.text_input("Tìm tài liệu", placeholder="Ví dụ: phát âm, IELTS, writing...", key="english_resource_query")

    def level_ok(item):
        return level == "Tất cả" or not item["levels"] or level in item["levels"]

    render_resource_results(
        resources, level_ok, tag, query,
        "Đang hiển thị 40 kết quả đầu. Hãy dùng bộ lọc hoặc tìm kiếm để thu hẹp danh sách.",
    )


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
        "Cách học", ["🧭 Lộ trình", "📚 Từ vựng", "🧠 Ngữ pháp", "📖 Đọc & Dịch", "✍️ Luyện 4 kỹ năng", "📅 Kế hoạch tuần"],
        horizontal=True, key="workplace_view",
    )
    if view.startswith("🧭"):
        _render_workplace_map(selected, data)
    elif view.startswith("📚"):
        _render_workplace_vocab(selected, data)
    elif view.startswith("🧠"):
        _render_grammar_map(selected)
    elif view.startswith("📖"):
        _render_reading_translation(selected)
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
        {tts_speak_fn('en', 0.72)}
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
    _render_grammar_cloze(level)


def _render_grammar_cloze(level, key_suffix="lesson"):
    exercise = GRAMMAR_CLOZE[level]
    st.markdown("### Bài tập điền đoạn văn · dạng TOEIC")
    st.caption("Đọc toàn đoạn trước, xác định thời gian–chủ ngữ–quan hệ giữa các câu rồi mới chọn đáp án.")
    st.markdown(
        f"<div style='font-size:18px;line-height:1.8;padding:17px 19px;background:#fffbeb;"
        f"border:1px solid #fde68a;border-radius:13px'>{html.escape(exercise['text'])}</div>",
        unsafe_allow_html=True,
    )
    with st.form(f"grammar_cloze_form_{level}_{key_suffix}"):
        answers = [
            st.radio(f"Ô ({index})", options, index=None, horizontal=True, key=f"grammar_cloze_{level}_{key_suffix}_{index}")
            for index, (_, options, _) in enumerate(exercise["items"], 1)
        ]
        submitted = st.form_submit_button("Chấm và xem giải thích")
    if submitted:
        if any(answer is None for answer in answers):
            st.warning("Bạn hãy điền đủ tất cả chỗ trống.")
            return
        score = sum(choice == answer for choice, (answer, _, _) in zip(answers, exercise["items"]))
        st.success(f"Kết quả: {score}/{len(exercise['items'])} câu đúng.")
        completed = exercise["text"]
        for index, (answer, _, _) in enumerate(exercise["items"], 1):
            completed = completed.replace(f"___ ({index})", f"**{answer}**")
        st.markdown("**Đoạn hoàn chỉnh:**")
        st.markdown(completed)
        for index, (choice, (answer, _, explanation)) in enumerate(zip(answers, exercise["items"]), 1):
            icon = "✅" if choice == answer else "❌"
            st.markdown(f"{icon} **Ô {index}: {answer}** — {explanation}")


def _render_reading_translation(level):
    lessons = [READING_PASSAGES[level], ENGLISH_EXTRA_READINGS[level]]
    selected_index = st.selectbox(
        "Chọn bài đọc", range(len(lessons)),
        format_func=lambda index: f"Bài {index + 1} · {lessons[index]['type']} · {lessons[index]['title']}",
        key=f"english_reading_lesson_{level}",
    )
    lesson = lessons[selected_index]
    lesson_key = f"{level}_{selected_index}"
    word_count = sum(len(paragraph.split()) for paragraph in lesson["paragraphs"])
    st.markdown(f"### {lesson['title']}")
    st.caption(f"Bài {selected_index + 1}/2 · {lesson['type']} · {level} · {word_count} từ · Theo mô tả năng lực CEFR")

    full_text = " ".join(lesson["paragraphs"])
    safe_text = html.escape(full_text, quote=True)
    rate = 0.62 if level.startswith(("Pre-A1", "A1")) else 0.68 if level.startswith("A2") else 0.75
    components.html(
        f"""<!doctype html><html><head><style>
        body{{margin:0;font-family:Arial,sans-serif}}button{{border:0;border-radius:10px;padding:9px 15px;
        background:#dbeafe;color:#1e40af;font-weight:700;cursor:pointer}}button.playing{{background:#2563eb;color:white}}
        </style></head><body><button id="read" data-text="{safe_text}">🔊 Giọng nữ · đọc chậm</button><script>
        {tts_speak_fn('en', rate)}
        const button=document.getElementById('read');button.onclick=()=>speak(button.dataset.text, button);
        </script></body></html>""", height=48,
    )

    show_translation = st.toggle("Hiện bản dịch sau từng đoạn", value=False, key=f"reading_translation_{lesson_key}")
    for index, (paragraph, translation) in enumerate(zip(lesson["paragraphs"], lesson["translations"]), 1):
        st.markdown(f"**Đoạn {index}**")
        st.markdown(
            f"<div style='font-size:18px;line-height:1.75;padding:16px 18px;background:#f8fafc;"
            f"border-left:5px solid #2563eb;border-radius:12px'>{html.escape(paragraph)}</div>",
            unsafe_allow_html=True,
        )
        if show_translation:
            st.info(translation)

    st.markdown("#### Từ khóa trong ngữ cảnh")
    columns = st.columns(2)
    for index, (word, meaning) in enumerate(lesson["vocab"]):
        columns[index % 2].markdown(f"- **{word}** — {meaning}")

    st.markdown("#### Đọc hiểu")
    answers = []
    for index, (question, options, _) in enumerate(lesson["questions"]):
        answers.append(st.radio(question, options, index=None, key=f"reading_question_{lesson_key}_{index}"))
    if st.button("Chấm phần đọc hiểu", key=f"reading_check_{lesson_key}"):
        if any(answer is None for answer in answers):
            st.warning("Bạn hãy trả lời đủ câu hỏi trước khi chấm.")
        else:
            score = sum(answer == options[correct] for answer, (_, options, correct) in zip(answers, lesson["questions"]))
            st.success(f"Bạn đúng {score}/{len(lesson['questions'])} câu.")

    st.markdown("#### Thực hành dịch")
    st.caption(lesson["task"])
    st.text_area("Bản dịch/tóm tắt của bạn", key=f"reading_work_{lesson_key}", height=150)
    with st.expander("Gợi ý quy trình dịch"):
        st.markdown("1. Đọc toàn đoạn để xác định mục đích.  \n2. Gạch chủ ngữ, động từ chính và từ nối.  \n3. Dịch theo ý của cả câu, tránh ghép nghĩa từng từ.  \n4. Bật bản dịch mẫu để đối chiếu sau khi đã tự làm.")


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
