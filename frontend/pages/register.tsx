import { useState } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import Layout from '@/components/Layout'
import { apiClient } from '@/lib/api'
import toast from 'react-hot-toast'
import { Mail, CheckCircle } from 'lucide-react'

export default function Register() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!email) {
      toast.error('Digite seu email')
      return
    }

    setLoading(true)
    try {
      const response = await apiClient.register({ email })
      
      // IMPORTANTE: Salvar o token mock
      localStorage.setItem('token', response.data.access_token)
      
      // Salvar dados do usuário mock
      localStorage.setItem('user', JSON.stringify({
        id: response.data.user_id,
        email: email,
        plan: 'free',
        minutesRemaining: 1000,
        minutesTotal: 1000,
        jobsCompleted: 0
      }))
      
      toast.success('Conta criada com sucesso!')
      
      // IR DIRETO PARA O DASHBOARD
      router.push('/dashboard')
      
    } catch (error: any) {
      console.error('Erro no registro:', error)
      toast.error('Erro ao criar conta - verifique o console')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <div className="min-h-[80vh] flex items-center justify-center px-4">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900">
              Crie sua conta grátis
            </h2>
            <p className="mt-2 text-gray-600">
              Ganhe 1000 minutos para testar (modo local)
            </p>
          </div>

          {/* Benefícios */}
          <div className="bg-purple-50 rounded-lg p-4 space-y-2">
            <div className="flex items-center text-sm">
              <CheckCircle className="h-4 w-4 text-purple-600 mr-2 flex-shrink-0" />
              <span>1000 minutos grátis (modo teste)</span>
            </div>
            <div className="flex items-center text-sm">
              <CheckCircle className="h-4 w-4 text-purple-600 mr-2 flex-shrink-0" />
              <span>Upload ilimitado localmente</span>
            </div>
            <div className="flex items-center text-sm">
              <CheckCircle className="h-4 w-4 text-purple-600 mr-2 flex-shrink-0" />
              <span>Sem necessidade de cartão</span>
            </div>
          </div>

          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 input"
                  placeholder="seu@email.com"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 rounded-lg font-medium hover:from-purple-700 hover:to-blue-700 disabled:opacity-50"
            >
              {loading ? 'Criando conta...' : 'Criar conta grátis'}
            </button>

            <p className="text-xs text-center text-gray-500">
              Modo de teste local - Sem validação real
            </p>

            <div className="text-center">
              <span className="text-gray-600">Já tem conta? </span>
              <Link href="/login" className="text-purple-600 hover:text-purple-700 font-medium">
                Fazer login
              </Link>
            </div>
          </form>
        </div>
      </div>
    </Layout>
  )
}