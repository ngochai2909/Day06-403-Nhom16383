# Synthesis & Decide — Track B: Travel & Hospitality

Tài liệu gạn lọc từ Evidence ra quyết định chốt Build Slice.

## 1. Gom evidence thành cụm

Từ các ảnh review 1 sao trên store, nhóm gom được các cụm vấn đề:
- **Hủy vé vô cớ:** Hệ thống tự động hủy đơn nhưng không hoàn tiền tự động.
- **Lời hứa ảo:** Ghi là hỗ trợ 24/7 nhưng khi có việc thì đùn đẩy, bắt đợi đến sáng.
- **Mập mờ chính sách:** Đổi vé xong mất hành lý ký gửi phải mua lại; mã giảm giá báo hết hạn lúc 00:01 phút.

## 2. Viết insight

```text
User của OTA (Online Travel Agency) không chỉ cần tính năng đặt vé ổn định (surface need).
Họ thật ra cần "một chiếc phao cứu sinh" tức thời khi xảy ra sự cố tài chính/lịch trình (deeper need),
vì loạt review chửi rủa "Lừa đảo" cho thấy khi lỗi xảy ra sát giờ khởi hành, sự im lặng hoặc trả lời theo văn mẫu của bot khiến họ hoảng loạn và mất hoàn toàn niềm tin.
```

## 3. Viết opportunity

```text
Cơ hội là dùng AI để phân tích log giao dịch và chẩn đoán lỗi ngay lập tức (automate hành động hẹp),
giúp user được giải thích minh bạch nguyên nhân sự cố và tự động bồi hoàn (kết quả),
trong khi vẫn kiểm soát rủi ro bằng cách tạo nút "Bypass" (bỏ qua bot) chuyển thẳng cho Human Agent đối với các case rắc rối chưa rõ nguyên nhân (failure/risk).
```

## 4. Chọn build slice (Sát hạch qua 5 câu hỏi)

| Câu hỏi | Trả lời & Đánh giá | Đạt |
|---|---|:---:|
| **User cụ thể chưa?** | Hành khách đang gặp lỗi thanh toán/bị hủy vé sát giờ bay. | ✅ |
| **Task đủ hẹp chưa?** | Chỉ làm đúng 1 màn hình popup/chat xử lý sự cố hoàn tiền. (Bỏ qua khâu search vé, book vé). | ✅ |
| **AI decision rõ chưa?** | AI đọc giao dịch $\rightarrow$ Dịch lỗi hệ thống thành ngôn ngữ người $\rightarrow$ Ra quyết định Auto-Refund hoặc Chuyển Agent. | ✅ |
| **Failure path rõ chưa?** | Nếu AI nhầm lỗi do người dùng $\rightarrow$ User gõ "Khẩn cấp" để bypass sang gọi Hotline. | ✅ |
| **Có evidence không?** | Có, 8 ảnh screenshot chửi "App lừa đảo, hủy vé không hoàn tiền" trên Store. | ✅ |

## 5. Quyết định: giữ, giảm scope, hay đổi hướng?

| Tình huống thực tế của nhóm | Quyết định |
|---|---|
| Ý tưởng ban đầu: Làm trợ lý ảo tư vấn du lịch từ A-Z. Quá rộng và dễ fail. | **Giảm scope & Đổi hướng**: Cắt xuống một flow hẹp nhất: Xử lý khủng hoảng (Crisis Copilot). |

## 6. Câu chốt cuối

```text
Dựa trên bằng chứng review 1 sao phẫn nộ từ App Store,
nhóm sẽ build tính năng "AI Crisis Copilot" (Xử lý khủng hoảng bồi hoàn),
cho hành khách bị hủy vé/lỗi thanh toán,
để giải quyết cảm giác bị lừa dối và bỏ rơi,
bằng cách AI chẩn đoán lỗi giao dịch để Auto-Refund,
và sẽ test failure path bằng cách cho user kích hoạt luồng "Khẩn cấp" gọi nhân viên thật.
```

## 7. Backlog (Không làm trong Day 06)

Những thứ **không build trong Day 06**:
- Không build màn hình trang chủ tìm vé, đặt phòng.
- Không làm AI gợi ý chỗ ăn chơi, lịch trình.
- Không làm hệ thống thanh toán thật (chỉ giả lập luồng đã thanh toán bị lỗi).
