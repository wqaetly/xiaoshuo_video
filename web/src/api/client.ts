import axios, { AxiosError } from 'axios'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可在此添加认证 token 等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error: AxiosError<{ detail?: string }>) => {
    const errorMessage = error.response?.data?.detail || error.message || '请求失败'
    
    // 不自动显示错误消息，让调用方处理
    console.error('API Error:', errorMessage)
    
    return Promise.reject(new Error(errorMessage))
  }
)

export default apiClient

