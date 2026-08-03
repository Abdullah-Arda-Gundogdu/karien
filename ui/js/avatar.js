/**
 * Karien — Avatar Module
 * 
 * Manages the orb state machine, floating particles, and mood expressions.
 * 
 * MOODS:  neutral, happy, sad, annoyed, embarrassed, proud, curious, excited, sleepy
 * STATES: idle, listening, thinking, speaking (orb animation states)
 */

const ORB_LABELS = {
    idle: 'Idle',
    listening: 'Listening...',
    thinking: 'Thinking...',
    speaking: 'Speaking...'
};

const VALID_MOODS = [
    'neutral', 'happy', 'sad', 'annoyed', 'embarrassed',
    'proud', 'curious', 'excited', 'sleepy'
];

let _currentMood = 'neutral';
let _currentState = 'idle';

/**
 * Initialize avatar: create particles.
 */
function initAvatar() {
    createParticles();
    initCursorTracking();
}

/**
 * Switch the orb to a visual state (idle/listening/thinking/speaking).
 * Preserves the current mood expression.
 */
function setOrbState(state, btn) {
    _currentState = state;
    const container = document.getElementById('orbContainer');

    // Remove old state classes but keep mood classes
    container.classList.remove('idle', 'listening', 'thinking', 'speaking');
    if (state !== 'idle') container.classList.add(state);

    document.getElementById('statusLabel').textContent = ORB_LABELS[state] || 'Idle';

    if (btn) {
        document.querySelectorAll('.state-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
}

/**
 * Set the mood expression on the orb face.
 * Called from Python via evaluate_js when LLM outputs a [mood] tag,
 * or from console via /mood command.
 * @param {string} mood - One of the 9 valid moods
 */
function setMood(mood) {
    const normalized = mood.toLowerCase().trim();
    if (!VALID_MOODS.includes(normalized)) {
        console.warn('Unknown mood:', mood);
        return;
    }

    _currentMood = normalized;
    const container = document.getElementById('orbContainer');

    // Remove all mood classes
    VALID_MOODS.forEach(m => container.classList.remove('mood-' + m));

    // Apply new mood (neutral = no extra class)
    if (normalized !== 'neutral') {
        container.classList.add('mood-' + normalized);
    }

    // Update status text with mood
    const label = document.getElementById('statusLabel');
    if (label && _currentState === 'idle') {
        const moodEmoji = {
            neutral: '', happy: '😊', sad: '😢', annoyed: '😤',
            embarrassed: '😳', proud: '✨', curious: '🤔', excited: '⭐', sleepy: '😴'
        };
        label.textContent = (normalized.charAt(0).toUpperCase() + normalized.slice(1) + ' ' + (moodEmoji[normalized] || '')).trim();
    }
}

/**
 * Called from Python via evaluate_js to update orb status.
 * @param {string} status - e.g. 'listening', 'thinking'
 */
function updateStatus(status) {
    const normalized = status.toLowerCase();
    setOrbState(normalized);
    document.querySelectorAll('.state-btn').forEach(b => {
        b.classList.toggle('active', b.textContent.toLowerCase().includes(normalized));
    });
}

/**
 * Create floating particle elements.
 */
function createParticles() {
    const particlesEl = document.getElementById('particles');
    if (!particlesEl) return;
    for (let i = 0; i < 30; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.left = Math.random() * 100 + '%';
        p.style.animationDuration = (6 + Math.random() * 8) + 's';
        p.style.animationDelay = Math.random() * 10 + 's';
        p.style.width = p.style.height = (1 + Math.random() * 2) + 'px';
        particlesEl.appendChild(p);
    }
}

/**
 * Toggle mute button label.
 */
function toggleMute(btn) {
    const muted = btn.textContent.includes('Unmute');
    btn.innerHTML = muted ? '🎤 Mute' : '🔇 Unmute';
}

// ═══════════════════════════════════════
//  CURSOR TRACKING (Eyes follow mouse)
// ═══════════════════════════════════════

const MOODS_WITH_CLOSED_EYES = ['happy', 'annoyed', 'sleepy', 'excited', 'proud'];

function initCursorTracking() {
    const orb = document.querySelector('.orb');
    if (!orb) return;

    document.addEventListener('mousemove', (e) => {
        // Skip if eyes are closed/hidden
        if (MOODS_WITH_CLOSED_EYES.includes(_currentMood)) return;

        const rect = orb.getBoundingClientRect();
        const orbCenterX = rect.left + rect.width / 2;
        const orbCenterY = rect.top + rect.height / 2;

        // Direction from orb center to cursor
        const dx = e.clientX - orbCenterX;
        const dy = e.clientY - orbCenterY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Normalize and clamp movement (max 3px offset)
        const maxOffset = 3;
        const factor = Math.min(distance / 200, 1);
        const moveX = (dx / (distance || 1)) * maxOffset * factor;
        const moveY = (dy / (distance || 1)) * maxOffset * factor;

        // Apply to all pupils
        document.querySelectorAll('.pupil').forEach(pupil => {
            pupil.style.transform = `translateX(calc(-50% + ${moveX}px)) translateY(${moveY}px)`;
        });
    });
}
