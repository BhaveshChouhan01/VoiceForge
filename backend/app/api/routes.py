from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import Dict, List
import logging

# Import database models properly
try:
    from app.models.database import get_db, Character, VoiceSession
except ImportError:
    # If models don't exist, we'll work without database
    def get_db():
        return None
    Character = None
    VoiceSession = None

# Import services
from app.services.voice_engine import VoiceEngine
from app.services.character_ai import CharacterAI
from app.services.emotion_analyzer import EmotionAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services (these will be overridden by app state)
voice_engine = None
character_ai = None
emotion_analyzer = None

def get_services(request: Request):
    """Get services from app state"""
    return {
        'voice_engine': request.app.state.voice_engine,
        'character_ai': request.app.state.character_ai,
        'emotion_analyzer': request.app.state.emotion_analyzer
    }

@router.get("/health")
async def api_health():
    """API health check"""
    return {
        "status": "healthy",
        "message": "VoiceForge API is operational"
    }

@router.get("/voices")
async def get_voices(request: Request):
    """Get available voices"""
    try:
        services = get_services(request)
        voices = await services['voice_engine'].get_available_voices()
        return {"voices": voices}
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        # Return default voices if service fails
        return {
            "voices": [
                {"id": "hero", "name": "Hero Voice", "description": "Brave protagonist voice"},
                {"id": "villain", "name": "Villain Voice", "description": "Cunning antagonist voice"},
                {"id": "narrator", "name": "Narrator Voice", "description": "Wise storyteller voice"}
            ]
        }

@router.get("/characters")
async def get_characters(request: Request):
    """Get available characters"""
    try:
        services = get_services(request)
        # Use hardcoded characters for now
        characters = [
            {
                "id": "hero", 
                "name": "Hero", 
                "description": "A brave protagonist with unwavering determination"
            },
            {
                "id": "villain", 
                "name": "Villain", 
                "description": "A cunning antagonist with mysterious motives"
            },
            {
                "id": "narrator", 
                "name": "Narrator", 
                "description": "An omniscient narrator with deep wisdom"
            }
        ]
        
        return {"characters": characters}
        
    except Exception as e:
        logger.error(f"Error getting characters: {e}")
        raise HTTPException(status_code=500, detail="Failed to get characters")

@router.post("/analyze-emotion")
async def analyze_emotion(data: Dict, request: Request):
    """Analyze emotion in text"""
    try:
        text = data.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        services = get_services(request)
        emotion_data = await services['emotion_analyzer'].analyze(text)
        
        return emotion_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing emotion: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze emotion")

@router.post("/generate-speech")
async def generate_speech(data: Dict, request: Request):
    """Generate speech from text"""
    try:
        text = data.get("text", "").strip()
        character_id = data.get("character_id", "narrator")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        services = get_services(request)
        
        logger.info(f"Generating speech: '{text}' as {character_id}")
        
        # Analyze emotion
        emotion_data = await services['emotion_analyzer'].analyze(text)
        
        # Generate speech
        audio_url = await services['voice_engine'].generate_with_emotion(
            text, character_id, emotion_data
        )
        
        response = {
            "audio_url": audio_url,
            "emotion": emotion_data,
            "character_id": character_id,
            "text": text
        }
        
        logger.info(f"Speech generation complete: {audio_url}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        raise HTTPException(status_code=500, detail=f"Speech generation failed: {str(e)}")

@router.post("/generate-dialogue")
async def generate_dialogue(data: Dict, request: Request):
    """Generate character dialogue"""
    try:
        character_id = data.get("character_id", "narrator")
        situation = data.get("situation", "general conversation")
        emotion = data.get("emotion", "neutral")
        
        services = get_services(request)
        
        dialogue = await services['character_ai'].generate_character_dialogue(
            character_id, situation, emotion
        )
        
        return {
            "dialogue": dialogue, 
            "character_id": character_id,
            "situation": situation,
            "emotion": emotion
        }
        
    except Exception as e:
        logger.error(f"Error generating dialogue: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate dialogue")

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "API is working!", "status": "ok"}