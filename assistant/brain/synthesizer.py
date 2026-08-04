"""
Tier 3: Response Synthesizer

The final layer of Karien's three-tier cognitive architecture.
Takes raw Worker output and transforms it into Karien's personality:
tsundere anime girl with mood tags and natural Turkish speech.

Design rationale:
- Separating personality from task execution prevents the personality
  prompt from "competing" with tool-calling instructions, reducing hallucinations
- Uses a lightweight model since the task is simple text transformation
- Adds mood tags ([happy], [annoyed], etc.) based on content analysis
- Ensures consistent character voice regardless of Worker model used
"""

import re
from typing import Generator
from assistant.core.logging_config import logger
from assistant.brain.providers.base import LLMProvider, StreamChunk

# The 9 moods the orb face and VTube Studio hotkeys understand
VALID_MOODS = {
    "neutral", "happy", "sad", "annoyed", "embarrassed",
    "proud", "curious", "excited", "sleepy",
}


def normalize_mood_tag(text: str) -> str:
    """
    Ensure the response starts with a VALID mood tag. Small local models
    sometimes invent tags like [Empati] which the UI cannot render.
    """
    if not text:
        return "[neutral]"
    match = re.match(r"^\s*\[([^\]]+)\]\s*", text)
    if not match:
        return "[neutral] " + text.strip()
    mood = match.group(1).strip().lower()
    rest = text[match.end():].strip()
    if mood not in VALID_MOODS:
        mood = "neutral"
    return f"[{mood}] {rest}" if rest else f"[{mood}]"


# Synthesizer system prompt — personality formatting only
SYNTHESIZER_SYSTEM_PROMPT = """Sen Karien'sin. Senden bir bilgi/cevap verilecek ve senin görevin bunu kendi kişiliğinle yeniden ifade etmek.

KİŞİLİĞİN:
- Tsundere anime kızısın. Bazen tatlı, bazen gıcık.
- AŞIRI DOĞAL ve KISA konuş. Robotik olma.
- Listeleme ve madde işareti KULLANMA.
- "Şunu yapabilirsin" yerine "Şunu dene bi" gibi konuş.

ZORUNLU FORMAT:
- Cümlenin BAŞINA mood tag ekle: [neutral], [happy], [sad], [annoyed], [embarrassed], [proud], [curious], [excited], [sleepy]
- Mood'u içeriğe göre belirle (olumlu → happy/excited, hata → annoyed/sad, bilgi → neutral/curious)
- KISA TUT. Maksimum 2-3 cümle.
- Asla [laughs], [sighs] gibi ses efektleri yazma. Duygunu kelimelerle ifade et ("Hahaha", "Off...", "Hmm").

ÖRNEK:
Giriş: "Spotify uygulaması açıldı."
Çıkış: [neutral] Açtım bakalım, ne dinleyeceğiz?

Giriş: "İstanbul'da hava 25 derece ve güneşli."
Çıkış: [happy] Süpermiş ya, 25 derece güneşli diyor! Dışarı çıkalım mı?

Giriş: "Dosya bulunamadı, hata oluştu."
Çıkış: [annoyed] Tsk, dosya yok diyor. Yolu doğru yazdın mı bari?
"""


class Synthesizer:
    """
    Tier 3 — Response Synthesizer.
    
    Transforms raw Worker output into Karien's personality voice.
    This separation ensures that personality prompts don't interfere
    with tool calling and factual reasoning in the Worker tier.
    
    Performance target: < 300ms with local model, < 600ms with cloud.
    """
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        logger.info(f"Synthesizer initialized with {provider}")
    
    def synthesize(self, raw_content: str, user_text: str = "") -> str:
        """
        Transform raw Worker output into Karien's voice.
        
        Args:
            raw_content: Raw text from Worker tier
            user_text: Original user message (for context)
            
        Returns:
            Personality-formatted response with mood tag
        """
        if not raw_content or not raw_content.strip():
            return "[neutral] Hmm, bir şey bulamadım."
        
        # If content already has a mood tag, skip synthesis
        if raw_content.strip().startswith("[") and "]" in raw_content[:20]:
            logger.debug("Content already has mood tag, skipping synthesis")
            return normalize_mood_tag(raw_content)
        
        messages = [
            {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Kullanıcının sorusu: {user_text}\n\nCevap bilgisi: {raw_content}"},
        ]
        
        try:
            response = self.provider.complete(
                messages=messages,
                stream=False,
                max_tokens=150,  # Synthesized output should be short
            )
            
            result = normalize_mood_tag(response.content.strip())

            logger.debug(f"Synthesized: '{raw_content[:50]}...' → '{result[:50]}...'")
            return result
            
        except Exception as e:
            logger.error(f"Synthesizer failed: {e}")
            # Fallback: add neutral tag to raw content
            return f"[neutral] {raw_content}"
    
    def synthesize_stream(self, raw_content: str, user_text: str = "") -> Generator:
        """
        Streaming version of synthesize for real-time TTS.
        
        Yields text chunks as they come from the model.
        """
        if not raw_content or not raw_content.strip():
            yield "[neutral] Hmm, bir şey bulamadım."
            return
        
        # If already formatted, yield as-is
        if raw_content.strip().startswith("[") and "]" in raw_content[:20]:
            yield raw_content
            return
        
        messages = [
            {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Kullanıcının sorusu: {user_text}\n\nCevap bilgisi: {raw_content}"},
        ]
        
        try:
            stream = self.provider.complete(
                messages=messages,
                stream=True,
                max_tokens=150,
            )
            
            for chunk in stream:
                if chunk.chunk_type == "content" and chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f"Synthesizer stream failed: {e}")
            yield f"[neutral] {raw_content}"
