# AI Crisis Copilot — Trip.com

> Trợ lý AI xử lý khủng hoảng booking cho khách hàng Trip.com (hủy vé, lỗi thanh toán, mất tiền oan).

## Cách chạy

### 1. Cài đặt
```bash
cd codebase
pip install -r requirements.txt
```

### 2. Cấu hình API Key
Tạo file `.env` trong folder `codebase/`:
```
OPENAI_API_KEY=sk-your-key-here
```

### 3. Chạy server
```bash
uvicorn main:app --reload --port 8000
```

### 4. Mở trình duyệt
Truy cập: **http://localhost:8000**

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| AI Model | OpenAI GPT-4o-mini (Tool Calling / Function Calling) |
| Backend | Python + FastAPI |
| Frontend | HTML + CSS + JavaScript (dựa trên mockup 03-prototype) |
| Database | Mock data (Python dict) |

## Demo 4 Paths

Dùng **Developer Panel** bên trái để chọn kịch bản:

| Path | Mã vé | AI sẽ làm gì? |
|---|---|---|
| **Happy** | BK-78901 | Phát hiện lỗi hệ thống → Tự động hoàn tiền |
| **Low-confidence** | BK-45678 | Không rõ nguyên nhân → Hỏi thêm / đề xuất 2 phương án |
| **Failure** | BK-99999 | Không có log → Chuyển cho nhân viên thật |
| **Correction** | BK-11111 | AI đọc sai ngày bay → User sửa → AI cập nhật ưu tiên |

## Phân công

| Thành viên | Việc phụ trách |
|---|---|
| [Hải] | Research / Evidence + Backend AI |
| [Lợi] | SPEC |
| [Đạt] | Prototype / Frontend |
| [Huy] | Test / Failure path |
| [Giang] | Demo script / Repo |
