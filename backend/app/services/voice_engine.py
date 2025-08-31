# app/services/voice_engine.py
import os
import uuid
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
    logger.warning("pyttsx3 not installed - install with: pip install pyttsx3")

# For audio conversion (optional)
try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

# For web-based TTS as fallback
try:
    import requests
except ImportError:
    requests = None

# Settings import with fallback
try:
    from app.core.config import settings
    BASE_DIR = getattr(settings, "BASE_DIR", Path(__file__).resolve().parents[2])
    SERVER_URL = getattr(settings, "SERVER_URL", "http://localhost:8000")
except ImportError:
    BASE_DIR = Path(__file__).resolve().parents[2]
    SERVER_URL = "http://localhost:8000"

AUDIO_DIR = Path(BASE_DIR) / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class VoiceEngine:
    def __init__(self):
        self.voices = {
            "hero": {
                "id": "hero", 
                "name": "Hero Voice", 
                "base_speed": 200, 
                "base_pitch": 1.1,
                "voice_index": 0  # Use first available voice
            },
            "villain": {
                "id": "villain", 
                "name": "Villain Voice", 
                "base_speed": 150, 
                "base_pitch": 0.85,
                "voice_index": 1  # Use second available voice if exists
            },
            "narrator": {
                "id": "narrator", 
                "name": "Narrator Voice", 
                "base_speed": 180, 
                "base_pitch": 1.0,
                "voice_index": 0  # Use first available voice
            }
        }
        
        # Initialize TTS engine
        self.tts_engine = None
        self.available_voices = []
        self._init_tts_engine()

    def _init_tts_engine(self):
        """Initialize the TTS engine and get available voices."""
        if pyttsx3:
            try:
                self.tts_engine = pyttsx3.init()
                self.available_voices = self.tts_engine.getProperty('voices') or []
                logger.info(f"Initialized TTS engine with {len(self.available_voices)} voices")
                
                # Test the engine
                rate = self.tts_engine.getProperty('rate')
                logger.info(f"TTS engine rate: {rate}")
                
            except Exception as e:
                logger.error(f"Failed to initialize TTS engine: {e}")
                self.tts_engine = None
        else:
            logger.warning("pyttsx3 not available - TTS will use fallback")

    async def get_available_voices(self) -> List[Dict]:
        """Return available voices."""
        voice_list = []
        
        # Add our character voices
        for voice_config in self.voices.values():
            voice_list.append({
                "id": voice_config["id"],
                "name": voice_config["name"],
                "description": f"Character voice for {voice_config['name']}",
                "base_speed": voice_config["base_speed"],
                "base_pitch": voice_config["base_pitch"]
            })
        
        # Add system voices if available
        if self.available_voices:
            for idx, voice in enumerate(self.available_voices[:3]):  # Limit to first 3
                voice_list.append({
                    "id": f"system_{idx}",
                    "name": getattr(voice, 'name', f"System Voice {idx}"),
                    "description": getattr(voice, 'id', 'System TTS voice'),
                    "base_speed": 200,
                    "base_pitch": 1.0
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
            return None
            
        # Run TTS generation in thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._generate_audio_sync, text, voice_id, emotion, speed, pitch)
        except Exception as e:
            logger.error(f"Speech generation failed: {e}")
            return None

    def _generate_audio_sync(self, text: str, voice_id: str, emotion: str, speed: float, pitch: float) -> Optional[str]:
        """Synchronous audio generation."""
        try:
            # Generate unique filename
            file_id = uuid.uuid4().hex[:12]
            wav_filename = f"{voice_id}_{emotion}_{file_id}.wav"
            wav_path = AUDIO_DIR / wav_filename
            
            if self.tts_engine and pyttsx3:
                return self._generate_with_pyttsx3(text, voice_id, speed, wav_path, wav_filename)
            else:
                return self._generate_fallback_audio(text, voice_id, wav_filename)
                
        except Exception as e:
            logger.error(f"Audio generation error: {e}")
            return None

    def _generate_with_pyttsx3(self, text: str, voice_id: str, speed: float, wav_path: Path, wav_filename: str) -> str:
        """Generate audio using pyttsx3."""
        try:
            # Configure voice settings
            voice_config = self.voices.get(voice_id, self.voices["narrator"])
            
            # Set speech rate
            target_rate = int(voice_config["base_speed"] * speed)
            self.tts_engine.setProperty('rate', target_rate)
            
            # Set voice if available
            if self.available_voices:
                voice_index = voice_config.get("voice_index", 0)
                if voice_index < len(self.available_voices):
                    self.tts_engine.setProperty('voice', self.available_voices[voice_index].id)
            
            # Generate audio file
            self.tts_engine.save_to_file(text, str(wav_path))
            self.tts_engine.runAndWait()
            
            # Verify file was created
            if wav_path.exists() and wav_path.stat().st_size > 0:
                logger.info(f"Generated audio file: {wav_path} ({wav_path.stat().st_size} bytes)")
                
                # Try to convert to MP3 if possible
                mp3_path = self._try_convert_to_mp3(wav_path)
                if mp3_path:
                    return f"{SERVER_URL}/static/audio/{mp3_path.name}"
                else:
                    return f"{SERVER_URL}/static/audio/{wav_filename}"
            else:
                logger.error(f"Audio file was not created or is empty: {wav_path}")
                return None
                
        except Exception as e:
            logger.error(f"pyttsx3 generation failed: {e}")
            return None

    def _try_convert_to_mp3(self, wav_path: Path) -> Optional[Path]:
        """Try to convert WAV to MP3 for better web compatibility."""
        if not AudioSegment:
            return None
            
        try:
            mp3_path = wav_path.with_suffix('.mp3')
            audio = AudioSegment.from_wav(str(wav_path))
            audio.export(str(mp3_path), format="mp3")
            
            # Remove original WAV file
            if mp3_path.exists() and mp3_path.stat().st_size > 0:
                wav_path.unlink()
                logger.info(f"Converted to MP3: {mp3_path}")
                return mp3_path
                
        except Exception as e:
            logger.warning(f"MP3 conversion failed: {e}")
            
        return None

    def _generate_fallback_audio(self, text: str, voice_id: str, filename: str) -> str:
        """Generate a simple beep sound as fallback when TTS is not available."""
        try:
            # Create a simple sine wave beep as fallback
            import math
            import wave
            import struct
            
            wav_path = AUDIO_DIR / filename
            
            # Generate a simple beep sound
            duration = min(3.0, len(text) * 0.1)  # Duration based on text length
            sample_rate = 44100
            frequency = 440  # A4 note
            
            frames = []
            for i in range(int(duration * sample_rate)):
                # Create a simple sine wave that fades out
                t = i / sample_rate
                fade = max(0, 1 - t / duration)  # Linear fade out
                amplitude = int(32767 * fade * 0.1)  # Low volume
                value = int(amplitude * math.sin(2 * math.pi * frequency * t))
                frames.append(struct.pack('<h', value))
            
            # Write WAV file
            with wave.open(str(wav_path), 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b''.join(frames))
            
            if wav_path.exists():
                logger.info(f"Generated fallback beep audio: {wav_path}")
                return f"{SERVER_URL}/static/audio/{filename}"
                
        except Exception as e:
            logger.error(f"Fallback audio generation failed: {e}")
        
        # Return a mock URL that the frontend can handle gracefully
        return f"{SERVER_URL}/static/audio/mock_generated_{voice_id}.wav"

    async def generate_with_emotion(self, text: str, character_id: str, emotion_data: Dict) -> Optional[str]:
        """Generate speech with emotion-based voice modulation."""
        if character_id not in self.voices:
            character_id = "narrator"
        
        # Extract voice modifiers from emotion data
        voice_modifiers = emotion_data.get("voice_modifiers", {})
        speed_modifier = voice_modifiers.get("speed_modifier", 1.0)
        pitch_modifier = voice_modifiers.get("pitch_modifier", 1.0)
        primary_emotion = emotion_data.get("primary_emotion", "neutral")
        
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
            audio_files = list(AUDIO_DIR.glob("*.wav")) + list(AUDIO_DIR.glob("*.mp3"))
            if len(audio_files) > max_files:
                # Sort by creation time and remove oldest files
                audio_files.sort(key=lambda f: f.stat().st_ctime)
                files_to_remove = audio_files[:-max_files]
                
                for file_path in files_to_remove:
                    file_path.unlink()
                    logger.info(f"Cleaned up old audio file: {file_path}")
                    
        except Exception as e:
            logger.error(f"File cleanup failed: {e}")