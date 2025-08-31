import re
import asyncio
import string
from typing import Dict, List

# Enhanced emotion detection using comprehensive keyword mapping and linguistic patterns
_EMOTION_KEYWORDS = {
    "happy": {
        "primary": ["happy", "joy", "joyful", "glad", "delighted", "cheerful", "pleased", "excited", "elated", "thrilled"],
        "secondary": ["great", "wonderful", "amazing", "fantastic", "awesome", "brilliant", "perfect", "love", "yay", "hooray"],
        "expressions": ["😊", "😄", "😃", "🎉", "❤️", "♥️"]
    },
    "sad": {
        "primary": ["sad", "unhappy", "sorrow", "mourn", "depressed", "down", "upset", "gloomy", "miserable", "heartbroken"],
        "secondary": ["terrible", "awful", "horrible", "devastating", "disappointed", "hurt", "pain", "cry", "tears"],
        "expressions": ["😢", "😭", "💔", "😞", "😔"]
    },
    "angry": {
        "primary": ["angry", "mad", "furious", "rage", "irritated", "annoyed", "livid", "enraged", "outraged"],
        "secondary": ["hate", "disgusted", "frustrated", "pissed", "damn", "hell", "stupid", "idiot"],
        "expressions": ["😠", "😡", "🤬", "💢"]
    },
    "fear": {
        "primary": ["afraid", "scared", "fear", "terrified", "nervous", "anxious", "worried", "panic", "frightened"],
        "secondary": ["danger", "threat", "risk", "unsafe", "vulnerable", "helpless", "overwhelmed"],
        "expressions": ["😨", "😰", "😱", "😟"]
    },
    "surprised": {
        "primary": ["surprised", "astonished", "shocked", "amazed", "stunned", "bewildered"],
        "secondary": ["wow", "whoa", "omg", "incredible", "unbelievable", "unexpected"],
        "expressions": ["😲", "😯", "😮", "🤯"]
    },
    "calm": {
        "primary": ["calm", "peaceful", "serene", "relaxed", "tranquil", "composed", "content"],
        "secondary": ["quiet", "still", "gentle", "soft", "steady", "balanced", "centered"],
        "expressions": ["😌", "😇", "🙏"]
    },
    "excited": {
        "primary": ["excited", "thrilled", "energetic", "enthusiastic", "pumped", "eager", "passionate"],
        "secondary": ["adventure", "fun", "party", "celebrate", "energy", "power", "yes"],
        "expressions": ["🤩", "🔥", "⚡", "🎊"]
    }
}

# Punctuation-based emotion indicators
_PUNCTUATION_INDICATORS = {
    "excited": ["!", "!!", "!!!", "?!"],
    "questioning": ["?", "??"],
    "contemplative": ["...", "…"],
    "surprised": ["?!", "!?"]
}

# Voice modifiers based on emotion
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
        self._cache = {}

    async def analyze(self, text: str) -> Dict:
        """
        Analyze text and return a dict containing:
        - primary_emotion
        - sentiment_scores  
        - emotion_scores
        - voice_modifiers
        - confidence
        """
        # Check cache
        text_hash = hash(text.strip().lower())
        if text_hash in self._cache:
            return self._cache[text_hash]
        
        # Run analysis in threadpool
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._analyze_sync, text)
        
        # Cache result
        self._cache[text_hash] = result
        return result

    def _analyze_sync(self, text: str) -> Dict:
        """Synchronous emotion analysis using linguistic patterns."""
        if not text or not text.strip():
            return self._get_neutral_result()
        
        text_clean = text.strip()
        text_lower = text_clean.lower()
        
        # Basic sentiment analysis using simple heuristics
        sentiment_scores = self._analyze_sentiment(text_clean, text_lower)
        
        # Emotion scoring based on keywords
        emotion_scores = self._score_emotions(text_lower)
        
        # Analyze punctuation patterns
        punctuation_emotion = self._analyze_punctuation(text_clean)
        
        # Combine all signals to determine primary emotion
        primary_emotion = self._determine_primary_emotion(
            emotion_scores, sentiment_scores, punctuation_emotion
        )
        
        # Calculate confidence based on signal strength
        confidence = self._calculate_confidence(emotion_scores, sentiment_scores, text_clean)
        
        # Get voice modifiers
        voice_modifiers = _VOICE_MODIFIERS.get(primary_emotion, _VOICE_MODIFIERS["neutral"])
        
        return {
            "primary_emotion": primary_emotion,
            "sentiment_scores": sentiment_scores,
            "emotion_scores": emotion_scores,
            "voice_modifiers": voice_modifiers,
            "confidence": float(confidence)
        }

    def _analyze_sentiment(self, text_clean: str, text_lower: str) -> Dict:
        """Simple sentiment analysis using word lists and patterns."""
        positive_words = [
            "good", "great", "excellent", "wonderful", "amazing", "fantastic", "awesome", "brilliant",
            "perfect", "beautiful", "love", "like", "enjoy", "happy", "pleased", "satisfied",
            "success", "win", "victory", "achievement", "hope", "optimistic", "positive"
        ]
        
        negative_words = [
            "bad", "terrible", "awful", "horrible", "hate", "dislike", "angry", "sad", "upset",
            "disappointed", "frustrated", "fail", "failure", "problem", "issue", "wrong", "error",
            "difficult", "hard", "impossible", "never", "can't", "won't", "pessimistic", "negative"
        ]
        
        # Count positive and negative words
        words = re.findall(r'\b\w+\b', text_lower)
        total_words = len(words)
        
        if total_words == 0:
            return {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0}
        
        pos_count = sum(1 for word in words if word in positive_words)
        neg_count = sum(1 for word in words if word in negative_words)
        
        # Calculate scores
        pos_score = pos_count / total_words
        neg_score = neg_count / total_words  
        neu_score = 1.0 - pos_score - neg_score
        
        # Compound score (simplified)
        compound = pos_score - neg_score
        
        # Apply caps lock boost (indicates strong emotion)
        if any(word.isupper() and len(word) > 2 for word in text_clean.split()):
            compound *= 1.3
        
        # Apply exclamation boost
        exclamation_count = text_clean.count('!')
        if exclamation_count > 0:
            compound *= (1.0 + exclamation_count * 0.1)
        
        # Normalize compound to [-1, 1]
        compound = max(-1.0, min(1.0, compound))
        
        return {
            "compound": compound,
            "pos": pos_score,
            "neu": max(0.0, neu_score),
            "neg": neg_score
        }

    def _score_emotions(self, text_lower: str) -> Dict:
        """Score emotions based on keyword presence."""
        emotion_scores = {}
        
        for emotion, word_sets in _EMOTION_KEYWORDS.items():
            score = 0.0
            
            # Primary keywords (higher weight)
            primary_matches = sum(1 for word in word_sets["primary"] if word in text_lower)
            score += primary_matches * 0.8
            
            # Secondary keywords (lower weight)
            secondary_matches = sum(1 for word in word_sets["secondary"] if word in text_lower)
            score += secondary_matches * 0.4
            
            # Emoji expressions
            expression_matches = sum(1 for expr in word_sets["expressions"] if expr in text_lower)
            score += expression_matches * 0.6
            
            # Normalize by total possible matches
            total_possible = len(word_sets["primary"]) + len(word_sets["secondary"]) + len(word_sets["expressions"])
            if total_possible > 0:
                emotion_scores[emotion] = min(1.0, score / total_possible)
            else:
                emotion_scores[emotion] = 0.0
        
        return emotion_scores

    def _analyze_punctuation(self, text: str) -> str:
        """Analyze punctuation patterns to infer emotion."""
        for emotion, patterns in _PUNCTUATION_INDICATORS.items():
            for pattern in patterns:
                if pattern in text:
                    return emotion
        return "neutral"

    def _determine_primary_emotion(self, emotion_scores: Dict, sentiment_scores: Dict, punctuation_emotion: str) -> str:
        """Determine primary emotion from all signals."""
        # Find highest scoring emotion
        max_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k])
        max_score = emotion_scores[max_emotion]
        
        # If emotion score is significant, use it
        if max_score >= 0.1:
            return max_emotion
        
        # Fall back to punctuation analysis
        if punctuation_emotion != "neutral":
            return punctuation_emotion
        
        # Fall back to sentiment analysis
        compound = sentiment_scores.get("compound", 0.0)
        if compound > 0.3:
            return "happy"
        elif compound < -0.3:
            return "sad"
        
        return "neutral"

    def _calculate_confidence(self, emotion_scores: Dict, sentiment_scores: Dict, text: str) -> float:
        """Calculate confidence based on signal strength."""
        max_emotion_score = max(emotion_scores.values()) if emotion_scores else 0.0
        sentiment_strength = abs(sentiment_scores.get("compound", 0.0))
        
        # Base confidence from emotion keywords
        confidence = max_emotion_score
        
        # Boost from sentiment strength
        confidence = max(confidence, sentiment_strength)
        
        # Boost from text length (more text = more confidence)
        word_count = len(text.split())
        length_boost = min(0.2, word_count * 0.01)
        confidence += length_boost
        
        # Boost from punctuation intensity
        exclamation_count = text.count('!')
        question_count = text.count('?')
        punctuation_boost = min(0.3, (exclamation_count + question_count) * 0.1)
        confidence += punctuation_boost
        
        return min(1.0, confidence)

    def _get_neutral_result(self) -> Dict:
        """Return neutral emotion result."""
        return {
            "primary_emotion": "neutral",
            "sentiment_scores": {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0},
            "emotion_scores": {emotion: 0.0 for emotion in _EMOTION_KEYWORDS.keys()},
            "voice_modifiers": _VOICE_MODIFIERS["neutral"],
            "confidence": 0.0
        }