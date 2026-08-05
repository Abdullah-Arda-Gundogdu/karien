/**
 * Karien — Overlay Avatar Module
 *
 * Implements the JS globals the Python bridge (assistant/ui/api.py) calls
 * on this window, plus the pluggable skin loader.
 *
 * Contract (do not rename):
 *   overlaySlideIn()   overlaySlideOut()
 *   overlaySetState(s) overlaySetMood(m)
 *   overlaySetSkin(id)
 *
 * All visuals are CSS-driven: #avatar-root carries data-state
 * (hidden|listen|think|speak) and data-mood (9 moods); the active skin
 * stylesheet (ui/avatars/<id>/skin.css) reacts to those attributes.
 */

(function () {
    'use strict';

    // Mount the canonical #avatar-root (single template in avatar-dom.js).
    // Scripts sit at the end of <body>, so the body exists; mounting
    // synchronously guarantees the root is there the moment the Python
    // bridge can call any of the globals below.
    if (!document.getElementById('avatar-root') && window.AvatarDom) {
        window.AvatarDom.mount(document.body);
    }

    function root() {
        return document.getElementById('avatar-root');
    }

    // States that show a cute status label under the avatar.
    const LABELED_STATES = ['listen', 'think', 'speak'];

    /** Sync the .status-label text with the given state (i18n table). */
    function updateStatusLabel(r, state) {
        const label = r.querySelector('.status-label');
        if (!label) return;
        label.textContent =
            LABELED_STATES.includes(state) && typeof window.t === 'function'
                ? window.t('overlay.state.' + state)
                : '';
    }

    // ───── Python-called globals ─────

    window.overlaySlideIn = function () {
        const r = root();
        if (r) r.classList.add('visible');
    };

    window.overlaySlideOut = function () {
        const r = root();
        if (!r) return;
        r.classList.remove('visible');
        // Reset state so the speak mouth / status label don't linger through
        // the slide-out, and the next show doesn't flash the previous state.
        r.dataset.state = 'hidden';
        updateStatusLabel(r, 'hidden');
    };

    window.overlaySetState = function (state) {
        const r = root();
        if (!r) return;
        r.dataset.state = state;
        updateStatusLabel(r, state);
    };

    window.overlaySetMood = function (mood) {
        const r = root();
        if (r) r.dataset.mood = mood;
    };

    /**
     * Swap the active skin stylesheet.
     * Convention: every skin ships as ui/avatars/<id>/skin.css.
     */
    window.overlaySetSkin = function (skinId) {
        if (typeof skinId !== 'string' || !/^[a-zA-Z0-9_-]+$/.test(skinId)) return;
        const link = document.getElementById('skin-link');
        if (link) link.href = 'avatars/' + skinId + '/skin.css';
    };

    // ───── Boot: load the configured skin from the backend ─────
    // (waitForApi is the shared helper from util.js)

    document.addEventListener('DOMContentLoaded', () => {
        // Timeout-based wait: the bridge injects after load, so an instant
        // window.pywebview check would skip skin loading in the real app.
        // In a plain browser (timeout) the default 'orb' skin stays.
        waitForApi(5000).then(async (ready) => {
            if (!ready) return;
            try {
                const config = await pywebview.api.get_avatar();
                if (config && config.avatar) {
                    overlaySetSkin(config.avatar);
                }
            } catch (e) {
                console.warn('Avatar skin load failed, keeping default:', e);
            }
        });
    });
})();
