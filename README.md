# AI Crisis Copilot — Trip.com

> Day 06 AI Product Hackathon · Nhóm 16383 · Track B (Travel & Hospitality)
>
> Sản phẩm là trợ lý AI xử lý khủng hoảng booking cho khách Trip.com khi bị hủy vé/lỗi thanh toán: chẩn đoán nguyên nhân, đề xuất đổi chuyến, hoặc chuyển nhân viên thật khi cần.

## Thành viên nhóm

| Mã HV       | Họ và tên           | Vai trò chính                  |
| ----------- | ------------------- | ------------------------------ |
| 2A202600614 | Nguyễn Ngọc Hải     | Research, Evidence, Backend AI |
| 2A202600784 | Phạm Văn Lợi        | SPEC, System Prompt            |
| 2A202600549 | Lê Xuân Tiến Đạt    | Prototype (Frontend + Backend) |
| 2A202600839 | Dương Quang Huy     | Testing, Failure Path          |
| 2A202600624 | Nguyễn Trường Giang | Demo Script, Repo              |

## Mô tả ngắn sản phẩm

AI Crisis Copilot tập trung vào một lát cắt hẹp nhưng quan trọng: hỗ trợ khách hàng ngay tại thời điểm phát sinh sự cố booking. Hệ thống ưu tiên tính minh bạch và an toàn:

- AI giải thích ngắn gọn tình trạng vé và nguyên nhân sự cố.
- Cho phép đổi chuyến trực tiếp từ danh sách chuyến thay thế.
- Có cơ chế xác nhận trước khi chuyển sang nhân viên thật.
- Hỗ trợ các case phụ thu, hoàn voucher, và phí dịch vụ trong luồng đổi chuyến.

## Nội dung nộp Day 06

- SPEC sản phẩm: [`spec/spec.md`](spec/spec.md)
- Slide demo: [`spec/demo-slides.html`](spec/demo-slides.html)
- Code prototype chạy được: [`codebase/`](codebase/)

> Lưu ý: `02-group-spec/` là tài liệu nội bộ team dùng để thống nhất từ Day 05, không phải thư mục nộp chính của Day 06.

## Cách chạy prototype

```bash
cd codebase
pip install -r requirements.txt
```

Tạo file `.env` trong `codebase/`:

```env
OPENAI_API_KEY=sk-your-key-here
```

Chạy server:

```bash
uvicorn main:app --reload --port 8000
```

Mở trình duyệt: [http://localhost:8000](http://localhost:8000)

## Demo scenarios chính

- Happy Path
- Low-confidence
- Failure
- Correction
- Clean Surcharge / Clean Refund / Clean Extra Fee / Mixed cases

Toàn bộ kịch bản được chọn trực tiếp từ Developer Panel trong UI.
