import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function UsageStats() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await apiClient.getStats()
      setStats(response.data)
    } catch (error) {
      console.error('Erro ao buscar estatísticas:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div>Carregando...</div>

  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-3 gap-4">
        <div className="card">
          <h3 className="text-lg font-medium mb-2">Total de Transcrições</h3>
          <p className="text-3xl font-bold text-purple-600">{stats?.total_jobs || 0}</p>
        </div>
        <div className="card">
          <h3 className="text-lg font-medium mb-2">Horas Processadas</h3>
          <p className="text-3xl font-bold text-blue-600">{stats?.total_hours_processed || 0}</p>
        </div>
        <div className="card">
          <h3 className="text-lg font-medium mb-2">Economia Total</h3>
          <p className="text-3xl font-bold text-green-600">R$ {stats?.total_savings || 0}</p>
        </div>
      </div>

      {/* Gráfico de uso mensal */}
      <div className="card">
        <h3 className="text-lg font-medium mb-4">Uso Mensal</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={stats?.monthly_usage || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="minutes" fill="#8b5cf6" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}