import re
import asyncio
from typing import Dict, List

# Optional dependencies
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except Exception:
    SentimentIntensityAnalyzer = None

try:
    from textblob import TextBlob
except Exception:
    TextBlob = None

# simple keyword map as robust fallback
_EMOTION_KEYWORDS = {
    "happy": ["happy", "joy", "glad", "delighted", "cheerful", "yay", "pleased", "excited"],
    "sad": ["sad", "unhappy", "sorrow", "mourn", "depressed", "down", "upset", "gloomy"],
    "angry": ["angry", "mad", "furious", "rage", "irritated", "annoyed"],
    "fear": ["afraid", "scared", "fear", "terrified", "nervous", "anxious", "worried"],
    "surprised": ["surprised", "astonished", "shocked", "wow", "whoa"],
    "calm": ["calm", "peaceful", "serene", "relaxed", "tranquil"],
    "excited": ["excited", "thrilled", "energetic", "enthusiastic"]
}

_VOICE_MODIFIERS = {
    "happy": {"speed_modifier": 1.15, "pitch_modifier": 1.05},
    "sad": {"speed_modifier": 0.85, "pitch_modifier": 0.9},
    "angry": {"speed_modifier": 1.25, "pitch_modifier": 1.02},
    "fear": {"speed_modifier": 1.05, "pitch_modifier": 0.95},
    "surprised": {"speed_modifier": 1.3, "pitch_modifier": 1.15},
    "calm": {"speed_modifier": 0.95, "pitch_modifier": 1.0},
    "excited": {"speed_modifier": 1.25, "pitch_modifier": 1.15},
    "neutral": {"speed_modifier": 1.0, "pitch_modifier": 1.0}
}


class EmotionAnalyzer:
    def __init__(self):
        # Use VADER if available for sentiment scoring
        self.vader = SentimentIntensityAnalyzer() if SentimentIntensityAnalyzer else None

    async def analyze(self, text: str) -> Dict:
        """
        Analyze text and return a dict containing:
        - primary_emotion
        - sentiment_scores
        - emotion_scores
        - voice_modifiers
        - confidence
        """
        # Run synchronous analysis in threadpool
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._analyze_sync, text)

    def _analyze_sync(self, text: str) -> Dict:
        txt = (text or "").strip()
        text_lower = txt.lower()

        # sentiment
        sentiment = {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
        try:
            if self.vader:
                sentiment = self.vader.polarity_scores(text)
            elif TextBlob:
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity
                sentiment = {"neg": max(0, -polarity), "neu": 1 - abs(polarity), "pos": max(0, polarity), "compound": polarity}
        except Exception:
            # keep defaults
            pass

        # keyword-based emotion scoring
        emotion_scores = {}
        for emo, keywords in _EMOTION_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            emotion_scores[emo] = min(1.0, count / max(1, len(keywords)))

        # choose primary emotion: highest score or based on sentiment when no keywords
        primary_emotion = max(emotion_scores, key=emotion_scores.get)
        if emotion_scores.get(primary_emotion, 0.0) < 0.1:
            comp = sentiment.get("compound", 0.0)
            if comp > 0.3:
                primary_emotion = "happy"
            elif comp < -0.3:
                primary_emotion = "sad"
            else:
                primary_emotion = "neutral"

        voice_modifiers = _VOICE_MODIFIERS.get(primary_emotion, _VOICE_MODIFIERS["neutral"])
        confidence = min(1.0, abs(sentiment.get("compound", 0.0)))

        return {
            "primary_emotion": primary_emotion,
            "sentiment_scores": sentiment,
            "emotion_scores": emotion_scores,
            "voice_modifiers": voice_modifiers,
            "confidence": float(confidence)
        }