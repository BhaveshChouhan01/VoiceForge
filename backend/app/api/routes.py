from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db, Character, VoiceSession
from app.services.voice_engine import VoiceEngine
from app.services.character_ai import CharacterAI
from app.services.emotion_analyzer import EmotionAnalyzer
from typing import Dict, List
import uuid

router = APIRouter()

# Initialize services
voice_engine = VoiceEngine()
character_ai = CharacterAI()
emotion_analyzer = EmotionAnalyzer()

@router.get("/voices")
async def get_voices():
    """Get available voices"""
    voices = await voice_engine.get_available_voices()
    return {"voices": voices}

@router.get("/characters")
async def get_characters():
    """Get available characters"""
    characters = [
        {"id": "hero", "name": "Hero", "description": "Brave protagonist"},
        {"id": "villain", "name": "Villain", "description": "Cunning antagonist"},
        {"id": "narrator", "name": "Narrator", "description": "Wise storyteller"}
    ]
    return {"characters": characters}

@router.post("/analyze-emotion")
async def analyze_emotion(data: Dict):
    """Analyze emotion in text"""
    text = data.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    emotion_data = await emotion_analyzer.analyze(text)
    return emotion_data

@router.post("/generate-speech")
async def generate_speech(data: Dict):
    """Generate speech from text"""
    text = data.get("text", "")
    character_id = data.get("character_id", "narrator")
    
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    # Analyze emotion
    emotion_data = await emotion_analyzer.analyze(text)
    
    # Generate speech
    audio_url = await voice_engine.generate_with_emotion(
        text, character_id, emotion_data
    )
    
    return {
        "audio_url": audio_url,
        "emotion": emotion_data,
        "character_id": character_id,
        "text": text
    }

@router.post("/generate-dialogue")
async def generate_dialogue(data: Dict):
    """Generate character dialogue"""
    character_id = data.get("character_id", "narrator")
    situation = data.get("situation", "general conversation")
    emotion = data.get("emotion", "neutral")
    
    dialogue = await character_ai.generate_character_dialogue(
        character_id, situation, emotion
    )
    
    return {"dialogue": dialogue, "character_id": character_id}