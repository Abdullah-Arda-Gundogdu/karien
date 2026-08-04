/**
 * Karien — Avatar DOM Template (single source of truth)
 *
 * The #avatar-root markup lives ONLY here; the overlay window and the
 * main-window preview stage both mount the exact same template, so the
 * skin CSS contract (ui/avatars/<id>/skin.css reacting to
 * data-state / data-mood on #avatar-root) has one canonical DOM.
 *
 * The DOM below is the superset of parts a skin may use — skins hide or
 * show parts via CSS (e.g. ears/whiskers are display:none unless the
 * skin enables them; see css/avatar-base.css).
 *
 * Contract (frozen): #avatar-root, data-state (hidden|idle|listen|think|speak),
 * data-mood (9 moods), child part class names.
 */

(function () {
    'use strict';

    var MARKUP =
        '<div class="avatar">' +
            '<div class="ear ear-l"></div>' +
            '<div class="ear ear-r"></div>' +
            '<div class="body"></div>' +
            '<div class="face">' +
                '<div class="brow brow-l"></div>' +
                '<div class="brow brow-r"></div>' +
                '<div class="eye eye-l"><div class="pupil"></div></div>' +
                '<div class="eye eye-r"><div class="pupil"></div></div>' +
                '<div class="blush blush-l"></div>' +
                '<div class="blush blush-r"></div>' +
                '<div class="whiskers whiskers-l"><span></span><span></span><span></span></div>' +
                '<div class="whiskers whiskers-r"><span></span><span></span><span></span></div>' +
                '<div class="mouth"></div>' +
            '</div>' +
        '</div>' +
        '<div class="status-label"></div>';

    window.AvatarDom = {
        /**
         * Mount the canonical #avatar-root into a container element.
         * @param {Element} el - container to append into
         * @param {{state?: string, mood?: string}=} opts - initial attributes
         *        (defaults match the overlay: hidden / neutral)
         * @returns {Element|null} the created #avatar-root
         */
        mount: function (el, opts) {
            if (!el) return null;
            var root = document.createElement('div');
            root.id = 'avatar-root';
            root.dataset.state = (opts && opts.state) || 'hidden';
            root.dataset.mood = (opts && opts.mood) || 'neutral';
            root.innerHTML = MARKUP;
            el.appendChild(root);
            return root;
        }
    };
})();
