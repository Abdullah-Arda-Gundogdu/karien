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
const PROVIDERS = {
    stt: [
        {
            id: 'deepgram',
            name: 'Deepgram',
            desc: t('wizard.p.deepgram.desc'),
            difficulty: 'easy',
            fields: [
                { key: 'DEEPGRAM_API_KEY', label: t('wizard.p.deepgram.key.label'), placeholder: t('wizard.p.deepgram.key.placeholder'), hint: t('wizard.p.deepgram.key.hint') }
            ]
        },
        {
            id: 'whisper_openai',
            name: 'Whisper (OpenAI)',
            desc: t('wizard.p.whisper.desc'),
            difficulty: 'easy',
            fields: [
                { key: 'OPENAI_API_KEY', label: t('wizard.p.whisper.key.label'), placeholder: 'sk-...', hint: t('wizard.p.whisper.key.hint') }
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
            ],
            models: ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo']
        },
        {
            id: 'groq',
            name: 'Groq',
            desc: t('wizard.p.groq.desc'),
            difficulty: 'easy',
            fields: [
                { key: 'GROQ_API_KEY', label: t('wizard.p.groq.key.label'), placeholder: 'gsk_...', hint: t('wizard.p.groq.key.hint') }
            ],
            models: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768']
        },
        {
            id: 'anthropic',
            name: 'Anthropic',
            desc: t('wizard.p.anthropic.desc'),
            difficulty: 'medium',
            warning: t('wizard.p.anthropic.warning'),
            fields: [
                { key: 'ANTHROPIC_API_KEY', label: t('wizard.p.anthropic.key.label'), placeholder: 'sk-ant-...', hint: t('wizard.p.anthropic.key.hint') }
            ],
            models: ['claude-sonnet-4-20250514', 'claude-3-5-haiku-20241022']
        },
        {
            id: 'ollama',
            name: t('wizard.p.ollama.name'),
            desc: t('wizard.p.ollama.desc'),
            difficulty: 'medium',
            warning: t('wizard.p.ollama.warning'),
            fields: [
                { key: 'OLLAMA_BASE_URL', label: t('wizard.p.ollama.url.label'), placeholder: 'http://localhost:11434/v1', hint: t('wizard.p.ollama.url.hint'), defaultValue: 'http://localhost:11434/v1' }
            ],
            models: ['llama3.2', 'mistral', 'gemma2']
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
        },
        {
            id: 'google_tts',
            name: 'Google Cloud TTS',
            desc: t('wizard.p.googletts.desc'),
            difficulty: 'hard',
            warning: t('wizard.p.googletts.warning'),
            fields: [
                { key: 'GOOGLE_APPLICATION_CREDENTIALS', label: t('wizard.p.googletts.path.label'), placeholder: t('wizard.p.googletts.path.placeholder'), hint: t('wizard.p.googletts.path.hint') }
            ]
        },
        {
            id: 'system_tts',
            name: t('wizard.p.systemtts.name'),
            desc: t('wizard.p.systemtts.desc'),
            difficulty: 'easy',
            offline: true,
            fields: []
        }
    ]
};

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
        card.className = 'provider-card';
        card.dataset.providerId = provider.id;
        card.dataset.type = type;
        card.onclick = () => selectProvider(type, provider.id);

        // Header row
        let html = `
      <div class="provider-card-header">
        <div class="provider-radio"></div>
        <span class="provider-name">${provider.name}</span>
        <span class="difficulty-badge ${provider.difficulty}">${t('wizard.difficulty.' + provider.difficulty)}</span>
      </div>
      <div class="provider-desc">${provider.desc}</div>
    `;

        // Offline badge
        if (provider.offline) {
            html += `<div class="offline-badge">${t('wizard.offlineBadge')}</div>`;
        }

        // Warning callout
        if (provider.warning) {
            const warnClass = provider.difficulty === 'hard' ? 'warn-hard' : 'warn-medium';
            html += `<div class="provider-warning ${warnClass}">${provider.warning}</div>`;
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
                   class="config-input"
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
    cards.forEach(c => c.classList.remove('selected'));

    // Select this card
    const card = document.querySelector(`.provider-card[data-type="${type}"][data-provider-id="${providerId}"]`);
    if (card) card.classList.add('selected');

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
        'GROQ_API_KEY': { minLen: 15, prefix: 'gsk_', label: t('wizard.val.GROQ_API_KEY') },
        'ANTHROPIC_API_KEY': { minLen: 20, prefix: 'sk-ant-', label: t('wizard.val.ANTHROPIC_API_KEY') },
        'ELEVENLABS_API_KEY': { minLen: 15, label: t('wizard.val.ELEVENLABS_API_KEY') },
        'ELEVENLABS_VOICE_ID': { minLen: 10, label: t('wizard.val.ELEVENLABS_VOICE_ID') },
        'GOOGLE_APPLICATION_CREDENTIALS': { minLen: 5, label: t('wizard.val.GOOGLE_APPLICATION_CREDENTIALS') },
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
        <div style="text-align: center; padding: 60px 20px;">
          <div style="font-size: 64px; margin-bottom: 20px; animation: float 2s ease-in-out infinite;">🎉</div>
          <h2 style="font-size: 24px; font-weight: 700; margin-bottom: 8px;">${t('wizard.done.title')}</h2>
          <p style="color: var(--text-secondary); font-size: 14px;">${t('wizard.done.subtitle')}</p>
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
