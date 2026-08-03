/**
 * Karien — Settings Module
 * 
 * Dynamically renders all settings sections from backend data.
 * Each section is populated via pywebview.api calls.
 */

// ═══════════════════════════════════════
//  DYNAMIC INIT (with pywebview backend)
// ═══════════════════════════════════════

async function initSettings() {
    try {
        await Promise.all([
            renderLLMConfig(),
            renderMCPServers(),
            renderAudioConfig(),
            renderVoiceConfig(),
            renderAPIKeys()
        ]);
    } catch (e) {
        console.error('Settings init error:', e);
    }

    // Bind section collapse
    bindSectionCollapse();
}

// ───── LLM CONFIGURATION ─────

async function renderLLMConfig() {
    try {
        const config = await pywebview.api.get_llm_config();

        const providerSelect = document.getElementById('llm-provider');
        const modelSelect = document.getElementById('llm-model');
        const tempSlider = document.getElementById('llm-temperature');
        const tempValue = document.getElementById('llm-temp-value');

        // Populate providers
        if (providerSelect && config.providers) {
            providerSelect.innerHTML = config.providers.map(p =>
                `<option ${p === config.provider ? 'selected' : ''}>${p}</option>`
            ).join('');

            providerSelect.addEventListener('change', () => {
                updateModelsForProvider(providerSelect.value);
                saveLLMConfig();
            });
        }

        // Populate models
        if (modelSelect && config.models) {
            const models = config.models[config.provider] || [];
            modelSelect.innerHTML = models.map(m =>
                `<option ${m === config.model ? 'selected' : ''}>${m}</option>`
            ).join('');

            modelSelect.addEventListener('change', saveLLMConfig);
        }

        // Temperature
        if (tempSlider) {
            tempSlider.value = Math.round((config.temperature || 0.7) * 100);
            tempValue.textContent = (config.temperature || 0.7).toFixed(2);
            tempSlider.addEventListener('input', () => {
                tempValue.textContent = (tempSlider.value / 100).toFixed(2);
            });
            tempSlider.addEventListener('change', saveLLMConfig);
        }
    } catch (e) {
        console.warn('LLM config load failed:', e);
    }
}

async function updateModelsForProvider(provider) {
    try {
        const config = await pywebview.api.get_llm_config();
        const modelSelect = document.getElementById('llm-model');
        const models = config.models[provider] || [];
        modelSelect.innerHTML = models.map(m => `<option>${m}</option>`).join('');
    } catch (e) {
        console.warn('Failed to update models:', e);
    }
}

async function saveLLMConfig() {
    const provider = document.getElementById('llm-provider')?.value;
    const model = document.getElementById('llm-model')?.value;
    const tempSlider = document.getElementById('llm-temperature');
    const temperature = tempSlider ? tempSlider.value / 100 : 0.7;

    try {
        await pywebview.api.set_llm_config({ provider, model, temperature });
    } catch (e) {
        console.warn('Failed to save LLM config:', e);
    }
}

// ───── MCP SERVERS ─────

async function renderMCPServers() {
    try {
        const servers = await pywebview.api.get_mcp_servers();
        const container = document.getElementById('mcp-list');
        if (!container) return;

        container.innerHTML = '';

        if (servers.length === 0) {
            container.innerHTML = '<div style="color: var(--text-dim); padding: 12px;">No MCP servers installed.</div>';
            return;
        }

        servers.forEach(mcp => {
            const item = document.createElement('div');
            item.className = 'mcp-item';
            item.innerHTML = `
        <div class="mcp-toggle ${mcp.enabled ? 'on' : ''}" 
             data-mcp-id="${mcp.id}"
             onclick="handleMCPToggle(this)"></div>
        <span class="mcp-name">${mcp.name}</span>
        <span class="mcp-desc">${mcp.description || ''}</span>
        <span class="mcp-status ${mcp.enabled ? 'connected' : 'disabled'}">
          ${mcp.enabled ? 'Enabled' : 'Disabled'}
        </span>
      `;
            container.appendChild(item);
        });
    } catch (e) {
        console.warn('MCP servers load failed:', e);
    }
}

async function handleMCPToggle(toggleEl) {
    toggleEl.classList.toggle('on');
    const mcpId = toggleEl.dataset.mcpId;
    const enabled = toggleEl.classList.contains('on');

    // Update status badge
    const statusEl = toggleEl.parentElement.querySelector('.mcp-status');
    if (statusEl) {
        statusEl.className = `mcp-status ${enabled ? 'connected' : 'disabled'}`;
        statusEl.textContent = enabled ? 'Enabled' : 'Disabled';
    }

    // Call backend
    if (window.pywebview && window.pywebview.api) {
        try {
            await pywebview.api.toggle_mcp(mcpId, enabled);
        } catch (e) {
            console.warn('MCP toggle failed:', e);
            // Revert
            toggleEl.classList.toggle('on');
        }
    }
}

// ───── AUDIO CONFIG ─────

async function renderAudioConfig() {
    try {
        const config = await pywebview.api.get_audio_config();
        const deviceSelect = document.getElementById('audio-device');
        const wakeWordSelect = document.getElementById('audio-wakeword');

        if (deviceSelect && config.devices) {
            deviceSelect.innerHTML = config.devices.map(d =>
                `<option ${d === config.currentDevice ? 'selected' : ''}>${d}</option>`
            ).join('');
        }

        if (wakeWordSelect && config.wakeWords) {
            wakeWordSelect.innerHTML = config.wakeWords.map(w =>
                `<option ${w === config.currentWakeWord ? 'selected' : ''}>${w}</option>`
            ).join('');
        }
    } catch (e) {
        console.warn('Audio config load failed, using defaults:', e);
    }
}

// ───── VOICE / TTS CONFIG ─────

async function renderVoiceConfig() {
    try {
        const config = await pywebview.api.get_voice_config();
        const engineSelect = document.getElementById('voice-engine');
        const voiceSelect = document.getElementById('voice-voice');
        const speedSlider = document.getElementById('voice-speed');
        const speedValue = document.getElementById('voice-speed-value');

        if (engineSelect && config.engines) {
            engineSelect.innerHTML = config.engines.map(e =>
                `<option ${e === config.currentEngine ? 'selected' : ''}>${e}</option>`
            ).join('');
        }

        if (voiceSelect && config.voices) {
            voiceSelect.innerHTML = config.voices.map(v =>
                `<option ${v === config.currentVoice ? 'selected' : ''}>${v}</option>`
            ).join('');
        }

        if (speedSlider && config.speed) {
            speedSlider.value = Math.round(config.speed * 100);
            speedValue.textContent = config.speed.toFixed(1) + 'x';
        }
    } catch (e) {
        console.warn('Voice config load failed, using defaults:', e);
    }
}

// ═══════════════════════════════════════
//  MOCK INIT (browser preview mode)
// ═══════════════════════════════════════

function initSettingsMock() {
    // Populate with reasonable defaults for browser preview

    // LLM
    const providerSelect = document.getElementById('llm-provider');
    if (providerSelect) {
        providerSelect.innerHTML = ['OpenAI', 'Groq', 'Anthropic', 'Ollama (Local)']
            .map(p => `<option>${p}</option>`).join('');
    }

    const modelSelect = document.getElementById('llm-model');
    if (modelSelect) {
        modelSelect.innerHTML = ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo']
            .map(m => `<option>${m}</option>`).join('');
    }

    // MCP - show some sample items
    const mcpContainer = document.getElementById('mcp-list');
    if (mcpContainer) {
        const mockMCPs = [
            { id: 'filesystem', name: 'Filesystem', desc: 'Read and write files', enabled: true },
            { id: 'fetch', name: 'Web Fetch', desc: 'Fetch web content', enabled: true },
            { id: 'desktop-automation', name: 'Desktop Automation', desc: 'Control mouse & keyboard', enabled: true },
            { id: 'memory', name: 'Memory', desc: 'Persistent knowledge graph', enabled: true }
        ];
        mcpContainer.innerHTML = '';
        mockMCPs.forEach(mcp => {
            const item = document.createElement('div');
            item.className = 'mcp-item';
            item.innerHTML = `
        <div class="mcp-toggle ${mcp.enabled ? 'on' : ''}" 
             data-mcp-id="${mcp.id}"
             onclick="handleMCPToggle(this)"></div>
        <span class="mcp-name">${mcp.name}</span>
        <span class="mcp-desc">${mcp.desc}</span>
        <span class="mcp-status ${mcp.enabled ? 'connected' : 'disabled'}">
          ${mcp.enabled ? 'Enabled' : 'Disabled'}
        </span>
      `;
            mcpContainer.appendChild(item);
        });
    }

    // Audio
    const deviceSelect = document.getElementById('audio-device');
    if (deviceSelect) {
        deviceSelect.innerHTML = ['Default', 'Microphone Array (Realtek)', 'External USB Mic']
            .map(d => `<option>${d}</option>`).join('');
    }

    // Voice
    const engineSelect = document.getElementById('voice-engine');
    if (engineSelect) {
        engineSelect.innerHTML = ['Google Cloud TTS', 'ElevenLabs', 'System TTS']
            .map(e => `<option>${e}</option>`).join('');
    }

    const voiceSelect = document.getElementById('voice-voice');
    if (voiceSelect) {
        voiceSelect.innerHTML = ['tr-TR-Wavenet-A (Female)', 'tr-TR-Wavenet-B (Male)', 'en-US-Neural2-F (Female)']
            .map(v => `<option>${v}</option>`).join('');
    }

    // Bind section collapse
    bindSectionCollapse();
}

// ═══════════════════════════════════════
//  API KEYS
// ═══════════════════════════════════════

const API_KEY_LABELS = {
    'OPENAI_API_KEY': { label: 'OpenAI API Key', icon: '🤖' },
    'DEEPGRAM_API_KEY': { label: 'Deepgram API Key', icon: '🎙️' },
    'ELEVENLABS_API_KEY': { label: 'ElevenLabs API Key', icon: '🗣️' },
    'ELEVENLABS_VOICE_ID': { label: 'ElevenLabs Voice ID', icon: '🎭' },
    'ELEVENLABS_MODEL_ID': { label: 'ElevenLabs Model ID', icon: '🔧' },
    'GROQ_API_KEY': { label: 'Groq API Key', icon: '⚡' },
    'ANTHROPIC_API_KEY': { label: 'Anthropic API Key', icon: '🧠' },
    'GOOGLE_APPLICATION_CREDENTIALS': { label: 'Google Credentials Path', icon: '☁️' },
    'SPOTIFY_CLIENT_ID': { label: 'Spotify Client ID', icon: '🎵' },
    'SPOTIFY_CLIENT_SECRET': { label: 'Spotify Client Secret', icon: '🔐' }
};

async function renderAPIKeys() {
    try {
        const keys = await pywebview.api.get_api_keys();
        const container = document.getElementById('api-keys-list');
        if (!container) return;

        container.innerHTML = '';

        Object.keys(keys).forEach(keyName => {
            const keyData = keys[keyName];
            const meta = API_KEY_LABELS[keyName] || { label: keyName, icon: '🔑' };

            const row = document.createElement('div');
            row.className = 'mcp-item';
            row.style.flexDirection = 'column';
            row.style.alignItems = 'stretch';
            row.style.gap = '8px';

            const headerRow = document.createElement('div');
            headerRow.style.display = 'flex';
            headerRow.style.alignItems = 'center';
            headerRow.style.gap = '10px';

            const statusDot = keyData.has_value
                ? '<span style="color: var(--accent-green); font-size: 8px;">●</span>'
                : '<span style="color: var(--accent-red); font-size: 8px;">●</span>';

            headerRow.innerHTML = `
                <span style="font-size: 16px;">${meta.icon}</span>
                <span class="mcp-name">${meta.label}</span>
                ${statusDot}
                <span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); flex: 2; text-align: right;">${keyData.masked || 'Not set'}</span>
            `;

            const inputRow = document.createElement('div');
            inputRow.style.display = 'flex';
            inputRow.style.gap = '8px';
            inputRow.style.alignItems = 'center';

            const input = document.createElement('input');
            input.type = keyName.includes('KEY') || keyName.includes('SECRET') ? 'password' : 'text';
            input.className = 'form-select';
            input.style.flex = '1';
            input.style.maxWidth = 'none';
            input.style.fontFamily = 'var(--font-mono)';
            input.style.fontSize = '12px';
            input.placeholder = keyData.has_value ? 'Enter new value to update...' : 'Enter value...';

            const saveBtn = document.createElement('button');
            saveBtn.className = 'connect-btn';
            saveBtn.textContent = '💾 Save';
            saveBtn.onclick = async () => {
                const val = input.value.trim();
                if (!val) return;
                saveBtn.textContent = '⏳';
                try {
                    await pywebview.api.set_api_key(keyName, val);
                    saveBtn.textContent = '✅';
                    input.value = '';
                    setTimeout(() => {
                        saveBtn.textContent = '💾 Save';
                        renderAPIKeys(); // Refresh to show updated masked value
                    }, 1500);
                } catch (e) {
                    saveBtn.textContent = '❌ Error';
                    setTimeout(() => saveBtn.textContent = '💾 Save', 2000);
                }
            };

            inputRow.appendChild(input);
            inputRow.appendChild(saveBtn);

            row.appendChild(headerRow);
            row.appendChild(inputRow);
            container.appendChild(row);
        });
    } catch (e) {
        console.warn('Failed to load API keys:', e);
    }
}

// ═══════════════════════════════════════
//  SECTION COLLAPSE
// ═══════════════════════════════════════

function bindSectionCollapse() {
    document.querySelectorAll('.section-header').forEach(header => {
        header.addEventListener('click', () => {
            const body = header.nextElementSibling;
            const chevron = header.querySelector('.section-chevron');
            if (body.style.display === 'none') {
                body.style.display = 'flex';
                chevron.classList.add('open');
            } else {
                body.style.display = 'none';
                chevron.classList.remove('open');
            }
        });
    });
}
