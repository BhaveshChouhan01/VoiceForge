import React from 'react';
import { VoiceStudio } from './components/VoiceStudio';
import './App.css';

function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 p-6">
        <h1 className="text-3xl font-bold text-center">
          🎭 VoiceForge - AI Voice Acting Studio
        </h1>
      </header>
      <main className="container mx-auto p-6">
        <VoiceStudio />
      </main>
    </div>
  );
}

export default App;