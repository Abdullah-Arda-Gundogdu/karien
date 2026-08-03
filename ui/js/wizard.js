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

const PROVIDERS = {
    stt: [
        {
            id: 'deepgram',
            name: 'Deepgram',
            desc: 'Fast, accurate, real-time streaming. Best for Turkish & multilingual.',
            difficulty: 'easy',
            fields: [
                { key: 'DEEPGRAM_API_KEY', label: 'API Key', placeholder: 'Enter your Deepgram API key', hint: 'Get one free at <a href="https://console.deepgram.com" target="_blank">console.deepgram.com</a>' }
            ]
        },
        {
            id: 'whisper_openai',
            name: 'Whisper (OpenAI)',
            desc: 'High accuracy speech recognition powered by OpenAI.',
            difficulty: 'easy',
            fields: [
                { key: 'OPENAI_API_KEY', label: 'OpenAI API Key', placeholder: 'sk-...', hint: 'Uses your OpenAI key. Create one at <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com</a>' }
            ]
        },
        {
            id: 'vosk',
            name: 'Vosk (Local)',
            desc: '100% offline, runs on your machine. No API key needed!',
            difficulty: 'easy',
            offline: true,
            fields: []
        }
    ],
    llm: [
        {
            id: 'openai',
            name: 'OpenAI',
            desc: 'GPT-4o, GPT-4o-mini — the industry standard for intelligence.',
            difficulty: 'easy',
            fields: [
                { key: 'OPENAI_API_KEY', label: 'API Key', placeholder: 'sk-...', hint: 'Get yours at <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com</a>' }
            ],
            models: ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo']
        },
        {
            id: 'groq',
            name: 'Groq',
            desc: 'Ultra-fast inference for Llama & Mixtral models. Free tier available!',
            difficulty: 'easy',
            fields: [
                { key: 'GROQ_API_KEY', label: 'API Key', placeholder: 'gsk_...', hint: 'Get a free key at <a href="https://console.groq.com" target="_blank">console.groq.com</a>' }
            ],
            models: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768']
        },
        {
            id: 'anthropic',
            name: 'Anthropic',
            desc: 'Claude Sonnet & Haiku — great for reasoning and code tasks.',
            difficulty: 'medium',
            warning: '⚠️ Anthropic uses a different API format. Full support is coming soon — basic chat works but tool calling may be limited.',
            fields: [
                { key: 'ANTHROPIC_API_KEY', label: 'API Key', placeholder: 'sk-ant-...', hint: 'Get yours at <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a>' }
            ],
            models: ['claude-sonnet-4-20250514', 'claude-3-5-haiku-20241022']
        },
        {
            id: 'ollama',
            name: 'Ollama (Local)',
            desc: 'Run LLMs locally on your machine. Completely free & private.',
            difficulty: 'medium',
            warning: '⚠️ You need to install Ollama first and pull a model (e.g. <code>ollama pull llama3.2</code>). Performance depends on your hardware.',
            fields: [
                { key: 'OLLAMA_BASE_URL', label: 'Base URL', placeholder: 'http://localhost:11434/v1', hint: 'Usually http://localhost:11434/v1 (default)', defaultValue: 'http://localhost:11434/v1' }
            ],
            models: ['llama3.2', 'mistral', 'gemma2']
        }
    ],
    tts: [
        {
            id: 'openai_tts',
            name: 'OpenAI TTS',
            desc: 'Natural-sounding voices. Fast and reliable.',
            difficulty: 'easy',
            fields: [
                { key: 'OPENAI_API_KEY', label: 'OpenAI API Key', placeholder: 'sk-...', hint: 'Same key as LLM. Create at <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com</a>' }
            ]
        },
        {
            id: 'elevenlabs',
            name: 'ElevenLabs',
            desc: 'Premium voice cloning & ultra-realistic speech synthesis.',
            difficulty: 'medium',
            warning: '⚠️ You need both an API key and a Voice ID. Free tier has limited characters per month.',
            fields: [
                { key: 'ELEVENLABS_API_KEY', label: 'API Key', placeholder: 'Enter your ElevenLabs API key', hint: 'Get at <a href="https://elevenlabs.io" target="_blank">elevenlabs.io</a>' },
                { key: 'ELEVENLABS_VOICE_ID', label: 'Voice ID', placeholder: 'e.g. fUjY9K2nAIwlALOwSiwc', hint: 'Find voice IDs in your ElevenLabs voice library' },
                { key: 'ELEVENLABS_MODEL_ID', label: 'Model ID', placeholder: 'eleven_flash_v2_5', hint: 'Default: eleven_flash_v2_5', defaultValue: 'eleven_flash_v2_5' }
            ]
        },
        {
            id: 'google_tts',
            name: 'Google Cloud TTS',
            desc: 'High quality WaveNet voices with many language options.',
            difficulty: 'hard',
            warning: '🔴 This is the hardest to set up! You need a Google Cloud project, enable the Text-to-Speech API, create a Service Account, and download the JSON credentials file. Not just an API key!',
            fields: [
                { key: 'GOOGLE_APPLICATION_CREDENTIALS', label: 'Service Account JSON Path', placeholder: '/path/to/service-account.json', hint: 'Full path to your Google Cloud service account JSON file' }
            ]
        },
        {
            id: 'system_tts',
            name: 'System TTS',
            desc: 'Uses your OS built-in text-to-speech. Zero setup needed!',
            difficulty: 'easy',
            offline: true,
            fields: []
        }
    ]
};

// ═══════════════════════════════════════
//  RENDERING
// ═══════════════════════════════════════

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
        <span class="difficulty-badge ${provider.difficulty}">${provider.difficulty === 'easy' ? '🟢 Easy' : provider.difficulty === 'medium' ? '🟡 Medium' : '🔴 Hard'}</span>
      </div>
      <div class="provider-desc">${provider.desc}</div>
    `;

        // Offline badge
        if (provider.offline) {
            html += `<div class="offline-badge">✨ Works offline — no internet needed!</div>`;
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
                const defaultVal = field.defaultValue || '';
                html += `
          <div class="config-field">
            <label class="config-label">${field.label}</label>
            <input type="${field.key.includes('KEY') || field.key.includes('SECRET') ? 'password' : 'text'}" 
                   class="config-input" 
                   id="wizard-${field.key}"
                   data-key="${field.key}"
                   placeholder="${field.placeholder}"
                   value="${defaultVal}"
                   autocomplete="off"
                   spellcheck="false" />
            <span class="config-hint">${field.hint}</span>
            <span class="validation-msg" id="wizard-${field.key}-error">This field is required</span>
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
        const config = wizardState[type].config;
        Object.keys(config).forEach(key => {
            const input = document.getElementById(`wizard-${key}`);
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

    // API key format rules
    const KEY_RULES = {
        'OPENAI_API_KEY': { minLen: 20, prefix: 'sk-', label: 'OpenAI key should start with sk- and be 20+ characters' },
        'DEEPGRAM_API_KEY': { minLen: 20, label: 'Deepgram key should be at least 20 characters' },
        'GROQ_API_KEY': { minLen: 15, prefix: 'gsk_', label: 'Groq key should start with gsk_ and be 15+ characters' },
        'ANTHROPIC_API_KEY': { minLen: 20, prefix: 'sk-ant-', label: 'Anthropic key should start with sk-ant- and be 20+ characters' },
        'ELEVENLABS_API_KEY': { minLen: 15, label: 'ElevenLabs key should be at least 15 characters' },
        'ELEVENLABS_VOICE_ID': { minLen: 10, label: 'Voice ID should be at least 10 characters' },
        'GOOGLE_APPLICATION_CREDENTIALS': { minLen: 5, label: 'Please enter a valid file path' },
    };

    // Validate required fields
    let valid = true;
    provider.fields.forEach(field => {
        if (field.defaultValue) return; // Optional fields with defaults are fine

        const input = document.getElementById(`wizard-${field.key}`);
        const errorEl = document.getElementById(`wizard-${field.key}-error`);
        const val = input ? input.value.trim() : '';
        const rule = KEY_RULES[field.key];

        let fieldValid = true;
        let errorMsg = 'This field is required';

        if (!val) {
            fieldValid = false;
        } else if (rule) {
            if (rule.minLen && val.length < rule.minLen) {
                fieldValid = false;
                errorMsg = rule.label || `Must be at least ${rule.minLen} characters`;
            } else if (rule.prefix && !val.startsWith(rule.prefix)) {
                fieldValid = false;
                errorMsg = rule.label || `Must start with ${rule.prefix}`;
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
    if (counter) counter.textContent = `Step ${currentStep + 1} of ${totalSteps}`;
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
        finishBtn.textContent = '⏳ Saving...';
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
          <h2 style="font-size: 24px; font-weight: 700; margin-bottom: 8px;">All set!</h2>
          <p style="color: var(--text-secondary); font-size: 14px;">Karien is ready to go. Launching in a moment...</p>
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
            finishBtn.textContent = "Let's Go! 🚀";
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

    // Try to pre-fill from existing .env
    if (window.pywebview && window.pywebview.api) {
        waitForWizardApi().then(async () => {
            try {
                const existing = await pywebview.api.get_existing_keys();
                if (existing) {
                    Object.keys(existing).forEach(key => {
                        const input = document.getElementById(`wizard-${key}`);
                        if (input && existing[key]) input.value = existing[key];
                    });
                }
            } catch (e) {
                console.warn('Could not load existing keys:', e);
            }
        });
    }
}

function waitForWizardApi() {
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

// Boot
document.addEventListener('DOMContentLoaded', initWizard);
