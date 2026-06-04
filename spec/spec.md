# SPEC sản phẩm — AI Crisis Copilot (Trip.com)

> **Nhóm 16383** · Track B — Travel & Hospitality · Ngày triển khai: **2026-06-01**
> Một trợ lý AI đứng cạnh khách Trip.com đúng lúc booking gặp sự cố: chẩn đoán nguyên nhân, giải thích minh bạch, và định tuyến xử lý đúng người (đổi chuyến · chuyển nhân viên hoàn tiền · cứu hộ khẩn cấp).

Tài liệu này phản ánh đúng prototype đã dựng trong [`../codebase/`](../codebase/).

---

## 1. Bằng chứng

Nhóm bắt đầu từ một quan sát của chính mình: khi một thành viên bị hủy đơn và mã giảm giá lỗi, gọi tổng đài ngoài giờ chỉ nhận được lời nhắn tự động "chờ đến sáng" — luồng hỗ trợ bị chặn hoàn toàn ngay lúc cần nhất. Để kiểm chứng đây không phải trường hợp cá biệt, nhóm rà soát các đánh giá 1★ công khai trên App Store của Trip.com.

Các review hội tụ về **bốn dạng sự cố** lặp đi lặp lại:

- **Hủy vé nhưng không hoàn tiền tự động** — khách đã thanh toán, dịch vụ bị hủy đột ngột, và không liên hệ được nhân viên để đòi lại tiền.
- **Lời hứa "24/7" sai sự thật** — khi phát sinh vấn đề, tổng đài lại báo chỉ làm việc đến 18:00.
- **Lỗi logic hệ thống** — mã giảm giá báo hết hạn dù chưa tới giờ; chính sách hành lý mập mờ khiến khách mất tiền thật.
- **Hoàn tiền bị giam quá lâu** — khách hủy nhầm nhưng tiền "mãi không thấy về", tổng đài đùn đẩy.

Đối chiếu với cách Agoda/Booking.com xử lý — họ có nút *Request Refund* tự duyệt khi lỗi thuộc đối tác và đường dây ưu tiên cho khách sắp khởi hành — nhóm thấy rõ khoảng trống của Trip.com nằm ở **khâu hồi phục sau sự cố**, không phải ở khâu đặt vé.

> **Điểm cần trung thực:** các nhận định trên dựa trên review công khai và trải nghiệm nhóm. Con số chi phí/độ trễ ở mục Feasibility là **ước lượng**, nhóm chưa đo thực tế trên tải lớn.

**Insight:** Thứ thật sự làm khách phẫn nộ không phải bản thân lỗi hệ thống, mà là **sự im lặng và câu trả lời văn mẫu của chatbot** ngay khoảnh khắc khủng hoảng — nó biến một lỗi kỹ thuật thành cảm giác *bị lừa và bị bỏ rơi*. Vậy nên cái khách cần không phải "đặt vé mượt hơn", mà là **một điểm tựa biết lắng nghe và hành động tức thì** khi mọi thứ đổ vỡ.

---

## 2. Lát cắt để build

Nhóm chỉ dựng đúng **một màn hình xử lý sự cố** — không đụng tới tìm vé, đặt phòng hay gợi ý du lịch. Lát cắt gói trong một câu:

> Khi một hành khách vừa nhận thông báo vé bị hủy/lỗi trừ tiền, họ mở Crisis Copilot, AI **đọc trạng thái giao dịch để chẩn đoán nguyên nhân**, rồi tùy mức độ chắc chắn mà **ra một quyết định**: đề xuất chuyến thay thế cho khách đổi, hoặc chuyển khách sang nhân viên thật để xử lý hoàn tiền — kèm một lời giải thích rõ ràng.

Phạm vi này đủ hẹp để demo trọn vẹn trong một ngày, nhưng đủ sâu để chứng minh được giá trị "hồi phục niềm tin".

---

## 3. AI Product Canvas

**Value.** Người dùng là khách Trip.com đang hoảng vì vé hỏng sát giờ. AI giải đúng điểm mà bot hiện tại làm tệ nhất: thay vì xin lỗi suông, nó nói được *vì sao* lỗi xảy ra và *làm gì tiếp theo* ngay trong vài giây.

**Trust.** Mỗi câu trả lời đều gắn với nguyên nhân cụ thể (lỗi cổng thanh toán, lỗi hãng bay, hay chưa rõ). Niềm tin được bảo vệ bằng ba lớp: AI nêu rõ nguồn lỗi; mọi hành động dính tiền đều hỏi xác nhận trước khi làm; và khách luôn có cửa thoát sang người thật chỉ bằng một từ "khẩn cấp".

**Feasibility.** Lõi AI chạy trên `gpt-4o-mini` với function-calling — chi phí ước tính dưới một cent mỗi lượt và độ trễ vài giây, đủ rẻ và nhanh cho kênh CSKH. Dữ liệu cần là trạng thái vé + log lỗi, được giả lập bằng mock data. Ngưỡng dừng nhóm tự đặt: nếu tỉ lệ AI chẩn đoán/định tuyến sai vượt mức chấp nhận, sẽ thu hẹp phạm vi tự quyết và để người duyệt nhiều hơn.

**Tín hiệu học.** Khi khách phản hồi rằng AI đánh giá sai (path Correction), hệ thống ghi lại tình huống đó như một tín hiệu để hiệu chỉnh tiêu chí mức độ khẩn cấp. Ở prototype, tín hiệu này được log lại — chưa đưa vào vòng học online.

---

## 4. Tăng năng lực hay tự động hóa

Nhóm chọn **tự động hóa có điều kiện (conditional automation)**. AI tự làm những phần an toàn — chẩn đoán nguyên nhân lỗi, giải thích cho khách, tìm và xác nhận đổi chuyến theo lựa chọn của khách. Nhưng có một ranh giới cứng: **mọi việc dính hoàn tiền đều do nhân viên thật xử lý, AI không tự trừ hay hoàn tiền.** Khi xác định vé đủ điều kiện hoàn, AI chỉ giải thích rồi chuyển khách (kèm toàn bộ ngữ cảnh) sang nhân viên để xử lý nhanh. Ra ngoài vùng an toàn — nguyên nhân mơ hồ, dữ liệu thiếu, hoặc có tranh chấp — AI hạ vai về mức *augment*: tổng hợp thông tin và bàn giao cho người quyết định.

Lý do của lựa chọn này rất thẳng: đây là **tiền bạc của khách**, sai thì hậu quả nặng và khó hoàn tác, nên ranh giới tự quyết của AI phải chặt. Con người giữ vai **Rescuer & Decider** ở mọi bước có rủi ro tài chính.

---

## 5. Bốn đường đi của trải nghiệm

Bốn đường đi không phải lý thuyết — mỗi đường gắn với một mã vé thật trong `mock_data.py` và được prototype thể hiện trực tiếp:

| Đường đi | Mã vé | Điều prototype chứng minh |
|----------|-------|---------------------------|
| **Thuận** | `BK-78901` | Lỗi hệ thống rõ → AI dịch mã lỗi kỹ thuật thành lời giải thích dễ hiểu, xác nhận vé đủ điều kiện hoàn tiền rồi chuyển nhân viên xử lý hoàn tiền nhanh (ưu tiên P2). |
| **Không chắc** | `BK-45678` | Nguyên nhân mơ hồ → AI **không tự kết luận**, mở hai hướng: gọi `find_alternative_flight` để đề xuất chuyến thay thế (khách chốt bằng `confirm_rebook`), hoặc chờ nhân viên. |
| **Bí / sai** | `BK-99999` | Không có log giao dịch → AI thừa nhận thiếu dữ liệu thay vì bịa, lắng nghe khách, rồi tạo ticket nối người thật. |
| **Khách sửa** | `BK-11111` | Hệ thống ghi sai ngày bay khiến AI gán nhầm ưu tiên thấp → khách đính chính → AI xin lỗi, nâng ưu tiên và escalate; tình huống được log lại. |

Ngoài 4 path lõi, prototype còn nạp thêm các booking "sạch" (đổi chuyến có phụ thu, có hoàn voucher, có phí dịch vụ) để luồng đổi vé trông thật khi demo.

**Lưới an toàn xuyên suốt:** ở bất kỳ đường nào, khi khách dùng từ khóa khẩn cấp ("khẩn cấp / sân bay / cứu / gấp / người thật / nhân viên"), AI dừng phân tích và đề xuất chuyển người thật mức **P0** ngay.

---

## 6. Những kiểu lỗi đáng lo nhất

**(1) AI chẩn đoán sai khiến khách không được cứu kịp — nguy hiểm nhất.** Tình huống xấu là khách bị hủy chuyến chỉ còn vài giờ trước khởi hành mà AI lại quy lỗi cho khách và không chuyển đúng hướng. Hậu quả: lỡ chuyến, thiệt hại có thể tới hàng chục triệu. Nhóm chặn bằng cơ chế bypass — bất cứ lúc nào khách thấy AI đi sai hướng, gõ "khẩn cấp" là được nối người thật ngay — và bằng nguyên tắc mọi việc hoàn tiền đều do nhân viên xử lý, AI không tự quyết chuyện tiền bạc.

**(2) AI xác nhận đổi chuyến sai.** Nếu AI gọi `confirm_rebook` khi khách chưa chốt rõ, khách có thể bị đổi sang chuyến không mong muốn (kèm phụ thu). Guardrail: chỉ `confirm_rebook` khi khách đã chọn `flight_id` cụ thể; còn việc hoàn tiền thì AI tuyệt đối không tự thực hiện.

**(3) AI trả lời lạc đề.** Khách (hoặc người thử nghịch) hỏi chuyện ngoài booking có thể kéo AI khỏi vai trò. Hàm `is_out_of_scope_message` lọc các câu hỏi kiến thức chung và kéo hội thoại về đúng vấn đề vé/chuyến bay.

---

## 7. Kế hoạch kiểm thử và bằng chứng demo

Để chứng minh khi đứng demo, nhóm chuẩn bị hai đầu vào đối lập:

- **Đầu vào thuận:** mã `BK-78901` — cho thấy AI chẩn đoán đúng và chuyển nhân viên xử lý hoàn tiền minh bạch, nhanh gọn.
- **Đầu vào gây nhiễu:** mã `BK-99999` (không có log) hoặc câu chứa "khẩn cấp" — cho thấy AI **không bịa**, biết lùi lại và chuyển người thật.

Bằng chứng giữ trong repo: ảnh chụp review thật trên App Store, system prompt và bộ tool trong `codebase/main.py`, 12 kịch bản dữ liệu trong `codebase/mock_data.py`, và video quay luồng failure do người phụ trách test thực hiện.

---

## 8. Phân công

| Thành viên | Mã HV | Phần phụ trách | Bằng chứng trong repo |
|-----------|-------|----------------|------------------------|
| Nguyễn Ngọc Hải | 2A202600614 | Nghiên cứu & bằng chứng | Ảnh chụp review + ghi chú phân tích painpoint |
| Phạm Văn Lợi | 2A202600784 | SPEC & system prompt | `spec/spec.md`, `codebase/main.py` (prompt) |
| Lê Xuân Tiến Đạt | 2A202600549 | Prototype (frontend + backend) | `codebase/` |
| Dương Quang Huy | 2A202600839 | Kiểm thử & failure path | Video luồng lỗi |
| Nguyễn Trường Giang | 2A202600624 | Kịch bản demo & repo | Repo nhóm, `spec/demo-slides.html` |

---

## Phụ lục — Công nghệ & cách chạy

| Thành phần | Lựa chọn |
|---|---|
| AI Model | OpenAI `gpt-4o-mini` (function/tool calling) |
| Backend | Python + FastAPI |
| Frontend | HTML + CSS + JavaScript (mobile-first) |
| Dữ liệu | Mock data — 12 kịch bản, 4 path lõi + các case đổi vé |

Hướng dẫn cài đặt và chạy chi tiết: [`../codebase/README.md`](../codebase/README.md).
