/**
 * Karien — i18n
 *
 * Single source of truth for every user-facing string in the UI.
 * Loaded FIRST on every page (index, overlay, wizard) so both static
 * markup (via applyI18n) and JS-generated content (via t) can use it.
 *
 * Adding a language later = adding a sibling table (e.g. I18N.en) and a
 * language switch; keys stay identical.
 *
 * API:
 *   t(key, vars)   → translated string; {name} placeholders filled from
 *                    vars; unknown keys fall back to the key itself.
 *   applyI18n(el?) → fills [data-i18n] (textContent),
 *                    [data-i18n-placeholder] and [data-i18n-title]
 *                    attributes under el (default: whole document).
 */

(function () {
    'use strict';

    window.I18N = {
        tr: {
            // ───── Kabuk / kenar çubuğu ─────
            'app.title': 'Karien Paneli',
            'nav.avatar': 'Avatar',
            'nav.console': 'Konsol',
            'nav.settings': 'Ayarlar',
            'sidebar.online': 'Çevrimiçi',

            // ───── Avatar görünümü ─────
            'avatar.statusPrefix': 'Durum:',
            'state.idle': 'Boşta',
            'state.listening': 'Dinliyor...',
            'state.thinking': 'Düşünüyor...',
            'state.speaking': 'Konuşuyor...',
            'stateBtn.idle': 'Boşta',
            'stateBtn.listening': 'Dinle',
            'stateBtn.thinking': 'Düşün',
            'stateBtn.speaking': 'Konuş',

            // ───── Ruh hâlleri ─────
            'mood.neutral': 'Sakin',
            'mood.happy': 'Mutlu',
            'mood.sad': 'Üzgün',
            'mood.annoyed': 'Sinirli',
            'mood.embarrassed': 'Utangaç',
            'mood.proud': 'Gururlu',
            'mood.curious': 'Meraklı',
            'mood.excited': 'Heyecanlı',
            'mood.sleepy': 'Uykulu',

            // ───── Alt bar ─────
            'bar.mute': '🎤 Sustur',
            'bar.unmute': '🔇 Sesi Aç',
            'bar.forceStop': '⏹ Durdur',
            'bar.screenshot': '📸 Ekran Görüntüsü',

            // ───── Konsol ─────
            'console.title': '⌘ Konsol Çıktısı',
            'console.clear': 'Temizle',
            'console.autoScroll': 'Otomatik Kaydırma',
            'console.inputPlaceholder': 'Komutunu buraya yaz...',
            'console.send': 'Gönder',
            'console.init': 'Sistem hazır. Arka uç bekleniyor...',
            'console.moodSet': 'Ruh hâli ayarlandı: {mood}',
            'console.moodList': 'Kullanılabilir ruh hâlleri: neutral, happy, sad, annoyed, embarrassed, proud, curious, excited, sleepy',
            'console.stateSet': 'Durum ayarlandı: {state}',
            'console.stateList': 'Kullanılabilir durumlar: idle, listening, thinking, speaking',
            'console.wakeOk': 'Avatar penceresi: uyandı (içeri kayar + dinler)',
            'console.wakeFail': 'Uyandırma başarısız: {error}',
            'console.sleepOk': 'Avatar penceresi: uykuya daldı (dışarı kayar + gizlenir)',
            'console.sleepFail': 'Uyutma başarısız: {error}',
            'console.noBackend': 'Arka uç yok (tarayıcı önizleme modu).',
            'console.helpCommands': 'Komutlar: /mood [ad] | /state [ad] | /wake | /sleep | /help',
            'console.helpWakeSleep': '/wake ve /sleep, mikrofon gerekmeden avatar penceresini dener.',
            'console.helpChat': 'Bunların dışında yazdığın her şey sohbet mesajı olarak Karien\'e gider.',
            'console.unknownCommand': 'Bilinmeyen komut: {cmd}. Komutları görmek için /help yaz.',
            'console.sendFail': 'Gönderilemedi: {error}',

            // ───── Ayarlar ─────
            'settings.title': '⚙ Ayarlar',
            'settings.subtitle': 'Asistanının beynini, araçlarını ve sesini buradan ayarla.',
            'settings.section.llm': 'LLM Ayarları',
            'settings.section.mcp': 'MCP Sunucuları (Araçlar)',
            'settings.section.audio': 'Ses Ayarları',
            'settings.section.voice': 'Ses / Konuşma (TTS)',
            'settings.section.avatar': 'Avatar',
            'settings.section.apiKeys': 'API Anahtarları',
            'settings.label.provider': 'Sağlayıcı',
            'settings.label.model': 'Model',
            'settings.label.temperature': 'Sıcaklık',
            'settings.label.inputDevice': 'Giriş Cihazı',
            'settings.label.wakeWord': 'Uyandırma Sözcüğü',
            'settings.label.ttsEngine': 'TTS Motoru',
            'settings.label.voice': 'Ses',
            'settings.label.speed': 'Hız',
            'settings.label.skin': 'Görünüm',
            'settings.mcp.none': 'Yüklü MCP sunucusu yok.',
            'settings.mcp.enabled': 'Etkin',
            'settings.mcp.disabled': 'Kapalı',
            'settings.keys.notSet': 'Ayarlı değil',
            'settings.keys.updatePlaceholder': 'Güncellemek için yeni değeri gir...',
            'settings.keys.placeholder': 'Değeri gir...',
            'settings.keys.save': '💾 Kaydet',
            'settings.keys.saving': '⏳',
            'settings.keys.saved': '✅',
            'settings.keys.error': '❌ Hata',

            // ───── API anahtarı etiketleri ─────
            'apikey.OPENAI_API_KEY': 'OpenAI API Anahtarı',
            'apikey.DEEPGRAM_API_KEY': 'Deepgram API Anahtarı',
            'apikey.ELEVENLABS_API_KEY': 'ElevenLabs API Anahtarı',
            'apikey.ELEVENLABS_VOICE_ID': 'ElevenLabs Ses Kimliği',
            'apikey.ELEVENLABS_MODEL_ID': 'ElevenLabs Model Kimliği',
            'apikey.GROQ_API_KEY': 'Groq API Anahtarı',
            'apikey.ANTHROPIC_API_KEY': 'Anthropic API Anahtarı',
            'apikey.GOOGLE_APPLICATION_CREDENTIALS': 'Google Kimlik Dosyası Yolu',
            'apikey.SPOTIFY_CLIENT_ID': 'Spotify İstemci Kimliği',
            'apikey.SPOTIFY_CLIENT_SECRET': 'Spotify İstemci Sırrı',

            // ───── Tarayıcı önizleme (mock) verileri ─────
            'mock.mcp.filesystem.name': 'Dosya Sistemi',
            'mock.mcp.filesystem.desc': 'Dosya okur ve yazar',
            'mock.mcp.fetch.name': 'Web Getirme',
            'mock.mcp.fetch.desc': 'Web içeriği getirir',
            'mock.mcp.desktop.name': 'Masaüstü Otomasyonu',
            'mock.mcp.desktop.desc': 'Fare ve klavyeyi kontrol eder',
            'mock.mcp.memory.name': 'Bellek',
            'mock.mcp.memory.desc': 'Kalıcı bilgi grafiği',
            'mock.audio.default': 'Varsayılan',
            'mock.audio.array': 'Mikrofon Dizisi (Realtek)',
            'mock.audio.usb': 'Harici USB Mikrofon',
            'mock.voice.a': 'tr-TR-Wavenet-A (Kadın)',
            'mock.voice.b': 'tr-TR-Wavenet-B (Erkek)',
            'mock.voice.c': 'en-US-Neural2-F (Kadın)',

            // ───── Yerleşim (overlay) durum etiketi ─────
            'overlay.state.listen': 'dinliyorum~',
            'overlay.state.think': 'düşünüyorum…',
            'overlay.state.speak': '♪',

            // ───── Sihirbaz — kabuk ─────
            'wizard.title': 'Karien — Kurulum',
            'wizard.tagline': 'Hadi seni hazırlayalım ✨',
            'wizard.step0.title': 'Kulaklarını seç',
            'wizard.step0.subtitle': 'Karien seni nasıl dinlesin?',
            'wizard.step1.title': 'Beynini seç',
            'wizard.step1.subtitle': 'Karien\'in düşünme gücünü hangi model versin?',
            'wizard.step2.title': 'Sesini seç',
            'wizard.step2.subtitle': 'Karien sana nasıl seslensin?',
            'wizard.back': '← Geri',
            'wizard.next': 'İleri →',
            'wizard.finish': 'Başlayalım! 🚀',
            'wizard.stepCounter': 'Adım {current} / {total}',
            'wizard.saving': '⏳ Kaydediliyor...',
            'wizard.done.title': 'Her şey hazır!',
            'wizard.done.subtitle': 'Karien kullanıma hazır. Birazdan başlıyoruz...',
            'wizard.difficulty.easy': '🟢 Kolay',
            'wizard.difficulty.medium': '🟡 Orta',
            'wizard.difficulty.hard': '🔴 Zor',
            'wizard.offlineBadge': '✨ Çevrimdışı çalışır — internet gerekmez!',

            // ───── Sihirbaz — doğrulama ─────
            'wizard.required': 'Bu alan zorunlu',
            'wizard.val.minLen': 'En az {n} karakter olmalı',
            'wizard.val.prefix': '{prefix} ile başlamalı',
            'wizard.val.OPENAI_API_KEY': 'OpenAI anahtarı sk- ile başlamalı ve en az 20 karakter olmalı',
            'wizard.val.DEEPGRAM_API_KEY': 'Deepgram anahtarı en az 20 karakter olmalı',
            'wizard.val.GROQ_API_KEY': 'Groq anahtarı gsk_ ile başlamalı ve en az 15 karakter olmalı',
            'wizard.val.ANTHROPIC_API_KEY': 'Anthropic anahtarı sk-ant- ile başlamalı ve en az 20 karakter olmalı',
            'wizard.val.ELEVENLABS_API_KEY': 'ElevenLabs anahtarı en az 15 karakter olmalı',
            'wizard.val.ELEVENLABS_VOICE_ID': 'Ses kimliği en az 10 karakter olmalı',
            'wizard.val.GOOGLE_APPLICATION_CREDENTIALS': 'Geçerli bir dosya yolu gir',

            // ───── Sihirbaz — sağlayıcılar (STT) ─────
            'wizard.p.deepgram.desc': 'Hızlı, isabetli, gerçek zamanlı akış. Türkçe ve çok dilli kullanım için en iyisi.',
            'wizard.p.deepgram.key.label': 'API Anahtarı',
            'wizard.p.deepgram.key.placeholder': 'Deepgram API anahtarını gir',
            'wizard.p.deepgram.key.hint': 'Ücretsiz anahtarını <a href="https://console.deepgram.com" target="_blank">console.deepgram.com</a> adresinden alabilirsin',
            'wizard.p.whisper.desc': 'OpenAI destekli, yüksek isabetli konuşma tanıma.',
            'wizard.p.whisper.key.label': 'OpenAI API Anahtarı',
            'wizard.p.whisper.key.hint': 'OpenAI anahtarını kullanır. <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com</a> üzerinden oluşturabilirsin',
            'wizard.p.vosk.name': 'Vosk (Yerel)',
            'wizard.p.vosk.desc': '%100 çevrimdışı, kendi bilgisayarında çalışır. API anahtarı gerekmez!',

            // ───── Sihirbaz — sağlayıcılar (LLM) ─────
            'wizard.p.openai.desc': 'GPT-4o, GPT-4o-mini — zekâda endüstri standardı.',
            'wizard.p.openai.key.label': 'API Anahtarı',
            'wizard.p.openai.key.hint': 'Anahtarını <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com</a> adresinden alabilirsin',
            'wizard.p.groq.desc': 'Llama ve Mixtral modelleri için ışık hızında yanıtlar. Ücretsiz katmanı var!',
            'wizard.p.groq.key.label': 'API Anahtarı',
            'wizard.p.groq.key.hint': 'Ücretsiz anahtarını <a href="https://console.groq.com" target="_blank">console.groq.com</a> adresinden alabilirsin',
            'wizard.p.anthropic.desc': 'Claude Sonnet ve Haiku — akıl yürütmede ve kod işlerinde harika.',
            'wizard.p.anthropic.warning': '⚠️ Anthropic farklı bir API biçimi kullanır. Tam destek yolda — temel sohbet çalışır ama araç çağırma sınırlı olabilir.',
            'wizard.p.anthropic.key.label': 'API Anahtarı',
            'wizard.p.anthropic.key.hint': 'Anahtarını <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a> adresinden alabilirsin',
            'wizard.p.ollama.name': 'Ollama (Yerel)',
            'wizard.p.ollama.desc': 'Modelleri kendi bilgisayarında çalıştır. Tamamen ücretsiz ve gizliliğe saygılı.',
            'wizard.p.ollama.warning': '⚠️ Önce Ollama\'yı kurup bir model indirmen gerekir (ör. <code>ollama pull llama3.2</code>). Performans donanımına bağlıdır.',
            'wizard.p.ollama.url.label': 'Temel URL',
            'wizard.p.ollama.url.hint': 'Genellikle http://localhost:11434/v1 (varsayılan)',

            // ───── Sihirbaz — sağlayıcılar (TTS) ─────
            'wizard.p.openaitts.desc': 'Doğal tınılı sesler. Hızlı ve güvenilir.',
            'wizard.p.openaitts.key.label': 'OpenAI API Anahtarı',
            'wizard.p.openaitts.key.hint': 'LLM ile aynı anahtar. <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com</a> üzerinden oluşturabilirsin',
            'wizard.p.eleven.desc': 'Üst düzey ses klonlama ve son derece gerçekçi konuşma sentezi.',
            'wizard.p.eleven.warning': '⚠️ Hem API anahtarı hem Ses Kimliği (Voice ID) gerekir. Ücretsiz katmanda aylık karakter sınırı var.',
            'wizard.p.eleven.key.label': 'API Anahtarı',
            'wizard.p.eleven.key.placeholder': 'ElevenLabs API anahtarını gir',
            'wizard.p.eleven.key.hint': 'Anahtarını <a href="https://elevenlabs.io" target="_blank">elevenlabs.io</a> adresinden alabilirsin',
            'wizard.p.eleven.voice.label': 'Ses Kimliği',
            'wizard.p.eleven.voice.placeholder': 'ör. fUjY9K2nAIwlALOwSiwc',
            'wizard.p.eleven.voice.hint': 'Ses kimliklerini ElevenLabs ses kitaplığında bulabilirsin',
            'wizard.p.eleven.model.label': 'Model Kimliği',
            'wizard.p.eleven.model.hint': 'Varsayılan: eleven_flash_v2_5',
            'wizard.p.googletts.desc': 'Bol dil seçenekli, yüksek kaliteli WaveNet sesleri.',
            'wizard.p.googletts.warning': '🔴 Kurulumu en zor olan bu! Google Cloud projesi açman, Text-to-Speech API\'sini etkinleştirmen, bir Servis Hesabı oluşturup JSON kimlik dosyasını indirmen gerekir. Sadece API anahtarı yetmez!',
            'wizard.p.googletts.path.label': 'Servis Hesabı JSON Yolu',
            'wizard.p.googletts.path.placeholder': '/yol/servis-hesabi.json',
            'wizard.p.googletts.path.hint': 'Google Cloud servis hesabı JSON dosyanın tam yolu',
            'wizard.p.systemtts.name': 'Sistem TTS',
            'wizard.p.systemtts.desc': 'İşletim sisteminin yerleşik sesini kullanır. Kurulum gerekmez!'
        }
    };

    /**
     * Translate a key with optional {var} interpolation.
     * Unknown keys fall back to the key itself (visible but harmless).
     * @param {string} key
     * @param {Object=} vars
     * @returns {string}
     */
    window.t = function t(key, vars) {
        let str = window.I18N.tr[key];
        if (str === undefined) return key;
        if (vars) {
            str = str.replace(/\{(\w+)\}/g, (match, name) =>
                Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match
            );
        }
        return str;
    };

    /**
     * Fill translated strings into static markup.
     * @param {Element=} root - defaults to the whole document
     */
    window.applyI18n = function applyI18n(root) {
        const scope = root || document;
        scope.querySelectorAll('[data-i18n]').forEach((el) => {
            el.textContent = window.t(el.getAttribute('data-i18n'));
        });
        scope.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
            el.setAttribute('placeholder', window.t(el.getAttribute('data-i18n-placeholder')));
        });
        scope.querySelectorAll('[data-i18n-title]').forEach((el) => {
            el.setAttribute('title', window.t(el.getAttribute('data-i18n-title')));
        });
    };

    // i18n.js is loaded first, so this listener runs before page modules'.
    document.addEventListener('DOMContentLoaded', () => window.applyI18n());
})();
