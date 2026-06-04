// DOM Elements
const screenBooking = document.getElementById('screen-booking');
const screenChat = document.getElementById('screen-chat');
const btnSupport = document.getElementById('btn-support');
const btnBack = document.getElementById('btn-back');
const chatBox = document.getElementById('chat-box');
const typingIndicator = document.getElementById('typing-indicator');
const quickActions = document.getElementById('quick-actions');
const chatInput = document.getElementById('chat-input');
const btnSend = document.getElementById('btn-send');
const handoffOverlay = document.getElementById('handoff-overlay');
const btnCloseHandoff = document.getElementById('btn-close-handoff');
const uiFlightStatus = document.getElementById('ui-flight-status');
const handoffMessage = document.getElementById('handoff-message');

// Configure marked.js for safe, clean Markdown rendering
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,       // \n → <br>
        gfm: true,          // GitHub Flavored Markdown
    });
}

function renderMarkdown(text) {
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    }
    return text.replace(/\n/g, '<br>'); // fallback
}

// Dev Panel
const scenarioSelector = document.getElementById('scenario-selector');
const btnRestartApp = document.getElementById('btn-restart-app');

let currentScenario = 'happy';
let sessionId = null;
let isWaiting = false;
let failureBookingCode = null;
let failureFirstMessage = true;

const SCENARIO_STATUS = {
    happy: "ĐÃ HỦY",
    low_confidence: "ĐANG XỬ LÝ",
    failure: "ĐÃ HỦY",
    correction: "ĐÃ HỦY"
};

// Gợi ý nhanh cho từng scenario — gửi như tin nhắn thật lên AI
const SCENARIO_ACTIONS = {
    happy: [
        { text: "Yêu cầu hoàn tiền qua nhân viên" },
        { text: "Tôi muốn đặt lại vé" }
    ],
    low_confidence: [
        { text: "🔀 Đổi chuyến tương đương" },
        { text: "🆘 Gặp nhân viên (Khẩn cấp)", urgent: true }
    ],
    failure: [],
    correction: [
        { text: "Sai rồi! Chuyến bay của tôi là hôm nay, không phải tháng sau", urgent: true },
        { text: "Đồng ý với thông tin hệ thống" }
    ]
};

// App Reset
function resetApp() {
    currentScenario = scenarioSelector.value;
    sessionId = null;
    isWaiting = false;
    failureBookingCode = null;
    failureFirstMessage = true;

    screenChat.classList.remove('active');
    screenBooking.classList.add('active');
    handoffOverlay.classList.add('hidden');

    Array.from(chatBox.querySelectorAll('.message:not(.typing-indicator)')).forEach(msg => msg.remove());
    clearQuickActions();

    uiFlightStatus.innerText = SCENARIO_STATUS[currentScenario] || "ĐÃ HỦY";
}

btnRestartApp.addEventListener('click', resetApp);

// Navigation
btnSupport.addEventListener('click', () => {
    screenBooking.classList.remove('active');
    screenChat.classList.add('active');
    startAIAnalysis();
});

btnBack.addEventListener('click', () => {
    screenChat.classList.remove('active');
    screenBooking.classList.add('active');
    resetApp();
});

btnCloseHandoff.addEventListener('click', () => {
    handoffOverlay.classList.add('hidden');
});

// Chat Functions
function escapeHtml(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function appendMessage(text, sender, isUrgent = false) {
    const msgDiv = document.createElement('div');
    if (sender === 'system') {
        msgDiv.className = 'system-msg';
        msgDiv.innerHTML = text;
    } else if (sender === 'bot') {
        // Render Markdown từ LLM thành HTML
        msgDiv.className = `message bot-msg ${isUrgent ? 'urgent' : ''}`;
        const bubble = document.createElement('div');
        bubble.className = 'bubble markdown-body';
        bubble.innerHTML = renderMarkdown(text);
        msgDiv.appendChild(bubble);
    } else {
        msgDiv.className = `message ${sender}-msg ${isUrgent ? 'urgent' : ''}`;
        const content = sender === 'user' ? escapeHtml(text) : text;
        msgDiv.innerHTML = `<div class="bubble">${content}</div>`;
    }
    chatBox.insertBefore(msgDiv, typingIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function renderQuickActions(actions) {
    quickActions.innerHTML = '';
    actions.forEach(action => {
        const btn = document.createElement('button');
        btn.className = `quick-btn ${action.urgent ? 'urgent' : ''}`;
        btn.innerText = action.text;
        btn.addEventListener('click', () => {
            clearQuickActions();
            sendMessage(action.text);
        });
        quickActions.appendChild(btn);
    });
}

function clearQuickActions() {
    quickActions.innerHTML = '';
}

function triggerHandoff(priority = 'P0') {
    appendMessage(`🆘 AI đã tạo mã khẩn cấp [${priority}_123]. Chuyển toàn bộ lịch sử chat cho nhân viên...`, 'system');
    handoffMessage.innerText = `AI đã ghi nhận tình huống khẩn cấp (${priority}). Vui lòng giữ máy, nhân viên hỗ trợ sẽ có mặt trong 30 giây...`;
    handoffOverlay.classList.remove('hidden');
}

// API
async function callAPI(message) {
    const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
}

// AI Flow — AI nói trước
async function startAIAnalysis() {
    sessionId = 'session_' + Date.now();

    typingIndicator.style.display = 'block';
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const codeRes = await fetch(`/api/booking-code/${currentScenario}`);
        const codeData = await codeRes.json();
        const bookingCode = codeData.booking_code;

        // Case failure: AI chào trước, chờ khách chat — không gửi booking code ngay
        if (currentScenario === 'failure') {
            failureBookingCode = bookingCode;
            failureFirstMessage = true;
            setTimeout(() => {
                typingIndicator.style.display = 'none';
                appendMessage('Xin chào! Tôi là trợ lý AI của Trip.com. Bạn cần hỗ trợ gì ạ?', 'bot');
            }, 800);
            return;
        }

        // Các case khác: gửi booking code ngầm để AI phân tích ngay
        const INIT_MESSAGES = {
            happy:          `Mã đặt vé của tôi là ${bookingCode}. Vé chuyến bay của tôi bị hủy đột ngột, tôi cần hỗ trợ ngay.`,
            low_confidence: `Mã đặt vé của tôi là ${bookingCode}. Vé chuyến bay của tôi bị hủy đột ngột, tôi cần hỗ trợ ngay.`,
            correction:     `Mã đặt vé của tôi là ${bookingCode}. Vé chuyến bay của tôi bị hủy đột ngột, tôi cần hỗ trợ ngay.`,
        };
        const initMsg = INIT_MESSAGES[currentScenario] || `Mã đặt vé của tôi là ${bookingCode}. Tôi cần hỗ trợ.`;
        const result = await callAPI(initMsg);

        typingIndicator.style.display = 'none';
        appendMessage(result.reply, 'bot');

        const actions = SCENARIO_ACTIONS[currentScenario] || [];
        if (actions.length > 0) renderQuickActions(actions);

        if (result.escalated) {
            setTimeout(() => triggerHandoff(result.escalation_priority || 'P0'), 800);
        }
    } catch (e) {
        typingIndicator.style.display = 'none';
        appendMessage('Không thể kết nối tới hệ thống. Hãy chắc chắn server đang chạy tại <b>localhost:8000</b>.', 'bot');
    }
}

// Gửi tin nhắn
async function sendMessage(text) {
    if (!text || isWaiting) return;

    // Case failure: lần đầu khách nhắn, đính kèm booking code ngầm vào API
    let apiText = text;
    if (currentScenario === 'failure' && failureFirstMessage && failureBookingCode) {
        apiText = `Mã đặt vé của tôi là ${failureBookingCode}. ${text}`;
        failureFirstMessage = false;
    }

    appendMessage(text, 'user');
    clearQuickActions();
    isWaiting = true;

    typingIndicator.style.display = 'block';
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const result = await callAPI(apiText);
        typingIndicator.style.display = 'none';
        isWaiting = false;
        appendMessage(result.reply, 'bot');

        if (result.escalated) {
            setTimeout(() => triggerHandoff(result.escalation_priority || 'P0'), 800);
        }
    } catch (e) {
        typingIndicator.style.display = 'none';
        isWaiting = false;
        appendMessage('Lỗi kết nối. Vui lòng thử lại.', 'bot');
    }
}

function handleUserInput() {
    const text = chatInput.value.trim();
    if (!text) return;
    chatInput.value = '';
    sendMessage(text);
}

btnSend.addEventListener('click', handleUserInput);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleUserInput();
});

// Init
resetApp();
