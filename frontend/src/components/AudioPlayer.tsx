import React, { useState, useRef, useEffect } from 'react';

interface AudioPlayerProps {
  audioUrl?: string;
  isLoading?: boolean;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ audioUrl, isLoading }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Reset playing state when audioUrl changes
  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setAudioError(null);
  }, [audioUrl]);

  const togglePlay = async () => {
    if (!audioRef.current || !audioUrl) return;

    try {
      setAudioError(null);
      
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        setIsLoadingAudio(true);
        
        // Check if this is a mock URL
        if (audioUrl.includes('mock-audio-service.com') || audioUrl.includes('placeholder_')) {
          // Simulate playing mock audio
          setIsLoadingAudio(false);
          setIsPlaying(true);
          setDuration(10); // Mock 10 second duration
          
          // Simulate progress
          let progress = 0;
          const interval = setInterval(() => {
            progress += 0.5;
            setCurrentTime(progress);
            
            if (progress >= 10) {
              setIsPlaying(false);
              setCurrentTime(0);
              clearInterval(interval);
            }
          }, 500);
          
          // Store interval reference to clear it if component unmounts
          setTimeout(() => {
            if (interval) clearInterval(interval);
          }, 10000);
          
          return;
        }

        // Try to load and play real audio
        await new Promise((resolve, reject) => {
          const audio = audioRef.current!;
          
          const onCanPlay = () => {
            audio.removeEventListener('canplay', onCanPlay);
            audio.removeEventListener('error', onError);
            setIsLoadingAudio(false);
            resolve(void 0);
          };
          
          const onError = () => {
            audio.removeEventListener('canplay', onCanPlay);
            audio.removeEventListener('error', onError);
            setIsLoadingAudio(false);
            reject(new Error('Failed to load audio'));
          };
          
          audio.addEventListener('canplay', onCanPlay);
          audio.addEventListener('error', onError);
          
          // Force reload the audio
          audio.load();
        });

        await audioRef.current.play();
        setIsPlaying(true);
      }
    } catch (error) {
      console.error('Audio playback failed:', error);
      setIsLoadingAudio(false);
      setIsPlaying(false);
      setAudioError('Unable to play audio. The file may not exist or be corrupted.');
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
      setAudioError(null);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const handleAudioError = () => {
    setIsPlaying(false);
    setIsLoadingAudio(false);
    setAudioError('Audio file could not be loaded');
  };

  const formatTime = (time: number) => {
    if (isNaN(time)) return '0:00';
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || duration === 0) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const width = rect.width;
    const percentage = clickX / width;
    const newTime = percentage * duration;
    
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  if (isLoading) {
    return (
      <div className="flex items-center space-x-3 p-4 bg-gray-700 rounded-lg">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <div>
          <div className="text-sm font-medium">Generating audio...</div>
          <div className="text-xs text-gray-400">Processing with AI voice engine</div>
        </div>
      </div>
    );
  }

  if (!audioUrl) {
    return (
      <div className="p-6 bg-gray-700 rounded-lg text-center">
        <div className="text-4xl mb-2">🎤</div>
        <div className="text-gray-400">No audio generated yet</div>
        <div className="text-xs text-gray-500 mt-1">Enter text and click "Generate Speech"</div>
      </div>
    );
  }

  const isMockUrl = audioUrl.includes('mock-audio-service.com') || audioUrl.includes('placeholder_');

  return (
    <div className="p-4 bg-gray-700 rounded-lg">
      <div className="flex items-center space-x-4 mb-3">
        <button
          onClick={togglePlay}
          disabled={isLoadingAudio}
          className="flex items-center justify-center w-12 h-12 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isLoadingAudio ? (
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
          ) : isPlaying ? (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
            </svg>
          ) : (
            <svg className="w-6 h-6 ml-1" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z"/>
            </svg>
          )}
        </button>

        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <div className="text-sm font-medium text-gray-200">
              {isMockUrl ? 'Mock Audio (Demo)' : 'Generated Speech'}
            </div>
            <div className="text-xs text-gray-400">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>
          </div>
          
          {/* Progress Bar - Clickable for seeking */}
          <div 
            className="w-full bg-gray-600 rounded-full h-2 cursor-pointer"
            onClick={handleSeek}
          >
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: duration > 0 ? `${(currentTime / duration) * 100}%` : '0%' }}
            ></div>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {audioError && (
        <div className="mb-3 text-sm text-red-400 bg-red-900/20 p-2 rounded">
          ⚠️ {audioError}
        </div>
      )}

      {/* Audio URL Display */}
      <div className="text-xs text-gray-400 bg-gray-800 p-2 rounded border">
        <div className="flex items-center space-x-2">
          <span className="text-gray-500">URL:</span>
          <span className="font-mono break-all">{audioUrl}</span>
        </div>
      </div>

      {isMockUrl && (
        <div className="mt-2 text-xs text-yellow-400 bg-yellow-900/20 p-2 rounded">
          ℹ️ This is a demo simulation. In production, this would play real AI-generated audio.
        </div>
      )}

      {/* Hidden audio element for real URLs */}
      {!isMockUrl && (
        <audio
          ref={audioRef}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={handleEnded}
          onError={handleAudioError}
          className="hidden"
          preload="metadata"
        >
          <source src={audioUrl} type="audio/mpeg" />
          <source src={audioUrl} type="audio/wav" />
          <source src={audioUrl} type="audio/ogg" />
        </audio>
      )}
    </div>
  );
};