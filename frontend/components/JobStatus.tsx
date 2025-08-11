import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'

export default function JobStatus({ jobId }: { jobId: string }) {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!jobId) return

    const checkStatus = async () => {
      try {
        const response = await apiClient.getJob(jobId)
        setStatus(response.data)
        
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          setLoading(false)
        }
      } catch (error) {
        console.error('Erro ao verificar status:', error)
      }
    }

    checkStatus()
    const interval = setInterval(checkStatus, 2000)
    
    return () => clearInterval(interval)
  }, [jobId])

  if (!status) return null

  return (
    <div className="mt-4 p-4 bg-gray-100 rounded-lg">
      <h3 className="font-semibold">Status do Processamento</h3>
      <p>Job ID: {jobId}</p>
      <p>Status: {status.status}</p>
      <p>Progresso: {status.progress}</p>
      
      {status.status === 'completed' && (
        <div className="mt-4 space-x-2">
          <a 
            href={`http://localhost:8000/api/v1/download/${jobId}/srt`}
            className="bg-blue-500 text-white px-4 py-2 rounded"
            download
          >
            Baixar SRT
          </a>
        </div>
      )}
    </div>
  )
}