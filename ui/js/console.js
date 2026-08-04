/**
 * Karien — Console Module
 *
 * Manages console log display (append-only, DOM-capped), auto-scroll,
 * and command sending.
 */

// Hard cap on rendered log entries: oldest DOM nodes are dropped beyond this.
const MAX_LOG_ENTRIES = 500;

/**
 * Initialize console: render the boot log line and bind events.
 */
function initConsole() {
    addLog('info', 'System initialized. Waiting for backend...');

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
 * Appends exactly one DOM node; never re-renders the whole list.
 * @param {string} level - 'info' | 'user' | 'llm' | 'tool' | 'tts' | 'error' | 'mcp'
 * @param {string} message - The log message
 */
function addLog(level, message) {
    const area = document.getElementById('logArea');
    if (!area) return;

    const entry = document.createElement('div');
    entry.className = 'log-entry';

    const time = document.createElement('span');
    time.className = 'log-time';
    time.textContent = now();

    const badge = document.createElement('span');
    badge.className = 'log-badge ' + level;
    badge.textContent = String(level).toUpperCase();

    const msg = document.createElement('span');
    msg.className = 'log-msg';
    msg.textContent = message;

    entry.appendChild(time);
    entry.appendChild(badge);
    entry.appendChild(msg);
    area.appendChild(entry);

    // Cap the DOM: drop oldest entries beyond the limit
    while (area.childElementCount > MAX_LOG_ENTRIES) {
        area.removeChild(area.firstChild);
    }

    // Auto-scroll if enabled
    const toggle = document.querySelector('.toggle-track');
    if (toggle && toggle.classList.contains('on')) {
        area.scrollTop = area.scrollHeight;
    }
}

/**
 * Clear all logs.
 */
function clearLogs() {
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
        } else if (cmd === '/wake') {
            // Demo the overlay avatar without the microphone (slide-in + listen)
            if (window.pywebview && window.pywebview.api) {
                try {
                    await pywebview.api.simulate_wake();
                    addLog('info', 'Overlay avatar: wake (slide-in + listen)');
                } catch (e) {
                    addLog('error', `Wake failed: ${e}`);
                }
            } else {
                addLog('error', 'Backend not available (browser preview mode).');
            }
        } else if (cmd === '/sleep') {
            // Demo the overlay avatar goodbye (slide-out + hide)
            if (window.pywebview && window.pywebview.api) {
                try {
                    await pywebview.api.simulate_sleep();
                    addLog('info', 'Overlay avatar: sleep (slide-out + hide)');
                } catch (e) {
                    addLog('error', `Sleep failed: ${e}`);
                }
            } else {
                addLog('error', 'Backend not available (browser preview mode).');
            }
        } else if (cmd === '/help') {
            addLog('info', 'Commands: /mood [name] | /state [name] | /wake | /sleep | /help');
            addLog('info', 'Moods: neutral, happy, sad, annoyed, embarrassed, proud, curious, excited, sleepy');
            addLog('info', 'States: idle, listening, thinking, speaking');
            addLog('info', '/wake and /sleep demo the overlay avatar (no mic needed).');
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
