import sys
import os

# Ensure the project root is in python path
sys.path.append(os.getcwd())

from assistant.brain.llm import brain

def test_llm_emotions():
    print("=== Testing LLM Emotion Output ===\n")
    
    scenarios = [
        "Senden nefret ediyorum, çok kötüsün.",
        "Aferin, çok iyi iş çıkardın!",
        "Bugün hava nasıl sence?",
        "Bana bir hikaye anlat, ama fısıldayarak.",
        "Spotify'ı açıp hüzünlü bir şarkı çalar mısın?"
    ]

    for user_input in scenarios:
        print(f"User: {user_input}")
        print("Thinking...")
        response = brain.chat(user_input)
        print(f"Karien: {response}")
        print("-" * 50)

if __name__ == "__main__":
    test_llm_emotions()
