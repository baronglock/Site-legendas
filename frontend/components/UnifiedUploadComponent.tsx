import React, { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileVideo, CheckCircle, XCircle, Download, Eye, AlertCircle, Link2, HardDrive } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { apiClient } from '@/lib/api'
import { showToast, subtitleToasts } from '@/components/CustomToast'
import URLUploadComponent from '@/components/URLUploadComponent'

interface ProcessingStage {
  name: string
  progress: number
  status: 'pending' | 'processing' | 'completed' | 'error'
}

export default function UnifiedUploadComponent() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<'file' | 'url'>('file')
  const [file, setFile] = useState<File | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [overallProgress, setOverallProgress] = useState(0)
  const [currentStage, setCurrentStage] = useState('')
  const [processingComplete, setProcessingComplete] = useState(false)
  const [downloadUrls, setDownloadUrls] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  
  const [stages, setStages] = useState<ProcessingStage[]>([
    { name: 'Upload', progress: 0, status: 'pending' },
    { name: 'Extração de Áudio', progress: 0, status: 'pending' },
    { name: 'Transcrição', progress: 0, status: 'pending' },
    { name: 'Tradução', progress: 0, status: 'pending' },
    { name: 'Finalização', progress: 0, status: 'pending' }
  ])

  const updateStage = (index: number, progress: number, status: ProcessingStage['status']) => {
    setStages(prev => {
      const newStages = [...prev]
      newStages[index] = { ...newStages[index], progress, status }
      return newStages
    })
  }

  const checkJobStatus = useCallback(async () => {
    if (!jobId || processingComplete) return

    try {
      const response = await apiClient.getJob(jobId)
      const job = response.data

      // Mapear status para progresso
      switch (job.status) {
        case 'queued':
          setCurrentStage('Na fila...')
          break
        case 'processing':
          updateStage(1, 100, 'completed')
          updateStage(2, 50, 'processing')
          setCurrentStage('Extraindo áudio...')
          setOverallProgress(30)
          break
        case 'transcribing':
          updateStage(1, 100, 'completed')
          updateStage(2, 100, 'completed')
          updateStage(3, 50, 'processing')
          setCurrentStage('Transcrevendo com IA...')
          setOverallProgress(60)
          break
        case 'translating':
          updateStage(1, 100, 'completed')
          updateStage(2, 100, 'completed')
          updateStage(3, 100, 'completed')
          updateStage(4, 50, 'processing')
          setCurrentStage('Traduzindo...')
          setOverallProgress(80)
          break
        case 'completed':
          // Atualizar todos os estágios como completos
          stages.forEach((_, index) => updateStage(index, 100, 'completed'))
          setOverallProgress(100)
          setCurrentStage('Concluído!')
          setProcessingComplete(true)
          setDownloadUrls(job.download_urls)
          subtitleToasts.processingComplete(job.download_urls)
          break
        case 'failed':
          setError(job.error || 'Erro no processamento')
          setCurrentStage('Erro')
          stages.forEach((stage, index) => {
            if (stage.status === 'processing') {
              updateStage(index, 0, 'error')
            }
          })
          break
      }
    } catch (error) {
      console.error('Erro ao verificar status:', error)
    }
  }, [jobId, processingComplete])

  useEffect(() => {
    if (jobId && !processingComplete && !error) {
      const interval = setInterval(checkJobStatus, 2000)
      return () => clearInterval(interval)
    }
  }, [jobId, processingComplete, error, checkJobStatus])

  // Função chamada quando um job é criado via URL
  const handleJobCreated = (newJobId: string) => {
    setJobId(newJobId)
    setFile(null) // Limpar arquivo se houver
    setError(null)
    setProcessingComplete(false)
    setDownloadUrls(null)
    setOverallProgress(20) // URL já foi processada, começar em 20%
    
    // Reset stages mas com upload já completo
    setStages([
      { name: 'Upload', progress: 100, status: 'completed' },
      { name: 'Extração de Áudio', progress: 0, status: 'processing' },
      { name: 'Transcrição', progress: 0, status: 'pending' },
      { name: 'Tradução', progress: 0, status: 'pending' },
      { name: 'Finalização', progress: 0, status: 'pending' }
    ])
    setCurrentStage('Processando URL...')
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setFile(file)
    setError(null)
    setProcessingComplete(false)
    setDownloadUrls(null)
    
    // Reset stages
    setStages([
      { name: 'Upload', progress: 0, status: 'processing' },
      { name: 'Extração de Áudio', progress: 0, status: 'pending' },
      { name: 'Transcrição', progress: 0, status: 'pending' },
      { name: 'Tradução', progress: 0, status: 'pending' },
      { name: 'Finalização', progress: 0, status: 'pending' }
    ])

    // Validações
    const maxSize = user?.plan === 'free' ? 30 : 300 // MB
    if (file.size > maxSize * 1024 * 1024) {
      subtitleToasts.fileTooLarge(maxSize)
      setError(`Arquivo muito grande. Máximo: ${maxSize}MB`)
      return
    }

    // Simular progresso de upload
    setCurrentStage('Enviando arquivo...')
    let uploadProgress = 0
    const uploadInterval = setInterval(() => {
      uploadProgress += 10
      updateStage(0, uploadProgress, 'processing')
      setOverallProgress(uploadProgress * 0.2) // Upload é 20% do total
      
      if (uploadProgress >= 100) {
        clearInterval(uploadInterval)
      }
    }, 200)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_language', 'auto')
    formData.append('target_language', 'pt')
    formData.append('translate', 'true')

    try {
      const response = await apiClient.uploadFile(formData)
      clearInterval(uploadInterval)
      updateStage(0, 100, 'completed')
      setOverallProgress(20)
      
      if (response.data.job_id) {
        setJobId(response.data.job_id)
        setCurrentStage('Processando...')
        subtitleToasts.uploadComplete(response.data.job_id)
      }
    } catch (error: any) {
      clearInterval(uploadInterval)
      updateStage(0, 0, 'error')
      setError('Erro no upload. Tente novamente.')
      setOverallProgress(0)
      subtitleToasts.networkError()
    }
  }, [user])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
      'audio/*': ['.mp3', '.wav', '.m4a', '.aac']
    },
    maxFiles: 1,
    disabled: !!jobId && !processingComplete && !error
  })

  const reset = () => {
    setFile(null)
    setJobId(null)
    setOverallProgress(0)
    setCurrentStage('')
    setProcessingComplete(false)
    setDownloadUrls(null)
    setError(null)
    setStages([
      { name: 'Upload', progress: 0, status: 'pending' },
      { name: 'Extração de Áudio', progress: 0, status: 'pending' },
      { name: 'Transcrição', progress: 0, status: 'pending' },
      { name: 'Tradução', progress: 0, status: 'pending' },
      { name: 'Finalização', progress: 0, status: 'pending' }
    ])
  }

  // Se há um job em processamento, mostrar o progresso independente da aba
  if (jobId || file) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-8">
        {/* Header com info do arquivo */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <FileVideo className="h-8 w-8 text-purple-600" />
              <div>
                <h3 className="font-medium text-gray-900">
                  {file ? file.name : 'Processando URL'}
                </h3>
                {file && (
                  <p className="text-sm text-gray-500">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                )}
              </div>
            </div>
            {processingComplete && (
              <button
                onClick={reset}
                className="text-sm text-purple-600 hover:text-purple-700"
              >
                Novo upload
              </button>
            )}
          </div>
        </div>

        {/* Progresso Circular */}
        <div className="flex flex-col items-center mb-8">
          <div className="relative w-48 h-48">
            <svg className="w-48 h-48 transform -rotate-90">
              <circle
                cx="96"
                cy="96"
                r="88"
                stroke="currentColor"
                strokeWidth="8"
                fill="none"
                className="text-gray-200"
              />
              <circle
                cx="96"
                cy="96"
                r="88"
                stroke="currentColor"
                strokeWidth="8"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 88}`}
                strokeDashoffset={`${2 * Math.PI * 88 * (1 - overallProgress / 100)}`}
                className={`text-purple-600 transition-all duration-500 ${
                  error ? 'text-red-500' : processingComplete ? 'text-green-500' : ''
                }`}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold text-gray-800">
                {Math.round(overallProgress)}%
              </span>
              <span className="text-sm text-gray-500 text-center px-4">
                {currentStage}
              </span>
            </div>
          </div>
        </div>

        {/* Lista de Estágios */}
        <div className="space-y-3 mb-8">
          {stages.map((stage, index) => (
            <div key={index} className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                {stage.status === 'completed' ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : stage.status === 'error' ? (
                  <XCircle className="h-5 w-5 text-red-500" />
                ) : stage.status === 'processing' ? (
                  <div className="h-5 w-5 border-2 border-purple-600 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <div className="h-5 w-5 border-2 border-gray-300 rounded-full" />
                )}
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <span className={`text-sm font-medium ${
                    stage.status === 'completed' ? 'text-gray-900' : 'text-gray-500'
                  }`}>
                    {stage.name}
                  </span>
                  {stage.status === 'processing' && (
                    <span className="text-xs text-purple-600">{stage.progress}%</span>
                  )}
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${
                      stage.status === 'error' ? 'bg-red-500' : 'bg-purple-600'
                    }`}
                    style={{ width: `${stage.progress}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Mensagem de erro */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
            <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-red-800 font-medium">Erro no processamento</p>
              <p className="text-xs text-red-700 mt-1">{error}</p>
              <button
                onClick={reset}
                className="text-xs text-red-600 hover:text-red-700 mt-2 underline"
              >
                Tentar novamente
              </button>
            </div>
          </div>
        )}

        {/* Ações de Download */}
        {processingComplete && downloadUrls && (
          <div className="border-t pt-6">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Downloads disponíveis:</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <a
                href={`http://localhost:8000${downloadUrls.original}`}
                download
                className="flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <Download className="h-4 w-4 mr-2" />
                SRT
              </a>
              <a
                href={`http://localhost:8000${downloadUrls.vtt}`}
                download
                className="flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <Download className="h-4 w-4 mr-2" />
                VTT
              </a>
              <a
                href={`http://localhost:8000${downloadUrls.json}`}
                download
                className="flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <Download className="h-4 w-4 mr-2" />
                JSON
              </a>
              <button
                className="flex items-center justify-center px-4 py-2 border border-purple-300 rounded-md text-sm font-medium text-purple-700 bg-purple-50 hover:bg-purple-100"
              >
                <Eye className="h-4 w-4 mr-2" />
                Preview
              </button>
            </div>
          </div>
        )}

        {/* Info adicional */}
        {jobId && !processingComplete && !error && (
          <div className="mt-6 text-xs text-gray-500 text-center">
            <p>Job ID: {jobId}</p>
            <p className="mt-1">Tempo estimado: 1 min para cada 5 min de áudio</p>
          </div>
        )}
      </div>
    )
  }

  // Interface inicial com abas
  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Tabs */}
      <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg mb-6">
        <button
          onClick={() => setActiveTab('file')}
          className={`flex-1 flex items-center justify-center py-2 px-4 rounded-md font-medium transition-colors ${
            activeTab === 'file'
              ? 'bg-white text-purple-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <HardDrive className="h-4 w-4 mr-2" />
          Upload de Arquivo
        </button>
        <button
          onClick={() => setActiveTab('url')}
          className={`flex-1 flex items-center justify-center py-2 px-4 rounded-md font-medium transition-colors ${
            activeTab === 'url'
              ? 'bg-white text-purple-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <Link2 className="h-4 w-4 mr-2" />
          URL do YouTube
        </button>
      </div>

      {/* Conteúdo das abas */}
      {activeTab === 'file' ? (
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
            transition-all duration-200 transform
            ${isDragActive ? 'border-purple-500 bg-purple-50 scale-105' : 'border-gray-300 hover:border-gray-400'}
            ${!user ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <input {...getInputProps()} />
          
          <div className="space-y-4">
            <div className="mx-auto w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center">
              <Upload className="h-8 w-8 text-purple-600" />
            </div>
            
            <div>
              <p className="text-xl font-medium text-gray-700">
                {isDragActive ? 'Solte o arquivo aqui...' : 'Arraste um arquivo ou clique para selecionar'}
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Vídeo (MP4, MOV, AVI) ou Áudio (MP3, WAV, M4A)
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Máximo: {user?.plan === 'free' ? '30MB' : '300MB'}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <URLUploadComponent onJobCreated={handleJobCreated} />
      )}
    </div>
  )
}