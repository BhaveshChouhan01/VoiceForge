import React from 'react';

interface EmotionData {
  primary_emotion: string;
  emotion_scores: { [key: string]: number };
  confidence: number;
  voice_modifiers: {
    speed_modifier: number;
    pitch_modifier: number;
  };
}

interface EmotionVisualizerProps {
  emotionData?: EmotionData;
}

export const EmotionVisualizer: React.FC<EmotionVisualizerProps> = ({ emotionData }) => {
  if (!emotionData) {
    return (
      <div className="p-4 bg-gray-700 rounded-lg text-gray-400">
        Enter text to see emotion analysis
      </div>
    );
  }

  const getEmotionColor = (emotion: string) => {
    const colors: { [key: string]: string } = {
      happy: 'bg-yellow-500',
      sad: 'bg-blue-500',
      angry: 'bg-red-500',
      excited: 'bg-orange-500',
      calm: 'bg-green-500',
      fear: 'bg-purple-500',
      surprise: 'bg-pink-500',
      neutral: 'bg-gray-500'
    };
    return colors[emotion] || 'bg-gray-500';
  };

  return (
    <div className="space-y-4">
      {/* Primary Emotion */}
      <div className="flex items-center space-x-3">
        <div className={`w-4 h-4 rounded-full ${getEmotionColor(emotionData.primary_emotion)}`}></div>
        <span className="font-medium capitalize">{emotionData.primary_emotion}</span>
        <span className="text-sm text-gray-400">
          {(emotionData.confidence * 100).toFixed(1)}% confidence
        </span>
      </div>

      {/* Emotion Scores */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-gray-300">Emotion Breakdown:</h4>
        {Object.entries(emotionData.emotion_scores).map(([emotion, score]) => (
          <div key={emotion} className="flex items-center space-x-2">
            <span className="text-sm capitalize w-20">{emotion}:</span>
            <div className="flex-1 bg-gray-600 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${getEmotionColor(emotion)}`}
                style={{ width: `${score * 100}%` }}
              ></div>
            </div>
            <span className="text-xs text-gray-400 w-12">
              {(score * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>

      {/* Voice Modifiers */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-600 p-3 rounded">
          <div className="text-xs text-gray-300">Speed</div>
          <div className="font-mono text-sm">
            {emotionData.voice_modifiers.speed_modifier.toFixed(2)}x
          </div>
        </div>
        <div className="bg-gray-600 p-3 rounded">
          <div className="text-xs text-gray-300">Pitch</div>
          <div className="font-mono text-sm">
            {emotionData.voice_modifiers.pitch_modifier.toFixed(2)}x
          </div>
        </div>
      </div>
    </div>
  );
};