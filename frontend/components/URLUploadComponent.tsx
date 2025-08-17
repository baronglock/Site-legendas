import React, { useState } from 'react'
import { Link2, Globe, Youtube, Video, Loader2 } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import { showToast } from '@/components/CustomToast'

interface URLUploadProps {
  onJobCreated: (jobId: string) => void
}

export default function URLUploadComponent({ onJobCreated }: URLUploadProps) {
  const { user } = useAuth()
  const [url, setUrl] = useState('')
  const [processing, setProcessing] = useState(false)
  const [validating, setValidating] = useState(false)
  const [urlInfo, setUrlInfo] = useState<any>(null)

  const supportedPlatforms = [
    { name: 'YouTube', icon: Youtube, color: 'text-red-500', pattern: /youtube\.com|youtu\.be/ },
    { name: 'Vimeo', icon: Video, color: 'text-blue-500', pattern: /vimeo\.com/ },
    { name: 'Twitter/X', icon: Globe, color: 'text-gray-600', pattern: /twitter\.com|x\.com/ },
    { name: 'TikTok', icon: Video, color: 'text-black', pattern: /tiktok\.com/ }
  ]

  const detectPlatform = (url: string) => {
    for (const platform of supportedPlatforms) {
      if (platform.pattern.test(url)) {
        return platform
      }
    }
    return null
  }

  const validateUrl = async () => {
    if (!url.trim()) {
      showToast.warning('Digite uma URL', 'Cole o link do vídeo que deseja transcrever')
      return
    }

    setValidating(true)
    const platform = detectPlatform(url)
    
    if (!platform) {
      setValidating(false)
      showToast.error('Plataforma não suportada', 'Use YouTube, Vimeo, Twitter ou TikTok')
      return
    }

    // Simular validação (em produção, fazer chamada real para verificar)
    setTimeout(() => {
      setUrlInfo({
        platform: platform.name,
        icon: platform.icon,
        color: platform.color,
        estimatedDuration: '2-5 minutos' // Em produção, tentar pegar duração real
      })
      setValidating(false)
    }, 1000)
  }

  const handleSubmit = async () => {
    if (!url.trim() || !urlInfo) return

    setProcessing(true)
    
    try {
      const response = await apiClient.processUrl({
        url: url.trim(),
        source_language: 'auto',
        target_language: 'pt',
        translate: true
      })

      if (response.data.job_id) {
        showToast.success(
          'URL processada com sucesso!',
          `Processando vídeo do ${urlInfo.platform}`,
          {
            label: 'Ver progresso',
            onClick: () => onJobCreated(response.data.job_id)
          }
        )
        
        // Limpar formulário
        setUrl('')
        setUrlInfo(null)
        
        // Notificar componente pai
        onJobCreated(response.data.job_id)
      }
    } catch (error: any) {
      showToast.error(
        'Erro ao processar URL',
        error.response?.data?.detail || 'Verifique a URL e tente novamente'
      )
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="mb-6">
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Upload por URL
        </h3>
        <p className="text-sm text-gray-600">
          Cole o link de um vídeo do YouTube, Vimeo, Twitter ou TikTok
        </p>
      </div>

      <div className="space-y-4">
        {/* Campo de URL */}
        <div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Link2 className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value)
                setUrlInfo(null)
              }}
              onBlur={validateUrl}
              placeholder="https://www.youtube.com/watch?v=..."
              className="pl-10 pr-4 py-3 w-full border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              disabled={processing}
            />
            {validating && (
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                <Loader2 className="h-5 w-5 text-gray-400 animate-spin" />
              </div>
            )}
          </div>
        </div>

        {/* Info da URL validada */}
        {urlInfo && (
          <div className="bg-gray-50 rounded-lg p-4 flex items-center space-x-3">
            <div className={`p-2 bg-white rounded-lg ${urlInfo.color}`}>
              <urlInfo.icon className="h-6 w-6" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">
                Vídeo do {urlInfo.platform} detectado
              </p>
              <p className="text-xs text-gray-500">
                Duração estimada: {urlInfo.estimatedDuration}
              </p>
            </div>
            <button
              onClick={handleSubmit}
              disabled={processing || !user}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Processando...</span>
                </>
              ) : (
                <>
                  <span>Processar Vídeo</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Plataformas suportadas */}
        <div className="border-t pt-4">
          <p className="text-xs text-gray-500 mb-2">Plataformas suportadas:</p>
          <div className="flex flex-wrap gap-3">
            {supportedPlatforms.map((platform) => (
              <div
                key={platform.name}
                className="flex items-center space-x-2 text-sm text-gray-600"
              >
                <platform.icon className={`h-4 w-4 ${platform.color}`} />
                <span>{platform.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Avisos */}
        {!user && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-sm text-yellow-800">
              Faça login para processar vídeos por URL
            </p>
          </div>
        )}

        <div className="text-xs text-gray-500 space-y-1">
          <p>• Vídeos privados não são suportados</p>
          <p>• Duração máxima: 2 horas (plano free: 30 min)</p>
          <p>• O processamento pode demorar alguns minutos extras</p>
        </div>
      </div>
    </div>
  )
}