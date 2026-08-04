/* ═══════════════════════════════════════
   Karien — Toast bildirimleri
   showToast(mesaj, tur) — tur: 'info' (varsayılan) | 'success' | 'warn' | 'error'
   Stiller: css/components.css (.toast-stack, .toast, .toast--*)
   ═══════════════════════════════════════ */

(function () {
    'use strict';

    var VISIBLE_MS = 3000;   // toast'un ekranda kalma süresi
    var LEAVE_MS = 320;      // çıkış animasyonunun süresi (css --dur-med + pay)

    function getStack() {
        var stack = document.querySelector('.toast-stack');
        if (!stack) {
            stack = document.createElement('div');
            stack.className = 'toast-stack';
            document.body.appendChild(stack);
        }
        return stack;
    }

    /**
     * Kısa ömürlü bildirim göster.
     * @param {string} message - gösterilecek metin (düz metin; textContent ile basılır)
     * @param {string} [kind] - 'info' | 'success' | 'warn' | 'error'
     */
    window.showToast = function (message, kind) {
        var toast = document.createElement('div');
        toast.className = 'toast' +
            (kind && kind !== 'info' ? ' toast--' + kind : '');
        toast.setAttribute('role', 'status');
        toast.textContent = message;

        getStack().appendChild(toast);

        setTimeout(function () {
            toast.classList.add('is-leaving');
            setTimeout(function () {
                toast.remove();
            }, LEAVE_MS);
        }, VISIBLE_MS);
    };
})();
