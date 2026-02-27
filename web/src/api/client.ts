import axios, { AxiosError } from 'axios'
import { message, notification } from 'antd'

/**
 * 标准化的 API 错误响应格式
 */
export interface ApiErrorResponse {
  success: false
  error_code: string
  message: string
  detail?: string
  suggestion?: string
}

/**
 * 自定义 API 错误类
 */
export class ApiError extends Error {
  code: string
  detail?: string
  suggestion?: string
  status: number

  constructor(
    message: string,
    code: string,
    status: number,
    detail?: string,
    suggestion?: string
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.detail = detail
    this.suggestion = suggestion
  }
}

// 错误码到中文描述的映射
const ERROR_CODE_MESSAGES: Record<string, string> = {
  service_unavailable: '服务不可用',
  service_timeout: '服务响应超时',
  api_error: '外部API调用失败',
  rate_limit: '请求过于频繁',
  project_not_found: '项目不存在',
  project_exists: '项目已存在',
  invalid_input: '输入参数无效',
  config_error: '配置错误',
  generation_error: '生成过程出错',
  internal_error: '服务器内部错误',
  http_error: '请求错误',
  network_error: '网络连接失败',
}

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
  (error: AxiosError<ApiErrorResponse>) => {
    // 网络错误或请求被取消
    if (!error.response) {
      const networkError = new ApiError(
        '网络连接失败，请检查网络后重试',
        'network_error',
        0
      )
      console.error('Network Error:', error.message)
      return Promise.reject(networkError)
    }

    const status = error.response.status
    const data = error.response.data

    // 解析后端返回的标准化错误响应
    if (data && typeof data === 'object' && 'error_code' in data) {
      const apiError = new ApiError(
        data.message || ERROR_CODE_MESSAGES[data.error_code] || '请求失败',
        data.error_code,
        status,
        data.detail,
        data.suggestion
      )
      console.error(`API Error [${data.error_code}]:`, data.message, data.detail)
      return Promise.reject(apiError)
    }

    // 处理旧格式的错误响应 (detail 字段)
    const legacyData = error.response.data as unknown as { detail?: string }
    const errorMessage = legacyData?.detail || error.message || '请求失败'

    const apiError = new ApiError(
      errorMessage,
      `http_${status}`,
      status
    )
    console.error('API Error:', errorMessage)
    return Promise.reject(apiError)
  }
)

/**
 * 显示 API 错误通知
 *
 * @param error 错误对象
 * @param fallbackMessage 默认错误消息
 */
export function showApiError(error: unknown, fallbackMessage = '操作失败') {
  if (error instanceof ApiError) {
    if (error.suggestion) {
      // 有排查建议时使用 notification 显示更详细的信息
      const description = error.detail
        ? `${error.detail}\n💡 ${error.suggestion}`
        : `💡 ${error.suggestion}`
      notification.error({
        message: error.message,
        description: description,
        duration: 6,
      })
    } else {
      // 简单错误使用 message 提示
      message.error(error.detail ? `${error.message}: ${error.detail}` : error.message)
    }
  } else if (error instanceof Error) {
    message.error(error.message || fallbackMessage)
  } else {
    message.error(fallbackMessage)
  }
}

// 扩展 apiClient 添加 FormData 支持
const apiClientExtended = {
  get: <T>(url: string, config?: { params?: Record<string, unknown> }): Promise<T> =>
    apiClient.get(url, config),
  post: <T>(url: string, data?: unknown): Promise<T> => apiClient.post(url, data),
  put: <T>(url: string, data?: unknown): Promise<T> => apiClient.put(url, data),
  delete: <T>(url: string): Promise<T> => apiClient.delete(url),
  postFormData: <T>(url: string, formData: FormData): Promise<T> =>
    apiClient.post(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  putFormData: <T>(url: string, formData: FormData): Promise<T> =>
    apiClient.put(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

export default apiClientExtended

