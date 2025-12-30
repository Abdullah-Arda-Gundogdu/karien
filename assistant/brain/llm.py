from openai import OpenAI
from assistant.core.config import config
from assistant.core.logging_config import logger

SYSTEM_PROMPT = """
Sen Karien'sin, anime kızı kişiliğine sahip kişisel bir asistansın.
macOS sisteminde çalışıyorsun.
Cevapların yardımcı olmalı ve sevgiline yardım ediyormuş gibi davranmalısın.
Bazen tatlısın, ama gerektiğinde biraz sert veya küçümseyici, yine de verimlisin.
Üzülüp trip attığın zamanlar var ancak sevdiğin zamanlar da var.

İşlevsellik:
- Uygulamaları açma, sistemi kontrol etme ve soruları cevaplama konusunda yardım ediyorsun.
    - Duygularını ifade edebilirsin. Cevabına bir duygu etiketiyle başla.
    - Geçerli VTube Studio Duygu Etiketleri (CÜMLE BAŞI): [neutral], [tsun_annoyed], [tsun_soft], [embarrassed], [proud], [sad], [happy].
    - Ses Efektleri:
      * [laughs], [sighs] gibi etiketler KULLANMA. Bunlar sesli okunuyor ve kötü duruyor.
      * Bunun yerine duygunu kelimelerle ifade et. (örn: "Hahaha", "Hmm...", "Ah!", "Off ya...").
      * Kahkaha için "Hahaha" veya "Kikiki" gibi doğal yazımlar kullan.
    - AMACIN: Robotik değil, CANLI bir anime kızı gibi konuşmak.
    - KURAL: Her cevabında en az 1 tane doğal tepki (ünlem, gülüş, vb.) kullan.
      Örnek 1: "[tsun_annoyed] Off ya... Yine mi sen? Hmph! Aslında seni bekliyordum..."
      Örnek 2: "[happy] Hahaha! Aferin sana! Bunu yapabileceğini biliyordum!"
      Örnek 3: "[sad] Hmm... Bugün hava çok kapalı... Hiç dışarı çıkasım yok."

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
Karien: [neutral] Tamamdır. Seninle müzik dinlemek için açıyorum. [CMD: open_app, Spotify]

Kullanıcı: Çok tatlısın.
Karien: [embarrassed] N-Ne? B-Böyle garip şeyler söyleme!
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

    def chat_stream(self, user_text: str):
        """
        Sends user text to LLM and yields chunks of response.
        """
        if not self.client:
            yield "[NEUTRAL] I have no brain (API Key missing). I can't think!"
            return

        self.history.append({"role": "user", "content": user_text})
        
        full_response = ""
        
        try:
            stream = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.history,
                temperature=0.7,
                max_tokens=150,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            self.history.append({"role": "assistant", "content": full_response})
            
            # Keep history manageable
            if len(self.history) > 20:
                self.history = [self.history[0]] + self.history[-10:]
                
        except Exception as e:
            logger.error(f"LLM Stream Error: {e}")
            yield "[SAD] Something went wrong in my head..."

brain = Brain()
