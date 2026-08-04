/**
 * Karien — Settings Module
 *
 * Renders the settings sections from live backend data:
 *   Yapay Zeka      → get_llm_config / set_llm_config  (.env, restart chip)
 *   Araçlar (MCP)   → get_mcp_servers / toggle_mcp     (live)
 *   Ses Girişi      → get_audio_devices / set_audio_device (.env, restart chip)
 *   Ses Çıkışı      → get_tts_status                   (read-only chip)
 *   Avatar          → get_avatar + applySkin           (live, js/avatar.js)
 *   API Anahtarları → get_api_keys / set_api_key       (.env)
 *
 * In browser preview (no pywebview) initSettingsPreview shows honest
 * empty-states — no fake data.
 */

// ═══════════════════════════════════════
//  DYNAMIC INIT (with pywebview backend)
// ═══════════════════════════════════════

async function initSettings() {
    try {
        await Promise.all([
            renderAIConfig(),
            renderMCPServers(),
            renderAudioInput(),
            renderAudioOutput(),
            renderAvatarConfig(),
            renderAPIKeys()
        ]);
    } catch (e) {
        console.error('Settings init error:', e);
    }

    bindSectionCollapse();
}

// ───── YAPAY ZEKA (LLM → .env, restart gerekir) ─────

async function renderAIConfig() {
    try {
        const config = await pywebview.api.get_llm_config();

        const providerSelect = document.getElementById('llm-provider');
        const modelInput = document.getElementById('llm-model');
        const tempSlider = document.getElementById('llm-temperature');
        const tempValue = document.getElementById('llm-temp-value');

        if (providerSelect && config.providers) {
            providerSelect.innerHTML = '';
            config.providers.forEach((p) => {
                const opt = document.createElement('option');
                opt.value = p;
                opt.textContent = t('settings.provider.' + p);
                opt.selected = (p === config.provider);
                providerSelect.appendChild(opt);
            });
            providerSelect.addEventListener('change', saveAIConfig);
        }

        if (modelInput) {
            modelInput.value = config.model || '';
            modelInput.addEventListener('change', saveAIConfig);
        }

        // Temperature (display sync is bound once in bindSettingsStatic)
        if (tempSlider && tempValue) {
            const temp = typeof config.temperature === 'number' ? config.temperature : 0.7;
            tempSlider.value = Math.round(temp * 100);
            tempValue.textContent = temp.toFixed(2);
            tempSlider.addEventListener('change', saveAIConfig);
        }
    } catch (e) {
        console.warn('LLM config load failed:', e);
    }
}

async function saveAIConfig() {
    const provider = document.getElementById('llm-provider')?.value;
    const model = document.getElementById('llm-model')?.value.trim();
    const tempSlider = document.getElementById('llm-temperature');
    const temperature = tempSlider ? tempSlider.value / 100 : 0.7;

    try {
        const res = await pywebview.api.set_llm_config({ provider, model, temperature });
        if (res && res.success) {
            showToast(t('settings.savedRestart'), 'success');
        } else {
            showToast(t('settings.saveFail', { error: (res && res.error) || '?' }), 'error');
        }
    } catch (e) {
        showToast(t('settings.saveFail', { error: e }), 'error');
    }
}

// ───── ARAÇLAR (MCP) ─────

async function renderMCPServers() {
    try {
        const servers = await pywebview.api.get_mcp_servers();
        const container = document.getElementById('mcp-list');
        if (!container) return;

        container.innerHTML = '';

        if (!servers || servers.length === 0) {
            appendEmptyNote(container, t('settings.mcp.none'));
            return;
        }

        servers.forEach((mcp) => container.appendChild(buildMCPRow(mcp)));
    } catch (e) {
        console.warn('MCP servers load failed:', e);
    }
}

function buildMCPRow(mcp) {
    const item = document.createElement('div');
    item.className = 'mcp-item';

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'toggle' + (mcp.enabled ? ' is-on' : '');
    toggle.setAttribute('role', 'switch');
    toggle.setAttribute('aria-checked', String(!!mcp.enabled));
    toggle.dataset.mcpId = mcp.id;

    const name = document.createElement('span');
    name.className = 'mcp-name';
    name.textContent = mcp.name;

    const desc = document.createElement('span');
    desc.className = 'mcp-desc';
    desc.textContent = mcp.description || '';

    const status = document.createElement('span');
    status.className = 'chip ' + (mcp.enabled ? 'chip--mint' : '');
    status.textContent = mcp.enabled ? t('settings.mcp.enabled') : t('settings.mcp.disabled');

    toggle.addEventListener('click', () => handleMCPToggle(toggle, status));

    item.appendChild(toggle);
    item.appendChild(name);
    item.appendChild(desc);
    item.appendChild(status);
    return item;
}

async function handleMCPToggle(toggleEl, statusEl) {
    const enabled = toggleEl.classList.toggle('is-on');
    toggleEl.setAttribute('aria-checked', String(enabled));
    reflectMCPStatus(statusEl, enabled);

    if (window.pywebview && window.pywebview.api) {
        try {
            await pywebview.api.toggle_mcp(toggleEl.dataset.mcpId, enabled);
        } catch (e) {
            console.warn('MCP toggle failed:', e);
            // Revert
            const reverted = toggleEl.classList.toggle('is-on');
            toggleEl.setAttribute('aria-checked', String(reverted));
            reflectMCPStatus(statusEl, reverted);
        }
    }
}

function reflectMCPStatus(statusEl, enabled) {
    if (!statusEl) return;
    statusEl.className = 'chip ' + (enabled ? 'chip--mint' : '');
    statusEl.textContent = enabled ? t('settings.mcp.enabled') : t('settings.mcp.disabled');
}

// ───── SES GİRİŞİ (mikrofon → .env MIC_INDEX, restart gerekir) ─────

async function renderAudioInput() {
    try {
        const res = await pywebview.api.get_audio_devices();
        const deviceSelect = document.getElementById('audio-device');
        if (!deviceSelect) return;

        deviceSelect.innerHTML = '';
        const devices = (res && res.devices) || [];

        if (devices.length === 0) {
            const opt = document.createElement('option');
            opt.textContent = t('settings.audio.none');
            opt.disabled = true;
            opt.selected = true;
            deviceSelect.appendChild(opt);
            deviceSelect.disabled = true;
            return;
        }

        // Sistem varsayılanı (MIC_INDEX yazılmamış = null)
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = t('settings.audio.systemDefault');
        defaultOpt.selected = (res.current === null || res.current === undefined);
        deviceSelect.appendChild(defaultOpt);

        devices.forEach((d) => {
            const opt = document.createElement('option');
            opt.value = String(d.index);
            opt.textContent = d.name;
            opt.selected = (d.index === res.current);
            deviceSelect.appendChild(opt);
        });

        deviceSelect.addEventListener('change', async () => {
            if (deviceSelect.value === '') return; // varsayılan seçildi — .env'e dokunma
            try {
                const r = await pywebview.api.set_audio_device(parseInt(deviceSelect.value, 10));
                if (r && r.success) {
                    showToast(t('settings.savedRestart'), 'success');
                } else {
                    showToast(t('settings.saveFail', { error: (r && r.error) || '?' }), 'error');
                }
            } catch (e) {
                showToast(t('settings.saveFail', { error: e }), 'error');
            }
        });
    } catch (e) {
        console.warn('Audio devices load failed:', e);
    }
}

// ───── SES ÇIKIŞI (salt-okunur motor çipi) ─────

const TTS_PROVIDER_NAMES = { elevenlabs: 'ElevenLabs', openai: 'OpenAI' };

async function renderAudioOutput() {
    const chip = document.getElementById('tts-engine-chip');
    if (!chip) return;
    try {
        const res = await pywebview.api.get_tts_status();
        if (res && res.available && res.provider) {
            const name = TTS_PROVIDER_NAMES[res.provider] || res.provider;
            chip.className = 'chip chip--mint';
            chip.textContent = t('settings.tts.auto', { provider: name });
        } else {
            chip.className = 'chip chip--coral';
            chip.textContent = t('settings.tts.unavailable');
        }
    } catch (e) {
        console.warn('TTS status load failed:', e);
        chip.className = 'chip';
        chip.textContent = t('settings.tts.unavailable');
    }
}

// ───── AVATAR SKIN ─────

async function renderAvatarConfig() {
    try {
        const config = await pywebview.api.get_avatar();
        const skinSelect = document.getElementById('avatar-skin');
        if (!skinSelect || !config.skins) return;

        skinSelect.innerHTML = '';
        config.skins.forEach((s) => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = s.name;
            opt.selected = (s.id === config.avatar);
            skinSelect.appendChild(opt);
        });

        // Bind here — in the REAL app path. applySkin (js/avatar.js)
        // persists via set_avatar AND keeps the preview stage + skin
        // chips in sync with this dropdown.
        skinSelect.onchange = () => applySkin(skinSelect.value);
    } catch (e) {
        console.warn('Avatar config load failed:', e);
    }
}

// ═══════════════════════════════════════
//  API KEYS
// ═══════════════════════════════════════

// Labels resolve through the i18n table (i18n.js loads before this file);
// unknown env keys fall back to the raw key name in renderAPIKeys.
// Only keys the engine actually reads are listed (see api.get_api_keys).
const API_KEY_LABELS = {
    'OPENAI_API_KEY': t('apikey.OPENAI_API_KEY'),
    'DEEPGRAM_API_KEY': t('apikey.DEEPGRAM_API_KEY'),
    'ELEVENLABS_API_KEY': t('apikey.ELEVENLABS_API_KEY'),
    'ELEVENLABS_VOICE_ID': t('apikey.ELEVENLABS_VOICE_ID'),
    'ELEVENLABS_MODEL_ID': t('apikey.ELEVENLABS_MODEL_ID'),
    'SPOTIFY_CLIENT_ID': t('apikey.SPOTIFY_CLIENT_ID'),
    'SPOTIFY_CLIENT_SECRET': t('apikey.SPOTIFY_CLIENT_SECRET')
};

async function renderAPIKeys() {
    try {
        const keys = await pywebview.api.get_api_keys();
        const container = document.getElementById('api-keys-list');
        if (!container) return;

        container.innerHTML = '';
        Object.keys(keys).forEach((keyName) => {
            container.appendChild(buildAPIKeyRow(keyName, keys[keyName]));
        });
    } catch (e) {
        console.warn('Failed to load API keys:', e);
    }
}

function buildAPIKeyRow(keyName, keyData) {
    const row = document.createElement('div');
    row.className = 'key-item';

    // Üst satır: ad + durum noktası + maskeli değer
    const headerRow = document.createElement('div');
    headerRow.className = 'key-item-header';

    const name = document.createElement('span');
    name.className = 'key-name';
    name.textContent = API_KEY_LABELS[keyName] || keyName;

    const dot = document.createElement('span');
    dot.className = 'key-dot ' + (keyData.has_value ? 'is-set' : '');

    const masked = document.createElement('span');
    masked.className = 'key-masked';
    masked.textContent = keyData.masked || t('settings.keys.notSet');

    headerRow.appendChild(name);
    headerRow.appendChild(dot);
    headerRow.appendChild(masked);

    // Alt satır: input + kaydet
    const inputRow = document.createElement('div');
    inputRow.className = 'key-item-input';

    const input = document.createElement('input');
    input.type = (keyName.includes('KEY') || keyName.includes('SECRET')) ? 'password' : 'text';
    input.className = 'field key-field';
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.placeholder = keyData.has_value
        ? t('settings.keys.updatePlaceholder')
        : t('settings.keys.placeholder');

    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn btn--primary btn--sm';
    saveBtn.textContent = t('settings.keys.save');
    saveBtn.addEventListener('click', async () => {
        const val = input.value.trim();
        if (!val) return;
        saveBtn.disabled = true;
        saveBtn.textContent = t('settings.keys.saving');
        try {
            await pywebview.api.set_api_key(keyName, val);
            saveBtn.textContent = t('settings.keys.saved');
            input.value = '';
            setTimeout(() => {
                saveBtn.disabled = false;
                saveBtn.textContent = t('settings.keys.save');
                renderAPIKeys(); // Refresh to show updated masked value
            }, 1200);
        } catch (e) {
            saveBtn.textContent = t('settings.keys.error');
            setTimeout(() => {
                saveBtn.disabled = false;
                saveBtn.textContent = t('settings.keys.save');
            }, 2000);
        }
    });

    inputRow.appendChild(input);
    inputRow.appendChild(saveBtn);

    row.appendChild(headerRow);
    row.appendChild(inputRow);
    return row;
}

// ═══════════════════════════════════════
//  BROWSER PREVIEW (no backend — honest empty states, no fake data)
// ═══════════════════════════════════════

function initSettingsPreview() {
    const noBackend = t('settings.preview.noBackend');

    const mcpContainer = document.getElementById('mcp-list');
    if (mcpContainer) appendEmptyNote(mcpContainer, noBackend);

    const keysContainer = document.getElementById('api-keys-list');
    if (keysContainer) appendEmptyNote(keysContainer, noBackend);

    const deviceSelect = document.getElementById('audio-device');
    if (deviceSelect) {
        const opt = document.createElement('option');
        opt.textContent = noBackend;
        opt.disabled = true;
        opt.selected = true;
        deviceSelect.appendChild(opt);
        deviceSelect.disabled = true;
    }

    const ttsChip = document.getElementById('tts-engine-chip');
    if (ttsChip) ttsChip.textContent = t('settings.tts.unavailable');

    bindSectionCollapse();
}

function appendEmptyNote(container, text) {
    const note = document.createElement('div');
    note.className = 'empty-note';
    note.textContent = text;
    container.appendChild(note);
}

// ═══════════════════════════════════════
//  STATIC BINDINGS (both real + preview paths)
// ═══════════════════════════════════════

/**
 * Bind the temperature slider's value display once, independent of
 * backend availability.
 */
function bindSettingsStatic() {
    const tempSlider = document.getElementById('llm-temperature');
    const tempValue = document.getElementById('llm-temp-value');
    if (tempSlider && tempValue) {
        tempSlider.addEventListener('input', () => {
            tempValue.textContent = (tempSlider.value / 100).toFixed(2);
        });
    }
}

// ═══════════════════════════════════════
//  SECTION COLLAPSE (components.css .section/.is-closed)
// ═══════════════════════════════════════

function bindSectionCollapse() {
    document.querySelectorAll('.settings-body .section-header').forEach((header) => {
        if (header.dataset.collapseBound) return; // idempotent
        header.dataset.collapseBound = '1';
        header.addEventListener('click', () => {
            header.closest('.section')?.classList.toggle('is-closed');
        });
    });
}
