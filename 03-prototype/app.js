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

// Dev Panel
const scenarioSelector = document.getElementById('scenario-selector');
const btnRestartApp = document.getElementById('btn-restart-app');

let currentScenario = 'happy';

// Mock Data logic for different paths
const SCENARIOS = {
    happy: {
        flightStatus: "ĐÃ HỦY",
        initMessage: "Hệ thống ghi nhận vé chuyến bay <b>VN123</b> của bạn bị hủy do lỗi từ cổng thanh toán đối tác (Mã lỗi: GATEWAY_TIMEOUT_PARTNER). <br><br>Đừng lo lắng, số tiền <b>2,500,000đ</b> của bạn vẫn an toàn và chưa bị trừ vào tài khoản.",
        actions: [
            { text: "✨ Hoàn tiền tự động", handler: () => triggerAutoRefund() },
            { text: "Tôi muốn đặt lại vé", handler: () => appendMessage("Chức năng đặt lại vé đang phát triển.", 'bot') }
        ]
    },
    low_confidence: {
        flightStatus: "ĐANG XỬ LÝ",
        initMessage: "Hệ thống ghi nhận trạng thái vé <b>VN123</b> có sự cố nhưng chưa rõ nguyên nhân (Mã lỗi: UNKNOWN_REASON). AI không thể tự động hoàn tiền trong trường hợp này.",
        actions: [
            { text: "🔀 Đổi chuyến tương đương", handler: () => appendMessage("Hệ thống đã tìm thấy chuyến bay VN456 lúc 18:00. Bạn có muốn đổi miễn phí sang chuyến này không?", 'bot') },
            { text: "🆘 Gặp nhân viên (Khẩn cấp)", urgent: true, handler: () => triggerBypass("P1") }
        ]
    },
    failure: {
        flightStatus: "ĐÃ HỦY",
        initMessage: "Xin chào, chuyến bay VN123 của bạn đã bị hủy. Bạn cần hỗ trợ gì?",
        actions: []
    },
    correction: {
        flightStatus: "ĐÃ HỦY",
        initMessage: "Vé VN123 (Khởi hành: 15:30 ngày 15/10/2026 - Còn 2 tháng) đã bị hủy. Mức độ ưu tiên của vé này là P3 (Thấp). Hệ thống sẽ xử lý hoàn tiền trong 7 ngày làm việc.",
        actions: [
            { text: "Sửa sai! Chuyến bay là hôm nay", urgent: true, handler: () => triggerCorrection() },
            { text: "Đồng ý", handler: () => appendMessage("Đã xác nhận.", 'bot') }
        ]
    }
};

// Application Reset
function resetApp() {
    currentScenario = scenarioSelector.value;
    
    // Reset UI
    screenChat.classList.remove('active');
    screenBooking.classList.add('active');
    handoffOverlay.classList.add('hidden');
    
    // Reset Chat Box
    Array.from(chatBox.querySelectorAll('.message:not(.typing-indicator)')).forEach(msg => msg.remove());
    clearQuickActions();
    
    // Apply Scenario Data to Screen 1
    uiFlightStatus.innerText = SCENARIOS[currentScenario].flightStatus;
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
});

btnCloseHandoff.addEventListener('click', () => {
    handoffOverlay.classList.add('hidden');
});

// Chat Functions
function appendMessage(text, sender, isUrgent = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-msg ${isUrgent ? 'urgent' : ''}`;
    msgDiv.innerHTML = `<div class="bubble">${text}</div>`;
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
            appendMessage(action.text, 'user');
            clearQuickActions();
            action.handler();
        });
        quickActions.appendChild(btn);
    });
}

function clearQuickActions() {
    quickActions.innerHTML = '';
}

// AI Flow Logic
function startAIAnalysis() {
    typingIndicator.style.display = 'block';
    chatBox.scrollTop = chatBox.scrollHeight;

    setTimeout(() => {
        typingIndicator.style.display = 'none';
        
        const scenarioData = SCENARIOS[currentScenario];
        appendMessage(scenarioData.initMessage, 'bot');
        
        if (scenarioData.actions.length > 0) {
            renderQuickActions(scenarioData.actions);
        }
    }, 1500);
}

// Sub-flows
function triggerAutoRefund() {
    typingIndicator.style.display = 'block';
    setTimeout(() => {
        typingIndicator.style.display = 'none';
        appendMessage("✅ <b>Thành công!</b> Hệ thống đã hủy lệnh trừ tiền của đối tác. Tiền sẽ hoàn về tài khoản của bạn trong vòng 5-10 phút. Trip.com thành thật xin lỗi vì sự cố không đáng có này.", 'bot');
    }, 1500);
}

function triggerCorrection() {
    typingIndicator.style.display = 'block';
    setTimeout(() => {
        typingIndicator.style.display = 'none';
        appendMessage("⚠️ Xin lỗi bạn, AI đã đọc nhầm ngày bay. Đã cập nhật lại mức độ khẩn cấp thành P0 (Cao nhất). Hệ thống đang kích hoạt kết nối khẩn cấp tới nhân viên trực ban...", 'system');
        setTimeout(() => triggerBypass("P0"), 2000);
    }, 1500);
}

function triggerBypass(priority = "P0") {
    appendMessage(`🆘 AI đã tạo mã khẩn cấp [${priority}_123]. Chuyển toàn bộ lịch sử chat cho nhân viên...`, 'system');
    handoffMessage.innerText = `AI đã ghi nhận tính huống khẩn cấp (${priority}). Vui lòng giữ máy, nhân viên hỗ trợ sẽ có mặt trong 30 giây...`;
    handoffOverlay.classList.remove('hidden');
}

// User Input Handling
function handleUserInput() {
    const text = chatInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user');
    chatInput.value = '';
    clearQuickActions();

    typingIndicator.style.display = 'block';
    chatBox.scrollTop = chatBox.scrollHeight;

    setTimeout(() => {
        typingIndicator.style.display = 'none';
        
        // Luồng Failure: Bắt lỗi khi khách gõ lung tung và AI không hiểu (thay vì xin lỗi vô ích)
        if (currentScenario === 'failure') {
            appendMessage("Xin lỗi, tôi chưa hiểu rõ yêu cầu của bạn. Nhưng tôi nhận thấy bạn đang gặp sự cố hủy vé. Để tránh mất thời gian, tôi đang kết nối trực tiếp với nhân viên thật...", 'bot');
            setTimeout(() => triggerBypass("P0"), 2000);
            return;
        }

        // Bẫy khẩn cấp chung cho mọi kịch bản
        const bypassWords = ['khẩn cấp', 'sân bay', 'cứu', 'gấp', 'người thật', 'nhân viên'];
        const isBypass = bypassWords.some(word => text.toLowerCase().includes(word));

        if (isBypass) {
            triggerBypass("P0");
        } else {
            appendMessage("AI hiểu bạn đang nói: " + text + ". Vui lòng chọn các thao tác trên hoặc gõ 'Khẩn cấp'.", 'bot');
        }
    }, 1000);
}

btnSend.addEventListener('click', handleUserInput);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleUserInput();
});

// Init
resetApp();
