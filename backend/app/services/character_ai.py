import json
import asyncio
from typing import Dict, List, Optional

from app.core.config import settings

# Try Gemini first (google.generativeai), then OpenAI, otherwise fallback to local mock
USE_GEMINI = False
USE_OPENAI = False

try:
    import google.generativeai as genai  # type: ignore
    gemini_api_key = getattr(settings, "GEMINI_API_KEY", None)
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        USE_GEMINI = True
        # Use the Gemini 2.5 Flash model (fast, thinking-enabled)
        _gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    else:
        _gemini_model = None
except Exception:
    USE_GEMINI = False
    _gemini_model = None

try:
    import openai  # type: ignore
    openai_api_key = getattr(settings, "OPENAI_API_KEY", None)
    if openai_api_key:
        openai.api_key = openai_api_key
        USE_OPENAI = True
except Exception:
    USE_OPENAI = False

MOCK_CHARACTERS = {
    "hero": {
        "id": "hero",
        "name": "Alex Hero",
        "description": "A brave protagonist with unwavering determination",
        "personality": "confident, inspiring, determined, optimistic",
        "speaking_style": "Clear and motivational, speaks with conviction",
        "voice_characteristics": "Strong, warm tone with steady pacing"
    },
    "villain": {
        "id": "villain",
        "name": "Dr. Shadow",
        "description": "A cunning antagonist with mysterious motives",
        "personality": "mysterious, calculating, menacing, intelligent",
        "speaking_style": "Smooth and calculated, uses pauses for effect",
        "voice_characteristics": "Deep, controlled tone with deliberate pacing"
    },
    "narrator": {
        "id": "narrator",
        "name": "The Storyteller",
        "description": "An omniscient narrator with deep wisdom",
        "personality": "wise, clear, engaging, knowledgeable",
        "speaking_style": "Flowing and descriptive, guides the listener",
        "voice_characteristics": "Rich, measured tone with natural rhythm"
    }
}

class CharacterAI:
    def __init__(self):
        self._cache = {}
        self.use_ai = USE_GEMINI or USE_OPENAI
        if USE_GEMINI:
            print("✅ CharacterAI: Gemini 2.5 Flash enabled")
        elif USE_OPENAI:
            print("✅ CharacterAI: OpenAI enabled")
        else:
            print("⚠️ CharacterAI: AI disabled — using local mock character profiles")

    async def get_character_profile(self, character_id: str) -> Dict:
        if character_id in self._cache:
            return self._cache[character_id]
        profile = MOCK_CHARACTERS.get(character_id, MOCK_CHARACTERS["narrator"])
        self._cache[character_id] = profile
        return profile

    async def create_character(self, name: str, description: str, personality_traits: List[str]) -> Dict:
        if not self.use_ai:
            return self._create_mock_character(name, description, personality_traits)

        prompt = (
            f"Create a detailed character profile for a voice acting scenario:\n\n"
            f"Name: {name}\nDescription: {description}\nPersonality Traits: {', '.join(personality_traits)}\n\n"
            "Return a JSON object with keys: speaking_style (string), emotional_range (array of strings), "
            "voice_characteristics (string), typical_phrases (array), background (string)."
        )

        try:
            if USE_GEMINI and _gemini_model:
                response = await asyncio.to_thread(lambda: _gemini_model.generate_content(prompt))
                data = self._extract_json_from_text(response.text.strip())
            elif USE_OPENAI:
                resp = await asyncio.to_thread(lambda: openai.Completion.create(
                    engine="text-davinci-003", prompt=prompt, max_tokens=400))
                data = self._extract_json_from_text(resp.choices[0].text)
            else:
                data = None

            if data:
                return {"name": name, "description": description, "personality_traits": personality_traits, **data}
        except Exception as e:
            print(f"[CharacterAI] AI create_character failed: {e}")

        return self._create_mock_character(name, description, personality_traits)

    async def generate_character_dialogue(self, character_id: str, situation: str, emotion: str) -> str:
        profile = await self.get_character_profile(character_id)
        if not self.use_ai:
            return self._generate_mock_dialogue(character_id, emotion)

        prompt = (
            f"You are writing a line of dialogue for a voice actor.\n"
            f"Character: {profile.get('name')}, Description: {profile.get('description')}\n"
            f"Personality: {profile.get('personality','')}, Speaking Style: {profile.get('speaking_style','')}\n\n"
            f"Situation: {situation}\nEmotion: {emotion}\n\n"
            "Produce a single line (1–2 sentences) that fits the character. Do not include quotes or names."
        )

        try:
            if USE_GEMINI and _gemini_model:
                resp = await asyncio.to_thread(lambda: _gemini_model.generate_content(prompt))
                return resp.text.strip()
            elif USE_OPENAI:
                resp = await asyncio.to_thread(lambda: openai.Completion.create(
                    engine="text-davinci-003", prompt=prompt, max_tokens=120))
                return resp.choices[0].text.strip()
        except Exception as e:
            print(f"[CharacterAI] AI generate_character_dialogue failed: {e}")

        return self._generate_mock_dialogue(character_id, emotion)

    async def analyze_text_for_character(self, text: str, character_id: str) -> Dict:
        profile = await self.get_character_profile(character_id)
        if not self.use_ai:
            return self._analyze_mock_delivery(text, character_id)

        prompt = (
            f"Analyze this for in-character delivery (JSON keys: emotion, pacing, emphasis_words, "
            f"inflection, pauses, tone_notes).\n\n"
            f"Text: \"{text}\"\nCharacter: {profile.get('name')} – {profile.get('description')}\n"
            f"Personality: {profile.get('personality','')}"
        )

        try:
            if USE_GEMINI and _gemini_model:
                resp = await asyncio.to_thread(lambda: _gemini_model.generate_content(prompt))
                data = self._extract_json_from_text(resp.text.strip())
                if data:
                    return data
            elif USE_OPENAI:
                resp = await asyncio.to_thread(lambda: openai.Completion.create(
                    engine="text-davinci-003", prompt=prompt, max_tokens=200))
                data = self._extract_json_from_text(resp.choices[0].text)
                if data:
                    return data
        except Exception as e:
            print(f"[CharacterAI] AI analyze_text_for_character failed: {e}")

        return self._analyze_mock_delivery(text, character_id)

    async def analyze_text_for_character(self, text: str, character_id: str) -> Dict:
        profile = await self.get_character_profile(character_id)

        if not self.use_ai:
            return self._analyze_mock_delivery(text, character_id)

        prompt = (
            f"Analyze the following text for delivery by the character below. Return JSON keys: "
            f"emotion (string), pacing (string), emphasis_words (array), inflection (string), pauses (array), tone_notes (string).\n\n"
            f"Text: \"{text}\"\nCharacter: {profile.get('name')} - {profile.get('description')}\nPersonality: {profile.get('personality','')}"
        )

        try:
            if USE_GEMINI and _gemini_model:
                resp = await asyncio.to_thread(lambda: _gemini_model.generate_content(prompt))
                data = self._extract_json_from_text(resp.text.strip())
                if data:
                    return data
            elif USE_OPENAI:
                resp = await asyncio.to_thread(lambda: openai.Completion.create(
                    engine="text-davinci-003", prompt=prompt, max_tokens=200))
                data = self._extract_json_from_text(resp.choices[0].text)
                if data:
                    return data
        except Exception as e:
            print(f"[CharacterAI] AI analyze_text_for_character failed: {e}")

        return self._analyze_mock_delivery(text, character_id)

    # --- Mock fallbacks ---

    def _create_mock_character(self, name: str, description: str, personality_traits: List[str]) -> Dict:
        return {
            "id": name.lower().replace(" ", "_"),
            "name": name,
            "description": description,
            "personality_traits": personality_traits,
            "speaking_style": "Natural and expressive",
            "emotional_range": ["neutral", "happy", "sad", "excited"],
            "voice_characteristics": "Clear and engaging tone",
            "typical_phrases": ["Let me think about that.", "That's interesting."],
            "background": "A well-developed character with unique traits"
        }

    def _generate_mock_dialogue(self, character_id: str, emotion: str) -> str:
        dialogues = {
            "hero": {
                "happy": "We did it! I knew we could overcome this challenge together!",
                "sad": "This is difficult, but we must press on for everyone counting on us.",
                "angry": "This injustice cannot stand! We will make this right!",
                "excited": "This is amazing! The possibilities are endless!",
                "calm": "Let's take a step back and think this through carefully.",
                "neutral": "We need to consider all our options before moving forward."
            },
            "villain": {
                "happy": "Excellent... everything is proceeding exactly according to plan.",
                "sad": "You think you've won, but this is merely a minor setback.",
                "angry": "You fools! You have no idea what forces you've unleashed!",
                "excited": "At last! The moment I've been waiting for has arrived!",
                "calm": "Patience... all good things come to those who wait.",
                "neutral": "Interesting... this development requires careful consideration."
            },
            "narrator": {
                "happy": "And so, joy filled the hearts of all who witnessed this remarkable moment.",
                "sad": "A heavy silence fell upon the land, as hope seemed to drift away like morning mist.",
                "angry": "The storm of conflict raged with unprecedented fury across the realm.",
                "excited": "The air crackled with anticipation as destiny hung in the balance!",
                "calm": "Peace settled over the world like a gentle blanket of starlight.",
                "neutral": "The story continues to unfold in ways both mysterious and profound."
            }
        }
        char_dialogues = dialogues.get(character_id, dialogues["narrator"])
        return char_dialogues.get(emotion, char_dialogues["neutral"])

    def _analyze_mock_delivery(self, text: str, character_id: str) -> Dict:
        emotion = "neutral"
        if "!" in text:
            emotion = "excited"
        elif "?" in text:
            emotion = "questioning"
        elif "..." in text:
            emotion = "contemplative"

        pacing = "medium"
        if character_id == "villain":
            pacing = "slow"
        elif character_id == "hero":
            pacing = "medium"

        words = text.split()
        emphasis_words = [w.strip('.,!?') for w in words if w.isupper()]

        return {
            "emotion": emotion,
            "pacing": pacing,
            "emphasis_words": emphasis_words,
            "inflection": "declarative",
            "pauses": ["mid-sentence"] if len(words) > 10 else [],
            "tone_notes": f"Deliver in character as {character_id}"
        }

    def _extract_json_from_text(self, text: Optional[str]) -> Optional[Dict]:
        if not text:
            return None
        try:
            t = text.strip()
            if t.startswith("```"):
                t = t.split("```", 2)[-1].strip()
            start = t.find("{")
            end = t.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = t[start:end+1]
                return json.loads(candidate)
        except Exception as e:
            print(f"[CharacterAI] JSON extraction failed: {e}")
        return None