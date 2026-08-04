/**
 * Karien — Console Module
 *
 * Manages console log display (append-only, DOM-capped), auto-scroll,
 * and command sending.
 */

// Hard cap on rendered log entries: oldest DOM nodes are dropped beyond this.
const MAX_LOG_ENTRIES = 500;

// The 5 real log levels → chip modifier (components.css .chip family).
// Anything else (unknown/legacy levels) falls back to 'info'.
const LOG_LEVEL_CHIPS = {
    info: '',
    user: 'chip--sakura',
    llm: 'chip--lavanta',
    tool: 'chip--peach',
    error: 'chip--coral'
};

/**
 * Initialize console: render the boot log line and bind events.
 */
function initConsole() {
    addLog('info', t('console.init'));

    // Bind send button
    const sendBtn = document.getElementById('btn-send');
    const input = document.querySelector('.console-input');
    if (sendBtn && input) {
        sendBtn.addEventListener('click', () => sendCommand(input));
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendCommand(input);
        });
    }

    // Toolbar: clear button + auto-scroll toggle (shared .toggle component)
    const clearBtn = document.getElementById('btn-clear-logs');
    if (clearBtn) clearBtn.addEventListener('click', clearLogs);

    const autoScroll = document.getElementById('autoscroll-toggle');
    if (autoScroll) {
        autoScroll.addEventListener('click', () => {
            const on = autoScroll.classList.toggle('is-on');
            autoScroll.setAttribute('aria-checked', String(on));
        });
    }
}

/**
 * Add a log entry (called from Python via evaluate_js).
 * Appends exactly one DOM node; never re-renders the whole list.
 * @param {string} level - 'info' | 'user' | 'llm' | 'tool' | 'error'
 *                         (unknown levels are rendered as 'info')
 * @param {string} message - The log message
 */
function addLog(level, message) {
    const area = document.getElementById('logArea');
    if (!area) return;

    const lvl = Object.prototype.hasOwnProperty.call(LOG_LEVEL_CHIPS, level)
        ? level : 'info';

    const entry = document.createElement('div');
    entry.className = 'log-entry';

    const time = document.createElement('span');
    time.className = 'log-time';
    time.textContent = now();

    const badge = document.createElement('span');
    badge.className = 'chip log-chip' + (LOG_LEVEL_CHIPS[lvl] ? ' ' + LOG_LEVEL_CHIPS[lvl] : '');
    badge.textContent = lvl.toUpperCase();

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
    const toggle = document.getElementById('autoscroll-toggle');
    if (toggle && toggle.classList.contains('is-on')) {
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
                addLog('info', t('console.moodSet', { mood: arg }));
            } else {
                addLog('info', t('console.moodList'));
            }
        } else if (cmd === '/state') {
            if (arg) {
                updateStatus(arg);
                addLog('info', t('console.stateSet', { state: arg }));
            } else {
                addLog('info', t('console.stateList'));
            }
        } else if (cmd === '/wake') {
            // Demo the overlay avatar without the microphone (slide-in + listen)
            if (window.pywebview && window.pywebview.api) {
                try {
                    await pywebview.api.simulate_wake();
                    addLog('info', t('console.wakeOk'));
                } catch (e) {
                    addLog('error', t('console.wakeFail', { error: e }));
                }
            } else {
                addLog('error', t('console.noBackend'));
            }
        } else if (cmd === '/sleep') {
            // Demo the overlay avatar goodbye (slide-out + hide)
            if (window.pywebview && window.pywebview.api) {
                try {
                    await pywebview.api.simulate_sleep();
                    addLog('info', t('console.sleepOk'));
                } catch (e) {
                    addLog('error', t('console.sleepFail', { error: e }));
                }
            } else {
                addLog('error', t('console.noBackend'));
            }
        } else if (cmd === '/help') {
            addLog('info', t('console.helpCommands'));
            addLog('info', t('console.moodList'));
            addLog('info', t('console.stateList'));
            addLog('info', t('console.helpWakeSleep'));
            addLog('info', t('console.helpChat'));
        } else {
            addLog('error', t('console.unknownCommand', { cmd: cmd }));
        }
        return;
    }

    // ── Regular text → send to LLM ──
    addLog('user', `"${text}"`);

    if (window.pywebview && window.pywebview.api) {
        try {
            await pywebview.api.send_command(text);
        } catch (e) {
            addLog('error', t('console.sendFail', { error: e }));
        }
    }
}

// ───── HELPERS ─────

function now() {
    const d = new Date();
    return d.toLocaleTimeString('en-GB', { hour12: false });
}
