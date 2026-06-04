// ============================================================
// AI Crisis Copilot — Frontend (gọi Backend API thật)
// ============================================================

const API_BASE = '';  // Same origin (FastAPI serves frontend)

// Configure marked.js for safe, clean Markdown rendering
marked.setOptions({
    breaks: true,       // \n → <br>
    gfm: true,          // GitHub Flavored Markdown
});

function renderMarkdown(text) {
    // Parse markdown to HTML
    return marked.parse(text);
}

// DOM Elements
const screenBooking = document.getElementById('screen-booking');
const screenChat    = document.getElementById('screen-chat');
const btnSupport    = document.getElementById('btn-support');
const btnBack       = document.getElementById('btn-back');
const chatBox       = document.getElementById('chat-box');
const typingIndicator = document.getElementById('typing-indicator');
const quickActions   = document.getElementById('quick-actions');
const chatInput      = document.getElementById('chat-input');
const btnSend        = document.getElementById('btn-send');
const handoffOverlay = document.getElementById('handoff-overlay');
const btnCloseHandoff = document.getElementById('btn-close-handoff');
const handoffMessage  = document.getElementById('handoff-message');
const uiFlightStatus = document.getElementById('ui-flight-status');

// Dev Panel
const scenarioSelector = document.getElementById('scenario-selector');
const btnRestartApp    = document.getElementById('btn-restart-app');
const devStatus        = document.getElementById('dev-status');

// State
let sessionId = crypto.randomUUID();
let currentBookingCode = 'BK-78901';
let isWaiting = false;

// Scenario → Booking code mapping
const SCENARIO_MAP = {
    happy:          'BK-78901',
    low_confidence: 'BK-45678',
    failure:        'BK-99999',
    correction:     'BK-11111',
};

// Scenario → Quick actions (gửi text cho AI xử lý)
const SCENARIO_ACTIONS = {
    happy: [
        { text: '✨ Hoàn tiền tự động', message: 'Tôi muốn được hoàn tiền tự động ngay bây giờ.' },
        { text: '📞 Gặp nhân viên', message: 'Tôi muốn gặp nhân viên hỗ trợ.', urgent: true },
    ],
    low_confidence: [
        { text: '🔀 Đổi chuyến tương đương', message: 'Tôi muốn đổi sang chuyến bay tương đương miễn phí.' },
        { text: '🆘 Gặp nhân viên (Khẩn cấp)', message: 'Khẩn cấp! Tôi cần gặp nhân viên ngay.', urgent: true },
    ],
    failure: [
        { text: '🆘 Kết nối nhân viên ngay', message: 'Tôi cần gặp người thật ngay lập tức!', urgent: true },
    ],
    correction: [
        { text: '⚠️ Sửa sai! Chuyến bay là HÔM NAY', message: 'Thông tin sai rồi! Chuyến bay của tôi là HÔM NAY 15:30 chứ không phải 15/10/2026. Tôi đang ở sân bay!', urgent: true },
        { text: '✅ Thông tin đúng', message: 'Đúng rồi, chuyến bay là ngày 15/10/2026.' },
    ],
};

// Flight status text per scenario
const SCENARIO_STATUS = {
    happy: 'ĐÃ HỦY',
    low_confidence: 'ĐANG XỬ LÝ',
    failure: 'ĐÃ HỦY',
    correction: 'ĐÃ HỦY',
};

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function setDevStatus(text, type = '') {
    devStatus.className = 'dev-status ' + type;
    devStatus.innerHTML = `<span class="status-dot"></span> ${text}`;
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
        // User message: escape HTML để tránh XSS
        msgDiv.className = `message user-msg ${isUrgent ? 'urgent' : ''}`;
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.textContent = text;
        msgDiv.appendChild(bubble);
    }
    chatBox.insertBefore(msgDiv, typingIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;
}


function showTyping() {
    typingIndicator.style.display = 'block';
    chatBox.scrollTop = chatBox.scrollHeight;
}

function hideTyping() {
    typingIndicator.style.display = 'none';
}

function renderQuickActions(scenario) {
    quickActions.innerHTML = '';
    const actions = SCENARIO_ACTIONS[scenario] || [];
    actions.forEach(action => {
        const btn = document.createElement('button');
        btn.className = `quick-btn ${action.urgent ? 'urgent' : ''}`;
        btn.innerText = action.text;
        btn.addEventListener('click', () => {
            appendMessage(action.text, 'user');
            clearQuickActions();
            sendMessage(action.message);
        });
        quickActions.appendChild(btn);
    });
}

function clearQuickActions() {
    quickActions.innerHTML = '';
}

function showHandoff(priority) {
    handoffMessage.innerText = `AI đã ghi nhận tình huống khẩn cấp (${priority}). Vui lòng giữ máy, nhân viên hỗ trợ sẽ có mặt trong 30 giây...`;
    handoffOverlay.classList.remove('hidden');
}

// ============================================================
// API CALLS
// ============================================================

async function sendMessage(text) {
    if (isWaiting) return;
    isWaiting = true;
    showTyping();
    setDevStatus('Đang gọi AI...', 'loading');

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, message: text }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        hideTyping();

        // Hiển thị câu trả lời AI (Markdown được render bởi marked.js)
        if (data.reply) {
            appendMessage(data.reply, 'bot');
        }


        // Kiểm tra escalation
        if (data.escalated) {
            setTimeout(() => showHandoff(data.escalation_priority || 'P0'), 1000);
        }

        // Kiểm tra refund
        if (data.refund_processed) {
            setDevStatus('✅ Đã hoàn tiền thành công', '');
        } else {
            setDevStatus('Sẵn sàng', '');
        }

    } catch (err) {
        hideTyping();
        appendMessage('⚠️ Lỗi kết nối server. Vui lòng kiểm tra backend đang chạy.', 'system');
        setDevStatus('Lỗi kết nối!', 'error');
        console.error(err);
    }

    isWaiting = false;
}

async function resetSession() {
    try {
        await fetch(`${API_BASE}/api/reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId }),
        });
    } catch (e) {
        console.error('Reset failed:', e);
    }
    sessionId = crypto.randomUUID();
}

// ============================================================
// APP LOGIC
// ============================================================

function resetApp() {
    const scenario = scenarioSelector.value;
    currentBookingCode = SCENARIO_MAP[scenario];

    // Reset UI
    screenChat.classList.remove('active');
    screenBooking.classList.add('active');
    handoffOverlay.classList.add('hidden');
    clearQuickActions();

    // Clear chat messages
    Array.from(chatBox.querySelectorAll('.message:not(.typing-indicator), .system-msg')).forEach(m => m.remove());

    // Update booking screen
    uiFlightStatus.innerText = SCENARIO_STATUS[scenario];

    // Reset backend session
    resetSession();
    setDevStatus(`Sẵn sàng — ${currentBookingCode}`, '');
}

function startChat() {
    const scenario = scenarioSelector.value;

    screenBooking.classList.remove('active');
    screenChat.classList.add('active');

    // Gửi tin nhắn đầu tiên tự động (giả lập user vừa bấm "Trợ Giúp Khẩn Cấp")
    const initMessage = `Tôi cần hỗ trợ khẩn cấp! Mã đặt vé của tôi là ${currentBookingCode}. Vé chuyến bay VN123 của tôi bị hủy và tôi rất lo lắng.`;
    appendMessage(initMessage, 'user');
    sendMessage(initMessage).then(() => {
        // Hiển thị quick actions sau khi AI trả lời
        renderQuickActions(scenario);
    });
}

// ============================================================
// EVENT LISTENERS
// ============================================================

btnRestartApp.addEventListener('click', resetApp);

btnSupport.addEventListener('click', startChat);

btnBack.addEventListener('click', () => {
    screenChat.classList.remove('active');
    screenBooking.classList.add('active');
});

btnCloseHandoff.addEventListener('click', () => {
    handoffOverlay.classList.add('hidden');
});

function handleUserInput() {
    const text = chatInput.value.trim();
    if (!text || isWaiting) return;
    appendMessage(text, 'user');
    chatInput.value = '';
    clearQuickActions();
    sendMessage(text);
}

btnSend.addEventListener('click', handleUserInput);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleUserInput();
});

// Init
resetApp();
