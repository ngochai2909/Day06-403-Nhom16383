# Tài liệu Chuyển giao: Cấu trúc AI Crisis Copilot (Trip.com)

Tài liệu này dùng để lưu trữ lại toàn bộ **Scope, Logic, và Hướng dẫn** của bản Prototype mà chúng ta đã xây dựng. Hãy cung cấp file này cho bất kỳ công cụ AI (như ChatGPT, Claude, Cursor) hoặc Developer nào ở các phiên làm việc sau để họ nắm bắt bối cảnh ngay lập tức và tiến hành đấu nối API thật.

---

## 1. Tổng quan Sản phẩm (Product Overview)
- **Tên dự án:** AI Crisis Copilot (áp dụng trên nền tảng Trip.com).
- **Vấn đề giải quyết:** Xử lý khủng hoảng (vé bị hủy sát giờ bay do lỗi cổng thanh toán), ngăn chặn việc chatbot lặp lại văn mẫu xin lỗi gây ức chế.
- **Tính năng cốt lõi:** Quét ngầm log giao dịch (Context Payload) để tự đưa ra phán đoán, và biết tự động "nhường quyền" (Smart Handoff) cho nhân viên người thật khi gặp tình huống khẩn cấp hoặc không hiểu ý khách.

---

## 2. Thiết kế 4 Luồng Hành Vi (Four Paths Design)
Hệ thống AI tương lai CẦN tuân thủ chặt chẽ 4 luồng này thông qua Guardrails và System Prompt:

| Luồng (Path) | Cơ chế hoạt động trong thực tế (Cách code Backend) |
|:---|:---|
| **1. Happy Path** | **Input:** API Backend trả về `errorCode: "GATEWAY_TIMEOUT"`.<br>**Logic AI:** System prompt ép AI giải thích lỗi và gọi hàm `trigger_auto_refund()`. |
| **2. Low-confidence** | **Input:** API Backend trả về `errorCode: "UNKNOWN"`.<br>**Logic AI:** System prompt ra lệnh: "Khi thiếu thông tin, không được tự hoàn tiền". AI phải đưa ra 2 nút: Đổi chuyến bay hoặc Gọi CSKH. |
| **3. Failure** | **Input:** Điểm tự tin (Confidence Score) phân tích ý định tin nhắn của khách `< 0.5`. Khách đang cáu hoặc dùng từ lóng.<br>**Logic AI:** Bắt sự kiện fallback. Ép AI dừng chat, gọi hàm `bypass_to_human(priority="P0")`. |
| **4. Correction** | **Input:** User bấm nút "Sửa sai! Chuyến bay là hôm nay" trên UI.<br>**Logic AI:** Bắn một message ẩn (System message) vào phiên chat để sửa biến `Priority` từ P3 lên P0, AI tự động xin lỗi và thay đổi hành vi. |

---

## 3. Kiến trúc Đấu nối API (Dự kiến)

Để biến bản Prototype HTML/JS hiện tại thành sản phẩm chạy thật, chúng ta cần xây dựng mô hình sau:

### A. Context Payload (Dữ liệu truyền ngầm)
Khi mở chat, Client (App) không chỉ gọi API `/chat`, mà phải gửi kèm theo `Payload` chứa bệnh án của khách:
```json
{
  "user_id": "U12345",
  "flight_number": "VN123",
  "status": "CANCELLED",
  "error_reason": "GATEWAY_TIMEOUT",
  "time_to_departure_hours": 5
}
```

### B. System Prompt (Lời gọi LLM)
Tất cả các lệnh gọi tới OpenAI API (hoặc Claude) phải mang theo System Prompt được tinh chỉnh như sau:
```text
Bạn là AI Crisis Copilot của Trip.com. 
Nhiệm vụ: Giải quyết sự cố hủy vé của khách hàng một cách ngắn gọn, không văn mẫu.
Thông tin vé hiện tại: [Insert Payload ở đây].
Luật (Guardrails):
1. Nếu khách hàng dùng từ khóa khẩn cấp (cứu, gấp, sân bay) hoặc bạn không hiểu ý khách, hãy kích hoạt tool "call_human_agent".
2. Nếu nguyên nhân lỗi là do đối tác thanh toán, hãy xin lỗi và đề xuất hoàn tiền.
3. Nếu khách hàng sửa sai thông tin, hãy cập nhật lại độ ưu tiên và báo cho nhân viên thật.
```

### C. Function Calling / Tools
Cần trang bị cho LLM các công cụ (Function Calling) sau để nó tương tác với Frontend:
- `auto_refund(booking_id)`
- `call_human_agent(priority_level, reason)`
- `suggest_alternative_flight(booking_id)`

---

## 4. Tình trạng Hiện tại của Codebase (03-prototype)
- Giao diện được xây dựng bằng **Vanilla HTML/CSS/JS**.
- **style.css**: Giao diện Mobile-first, tông màu Trip.com, có hiệu ứng Glassmorphism và Typing Indicator.
- **app.js**: Hiện đang chứa Mock Data và luồng `switch-case` tương ứng với 4 Paths để Demo (Thông qua Dev Panel dropdown).
- **Mục tiêu tiếp theo:** Xóa các Mock Data trong `app.js` và thay bằng hàm `fetch()` gọi tới Backend Server (NodeJS/Python) nơi có chứa kết nối thực với LLM (OpenAI API).
