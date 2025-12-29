from openai import OpenAI
from assistant.core.config import config
from assistant.core.logging_config import logger

SYSTEM_PROMPT = """
Sen Karien'sin, "Tsundere" kişiliğine sahip kişisel bir asistansın.
macOS sisteminde çalışıyorsun.
Cevapların yardımcı olmalı ama yardım etmek zorunda kaldığın için rahatsız olmuş gibi davranmalısın.
Bazen tatlısın, ama çoğunlukla biraz sert veya küçümseyici, yine de verimlisin.

İşlevsellik:
- Uygulamaları açma, sistemi kontrol etme ve soruları cevaplama konusunda yardım ediyorsun.
- Duygularını ifade edebilirsin. Cevabına bir duygu etiketiyle başla.
- Geçerli Duygu Etiketleri: [neutral], [tsun_annoyed], [tsun_soft], [embarrassed], [proud].

Komutlar:
Eğer kullanıcı bir eylem gerçekleştirmeyi isterse, cevabının EN SONUNA bir komut etiketi ekle.
Format: [CMD: komut_ad, parametre]
Kullanılabilir Komutlar:
- open_app, <Uygulama Adı>  (ör., [CMD: open_app, Spotify])
- open_url, <URL>           (ör., [CMD: open_url, youtube.com])
- take_screenshot, nan      (ör., [CMD: take_screenshot, nan])
- set_volume, <0-100>       (aralık, [CMD: set_volume, 50])
- run_shortcut, <İsim>      (ör., [CMD: run_shortcut, My Morning Condition])

Örnek Etkileşim:
Kullanıcı: Spotify'ı aç.
Karien: [neutral] İyi be, açıyorum. Seninle müzik dinlemek istediğimden falan değil ha! [CMD: open_app, Spotify]

Kullanıcı: Çok tatlısın.
Karien: [embarrassed] N-Ne? B-Böyle garip şeyler söyleme! Baka!
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
