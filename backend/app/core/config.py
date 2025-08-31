import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Get the project root directory (parent of parent of this config file)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/voiceforge.db"
    
    # Paths
    BASE_DIR: Path = BASE_DIR
    STATIC_DIR: Path = BASE_DIR / "static"
    AUDIO_DIR: Path = BASE_DIR / "static" / "audio"
    
    # Server
    SERVER_URL: str = "http://localhost:8000"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # API Keys - Add your keys here or in .env file
    MURF_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173"
    ]
    
    # Murf API Settings
    MURF_API_URL: str = "https://api.murf.ai/v1/speech/generate"
    MURF_TIMEOUT: int = 30
    MURF_RETRIES: int = 2
    MURF_FALLBACK_ENABLED: bool = True
    
    # Audio Settings
    AUDIO_CLEANUP_ENABLED: bool = True
    AUDIO_MAX_FILES: int = 100
    AUDIO_FORMATS: list = ["mp3", "wav", "ogg"]
    
    class Config:
        env_file = ".env"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.STATIC_DIR.mkdir(parents=True, exist_ok=True)
        self.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        
        # Log configuration warnings
        if not self.MURF_API_KEY:
            logger.warning("MURF_API_KEY not set - voice generation will use fallback mode")
        
        # Validate audio directory permissions
        try:
            test_file = self.AUDIO_DIR / "test_permissions.tmp"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            logger.error(f"Audio directory not writable: {e}")

settings = Settings()

# Print configuration status with better formatting
def print_config_status():
    print("\n" + "="*50)
    print("🔧 VoiceForge Configuration Status")
    print("="*50)
    print(f"📁 Audio Directory: {settings.AUDIO_DIR}")
    print(f"   ├─ Writable: {'✅' if settings.AUDIO_DIR.exists() else '❌'}")
    print(f"   └─ Max Files: {settings.AUDIO_MAX_FILES}")
    
    print(f"\n🌍 Server Configuration:")
    print(f"   ├─ URL: {settings.SERVER_URL}")
    print(f"   ├─ Host: {settings.HOST}:{settings.PORT}")
    print(f"   └─ CORS Origins: {len(settings.ALLOWED_ORIGINS)} configured")
    
    print(f"\n🎤 Audio Services:")
    murf_status = "✅ Configured" if settings.MURF_API_KEY else "⚠️ Not configured (fallback mode)"
    print(f"   ├─ Murf AI TTS: {murf_status}")
    
    print(f"\n🤖 AI Services:")
    gemini_status = "✅ Configured" if settings.GEMINI_API_KEY else "⚠️ Not configured"
    openai_status = "✅ Configured" if settings.OPENAI_API_KEY else "⚠️ Not configured"
    print(f"   ├─ Gemini API: {gemini_status}")
    print(f"   └─ OpenAI API: {openai_status}")
    
    if not settings.MURF_API_KEY:
        print(f"\n💡 To enable Murf AI:")
        print(f"   1. Sign up at https://murf.ai")
        print(f"   2. Get your API key")
        print(f"   3. Set MURF_API_KEY in your .env file")
    
    print("="*50 + "\n")

# Configuration validation
def validate_configuration():
    """Validate the current configuration and return any issues."""
    issues = []
    warnings = []
    
    # Check critical paths
    if not settings.AUDIO_DIR.exists():
        issues.append(f"Audio directory does not exist: {settings.AUDIO_DIR}")
    elif not os.access(settings.AUDIO_DIR, os.W_OK):
        issues.append(f"Audio directory is not writable: {settings.AUDIO_DIR}")
    
    # Check API keys
    if not settings.MURF_API_KEY:
        warnings.append("Murf API key not configured - using fallback mode")
    
    if not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY:
        warnings.append("No AI API keys configured - using mock responses")
    
    # Check server configuration
    if settings.PORT < 1024 and os.geteuid() != 0:  # Unix/Linux check
        warnings.append(f"Port {settings.PORT} may require root privileges")
    
    return issues, warnings

def get_environment_info():
    """Get information about the current environment."""
    return {
        "python_version": os.sys.version,
        "working_directory": os.getcwd(),
        "base_directory": str(settings.BASE_DIR),
        "static_directory": str(settings.STATIC_DIR),
        "audio_directory": str(settings.AUDIO_DIR),
        "environment_variables": {
            "MURF_API_KEY": "SET" if settings.MURF_API_KEY else "NOT SET",
            "GEMINI_API_KEY": "SET" if settings.GEMINI_API_KEY else "NOT SET",
            "OPENAI_API_KEY": "SET" if settings.OPENAI_API_KEY else "NOT SET"
        }
    }