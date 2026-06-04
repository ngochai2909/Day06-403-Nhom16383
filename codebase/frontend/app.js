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
const paymentOverlay = document.getElementById('payment-overlay');
const paymentQrImage = document.getElementById('payment-qr-image');
const paymentDescription = document.getElementById('payment-description');
const paymentTransferNote = document.getElementById('payment-transfer-note');
const btnCancelPayment = document.getElementById('btn-cancel-payment');
const btnConfirmPayment = document.getElementById('btn-confirm-payment');
const uiFlightStatus = document.getElementById('ui-flight-status');
const handoffMessage = document.getElementById('handoff-message');
const scenarioSelector = document.getElementById('scenario-selector');
const btnRestartApp = document.getElementById('btn-restart-app');
const statusBadgeScenario = document.getElementById('status-badge-scenario');
const statusBadgeBooking = document.getElementById('status-badge-booking');

if (typeof marked !== 'undefined') {
    marked.setOptions({ breaks: true, gfm: true });
}

function renderMarkdown(text) {
    if (typeof marked !== 'undefined') return marked.parse(text);
    return text.replace(/\n/g, '<br>');
}

let currentScenario = 'happy';
let sessionId = null;
let isWaiting = false;
let hasSentFirstUserMessage = false;
let currentBookingCode = null;
let pendingPayment = null;
let pendingEscalation = null;

const SCENARIO_STATUS = {
    happy: 'ĐÃ HỦY',
    low_confidence: 'ĐANG XỬ LÝ',
    failure: 'ĐÃ HỦY',
    correction: 'ĐÃ HỦY',
    clean_case_1: 'XÁC NHẬN',
    clean_case_2: 'XÁC NHẬN',
    clean_case_3: 'XÁC NHẬN',
    clean_surcharge: 'XÁC NHẬN',
    clean_refund: 'XÁC NHẬN',
    clean_extra_fee: 'XÁC NHẬN',
    clean_mixed_1: 'XÁC NHẬN',
    clean_mixed_2: 'XÁC NHẬN',
};

const SCENARIO_ACTIONS = {
    happy: [{ text: 'Yêu cầu hoàn tiền qua nhân viên' }, { text: 'Xem chuyến bay thay thế' }],
    low_confidence: [{ text: '🔀 Tôi muốn đổi chuyến bay' }, { text: '🆘 Chuyển nhân viên ngay', urgent: true }],
    failure: [{ text: 'Khẩn cấp, tôi đang ở sân bay', urgent: true }],
    correction: [{ text: 'Sai rồi! Chuyến bay của tôi là hôm nay', urgent: true }, { text: 'Xem chuyến bay thay thế' }],
    clean_case_1: [{ text: 'Tôi muốn đổi chuyến bay' }],
    clean_case_2: [{ text: 'Kiểm tra thông tin chuyến bay giúp tôi' }, { text: 'Xem chuyến bay thay thế' }],
    clean_case_3: [{ text: 'Tôi muốn đổi chuyến bay' }],
    clean_surcharge: [{ text: 'Xem chuyến bay thay thế' }, { text: 'Tôi muốn đổi chuyến bay' }],
    clean_refund: [{ text: 'Xem chuyến bay thay thế' }, { text: 'Đổi sang chuyến ít phí hơn' }],
    clean_extra_fee: [{ text: 'Xem chuyến bay thay thế' }, { text: 'Chi tiết phí đổi chuyến' }],
    clean_mixed_1: [{ text: 'Xem chuyến bay thay thế' }, { text: 'So sánh phương án đổi chuyến' }],
    clean_mixed_2: [{ text: 'Xem chuyến bay thay thế' }, { text: 'Tôi muốn tối ưu chi phí đổi chuyến' }],
};

function escapeHtml(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function resetApp() {
    syncScenarioFromPanel({ preserveActiveScreen: false });
}

function syncScenarioFromPanel({ preserveActiveScreen = true } = {}) {
    currentScenario = scenarioSelector.value;
    sessionId = null;
    isWaiting = false;
    hasSentFirstUserMessage = false;
    currentBookingCode = null;
    pendingPayment = null;
    pendingEscalation = null;
    handoffOverlay.classList.add('hidden');
    paymentOverlay.classList.add('hidden');

    if (!preserveActiveScreen) {
        screenChat.classList.remove('active');
        screenBooking.classList.add('active');
    }

    Array.from(chatBox.querySelectorAll('.message:not(.typing-indicator)')).forEach((msg) => msg.remove());
    clearQuickActions();
    uiFlightStatus.innerText = SCENARIO_STATUS[currentScenario] || 'ĐÃ HỦY';
    statusBadgeScenario.textContent = `Scenario: ${currentScenario}`;
    statusBadgeBooking.textContent = 'Booking: --';

    // Nếu user đang đứng ở màn chat, sync ngay và mở greeting mới theo scenario vừa chọn.
    if (preserveActiveScreen && screenChat.classList.contains('active')) {
        startAIAnalysis();
    }
}

function appendMessage(text, sender, isUrgent = false) {
    const msgDiv = document.createElement('div');
    if (sender === 'system') {
        msgDiv.className = 'system-msg';
        msgDiv.innerHTML = text;
    } else if (sender === 'bot') {
        msgDiv.className = `message bot-msg ${isUrgent ? 'urgent' : ''}`;
        const bubble = document.createElement('div');
        bubble.className = 'bubble markdown-body';
        bubble.innerHTML = renderMarkdown(text);
        msgDiv.appendChild(bubble);
    } else {
        msgDiv.className = `message ${sender}-msg ${isUrgent ? 'urgent' : ''}`;
        msgDiv.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
    }
    chatBox.insertBefore(msgDiv, typingIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function appendFlightOptions(flights, bookingCode) {
    if (!flights || flights.length === 0) {
        appendMessage('Hiện chưa có chuyến bay thay thế khả dụng.', 'bot');
        return;
    }
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-msg flight-options-msg';
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = '<div class="flight-options-title">Danh sách chuyến bay thay thế (chạm để đổi chuyến):</div>';

    flights.forEach((flight) => {
        const card = document.createElement('button');
        card.className = 'flight-option-btn';
        const diff = Number(flight.price_difference || 0);
        const diffText = diff === 0 ? 'Không phụ thu' : diff > 0 ? `+${diff.toLocaleString('vi-VN')}đ` : `${diff.toLocaleString('vi-VN')}đ`;
        card.innerHTML = `
            <div class="flight-head">
                <strong>${escapeHtml(flight.flight)}</strong>
                <span class="price-diff">${escapeHtml(diffText)}</span>
            </div>
            <div>${escapeHtml(flight.route)} | ${escapeHtml(flight.departure)} - ${escapeHtml(flight.arrival)}</div>
            <div>Ghế: ${escapeHtml(flight.seat_available)} | ID: ${escapeHtml(flight.flight_id)}</div>
        `;
        card.addEventListener('click', () => handleFlightSelection(bookingCode, flight));
        bubble.appendChild(card);
    });
    msgDiv.appendChild(bubble);
    chatBox.insertBefore(msgDiv, typingIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function renderQuickActions(actions) {
    quickActions.innerHTML = '';
    actions.forEach((action) => {
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

function triggerHandoff(priority = 'P0', ticketId = 'N/A') {
    appendMessage(`🆘 Đã tạo mã khẩn cấp [${escapeHtml(ticketId)} - ${escapeHtml(priority)}]. Chuyển lịch sử chat cho nhân viên...`, 'system');
    handoffMessage.innerText = `Ticket ${ticketId} (${priority}) đã được tạo. Vui lòng giữ máy, nhân viên hỗ trợ sẽ có mặt trong 30 giây...`;
    handoffOverlay.classList.remove('hidden');
}

async function callChatAPI(message) {
    const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function fetchFlightOptions(bookingCode) {
    const res = await fetch(`/api/flight-options/${bookingCode}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function callRebookAPI(bookingCode, flightId) {
    const res = await fetch('/api/rebook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_code: bookingCode, flight_id: flightId }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function callEscalationConfirmAPI(escalationPayload) {
    const res = await fetch('/api/escalate-confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(escalationPayload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

function formatVnd(amount) {
    return `${Math.abs(Number(amount || 0)).toLocaleString('vi-VN')}đ`;
}

function buildPaymentQrUrl({ bookingCode, flightId, amount }) {
    const transferContent = `REBOOK ${bookingCode} ${flightId}`;
    const payload = `BANK: TPBANK | ACC: 190036868686 | AMOUNT: ${amount} | NOTE: ${transferContent}`;
    return `https://api.qrserver.com/v1/create-qr-code/?size=260x260&data=${encodeURIComponent(payload)}`;
}

function openPaymentModal(bookingCode, flight) {
    const surcharge = Number(flight.price_difference || 0);
    const transferContent = `REBOOK ${bookingCode} ${flight.flight_id}`;
    pendingPayment = { bookingCode, flight };
    paymentDescription.textContent = `Chuyến ${flight.flight} có phụ thu ${formatVnd(surcharge)}. Vui lòng thanh toán để xác nhận đổi chuyến.`;
    paymentTransferNote.innerHTML = `<strong>Nội dung:</strong> ${escapeHtml(transferContent)}`;
    paymentQrImage.src = buildPaymentQrUrl({ bookingCode, flightId: flight.flight_id, amount: surcharge });
    paymentOverlay.classList.remove('hidden');
}

function closePaymentModal() {
    pendingPayment = null;
    paymentOverlay.classList.add('hidden');
}

function createVoucherCode(bookingCode) {
    const suffix = Math.random().toString(36).slice(2, 7).toUpperCase();
    return `VC-${bookingCode?.slice(-4) || '0000'}-${suffix}`;
}

function showRefundVoucher(bookingCode, refundAmount) {
    const voucherCode = createVoucherCode(bookingCode);
    appendMessage(
        `🎁 Bạn đã đổi sang chuyến rẻ hơn nên được hoàn ${formatVnd(refundAmount)} dưới dạng voucher.\n\n` +
        `**Mã voucher:** \`${voucherCode}\`\n` +
        `Hiệu lực: 30 ngày, áp dụng cho đơn đặt vé tiếp theo.`,
        'bot'
    );
}

function renderEscalationConfirmActions() {
    if (!pendingEscalation) return;
    quickActions.innerHTML = '';

    const agreeBtn = document.createElement('button');
    agreeBtn.className = 'quick-btn urgent';
    agreeBtn.innerText = '✅ Đồng ý gọi nhân viên';
    agreeBtn.addEventListener('click', () => confirmEscalation());

    const rejectBtn = document.createElement('button');
    rejectBtn.className = 'quick-btn';
    rejectBtn.innerText = '❎ Chưa cần';
    rejectBtn.addEventListener('click', () => cancelEscalation());

    quickActions.appendChild(agreeBtn);
    quickActions.appendChild(rejectBtn);
}

async function confirmEscalation() {
    if (!pendingEscalation || isWaiting) return;
    isWaiting = true;
    typingIndicator.style.display = 'block';
    try {
        const result = await callEscalationConfirmAPI(pendingEscalation);
        typingIndicator.style.display = 'none';
        isWaiting = false;
        clearQuickActions();
        pendingEscalation = null;
        appendMessage(result.message, 'system');
        triggerHandoff(result.priority || 'P0', result.ticket_id || 'ESC-UNKNOWN');
    } catch (e) {
        typingIndicator.style.display = 'none';
        isWaiting = false;
        appendMessage('Không thể kết nối nhân viên lúc này. Vui lòng thử lại.', 'bot', true);
    }
}

function cancelEscalation() {
    pendingEscalation = null;
    clearQuickActions();
    appendMessage('Đã ghi nhận: bạn chưa muốn gọi nhân viên lúc này. Mình sẽ tiếp tục hỗ trợ bằng AI.', 'system');
    renderQuickActions(SCENARIO_ACTIONS[currentScenario] || []);
}

function isAffirmativeEscalationText(text) {
    const t = (text || '').trim().toLowerCase();
    const affirmativePhrases = [
        'có',
        'ok',
        'oke',
        'yes',
        'đồng ý',
        'dong y',
        'gọi cho tôi',
        'goi cho toi',
        'kết nối nhân viên',
        'ket noi nhan vien',
        'chuyển nhân viên',
        'chuyen nhan vien',
        'gọi nhân viên',
        'goi nhan vien',
        'xác nhận',
        'xac nhan',
    ];
    return affirmativePhrases.some((phrase) => t === phrase || t.includes(phrase));
}

function isNegativeEscalationText(text) {
    const t = (text || '').trim().toLowerCase();
    const negativePhrases = [
        'không',
        'khong',
        'chưa',
        'chua',
        'chưa cần',
        'chua can',
        'không cần',
        'khong can',
        'để sau',
        'de sau',
    ];
    return negativePhrases.some((phrase) => t === phrase || t.includes(phrase));
}

async function showAlternativeFlights() {
    if (!currentBookingCode) {
        appendMessage('Hiện chưa xác định được mã booking để tìm chuyến thay thế.', 'bot');
        return;
    }
    typingIndicator.style.display = 'block';
    try {
        const options = await fetchFlightOptions(currentBookingCode);
        typingIndicator.style.display = 'none';
        appendFlightOptions(options.flights || [], currentBookingCode);
    } catch (e) {
        typingIndicator.style.display = 'none';
        appendMessage('Không thể tải danh sách chuyến bay thay thế lúc này.', 'bot');
    }
}

async function handleFlightSelection(bookingCode, flight) {
    const surcharge = Number(flight.price_difference || 0);
    if (surcharge > 0) {
        openPaymentModal(bookingCode, flight);
        return;
    }
    await confirmRebook(bookingCode, flight);
}

async function confirmRebook(bookingCode, flight) {
    if (isWaiting) return;
    isWaiting = true;
    typingIndicator.style.display = 'block';
    try {
        const result = await callRebookAPI(bookingCode, flight.flight_id);
        typingIndicator.style.display = 'none';
        isWaiting = false;
        if (result.status === 'CONFIRMED') {
            appendMessage(`✅ ${result.message}`, 'bot');
            appendMessage(`Mã mới: ${result.new_booking_code} | Chuyến: ${result.flight} | Ghế: ${result.seat}`, 'system');
            const priceDiff = Number(flight.price_difference || 0);
            if (priceDiff < 0) {
                showRefundVoucher(bookingCode, Math.abs(priceDiff));
            }
        } else {
            appendMessage(`⚠️ ${result.message || 'Không thể đổi chuyến lúc này.'}`, 'bot', true);
        }
    } catch (e) {
        typingIndicator.style.display = 'none';
        isWaiting = false;
        appendMessage('Lỗi khi đổi chuyến. Vui lòng thử lại sau.', 'bot');
    }
}

function shouldOpenFlightOptions(text) {
    const lowered = text.toLowerCase();
    return lowered.includes('đổi chuyến') || lowered.includes('chuyen bay') || lowered.includes('chuyến bay thay thế');
}

function handleChatResult(result) {
    if (result.reply) appendMessage(result.reply, 'bot');
    if (result.booking_code) {
        currentBookingCode = result.booking_code;
        statusBadgeBooking.textContent = `Booking: ${currentBookingCode}`;
    }
    if (result.available_flights && result.available_flights.length > 0) {
        appendFlightOptions(result.available_flights, currentBookingCode);
    }
    if (result.escalation_recommended) {
        pendingEscalation = {
            booking_code: currentBookingCode || result.booking_code || '',
            priority: result.escalation_priority || 'P1',
            reason: result.escalation_reason || 'Khách hàng cần hỗ trợ từ nhân viên.',
        };
        appendMessage(
            `Mình đề xuất chuyển nhân viên hỗ trợ (${pendingEscalation.priority}). Bạn có đồng ý kết nối ngay không?`,
            'system'
        );
        renderEscalationConfirmActions();
        return;
    }
}

async function startAIAnalysis() {
    sessionId = `session_${Date.now()}`;
    typingIndicator.style.display = 'block';
    chatBox.scrollTop = chatBox.scrollHeight;
    try {
        const codeRes = await fetch(`/api/booking-code/${currentScenario}`);
        const codeData = await codeRes.json();
        currentBookingCode = codeData.booking_code || null;
        statusBadgeBooking.textContent = `Booking: ${currentBookingCode || '--'}`;
        typingIndicator.style.display = 'none';
        appendMessage('Xin chào! Tôi là trợ lý AI của Trip.com. Bạn cần hỗ trợ gì ngay lúc này ạ?', 'bot');
        renderQuickActions(SCENARIO_ACTIONS[currentScenario] || []);
    } catch (e) {
        typingIndicator.style.display = 'none';
        appendMessage('Không thể kết nối hệ thống. Hãy đảm bảo server đang chạy ở localhost:8000.', 'bot');
    }
}

async function sendMessage(text) {
    if (!text || isWaiting) return;
    appendMessage(text, 'user');
    clearQuickActions();

    if (pendingEscalation) {
        if (isAffirmativeEscalationText(text)) {
            await confirmEscalation();
            return;
        }
        if (isNegativeEscalationText(text)) {
            cancelEscalation();
            return;
        }
        appendMessage('Mình đang chờ xác nhận gọi nhân viên. Bạn trả lời "đồng ý" hoặc "chưa cần" nhé.', 'system');
        renderEscalationConfirmActions();
        return;
    }

    if (shouldOpenFlightOptions(text) && currentBookingCode) {
        await showAlternativeFlights();
        renderQuickActions(SCENARIO_ACTIONS[currentScenario] || []);
        return;
    }

    let apiText = text;
    if (!hasSentFirstUserMessage && currentBookingCode) {
        apiText = `Mã đặt vé của tôi là ${currentBookingCode}. Câu hỏi của tôi: ${text}`;
        hasSentFirstUserMessage = true;
    }

    isWaiting = true;
    typingIndicator.style.display = 'block';
    chatBox.scrollTop = chatBox.scrollHeight;
    try {
        const result = await callChatAPI(apiText);
        typingIndicator.style.display = 'none';
        isWaiting = false;
        handleChatResult(result);
        if (!pendingEscalation) {
            renderQuickActions(SCENARIO_ACTIONS[currentScenario] || []);
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

btnRestartApp.addEventListener('click', resetApp);
scenarioSelector.addEventListener('change', () => syncScenarioFromPanel({ preserveActiveScreen: true }));
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
btnCloseHandoff.addEventListener('click', () => handoffOverlay.classList.add('hidden'));
btnCancelPayment.addEventListener('click', closePaymentModal);
btnConfirmPayment.addEventListener('click', async () => {
    if (!pendingPayment) return;
    const { bookingCode, flight } = pendingPayment;
    paymentOverlay.classList.add('hidden');
    pendingPayment = null;
    appendMessage(`💳 Đã ghi nhận thanh toán phụ thu ${formatVnd(flight.price_difference)}. Đang xác nhận đổi chuyến...`, 'system');
    await confirmRebook(bookingCode, flight);
});
btnSend.addEventListener('click', handleUserInput);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleUserInput();
});

resetApp();
