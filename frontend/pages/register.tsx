import { useState } from 'react'
import { useRouter } from 'next/router'
import Layout from '@/components/Layout'
import { CheckCircle, XCircle } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import toast from 'react-hot-toast'

const plans = [
  {
    id: 'free',
    name: 'Gratuito',
    price: 0,
    minutes: 20,
    features: [
      '20 minutos/mês',
      'Transcrição básica',
      'Tradução com IA (qualidade padrão)',
      'Arquivos até 30MB',
      'Fila de espera',
    ],
    notIncluded: [
      'Tradução premium',
      'Prioridade no processamento',
      'Arquivos grandes',
    ]
  },
  {
    id: 'starter',
    name: 'Iniciante',
    price: 19,
    minutes: 60,
    popular: false,
    features: [
      '1 hora/mês',
      'Transcrição avançada',
      'Tradução adaptada com IA premium',
      'Arquivos até 100MB',
      'Processamento prioritário',
      'Suporte por email',
    ],
    notIncluded: []
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 49,
    minutes: 300,
    popular: true,
    features: [
      '5 horas/mês',
      'Transcrição de alta precisão',
      'Tradução contextual avançada',
      'Arquivos até 300MB',
      'Processamento expresso',
      'Múltiplos idiomas',
      'API de integração',
      'Suporte prioritário',
    ],
    notIncluded: []
  },
  {
    id: 'premium',
    name: 'Premium',
    price: 99,
    minutes: 900,
    features: [
      '15 horas/mês',
      'Todos os recursos Pro',
      'Arquivos ilimitados',
      'Processamento instantâneo',
      'White-label disponível',
      'Gerente de conta',
      'SLA garantido',
    ],
    notIncluded: []
  }
]

export default function Pricing() {
  const router = useRouter()
  const { user } = useAuth()
  const [loading, setLoading] = useState<string | null>(null)

  const handleSelectPlan = async (planId: string) => {
    if (!user) {
      router.push('/register')
      return
    }

    if (planId === 'free') {
      router.push('/dashboard')
      return
    }

    setLoading(planId)
    try {
      const response = await apiClient.createCheckout(planId)
      window.location.href = response.data.checkout_url
    } catch (error) {
      toast.error('Erro ao processar pagamento')
      setLoading(null)
    }
  }

  return (
    <Layout>
      <div className="py-12 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Escolha seu plano
            </h1>
            <p className="text-xl text-gray-600">
              Pague apenas pelo que usar. Cancele quando quiser.
            </p>
          </div>

          {/* Comparação rápida */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-8 max-w-3xl mx-auto">
            <p className="text-center text-sm">
              💡 <strong>Economize até 80%</strong> comparado aos concorrentes. 
              Nossa IA traduz e adapta, não apenas traduz palavra por palavra.
            </p>
          </div>

          {/* Grid de planos */}
          <div className="grid md:grid-cols-4 gap-6 mb-12">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className={`relative rounded-lg border-2 p-6 ${
                  plan.popular
                    ? 'border-purple-500 shadow-xl'
                    : 'border-gray-200'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-purple-500 text-white px-4 py-1 rounded-full text-sm font-medium">
                      Mais Popular
                    </span>
                  </div>
                )}

                <div className="text-center mb-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-2">
                    {plan.name}
                  </h3>
                  <div className="mb-1">
                    <span className="text-4xl font-bold">
                      {plan.price === 0 ? 'Grátis' : `R$ ${plan.price}`}
                    </span>
                    {plan.price > 0 && <span className="text-gray-600">/mês</span>}
                  </div>
                  <p className="text-sm text-gray-600">
                    {plan.minutes} minutos/mês
                  </p>
                  {plan.price > 0 && (
                    <p className="text-xs text-green-600 mt-1">
                      R$ {(plan.price / plan.minutes * 60).toFixed(2)}/hora
                    </p>
                  )}
                </div>

                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, i) => (
                    <li key={i} className="flex items-start text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                  {plan.notIncluded.map((feature, i) => (
                    <li key={`not-${i}`} className="flex items-start text-sm text-gray-400">
                      <XCircle className="h-4 w-4 text-gray-300 mr-2 flex-shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleSelectPlan(plan.id)}
                  disabled={loading !== null}
                  className={`w-full py-3 px-4 rounded-lg font-medium transition ${
                    plan.popular
                      ? 'bg-purple-600 text-white hover:bg-purple-700'
                      : plan.price === 0
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                  } disabled:opacity-50`}
                >
                  {loading === plan.id ? 'Processando...' : 
                   plan.price === 0 ? 'Usar Grátis' : 'Escolher Plano'}
                </button>
              </div>
            ))}
          </div>

          {/* Créditos extras */}
          <div className="max-w-3xl mx-auto">
            <h3 className="text-2xl font-bold text-center mb-6">
              Precisa de mais minutos?
            </h3>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="border rounded-lg p-4 text-center">
                <p className="font-bold">30 minutos</p>
                <p className="text-2xl font-bold text-purple-600">R$ 7,99</p>
                <p className="text-xs text-gray-600">R$ 15,98/hora</p>
              </div>
              <div className="border rounded-lg p-4 text-center">
                <p className="font-bold">1 hora</p>
                <p className="text-2xl font-bold text-purple-600">R$ 14,99</p>
                <p className="text-xs text-gray-600">R$ 14,99/hora</p>
              </div>
              <div className="border rounded-lg p-4 text-center">
                <p className="font-bold">3 horas</p>
                <p className="text-2xl font-bold text-purple-600">R$ 39,99</p>
                <p className="text-xs text-gray-600">R$ 13,33/hora</p>
              </div>
            </div>
          </div>

          {/* FAQ */}
          <div className="mt-16 max-w-3xl mx-auto">
            <h3 className="text-2xl font-bold text-center mb-8">
              Perguntas Frequentes
            </h3>
            <div className="space-y-4">
              <details className="border rounded-lg p-4">
                <summary className="font-medium cursor-pointer">
                  Posso cancelar a qualquer momento?
                </summary>
                <p className="mt-2 text-gray-600">
                  Sim! Não há fidelidade. Você pode cancelar ou trocar de plano quando quiser.
                </p>
              </details>
              <details className="border rounded-lg p-4">
                <summary className="font-medium cursor-pointer">
                  Os minutos acumulam para o próximo mês?
                </summary>
                <p className="mt-2 text-gray-600">
                  Não, os minutos são renovados mensalmente. Use créditos extras para projetos pontuais.
                </p>
              </details>
              <details className="border rounded-lg p-4">
                <summary className="font-medium cursor-pointer">
                  Qual a diferença da tradução premium?
                </summary>
                <p className="mt-2 text-gray-600">
                  A tradução premium usa IA avançada que entende contexto, adapta expressões e 
                  mantém o tom original, não apenas traduz palavra por palavra.
                </p>
              </details>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}