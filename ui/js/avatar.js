/**
 * Karien — Avatar Module
 * 
 * Manages the orb state machine and floating particles.
 */

const ORB_LABELS = {
    idle: 'Idle',
    listening: 'Listening...',
    thinking: 'Thinking...',
    speaking: 'Speaking...'
};

/**
 * Initialize avatar: create particles.
 */
function initAvatar() {
    createParticles();
}

/**
 * Switch the orb to a visual state.
 * @param {string} state - 'idle' | 'listening' | 'thinking' | 'speaking'
 * @param {HTMLElement} [btn] - The button that was clicked (for highlighting)
 */
function setOrbState(state, btn) {
    const container = document.getElementById('orbContainer');
    container.className = 'orb-container';
    if (state !== 'idle') container.classList.add(state);

    document.getElementById('statusLabel').textContent = ORB_LABELS[state] || 'Idle';

    if (btn) {
        document.querySelectorAll('.state-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
}

/**
 * Called from Python via evaluate_js to update status text.
 * @param {string} status - e.g. 'listening', 'thinking'
 */
function updateStatus(status) {
    const normalized = status.toLowerCase();
    setOrbState(normalized);
    // Also update state buttons
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
