"""
AI Crisis Copilot — Backend Server (FastAPI + OpenAI Tool Calling)
Chạy: uvicorn main:app --reload --port 8000
"""

import json
import os
import re
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from mock_data import ALTERNATIVE_FLIGHTS, MOCK_BOOKINGS, SCENARIO_BOOKING_MAP

load_dotenv()

_api_key = os.environ.get("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY chưa được đặt. Kiểm tra file .env trong thư mục codebase/.")

client = OpenAI(
    api_key=_api_key,
)

# ============================================================
# SESSION STORE (in-memory, đủ cho demo)
# ============================================================
sessions: dict[str, list] = {}

DOMAIN_KEYWORDS = [
    "vé", "chuyến", "bay", "booking", "đổi", "hoàn", "refund", "thanh toán",
    "phụ thu", "hỗ trợ", "khẩn cấp", "sân bay", "hủy", "trip", "mã vé",
    "gọi", "nhân viên", "đồng ý", "xác nhận",
]

GENERAL_KNOWLEDGE_PATTERNS = [
    r"\blà ai\b",
    r"\blà gì\b",
    r"\bbao nhiêu\b",
    r"\bthủ đô\b",
    r"\btổng thống\b",
    r"\bchủ tịch nước\b",
    r"\bthời tiết\b",
    r"\btỉ số\b",
]

BOOKING_PREFIX_PATTERNS = [
    r"mã đặt vé của tôi là\s*bk-[a-z0-9-]+[.,]?\s*",
    r"booking code của tôi là\s*bk-[a-z0-9-]+[.,]?\s*",
]


def extract_user_intent_text(message: str) -> str:
    text = (message or "").strip()
    if not text:
        return ""

    lower_text = text.lower()
    marker = "câu hỏi của tôi:"
    idx = lower_text.find(marker)
    if idx != -1:
        return text[idx + len(marker):].strip()

    cleaned = lower_text
    for pattern in BOOKING_PREFIX_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned)
    return cleaned.strip()

SYSTEM_PROMPT = """# VAI TRÒ
Bạn là **AI Crisis Copilot** của Trip.com — trợ lý chuyên xử lý KHỦNG HOẢNG booking (vé bị hủy, lỗi thanh toán, mất tiền oan), thường gặp khách đang hoảng loạn và SÁT GIỜ BAY. Bạn KHÔNG phải chatbot tư vấn du lịch chung; nhiệm vụ duy nhất là cứu khách khỏi sự cố một cách nhanh, minh bạch, đáng tin.

# GIỌNG ĐIỆU & CÁCH TRẢ LỜI
- Đồng cảm TRƯỚC, giải pháp SAU. Câu đầu luôn trấn an ("Mình hiểu bạn đang rất lo, để mình kiểm tra ngay...").
- Ngắn gọn 2–4 câu/lượt, tiếng Việt tự nhiên, tập trung vào hành động kế tiếp.
- Minh bạch: dịch mã lỗi kỹ thuật sang ngôn ngữ đời thường (vd "GATEWAY_TIMEOUT_PARTNER" → "lỗi từ cổng thanh toán đối tác"), KHÔNG đọc thô mã lỗi cho khách.
- Khi tiền của khách an toàn hoặc đủ điều kiện hoàn, nói rõ để khách yên tâm. Khi đưa lựa chọn, nêu rõ ràng để khách dễ chọn.

# QUY TRÌNH MỖI LƯỢT
1. LUÔN gọi `check_flight_information` TRƯỚC khi kết luận bất cứ điều gì. Không phỏng đoán khi chưa tra cứu.
2. Đọc kỹ dữ liệu trả về: `error_source`, `error_detail`, `refund_eligible`, `amount`, và danh sách `available_flights` (nếu có).
3. Trấn an → giải thích nguyên nhân → hành động đúng theo NGUYÊN TẮC. Khi nhắc số tiền, dùng đúng `amount` từ kết quả tra cứu, không tự bịa.

# LƯU Ý VỀ DỮ LIỆU
Field `urgency_auto` và `time_to_departure_hours` chỉ là thông tin THAM KHẢO, KHÔNG phải lệnh escalate. Tuyệt đối không escalate chỉ vì các field này có giá trị — luôn tuân theo NGUYÊN TẮC bên dưới.

# CÔNG CỤ (gọi đúng lúc)
- `check_flight_information(booking_code)`: tra cứu vé + chuyến thay thế. Gọi đầu tiên; gọi lại nếu khách đưa mã mới.
- `find_alternative_flight(booking_code)`: tìm chuyến thay thế khi khách muốn đổi chuyến (chỉ liệt kê, CHƯA đặt).
- `confirm_rebook(booking_code, flight_id)`: chốt đổi sang chuyến mà khách đã chọn (có `flight_id` cụ thể).
- `escalate_to_human_agent(booking_code, priority, reason)`: chuyển nhân viên thật. `priority` ∈ {P0,P1,P2,P3}; `reason` ghi rõ lý do. Lưu ý: tool này chỉ ĐỀ XUẤT chuyển và chờ khách xác nhận — vì vậy phải HỎI khách đồng ý trước khi gọi (trừ khi nguyên tắc nói gọi luôn).
- `initiate_auto_refund(booking_code, amount)`: **KHÔNG sử dụng.** Theo chính sách hiện tại, AI không tự hoàn tiền — mọi việc hoàn tiền đều chuyển nhân viên thật xử lý (xem Nguyên tắc 2).

# NGUYÊN TẮC XỬ LÝ (ưu tiên theo thứ tự)
1. LUÔN `check_flight_information` trước tiên.
2. **Lỗi hệ thống, đủ điều kiện hoàn** — `error_source="system"` VÀ `refund_eligible=true`:
   Giải thích rõ đây là lỗi hệ thống/đối tác (khách không có lỗi), xin lỗi chân thành, thông báo vé ĐỦ ĐIỀU KIỆN hoàn tiền, rồi HỎI khách có muốn chuyển sang nhân viên để xử lý hoàn tiền không. CHƯA escalate. Chỉ gọi `escalate_to_human_agent` (priority **P2**) khi khách đồng ý/muốn tiếp tục.
3. **Không rõ nguyên nhân** — `error_source="unknown"`:
   KHÔNG tự kết luận, KHÔNG escalate ngay. Đưa ĐÚNG 2 lựa chọn: (a) đổi sang chuyến tương đương, (b) chờ nhân viên xử lý.
   - Khách chọn (a) → gọi `find_alternative_flight`, trình bày danh sách; khi khách chọn `flight_id` cụ thể → gọi `confirm_rebook`. KHÔNG escalate trong luồng này.
   - Khách chọn (b) → gọi `escalate_to_human_agent` priority **P1**.
4. **Không có dữ liệu** — `error_detail=null`:
   Thừa nhận hệ thống không có log, HỎI khách mô tả vấn đề. Lắng nghe 1–2 lượt, cố gắng hỗ trợ. Chỉ khi vẫn không đủ cơ sở xử lý mới gọi `escalate_to_human_agent`. KHÔNG escalate ngay lần đầu.
5. **Khách nói khẩn cấp** — chứa "khẩn cấp/sân bay/cứu/gấp/người thật/nhân viên":
   ĐỀ XUẤT escalate **P0** và HỎI xác nhận khách trước khi gọi `escalate_to_human_agent`.
6. **Khách báo dữ liệu hệ thống SAI** (ngày bay sai, mức ưu tiên sai):
   Tin lời khách, xin lỗi ngay vì đánh giá sai, ĐỀ XUẤT escalate **P0** (kèm `reason` "khách báo dữ liệu hệ thống sai") và HỎI xác nhận trước khi gọi tool.

# THANG ĐỘ ƯU TIÊN (tham chiếu, không phải tự động)
- **P0**: khách dùng từ khóa khẩn cấp, hoặc báo dữ liệu sai khiến nguy cơ lỡ chuyến/thiệt hại lớn.
- **P1**: khách chủ động chọn gặp nhân viên khi nguyên nhân chưa rõ.
- **P2**: chuyển nhân viên để xử lý hoàn tiền (lỗi hệ thống đã xác định).
- **P3**: việc không gấp, không ảnh hưởng chuyến sắp khởi hành.

# TUYỆT ĐỐI CẤM
- Cấm câu kiểu "Xin lỗi quý khách, vui lòng liên hệ lại trong giờ hành chính" hay đẩy khách đi nơi khác.
- Cấm escalate chỉ dựa trên `urgency_auto`/`time_to_departure_hours`.
- Cấm bịa nguyên nhân, số tiền, thời gian hoàn khi dữ liệu không có — thiếu thì hỏi lại hoặc escalate.
- Cấm hứa điều ngoài khả năng của các công cụ trên.
- Trả lời ngắn gọn, tập trung giải pháp, bằng tiếng Việt."""


def is_out_of_scope_message(message: str) -> bool:
    text = extract_user_intent_text(message).lower()
    if not text:
        return False

    # Chặn cứng các câu hỏi kiến thức chung dù có dính prefix booking.
    if any(re.search(pattern, text) for pattern in GENERAL_KNOWLEDGE_PATTERNS):
        return True

    # Cho phép câu chào ngắn để AI tiếp tục hỏi lại vấn đề booking.
    if text in {"xin chào", "hello", "hi", "alo", "alo ad", "chào"}:
        return False

    # Nếu không có từ khóa domain booking/travel support thì coi là ngoài phạm vi.
    if not any(keyword in text for keyword in DOMAIN_KEYWORDS):
        return True

    return False

# ============================================================
# TOOL DEFINITIONS
# ============================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_flight_information",
            "description": "Tra cứu đầy đủ thông tin chuyến bay theo mã vé và gợi ý danh sách chuyến bay thay thế.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_code": {"type": "string", "description": "Mã đặt vé (vd: BK-78901)"}
                },
                "required": ["booking_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_auto_refund", 
            "description": "Hoàn tiền tự động. CHỈ gọi khi error_source='system' và refund_eligible=true.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_code": {"type": "string"},
                    "amount": {"type": "number", "description": "Số tiền hoàn (VNĐ)"},
                },
                "required": ["booking_code", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_alternative_flight",
            "description": "Tìm chuyến bay thay thế còn chỗ. Gọi khi khách muốn đổi chuyến. Chỉ trả về thông tin, CHƯA đặt vé.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_code": {"type": "string"},
                },
                "required": ["booking_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_rebook",
            "description": "Xác nhận đổi sang chuyến bay thay thế theo flight_id đã chọn.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_code": {"type": "string"},
                    "flight_id": {"type": "string", "description": "Mã chuyến bay thay thế khách đã chọn"},
                },
                "required": ["booking_code", "flight_id"],
            },
        },
    },


    {
        "type": "function",
        "function": {
            "name": "escalate_to_human_agent",
            "description": "Chuyển sang nhân viên thật. Gọi khi: không xác định lỗi / khách yêu cầu / tình huống khẩn cấp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_code": {"type": "string"},
                    "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                    "reason": {"type": "string", "description": "Lý do chuyển"},
                },
                "required": ["booking_code", "priority", "reason"],
            },
        },
    },
]


# ============================================================
# TOOL EXECUTION
# ============================================================
def execute_tool(name: str, args: dict) -> tuple[str, dict]:
    """Trả về (result_json, metadata). metadata chứa flags cho frontend."""
    meta = {
        "refund_processed": False,
        "escalated": False,
        "escalation_priority": None,
        "escalation_ticket_id": None,
        "escalation_recommended": False,
        "escalation_reason": None,
        "available_flights": None,
        "selected_flight": None,
        "booking_code": args.get("booking_code"),
    }

    if name == "check_flight_information":
        code = args.get("booking_code", "")
        booking = MOCK_BOOKINGS.get(code)
        if booking:
            options = ALTERNATIVE_FLIGHTS.get(code, [])
            if options:
                meta["available_flights"] = options
            return json.dumps(
                {
                    "booking": booking,
                    "available_flights": options,
                    "has_alternative_flights": len(options) > 0,
                },
                ensure_ascii=False,
            ), meta
        return json.dumps({"error": f"Không tìm thấy mã vé {code} trong hệ thống."}), meta

    if name == "initiate_auto_refund":
        code = args.get("booking_code", "")
        amount = args.get("amount", 0)
        booking = MOCK_BOOKINGS.get(code)
        if booking and booking.get("refund_eligible"):
            meta["refund_processed"] = True
            return json.dumps({
                "status": "SUCCESS",
                "booking_code": code,
                "refund_amount": amount,
                "message": f"Đã kích hoạt hoàn tiền {amount:,.0f}đ. Tiền sẽ về tài khoản trong 5-10 phút.",
            }, ensure_ascii=False), meta
        return json.dumps({"status": "DENIED", "message": "Không đủ điều kiện hoàn tiền tự động."}), meta

    if name == "find_alternative_flight":
        code = args.get("booking_code", "")
        options = ALTERNATIVE_FLIGHTS.get(code, [])
        if options:
            meta["available_flights"] = options
            return json.dumps(
                {
                    "status": "AVAILABLE",
                    "booking_code": code,
                    "flights": options,
                    "message": "Đã tìm thấy danh sách chuyến bay thay thế khả dụng.",
                },
                ensure_ascii=False,
            ), meta
        return json.dumps(
            {"status": "UNAVAILABLE", "booking_code": code, "message": "Hiện chưa có chuyến thay thế khả dụng."},
            ensure_ascii=False,
        ), meta

    if name == "confirm_rebook":
        code = args.get("booking_code", "")
        flight_id = args.get("flight_id", "")
        options = ALTERNATIVE_FLIGHTS.get(code, [])
        selected = next((f for f in options if f.get("flight_id") == flight_id), None)
        if not selected:
            return json.dumps(
                {"status": "DENIED", "message": "Không tìm thấy chuyến bay đã chọn. Vui lòng chọn lại."},
                ensure_ascii=False,
            ), meta

        new_booking = f"BK-{uuid.uuid4().hex[:5].upper()}"
        meta["selected_flight"] = selected
        return json.dumps(
            {
                "status": "CONFIRMED",
                "new_booking_code": new_booking,
                "flight_id": selected["flight_id"],
                "flight": selected["flight"],
                "route": selected["route"],
                "departure": selected["departure"],
                "arrival": selected["arrival"],
                "seat": selected["seat_available"],
                "message": f"Đổi chuyến thành công sang {selected['flight']} ({selected['departure']}). Mã đặt chỗ mới: {new_booking}.",
            },
            ensure_ascii=False,
        ), meta

    if name == "escalate_to_human_agent":
        priority = args.get("priority", "P1")
        meta["escalation_recommended"] = True
        meta["escalation_priority"] = priority
        meta["escalation_reason"] = args.get("reason", "")
        return json.dumps({
            "status": "PENDING_USER_CONFIRMATION",
            "priority": priority,
            "reason": args.get("reason", ""),
            "message": "Đề xuất chuyển sang nhân viên hỗ trợ. Chờ xác nhận của khách hàng trước khi tạo ticket.",
        }, ensure_ascii=False), meta

    return json.dumps({"error": "Unknown tool"}), meta


# ============================================================
# CHAT LOGIC (xử lý tool-calling loop)
# ============================================================
def chat_with_ai(session_id: str, user_message: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    metadata = {
        "refund_processed": False,
        "escalated": False,
        "escalation_priority": None,
        "escalation_ticket_id": None,
        "escalation_recommended": False,
        "escalation_reason": None,
        "available_flights": None,
        "selected_flight": None,
        "booking_code": None,
    }
    messages = sessions[session_id]
    messages.append({"role": "user", "content": user_message})

    if is_out_of_scope_message(user_message):
        fallback_text = (
            "Mình chỉ hỗ trợ các vấn đề liên quan đến vé/chuyến bay trong Trip.com "
            "(đổi chuyến, hoàn tiền, phụ thu, kết nối nhân viên). "
            "Bạn mô tả giúp mình sự cố của booking hiện tại nhé."
        )
        messages.append({"role": "assistant", "content": fallback_text})
        return {"reply": fallback_text, **metadata}

    try:
        # Loop: OpenAI có thể gọi nhiều tool liên tiếp
        for _ in range(5):  # max 5 vòng để tránh infinite loop
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result, meta = execute_tool(tc.function.name, args)
                    # Merge metadata
                    for k, v in meta.items():
                        if v:
                            metadata[k] = v
                    messages.append({
                        "tool_call_id": tc.id,
                        "role": "tool",
                        "name": tc.function.name,
                        "content": result,
                    })
            else:
                # AI trả lời text cuối cùng
                final_text = msg.content or ""
                messages.append({"role": "assistant", "content": final_text})
                return {"reply": final_text, **metadata}

    except Exception as e:
        return {"reply": f"Hệ thống tạm thời gián đoạn. Vui lòng thử lại sau giây lát. (Lỗi: {type(e).__name__})", **metadata}

    return {"reply": "Xin lỗi, hệ thống đang quá tải. Vui lòng thử lại.", **metadata}


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(title="AI Crisis Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


class RebookRequest(BaseModel):
    booking_code: str
    flight_id: str


class EscalationConfirmRequest(BaseModel):
    booking_code: str
    priority: str
    reason: str


@app.get("/")
async def serve_index():
    return FileResponse("frontend/index.html")


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    result = chat_with_ai(req.session_id, req.message)
    return result


@app.post("/api/reset")
async def api_reset(req: ResetRequest):
    sessions.pop(req.session_id, None)
    return {"status": "ok"}


@app.get("/api/booking-code/{scenario}")
async def get_booking_code(scenario: str):
    code = SCENARIO_BOOKING_MAP.get(scenario)
    if code:
        return {"booking_code": code}
    return {"error": "Unknown scenario"}


@app.get("/api/flight-options/{booking_code}")
async def get_flight_options(booking_code: str):
    flights = ALTERNATIVE_FLIGHTS.get(booking_code, [])
    return {"booking_code": booking_code, "flights": flights}


@app.post("/api/rebook")
async def api_rebook(req: RebookRequest):
    result_json, _ = execute_tool("confirm_rebook", {"booking_code": req.booking_code, "flight_id": req.flight_id})
    return json.loads(result_json)


@app.post("/api/escalate-confirm")
async def api_escalate_confirm(req: EscalationConfirmRequest):
    ticket_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
    return {
        "status": "ESCALATED",
        "ticket_id": ticket_id,
        "priority": req.priority,
        "reason": req.reason,
        "message": f"Đã tạo ticket {ticket_id} ({req.priority}). Nhân viên sẽ tiếp nhận trong 30 giây.",
    }
