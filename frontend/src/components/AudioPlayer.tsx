import React, { useState, useRef, useEffect, useCallback } from 'react';

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
  const [audioTested, setAudioTested] = useState(false);
  const [volume, setVolume] = useState(1.0);
  const audioRef = useRef<HTMLAudioElement>(null);
  const playPromiseRef = useRef<Promise<void> | null>(null);
  const simulationIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Reset states when audioUrl changes
  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setAudioError(null);
    setAudioTested(false);
    setIsLoadingAudio(false);
    
    // Clear simulation interval
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }
    
    // Cancel any pending play promise
    playPromiseRef.current = null;
    
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
  }, [audioUrl]);

  // Test audio URL accessibility when it changes
  useEffect(() => {
    if (audioUrl && !audioTested && !isPlaceholderUrl(audioUrl)) {
      testAudioUrl(audioUrl);
    }
  }, [audioUrl, audioTested]);

  const isPlaceholderUrl = (url: string) => {
    return url.includes('placeholder_') || 
           url.includes('mock-audio') || 
           url.includes('error_placeholder') ||
           url.includes('fallback_');
  };

  const isMurfUrl = (url: string) => {
    return url.includes('murf.ai') || url.includes('amazonaws.com');
  };

  const testAudioUrl = async (url: string) => {
    try {
      // For Murf URLs, we'll skip the HEAD request test since they have CORS restrictions
      if (isMurfUrl(url)) {
        setAudioTested(true);
        return;
      }
      
      const response = await fetch(url, { method: 'HEAD' });
      if (!response.ok) {
        setAudioError(`Audio file not accessible (${response.status})`);
      }
      setAudioTested(true);
    } catch (error) {
      console.warn('Audio URL test failed:', error);
      // Don't show error for CORS issues, just mark as tested
      setAudioTested(true);
    }
  };

  const playPlaceholderAudio = useCallback(async () => {
    if (!audioUrl) return;

    setIsLoadingAudio(false);
    setIsPlaying(true);
    setDuration(5); // Mock 5 second duration
    
    // Clear any existing interval
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
    }
    
    // Simulate audio playback
    let progress = 0;
    simulationIntervalRef.current = setInterval(() => {
      progress += 0.1;
      setCurrentTime(progress);
      
      if (progress >= 5) {
        setIsPlaying(false);
        setCurrentTime(0);
        if (simulationIntervalRef.current) {
          clearInterval(simulationIntervalRef.current);
          simulationIntervalRef.current = null;
        }
      }
    }, 100);
  }, [audioUrl]);

  const stopCurrentPlayback = useCallback(async () => {
    // Clear simulation interval
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }

    if (audioRef.current) {
      // Wait for any pending play promise to resolve
      if (playPromiseRef.current) {
        try {
          await playPromiseRef.current;
        } catch (e) {
          // Ignore - play was probably cancelled
        }
        playPromiseRef.current = null;
      }
      
      if (!audioRef.current.paused) {
        audioRef.current.pause();
      }
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setCurrentTime(0);
  }, []);

  const togglePlay = async () => {
    if (!audioUrl) {
      setAudioError('No audio URL available');
      return;
    }

    try {
      setAudioError(null);
      
      // Handle placeholder URLs
      if (isPlaceholderUrl(audioUrl)) {
        if (isPlaying) {
          await stopCurrentPlayback();
        } else {
          await playPlaceholderAudio();
        }
        return;
      }

      // Handle real audio
      if (!audioRef.current) return;

      if (isPlaying) {
        await stopCurrentPlayback();
        return;
      }

      setIsLoadingAudio(true);
      
      // Ensure audio source is set correctly
      if (audioRef.current.src !== audioUrl) {
        audioRef.current.src = audioUrl;
        // For Murf URLs, set crossOrigin to anonymous to handle CORS
        if (isMurfUrl(audioUrl)) {
          audioRef.current.crossOrigin = 'anonymous';
        }
      }
      
      // Wait for audio to be ready with a timeout
      const loadTimeout = new Promise<void>((_, reject) => {
        setTimeout(() => reject(new Error('Audio load timeout')), 10000);
      });
      
      const loadAudio = new Promise<void>((resolve, reject) => {
        const audio = audioRef.current!;
        
        if (audio.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
          resolve();
          return;
        }
        
        const onCanPlay = () => {
          audio.removeEventListener('canplaythrough', onCanPlay);
          audio.removeEventListener('loadeddata', onCanPlay);
          audio.removeEventListener('error', onError);
          resolve();
        };
        
        const onError = (e: Event) => {
          audio.removeEventListener('canplaythrough', onCanPlay);
          audio.removeEventListener('loadeddata', onCanPlay);
          audio.removeEventListener('error', onError);
          const error = audio.error;
          if (error) {
            reject(new Error(`Audio load error: ${error.message || 'Unknown error'}`));
          } else {
            reject(new Error('Audio failed to load'));
          }
        };
        
        audio.addEventListener('canplaythrough', onCanPlay);
        audio.addEventListener('loadeddata', onCanPlay);
        audio.addEventListener('error', onError);
        
        // Force load
        if (audio.networkState === HTMLMediaElement.NETWORK_NO_SOURCE) {
          audio.load();
        }
      });

      await Promise.race([loadAudio, loadTimeout]);

      // Set volume
      audioRef.current.volume = volume;
      
      // Attempt to play - store promise to handle interruption
      playPromiseRef.current = audioRef.current.play();
      await playPromiseRef.current;
      
      setIsPlaying(true);
      setIsLoadingAudio(false);
      playPromiseRef.current = null;
      
    } catch (error) {
      console.error('Audio playback failed:', error);
      setIsLoadingAudio(false);
      setIsPlaying(false);
      playPromiseRef.current = null;
      
      // Provide specific error messages
      if (error instanceof Error) {
        const errorMessage = error.message.toLowerCase();
        if (errorMessage.includes('interrupted') || errorMessage.includes('aborted')) {
          setAudioError('Playback was interrupted. Please try again.');
        } else if (errorMessage.includes('cors') || errorMessage.includes('cross-origin')) {
          setAudioError('CORS error - audio may still be accessible via direct link');
        } else if (errorMessage.includes('timeout')) {
          setAudioError('Audio loading timed out - the file may be large or server slow');
        } else if (error.name === 'NotSupportedError') {
          setAudioError('Audio format not supported by your browser');
        } else if (error.name === 'NotAllowedError') {
          setAudioError('Audio playback blocked. Click to enable audio');
        } else if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
          setAudioError('Network error: Unable to load audio file');
        } else {
          setAudioError(`Playback failed: ${error.message}`);
        }
      } else {
        setAudioError('Unable to play audio. The file may be temporarily unavailable.');
      }
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current && isPlaying) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration || 0);
      setAudioError(null);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
    playPromiseRef.current = null;
    
    // Clear simulation interval
    if (simulationIntervalRef.current) {
      clearInterval(simulationIntervalRef.current);
      simulationIntervalRef.current = null;
    }
  };

  const handleAudioError = (e: React.SyntheticEvent<HTMLAudioElement, Event>) => {
    const audio = e.currentTarget;
    setIsPlaying(false);
    setIsLoadingAudio(false);
    playPromiseRef.current = null;
    
    // Get more specific error information
    if (audio.error) {
      switch (audio.error.code) {
        case MediaError.MEDIA_ERR_ABORTED:
          setAudioError('Audio loading was aborted');
          break;
        case MediaError.MEDIA_ERR_NETWORK:
          setAudioError('Network error while loading audio - check your connection');
          break;
        case MediaError.MEDIA_ERR_DECODE:
          setAudioError('Audio file is corrupted or invalid format');
          break;
        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
          setAudioError('Audio format not supported');
          break;
        default:
          setAudioError('Audio error occurred - file may be temporarily unavailable');
      }
    } else {
      setAudioError('Audio file could not be loaded');
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || duration === 0 || isPlaceholderUrl(audioUrl || '')) return;
    
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const width = rect.width;
    const percentage = clickX / width;
    const newTime = percentage * duration;
    
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  const formatTime = (time: number) => {
    if (isNaN(time) || !isFinite(time)) return '0:00';
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const openAudioInNewTab = () => {
    if (audioUrl && !isPlaceholderUrl(audioUrl)) {
      window.open(audioUrl, '_blank');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center space-x-3 p-4 bg-gray-700 rounded-lg">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <div>
          <div className="text-sm font-medium">Generating audio with Murf AI...</div>
          <div className="text-xs text-gray-400">Processing with voice engine</div>
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

  const isPlaceholder = isPlaceholderUrl(audioUrl);

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
              {isPlaceholder ? 'Fallback Audio' : 'Murf AI Speech'}
            </div>
            <div className="text-xs text-gray-400">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>
          </div>
          
          {/* Progress Bar */}
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

        {/* Volume Control */}
        <div className="flex items-center space-x-2">
          <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
          </svg>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={volume}
            onChange={handleVolumeChange}
            className="w-16 h-1 bg-gray-600 rounded-full appearance-none slider"
          />
        </div>
      </div>

      {/* Error Message */}
      {audioError && (
        <div className="mb-3 text-sm text-red-400 bg-red-900/20 p-2 rounded flex items-start space-x-2">
          <span>⚠️</span>
          <div className="flex-1">
            <div>{audioError}</div>
            <div className="text-xs text-gray-400 mt-1">
              {isMurfUrl(audioUrl) ? (
                <button 
                  onClick={openAudioInNewTab}
                  className="text-blue-400 hover:text-blue-300 underline"
                >
                  Try opening audio file directly
                </button>
              ) : (
                "Try refreshing the page or generating new audio"
              )}
            </div>
          </div>
        </div>
      )}

      {/* Audio URL Display */}
      <div className="text-xs text-gray-400 bg-gray-800 p-2 rounded border">
        <div className="flex items-center space-x-2">
          <span className="text-gray-500">URL:</span>
          <span className="font-mono break-all flex-1">{audioUrl}</span>
          {!isPlaceholder && (
            <button
              onClick={openAudioInNewTab}
              className="text-blue-400 hover:text-blue-300 text-xs underline whitespace-nowrap"
              title="Open audio file in new tab"
            >
              Open Direct
            </button>
          )}
          {audioTested && !audioError && (
            <span className="text-green-400">✓</span>
          )}
        </div>
      </div>

      {/* Status Messages */}
      {isPlaceholder && (
        <div className="mt-2 text-xs text-yellow-400 bg-yellow-900/20 p-2 rounded">
          ℹ️ This is fallback audio. Murf AI may not be available or configured.
        </div>
      )}

      {isMurfUrl(audioUrl) && !audioError && (
        <div className="mt-2 text-xs text-green-400 bg-green-900/20 p-2 rounded">
          🎵 Using Murf AI generated audio. If playback fails, try the "Open Direct" link.
        </div>
      )}

      {/* Hidden audio element for real URLs */}
      {!isPlaceholder && (
        <audio
          ref={audioRef}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={handleEnded}
          onError={handleAudioError}
          className="hidden"
          preload="metadata"
          crossOrigin={isMurfUrl(audioUrl) ? "anonymous" : undefined}
        >
          <source src={audioUrl} type="audio/mpeg" />
          <source src={audioUrl} type="audio/wav" />
          <source src={audioUrl} type="audio/ogg" />
          Your browser does not support audio playback.
        </audio>
      )}
    </div>
  );
};