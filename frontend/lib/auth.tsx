import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter } from 'next/router'
import { apiClient } from './api'

interface User {
  id: string
  email: string
  plan: string
  minutesRemaining: number
  minutesTotal: number
  jobsCompleted: number
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string) => Promise<void>
  logout: () => void
  updateUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('token')
      
      // MODO LOCAL - usar dados do localStorage
      const savedUser = localStorage.getItem('user')
      if (savedUser) {
        setUser(JSON.parse(savedUser))
        setLoading(false)
        return
      }
      
      if (!token) {
        setLoading(false)
        return
      }

      // Tenta pegar do servidor
      try {
        const response = await apiClient.getMe()
        const userData = {
          id: response.data.id,
          email: response.data.email,
          plan: response.data.plan || 'free',
          minutesRemaining: response.data.usage?.minutes_available || 1000,
          minutesTotal: response.data.usage?.minutes_limit || 1000,
          jobsCompleted: 0
        }
        setUser(userData)
        localStorage.setItem('user', JSON.stringify(userData))
      } catch (error) {
        console.log('Usando modo mock local')
      }
    } catch (error) {
      console.error('Erro auth:', error)
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    } finally {
      setLoading(false)
    }
  }

  const login = async (email: string) => {
    try {
      const response = await apiClient.login({ email })
      localStorage.setItem('token', response.data.access_token)
      
      const userData = {
        id: response.data.user_id || 'mock_user',
        email: email,
        plan: 'free',
        minutesRemaining: 1000,
        minutesTotal: 1000,
        jobsCompleted: 0
      }
      
      setUser(userData)
      localStorage.setItem('user', JSON.stringify(userData))
      router.push('/dashboard')
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    router.push('/')
  }

  const updateUser = async () => {
    await checkAuth()
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}