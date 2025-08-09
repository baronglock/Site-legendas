import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Link, FileVideo, AlertCircle, Settings } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function UploadForm() {
  const { user } = useAuth()
  const [mode, setMode] = useState<'file' | 'url'>('file')
  const [url, setUrl] = useState('')
  const [processing, setProcessing] = useState(false)
  const [advancedOptions, setAdvancedOptions] = useState(false)
  
  // Opções avançadas para economia de créditos
  const [options, setOptions] = useState({
    transcribeOnly: false,
    translateOnly: false,
    sourceLanguage: 'auto',
    targetLanguage: 'pt',
    subtitleStyle: 'standard' // standard, social, cinema
  })

  const estimateCredits = () => {
    if (options.transcribeOnly) return 0.5
    if (options.translateOnly) return 0.3
    return 1.0 // Processo completo
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    // Validações
    const maxSize = user?.plan === 'free' ? 30 : 300 // MB
    if (file.size > maxSize * 1024 * 1024) {
      toast.error(`Arquivo muito grande. Máximo: ${maxSize}MB`)
      return
    }

    // Estimativa de duração baseada no tamanho
    const estimatedMinutes = Math.ceil(file.size / (1024 * 1024 * 2)) // ~2MB por minuto
    const creditsNeeded = estimatedMinutes * estimateCredits()

    if (creditsNeeded > user?.minutesRemaining) {
      toast.error(
        <div>
          <p>Créditos insuficientes!</p>
          <p className="text-sm">Necessário: {creditsNeeded}min | Disponível: {user?.minutesRemaining}min</p>
        </div>
      )
      return
    }

    setProcessing(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('options', JSON.stringify(options))

    try {
      const response = await api.uploadFile(formData)
      toast.success('Upload iniciado! Acompanhe o progresso abaixo.')
      // Redirecionar ou atualizar lista de jobs
    } catch (error) {
      toast.error('Erro no upload. Tente novamente.')
    } finally {
      setProcessing(false)
    }
  }, [user, options])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv'],
      'audio/*': ['.mp3', '.wav', '.m4a']
    },
    maxFiles: 1,
    disabled: processing
  })

  const handleUrlSubmit = async () => {
    if (!url) {
      toast.error('Digite uma URL válida')
      return
    }

    setProcessing(true)
    try {
      const response = await api.processUrl({ url, options })
      toast.success('Processamento iniciado!')
    } catch (error) {
      toast.error('Erro ao processar URL')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Tabs de modo */}
      <div className="flex space-x-4 mb-6">
        <button
          onClick={() => setMode('file')}
          className={`flex items-center px-4 py-2 rounded-lg font-medium ${
            mode === 'file'
              ? 'bg-purple-100 text-purple-700'
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          <FileVideo className="h-4 w-4 mr-2" />
          Upload de Arquivo
        </button>
        <button
          onClick={() => setMode('url')}
          className={`flex items-center px-4 py-2 rounded-lg font-medium ${
            mode === 'url'
              ? 'bg-purple-100 text-purple-700'
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          <Link className="h-4 w-4 mr-2" />
          URL do Vídeo
        </button>
      </div>

      {/* Upload de arquivo */}
      {mode === 'file' && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-purple-500 bg-purple-50'
              : 'border-gray-300 hover:border-purple-400'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p className="text-lg font-medium text-gray-700 mb-2">
            {isDragActive
              ? 'Solte o arquivo aqui...'
              : 'Arraste um arquivo ou clique para selecionar'}
          </p>
          <p className="text-sm text-gray-500">
            MP4, MOV, AVI, MKV, MP3, WAV • Máx {user?.plan === 'free' ? '30' : '300'}MB
          </p>
        </div>
      )}

      {/* URL */}
      {mode === 'url' && (
        <div>
          <div className="flex space-x-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://youtube.com/watch?v=..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              disabled={processing}
            />
            <button
              onClick={handleUrlSubmit}
              disabled={processing || !url}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {processing ? 'Processando...' : 'Processar'}
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Suportamos YouTube, Vimeo, e outras plataformas
          </p>
        </div>
      )}

      {/* Opções avançadas */}
      <div className="mt-6">
        <button
          onClick={() => setAdvancedOptions(!advancedOptions)}
          className="flex items-center text-sm text-purple-600 hover:text-purple-700"
        >
          <Settings className="h-4 w-4 mr-1" />
          Opções Avançadas (Economize Créditos)
        </button>
        
        {advancedOptions && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
            {/* Escolha de processo */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">
                Escolha o que processar:
              </p>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="process"
                    checked={!options.transcribeOnly && !options.translateOnly}
                    onChange={() => setOptions({...options, transcribeOnly: false, translateOnly: false})}
                    className="mr-2"
                  />
                  <span className="text-sm">
                    Processo completo (1x crédito)
                  </span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="process"
                    checked={options.transcribeOnly}
                    onChange={() => setOptions({...options, transcribeOnly: true, translateOnly: false})}
                    className="mr-2"
                  />
                  <span className="text-sm">
                    Apenas transcrição (0.5x crédito) 
                    <span className="text-green-600 ml-1">Economize 50%</span>
                  </span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="process"
                    checked={options.translateOnly}
                    onChange={() => setOptions({...options, transcribeOnly: false, translateOnly: true})}
                    className="mr-2"
                    disabled={user?.plan === 'free'}
                  />
                  <span className="text-sm">
                    Apenas tradução de SRT existente (0.3x crédito)
                    {user?.plan === 'free' && <span className="text-gray-500 ml-1">(Plano pago)</span>}
                  </span>
                </label>
              </div>
            </div>

            {/* Estilo de legenda */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Estilo de Legenda:
              </label>
              <select
                value={options.subtitleStyle}
                onChange={(e) => setOptions({...options, subtitleStyle: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="standard">Padrão (TV/Cinema)</option>
                <option value="social">Redes Sociais (Curto e Impactante)</option>
                <option value="formal">Formal (Corporativo)</option>
                <option value="informal">Informal (YouTube/TikTok)</option>
              </select>
            </div>

            {/* Estimativa de créditos */}
            <div className="bg-blue-50 border border-blue-200 rounded p-3">
              <p className="text-sm text-blue-800">
                <AlertCircle className="inline h-4 w-4 mr-1" />
                Consumo estimado: <strong>{estimateCredits()}x crédito por minuto</strong>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}