import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, AlertCircle, Settings, Globe } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { apiClient as api } from '@/lib/api'
import toast from 'react-hot-toast'

// Interface para as opções de upload
interface UploadOptions {
  sourceLanguage: string
  targetLanguage: string
  translate: boolean
}

export default function UploadForm() {
  const { user } = useAuth()
  const [processing, setProcessing] = useState(false)
  const [showOptions, setShowOptions] = useState(false)
  const [options, setOptions] = useState<UploadOptions>({
    sourceLanguage: 'auto',
    targetLanguage: 'pt',
    translate: true
  })

  // Função para estimar créditos necessários
  const estimateCredits = () => {
    // 1 minuto por arquivo base + 1 minuto se traduzir
    return options.translate ? 2 : 1
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    console.log('🎯 onDrop chamado!', acceptedFiles)
    
    const file = acceptedFiles[0]
    if (!file) {
        console.log('❌ Nenhum arquivo')
        return
    }

    console.log('📁 Arquivo:', file.name, file.size)
    
    // Validações
    const maxSize = user?.plan === 'free' ? 30 : 300 // MB
    console.log('📏 Tamanho máximo permitido:', maxSize, 'MB')
    
    if (file.size > maxSize * 1024 * 1024) {
        console.log('❌ Arquivo muito grande')
        toast.error(`Arquivo muito grande. Máximo: ${maxSize}MB`)
        return
    }

    // Estimativa de duração baseada no tamanho
    const estimatedMinutes = Math.ceil(file.size / (1024 * 1024 * 2))
    const creditsNeeded = estimatedMinutes * estimateCredits()
    
    console.log('⏱️ Minutos estimados:', estimatedMinutes)
    console.log('💳 Créditos necessários:', creditsNeeded)
    console.log('👤 User:', user)
    
    if (!user || creditsNeeded > (user?.minutesRemaining || 0)) {
        console.log('❌ Créditos insuficientes')
        toast.error(
            <div>
                <p>Créditos insuficientes!</p>
                <p className="text-sm">Necessário: {creditsNeeded}min | Disponível: {user?.minutesRemaining || 0}min</p>
            </div>
        )
        return
    }

    console.log('✅ Validações OK, iniciando upload...')
    setProcessing(true)
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_language', options.sourceLanguage)
    formData.append('target_language', options.targetLanguage)
    formData.append('translate', String(options.translate))

    try {
        console.log('📤 Chamando api.uploadFile...')
        const response = await api.uploadFile(formData)
        console.log('✅ Resposta do upload:', response)
        
        if (response.data.job_id) {
            console.log('📋 Job ID:', response.data.job_id)
            toast.success(
                <div>
                    <p>Upload iniciado com sucesso!</p>
                    <p className="text-sm">Job ID: {response.data.job_id}</p>
                    <p className="text-sm mt-1">Vá para aba "Processados" para acompanhar</p>
                </div>
            )
        }
    } catch (error: any) {
        console.error('❌ Erro no upload:', error)
        console.error('Detalhes:', error.response?.data)
        toast.error('Erro no upload. Tente novamente.')
    } finally {
        setProcessing(false)
    }
  }, [user, options])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
      'audio/*': ['.mp3', '.wav', '.m4a', '.aac', '.ogg']
    },
    maxFiles: 1,
    disabled: processing || !user
  })

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Área de Upload */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive ? 'border-purple-500 bg-purple-50' : 'border-gray-300 hover:border-gray-400'}
          ${processing ? 'opacity-50 cursor-not-allowed' : ''}
          ${!user ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        
        {processing ? (
          <>
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Enviando arquivo...</p>
          </>
        ) : isDragActive ? (
          <p className="text-purple-600 font-medium">Solte o arquivo aqui...</p>
        ) : (
          <>
            <p className="text-gray-600 mb-2">
              Arraste um arquivo ou clique para selecionar
            </p>
            <p className="text-sm text-gray-500">
              Vídeo: MP4, MOV, AVI, MKV, WEBM
            </p>
            <p className="text-sm text-gray-500">
              Áudio: MP3, WAV, M4A, AAC, OGG
            </p>
            <p className="text-xs text-gray-400 mt-2">
              Máximo: {user?.plan === 'free' ? '30MB' : '300MB'}
            </p>
          </>
        )}
      </div>

      {/* Opções Avançadas */}
      <div className="mt-6">
        <button
          onClick={() => setShowOptions(!showOptions)}
          className="flex items-center text-sm text-gray-600 hover:text-gray-800"
        >
          <Settings className="w-4 h-4 mr-1" />
          Opções Avançadas
        </button>
        
        {showOptions && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Idioma de Origem
              </label>
              <select
                value={options.sourceLanguage}
                onChange={(e) => setOptions({...options, sourceLanguage: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="auto">Auto-detectar</option>
                <option value="pt">Português</option>
                <option value="en">Inglês</option>
                <option value="es">Espanhol</option>
                <option value="fr">Francês</option>
                <option value="de">Alemão</option>
                <option value="it">Italiano</option>
                <option value="ja">Japonês</option>
                <option value="ko">Coreano</option>
                <option value="zh">Chinês</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <input
                  type="checkbox"
                  checked={options.translate}
                  onChange={(e) => setOptions({...options, translate: e.target.checked})}
                  className="mr-2"
                />
                Traduzir legendas
              </label>
              {options.translate && (
                <select
                  value={options.targetLanguage}
                  onChange={(e) => setOptions({...options, targetLanguage: e.target.value})}
                  className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="pt">Português</option>
                  <option value="en">Inglês</option>
                  <option value="es">Espanhol</option>
                  <option value="fr">Francês</option>
                  <option value="de">Alemão</option>
                  <option value="it">Italiano</option>
                </select>
              )}
            </div>

            <div className="text-xs text-gray-500">
              <Globe className="w-3 h-3 inline mr-1" />
              Tradução adiciona {estimateCredits() - 1} minuto(s) ao custo
            </div>
          </div>
        )}
      </div>

      {/* Avisos */}
      {!user && (
        <div className="mt-4 p-4 bg-yellow-50 rounded-lg flex items-start">
          <AlertCircle className="h-5 w-5 text-yellow-600 mr-2 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-yellow-800 font-medium">
              Faça login para fazer upload
            </p>
            <p className="text-xs text-yellow-700 mt-1">
              Crie uma conta grátis e ganhe 10 minutos para testar
            </p>
          </div>
        </div>
      )}

      {user && user.minutesRemaining < 5 && (
        <div className="mt-4 p-4 bg-orange-50 rounded-lg flex items-start">
          <AlertCircle className="h-5 w-5 text-orange-600 mr-2 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-orange-800 font-medium">
              Créditos baixos
            </p>
            <p className="text-xs text-orange-700 mt-1">
              Você tem apenas {user.minutesRemaining} minutos restantes
            </p>
          </div>
        </div>
      )}

      {/* Informações */}
      <div className="mt-6 text-xs text-gray-500 space-y-1">
        <p>• A transcrição usa IA para detectar falas automaticamente</p>
        <p>• Tempo de processamento: ~1 minuto para cada 5 minutos de áudio</p>
        <p>• Formatos de saída: SRT, VTT, JSON</p>
        <p>• Seus arquivos são processados com segurança e deletados após 24h</p>
      </div>
    </div>
  )
}