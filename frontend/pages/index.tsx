import { useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import Layout from '@/components/Layout'
import { CheckCircle, ArrowRight, Zap, Globe, Clock } from 'lucide-react'

export default function Home() {
  const [showComparison, setShowComparison] = useState(false)

  return (
    <Layout>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-purple-600 to-blue-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center"
          >
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              Legendas em Minutos,<br />
              <span className="text-yellow-300">Não em Horas</span>
            </h1>
            <p className="text-xl md:text-2xl mb-8 text-blue-100">
              Upload → Transcrição → Tradução Adaptada → Pronto!<br />
              <span className="text-sm">Tudo em um único fluxo, sem complicação</span>
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/register" className="inline-flex items-center px-8 py-4 bg-yellow-400 text-gray-900 font-bold rounded-lg hover:bg-yellow-300 transition">
                Começar Grátis (20 min)
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <button 
                onClick={() => setShowComparison(!showComparison)}
                className="px-8 py-4 bg-white/10 backdrop-blur border border-white/20 rounded-lg hover:bg-white/20 transition"
              >
                Ver Comparação de Preços
              </button>
            </div>
          </motion.div>
        </div>
        
        {/* Animated background */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-600/20 to-blue-600/20" />
      </section>

      {/* Diferencial Competitivo */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Por que somos diferentes?
            </h2>
            <p className="text-xl text-gray-600">
              Enquanto outros cobram por partes separadas, nós entregamos tudo de uma vez
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="bg-white p-6 rounded-xl shadow-lg"
            >
              <Zap className="h-12 w-12 text-yellow-500 mb-4" />
              <h3 className="text-xl font-bold mb-2">Fluxo Único</h3>
              <p className="text-gray-600">
                Upload e pronto! Receba suas legendas traduzidas sem precisar rodar processos separados.
              </p>
            </motion.div>

            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="bg-white p-6 rounded-xl shadow-lg"
            >
              <Globe className="h-12 w-12 text-blue-500 mb-4" />
              <h3 className="text-xl font-bold mb-2">Tradução Adaptada</h3>
              <p className="text-gray-600">
                IA que entende contexto e adapta expressões, não apenas traduz palavra por palavra.
              </p>
            </motion.div>

            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="bg-white p-6 rounded-xl shadow-lg"
            >
              <Clock className="h-12 w-12 text-green-500 mb-4" />
              <h3 className="text-xl font-bold mb-2">Pague Só o Que Usar</h3>
              <p className="text-gray-600">
                Planos flexíveis + créditos avulsos. Sem pacotes gigantes que você não vai usar.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Comparação de Preços */}
      {showComparison && (
        <motion.section 
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="py-16 bg-white"
        >
          <div className="max-w-4xl mx-auto px-4">
            <h3 className="text-2xl font-bold mb-8 text-center">
              Comparação Honesta de Preços
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-4">Serviço</th>
                    <th className="text-center py-4">Nós</th>
                    <th className="text-center py-4">Concorrente</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-4">Plano Básico</td>
                    <td className="text-center font-bold text-green-600">
                      R$ 19/mês<br />
                      <span className="text-sm text-gray-500">1 hora completa</span>
                    </td>
                    <td className="text-center">
                      R$ 290/mês<br />
                      <span className="text-sm text-gray-500">100 min (1.6h)</span>
                    </td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-4">Processo</td>
                    <td className="text-center text-green-600">
                      <CheckCircle className="inline h-5 w-5" /> Tudo incluso
                    </td>
                    <td className="text-center text-gray-500">
                      Cobra separado
                    </td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-4">Tradução</td>
                    <td className="text-center text-green-600">
                      <CheckCircle className="inline h-5 w-5" /> Adaptada por IA
                    </td>
                    <td className="text-center text-gray-500">
                      Literal/Básica
                    </td>
                  </tr>
                  <tr>
                    <td className="py-4">Créditos Avulsos</td>
                    <td className="text-center text-green-600">
                      <CheckCircle className="inline h-5 w-5" /> R$ 14,99/hora
                    </td>
                    <td className="text-center text-gray-500">
                      Não oferece
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-center mt-6 text-gray-600">
              💡 No concorrente, para ter o mesmo que oferecemos, você pagaria o dobro e ainda teria que rodar etapas separadas.
            </p>
          </div>
        </motion.section>
      )}

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-purple-600 to-blue-600 text-white">
        <div className="max-w-4xl mx-auto text-center px-4">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Pronto para economizar tempo e dinheiro?
          </h2>
          <p className="text-xl mb-8">
            Ganhe 20 minutos grátis agora e veja a diferença!
          </p>
          <Link href="/register" className="inline-flex items-center px-8 py-4 bg-yellow-400 text-gray-900 font-bold rounded-lg hover:bg-yellow-300 transition text-lg">
            Criar Conta Grátis
            <ArrowRight className="ml-2 h-6 w-6" />
          </Link>
          <p className="mt-4 text-sm opacity-80">
            Não pedimos cartão de crédito
          </p>
        </div>
      </section>
    </Layout>
  )
}