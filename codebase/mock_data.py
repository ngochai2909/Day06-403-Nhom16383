"""
Mock Database cho AI Crisis Copilot.
Mỗi booking tương ứng với 1 trong 4 Paths cần demo.
"""

MOCK_BOOKINGS = {
    # ===== HAPPY PATH =====
    # Lỗi hệ thống rõ ràng → AI tự tin hoàn tiền
    "BK-78901": {
        "booking_code": "BK-78901",
        "flight": "VN123",
        "route": "HAN → SGN (Hà Nội → Hồ Chí Minh)",
        "departure": "15:30 Hôm nay",
        "passenger": "Nguyễn Văn An",
        "amount": 2500000,
        "status": "CANCELLED",
        "error_code": "GATEWAY_TIMEOUT_PARTNER",
        "error_source": "system",
        "error_detail": "Cổng thanh toán đối tác (VNPay) bị timeout lúc 09:15. Hệ thống tự động hủy vé nhưng lệnh trừ tiền đã được gửi thành công. Tiền 2,500,000đ đã bị trừ khỏi tài khoản khách.",
        "refund_eligible": True,
        "urgency_auto": "P1",
        "time_to_departure_hours": 6,
    },

    # ===== LOW-CONFIDENCE PATH =====
    # Không rõ nguyên nhân → AI cần hỏi thêm hoặc đề xuất lựa chọn
    "BK-45678": {
        "booking_code": "BK-45678",
        "flight": "VN123",
        "route": "HAN → SGN (Hà Nội → Hồ Chí Minh)",
        "departure": "15:30 Hôm nay",
        "passenger": "Trần Thị Bình",
        "amount": 2500000,
        "status": "CANCELLED",
        "error_code": "UNKNOWN_REASON",
        "error_source": "unknown",
        "error_detail": "Không xác định được nguyên nhân hủy vé. Log giao dịch ghi nhận trạng thái 'cancelled' nhưng không có mã lỗi từ cổng thanh toán lẫn hãng bay.",
        "refund_eligible": None,
        "urgency_auto": "P2",
        "time_to_departure_hours": 6,
    },

    # ===== FAILURE PATH =====
    # Không có log giao dịch → AI bất lực, phải chuyển người thật
    "BK-99999": {
        "booking_code": "BK-99999",
        "flight": "VN123",
        "route": "HAN → SGN (Hà Nội → Hồ Chí Minh)",
        "departure": "15:30 Hôm nay",
        "passenger": "Lê Văn Cường",
        "amount": 2500000,
        "status": "CANCELLED",
        "error_code": None,
        "error_source": None,
        "error_detail": None,
        "refund_eligible": None,
        "urgency_auto": None,
        "time_to_departure_hours": 6,
    },

    # ===== CORRECTION PATH =====
    # Dữ liệu hệ thống SAI ngày bay → AI đánh giá sai mức ưu tiên
    # Thực tế chuyến bay là HÔM NAY nhưng hệ thống ghi sai là 15/10/2026
    "BK-11111": {
        "booking_code": "BK-11111",
        "flight": "VN123",
        "route": "HAN → SGN (Hà Nội → Hồ Chí Minh)",
        "departure": "15:30 ngày 15/10/2026",
        "passenger": "Phạm Văn Dũng",
        "amount": 2500000,
        "status": "CANCELLED",
        "error_code": "AIRLINE_SCHEDULE_CHANGE",
        "error_source": "airline",
        "error_detail": "Hãng hàng không thay đổi lịch bay. Vé bị hủy tự động theo chính sách của hãng.",
        "refund_eligible": False,
        "urgency_auto": "P3",
        "time_to_departure_hours": 2160,
        "note": "Ưu tiên thấp (P3). Xử lý hoàn tiền theo chính sách hãng bay trong 7-14 ngày làm việc.",
    },
}

# Mapping scenario names to booking codes (for Dev Panel)
SCENARIO_BOOKING_MAP = {
    "happy": "BK-78901",
    "low_confidence": "BK-45678",
    "failure": "BK-99999",
    "correction": "BK-11111",
}