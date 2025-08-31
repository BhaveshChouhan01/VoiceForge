# app/services/voice_engine.py
import os
import uuid
import asyncio
import aiohttp
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Settings import with fallback
try:
    from app.core.config import settings
    BASE_DIR = settings.BASE_DIR
    SERVER_URL = settings.SERVER_URL
    AUDIO_DIR = settings.AUDIO_DIR
    MURF_API_KEY = getattr(settings, 'MURF_API_KEY', None)
except ImportError:
    BASE_DIR = Path(__file__).resolve().parents[2]
    SERVER_URL = "http://localhost:8000"
    AUDIO_DIR = BASE_DIR / "static" / "audio"
    MURF_API_KEY = os.getenv('MURF_API_KEY')

# Ensure audio directory exists
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class VoiceEngine:
    def __init__(self):
        # Updated voice IDs based on actual Murf voices
        self.voices = {
            "hero": {
                "id": "hero",
                "name": "Hero Voice",
                "murf_voice_id": "en-US-maverick",  # Strong male voice
                "style": "confident",
                "speed": 1.1,
                "pitch": 1.0
            },
            "villain": {
                "id": "villain",
                "name": "Villain Voice", 
                "murf_voice_id": "en-US-cooper",  # Deep male voice
                "style": "serious",
                "speed": 0.9,
                "pitch": 0.8
            },
            "narrator": {
                "id": "narrator",
                "name": "Narrator Voice",
                "murf_voice_id": "en-US-natalie",  # Clear female voice
                "style": "conversational",
                "speed": 1.0,
                "pitch": 1.0
            }
        }
        
        self.murf_api_key = MURF_API_KEY
        self.murf_enabled = bool(self.murf_api_key)
        self.murf_api_url = "https://api.murf.ai/v1/speech/generate"
        
        if self.murf_enabled:
            logger.info("✅ Murf AI TTS enabled")
        else:
            logger.warning("⚠️ Murf API key not found - using fallback audio")

    async def get_available_voices(self) -> List[Dict]:
        """Return available voices."""
        voice_list = []
        
        for voice_config in self.voices.values():
            voice_list.append({
                "id": voice_config["id"],
                "name": voice_config["name"],
                "description": f"Character voice for {voice_config['name']}",
                "murf_voice_id": voice_config.get("murf_voice_id", "en-US-davis"),
                "engine": "murf" if self.murf_enabled else "fallback"
            })
        
        return voice_list

    async def generate_speech(
        self,
        text: str,
        voice_id: str,
        emotion: str = "neutral",
        speed: float = 1.0,
        pitch: float = 1.0
    ) -> Optional[str]:
        """Generate speech and return URL to audio file."""
        if not text.strip():
            logger.warning("Empty text provided for speech generation")
            return None
            
        logger.info(f"Generating speech: '{text[:50]}...' with voice '{voice_id}'")
        
        try:
            if self.murf_enabled:
                return await self._generate_with_murf(text, voice_id, emotion, speed, pitch)
            else:
                return await self._generate_fallback_audio(text, voice_id, emotion)
        except Exception as e:
            logger.error(f"Speech generation failed: {e}")
            return await self._generate_fallback_audio(text, voice_id, emotion)

    async def _generate_with_murf(
        self, 
        text: str, 
        voice_id: str, 
        emotion: str, 
        speed: float, 
        pitch: float
    ) -> Optional[str]:
        """Generate speech using Murf AI API with proper response handling."""
        try:
            voice_config = self.voices.get(voice_id, self.voices["narrator"])
            murf_voice_id = voice_config["murf_voice_id"]
            
            # Apply emotion-based modifiers
            final_speed = voice_config["speed"] * speed
            final_pitch = voice_config["pitch"] * pitch
            
            # Clamp values to Murf's acceptable ranges (0.5 to 2.0)
            final_speed = max(0.5, min(2.0, final_speed))
            final_pitch = max(0.5, min(2.0, final_pitch))
            
            logger.info(f"Using Murf voice: {murf_voice_id}, speed: {final_speed}, pitch: {final_pitch}")
            
            # Murf API request format
            payload = {
                "text": text,
                "voiceId": murf_voice_id,
                "format": "MP3",
                "sampleRate": 44100,
                "channelType": "MONO"
            }
            
            # Add speed and pitch if they're different from default
            if final_speed != 1.0:
                payload["speed"] = final_speed
            if final_pitch != 1.0:
                payload["pitch"] = final_pitch
            
            headers = {
                "api-key": self.murf_api_key,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Sending request to Murf API: {self.murf_api_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.murf_api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    logger.info(f"Murf API response status: {response.status}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Murf API error {response.status}: {error_text}")
                        return None
                    
                    try:
                        response_data = await response.json()
                        logger.info(f"Parsed Murf response keys: {list(response_data.keys())}")
                        
                        # Handle the actual Murf API response format based on the logs
                        if "audioFile" in response_data:
                            # This is the direct URL format from Murf
                            murf_url = response_data["audioFile"]
                            logger.info(f"Got direct audio file URL from Murf: {murf_url[:100]}...")
                            
                            # Return the Murf URL directly - it's already publicly accessible
                            return murf_url
                        
                        # Handle base64 encoded audio if present
                        if "encodedAudio" in response_data and response_data["encodedAudio"]:
                            return await self._save_murf_audio_base64(
                                response_data["encodedAudio"], voice_id, emotion
                            )
                        
                        # Handle nested data responses
                        if "data" in response_data:
                            data = response_data["data"]
                            if isinstance(data, dict):
                                if "audioFile" in data:
                                    return data["audioFile"]
                                if "encodedAudio" in data and data["encodedAudio"]:
                                    return await self._save_murf_audio_base64(
                                        data["encodedAudio"], voice_id, emotion
                                    )
                        
                        logger.error(f"Unexpected Murf response format: {response_data}")
                        return None
                        
                    except json.JSONDecodeError:
                        # Response might be binary audio
                        if response.headers.get('content-type', '').startswith('audio/'):
                            audio_data = await response.read()
                            return await self._save_murf_audio_direct(audio_data, voice_id, emotion)
                        
                        error_text = await response.text()
                        logger.error(f"Invalid JSON response from Murf API: {error_text[:200]}")
                        return None
                    
        except asyncio.TimeoutError:
            logger.error("Murf API request timed out")
            return None
        except Exception as e:
            logger.error(f"Murf generation error: {e}")
            return None

    async def _save_murf_audio_base64(self, audio_base64: str, voice_id: str, emotion: str) -> Optional[str]:
        """Save base64 encoded audio data from Murf."""
        try:
            file_id = uuid.uuid4().hex[:12]
            filename = f"murf_{voice_id}_{emotion}_{file_id}.mp3"
            file_path = AUDIO_DIR / filename
            
            # Decode base64 audio data
            audio_data = base64.b64decode(audio_base64)
            
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            if file_path.exists() and file_path.stat().st_size > 0:
                local_url = f"{SERVER_URL}/static/audio/{filename}"
                logger.info(f"Murf audio saved from base64: {local_url} ({file_path.stat().st_size} bytes)")
                return local_url
            
            logger.error(f"Failed to save base64 audio: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error saving base64 Murf audio: {e}")
            return None

    async def _save_murf_audio_direct(self, audio_data: bytes, voice_id: str, emotion: str) -> Optional[str]:
        """Save audio data directly from Murf response."""
        try:
            file_id = uuid.uuid4().hex[:12]
            filename = f"murf_{voice_id}_{emotion}_{file_id}.mp3"
            file_path = AUDIO_DIR / filename
            
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            if file_path.exists() and file_path.stat().st_size > 0:
                local_url = f"{SERVER_URL}/static/audio/{filename}"
                logger.info(f"Murf audio saved directly: {local_url} ({file_path.stat().st_size} bytes)")
                return local_url
            
            logger.error(f"Failed to save direct audio: {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error saving direct Murf audio: {e}")
            return None

    async def _generate_fallback_audio(self, text: str, voice_id: str, emotion: str) -> str:
        """Generate fallback audio when Murf is not available."""
        logger.info("Generating fallback audio...")
        
        # Return a mock URL that the frontend can handle gracefully
        file_id = uuid.uuid4().hex[:8]
        return f"{SERVER_URL}/static/audio/fallback_{voice_id}_{emotion}_{file_id}.mp3"

    async def generate_with_emotion(self, text: str, character_id: str, emotion_data: Dict) -> Optional[str]:
        """Generate speech with emotion-based voice modulation."""
        if character_id not in self.voices:
            character_id = "narrator"
        
        # Extract voice modifiers from emotion data
        voice_modifiers = emotion_data.get("voice_modifiers", {})
        speed_modifier = voice_modifiers.get("speed_modifier", 1.0)
        pitch_modifier = voice_modifiers.get("pitch_modifier", 1.0)
        primary_emotion = emotion_data.get("primary_emotion", "neutral")
        
        logger.info(f"Generating emotional speech - Character: {character_id}, Emotion: {primary_emotion}, Speed: {speed_modifier}x")
        
        # Generate the speech
        return await self.generate_speech(
            text=text,
            voice_id=character_id,
            emotion=primary_emotion,
            speed=speed_modifier,
            pitch=pitch_modifier
        )

    def cleanup_old_files(self, max_files: int = 50):
        """Clean up old audio files to prevent disk space issues."""
        try:
            audio_files = list(AUDIO_DIR.glob("*.mp3")) + list(AUDIO_DIR.glob("*.wav"))
            if len(audio_files) > max_files:
                # Sort by creation time and remove oldest files
                audio_files.sort(key=lambda f: f.stat().st_ctime)
                files_to_remove = audio_files[:-max_files]
                
                for file_path in files_to_remove:
                    file_path.unlink()
                    logger.info(f"Cleaned up old audio file: {file_path}")
                    
        except Exception as e:
            logger.error(f"File cleanup failed: {e}")

    async def test_murf_connection(self) -> bool:
        """Test connection to Murf API."""
        if not self.murf_enabled:
            logger.warning("Murf API key not configured")
            return False
        
        try:
            test_payload = {
                "text": "Test connection",
                "voiceId": "en-US-davis",
                "format": "MP3",
                "sampleRate": 44100,
                "channelType": "MONO"
            }
            
            headers = {
                "api-key": self.murf_api_key,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.murf_api_url,
                    json=test_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        logger.info("✅ Murf API connection test successful")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Murf API connection test failed: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Murf API connection test failed: {e}")
            return False