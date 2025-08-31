from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
import json
import logging

from app.core.config import settings
from app.api.routes import router as api_router
from app.core.websocket_manager import ConnectionManager
from app.services.voice_engine import VoiceEngine
from app.services.character_ai import CharacterAI
from app.services.emotion_analyzer import EmotionAnalyzer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting VoiceForge Backend...")
    
    try:
        # Initialize services
        app.state.voice_engine = VoiceEngine()
        app.state.character_ai = CharacterAI()
        app.state.emotion_analyzer = EmotionAnalyzer()
        app.state.connection_manager = ConnectionManager()
        
        logger.info("VoiceForge Backend Started Successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        raise
    finally:
        # Shutdown
        logger.info("VoiceForge Backend Stopped")

app = FastAPI(
    title="VoiceForge API",
    description="AI-Powered Voice Acting Studio",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (ensure directory exists)
if settings.STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {settings.STATIC_DIR}")

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "VoiceForge API is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "voice_engine": hasattr(app.state, 'voice_engine'),
            "character_ai": hasattr(app.state, 'character_ai'),
            "emotion_analyzer": hasattr(app.state, 'emotion_analyzer'),
            "connection_manager": hasattr(app.state, 'connection_manager')
        }
    }

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    manager = app.state.connection_manager
    await manager.connect(websocket, session_id)
    logger.info(f"WebSocket connected: {session_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                logger.info(f"WebSocket message from {session_id}: {message.get('type', 'unknown')}")
                
                if message["type"] == "voice_request":
                    await handle_voice_request(websocket, message, app.state, session_id)
                elif message["type"] == "character_switch":
                    await handle_character_switch(websocket, message, app.state, session_id)
                else:
                    logger.warning(f"Unknown message type: {message.get('type')}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {session_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error processing message from {session_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to process request"
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
        manager.disconnect(session_id)

async def handle_voice_request(websocket: WebSocket, message: dict, state, session_id: str):
    try:
        text = message.get("text", "").strip()
        character_id = message.get("character_id", "narrator")
        
        if not text:
            await websocket.send_json({
                "type": "error",
                "message": "Text is required"
            })
            return
        
        logger.info(f"Generating voice for {session_id}: '{text}' as {character_id}")
        
        # Analyze emotion
        emotion = await state.emotion_analyzer.analyze(text)
        
        # Generate voice
        audio_url = await state.voice_engine.generate_with_emotion(
            text, character_id, emotion
        )
        
        response = {
            "type": "voice_response",
            "audio_url": audio_url,
            "emotion": emotion,
            "character_id": character_id,
            "text": text
        }
        
        await websocket.send_json(response)
        logger.info(f"Voice generation complete for {session_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_voice_request for {session_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Voice generation failed: {str(e)}"
        })

async def handle_character_switch(websocket: WebSocket, message: dict, state, session_id: str):
    try:
        character_id = message.get("character_id", "narrator")
        character = await state.character_ai.get_character_profile(character_id)
        
        await websocket.send_json({
            "type": "character_switched",
            "character": character
        })
        
        logger.info(f"Character switched for {session_id}: {character_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_character_switch for {session_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Character switch failed: {str(e)}"
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=True,
        log_level="info"
    )