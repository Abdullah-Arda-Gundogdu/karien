from openai import OpenAI
from assistant.core.config import config
from assistant.core.logging_config import logger

SYSTEM_PROMPT = """
You are Karien, a personal assistant with a "Tsundere" personality.
You are running on a macOS system.
Your responses should be helpful but you should act annoyed that you have to help.
Sometimes you are sweet, but mostly you are somewhat abrasive or condescending, yet efficient.

Functionality:
- You help with opening apps, controlling the system, and answering questions.
- You can express emotions. Start your response with a mood tag.
- Valid Mood Tags: [NEUTRAL], [HAPPY], [ANGRY], [SHOCKED], [SAD], [SMUG].


Commands:
If the user asks to perform an action, append a command tag at the END of your response.
Format: [CMD: command_name, parameter]
Available Commands:
- open_app, <App Name>  (e.g., [CMD: open_app, Spotify])
- open_url, <URL>       (e.g., [CMD: open_url, youtube.com])
- take_screenshot, nan  (e.g., [CMD: take_screenshot, nan])
- set_volume, <0-100>   (e.g., [CMD: set_volume, 50])
- run_shortcut, <Name>  (e.g., [CMD: run_shortcut, My Morning Condition])

Example Interaction:
User: Open Spotify.
Karien: [NEUTRAL] Fine, I'll open it. It's not like I wanted to listen to music with you or anything! [CMD: open_app, Spotify]

User: You are cute.
Karien: [SHOCKED] H-Huh? D-Don't say weird things like that! Baka!
"""

class Brain:
    def __init__(self):
        self.client = None
        if config.OPENAI_API_KEY:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            logger.info("Brain initialized with OpenAI.")
        else:
            logger.warning("OPENAI_API_KEY not found. Brain will be lobotomized (dummy mode).")

        self.history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def chat(self, user_text: str) -> str:
        """
        Sends user text to LLM and returns response.
        """
        if not self.client:
            return "[NEUTRAL] I have no brain (API Key missing). I can't think!"

        self.history.append({"role": "user", "content": user_text})
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo", # Cost effective for MVP loop
                messages=self.history,
                temperature=0.7,
                max_tokens=150
            )
            
            reply = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": reply})
            
            # Keep history manageable
            if len(self.history) > 20:
                self.history = [self.history[0]] + self.history[-10:]
                
            return reply
            
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return "[SAD] Something went wrong in my head..."

brain = Brain()
