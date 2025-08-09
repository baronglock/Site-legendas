import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Layout from '@/components/Layout'
import UploadForm from '@/components/UploadForm'
import JobStatus from '@/components/JobStatus'
import UsageStats from '@/components/UsageStats'
import { useAuth } from '@/lib/auth'
import { Upload, Clock, TrendingUp, Gift } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Dashboard() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('upload')
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  // Simular quando usuário está perto do limite
  useEffect(() => {
    if (user && user.minutesRemaining < 5 && user.plan === 'free') {
      setTimeout(() => {
        toast((t) => (
          <div>
            <p className="font-bold">⏰ Apenas {user.minutesRemaining} minutos restantes!</p>
            <p className="text-sm">Faça upgrade para continuar sem interrupções</p>
            <button 
              onClick={() => {
                toast.dismiss(t.id)
                setShowUpgradeModal(true)
              }}
              className="mt-2 bg-purple-600 text-white px-4 py-1 rounded text-sm"
            >
              Ver Planos
            </button>
          </div>
        ), { duration: 6000 })
      }, 2000)
    }
  }, [user])

  if (loading) return <div>Carregando...</div>

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header com Stats */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Dashboard</h1>
          
          {/* Card de uso atual */}
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl p-6 text-white mb-6">
            <div className="grid md:grid-cols-3 gap-6">
              <div>
                <p className="text-purple-200 text-sm">Plano Atual</p>
                <p className="text-2xl font-bold capitalize">{user?.plan || 'Free'}</p>
              </div>
              <div>
                <p className="text-purple-200 text-sm">Minutos Restantes</p>
                <p className="text-2xl font-bold">{user?.minutesRemaining || 0} min</p>
                <div className="w-full bg-purple-800 rounded-full h-2 mt-2">
                  <div 
                    className="bg-yellow-400 h-2 rounded-full transition-all"
                    style={{ width: `${(user?.minutesRemaining / user?.minutesTotal) * 100}%` }}
                  />
                </div>
              </div>
              <div>
                <p className="text-purple-200 text-sm">Economia vs Concorrente</p>
                <p className="text-2xl font-bold">R$ {((user?.jobsCompleted || 0) * 17.4).toFixed(2)}</p>
              </div>
            </div>
          </div>

          {/* Bonus/Indicação */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Gift className="h-5 w-5 text-yellow-600 mr-2" />
                <span className="text-sm">
                  <strong>Ganhe 10 minutos extras!</strong> Indique um amigo e ambos ganham créditos.
                </span>
              </div>
              <button className="text-yellow-600 hover:text-yellow-700 text-sm font-medium">
                Indicar Agora
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('upload')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'upload'
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Upload className="inline h-4 w-4 mr-2" />
              Novo Upload
            </button>
            <button
              onClick={() => setActiveTab('jobs')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'jobs'
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Clock className="inline h-4 w-4 mr-2" />
              Trabalhos Recentes
            </button>
            <button
              onClick={() => setActiveTab('stats')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'stats'
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <TrendingUp className="inline h-4 w-4 mr-2" />
              Estatísticas
            </button>
          </nav>
        </div>

        {/* Content */}
        <div>
          {activeTab === 'upload' && <UploadForm />}
          {activeTab === 'jobs' && <JobStatus />}
          {activeTab === 'stats' && <UsageStats />}
        </div>
      </div>

      {/* Modal de Upgrade */}
      {showUpgradeModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-8 max-w-md w-full">
            <h3 className="text-2xl font-bold mb-4">Seus minutos estão acabando!</h3>
            <p className="text-gray-600 mb-6">
              Faça upgrade agora e continue legendando sem interrupções.
            </p>
            <div className="space-y-4">
              <div className="border rounded-lg p-4 hover:border-purple-500 cursor-pointer">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="font-bold">Plano Pro</h4>
                    <p className="text-sm text-gray-600">5 horas/mês</p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold">R$ 49</p>
                    <p className="text-xs text-gray-500">R$ 9,80/hora</p>
                  </div>
                </div>
              </div>
              <button 
                onClick={() => router.push('/pricing')}
                className="w-full bg-purple-600 text-white py-3 rounded-lg font-medium hover:bg-purple-700"
              >
                Ver Todos os Planos
              </button>
              <button 
                onClick={() => setShowUpgradeModal(false)}
                className="w-full text-gray-500 text-sm"
              >
                Continuar com plano atual
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}