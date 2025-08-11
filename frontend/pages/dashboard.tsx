import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAuth } from '@/lib/auth'
import Layout from '@/components/Layout'
import { 
  Upload, 
  FileText, 
  BarChart3, 
  CreditCard, 
  Clock,
  Download,
  AlertCircle
} from 'lucide-react'
import UploadForm from '@/components/UploadForm'
import UsageStats from '@/components/UsageStats'
import JobsList from '@/components/JobsList'
import { apiClient } from '@/lib/api'  // Adicionar este import
import toast from 'react-hot-toast'

export default function Dashboard() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('upload')
  const [jobs, setJobs] = useState([])  // Adicionar este estado
  const [stats, setStats] = useState<any>(null)
  
  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  // Adicionar esta função
  useEffect(() => {
    if (activeTab === 'jobs' && user) {
      fetchJobs()
      const interval = setInterval(fetchJobs, 3000)
      return () => clearInterval(interval)
    }
  }, [activeTab, user])

  // Adicionar esta função
  const fetchJobs = async () => {
    try {
      const response = await apiClient.getJobs()
      setJobs(response.data.jobs)
    } catch (error) {
      console.error('Erro ao buscar jobs:', error)
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        </div>
      </Layout>
    )
  }

  if (!user) return null

  const tabs = [
    { id: 'upload', name: 'Novo Upload', icon: Upload },
    { id: 'jobs', name: 'Processados', icon: FileText },
    { id: 'stats', name: 'Estatísticas', icon: BarChart3 },
  ]

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Bem-vindo, {user.email}
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Minutos Disponíveis</p>
                <p className="text-2xl font-bold text-gray-900">
                  {user.minutesRemaining || 0}
                </p>
              </div>
              <Clock className="h-8 w-8 text-purple-600" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Arquivos Processados</p>
                <p className="text-2xl font-bold text-gray-900">
                  {jobs.length}
                </p>
              </div>
              <FileText className="h-8 w-8 text-blue-600" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Plano Atual</p>
                <p className="text-2xl font-bold text-gray-900 capitalize">
                  {user.plan || 'Free'}
                </p>
              </div>
              <CreditCard className="h-8 w-8 text-green-600" />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 px-6" aria-label="Tabs">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`
                      flex items-center py-4 px-1 border-b-2 font-medium text-sm
                      ${activeTab === tab.id
                        ? 'border-purple-500 text-purple-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }
                    `}
                  >
                    <Icon className="mr-2 h-5 w-5" />
                    {tab.name}
                  </button>
                )
              })}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'upload' && <UploadForm />}
            {activeTab === 'jobs' && <JobsList />}
            {activeTab === 'stats' && <UsageStats />}
          </div>
        </div>
      </div>
    </Layout>
  )
}