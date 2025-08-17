import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAuth } from '@/lib/auth'
import Layout from '@/components/Layout'
import { 
  Upload, 
  FileText, 
  BarChart3, 
  Clock,
  CreditCard,
  TrendingUp,
  Activity
} from 'lucide-react'
import UnifiedUploadComponent from '@/components/UnifiedUploadComponent'
import JobsList from '@/components/JobsList'
import UsageStats from '@/components/UsageStats'
import { apiClient } from '@/lib/api'
import { showToast } from '@/components/CustomToast'

export default function Dashboard() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('upload')
  const [stats, setStats] = useState<any>(null)
  const [recentActivity, setRecentActivity] = useState<any[]>([])
  
  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  useEffect(() => {
    if (user) {
      fetchDashboardData()
    }
  }, [user])

  const fetchDashboardData = async () => {
    try {
      // Buscar estatísticas
      const [statsResponse, jobsResponse] = await Promise.all([
        apiClient.getStats(),
        apiClient.getJobs({ limit: 5 })
      ])
      
      setStats(statsResponse.data)
      setRecentActivity(jobsResponse.data.jobs)
    } catch (error) {
      console.error('Erro ao buscar dados:', error)
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
        </div>
      </Layout>
    )
  }

  if (!user) return null

  const tabs = [
    { id: 'upload', name: 'Nova Transcrição', icon: Upload },
    { id: 'jobs', name: 'Meus Arquivos', icon: FileText },
    { id: 'stats', name: 'Estatísticas', icon: BarChart3 },
  ]

  // Calcular porcentagem de uso
  const usagePercentage = user.minutesTotal > 0 
    ? ((user.minutesTotal - user.minutesRemaining) / user.minutesTotal) * 100 
    : 0

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header Melhorado */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">
              Olá, {user.email.split('@')[0]}! 👋
            </h1>
            <p className="mt-2 text-gray-600">
              Vamos criar legendas incríveis hoje?
            </p>
          </div>

          {/* Cards de Status - Design Melhorado */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* Card de Minutos */}
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Clock className="h-6 w-6 text-purple-600" />
                </div>
                <span className="text-xs font-medium text-purple-600 bg-purple-50 px-2 py-1 rounded-full">
                  {Math.round(100 - usagePercentage)}% disponível
                </span>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Minutos Disponíveis</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {user.minutesRemaining || 0}
                  <span className="text-sm font-normal text-gray-500">/{user.minutesTotal || 0}</span>
                </p>
                {/* Barra de progresso */}
                <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-purple-500 to-purple-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${100 - usagePercentage}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Card de Arquivos */}
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <FileText className="h-6 w-6 text-blue-600" />
                </div>
                <TrendingUp className="h-4 w-4 text-green-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Arquivos Processados</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {stats?.total_jobs || 0}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  +{recentActivity.filter(job => {
                    const createdAt = new Date(job.created_at)
                    const today = new Date()
                    return createdAt.toDateString() === today.toDateString()
                  }).length} hoje
                </p>
              </div>
            </div>

            {/* Card de Horas Economizadas */}
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Activity className="h-6 w-6 text-green-600" />
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Horas Economizadas</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {Math.round((stats?.total_minutes_processed || 0) * 8 / 60)}h
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  vs. transcrição manual
                </p>
              </div>
            </div>

            {/* Card do Plano */}
            <div className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-xl shadow-sm p-6 text-white hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className="p-2 bg-white/20 rounded-lg">
                  <CreditCard className="h-6 w-6 text-white" />
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-purple-100">Plano Atual</p>
                <p className="text-2xl font-bold text-white mt-1 capitalize">
                  {user.plan || 'Free'}
                </p>
                {user.plan === 'free' && (
                  <button 
                    onClick={() => router.push('/pricing')}
                    className="text-xs text-white/80 hover:text-white mt-1 underline"
                  >
                    Fazer upgrade →
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Tabs com Design Melhorado */}
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="border-b border-gray-200">
              <nav className="flex" aria-label="Tabs">
                {tabs.map((tab) => {
                  const Icon = tab.icon
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`
                        flex-1 flex items-center justify-center py-4 px-6 text-sm font-medium
                        border-b-2 transition-colors duration-200
                        ${activeTab === tab.id
                          ? 'border-purple-500 text-purple-600 bg-purple-50/50'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
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

            <div className="p-8">
              {activeTab === 'upload' && (
                <div className="space-y-6">
                  {/* Quick tips */}
                  {user.minutesRemaining < 10 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start">
                      <AlertCircle className="h-5 w-5 text-amber-600 mr-3 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-amber-900">
                          Créditos baixos!
                        </p>
                        <p className="text-sm text-amber-700 mt-1">
                          Você tem apenas {user.minutesRemaining} minutos restantes. 
                          <button 
                            onClick={() => router.push('/pricing')}
                            className="font-medium underline ml-1"
                          >
                            Comprar mais créditos
                          </button>
                        </p>
                      </div>
                    </div>
                  )}
                  
                  <UnifiedUploadComponent />
                  
                  {/* Atividade Recente */}
                  {recentActivity.length > 0 && (
                    <div className="mt-8 pt-8 border-t">
                      <h3 className="text-lg font-medium text-gray-900 mb-4">
                        Processados Recentemente
                      </h3>
                      <div className="space-y-3">
                        {recentActivity.slice(0, 3).map((job) => (
                          <div key={job.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center space-x-3">
                              <FileText className="h-5 w-5 text-gray-400" />
                              <div>
                                <p className="text-sm font-medium text-gray-900">{job.filename}</p>
                                <p className="text-xs text-gray-500">
                                  {new Date(job.created_at).toLocaleString('pt-BR')}
                                </p>
                              </div>
                            </div>
                            {job.status === 'completed' && (
                              <button
                                onClick={() => setActiveTab('jobs')}
                                className="text-sm text-purple-600 hover:text-purple-700"
                              >
                                Ver →
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {activeTab === 'jobs' && <JobsList />}
              {activeTab === 'stats' && <UsageStats />}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}