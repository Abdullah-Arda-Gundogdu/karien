# Karien Assistant

Karien is a modular, AI-powered Virtual Assistant featuring a multi-tier cognitive architecture. It combines advanced Language Models (LLMs), multimodal capabilities (Vision, Speech-to-Text, and Text-to-Speech), and PC control to act as an interactive and capable desktop agent. 

Moreover, Karien seamlessly integrates with **VTube Studio**, enabling the assistant to control a live VTuber avatar with lip-sync and emotional expressions based on the interaction.

---

## 🌟 Key Features

* **Three-Tier Cognitive Architecture**: Built around a Router, Worker, and Synthesizer flow to handle reasoning, tool execution, and final response generation.
* **VTube Studio Integration**: Connects via WebSocket (`127.0.0.1:8001`) to control VTuber avatars, including real-time lip-sync and dynamic mood adjustments.
* **Multimodal Input/Output**:
  * **Speech Recognition**: Local (Vosk) or Cloud-based (Deepgram) Speech-to-Text.
  * **Text-to-Speech (TTS)**: High-quality voice using ElevenLabs, or local fallback with `pyttsx3`.
  * **Vision & Screen Awareness**: Utilizes `gpt-4o` combined with `pywinauto` and `pyautogui` for screen reading and UI automation.
* **Model Context Protocol (MCP)**: Extensible capabilities through an MCP catalog, allowing Karien to dynamically load tools and skills.
* **Orchestrator**: Asynchronous event-driven orchestrator managing the lifecycle of jobs, UI events, and connections.

---

## 🛠️ Prerequisites

* **Python 3.10+**
* [VTube Studio](https://store.steampowered.com/app/1325860/VTube_Studio/) with the API/WebSocket enabled (Port: `8001`).
* Required API Keys (depending on modules used):
  * OpenAI API Key (Required for core reasoning)
  * ElevenLabs API Key (For premium TTS)
  * Deepgram API Key (For fast cloud STT)

---

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Abdullah-Arda-Gundogdu/karien.git
   cd karien
   ```

2. **Set up a virtual environment (Recommended):**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables Configuration:**
   Copy the example environment file and add your credentials:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` and fill in your `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, and other required keys.*

5. **Authenticate VTube Studio (Optional but Recommended):**
   When the assistant runs for the first time, VTube Studio will prompt you to "Allow" a new plugin connection. Give Karien the necessary permissions. The token will be saved in `.secrets/vts_token.json`.

---

## 🎮 Usage

To start Karien, run the orchestrator script:

```bash
python assistant/main.py
```

Check the `docs/` folder for additional setup instructions (e.g., `setup_lip_sync.md`).

---

## 📁 Project Structure

```text
karien/
├── assistant/
│   ├── brain/        # Core LLM reasoning, context, and memory management
│   ├── core/         # Orchestrator, Configuration, Authentication, Logging
│   ├── input/        # Speech Recognition (VAD, STT)
│   ├── mcp/          # Model Context Protocol integration and tool registry
│   ├── output/       # Text-to-Speech handling, VTube Studio WebSocket link
│   ├── skills/       # Custom skills and execution modules
│   ├── ui/           # CustomTkinter based graphical interfaces
│   └── main.py       # Main entry point
├── config/           # Static configurations, moods, tool catalogs
├── docs/             # Project documentation and guides
├── scripts/          # Helper and utility scripts
├── .env.example      # Environment variables template
└── requirements.txt  # Python requirements
```

## 📜 License
This project is for educational and research purposes.
