/**
 * Karien — App Bootstrap
 *
 * Initializes all UI modules, handles tab switching, binds the shell
 * (nav + bottom bar) and polls backend status for the sidebar.
 * Waits for pywebview API to be ready before fetching backend data.
 */

// ───── TAB SWITCHING ─────
function switchTab(name) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-tab="${name}"]`).classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + name).classList.add('active');
}

// ───── SHELL HELPERS ─────

function hasApi() {
    return !!(window.pywebview && window.pywebview.api);
}

/**
 * Reflect voice pipeline state on the mute button + sidebar mic line.
 * @param {boolean} enabled - true when the microphone pipeline is running
 */
function reflectVoiceState(enabled) {
    const btn = document.getElementById('btn-mute');
    if (btn) {
        btn.classList.toggle('muted', !enabled);
        const use = btn.querySelector('use');
        if (use) use.setAttribute('href', enabled ? '#icon-mic' : '#icon-mic-off');
        const label = btn.querySelector('span');
        if (label) label.textContent = enabled ? t('bar.mute') : t('bar.unmute');
    }
    const micLine = document.getElementById('sidebar-mic');
    if (micLine) {
        micLine.textContent = enabled ? t('sidebar.micOn') : t('sidebar.micOff');
    }
}

// ───── SHELL BINDINGS (nav + bottom bar; inline onclick yok) ─────

function bindShell() {
    // Sidebar navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => switchTab(item.dataset.tab));
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                switchTab(item.dataset.tab);
            }
        });
    });

    // ── Sustur / Sesi Aç ──
    const muteBtn = document.getElementById('btn-mute');
    if (muteBtn) {
        muteBtn.addEventListener('click', async () => {
            if (!hasApi()) { showToast(t('console.noBackend'), 'warn'); return; }
            muteBtn.disabled = true;
            try {
                const res = await pywebview.api.toggle_voice();
                reflectVoiceState(!!(res && res.enabled));
                if (res && !res.success) {
                    showToast(t('bar.muteFail', { error: res.error || '?' }), 'error');
                }
            } catch (e) {
                showToast(t('bar.muteFail', { error: e }), 'error');
            } finally {
                muteBtn.disabled = false;
            }
        });
    }

    // ── Durdur (TTS'i kes) ──
    const stopBtn = document.getElementById('btn-stop');
    if (stopBtn) {
        stopBtn.addEventListener('click', async () => {
            if (!hasApi()) { showToast(t('console.noBackend'), 'warn'); return; }
            try {
                const res = await pywebview.api.stop_speaking();
                if (res && res.success) {
                    showToast(t('bar.stopped'), 'info');
                } else {
                    showToast(t('bar.stopFail', { error: (res && res.error) || '?' }), 'error');
                }
            } catch (e) {
                showToast(t('bar.stopFail', { error: e }), 'error');
            }
        });
    }

    // ── Ekran Görüntüsü ──
    const shotBtn = document.getElementById('btn-screenshot');
    if (shotBtn) {
        shotBtn.addEventListener('click', async () => {
            if (!hasApi()) { showToast(t('console.noBackend'), 'warn'); return; }
            shotBtn.disabled = true;
            try {
                const res = await pywebview.api.take_screenshot();
                if (res && res.success) {
                    showToast(t('bar.screenshotOk'), 'success');
                } else {
                    showToast(t('bar.screenshotFail'), 'error');
                }
            } catch (e) {
                showToast(t('bar.screenshotFail'), 'error');
            } finally {
                shotBtn.disabled = false;
            }
        });
    }
}

// ───── STATUS POLL (kenar çubuğu: sürüm + mikrofon durumu) ─────

const STATUS_POLL_MS = 5000;

async function pollStatus() {
    try {
        const [status, voice] = await Promise.all([
            pywebview.api.get_status(),
            pywebview.api.get_voice_status()
        ]);
        const versionEl = document.getElementById('sidebar-version');
        if (versionEl && status && status.version) {
            versionEl.textContent = status.version;
        }
        reflectVoiceState(!!(voice && voice.enabled));
    } catch (e) {
        console.warn('Status poll failed:', e);
    }
}

// ───── BOOT SEQUENCE ─────
document.addEventListener('DOMContentLoaded', () => {
    // Initialize modules (these work offline / without pywebview)
    initAvatar();
    initConsole();
    bindShell();
    bindSettingsStatic();

    // Wait for pywebview API bridge (shared helper in util.js),
    // then load dynamic data
    if (window.pywebview) {
        waitForApi().then(() => {
            initSettings();
            pollStatus();
            setInterval(pollStatus, STATUS_POLL_MS);
        });
    } else {
        // Running in a normal browser (dev/preview mode) — honest empty states
        initSettingsPreview();
    }
});
