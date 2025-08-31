import React, { useState, useEffect } from 'react';
import { AudioPlayer } from './AudioPlayer';
import { EmotionVisualizer } from './EmotionVisualizer';

interface Character {
  id: string;
  name: string;
  description: string;
}

interface EmotionData {
  primary_emotion: string;
  confidence: number;
  emotion_scores: { [key: string]: number };
  voice_modifiers: {
    speed_modifier: number;
    pitch_modifier: number;
  };
  sentiment_scores: {
    compound: number;
    pos: number;
    neu: number;
    neg: number;
  };
}

interface VoiceResult {
  audio_url: string;
  emotion: EmotionData;
  character_id: string;
  text: string;
  type: string;
}

export const VoiceStudio: React.FC = () => {
  const [text, setText] = useState('');
  const [selectedCharacter, setSelectedCharacter] = useState('narrator');
  const [characters, setCharacters] = useState<Character[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [lastResult, setLastResult] = useState<VoiceResult | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');

  // WebSocket connection
  useEffect(() => {
    const sessionId = Math.random().toString(36).substring(7);
    const websocket = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
    
    websocket.onopen = () => {
      console.log('Connected to WebSocket');
      setWs(websocket);
      setConnectionStatus('connected');
    };
    
    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        
        if (data.type === 'voice_response') {
          setLastResult(data);
          setIsGenerating(false);
        } else if (data.type === 'character_switched') {
          console.log('Character switched to:', data.character);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        setIsGenerating(false);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('disconnected');
      setIsGenerating(false);
    };

    websocket.onclose = () => {
      console.log('WebSocket connection closed');
      setConnectionStatus('disconnected');
      setIsGenerating(false);
    };
    
    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, []);

  // Load characters
  useEffect(() => {
    const loadCharacters = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/characters');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setCharacters(data.characters || []);
      } catch (err) {
        console.error('Error loading characters:', err);
        // Fallback characters if API fails
        setCharacters([
          { id: 'hero', name: 'Hero', description: 'Brave protagonist' },
          { id: 'villain', name: 'Villain', description: 'Cunning antagonist' },
          { id: 'narrator', name: 'Narrator', description: 'Wise storyteller' }
        ]);
      }
    };

    loadCharacters();
  }, []);

  const generateSpeech = async () => {
    if (!text.trim()) {
      alert('Please enter some text first!');
      return;
    }
    
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      alert('WebSocket connection is not available. Please refresh the page.');
      return;
    }
    
    setIsGenerating(true);
    
    try {
      ws.send(JSON.stringify({
        type: 'voice_request',
        text: text.trim(),
        character_id: selectedCharacter
      }));
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      setIsGenerating(false);
      alert('Failed to send request. Please try again.');
    }
  };

  const generateDialogue = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/generate-dialogue', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          character_id: selectedCharacter,
          situation: 'general conversation',
          emotion: 'neutral'
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setText(data.dialogue || 'No dialogue generated');
    } catch (err) {
      console.error('Error generating dialogue:', err);
      alert('Failed to generate dialogue. Please try again.');
    }
  };

  const handleCharacterChange = (characterId: string) => {
    setSelectedCharacter(characterId);
    
    // Notify WebSocket of character change
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'character_switch',
        character_id: characterId
      }));
    }
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'bg-green-500';
      case 'connecting': return 'bg-yellow-500';
      case 'disconnected': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return 'Connected to server';
      case 'connecting': return 'Connecting to server...';
      case 'disconnected': return 'Disconnected from server';
      default: return 'Unknown connection status';
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Character Selection */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">🎭 Select Character</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {characters.map(character => (
            <button
              key={character.id}
              onClick={() => handleCharacterChange(character.id)}
              className={`p-4 rounded-lg border-2 transition-all ${
                selectedCharacter === character.id
                  ? 'border-blue-500 bg-blue-900'
                  : 'border-gray-600 bg-gray-700 hover:bg-gray-600'
              }`}
            >
              <h3 className="font-bold">{character.name}</h3>
              <p className="text-sm text-gray-300">{character.description}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Input */}
        <div className="space-y-6">
          {/* Text Input */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">📝 Script Input</h2>
            <div className="space-y-4">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Enter your script here or generate dialogue..."
                className="w-full h-32 p-4 bg-gray-700 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none resize-none"
                disabled={isGenerating}
              />
              <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-4">
                <button
                  onClick={generateSpeech}
                  disabled={isGenerating || !text.trim() || connectionStatus !== 'connected'}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
                >
                  {isGenerating ? '⏳ Generating...' : '🎤 Generate Speech'}
                </button>
                <button
                  onClick={generateDialogue}
                  disabled={isGenerating}
                  className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
                >
                  ✨ Generate Dialogue
                </button>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h3 className="text-lg font-bold mb-4">🚀 Quick Actions</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={() => setText("Hello! Welcome to VoiceForge!")}
                disabled={isGenerating}
                className="p-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm transition-colors text-left"
              >
                Welcome Message
              </button>
              <button
                onClick={() => setText("This is absolutely incredible!")}
                disabled={isGenerating}
                className="p-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm transition-colors text-left"
              >
                Excited Speech
              </button>
              <button
                onClick={() => setText("I'm not sure about this...")}
                disabled={isGenerating}
                className="p-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm transition-colors text-left"
              >
                Uncertain Tone
              </button>
              <button
                onClick={() => setText("Once upon a time, in a land far away...")}
                disabled={isGenerating}
                className="p-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm transition-colors text-left"
              >
                Storytelling
              </button>
            </div>
          </div>
        </div>

        {/* Right Column - Results */}
        <div className="space-y-6">
          {/* Audio Player */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">🔊 Audio Output</h2>
            <AudioPlayer 
              audioUrl={lastResult?.audio_url} 
              isLoading={isGenerating} 
            />
          </div>

          {/* Emotion Analysis */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">🎭 Emotion Analysis</h2>
            <EmotionVisualizer emotionData={lastResult?.emotion} />
          </div>

          {/* Connection Status */}
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="font-medium">Server Connection</span>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${getConnectionStatusColor()}`}></div>
                <span className="text-sm">{getConnectionStatusText()}</span>
              </div>
            </div>
            {connectionStatus === 'disconnected' && (
              <div className="mt-2 text-sm text-yellow-400">
                Try refreshing the page to reconnect
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Debug Info (Optional) */}
      {lastResult && (
        <details className="bg-gray-800 rounded-lg p-4">
          <summary className="cursor-pointer font-medium">🔍 Debug Information</summary>
          <pre className="mt-4 p-4 bg-gray-900 rounded text-xs overflow-auto">
            {JSON.stringify(lastResult, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};