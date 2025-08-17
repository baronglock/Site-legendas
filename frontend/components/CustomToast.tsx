import React from 'react'
import toast, { Toast } from 'react-hot-toast'
import { CheckCircle, XCircle, AlertCircle, Info, X, Clock, CreditCard } from 'lucide-react'

interface CustomToastProps {
  t: Toast
  type: 'success' | 'error' | 'warning' | 'info' | 'credits' | 'processing'
  title: string
  message?: string
  action?: {
    label: string
    onClick: () => void
  }
}

const CustomToast: React.FC<CustomToastProps> = ({ t, type, title, message, action }) => {
  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-500" />,
    error: <XCircle className="w-5 h-5 text-red-500" />,
    warning: <AlertCircle className="w-5 h-5 text-yellow-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />,
    credits: <CreditCard className="w-5 h-5 text-purple-500" />,
    processing: <Clock className="w-5 h-5 text-blue-500 animate-spin" />
  }

  const backgrounds = {
    success: 'bg-green-50 border-green-200',
    error: 'bg-red-50 border-red-200',
    warning: 'bg-yellow-50 border-yellow-200',
    info: 'bg-blue-50 border-blue-200',
    credits: 'bg-purple-50 border-purple-200',
    processing: 'bg-blue-50 border-blue-200'
  }

  const titleColors = {
    success: 'text-green-900',
    error: 'text-red-900',
    warning: 'text-yellow-900',
    info: 'text-blue-900',
    credits: 'text-purple-900',
    processing: 'text-blue-900'
  }

  const messageColors = {
    success: 'text-green-700',
    error: 'text-red-700',
    warning: 'text-yellow-700',
    info: 'text-blue-700',
    credits: 'text-purple-700',
    processing: 'text-blue-700'
  }

  return (
    <div
      className={`${
        t.visible ? 'animate-enter' : 'animate-leave'
      } max-w-md w-full ${backgrounds[type]} shadow-lg rounded-lg pointer-events-auto border`}
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">{icons[type]}</div>
          <div className="ml-3 flex-1">
            <p className={`text-sm font-medium ${titleColors[type]}`}>{title}</p>
            {message && (
              <p className={`mt-1 text-sm ${messageColors[type]}`}>{message}</p>
            )}
            {action && (
              <button
                onClick={action.onClick}
                className={`mt-2 text-sm font-medium ${titleColors[type]} hover:underline`}
              >
                {action.label} →
              </button>
            )}
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={() => toast.dismiss(t.id)}
              className="rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Helpers para usar o toast customizado
export const showToast = {
  success: (title: string, message?: string, action?: { label: string; onClick: () => void }) => {
    toast.custom((t) => (
      <CustomToast t={t} type="success" title={title} message={message} action={action} />
    ))
  },
  
  error: (title: string, message?: string) => {
    toast.custom((t) => (
      <CustomToast t={t} type="error" title={title} message={message} />
    ))
  },
  
  warning: (title: string, message?: string) => {
    toast.custom((t) => (
      <CustomToast t={t} type="warning" title={title} message={message} />
    ))
  },
  
  info: (title: string, message?: string) => {
    toast.custom((t) => (
      <CustomToast t={t} type="info" title={title} message={message} />
    ))
  },
  
  credits: (used: number, remaining: number) => {
    toast.custom((t) => (
      <CustomToast 
        t={t} 
        type="credits" 
        title="Créditos utilizados" 
        message={`${used} minutos usados. Restam ${remaining} minutos este mês.`}
        action={{
          label: "Comprar mais",
          onClick: () => window.location.href = '/pricing'
        }}
      />
    ))
  },
  
  processing: (fileName: string, stage: string) => {
    toast.custom((t) => (
      <CustomToast 
        t={t} 
        type="processing" 
        title={`Processando ${fileName}`}
        message={stage}
      />
    ), {
      duration: Infinity // Não desaparece automaticamente
    })
  }
}

// Exemplo de uso específico para o projeto
export const subtitleToasts = {
  uploadStarted: (fileName: string) => {
    showToast.processing(fileName, "Enviando arquivo...")
  },
  
  uploadComplete: (jobId: string) => {
    showToast.success(
      "Upload concluído!", 
      `Job ID: ${jobId}`,
      {
        label: "Ver progresso",
        onClick: () => {
          // Scroll para área de progresso ou mudar aba
          const progressElement = document.getElementById('progress-section')
          progressElement?.scrollIntoView({ behavior: 'smooth' })
        }
      }
    )
  },
  
  transcriptionComplete: () => {
    showToast.success("Transcrição concluída!", "Iniciando tradução...")
  },
  
  processingComplete: (downloadUrls: any) => {
    showToast.success(
      "Processamento concluído!",
      "Suas legendas estão prontas para download.",
      {
        label: "Baixar agora",
        onClick: () => {
          // Scroll para downloads ou abrir modal
          const downloadSection = document.getElementById('download-section')
          downloadSection?.scrollIntoView({ behavior: 'smooth' })
        }
      }
    )
  },
  
  insufficientCredits: (required: number, available: number) => {
    showToast.error(
      "Créditos insuficientes",
      `Necessário: ${required} min | Disponível: ${available} min`
    )
  },
  
  fileTooLarge: (maxSize: number) => {
    showToast.warning(
      "Arquivo muito grande",
      `O tamanho máximo permitido é ${maxSize}MB`
    )
  },
  
  networkError: () => {
    showToast.error(
      "Erro de conexão",
      "Verifique sua internet e tente novamente"
    )
  }
}

export default CustomToast