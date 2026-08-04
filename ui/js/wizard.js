/**
 * Karien — Setup Wizard
 *
 * 3-step wizard: STT → LLM → TTS
 * Handles provider selection, API key entry, validation, and saving.
 */

// ═══════════════════════════════════════
//  STATE
// ═══════════════════════════════════════

let currentStep = 0;
const totalSteps = 3;

const wizardState = {
    stt: { provider: null, config: {} },
    llm: { provider: null, config: {} },
    tts: { provider: null, config: {} },
};

// ═══════════════════════════════════════
//  PROVIDER DATA
// ═══════════════════════════════════════

// All user-facing text resolves through the i18n table (i18n.js loads first).
// Only providers the engine actually supports are offered (honest cards):
// STT Deepgram/Vosk, LLM OpenAI/Ollama, TTS OpenAI TTS/ElevenLabs.
const PROVIDERS = {
    stt: [
        {
            id: 'deepgram',
            name: 'Deepgram',
            desc: t('wizard.p.deepgram.desc'),
            difficulty: 'easy',
            recommended: true,
            fields: [
                { key: 'DEEPGRAM_API_KEY', label: t('wizard.p.deepgram.key.label'), placeholder: t('wizard.p.deepgram.key.placeholder'), hint: t('wizard.p.deepgram.key.hint') }
            ]
        },
        {
            id: 'vosk',
            name: t('wizard.p.vosk.name'),
            desc: t('wizard.p.vosk.desc'),
            difficulty: 'easy',
            offline: true,
            fields: []
        }
    ],
    llm: [
        {
            id: 'openai',
            name: 'OpenAI',
            desc: t('wizard.p.openai.desc'),
            difficulty: 'easy',
            fields: [
                { key: 'OPENAI_API_KEY', label: t('wizard.p.openai.key.label'), placeholder: 'sk-...', hint: t('wizard.p.openai.key.hint') }
            ]
        },
        {
            id: 'ollama',
            name: t('wizard.p.ollama.name'),
            desc: t('wizard.p.ollama.desc'),
            difficulty: 'medium',
            warning: t('wizard.p.ollama.warning'),
            fields: [
                { key: 'OLLAMA_BASE_URL', label: t('wizard.p.ollama.url.label'), placeholder: 'http://localhost:11434/v1', hint: t('wizard.p.ollama.url.hint'), defaultValue: 'http://localhost:11434/v1' }
            ]
        }
    ],
    tts: [
        {
            id: 'openai_tts',
            name: 'OpenAI TTS',
            desc: t('wizard.p.openaitts.desc'),
            difficulty: 'easy',
            fields: [
                { key: 'OPENAI_API_KEY', label: t('wizard.p.openaitts.key.label'), placeholder: 'sk-...', hint: t('wizard.p.openaitts.key.hint') }
            ]
        },
        {
            id: 'elevenlabs',
            name: 'ElevenLabs',
            desc: t('wizard.p.eleven.desc'),
            difficulty: 'medium',
            warning: t('wizard.p.eleven.warning'),
            fields: [
                { key: 'ELEVENLABS_API_KEY', label: t('wizard.p.eleven.key.label'), placeholder: t('wizard.p.eleven.key.placeholder'), hint: t('wizard.p.eleven.key.hint') },
                { key: 'ELEVENLABS_VOICE_ID', label: t('wizard.p.eleven.voice.label'), placeholder: t('wizard.p.eleven.voice.placeholder'), hint: t('wizard.p.eleven.voice.hint') },
                { key: 'ELEVENLABS_MODEL_ID', label: t('wizard.p.eleven.model.label'), placeholder: 'eleven_flash_v2_5', hint: t('wizard.p.eleven.model.hint'), defaultValue: 'eleven_flash_v2_5' }
            ]
        }
    ]
};

// difficulty → chip color (only easy/medium exist after the card reduction)
const DIFFICULTY_CHIPS = { easy: 'chip--mint', medium: 'chip--peach' };

// ═══════════════════════════════════════
//  RENDERING
// ═══════════════════════════════════════

// Keys pre-loaded from the existing .env (filled in initWizard)
let existingKeys = {};

function renderWizardStep(stepIndex) {
    const types = ['stt', 'llm', 'tts'];
    const type = types[stepIndex];
    const providers = PROVIDERS[type];

    const container = document.getElementById(`step-${stepIndex}-cards`);
    if (!container) return;

    container.innerHTML = '';

    providers.forEach(provider => {
        const card = document.createElement('div');
        card.className = 'card card--select provider-card';
        card.dataset.providerId = provider.id;
        card.dataset.type = type;
        card.onclick = () => selectProvider(type, provider.id);

        // Header row: name + chips (recommended / offline / difficulty)
        let chips = '';
        if (provider.recommended) {
            chips += `<span class="chip chip--sakura">${t('wizard.recommended')}</span>`;
        }
        if (provider.offline) {
            chips += `<span class="chip chip--mint">${t('wizard.offlineBadge')}</span>`;
        } else {
            chips += `<span class="chip ${DIFFICULTY_CHIPS[provider.difficulty] || ''}">${t('wizard.difficulty.' + provider.difficulty)}</span>`;
        }

        let html = `
      <div class="provider-card-header">
        <span class="provider-radio"></span>
        <span class="provider-name">${provider.name}</span>
        ${chips}
      </div>
      <div class="provider-desc">${provider.desc}</div>
    `;

        // Warning callout (peach — only medium-difficulty warnings remain)
        if (provider.warning) {
            html += `<div class="provider-warning">${provider.warning}</div>`;
        }

        // Config fields (API key inputs)
        if (provider.fields.length > 0) {
            html += `<div class="provider-config">`;
            provider.fields.forEach(field => {
                // NOTE: ids are step-scoped — the same key (e.g. OPENAI_API_KEY)
                // can appear in several steps, and duplicate ids made
                // getElementById always hit the hidden step-0 input.
                const defaultVal = field.defaultValue || existingKeys[field.key] || '';
                html += `
          <div class="config-field">
            <label class="config-label">${field.label}</label>
            <input type="${field.key.includes('KEY') || field.key.includes('SECRET') ? 'password' : 'text'}"
                   class="field config-input"
                   id="wizard-${stepIndex}-${field.key}"
                   data-key="${field.key}"
                   placeholder="${field.placeholder}"
                   value="${defaultVal}"
                   autocomplete="off"
                   spellcheck="false" />
            <span class="config-hint">${field.hint}</span>
            <span class="validation-msg" id="wizard-${stepIndex}-${field.key}-error">${t('wizard.required')}</span>
          </div>
        `;
            });
            html += `</div>`;
        }

        card.innerHTML = html;
        container.appendChild(card);
    });

    // Restore selection if user navigated back
    if (wizardState[type].provider) {
        selectProvider(type, wizardState[type].provider, true);
    }
}

// ═══════════════════════════════════════
//  INTERACTION
// ═══════════════════════════════════════

function selectProvider(type, providerId, restoring = false) {
    // Deselect all in this type
    const cards = document.querySelectorAll(`.provider-card[data-type="${type}"]`);
    cards.forEach(c => c.classList.remove('is-selected'));

    // Select this card
    const card = document.querySelector(`.provider-card[data-type="${type}"][data-provider-id="${providerId}"]`);
    if (card) card.classList.add('is-selected');

    // Update state
    wizardState[type].provider = providerId;

    // Restore values if coming back
    if (restoring) {
        const stepIdx = ['stt', 'llm', 'tts'].indexOf(type);
        const config = wizardState[type].config;
        Object.keys(config).forEach(key => {
            const input = document.getElementById(`wizard-${stepIdx}-${key}`);
            if (input && config[key]) input.value = config[key];
        });
    }

    // Update button state
    updateNavButtons();
}

function saveCurrentStepConfig() {
    const types = ['stt', 'llm', 'tts'];
    const type = types[currentStep];

    // Save all input values
    const inputs = document.querySelectorAll(`#step-${currentStep}-cards .config-input`);
    inputs.forEach(input => {
        const key = input.dataset.key;
        if (key && input.value.trim()) {
            wizardState[type].config[key] = input.value.trim();
        }
    });
}

function validateCurrentStep() {
    const types = ['stt', 'llm', 'tts'];
    const type = types[currentStep];

    // Must have a provider selected
    if (!wizardState[type].provider) return false;

    // Get the selected provider config
    const provider = PROVIDERS[type].find(p => p.id === wizardState[type].provider);
    if (!provider) return false;

    // Offline providers don't need validation
    if (provider.offline || provider.fields.length === 0) return true;

    // API key format rules (labels resolve through the i18n table)
    const KEY_RULES = {
        'OPENAI_API_KEY': { minLen: 20, prefix: 'sk-', label: t('wizard.val.OPENAI_API_KEY') },
        'DEEPGRAM_API_KEY': { minLen: 20, label: t('wizard.val.DEEPGRAM_API_KEY') },
        'ELEVENLABS_API_KEY': { minLen: 15, label: t('wizard.val.ELEVENLABS_API_KEY') },
        'ELEVENLABS_VOICE_ID': { minLen: 10, label: t('wizard.val.ELEVENLABS_VOICE_ID') },
    };

    // Validate required fields
    let valid = true;
    provider.fields.forEach(field => {
        if (field.defaultValue) return; // Optional fields with defaults are fine

        const input = document.getElementById(`wizard-${currentStep}-${field.key}`);
        const errorEl = document.getElementById(`wizard-${currentStep}-${field.key}-error`);
        const val = input ? input.value.trim() : '';
        const rule = KEY_RULES[field.key];

        let fieldValid = true;
        let errorMsg = t('wizard.required');

        if (!val) {
            fieldValid = false;
        } else if (rule) {
            if (rule.minLen && val.length < rule.minLen) {
                fieldValid = false;
                errorMsg = rule.label || t('wizard.val.minLen', { n: rule.minLen });
            } else if (rule.prefix && !val.startsWith(rule.prefix)) {
                fieldValid = false;
                errorMsg = rule.label || t('wizard.val.prefix', { prefix: rule.prefix });
            }
        }

        if (!fieldValid) {
            if (input) input.classList.add('error');
            if (errorEl) {
                errorEl.textContent = errorMsg;
                errorEl.classList.add('show');
            }
            valid = false;
        } else {
            if (input) input.classList.remove('error');
            if (errorEl) errorEl.classList.remove('show');
        }
    });

    return valid;
}

// ═══════════════════════════════════════
//  NAVIGATION
// ═══════════════════════════════════════

function nextStep() {
    saveCurrentStepConfig();

    if (!validateCurrentStep()) return;

    if (currentStep < totalSteps - 1) {
        transitionStep(currentStep, currentStep + 1);
        currentStep++;
        updateProgress();
        updateNavButtons();
        renderWizardStep(currentStep);
    }
}

function prevStep() {
    saveCurrentStepConfig();

    if (currentStep > 0) {
        transitionStep(currentStep, currentStep - 1, true);
        currentStep--;
        updateProgress();
        updateNavButtons();
        renderWizardStep(currentStep);
    }
}

function transitionStep(fromIdx, toIdx, backwards = false) {
    const fromStep = document.getElementById(`wizard-step-${fromIdx}`);
    const toStep = document.getElementById(`wizard-step-${toIdx}`);

    // Hide old step
    if (fromStep) {
        fromStep.classList.remove('active');
    }

    // Show new step
    if (toStep) {
        toStep.classList.add('active');
    }
}

function updateProgress() {
    for (let i = 0; i < totalSteps; i++) {
        const dot = document.getElementById(`progress-dot-${i}`);
        const connector = document.getElementById(`progress-conn-${i}`);

        if (dot) {
            dot.classList.remove('active', 'done');
            if (i === currentStep) dot.classList.add('active');
            else if (i < currentStep) dot.classList.add('done');
        }

        if (connector) {
            connector.classList.toggle('done', i < currentStep);
        }
    }

    // Step counter
    const counter = document.getElementById('step-counter');
    if (counter) counter.textContent = t('wizard.stepCounter', { current: currentStep + 1, total: totalSteps });
}

function updateNavButtons() {
    const prevBtn = document.getElementById('wizard-prev');
    const nextBtn = document.getElementById('wizard-next');
    const finishBtn = document.getElementById('wizard-finish');

    if (prevBtn) prevBtn.style.display = currentStep === 0 ? 'none' : 'flex';
    if (nextBtn) nextBtn.style.display = currentStep < totalSteps - 1 ? 'flex' : 'none';
    if (finishBtn) finishBtn.style.display = currentStep === totalSteps - 1 ? 'flex' : 'none';
}

// ═══════════════════════════════════════
//  FINISH WIZARD
// ═══════════════════════════════════════

async function finishWizard() {
    saveCurrentStepConfig();

    if (!validateCurrentStep()) return;

    const finishBtn = document.getElementById('wizard-finish');
    if (finishBtn) {
        finishBtn.disabled = true;
        finishBtn.textContent = t('wizard.saving');
    }

    try {
        if (window.pywebview && window.pywebview.api) {
            await pywebview.api.save_wizard_config(wizardState);
        }

        // Show success animation
        const container = document.querySelector('.wizard-container');
        if (container) {
            container.innerHTML = `
        <div class="wizard-done">
          <div class="wizard-done-emoji">🎉</div>
          <h2 class="wizard-done-title">${t('wizard.done.title')}</h2>
          <p class="wizard-done-subtitle">${t('wizard.done.subtitle')}</p>
        </div>
      `;
        }

        // Navigate to main app after a moment
        setTimeout(() => {
            if (window.pywebview && window.pywebview.api) {
                pywebview.api.launch_main_app();
            }
        }, 2000);

    } catch (e) {
        console.error('Failed to save wizard config:', e);
        if (finishBtn) {
            finishBtn.disabled = false;
            finishBtn.textContent = t('wizard.finish');
        }
    }
}

// ═══════════════════════════════════════
//  INIT
// ═══════════════════════════════════════

function initWizard() {
    // Nav bindings (inline onclick'ler kaldırıldı — plan kuralı)
    const prevBtn = document.getElementById('wizard-prev');
    const nextBtn = document.getElementById('wizard-next');
    const finishBtn = document.getElementById('wizard-finish');
    if (prevBtn) prevBtn.addEventListener('click', prevStep);
    if (nextBtn) nextBtn.addEventListener('click', nextStep);
    if (finishBtn) finishBtn.addEventListener('click', finishWizard);

    renderWizardStep(0);
    updateProgress();
    updateNavButtons();

    // Try to pre-fill from existing .env (waitForApi from util.js)
    if (window.pywebview && window.pywebview.api) {
        waitForApi().then(async () => {
            try {
                const existing = await pywebview.api.get_existing_keys();
                if (existing) {
                    // Stash for ALL steps (they render lazily on navigation),
                    // then re-render the current step so it picks them up.
                    existingKeys = existing;
                    renderWizardStep(currentStep);
                }
            } catch (e) {
                console.warn('Could not load existing keys:', e);
            }
        });
    }
}

// Boot
document.addEventListener('DOMContentLoaded', initWizard);
