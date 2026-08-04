/**
 * Karien — Avatar Preview (main window)
 *
 * Drives the preview stage with the SAME skin contract as the overlay:
 * data-state / data-mood attributes on #avatar-root + the active
 * avatars/<id>/skin.css (swapped via #skin-link for live preview).
 *
 * Python contract (frozen, do not rename): window.updateStatus, window.setMood.
 *
 * MOODS:  neutral, happy, sad, annoyed, embarrassed, proud, curious, excited, sleepy
 * STATES: Python/console use idle|listening|thinking|speaking;
 *         skins react to data-state idle|listen|think|speak.
 */

const STATE_MAP = { idle: 'idle', listening: 'listen', thinking: 'think', speaking: 'speak' };
const STATE_LABEL_KEYS = { idle: 'state.idle', listen: 'state.listening', think: 'state.thinking', speak: 'state.speaking' };

const VALID_MOODS = [
    'neutral', 'happy', 'sad', 'annoyed', 'embarrassed',
    'proud', 'curious', 'excited', 'sleepy'
];
const MOODS_WITH_CLOSED_EYES = ['happy', 'annoyed', 'sleepy', 'excited', 'proud'];
const MOOD_EMOJI = {
    neutral: '', happy: '😊', sad: '😢', annoyed: '😤',
    embarrassed: '😳', proud: '✨', curious: '🤔', excited: '⭐', sleepy: '😴'
};

let _avatarRoot = null;
let _currentMood = 'neutral';
let _currentState = 'idle';   // data-state form (idle|listen|think|speak)

/** Initialize the preview stage: mount the canonical avatar DOM + chips. */
function initAvatar() {
    const stage = document.getElementById('preview-stage');
    if (stage && window.AvatarDom) {
        _avatarRoot = AvatarDom.mount(stage, { state: 'idle' });
    }
    initCursorTracking();
    bindStateChips();
    loadSkinChips();
}

/** Set the preview's data-state + header status label + chip highlight. */
function setPreviewState(state) {
    _currentState = state;
    if (_avatarRoot) _avatarRoot.dataset.state = state;

    const label = document.getElementById('statusLabel');
    if (label) label.textContent = t(STATE_LABEL_KEYS[state] || 'state.idle');

    document.querySelectorAll('#state-chips .chip--action').forEach(c => {
        c.classList.toggle('is-selected', c.dataset.previewState === state);
    });
}

/** Called from Python via evaluate_js (and console /state). FROZEN name. */
function updateStatus(status) {
    const normalized = String(status).toLowerCase();
    setPreviewState(STATE_MAP[normalized] || normalized);
}

/** Called from Python via evaluate_js (and console /mood). FROZEN name. */
function setMood(mood) {
    const normalized = String(mood).toLowerCase().trim();
    if (!VALID_MOODS.includes(normalized)) {
        console.warn('Unknown mood:', mood);
        return;
    }
    _currentMood = normalized;
    if (_avatarRoot) _avatarRoot.dataset.mood = normalized;

    // Show the mood in the header label while idle
    const label = document.getElementById('statusLabel');
    if (label && _currentState === 'idle') {
        label.textContent = (t('mood.' + normalized) + ' ' + (MOOD_EMOJI[normalized] || '')).trim();
    }
}

// ───── SKIN CHIPS (Orb/Kedi — canlı önizleme + set_avatar kalıcılığı) ─────

function setSkinLink(skinId) {
    if (typeof skinId !== 'string' || !/^[a-zA-Z0-9_-]+$/.test(skinId)) return;
    const link = document.getElementById('skin-link');
    if (link) link.href = 'avatars/' + skinId + '/skin.css';
}

async function applySkin(skinId) {
    setSkinLink(skinId);   // live preview, immediately
    document.querySelectorAll('#skin-chips .chip--action').forEach(c => {
        c.classList.toggle('is-selected', c.dataset.skinId === skinId);
    });
    // Keep the settings dropdown (rendered by settings.js) in sync
    const sel = document.getElementById('avatar-skin');
    if (sel) sel.value = skinId;
    // Persist + live-apply on the overlay window
    if (window.pywebview && window.pywebview.api) {
        try {
            await pywebview.api.set_avatar(skinId);
        } catch (e) {
            console.warn('Failed to save avatar skin:', e);
        }
    }
}

async function loadSkinChips() {
    let avatar = 'orb';
    let skins = [{ id: 'orb', name: 'Orb' }, { id: 'kedi', name: 'Kedi' }];

    if (window.pywebview) {
        await waitForApi();
        try {
            const config = await pywebview.api.get_avatar();
            if (config && config.skins) {
                avatar = config.avatar || 'orb';
                skins = config.skins;
            }
        } catch (e) {
            console.warn('Avatar config load failed, using defaults:', e);
        }
    }

    const row = document.getElementById('skin-chips');
    if (!row) return;
    skins.forEach(s => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'chip chip--action' + (s.id === avatar ? ' is-selected' : '');
        chip.dataset.skinId = s.id;
        chip.textContent = s.name;
        chip.addEventListener('click', () => applySkin(s.id));
        row.appendChild(chip);
    });
    setSkinLink(avatar);
}

// ───── STATE TRY-OUT CHIPS (sadece önizlemeyi sürer) ─────

function bindStateChips() {
    document.querySelectorAll('#state-chips .chip--action').forEach(chip => {
        chip.addEventListener('click', () => setPreviewState(chip.dataset.previewState));
    });
}

// ───── CURSOR TRACKING (eyes follow mouse) ─────

function initCursorTracking() {
    document.addEventListener('mousemove', (e) => {
        if (!_avatarRoot) return;
        if (MOODS_WITH_CLOSED_EYES.includes(_currentMood)) return;

        const avatar = _avatarRoot.querySelector('.avatar');
        if (!avatar) return;
        const rect = avatar.getBoundingClientRect();
        const dx = e.clientX - (rect.left + rect.width / 2);
        const dy = e.clientY - (rect.top + rect.height / 2);
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Normalize and clamp movement (max 3px offset)
        const maxOffset = 3;
        const factor = Math.min(distance / 200, 1);
        const moveX = (dx / (distance || 1)) * maxOffset * factor;
        const moveY = (dy / (distance || 1)) * maxOffset * factor;

        _avatarRoot.querySelectorAll('.pupil').forEach(pupil => {
            pupil.style.transform = `translateX(calc(-50% + ${moveX}px)) translateY(${moveY}px)`;
        });
    });
}
