/**
 * Karien — Shared UI helpers
 *
 * Loaded before every page module (index, overlay, wizard) so all three
 * share a single copy of the tiny cross-page utilities.
 */

/**
 * Wait for pywebview.api to become available.
 * pywebview injects the `api` object asynchronously after page load.
 * @returns {Promise<void>} resolves once window.pywebview.api exists
 */
function waitForApi() {
    return new Promise((resolve) => {
        if (window.pywebview && window.pywebview.api) {
            resolve();
            return;
        }
        // Poll every 100ms until the bridge is injected
        const interval = setInterval(() => {
            if (window.pywebview && window.pywebview.api) {
                clearInterval(interval);
                resolve();
            }
        }, 100);
    });
}
