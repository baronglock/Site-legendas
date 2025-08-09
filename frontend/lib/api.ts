import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para adicionar token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor para lidar com erros
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const apiClient = {
  // Auth
  login: (data: any) => api.post('/auth/login', data),
  register: (data: any) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  
  // Subtitle
  uploadFile: (formData: FormData) => api.post('/subtitle/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  processUrl: (data: any) => api.post('/subtitle/url', data),
  getJob: (jobId: string) => api.get(`/subtitle/job/${jobId}`),
  
  // User
  getUsage: () => api.get('/user/usage'),
  getJobs: (params?: any) => api.get('/user/jobs', { params }),
  getStats: () => api.get('/user/stats'),
  
  // Payment
  getPlans: () => api.get('/payment/plans'),
  createCheckout: (planId: string) => api.post('/payment/create-checkout-session', {
    plan_id: planId,
    success_url: `${window.location.origin}/dashboard?payment=success`,
    cancel_url: `${window.location.origin}/pricing?payment=cancelled`
  }),
}

export { api }