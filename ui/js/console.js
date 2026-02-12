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
    area.innerHTML = '';
    _logs.forEach(l => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';

        const time = document.createElement('span');
        time.className = 'log-time';
        time.textContent = l.time;

        const badge = document.createElement('span');
        badge.className = 'log-badge ' + l.type;
        badge.textContent = l.type.toUpperCase();

        const msg = document.createElement('span');
        msg.className = 'log-msg';
        msg.textContent = l.msg;

        entry.appendChild(time);
        entry.appendChild(badge);
        entry.appendChild(msg);
        area.appendChild(entry);
    });
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
 * Supports slash commands: /mood <name>, /state <name>, /help
 */
async function sendCommand(input) {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';

    // ── Slash commands (handled locally) ──
    if (text.startsWith('/')) {
        const parts = text.split(/\s+/);
        const cmd = parts[0].toLowerCase();
        const arg = parts[1] || '';

        if (cmd === '/mood') {
            if (arg) {
                setMood(arg);
                addLog('info', `Mood set to: ${arg}`);
            } else {
                addLog('info', 'Available moods: neutral, happy, sad, annoyed, embarrassed, proud, curious, excited, sleepy');
            }
        } else if (cmd === '/state') {
            if (arg) {
                setOrbState(arg);
                addLog('info', `State set to: ${arg}`);
            } else {
                addLog('info', 'Available states: idle, listening, thinking, speaking');
            }
        } else if (cmd === '/help') {
            addLog('info', 'Commands: /mood [name] | /state [name] | /help');
            addLog('info', 'Moods: neutral, happy, sad, annoyed, embarrassed, proud, curious, excited, sleepy');
            addLog('info', 'States: idle, listening, thinking, speaking');
            addLog('info', 'Anything else is sent to the LLM as a chat message.');
        } else {
            addLog('error', 'Unknown command: ' + cmd + '. Type /help for available commands.');
        }
        return;
    }

    // ── Regular text → send to LLM ──
    addLog('user', `"${text}"`);

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
