/**
 * Karien — App Bootstrap
 * 
 * Initializes all UI modules and handles tab switching.
 * Waits for pywebview API to be ready before fetching backend data.
 */

// ───── TAB SWITCHING ─────
function switchTab(name) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-tab="${name}"]`).classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + name).classList.add('active');
}

// ───── BOOT SEQUENCE ─────
document.addEventListener('DOMContentLoaded', () => {
    // Initialize modules (these work offline / without pywebview)
    initAvatar();
    initConsole();

    // Wait for pywebview API bridge (shared helper in util.js),
    // then load dynamic data
    if (window.pywebview) {
        waitForApi().then(() => {
            initSettings();
            loadStatus();
        });
    } else {
        // Running in a normal browser (dev/preview mode) — use mock data
        initSettingsMock();
    }
});

/**
 * Load app-wide status (version, online state, MCP count).
 */
async function loadStatus() {
    try {
        const status = await pywebview.api.get_status();
        document.getElementById('sidebar-version').textContent = status.version || 'v0.2.0';
    } catch (e) {
        console.warn('Failed to load status:', e);
    }
}
