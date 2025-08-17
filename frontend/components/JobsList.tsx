import { useState, useEffect } from 'react'
import { Download, CheckCircle, Clock, XCircle, RefreshCw, Globe, Eye, FileText } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { showToast } from '@/components/CustomToast'
import SubtitlePreview from '@/components/SubtitlePreview'

interface Job {
  id: string
  filename: string
  status: string
  created_at: number | string
  progress?: string
  error?: string
  detected_language?: string
  segments_count?: number
  duration?: number
  download_urls?: {
    original: string
    vtt: string
    json: string
    srt_pt?: string
  }
}

export default function JobsList() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [previewJob, setPreviewJob] = useState<string | null>(null) // ADICIONE ESTA LINHA

  useEffect(() => {
    fetchJobs()
    const interval = setInterval(fetchJobs, 2000)
    return () => clearInterval(interval)
  }, [])

  const fetchJobs = async () => {
    try {
      const response = await apiClient.getJobs()
      setJobs(response.data.jobs)
      setLoading(false)
    } catch (error) {
      console.error('Erro ao buscar jobs:', error)
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'processing':
        return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <Clock className="w-5 h-5 text-gray-500" />
    }
  }

  const getStatusText = (status: string, progress?: string) => {
    if (status === 'processing' && progress) {
      return progress
    }
    
    switch (status) {
      case 'completed':
        return 'Concluído'
      case 'processing':
        return 'Processando...'
      case 'failed':
        return 'Erro'
      default:
        return 'Aguardando'
    }
  }

  const formatDate = (timestamp: number | string) => {
    if (typeof timestamp === 'string') {
        return new Date(timestamp).toLocaleString('pt-BR')
    }
    return new Date(timestamp * 1000).toLocaleString('pt-BR')
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleDownload = (url: string, filename: string) => {
    const fullUrl = `http://localhost:8000${url}`
    const a = document.createElement('a')
    a.href = fullUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    showToast.success('Download iniciado!', `Baixando ${filename}`)
  }

  const handleTranslate = async (jobId: string) => {
    try {
      await fetch(`http://localhost:8000/api/v1/subtitle/translate/${jobId}`, {
        method: 'POST'
      })
      showToast.info('Tradução iniciada!', 'Aguarde alguns instantes...')
    } catch (error) {
      showToast.error('Erro ao iniciar tradução', 'Tente novamente mais tarde')
    }
  }

  if (loading) {
    return (
      <div className="text-center py-8">
        <RefreshCw className="w-8 h-8 text-gray-400 animate-spin mx-auto" />
        <p className="mt-2 text-gray-500">Carregando...</p>
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">Nenhum arquivo processado ainda.</p>
        <p className="text-sm text-gray-400 mt-2">
          Faça upload de um arquivo na aba "Nova Transcrição"
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">
            Arquivos Processados ({jobs.length})
          </h3>
          <button
            onClick={fetchJobs}
            className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <RefreshCw className="w-4 h-4" />
            Atualizar
          </button>
        </div>

        <div className="space-y-4">
          {jobs.map((job) => (
            <div key={job.id} className="bg-white border rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{job.filename}</h4>
                  <div className="mt-1 text-sm text-gray-500 space-y-1">
                    <p>ID: {job.id}</p>
                    <p>Data: {formatDate(job.created_at)}</p>
                    {job.detected_language && (
                      <p>Idioma detectado: {job.detected_language}</p>
                    )}
                    {job.segments_count && (
                      <p>Segmentos: {job.segments_count}</p>
                    )}
                    {job.duration && (
                      <p>Tempo de processamento: {job.duration.toFixed(1)}s</p>
                    )}
                  </div>
                </div>

                <div className="ml-4">
                  <div className="flex items-center gap-2 mb-2">
                    {getStatusIcon(job.status)}
                    <span className="text-sm font-medium">
                      {getStatusText(job.status, job.progress)}
                    </span>
                  </div>

                  {job.status === 'completed' && job.download_urls && (
                    <div className="space-y-2">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleDownload(job.download_urls!.original, `${job.filename}.srt`)}
                          className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-xs font-medium text-gray-700 bg-white hover:bg-gray-50"
                        >
                          <Download className="w-3 h-3 mr-1" />
                          SRT
                        </button>
                        <button
                          onClick={() => handleDownload(job.download_urls!.vtt, `${job.filename}.vtt`)}
                          className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-xs font-medium text-gray-700 bg-white hover:bg-gray-50"
                        >
                          <Download className="w-3 h-3 mr-1" />
                          VTT
                        </button>
                        <button
                          onClick={() => setPreviewJob(job.id)} // MUDANÇA AQUI
                          className="inline-flex items-center px-3 py-1 border border-purple-300 rounded-md text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100"
                        >
                          <Eye className="w-3 h-3 mr-1" />
                          Preview
                        </button>
                      </div>
                      
                      {job.detected_language !== 'pt' && (
                        <button
                          onClick={() => handleTranslate(job.id)}
                          className="inline-flex items-center px-3 py-1 border border-blue-300 rounded-md text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 w-full justify-center"
                        >
                          <Globe className="w-3 h-3 mr-1" />
                          Traduzir para PT
                        </button>
                      )}
                    </div>
                  )}

                  {job.status === 'failed' && job.error && (
                    <p className="text-xs text-red-600 mt-2">{job.error}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ADICIONE ESTE BLOCO NO FINAL DO COMPONENTE */}
      {previewJob && (
        <SubtitlePreview 
          jobId={previewJob}
          onClose={() => setPreviewJob(null)}
        />
      )}
    </>
  )
}