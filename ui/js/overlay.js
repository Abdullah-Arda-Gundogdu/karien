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

    function root() {
        return document.getElementById('avatar-root');
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
    };

    window.overlaySetState = function (state) {
        const r = root();
        if (r) r.dataset.state = state;
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

    function waitForApi() {
        return new Promise((resolve) => {
            if (window.pywebview && window.pywebview.api) {
                resolve();
                return;
            }
            const interval = setInterval(() => {
                if (window.pywebview && window.pywebview.api) {
                    clearInterval(interval);
                    resolve();
                }
            }, 100);
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        // In a plain browser (preview mode) keep the default 'orb' skin.
        if (!window.pywebview) return;

        waitForApi().then(async () => {
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
