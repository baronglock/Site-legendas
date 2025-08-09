import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api'
import { Clock, CheckCircle, XCircle, Download } from 'lucide-react'

export default function JobStatus() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchJobs()
  }, [])

  const fetchJobs = async () => {
    try {
      const response = await apiClient.getJobs()
      setJobs(response.data.jobs)
    } catch (error) {
      console.error('Erro ao buscar jobs:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div>Carregando...</div>

  return (
    <div className="space-y-4">
      {jobs.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          Nenhum trabalho ainda. Faça seu primeiro upload!
        </p>
      ) : (
        jobs.map((job: any) => (
          <div key={job.id} className="card">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                {job.status === 'completed' && <CheckCircle className="h-5 w-5 text-green-500" />}
                {job.status === 'processing' && <Clock className="h-5 w-5 text-yellow-500 animate-spin" />}
                {job.status === 'failed' && <XCircle className="h-5 w-5 text-red-500" />}
                
                <div>
                  <p className="font-medium">{job.filename || 'Arquivo'}</p>
                  <p className="text-sm text-gray-500">
                    {new Date(job.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {job.status === 'completed' && job.downloads && (
                <button className="flex items-center text-purple-600 hover:text-purple-700">
                  <Download className="h-4 w-4 mr-1" />
                  Baixar
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  )
}