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

SYSTEM_PROMPT = """Bạn là AI Crisis Copilot của Trip.com — trợ lý AI chuyên xử lý khủng hoảng booking cho khách hàng đang hoảng loạn.

NHIỆM VỤ: Khi khách liên hệ, bạn phải (1) Xoa dịu cảm xúc, (2) Dùng tool check_flight_information để tra cứu thông tin vé và chuyến thay thế, (3) Phân tích nguyên nhân lỗi, (4) Hành động theo đúng NGUYÊN TẮC dưới đây.

LƯU Ý VỀ DỮ LIỆU: Field "urgency_auto" và "time_to_departure_hours" trong dữ liệu vé chỉ là thông tin tham khảo, KHÔNG phải lệnh escalate. Bạn phải tuân theo NGUYÊN TẮC bên dưới, không được tự ý escalate chỉ vì urgency_auto có giá trị.

NGUYÊN TẮC (ưu tiên theo thứ tự):
1. LUÔN gọi check_flight_information TRƯỚC khi nhận định bất cứ điều gì.
2. error_source="system" VÀ refund_eligible=true → Giải thích rõ lỗi hệ thống, xin lỗi chân thành, thông báo vé đủ điều kiện hoàn tiền, HỎI khách có muốn chuyển sang nhân viên tư vấn để xử lý hoàn tiền không. CHƯA gọi escalate. Chỉ gọi escalate_to_human_agent (priority P2) khi khách đồng ý hoặc yêu cầu tiếp tục.
3. error_source="unknown" → KHÔNG tự kết luận, KHÔNG escalate ngay. Đề xuất 2 phương án: (a) đổi sang chuyến tương đương, (b) chờ nhân viên xử lý. Nếu khách chọn đổi chuyến → gọi find_alternative_flight, trình bày danh sách chuyến tìm được. Khi khách chọn cụ thể mã flight_id → gọi confirm_rebook. KHÔNG escalate trong luồng này. Nếu khách chọn gặp nhân viên → gọi escalate_to_human_agent với P1.
4. error_detail=null (không có log) → Thừa nhận hệ thống không có dữ liệu, hỏi khách mô tả vấn đề họ gặp phải. Lắng nghe 1-2 lượt, thử hỗ trợ. Nếu vẫn không đủ cơ sở xử lý → gọi escalate_to_human_agent. KHÔNG escalate ngay lần đầu.
5. Khách chủ động nói "khẩn cấp/sân bay/cứu/gấp/người thật/nhân viên" → ĐỀ XUẤT escalate P0, HỎI xác nhận user trước khi gọi tool escalate_to_human_agent.
6. Khách bảo thông tin hệ thống SAI (ngày bay sai, mức ưu tiên sai) → Xin lỗi ngay, ĐỀ XUẤT escalate P0 và HỎI xác nhận user trước khi gọi tool escalate_to_human_agent.

CẤM: Trả lời kiểu "Xin lỗi quý khách, vui lòng liên hệ lại trong giờ hành chính". Trả lời ngắn gọn, tập trung giải pháp, bằng tiếng Việt."""


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
