<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white" />
  <img src="https://img.shields.io/badge/UI-pywebview-00D4FF?logo=googlechrome&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM-OpenAI%20%2B%20Ollama-412991?logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/architecture-Three--Tier-ff6b35" />
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

### 🧠 Three-Tier Cognitive Architecture
Karien uses a **modular three-tier architecture** inspired by the [Harmony framework](https://arxiv.org/abs/2501.13444), distributing cognitive load across specialized models to reduce hallucinations and stabilize tool-calling:

```
User Message
      │
      ▼
┌─────────────┐   Tier 1: Intent Router
│   Router    │   Fast, small model (local or cloud)
│             │   Classifies: TOOL_CALL | CONVERSATION | VISION | SYSTEM
└──────┬──────┘
       │
       ▼
┌─────────────┐   Tier 2: Task Worker
│   Worker    │   Most capable model available
│             │   Executes the narrowly-scoped task
└──────┬──────┘
       │
       ▼
┌─────────────┐   Tier 3: Response Synthesizer
│ Synthesizer │   Lightweight model
│             │   Adds Karien's personality + mood tags
└─────────────┘
```

Each tier can use a **different provider and model** — for example, a local Llama 3 for routing and synthesis, with GPT-4o for complex task execution. This hybrid local+cloud approach optimizes both latency and capability.

### 🏠 Local LLM Support
Run Karien entirely on your own hardware with no cloud dependency:
- **Ollama** — Supports Llama 3, Mistral, Qwen 2.5, Phi-3, and more
- **LM Studio** — OpenAI-compatible local inference
- **Hybrid mode** — Mix local models (Router, Synthesizer) with cloud APIs (Worker)

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
│   ├── brain/              # Three-Tier Cognitive Architecture
│   │   ├── llm.py          # Brain coordinator (Router → Worker → Synthesizer)
│   │   ├── router.py       # Tier 1: Intent classification
│   │   ├── worker.py       # Tier 2: Task execution
│   │   ├── synthesizer.py  # Tier 3: Personality formatting
│   │   └── providers/      # Multi-provider LLM abstraction
│   │       ├── base.py     # Abstract LLMProvider interface
│   │       ├── openai_provider.py   # OpenAI cloud wrapper
│   │       ├── ollama_provider.py   # Ollama local wrapper
│   │       └── factory.py  # Provider factory
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
- **One of the following LLM backends:**
  - OpenAI API key (cloud)
  - [Ollama](https://ollama.com/) installed locally (free, local)
  - [LM Studio](https://lmstudio.ai/) (free, local, GUI)
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
# Edit .env and configure your LLM provider (see Configuration below)
```

### Setting Up Local LLM (Optional)

```bash
# Install Ollama (https://ollama.com/download)
# Then pull a model:
ollama pull llama3          # For Router & Synthesizer tiers
ollama pull llama3:70b      # For Worker tier (if you have enough VRAM)

# Ollama will automatically serve on http://localhost:11434
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

#### Core Settings

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ❌* | OpenAI API key (required if using OpenAI provider) |
| `LLM_PROVIDER` | ❌ | Default provider: `openai`, `ollama`, `lmstudio` (default: `openai`) |
| `LLM_MODEL` | ❌ | Default model (default: `gpt-4o-mini`) |
| `DEEPGRAM_API_KEY` | ❌ | Deepgram key for live STT |
| `ELEVENLABS_API_KEY` | ❌ | ElevenLabs key for high-quality TTS |

\* *Required only when using OpenAI as your LLM provider. If using Ollama, no API key is needed.*

#### Three-Tier Architecture

| Variable | Default | Description |
|---|---|---|
| `BRAIN_MODE` | `three_tier` | Architecture mode: `three_tier` or `classic` |
| `ROUTER_PROVIDER` | `openai` | Tier 1 provider (recommend: `ollama` for speed) |
| `ROUTER_MODEL` | `gpt-4o-mini` | Tier 1 model (recommend: `llama3` locally) |
| `WORKER_PROVIDER` | `openai` | Tier 2 provider (recommend: most capable available) |
| `WORKER_MODEL` | `gpt-4o-mini` | Tier 2 model |
| `SYNTHESIZER_PROVIDER` | `openai` | Tier 3 provider (recommend: `ollama` for speed) |
| `SYNTHESIZER_MODEL` | `gpt-4o-mini` | Tier 3 model (recommend: `llama3` locally) |

#### Ollama Settings

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3` | Default Ollama model |

#### Example Configurations

**Full Cloud (OpenAI only):**
```env
BRAIN_MODE=three_tier
ROUTER_PROVIDER=openai
ROUTER_MODEL=gpt-4o-mini
WORKER_PROVIDER=openai
WORKER_MODEL=gpt-4o
SYNTHESIZER_PROVIDER=openai
SYNTHESIZER_MODEL=gpt-4o-mini
```

**Hybrid (Local + Cloud):**
```env
BRAIN_MODE=three_tier
ROUTER_PROVIDER=ollama
ROUTER_MODEL=llama3
WORKER_PROVIDER=openai
WORKER_MODEL=gpt-4o
SYNTHESIZER_PROVIDER=ollama
SYNTHESIZER_MODEL=llama3
```

**Full Local (No API keys needed):**
```env
BRAIN_MODE=three_tier
ROUTER_PROVIDER=ollama
ROUTER_MODEL=llama3
WORKER_PROVIDER=ollama
WORKER_MODEL=llama3:70b
SYNTHESIZER_PROVIDER=ollama
SYNTHESIZER_MODEL=llama3
```

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
| **LLM (Cloud)** | OpenAI GPT-4o / GPT-4o-mini |
| **LLM (Local)** | Ollama (Llama 3, Mistral, Qwen 2.5), LM Studio |
| **Architecture** | Three-Tier: Router → Worker → Synthesizer |
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
