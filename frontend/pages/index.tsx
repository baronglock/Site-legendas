import { useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import Layout from '@/components/Layout'
import { 
  CheckCircle, ArrowRight, Zap, Globe, Clock, Play, 
  FileText, DollarSign, Users, Star, ChevronDown,
  Sparkles, Shield, Headphones
} from 'lucide-react'

export default function Home() {
  const [openFaq, setOpenFaq] = useState<number | null>(null)

  const features = [
    {
      icon: Zap,
      title: 'Processamento Ultrarrápido',
      description: 'IA de última geração processa 1 hora de vídeo em apenas 3 minutos',
      color: 'bg-yellow-500'
    },
    {
      icon: Globe,
      title: 'Tradução Contextual',
      description: 'Nossa IA entende contexto e adapta expressões culturais, não apenas traduz',
      color: 'bg-blue-500'
    },
    {
      icon: DollarSign,
      title: '80% Mais Barato',
      description: 'Economize comparado aos concorrentes. Pague apenas pelo que usar',
      color: 'bg-green-500'
    },
    {
      icon: Shield,
      title: '100% Seguro',
      description: 'Seus arquivos são processados com segurança e deletados em 24h',
      color: 'bg-purple-500'
    }
  ]

  const testimonials = [
    {
      name: 'Maria Silva',
      role: 'YouTuber',
      content: 'Economizo 10 horas por semana! A tradução é perfeita para meu público.',
      rating: 5,
      avatar: '👩‍💼'
    },
    {
      name: 'João Santos',
      role: 'Professor',
      content: 'Uso para criar legendas das minhas aulas. Simples e eficiente!',
      rating: 5,
      avatar: '👨‍🏫'
    },
    {
      name: 'Tech Startup',
      role: 'Empresa',
      content: 'API robusta para nossos produtos. Suporte excelente!',
      rating: 5,
      avatar: '🏢'
    }
  ]

  const faqs = [
    {
      question: 'Como funciona o processo?',
      answer: 'É simples: você faz upload do vídeo/áudio, nossa IA transcreve com alta precisão, traduz mantendo o contexto, e você baixa as legendas prontas em SRT, VTT ou JSON.'
    },
    {
      question: 'Quanto tempo demora?',
      answer: 'Em média, processamos 1 hora de vídeo em 3-5 minutos. Vídeos menores são ainda mais rápidos!'
    },
    {
      question: 'Quais idiomas são suportados?',
      answer: 'Suportamos mais de 50 idiomas para transcrição e tradução entre português, inglês, espanhol, francês, alemão, italiano, japonês, coreano, chinês e mais.'
    },
    {
      question: 'Posso editar as legendas depois?',
      answer: 'Sim! Você pode baixar o arquivo e editar em qualquer editor de texto, ou usar nosso editor online (em breve).'
    },
    {
      question: 'É seguro enviar meus vídeos?',
      answer: 'Totalmente! Usamos criptografia em todo o processo e deletamos automaticamente seus arquivos após 24 horas.'
    }
  ]

  return (
    <Layout>
      {/* Hero Section Melhorada */}
      <section className="relative overflow-hidden bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800">
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-black/20" />
          <div className="absolute top-0 left-0 w-96 h-96 bg-purple-500 rounded-full filter blur-3xl opacity-20 animate-pulse" />
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-indigo-500 rounded-full filter blur-3xl opacity-20 animate-pulse" />
        </div>
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center"
          >
            <div className="inline-flex items-center px-4 py-2 bg-white/10 backdrop-blur border border-white/20 rounded-full text-white text-sm mb-8">
              <Sparkles className="h-4 w-4 mr-2" />
              <span>Novo: Upload por URL do YouTube!</span>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold mb-6 text-white">
              Legendas com IA em<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-300 to-orange-400">
                Minutos, Não Horas
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl mb-12 text-purple-100 max-w-3xl mx-auto">
              Transcreva e traduza vídeos com precisão profissional.
              <span className="block text-lg mt-2">Upload → IA Processa → Legendas Prontas ✨</span>
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
              <Link 
                href="/register" 
                className="group inline-flex items-center px-8 py-4 bg-gradient-to-r from-yellow-400 to-orange-400 text-gray-900 font-bold rounded-xl hover:from-yellow-300 hover:to-orange-300 transform hover:scale-105 transition-all shadow-xl"
              >
                Começar Grátis (20 min)
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              
              <Link 
                href="#demo"
                className="inline-flex items-center px-8 py-4 bg-white/10 backdrop-blur border-2 border-white/30 text-white font-bold rounded-xl hover:bg-white/20 transition-all"
              >
                <Play className="mr-2 h-5 w-5" />
                Ver Demonstração
              </Link>
            </div>
            
            <div className="flex items-center justify-center space-x-8 text-white/80">
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 mr-2 text-green-400" />
                <span>Sem cartão de crédito</span>
              </div>
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 mr-2 text-green-400" />
                <span>Cancele quando quiser</span>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 bg-gray-50 border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <div className="text-4xl font-bold text-gray-900">50k+</div>
              <div className="text-gray-600">Vídeos Processados</div>
            </motion.div>
            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <div className="text-4xl font-bold text-gray-900">98%</div>
              <div className="text-gray-600">Precisão</div>
            </motion.div>
            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <div className="text-4xl font-bold text-gray-900">3min</div>
              <div className="text-gray-600">Tempo Médio</div>
            </motion.div>
            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <div className="text-4xl font-bold text-gray-900">50+</div>
              <div className="text-gray-600">Idiomas</div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Por que escolher o SubtitleAI?
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Tecnologia de ponta que economiza seu tempo e dinheiro
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -5 }}
                className="bg-white p-6 rounded-2xl shadow-lg hover:shadow-xl transition-all border border-gray-100"
              >
                <div className={`${feature.color} w-14 h-14 rounded-xl flex items-center justify-center mb-4`}>
                  <feature.icon className="h-7 w-7 text-white" />
                </div>
                <h3 className="text-xl font-bold mb-2 text-gray-900">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section className="py-20 bg-gray-50" id="demo">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Como funciona?
            </h2>
            <p className="text-xl text-gray-600">
              Processo simples em 3 passos
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl font-bold text-purple-600">1</span>
              </div>
              <h3 className="text-xl font-bold mb-2">Upload</h3>
              <p className="text-gray-600">
                Envie seu vídeo/áudio ou cole uma URL do YouTube
              </p>
            </motion.div>

            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl font-bold text-purple-600">2</span>
              </div>
              <h3 className="text-xl font-bold mb-2">IA Processa</h3>
              <p className="text-gray-600">
                Nossa IA transcreve e traduz com alta precisão
              </p>
            </motion.div>

            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl font-bold text-purple-600">3</span>
              </div>
              <h3 className="text-xl font-bold mb-2">Baixe</h3>
              <p className="text-gray-600">
                Receba suas legendas em SRT, VTT ou JSON
              </p>
            </motion.div>
          </div>

          {/* Demo Video Placeholder */}
          <div className="mt-16 max-w-4xl mx-auto">
            <div className="bg-gray-900 rounded-2xl p-8 shadow-2xl">
              <div className="aspect-video bg-gray-800 rounded-lg flex items-center justify-center">
                <button className="group flex items-center space-x-3 bg-white/10 backdrop-blur px-6 py-3 rounded-lg hover:bg-white/20 transition">
                  <Play className="h-8 w-8 text-white group-hover:scale-110 transition" />
                  <span className="text-white font-medium">Ver demonstração</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              O que dizem nossos usuários
            </h2>
            <p className="text-xl text-gray-600">
              Junte-se a milhares de criadores satisfeitos
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 }}
                className="bg-gray-50 p-8 rounded-2xl"
              >
                <div className="flex items-center mb-4">
                  <div className="text-4xl mr-4">{testimonial.avatar}</div>
                  <div>
                    <div className="font-bold text-gray-900">{testimonial.name}</div>
                    <div className="text-sm text-gray-600">{testimonial.role}</div>
                  </div>
                </div>
                <div className="flex mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="h-5 w-5 text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className="text-gray-700">{testimonial.content}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Perguntas Frequentes
            </h2>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white rounded-lg shadow-sm"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === index ? null : index)}
                  className="w-full px-6 py-4 text-left flex items-center justify-between hover:bg-gray-50 transition"
                >
                  <span className="font-medium text-gray-900">{faq.question}</span>
                  <ChevronDown 
                    className={`h-5 w-5 text-gray-500 transition-transform ${
                      openFaq === index ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {openFaq === index && (
                  <div className="px-6 py-4 border-t">
                    <p className="text-gray-600">{faq.answer}</p>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Final */}
      <section className="py-20 bg-gradient-to-r from-purple-600 to-indigo-600">
        <div className="max-w-4xl mx-auto text-center px-4">
          <h2 className="text-4xl md:text-5xl font-bold mb-6 text-white">
            Pronto para economizar horas de trabalho?
          </h2>
          <p className="text-xl mb-8 text-purple-100">
            Comece grátis hoje e veja a diferença que nossa IA pode fazer
          </p>
          <Link 
            href="/register" 
            className="group inline-flex items-center px-8 py-4 bg-white text-purple-600 font-bold rounded-xl hover:bg-gray-100 transform hover:scale-105 transition-all shadow-xl text-lg"
          >
            Criar Conta Grátis
            <ArrowRight className="ml-2 h-6 w-6 group-hover:translate-x-1 transition-transform" />
          </Link>
          <p className="mt-4 text-purple-200">
            20 minutos grátis • Sem cartão de crédito • Cancele quando quiser
          </p>
        </div>
      </section>
    </Layout>
  )
}