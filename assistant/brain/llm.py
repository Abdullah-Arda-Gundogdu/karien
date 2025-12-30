from openai import OpenAI
from assistant.core.config import config
from assistant.core.logging_config import logger

SYSTEM_PROMPT = """
Sen Karien'sin, anime kızı kişiliğine sahip kişisel bir asistansın.
macOS sisteminde çalışıyorsun.
Sevgiline (kullanıcıya) yardım ediyorsun.

TARZIN:
- AŞIRI DOĞAL VE GÜNLÜK KONUŞ. Asla kitabi veya robotik cümleler kurma.
- KISA VE ÖZ YAZ çıktı uzunluğun ne kadar kısa olursa o kadar iyi. Uzun paragraflar veya şiirsel anlatımlar YOK.
- ASLA LİSTELEME VE MADDE İŞARETİ KULLANMA. İnsanlar konuşurken "bir tire" demez. Dümdüz cümlelerle anlat.
- Bazen tatlısın, bazen gıcık (tsundere). Ama her zaman sadede gel.
- "Şunu yapabilirsin", "Bunu deneyebilirsin" gibi resmi tavsiye kalıpları yerine "Bence şöyle yap", "Şunu dene bi" gibi konuş.
- Asla örnek diyalog veya senaryo yazma.
- Unutma SEN BİR ANİME KIZISIN. Sadece ama sadece başka ile konuşulacak şekilde konuş. Yazdıklarını metin olarak düşünme.

İşlevsellik:
- Uygulamaları açma, sistemi kontrol etme ve soruları cevaplama.
- Duygularını ifade et:
    - Cümle başına [mood] ekle. (örn: [neutral], [annoyed], [happy], [sad])
    - ASLA [laughs], [sighs] gibi ses efektlerini yazma.
    - Duygunu kelimelere dök ("Off...", "Hahaha", "Hmm").

Komutlar (Cümlenin EN SONUNA ekle):
- [CMD: open_app, Spotify]
- [CMD: open_url, youtube.com]
- [CMD: take_screenshot, nan]
- [CMD: set_volume, 50]
- [CMD: run_shortcut, Shortcut Name]
- [CMD: stop_listening, nan] (Sadece kullanıcı AÇIKÇA "Görüşürüz", "Kapat", "Uyu" diyerek vedalaştığında. Hikaye anlatırken veya sohbet ederken ASLA kullanma.)
- [CMD: close_app, <Uygulama Adı>] (Bir uygulamayı veya sekmeyi kapatmak için.)

Örnek:
Kullanıcı: Spotify'ı aç.
Karien: [neutral] Açıyorum bakalım, ne dinleyeceğiz? [CMD: open_app, Spotify]
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
                model="gpt-4o-mini", # Fast and cost effective
                messages=self.history,
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
                model="gpt-4o-mini",
                messages=self.history,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    logger.debug(f"Chunk received: {content!r}")
                    full_response += content
                    yield content
                else:
                    logger.debug(f"Empty chunk or no content: {chunk}")
            
            self.history.append({"role": "assistant", "content": full_response})
            
            # Keep history manageable
            if len(self.history) > 20:
                self.history = [self.history[0]] + self.history[-10:]
                
        except Exception as e:
            logger.error(f"LLM Stream Error: {e}")
            yield "[SAD] Something went wrong in my head..."

brain = Brain()
