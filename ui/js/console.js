/**
 * Karien — Console Module
 * 
 * Manages console log display, auto-scroll, and command sending.
 */

let _logs = [];

/**
 * Initialize console: render placeholder logs and bind events.
 */
function initConsole() {
    // Start with some placeholder logs
    _logs = [
        { time: now(), type: 'info', msg: 'System initialized. Waiting for backend...' },
    ];
    renderLogs();

    // Bind send button
    const sendBtn = document.querySelector('.send-btn');
    const input = document.querySelector('.console-input');
    if (sendBtn && input) {
        sendBtn.addEventListener('click', () => sendCommand(input));
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendCommand(input);
        });
    }
}

/**
 * Add a log entry (called from Python via evaluate_js).
 * @param {string} level - 'info' | 'user' | 'llm' | 'tool' | 'tts' | 'error' | 'mcp'
 * @param {string} message - The log message
 */
function addLog(level, message) {
    _logs.push({ time: now(), type: level, msg: message });
    renderLogs();

    // Auto-scroll if enabled
    const toggle = document.querySelector('.toggle-track');
    if (toggle && toggle.classList.contains('on')) {
        const area = document.getElementById('logArea');
        if (area) area.scrollTop = area.scrollHeight;
    }
}

/**
 * Render all logs to the log area.
 */
function renderLogs() {
    const area = document.getElementById('logArea');
    if (!area) return;
    area.innerHTML = _logs.map(l => `
    <div class="log-entry">
      <span class="log-time">${l.time}</span>
      <span class="log-badge ${l.type}">${l.type.toUpperCase()}</span>
      <span class="log-msg">${escapeHtml(l.msg)}</span>
    </div>
  `).join('');
}

/**
 * Clear all logs.
 */
function clearLogs() {
    _logs = [];
    const area = document.getElementById('logArea');
    if (area) area.innerHTML = '';
}

/**
 * Send a text command from the console input.
 */
async function sendCommand(input) {
    const text = input.value.trim();
    if (!text) return;

    addLog('user', `"${text}"`);
    input.value = '';

    if (window.pywebview && window.pywebview.api) {
        try {
            await pywebview.api.send_command(text);
        } catch (e) {
            addLog('error', `Failed to send: ${e}`);
        }
    }
}

// ───── HELPERS ─────

function now() {
    const d = new Date();
    return d.toLocaleTimeString('en-GB', { hour12: false });
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
