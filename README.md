<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white" />
  <img src="https://img.shields.io/badge/UI-pywebview-00D4FF?logo=googlechrome&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM-OpenAI-412991?logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
</p>

<h1 align="center">✦ Karien ✦</h1>
<p align="center">
  <em>Your tsundere AI desktop companion with an expressive soul.</em>
</p>

<p align="center">
  Karien is a voice-activated, personality-driven AI assistant that lives on your desktop as an animated orb with chibi-style facial expressions. She can open apps, control your system, answer questions, and react with 9 distinct mood expressions — all while maintaining a lovable tsundere anime personality.
</p>

---

## ✨ Features

### 🎭 Expressive Orb Avatar
An animated orb with chibi-style facial features (eyes, eyebrows, mouth, blush) that dynamically change based on the LLM's detected mood.

| Mood | Expression | Orb Color |
|---|---|---|
| `neutral` | Normal round eyes, flat brows | 🔵 Blue |
| `happy` | Squinted curved (＾▽＾) | 🩵 Warm Cyan |
| `sad` | Droopy eyes + teardrop | 🫧 Deep Blue |
| `annoyed` | Half-lidded (−_−), angry brows | 🔴 Red |
| `embarrassed` | Wide eyes + blush marks | 🩷 Pink |
| `proud` | Star symbols (✦) | 🌟 Gold |
| `curious` | Asymmetric big eyes, circle mouth | 💎 Bright Blue |
| `excited` | Star eyes (★), bouncy orb | 💜 Purple-Pink |
| `sleepy` | Barely-open (u_u), slow breathing | 🌙 Muted Purple |

### 🎙️ Voice Interaction
- **Wake Word** detection ("Hey Karien") via Vosk (offline)
- **Speech-to-Text** via Deepgram (live streaming)
- **Text-to-Speech** via ElevenLabs (high quality) or pyttsx3 (offline fallback)
- **Interruption handling** — speak over Karien and she'll stop to listen

### 🧠 LLM Brain
- Powered by **OpenAI GPT-4o** (configurable model)
- Streaming responses with sentence-level TTS pipelining
- Automatic mood detection from `[mood]` tags in LLM output
- Conversation history with smart truncation

### 🔧 Skills & Tool Use
Built-in skills that the LLM can invoke via function calling:

| Skill | Description |
|---|---|
| **Launcher** | Open any application by name |
| **System** | Volume control, brightness, system info |
| **Shortcuts** | Trigger keyboard shortcuts |
| **Vision** | Analyze screen content via screenshots |

### 🔌 MCP Integration
Extensible tool system via the **Model Context Protocol (MCP)**:
- Built-in catalog of MCP servers (filesystem, web fetch, desktop automation, etc.)
- Registry-based enable/disable per server
- Google services integration (Calendar, Gmail, etc.)
- Hot-reload without restarting the app

### 🖥️ Desktop UI
A sleek, dark-themed desktop app built with **pywebview**:
- **Avatar View** — Animated orb with particles and mood expressions
- **Console View** — Real-time log streaming, chat with the LLM, slash commands
- **Settings View** — Configure LLM provider, model, temperature, audio devices, TTS engine, and MCP servers

---

## 🏗️ Architecture

```
karien/
├── desktop_app.py          # pywebview entry point
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
│
├── assistant/              # Core backend
│   ├── main.py             # CLI entry point (voice mode)
│   ├── brain/              # LLM interaction (chat_stream, tool calls)
│   ├── core/               # Config, logging, orchestrator, auth
│   ├── input/              # STT (Deepgram, Vosk), VAD, audio capture
│   ├── output/             # TTS (ElevenLabs, pyttsx3), VTS client
│   ├── skills/             # Built-in tools (launcher, system, vision)
│   ├── mcp/                # MCP server manager, catalog, registry
│   └── ui/                 # API bridge (pywebview ↔ frontend)
│
├── ui/                     # Frontend (HTML/CSS/JS)
│   ├── index.html          # Main layout with sidebar navigation
│   ├── css/
│   │   ├── variables.css   # Design tokens & CSS variables
│   │   ├── layout.css      # Grid layout, sidebar, bottom bar
│   │   ├── avatar.css      # Orb animations & states
│   │   ├── face.css        # Chibi face expressions (9 moods)
│   │   ├── console.css     # Console log area & input
│   │   └── settings.css    # Settings panels & forms
│   └── js/
│       ├── app.js          # Bootstrap, tab switching
│       ├── avatar.js       # Orb state machine, setMood(), particles
│       ├── console.js      # Log rendering, slash commands, send
│       └── settings.js     # Dynamic settings from backend
│
├── config/                 # Runtime configuration
│   ├── moods.json          # Mood-to-VTS mapping (9 moods)
│   └── settings.json       # UI settings (LLM, audio, voice)
│
├── assets/                 # Static assets
│   ├── system_prompt.txt   # Karien's personality definition
│   └── sounds/             # Startup, error, notification sounds
│
└── scripts/                # Utility scripts
    ├── list_audio_devices.py
    ├── manage_mcp.py
    ├── vad_visualizer.py
    └── verify_google.py
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **Windows 10/11** (some features use Windows-specific APIs)
- An **OpenAI API key** (required)
- Optionally: Deepgram API key (STT), ElevenLabs API key (TTS)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Abdullah-Arda-Gundogdu/karien.git
cd karien

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
copy .env.example .env
# Edit .env and add your API keys
```

### Running

```bash
# Desktop UI mode (recommended)
python desktop_app.py

# Voice-only CLI mode
python -m assistant.main
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI API key for the LLM brain |
| `LLM_MODEL` | ❌ | Model to use (default: `gpt-4o-mini`) |
| `DEEPGRAM_API_KEY` | ❌ | Deepgram key for live STT |
| `ELEVENLABS_API_KEY` | ❌ | ElevenLabs key for high-quality TTS |
| `ELEVENLABS_VOICE_ID` | ❌ | ElevenLabs voice ID |
| `MIC_INDEX` | ❌ | Microphone device index (run `scripts/list_audio_devices.py` to find it) |

### Console Slash Commands

Type these in the UI console (they run locally, not sent to the LLM):

| Command | Description |
|---|---|
| `/mood happy` | Set the orb expression to any of the 9 moods |
| `/state thinking` | Set the orb animation state |
| `/help` | List all available commands |

---

## 🎨 Mood System

Karien's LLM responses start with a `[mood]` tag that drives the orb's facial expression:

```
User: Hey, I got an A+ on my exam!
Karien: [excited] Cidden mi?! Hahaha harikasın ya, gurur duydum senden! ★
```

The mood tag is parsed by the backend, stripped from the spoken text, and pushed to the UI to update the orb's face and glow color in real-time.

---

## 🔌 Extending with MCP

Karien uses the [Model Context Protocol](https://modelcontextprotocol.io/) to integrate external tools:

```bash
# List available MCP servers
python scripts/manage_mcp.py list

# Install an MCP server
python scripts/manage_mcp.py install filesystem

# Toggle servers from the UI's Settings tab
```

The MCP catalog includes: **filesystem**, **web fetch**, **desktop automation**, **memory**, **Google Calendar**, **Google Gmail**, and more.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | OpenAI GPT-4o / GPT-4o-mini |
| **STT** | Deepgram (live), Vosk (offline wake word) |
| **TTS** | ElevenLabs, pyttsx3 (fallback) |
| **Desktop UI** | pywebview + HTML/CSS/JS |
| **Tool Protocol** | Model Context Protocol (MCP) |
| **Audio** | PyAudio, pygame, torchaudio |
| **Automation** | pywinauto, pyautogui (Windows) |
| **Auth** | Google OAuth2 (Calendar, Gmail) |

---

## 📁 Utility Scripts

| Script | Description |
|---|---|
| `scripts/list_audio_devices.py` | List available microphones with their indices |
| `scripts/manage_mcp.py` | CLI tool for managing MCP server installations |
| `scripts/vad_visualizer.py` | Visual debugger for Voice Activity Detection |
| `scripts/verify_google.py` | Test Google OAuth authentication |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome-thing`)
3. Commit your changes (`git commit -m 'feat: add awesome thing'`)
4. Push to the branch (`git push origin feature/awesome-thing`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">
  <em>Built with 💙 and a little tsundere energy.</em>
</p>
