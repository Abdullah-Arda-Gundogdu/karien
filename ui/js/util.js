/**
 * Karien — Shared UI helpers
 *
 * Loaded before every page module (index, overlay, wizard) so all three
 * share a single copy of the tiny cross-page utilities.
 */

/**
 * Wait for pywebview.api to become available.
 *
 * pywebview injects `window.pywebview` asynchronously AFTER page load, so
 * checking its presence at DOMContentLoaded is a race — the real app can
 * wrongly look like browser-preview mode. Always await this instead.
 *
 * @param {number} [timeoutMs] - optional; resolve false if the bridge never
 *   appears within this window (browser preview mode). Omit to wait forever.
 * @returns {Promise<boolean>} true = bridge ready, false = timed out
 */
function waitForApi(timeoutMs) {
    return new Promise((resolve) => {
        if (window.pywebview && window.pywebview.api) {
            resolve(true);
            return;
        }
        let timer = null;
        const interval = setInterval(() => {
            if (window.pywebview && window.pywebview.api) {
                clearInterval(interval);
                if (timer) clearTimeout(timer);
                resolve(true);
            }
        }, 50);
        if (timeoutMs) {
            timer = setTimeout(() => {
                clearInterval(interval);
                resolve(false);
            }, timeoutMs);
        }
    });
}
