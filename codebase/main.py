"""
AI Crisis Copilot — Backend Server (FastAPI + OpenAI Tool Calling)
Chạy: uvicorn main:app --reload --port 8000
"""

import json
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from mock_data import MOCK_BOOKINGS, SCENARIO_BOOKING_MAP

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    # base_url="http://localhost:20128/v1"
)

# ============================================================
# SESSION STORE (in-memory, đủ cho demo)
# ============================================================
sessions: dict[str, list] = {}

SYSTEM_PROMPT = """Bạn là AI Crisis Copilot của Trip.com — trợ lý AI chuyên xử lý khủng hoảng booking cho khách hàng đang hoảng loạn.

NHIỆM VỤ: Khi khách liên hệ, bạn phải (1) Xoa dịu cảm xúc, (2) Dùng tool check_booking_status để tra cứu mã vé, (3) Phân tích nguyên nhân lỗi, (4) Hành động phù hợp.

NGUYÊN TẮC:
1. LUÔN gọi check_booking_status TRƯỚC khi nhận định bất cứ điều gì.
2. error_source="system" VÀ refund_eligible=true → Giải thích rõ lỗi hệ thống, xin lỗi chân thành, rồi gọi initiate_auto_refund.
3. error_source="unknown" → KHÔNG tự kết luận. Hỏi thêm hoặc đề xuất 2 phương án (đổi vé / chờ nhân viên).
4. error_detail=null → Thừa nhận thiếu dữ liệu, gọi escalate_to_human_agent ngay.
5. Khách nói "khẩn cấp/sân bay/cứu/gấp/người thật/nhân viên" → escalate_to_human_agent với P0 NGAY.
6. Khách bảo thông tin hệ thống SAI (ngày bay sai, mức ưu tiên sai) → Xin lỗi, cập nhật đánh giá, escalate nếu cần.
CẤM: Trả lời kiểu "Xin lỗi quý khách, vui lòng liên hệ lại trong giờ hành chính". Trả lời ngắn gọn, tập trung giải pháp, bằng tiếng Việt."""

# ============================================================
# TOOL DEFINITIONS
# ============================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_booking_status",
            "description": "Tra cứu trạng thái đặt vé (chuyến bay, lỗi, mức ưu tiên). LUÔN gọi trước khi trả lời.",
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
    meta = {"refund_processed": False, "escalated": False, "escalation_priority": None}

    if name == "check_booking_status":
        code = args.get("booking_code", "")
        booking = MOCK_BOOKINGS.get(code)
        if booking:
            return json.dumps(booking, ensure_ascii=False), meta
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

    if name == "escalate_to_human_agent":
        ticket_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
        priority = args.get("priority", "P1")
        meta["escalated"] = True
        meta["escalation_priority"] = priority
        return json.dumps({
            "status": "ESCALATED",
            "ticket_id": ticket_id,
            "priority": priority,
            "reason": args.get("reason", ""),
            "message": f"Đã tạo ticket {ticket_id} ({priority}). Nhân viên sẽ tiếp nhận trong 30 giây.",
        }, ensure_ascii=False), meta

    return json.dumps({"error": "Unknown tool"}), meta


# ============================================================
# CHAT LOGIC (xử lý tool-calling loop)
# ============================================================
def chat_with_ai(session_id: str, user_message: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    messages = sessions[session_id]
    messages.append({"role": "user", "content": user_message})

    metadata = {"refund_processed": False, "escalated": False, "escalation_priority": None}

    # Loop: OpenAI có thể gọi nhiều tool liên tiếp
    for _ in range(5):  # max 5 vòng để tránh infinite loop
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            # model="ag/gemini-3-flash-agent",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
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
