# Thin SPEC — Track B: Travel & Hospitality (AI Crisis Copilot)

Đây là bản cam kết để sáng Day 06 nhóm build ngay.

## 1. Track, product/app và user

**Track:** B. Travel & Hospitality
**Product/app thật:** Trip.com (hoặc OTA tương tự)
**User cụ thể:** Khách hàng cá nhân vừa phát hiện hệ thống hủy vé/mã giảm giá bị lỗi sát giờ.
**Nhóm có phải user thật không?** Có thể không ở hoàn cảnh sát giờ bay, nhưng thành viên nhóm từng bị tự động hủy đơn/mã giảm giá lỗi mà không có cách liên hệ.

## 2. Evidence summary

| Evidence | Nguồn | User/pain nói lên điều gì? | SPEC phải đổi gì? |
|---|---|---|---|
| User gào thét vì bị "tự động hủy vé không hoàn tiền", "bảo 24/7 nhưng gọi lại bảo ngoài giờ" | App Store (Trip.com) | User mất quyền kiểm soát (loss of agency). Sự giận dữ đến từ việc bị bỏ rơi lúc khẩn cấp. | Không build chatbot tư vấn du lịch. BẮT BUỘC build luồng xử lý sự cố. Màn hình chat phải có AI đọc tình trạng vé và nút Escalation (chuyển người) hoạt động được 24/7. |

## 3. Pain statement

```text
User khách du lịch cá nhân đang gặp khó ở bước xử lý hậu kỳ khi bị hệ thống tự động hủy vé/lỗi thanh toán sát giờ khởi hành,
vì bot CSKH hiện tại chỉ trả lời theo văn mẫu và từ chối hỗ trợ ngoài giờ hành chính,
dẫn tới hậu quả là user hoảng loạn, cảm thấy bị lừa đảo (Trust Score bằng 0) và lên store đánh giá 1 sao.
Bằng chứng chính là loạt review "Lừa đảo", "Không liên lạc được nhân viên" trên App Store của Trip.com.
```

## 4. Build slice

```text
Cho hành khách vừa nhận thông báo lỗi trừ tiền/hủy vé tự động,
prototype sẽ dùng AI (LLM) để đọc tình trạng log giao dịch nhằm chẩn đoán lỗi (ví dụ: lỗi thanh toán phía đối tác),
tạo ra một giải thích minh bạch lập tức (kèm nút "Auto-Refund" hoặc "Kết nối khẩn cấp"),
và xử lý trường hợp AI không đủ dữ liệu/không giải quyết được bằng cách tạo ticket độ ưu tiên cao (P0) bắn thẳng vào luồng của Human Agent (bypass chatbot thường).
```

## 5. Auto/Aug decision

Chọn một:
- [ ] **Augmentation:** AI gợi ý/draft/phân loại, user quyết cuối.
- [x] **Conditional automation:** AI tự làm trong case hẹp; case mơ hồ/rủi ro chuyển người.
- [ ] **Automation:** AI tự quyết và tự hành động.

**Lý do chọn:** Sự cố thanh toán/hủy vé liên quan đến tiền bạc, nên AI chỉ được phép Auto-refund nếu lỗi 100% thuộc về hệ thống (Conditional Automation). Nếu có tranh chấp hoặc mập mờ, AI phải lùi lại làm nhiệm vụ tổng hợp thông tin (Augment) cho nhân viên giải quyết.
**Human role:** Rescuer (Người cứu hộ) & Decider (Người quyết định các case phức tạp).

## 6. Four paths

| Path | Prototype phải thể hiện gì? |
|---|---|
| Happy | AI nhận diện lỗi hệ thống rõ ràng -> Tự động giải thích ngọn ngành -> Bấm 1 nút hoàn tiền ngay không cần chờ. |
| Low-confidence | AI không chắc lý do vé bị hủy -> Hỏi thêm user 1 câu xác nhận hoặc đề xuất 2 phương án: Đổi vé tương đương / Chờ kết nối nhân viên. |
| Failure | AI không đọc được log giao dịch hoặc không hiểu intent -> Thay vì xin lỗi văn mẫu, AI tự tạo "Mã khẩn cấp" và kết nối agent người thật. |
| Correction | Khi AI phân loại sai mức độ khẩn cấp (vd: chuyến bay còn 2 tháng nhưng AI ưu tiên nhầm), nhân viên hoặc người dùng có thể hạ cấp độ ticket, AI học lại tiêu chí thời gian. |

## 7. Failure mode nguy hiểm nhất

```text
Nếu user bị hủy chuyến bay trong 2 tiếng tới (trigger),
AI có thể phân loại sai (hallucinate) bảo lỗi do khách hàng và từ chối hoàn tiền (failure),
hậu quả là khách lỡ chuyến bay, thiệt hại hàng chục triệu (impact).
Prototype sẽ xử lý bằng cơ chế Bypass: Bất cứ lúc nào user gõ "Khẩn cấp" hoặc "Sân bay", AI lùi lại ngay lập tức và mở kênh chat/hotline với người thật (human rescuer).
Owner kiểm thử path này là [Điền tên thành viên].
```

## 8. Owner plan cho sáng Day 06

| Thành viên | Việc phụ trách | Bằng chứng cần có trong repo |
|---|---|---|
| [Hải] | Research / evidence | Hoàn thành file evidence-pack.md |
| [Lợi] | SPEC | Hoàn thành file thin-spec.md này |
| [Đạt] | Prototype | File code UI / Colab / Flowise (tùy nhóm chọn tool) |
| [Huy] | Test / failure path | Video quay lại cảnh test luồng lỗi (Failure path) |
| [Giang] | Demo script / repo | Repo github nhóm, kịch bản pitch 3 phút |
