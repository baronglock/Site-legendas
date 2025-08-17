import React, { useState, useEffect, useRef } from 'react'
import { X, Play, Pause, SkipBack, SkipForward, Download, Settings } from 'lucide-react'
import { apiClient } from '@/lib/api'

interface SubtitleSegment {
  id: number
  start: number
  end: number
  text: string
}

interface SubtitlePreviewProps {
  jobId: string
  videoUrl?: string
  onClose: () => void
}

export default function SubtitlePreview({ jobId, videoUrl, onClose }: SubtitlePreviewProps) {
  const [subtitles, setSubtitles] = useState<SubtitleSegment[]>([])
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [activeSubtitle, setActiveSubtitle] = useState<SubtitleSegment | null>(null)
  const [fontSize, setFontSize] = useState('medium')
  const [showSettings, setShowSettings] = useState(false)
  
  const videoRef = useRef<HTMLVideoElement>(null)
  const animationRef = useRef<number>()

  useEffect(() => {
    // Carregar legendas
    fetchSubtitles()
  }, [jobId])

  useEffect(() => {
    // Atualizar legenda ativa baseado no tempo atual
    const active = subtitles.find(
      sub => currentTime >= sub.start && currentTime <= sub.end
    )
    setActiveSubtitle(active || null)
  }, [currentTime, subtitles])

  const fetchSubtitles = async () => {
    try {
      // Buscar arquivo JSON das legendas
      const response = await fetch(`http://localhost:8000/api/v1/download/${jobId}/json`)
      const data = await response.json()
      setSubtitles(data)
    } catch (error) {
      console.error('Erro ao carregar legendas:', error)
    }
  }

  const updateTime = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime)
      if (isPlaying) {
        animationRef.current = requestAnimationFrame(updateTime)
      }
    }
  }

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
        cancelAnimationFrame(animationRef.current!)
      } else {
        videoRef.current.play()
        animationRef.current = requestAnimationFrame(updateTime)
      }
      setIsPlaying(!isPlaying)
    }
  }

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time
      setCurrentTime(time)
    }
  }

  const handleSkip = (seconds: number) => {
    if (videoRef.current) {
      const newTime = Math.max(0, Math.min(duration, currentTime + seconds))
      handleSeek(newTime)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const fontSizes = {
    small: 'text-sm',
    medium: 'text-base',
    large: 'text-lg',
    xlarge: 'text-xl'
  }

  return (
    <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 rounded-lg max-w-5xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <h3 className="text-white font-medium">Preview das Legendas</h3>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800"
            >
              <Settings className="h-5 w-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="p-4 bg-gray-800 border-b border-gray-700">
            <div className="flex items-center space-x-4">
              <label className="text-sm text-gray-300">Tamanho da fonte:</label>
              <div className="flex space-x-2">
                {Object.entries(fontSizes).map(([size, _]) => (
                  <button
                    key={size}
                    onClick={() => setFontSize(size)}
                    className={`px-3 py-1 rounded text-sm ${
                      fontSize === size
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {size.charAt(0).toUpperCase() + size.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 flex">
          {/* Video/Preview Area */}
          <div className="flex-1 bg-black relative">
            {videoUrl ? (
              <video
                ref={videoRef}
                src={videoUrl}
                className="w-full h-full object-contain"
                onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  <div className="w-32 h-32 bg-gray-800 rounded-lg mx-auto mb-4 flex items-center justify-center">
                    <Play className="h-12 w-12 text-gray-600" />
                  </div>
                  <p className="text-gray-400">Sem vídeo disponível</p>
                  <p className="text-sm text-gray-500 mt-2">Visualizando apenas as legendas</p>
                </div>
              </div>
            )}

            {/* Subtitle Overlay */}
            {activeSubtitle && (
              <div className="absolute bottom-8 left-0 right-0 text-center px-4">
                <div className="inline-block bg-black/80 backdrop-blur-sm rounded px-4 py-2">
                  <p className={`text-white ${fontSizes[fontSize]} leading-relaxed drop-shadow-lg`}>
                    {activeSubtitle.text}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Subtitle List */}
          <div className="w-80 bg-gray-800 overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-700">
              <h4 className="text-white font-medium">Lista de Legendas</h4>
              <p className="text-sm text-gray-400 mt-1">{subtitles.length} segmentos</p>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              <div className="p-2 space-y-1">
                {subtitles.map((subtitle) => (
                  <button
                    key={subtitle.id}
                    onClick={() => handleSeek(subtitle.start)}
                    className={`w-full text-left p-3 rounded-lg transition-colors ${
                      activeSubtitle?.id === subtitle.id
                        ? 'bg-purple-600/20 border border-purple-600/50'
                        : 'bg-gray-700/50 hover:bg-gray-700'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <span className="text-xs text-gray-400">
                        {formatTime(subtitle.start)} - {formatTime(subtitle.end)}
                      </span>
                      {activeSubtitle?.id === subtitle.id && (
                        <span className="text-xs text-purple-400">Ativo</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-200 mt-1 line-clamp-2">
                      {subtitle.text}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="p-4 bg-gray-800 border-t border-gray-700">
          <div className="flex items-center space-x-4">
            {/* Play Controls */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleSkip(-10)}
                className="p-2 text-white hover:bg-gray-700 rounded-lg"
                title="Voltar 10s"
              >
                <SkipBack className="h-5 w-5" />
              </button>
              
              <button
                onClick={handlePlayPause}
                className="p-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
              </button>
              
              <button
                onClick={() => handleSkip(10)}
                className="p-2 text-white hover:bg-gray-700 rounded-lg"
                title="Avançar 10s"
              >
                <SkipForward className="h-5 w-5" />
              </button>
            </div>

            {/* Timeline */}
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-400">{formatTime(currentTime)}</span>
                <div className="flex-1 relative">
                  <input
                    type="range"
                    min="0"
                    max={duration || 100}
                    value={currentTime}
                    onChange={(e) => handleSeek(parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                    style={{
                      background: `linear-gradient(to right, #9333ea ${(currentTime / duration) * 100}%, #374151 ${(currentTime / duration) * 100}%)`
                    }}
                  />
                  
                  {/* Subtitle markers */}
                  <div className="absolute inset-0 pointer-events-none">
                    {subtitles.map((sub) => (
                      <div
                        key={sub.id}
                        className="absolute top-0 h-full w-0.5 bg-purple-400/30"
                        style={{ left: `${(sub.start / duration) * 100}%` }}
                      />
                    ))}
                  </div>
                </div>
                <span className="text-sm text-gray-400">{formatTime(duration)}</span>
              </div>
            </div>

            {/* Download Button */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => window.open(`http://localhost:8000/api/v1/download/${jobId}/srt`, '_blank')}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
              >
                <Download className="h-4 w-4" />
                <span>Baixar SRT</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 16px;
          height: 16px;
          background: #9333ea;
          border-radius: 50%;
          cursor: pointer;
        }
        
        .slider::-moz-range-thumb {
          width: 16px;
          height: 16px;
          background: #9333ea;
          border-radius: 50%;
          cursor: pointer;
          border: none;
        }
        
        .line-clamp-2 {
          overflow: hidden;
          display: -webkit-box;
          -webkit-box-orient: vertical;
          -webkit-line-clamp: 2;
        }
      `}</style>
    </div>
  )
}