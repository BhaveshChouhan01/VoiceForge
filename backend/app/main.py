from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import uuid
from app.core.config import settings
from app.api.routes import router as api_router
from app.core.websocket_manager import ConnectionManager
from app.services.voice_engine import VoiceEngine
from app.services.character_ai import CharacterAI
from app.services.emotion_analyzer import EmotionAnalyzer
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.voice_engine = VoiceEngine()
    app.state.character_ai = CharacterAI()
    app.state.emotion_analyzer = EmotionAnalyzer()
    app.state.connection_manager = ConnectionManager()
    print("✅ VoiceForge Backend Started")
    yield
    # Shutdown
    print("🛑 VoiceForge Backend Stopped")

app = FastAPI(
    title="VoiceForge API",
    description="AI-Powered Voice Acting Studio",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "VoiceForge API is running!", "version": "1.0.0"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    manager = app.state.connection_manager
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "voice_request":
                await handle_voice_request(websocket, message, app.state)
            elif message["type"] == "character_switch":
                await handle_character_switch(websocket, message, app.state)
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)

async def handle_voice_request(websocket: WebSocket, message: dict, state):
    text = message.get("text", "")
    character_id = message.get("character_id", "narrator")
    
    # Analyze emotion
    emotion = await state.emotion_analyzer.analyze(text)
    
    # Generate voice
    audio_url = await state.voice_engine.generate_with_emotion(
        text, character_id, emotion
    )
    
    await websocket.send_json({
        "type": "voice_response",
        "audio_url": audio_url,
        "emotion": emotion,
        "character_id": character_id,
        "text": text
    })

async def handle_character_switch(websocket: WebSocket, message: dict, state):
    character_id = message.get("character_id", "narrator")
    character = await state.character_ai.get_character_profile(character_id)
    
    await websocket.send_json({
        "type": "character_switched",
        "character": character
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)